"""Stage 7 tests: semantics (JSON-LD contexts, ontologies, codelists, SHACL), checked without RDF libraries.

The RDF itself (uplift of every example, SHACL validation, the SHACL must-fail tests) is checked by the
OGC Building Blocks postprocessor build; these tests keep the semantic files consistent with each other
and with the schemas.

Run from the repository root:  python3 -m pytest tests-py
"""
import json
import re

import pytest

from harness import REPO_ROOT, run_transform

SOURCES = REPO_ROOT / '_sources'
ENVELOPE_CONTEXT = SOURCES / 'cadastral-report/context.jsonld'
STRATA_CONTEXT = SOURCES / 'reports/strata-entitlement/context.jsonld'
CR_ONTOLOGY = SOURCES / 'cadastral-report-ontology/ontology.ttl'
CODELISTS = SOURCES / 'cadastral-report-ontology/data.ttl'
SE_ONTOLOGY = SOURCES / 'reports/strata-entitlement/ontology.ttl'
BASE = 'https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/'
LADM_ENTITLEMENT = 'https://w3id.org/ogc/ladm/parcels/entitlementPortion'

# Namespaces whose terms are reused, not minted here.
REUSED = ('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'http://www.w3.org/2000/01/rdf-schema#',
          'http://purl.org/dc/terms/', 'http://www.w3.org/ns/prov#', 'http://www.w3.org/ns/earl#',
          'http://www.w3.org/ns/shacl#', 'https://schema.org/')


def load_context(path):
    return json.loads(path.read_text(encoding='utf-8'))['@context']


def expand(curie, contexts):
    prefixes = {k: v for c in contexts for k, v in c.items() if isinstance(v, str) and v.endswith(('/', '#'))}
    prefix, _, local = curie.partition(':')
    return prefixes[prefix] + local if prefix in prefixes and not local.startswith('//') else curie


def term_iris(context, contexts):
    """(term, IRI) for every term definition in a context, including scoped contexts."""
    for term, definition in context.items():
        if term.startswith('@') or (isinstance(definition, str) and definition.endswith(('/', '#'))):
            continue
        iri = definition if isinstance(definition, str) else definition.get('@id')
        if iri:
            yield term, expand(iri, contexts)
        if isinstance(definition, dict) and isinstance(definition.get('@context'), dict):
            yield from term_iris(definition['@context'], contexts)


def minted(path, prefix):
    """Local names declared in an ontology file (`prefix:name a owl:...`)."""
    return set(re.findall(rf'^{prefix}:(\S+) a owl:', path.read_text(encoding='utf-8'), flags=re.M))


# Every vocabulary of the register: (ontology file, its prefix, its namespace). Discovered, so a new report
# type's ontology is covered without changing these tests.
ONTOLOGIES = [(path, prefix, namespace) for path in sorted(SOURCES.rglob('ontology.ttl'))
              for prefix, namespace in re.findall(rf'^PREFIX (\w+): <({re.escape(BASE)}[\w-]+/)>',
                                                  path.read_text(encoding='utf-8'), flags=re.M)
              if minted(path, prefix)]


@pytest.fixture(scope='module')
def contexts():
    return [load_context(path) for path in sorted(SOURCES.rglob('context.jsonld'))]


def test_every_report_block_has_a_context_and_a_vocabulary():
    report_blocks = sorted(p.parent for p in (SOURCES / 'reports').glob('*/bblock.json'))
    assert len(report_blocks) >= 2
    for block in report_blocks:
        assert (block / 'context.jsonld').exists() and (block / 'ontology.ttl').exists(), block.name


# --- Contexts and ontologies agree --------------------------------------------------------------------

def test_every_context_term_is_reused_or_defined_in_an_ontology(contexts):
    defined = {namespace + n for path, prefix, namespace in ONTOLOGIES for n in minted(path, prefix)}
    undefined = sorted({iri for c in contexts for _, iri in term_iris(c, contexts)
                        if not iri.startswith(REUSED) and iri not in defined})
    assert undefined == []


@pytest.mark.parametrize('path, prefix, namespace', [o for o in ONTOLOGIES if o[1] != 'cr'],
                         ids=[o[1] for o in ONTOLOGIES if o[1] != 'cr'])
def test_every_minted_report_type_term_is_used_by_the_context(contexts, path, prefix, namespace):
    used = {iri for c in contexts for _, iri in term_iris(c, contexts)}
    assert sorted(n for n in minted(path, prefix) if namespace + n not in used) == []


def test_every_minted_report_term_is_used_by_a_context_shape_or_schema_annotation(contexts):
    used = {iri for c in contexts for _, iri in term_iris(c, contexts)}
    text = ''.join(p.read_text(encoding='utf-8') for p in (SOURCES / 'cadastral-report/shapes.shacl',
                                                            SOURCES / 'cadastral-report/schema.yaml'))
    unused = sorted(n for n in minted(CR_ONTOLOGY, 'cr')
                    if BASE + 'cadastral-report/' + n not in used and f'cr:{n}' not in text
                    and f'cadastral-report/{n}' not in text and n[0].islower())
    assert unused == []


