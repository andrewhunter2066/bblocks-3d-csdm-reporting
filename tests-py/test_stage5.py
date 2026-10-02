"""Stage 5 tests: scheme context, the schedule document, approved form, certification and legislation.

Run from the repository root:  python3 -m pytest tests-py
"""
import json
import re
import subprocess
import sys

import pytest

from harness import REPO_ROOT, run_transform

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
EXAMPLES = REPO_ROOT / '_sources/adapters/wa-csdm/examples'
FIXTURE = EXAMPLES / 'sp83687-entitlement.json'
LABELS = REPO_ROOT / '_sources/adapters/wa-csdm/transforms/vocabulary_labels.py'
FORM_IRI = 'https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738'
FORM_SCHEME = 'https://linked.data.gov.au/def/csdm/wa-approved-form'
LOCALITY_SCHEME = 'https://linked.data.gov.au/def/csdm/wa-locality'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def to_report(csd, transform='to-strata-entitlement-report'):
    text = csd if isinstance(csd, str) else json.dumps(csd)
    return json.loads(run_transform(ADAPTER, transform, text))


def outcome(report, check_id):
    return next(c['outcome'] for c in report['checks'] if c['id'] == check_id)


def resolve(document, pointer):
    target = document
    for token in pointer.split('/')[1:]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    return target


