#!/usr/bin/env python3
"""Generate the WA 3D CSDM adapter's vocabulary label table from local SKOS (.ttl) vocabularies.

The WA vocabularies the entitlement report needs (localities, approved forms) are not yet published at
resolvable IRIs, so the adapter carries their labels in a generated transform,
`_sources/adapters/wa-csdm/transforms/vocabulary_labels.py` (transform id `vocabulary-labels`), which
other transforms read through get_transformer(). Re-run this script when the vocabularies change;
once they are published, the adapter can look them up instead.

The parser reads the regular Turtle layout these vocabularies are generated in (one `:concept` block per
concept, closed by a line holding only `.`), taking each wanted property's value from a quoted literal or
an `<IRI>`. It is not a general Turtle parser: it fails loudly if a vocabulary does not have the expected
number of concepts.

ICSM vocabularies come from Surround's fork, sa-icsm-vocabs, until the WA vocabulary remediation is merged
upstream into icsm-vocabs; set ICSM_VOCAB_ROOT or pass --icsm-vocabs to read another checkout. Either may name the
checkout or its vocabs/ folder (the workspace sets ICSM_VOCAB_ROOT to the vocabs/ folder).

Usage (from the repository root):
    python3 scripts/build_vocabulary_labels.py [--icsm-vocabs ../sa-icsm-vocabs] [--wa-profile ../3d-csdm-profile-wa]
"""
import argparse
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ICSM_VOCABS = Path(os.environ.get('ICSM_VOCAB_ROOT') or REPO.parent / 'sa-icsm-vocabs')
OUTPUT = REPO / '_sources/adapters/wa-csdm/transforms/vocabulary_labels.py'

# (CURIE prefix used in the data, path relative to its repository, repository option, wanted properties)
VOCABULARIES = [
    ('wa-locality', 'vocabs/LandParcels/CSD-Header/wa-locality.ttl', 'icsm_vocabs',
     ('prefLabel',)),
    ('wa-approved-form', 'profiles/wa-approved-form-supplement.ttl', 'wa_profile',
     ('prefLabel', 'definition', 'valid', 'source', 'scopeNote')),
]
PROPERTIES = {'prefLabel': 'skos:prefLabel', 'definition': 'skos:definition', 'scopeNote': 'skos:scopeNote',
              'valid': 'dcterms:valid', 'source': 'dcterms:source'}


def icsm_checkout(path: Path) -> Path:
    """The ICSM vocabularies checkout, given the checkout or its vocabs/ folder."""
    return path.parent if path.name == 'vocabs' and not (path / 'vocabs').is_dir() else path


def parse(path: Path, wanted):
    text = path.read_text(encoding='utf-8')
    namespace = re.search(r'^PREFIX : <([^>]+)>', text, flags=re.M).group(1)
    scheme = re.search(r'^PREFIX cs: <([^>]+)>', text, flags=re.M).group(1)
    scheme_block = re.search(r'^cs:\n(.*?)^\.$', text, flags=re.M | re.S)
    title = re.search(r'skos:(?:prefLabel|definition) "([^"]*)"', scheme_block.group(1)) if scheme_block else None
    concepts = {}
    for name, body in re.findall(r'^:(\S+)\n(.*?)^\.$', text, flags=re.M | re.S):
        if 'skos:Concept' not in body:
            continue
        concept = {}
        for key in wanted:
            # A literal ("...") or an IRI (<...>); dcterms:source, for example, is an IRI.
            match = re.search(rf'{re.escape(PROPERTIES[key])} (?:"((?:[^"\\]|\\.)*)"|<([^<>"\s]*)>)', body)
            if match:
                concept[key] = match.group(1) if match.group(1) is not None else match.group(2)
        concepts[name] = concept
    declared = len(re.findall(r'^:\S+\n', text, flags=re.M))
    if len(concepts) != declared:
        raise SystemExit(f'{path}: parsed {len(concepts)} concepts but the file declares {declared}')
    return {'namespace': namespace, 'scheme': scheme, 'title': title.group(1) if title else None,
            'file': str(path), 'concepts': concepts}


def _python_literal(table):
    """The table as a Python literal with one concept per line (compact: the register inlines it)."""
    lines = ['{']
    for prefix, vocabulary in sorted(table.items()):
        lines.append(f'    {prefix!r}: {{')
        for key in ('namespace', 'scheme', 'title', 'file'):
            lines.append(f'        {key!r}: {vocabulary[key]!r},')
        lines.append("        'concepts': {")
        for name, concept in sorted(vocabulary['concepts'].items()):
            lines.append(f'            {name!r}: {dict(sorted(concept.items()))!r},')
        lines.append('        },')
        lines.append('    },')
    lines.append('}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--icsm-vocabs', default=str(ICSM_VOCABS))
    parser.add_argument('--wa-profile', default=str(REPO.parent / '3d-csdm-profile-wa'))
    args = parser.parse_args()
    roots = {'icsm_vocabs': icsm_checkout(Path(args.icsm_vocabs)), 'wa_profile': Path(args.wa_profile)}

    table = {}
    for prefix, relative, root, wanted in VOCABULARIES:
        vocabulary = parse(roots[root] / relative, wanted)
        vocabulary['file'] = f'{roots[root].name}/{relative}'
        table[prefix] = vocabulary
        print(f'{prefix}: {len(vocabulary["concepts"])} concepts from {vocabulary["file"]}')

    body = _python_literal(table)
    OUTPUT.write_text(f'''# Transform: (ignored input) -> WA vocabulary label table (JSON).
# GENERATED by scripts/build_vocabulary_labels.py from local SKOS vocabularies; do not edit by hand.
#
# Carries the labels (and, for approved forms, validity, source and scope note) of the WA vocabularies
# the adapter needs, keyed by the CURIE prefix and local name used in WA 3D CSDM data. Other transforms
# read it with get_transformer('csdm.reporting.adapters.wa-csdm', 'vocabulary-labels'). When run on its
# own (for example against this block's examples) it produces no output.
import json

VOCABULARIES = {body}

nested = bool((getattr(transform_metadata, 'metadata', None) or {{}}).get('_nested_transform'))
output_data = json.dumps(VOCABULARIES, ensure_ascii=False) if nested else None
''', encoding='utf-8', newline='\n')
    print(f'wrote {OUTPUT.relative_to(REPO)} ({OUTPUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
