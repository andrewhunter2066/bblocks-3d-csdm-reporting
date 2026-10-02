"""Summarise a source-conformance run (called by check_source_conformance.sh).

Runs inside the bblocks-postprocess image (/venv/bin/python), which provides jsonschema,
requests, PyYAML and rdflib.

The postprocessor's own report stops at the first JSON Schema error and stores SHACL results
as raw Turtle. This script lists *every* JSON Schema error (validating against the profile's
published annotated schema) and groups SHACL results by message, path and value.

Usage: summarise_conformance.py REPORT_JSON DATASET_JSON PROFILE_ID REGISTER_URL [REGISTER_URL ...]
Exit status: 0 = conforms, 1 = does not conform, 2 = could not evaluate.
"""
import collections
import json
import re
import sys

import jsonschema
import rdflib
import requests
import yaml
from rdflib.namespace import SH

MAX_VALUES = 10


def fetch(uri):
    response = requests.get(uri, timeout=120)
    response.raise_for_status()
    return yaml.safe_load(response.text) if uri.endswith(('.yaml', '.yml')) else response.json()


def find_schema_url(profile_id, register_urls):
    for url in register_urls:
        register = fetch(url)
        for bblock in register.get('bblocks', []):
            if bblock.get('itemIdentifier') == profile_id:
                schema = bblock.get('schema') or {}
                return schema.get('application/json') if isinstance(schema, dict) else schema
    return None


def leaf_errors(error):
    if error.context:
        for child in error.context:
            yield from leaf_errors(child)
    else:
        yield error


def json_schema_errors(dataset, schema_url):
    schema = fetch(schema_url)
    validator_cls = jsonschema.validators.validator_for(schema)
    resolver = jsonschema.RefResolver(schema_url, schema, handlers={'https': fetch, 'http': fetch})
    validator = validator_cls(schema, resolver=resolver)
    grouped = collections.Counter()
    for error in validator.iter_errors(dataset):
        for leaf in leaf_errors(error):
            path = re.sub(r'/\d+', '/*', '/'.join(str(p) for p in leaf.absolute_path)) or '(root)'
            grouped[(path, leaf.message[:160])] += 1
    return grouped


def shacl_results(report):
    grouped = collections.defaultdict(list)
    for block in report['bblocks'].values():
        for item in block['items']:
            for section in item['sections']:
                if section['name'] != 'SHACL':
                    continue
                for entry in section['entries']:
                    if not (entry.get('isError') and entry.get('graph')):
                        continue
                    graph = rdflib.Graph().parse(data=entry['graph'], format='turtle')
                    for result in graph.subjects(rdflib.RDF.type, SH.ValidationResult):
                        path = graph.value(result, SH.resultPath)
                        key = (str(graph.value(result, SH.resultMessage)),
                               str(path) if isinstance(path, rdflib.URIRef) else '(complex path)')
                        grouped[key].append(str(graph.value(result, SH.value)))
    return grouped


def main(report_path, dataset_path, profile_id, *register_urls):
    with open(report_path, encoding='utf-8') as f:
        report = json.load(f)
    if not any(block['items'] for block in report['bblocks'].values()):
        print('No test resources were validated: see postprocess.log')
        return 2
    with open(dataset_path, encoding='utf-8') as f:
        dataset = json.load(f)

    conforms = True

    schema_url = find_schema_url(profile_id, register_urls)
    print(f'JSON Schema ({schema_url or "schema not found"})')
    if not schema_url:
        return 2
    js_errors = json_schema_errors(dataset, schema_url)
    if not js_errors:
        print('  pass')
    for (path, message), count in sorted(js_errors.items()):
        conforms = False
        print(f'  FAIL x{count:<4} {path}\n             {message}')

    print('\nSHACL (profile shapes, after JSON-LD uplift with the profile context)')
    shacl = shacl_results(report)
    if not shacl:
        print('  pass')
    for (message, path), values in sorted(shacl.items(), key=lambda kv: -len(kv[1])):
        conforms = False
        distinct = sorted(set(values))
        print(f'  FAIL x{len(values):<4} {message}\n             path: {path}')
        for value in distinct[:MAX_VALUES]:
            print(f'             value: {value}')
        if len(distinct) > MAX_VALUES:
            print(f'             ... {len(distinct) - MAX_VALUES} more distinct values')

    print(f'\nResult: dataset {"CONFORMS" if conforms else "DOES NOT CONFORM"} to {profile_id}')
    return 0 if conforms else 1


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:]))