def scheme_of(csd):
    return next(f for f in csd['parcels'][0]['features']
                if f['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-scheme')


def address_part(csd, part_type):
    return next(p for p in scheme_of(csd)['properties']['schemeAddress']['hasPart'] if p['partType'] == part_type)


def certification_annotation(csd):
    return next(a for a in csd['annotations'] if a['role'] == 'wa-annotation-role:licensed-valuer-certification')


def schedule_document(csd):
    return next(d for d in csd['supportingDocuments']
                if d['role'] == 'wa-survey-documentation-type:unitEntitlementSchedule')


@pytest.fixture
def csd():
    return load(FIXTURE)


@pytest.fixture(scope='module')
def sp83687():
    return to_report(FIXTURE.read_text(encoding='utf-8'))


# --- Done-when criterion: every mapping row marked Yes/Opt. is populated or explicitly statused --------

def test_every_mapping_row_is_populated(sp83687):
    content = sp83687['content']
    scheme, basis = content['scheme'], content['basis']
    rows = {
        '1 source dataset': sp83687['sources'][0]['id'] == 'SP-83687-1-1-0.00',
        '2 scheme (subject)': sp83687['subject']['ref']['id'] == 'uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e',
        '3 scheme number': scheme['schemeNumber']['value'] == 'SP83687',
        '4 scheme address': scheme['address']['formatted']['value'] == '281 Belmont Avenue, Cloverdale',
        '5 scheme name': scheme['schemeName']['value'] == '281 Belmont Avenue, Cloverdale',
        '6 member lots': len(content['lots']) == 9,
        '7 lot numbers': [l['lotNumber']['value'] for l in content['lots']] == [str(n) for n in range(1, 10)],
        '8 lot identity': all(l['ref']['id'].startswith('uuid:') for l in content['lots']),
        '9 unit entitlements': [l['entitlement']['value'] for l in content['lots']]
                               == [117, 108, 113, 108, 108, 113, 108, 108, 117],
        '10 declared total': content['totals']['declared']['value'] == 1000,
        '11 calculated total': content['totals']['calculated']['value'] == 1000,
        '13 schedule document': sp83687['documents'][0]['title'] == 'Schedule of Unit Entitlements - SP83687',
        '14 approved form': basis['form']['label']['value']
                            == 'Approved Schedule of Unit Entitlements Form number 2021-47738',
        '15 valuer certification': (basis['certification']['certifier']['lastName']['value'],
                                    basis['certification']['dateCertified']['value']) == ('Example', '2022-05-17'),
        '16 legislative basis': 'Strata Titles Act 1985' in content['legislativeBasis'][0]['value'],
    }
    assert [row for row, ok in rows.items() if not ok] == []
    # Row 12 (lot proportion) is optional and awaits a decision ("Include?"), so it is not produced.
    assert all('proportion' not in lot for lot in content['lots'])


def test_sp83687_is_complete_with_document_checks_evaluated(sp83687):
    assert sp83687['status'] == 'complete'
    for check_id in ('schedule-document-referenced', 'valuer-certification-present',
                     'certification-linked-to-schedule', 'scheme-number-consistent'):
        assert outcome(sp83687, check_id) == 'pass'
    assert outcome(sp83687, 'document-hrefs-resolvable') == 'not-evaluated'  # D12: no base for relative hrefs


# --- Provenance --------------------------------------------------------------------------------------

def test_source_values_point_at_the_source(sp83687):
    csd = load(FIXTURE)
    certification = sp83687['content']['basis']['certification']
    for rv in (sp83687['content']['scheme']['schemeName'], certification['dateCertified'],
               *certification['certifier'].values()):
        assert rv['status'] == 'reported'
        assert resolve(csd, rv['sourceRefs'][0]['pointer']) == rv['value']
    road = sp83687['content']['scheme']['address']['parts'][1]
    assert road['partType'] == 'apt:road'
    assert resolve(csd, road['label']['sourceRefs'][0]['pointer']) == 'Belmont Avenue'


def test_vocabulary_values_name_their_concept_and_vocabulary(sp83687):
    sources = {s['id']: s for s in sp83687['sources']}
    form = sp83687['content']['basis']['form']
    for rv in (form['label'], form['validFrom'], form['source'], *sp83687['content']['legislativeBasis']):
        assert rv['status'] == 'reported'
        assert rv['sourceRefs'] == [{'dataset': FORM_SCHEME, 'pointer': '', 'id': FORM_IRI}]
    assert (form['validFrom']['value'], form['validFrom']['lexicalValue']) == ('2021-07-07', '2021-07-07/..')
    locality = sp83687['content']['scheme']['address']['parts'][2]['label']
    assert locality == {'value': 'Cloverdale', 'status': 'reported',
                        'sourceRefs': [{'dataset': LOCALITY_SCHEME, 'pointer': '',
                                        'id': LOCALITY_SCHEME + '/cloverdale'}]}
    assert sources[FORM_SCHEME]['kind'] == sources[LOCALITY_SCHEME]['kind'] == 'vocabulary'


def test_formatted_address_is_derived_from_its_parts(sp83687):
    formatted = sp83687['content']['scheme']['address']['formatted']
    assert formatted['derivation']['method'] == 'format-address'
    pieces = [resolve(sp83687, p) for p in formatted['derivation']['inputs']]
    pieces = [p['value'] if isinstance(p, dict) else p for p in pieces]
    assert pieces == [281, 'Belmont Avenue', 'Cloverdale']


def test_documents_and_annotations_hold_only_what_the_report_relies_on(sp83687):
    assert [d['id'] for d in sp83687['documents']] == ['unit-entitlement-schedule']
    assert sp83687['documents'][0]['conformsTo'] == 'wa-approved-form:2021-47738'
    assert sp83687['documents'][0]['sourceRef']['pointer'] == '/supportingDocuments/3'
    annotation = sp83687['annotations'][0]
    assert (annotation['id'], annotation['documentRef']) == ('licensed-valuer-certification', 'unit-entitlement-schedule')
    assert annotation['statement'].startswith('Schedule of Unit Entitlements certified by Jordan Example')


# --- Address (D8) ------------------------------------------------------------------------------------

def test_road_without_label_makes_the_address_unresolved(csd):
    del address_part(csd, 'apt:road')['value']['label']
    formatted = to_report(csd)['content']['scheme']['address']['formatted']
    assert formatted['status'] == 'unresolved' and formatted['value'] is None
    assert formatted['sourceRefs'][0]['pointer'].endswith('/schemeAddress/hasPart/1/value')


def test_unknown_locality_makes_the_address_unresolved(csd):
    address_part(csd, 'apt:locality')['value'] = 'wa-locality:atlantis'
    address = to_report(csd)['content']['scheme']['address']
    assert address['parts'][2]['label']['status'] == 'unresolved'
    assert address['formatted']['status'] == 'unresolved'


def test_number_range_is_formatted(csd):
    address_part(csd, 'apt:addressNumberFirst')  # present
    scheme_of(csd)['properties']['schemeAddress']['hasPart'].insert(1, {'partType': 'apt:addressNumberLast', 'value': 285})
    assert to_report(csd)['content']['scheme']['address']['formatted']['value'] == '281-285 Belmont Avenue, Cloverdale'


def test_missing_address_is_not_supplied(csd):
    del scheme_of(csd)['properties']['schemeAddress']
    address = to_report(csd)['content']['scheme']['address']
    assert address == {'parts': [], 'formatted': {
        'value': None, 'status': 'not-supplied', 'note': 'The scheme parcel has no schemeAddress',
        'sourceRefs': [{'dataset': 'SP-83687-1-1-0.00', 'pointer': '/parcels/0/features/1/properties'}]}}


# --- Schedule, form and legislation ------------------------------------------------------------------

def test_unknown_form_is_unresolved_and_gives_no_legislation_text(csd):
    schedule_document(csd)['conformsTo'] = 'wa-approved-form:9999'
    report = to_report(csd)
    form = report['content']['basis']['form']
    assert form['label']['status'] == form['validFrom']['status'] == 'unresolved'
    assert report['content']['legislativeBasis'][0]['status'] == 'unresolved'
    assert report['status'] == 'complete'  # the schedule and certification are still there


def test_missing_schedule_document_is_incomplete(csd):
    csd['supportingDocuments'] = [d for d in csd['supportingDocuments'] if d is not schedule_document(csd)]
    report = to_report(csd)
    assert 'schedule' not in report['content']['basis'] and report['content']['legislativeBasis'] == []
    assert outcome(report, 'schedule-document-referenced') == 'fail'
    assert outcome(report, 'certification-linked-to-schedule') == 'not-applicable'
    assert report['status'] == 'incomplete'


# --- Certification (D9) ------------------------------------------------------------------------------

def test_missing_certification_is_incomplete(csd):
    csd['annotations'].remove(certification_annotation(csd))
    report = to_report(csd)
    assert 'certification' not in report['content']['basis'] and report['annotations'] == []
    assert outcome(report, 'valuer-certification-present') == 'fail'
    assert report['status'] == 'incomplete'


def test_certification_without_licence_number_is_incomplete(csd):
    del certification_annotation(csd)['certifier']['licensedValuerNumber']
    report = to_report(csd)
    number = report['content']['basis']['certification']['certifier']['licensedValuerNumber']
    assert number['status'] == 'not-supplied'
    assert outcome(report, 'valuer-certification-present') == 'fail'
    assert report['status'] == 'incomplete'


def test_certification_linked_to_another_document_is_reported(csd):
    certification_annotation(csd)['href'] = csd['supportingDocuments'][0]['href']
    report = to_report(csd)
    assert [d['id'] for d in report['documents']] == ['unit-entitlement-schedule', 'document-1']
    assert report['content']['basis']['certification']['documentRef'] == 'document-1'
    assert outcome(report, 'certification-linked-to-schedule') == 'fail'
    assert report['status'] == 'complete'  # an info check does not change the status


# --- Scheme number cross-check -----------------------------------------------------------------------

def test_scheme_number_that_disagrees_is_a_warning(csd):
    scheme_of(csd)['properties']['schemeNumber'] = 'SP83688'
    report = to_report(csd)
    check = next(c for c in report['checks'] if c['id'] == 'scheme-number-consistent')
    assert check['outcome'] == 'fail' and check['evidence']['csdName'] == 'SP83687'
    assert report['status'] == 'incomplete'


# --- Vocabulary label table --------------------------------------------------------------------------

def nested_labels():
    """The label table as the facts transform sees it (a nested get_transformer call)."""
    return json.loads(run_transform(ADAPTER, 'vocabulary-labels', '{}', _stack=((ADAPTER, 'caller'),)))


def test_label_table_is_only_output_when_called_by_another_transform():
    assert run_transform(ADAPTER, 'vocabulary-labels', '{}') is None
    table = nested_labels()
    assert set(table) == {'wa-locality', 'wa-approved-form'}
    assert table['wa-locality']['concepts']['cloverdale'] == {'prefLabel': 'Cloverdale'}
    assert table['wa-approved-form']['concepts']['2021-47738']['valid'] == '2021-07-07/..'


def test_label_table_matches_the_local_vocabularies():
    icsm, wa = REPO_ROOT.parent / 'icsm-vocabs', REPO_ROOT.parent / '3d-csdm-profile-wa'
    if not (icsm.exists() and wa.exists()):
        pytest.skip('sibling vocabulary repositories are not checked out')
    current = LABELS.read_text(encoding='utf-8')
    try:
        subprocess.run([sys.executable, str(REPO_ROOT / 'scripts/build_vocabulary_labels.py')],
                       check=True, capture_output=True)
        assert LABELS.read_text(encoding='utf-8') == current, 'out of date: run scripts/build_vocabulary_labels.py'
    finally:
        LABELS.write_text(current, encoding='utf-8', newline='\n')
    table = nested_labels()
    for prefix, path in (('wa-locality', icsm / 'vocabs/LandParcels/CSD-Header/wa-locality.ttl'),
                         ('wa-approved-form', wa / 'profiles/wa-approved-form-supplement.ttl')):
        declared = len(re.findall(r'^:\S+\n', path.read_text(encoding='utf-8'), flags=re.M))
        assert len(table[prefix]['concepts']) == declared


# --- Presentation ------------------------------------------------------------------------------------

def test_html_shows_the_basis_of_the_schedule(sp83687):
    html = run_transform(REPORT, 'to-html', json.dumps(sp83687))
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<sup.*?</sup>', '', html, flags=re.S)))
    for expected in ('Scheme address 281 Belmont Avenue, Cloverdale',
                     'Effective for use from 2021-07-07',
                     'Legislation Approved under section 37',
                     'Licensed valuer number 00000',
                     'Date certified 2022-05-17'):
        assert expected in text, expected
    assert '<a href="documents/SP83687-unit-entitlement-schedule.pdf">' in html
    assert 'source: ' + FORM_IRI in html  # vocabulary provenance in the tooltip