@pytest.mark.parametrize('path, prefix, namespace', ONTOLOGIES, ids=[o[1] for o in ONTOLOGIES])
def test_every_minted_term_is_labelled_defined_and_attributed(path, prefix, namespace):
    blocks = re.findall(rf'^{prefix}:(\S+) a owl:\w+ ;(.*?) \.\n', path.read_text(encoding='utf-8'), flags=re.M | re.S)
    assert len(blocks) == len(minted(path, prefix)) > 0
    for name, body in blocks:
        for annotation in ('rdfs:label', 'skos:definition', 'rdfs:isDefinedBy'):
            assert annotation in body, f'{prefix}:{name} lacks {annotation}'


def test_unit_entitlement_is_aligned_with_ladm():
    body = SE_ONTOLOGY.read_text(encoding='utf-8').split('se:unitEntitlement a')[1].split(' .\n')[0]
    assert f'skos:closeMatch <{LADM_ENTITLEMENT}>' in body


# --- Codelists and code mappings ----------------------------------------------------------------------

@pytest.mark.parametrize('scheme, values', [
    ('report-stage', ['facts', 'complete']),
    ('report-status', ['complete', 'incomplete', 'invalid']),
    ('check-category', ['source-conformance', 'generation', 'domain']),
    ('value-status', ['reported', 'derived', 'documented', 'configured', 'not-supplied', 'unresolved',
                      'invalid', 'conflicting']),
])
def test_codelists_match_the_schema_enums(scheme, values):
    ttl = CODELISTS.read_text(encoding='utf-8')
    schema = (SOURCES / 'cadastral-report/schema.yaml').read_text(encoding='utf-8')
    assert f'<{BASE}{scheme}>' in ttl or f'{BASE}{scheme}>' in ttl
    for value in values:
        assert f'skos:notation "{value}"' in ttl
        assert f'- {value}' in schema
    assert f'"@vocab": "{BASE}{scheme}/"' in ENVELOPE_CONTEXT.read_text(encoding='utf-8')


def test_check_outcome_and_severity_codes_map_to_earl_and_shacl():
    schema = (SOURCES / 'cadastral-report/schema.yaml').read_text(encoding='utf-8')
    block = schema[schema.index('x-jsonld-extra-terms:'):schema.index('required:', schema.index('x-jsonld-extra-terms:'))]
    mapped = dict(re.findall(r'^\s+([a-z-]+): (\S+)$', block, flags=re.M))
    assert mapped == {
        'pass': 'http://www.w3.org/ns/earl#passed', 'fail': 'http://www.w3.org/ns/earl#failed',
        'not-evaluated': 'http://www.w3.org/ns/earl#untested', 'not-applicable': 'http://www.w3.org/ns/earl#inapplicable',
        'error': 'http://www.w3.org/ns/shacl#Violation', 'warning': 'http://www.w3.org/ns/shacl#Warning',
        'info': 'http://www.w3.org/ns/shacl#Info'}


# --- Provenance to the source's own semantics (Stage 7 done-when criterion, JSON side) ---------------

def test_entitlement_values_name_the_ladm_property_they_were_read_from():
    source = (SOURCES / 'adapters/wa-csdm/examples/sp83687-entitlement.json').read_text(encoding='utf-8')
    report = json.loads(run_transform('csdm.reporting.adapters.wa-csdm', 'to-strata-entitlement-report', source))
    for lot in report['content']['lots']:
        assert [ref['property'] for ref in lot['entitlement']['sourceRefs']] == [LADM_ENTITLEMENT]
    # No IRI is invented for source properties the source profile does not define.
    assert 'property' not in report['content']['totals']['declared']['sourceRefs'][0]
    assert all('property' not in ref for lot in report['content']['lots'] for ref in lot['lotNumber']['sourceRefs'])


def test_report_examples_carry_the_ladm_link():
    report = json.loads((SOURCES / 'reports/strata-entitlement/examples/sp83687-report.json').read_text(encoding='utf-8'))
    assert sum(ref.get('property') == LADM_ENTITLEMENT for lot in report['content']['lots']
               for ref in lot['entitlement']['sourceRefs']) == 9


# --- SHACL must-fail tests change exactly one thing ---------------------------------------------------

@pytest.mark.parametrize('block, name, path, expected', [
    ('reports/strata-entitlement', 'calculated-total-not-the-sum', ['content', 'totals', 'calculated', 'value'], 1001),
    ('reports/strata-entitlement', 'lot-count-not-the-number-of-lots', ['content', 'totals', 'lotCount', 'value'], 10),
    ('reports/strata-entitlement', 'document-ref-unresolved', ['content', 'basis', 'certification', 'documentRef'], 'no-such-document'),
    ('cadastral-report', 'status-contradicts-checks', ['status'], 'incomplete'),
])
def test_shacl_must_fail_tests_differ_from_the_valid_example_in_one_value(block, name, path, expected):
    example = json.loads((SOURCES / 'reports/strata-entitlement/examples/sp83687-report.json').read_text(encoding='utf-8'))
    failing = json.loads((SOURCES / block / 'tests' / f'{name}-fail.json').read_text(encoding='utf-8'))
    target = failing
    for key in path[:-1]:
        target = target[key]
    assert target[path[-1]] == expected
    target[path[-1]] = None
    reference = example
    for key in path[:-1]:
        reference = reference[key]
    reference[path[-1]] = None
    assert failing == example
