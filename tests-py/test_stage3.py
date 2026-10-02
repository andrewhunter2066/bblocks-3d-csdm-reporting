"""Stage 3 tests: provenance and explicit status for every report value.

Run from the repository root:  python3 -m pytest tests-py
"""
import json

import pytest

from harness import REPO_ROOT, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
EXAMPLES = REPO_ROOT / '_sources/adapters/wa-csdm/examples'
FIXTURE = EXAMPLES / 'sp83687-entitlement.json'
MISSING = EXAMPLES / 'missing-entitlement.json'
STATUS_CODELIST = REPO_ROOT / '_sources/cadastral-report-ontology/data.ttl'
NO_VALUE = {'not-supplied', 'unresolved', 'invalid', 'conflicting'}


def resolve(document, pointer):
    """Resolve a JSON Pointer (RFC 6901)."""
    target = document
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        target = target[int(token)] if isinstance(target, list) else target[token]
    return target


def report_values(report):
    """Yield (pointer, ReportValue) for every ReportValue in the report content."""
    content = report['content']
    yield '/content/scheme/schemeNumber', content['scheme']['schemeNumber']
    for i, lot in enumerate(content['lots']):
        yield f'/content/lots/{i}/lotNumber', lot['lotNumber']
        yield f'/content/lots/{i}/entitlement', lot['entitlement']
    for name, value in (content.get('totals') or {}).items():
        yield f'/content/totals/{name}', value


def all_statuses(node):
    """Status of every ReportValue anywhere in the report content."""
    if isinstance(node, dict):
        if 'status' in node and 'value' in node:
            yield node['status']
        else:
            for child in node.values():
                yield from all_statuses(child)
    elif isinstance(node, list):
        for child in node:
            yield from all_statuses(child)


def assert_status_rules(rv):
    """The ReportValue rules of csdm.reporting.cadastral-report, checked without Docker."""
    if rv['status'] in NO_VALUE:
        assert rv.get('value') is None
    else:
        assert rv.get('value') is not None
    required = {'reported': ['sourceRefs'], 'derived': ['derivation'], 'unresolved': ['sourceRefs'],
                'invalid': ['sourceRefs', 'lexicalValue'], 'conflicting': ['sourceRefs']}
    for field in required.get(rv['status'], []):
        assert rv.get(field), f'{rv["status"]} value without {field}'


def to_report(data, transform='to-strata-entitlement-report'):
    text = data if isinstance(data, str) else json.dumps(data)
    return json.loads(run_transform(ADAPTER, transform, text))


def csd_with_lot_interests(interests, lot_extra=None):
    lot = {'id': 'lot-1', 'properties': {
        'parcelPurpose': 'wa-parcel-purpose:strata-lot',
        'appellation': {'hasPart': [{'type': 'lotNumber', 'label': '1'}]},
        'interests': interests, **(lot_extra or {})}}
    scheme = {'id': 'scheme', 'topology': {'type': 'ParcelAggregate', 'references': ['lot-1']},
              'properties': {'parcelPurpose': 'wa-parcel-purpose:strata-scheme', 'schemeNumber': 'SP1'}}
    return {'id': 'csd-1', 'parcels': [{'features': [scheme, lot]}]}


def lot_interest(value):
    return {'interestType': 'wa-interest-type:strata-lot', 'entitlementPortion': value}


# --- Provenance resolves ----------------------------------------------------------------------------

@pytest.mark.parametrize('source', [FIXTURE, MISSING], ids=['sp83687', 'missing-entitlement'])
def test_every_value_has_a_status_and_its_provenance_resolves(source):
    csd = json.loads(source.read_text(encoding='utf-8'))
    report = to_report(csd)
    for pointer, rv in report_values(report):
        assert_status_rules(rv)
        for ref in rv.get('sourceRefs', []):
            assert ref['dataset'] == csd['id']
            found = resolve(csd, ref['pointer'])  # every source pointer exists in the source dataset
            if rv['status'] == 'reported':
                assert rv['value'] == (int(found) if isinstance(rv['value'], int) else str(found)), pointer
        if rv['status'] == 'derived':
            inputs = [resolve(report, p) for p in rv['derivation']['inputs']]
            if rv['derivation']['method'] == 'sum':
                assert rv['value'] == sum(i['value'] for i in inputs)
            else:
                assert rv['derivation']['method'] == 'count' and rv['value'] == len(inputs[0])


def test_sp83687_values_are_all_reported_and_totals_derived():
    report = to_report(FIXTURE.read_text(encoding='utf-8'))
    statuses = {pointer: rv['status'] for pointer, rv in report_values(report)}
    assert {s for p, s in statuses.items()
            if not p.startswith('/content/totals') or p.endswith('/declared')} == {'reported'}
    assert statuses['/content/totals/calculated'] == statuses['/content/totals/lotCount'] == 'derived'
    calculated = report['content']['totals']['calculated']
    assert calculated['value'] == 1000 and len(calculated['derivation']['inputs']) == 9
    assert 'note' not in calculated
    # integers in the source need no lexical value
    assert all('lexicalValue' not in lot['entitlement'] for lot in report['content']['lots'])


# --- Missing entitlement (Stage 3 done-when criterion) ----------------------------------------------

def test_missing_entitlement_is_reported_as_not_supplied_not_an_error():
    report = to_report(MISSING.read_text(encoding='utf-8'))
    lot4 = report['content']['lots'][3]
    assert lot4['lotNumber']['value'] == '4'
    assert lot4['entitlement']['status'] == 'not-supplied' and lot4['entitlement']['value'] is None
    assert lot4['entitlement']['sourceRefs'][0]['pointer'].endswith('/properties/interests')
    calculated = report['content']['totals']['calculated']
    assert calculated['value'] == 892
    assert '/content/lots/3/entitlement' not in calculated['derivation']['inputs']
    assert len(calculated['derivation']['inputs']) == 8
    assert calculated['note'] == 'Sum of 8 of 9 lots; 1 lot(s) have no usable entitlement'
    assert report['content']['totals']['lotCount']['value'] == 9


def test_missing_entitlement_html_marks_the_gap():
    html = run_transform(ADAPTER, 'to-strata-entitlement-html', MISSING.read_text(encoding='utf-8'))
    assert table_rows(html)[4] == ('4', 'not supplied')
    assert ('Calculated total (9 lots)', '892') in table_rows(html)
    assert 'Sum of 8 of 9 lots' in html  # the note is in the total's tooltip
    assert 'Not supplied by the source' in html  # legend entry


# --- Status per source situation --------------------------------------------------------------------

@pytest.mark.parametrize('raw, status, value, lexical', [
    (117, 'reported', 117, None),
    ('117', 'reported', 117, '117'),
    (' 42 ', 'reported', 42, ' 42 '),
    ('12.5', 'invalid', None, '12.5'),
    (12.5, 'invalid', None, '12.5'),
    (0, 'invalid', None, '0'),
    (-5, 'invalid', None, '-5'),
    (True, 'invalid', None, 'true'),
    ('abc', 'invalid', None, 'abc'),
])
def test_entitlement_status_and_lexical_value(raw, status, value, lexical):
    entitlement = to_report(csd_with_lot_interests([lot_interest(raw)]))['content']['lots'][0]['entitlement']
    assert (entitlement['status'], entitlement['value'], entitlement.get('lexicalValue')) == (status, value, lexical)
    assert_status_rules(entitlement)


@pytest.mark.parametrize('interests', [[], [{'interestType': 'wa-interest-type:ct'}], [lot_interest(None)]],
                         ids=['no interests', 'other interest only', 'null entitlementPortion'])
def test_absent_entitlement_is_not_supplied(interests):
    entitlement = to_report(csd_with_lot_interests(interests))['content']['lots'][0]['entitlement']
    assert entitlement['status'] == 'not-supplied' and entitlement['value'] is None


def test_disagreeing_interests_are_conflicting_and_agreeing_ones_are_not():
    conflicting = to_report(csd_with_lot_interests([lot_interest(10), lot_interest(12)]))
    entitlement = conflicting['content']['lots'][0]['entitlement']
    assert entitlement['status'] == 'conflicting' and len(entitlement['sourceRefs']) == 2
    assert conflicting['content']['totals']['calculated']['value'] == 0
    agreeing = to_report(csd_with_lot_interests([lot_interest(10), lot_interest(10)]))
    assert agreeing['content']['lots'][0]['entitlement']['status'] == 'reported'


def test_unresolved_member_points_at_the_reference():
    data = csd_with_lot_interests([lot_interest(10)])
    data['parcels'][0]['features'][0]['topology']['references'].append('lot-missing')
    report = to_report(data)
    lot = report['content']['lots'][1]
    assert lot['lotNumber']['status'] == lot['entitlement']['status'] == 'unresolved'
    assert resolve(data, lot['entitlement']['sourceRefs'][0]['pointer']) == 'lot-missing'
    assert report['content']['totals']['lotCount']['value'] == 2


def test_missing_lot_number_and_scheme_number_are_not_supplied():
    data = csd_with_lot_interests([lot_interest(10)])
    data['parcels'][0]['features'][1]['properties']['appellation']['hasPart'] = []
    del data['parcels'][0]['features'][0]['properties']['schemeNumber']
    report = to_report(data)
    assert report['content']['lots'][0]['lotNumber']['status'] == 'not-supplied'
    assert report['content']['scheme']['schemeNumber']['status'] == 'not-supplied'
    for _, rv in report_values(report):
        assert_status_rules(rv)


# --- Facts stage carries statuses, complete adds derived values --------------------------------------

def test_facts_stage_values_have_statuses_and_no_derived_values():
    facts = to_report(FIXTURE.read_text(encoding='utf-8'), 'to-strata-entitlement-facts')
    statuses = {pointer: rv['status'] for pointer, rv in report_values(facts)}
    assert set(statuses.values()) == {'reported'}
    assert not any(p.endswith(('/calculated', '/lotCount')) for p in statuses)


# --- Presentation -----------------------------------------------------------------------------------

def test_html_marks_every_value_with_its_status():
    report = to_report(FIXTURE.read_text(encoding='utf-8'))
    html = run_transform(REPORT, 'to-html', json.dumps(report))
    statuses = list(all_statuses(report['content']))
    legend_entries = len(set(statuses))
    # every value is marked, except the address part labels, which are shown through the formatted address
    address_part_labels = sum(1 for part in report['content']['scheme']['address']['parts'] if 'label' in part)
    assert html.count('<sup class="status status-') == len(statuses) - address_part_labels + legend_entries
    assert html.count('data-status="reported"') == statuses.count('reported') - address_part_labels
    assert html.count('data-status="derived"') == statuses.count('derived') == 3  # two totals and the address
    assert 'source: /parcels/0/features/2/properties/interests/0/entitlementPortion' in html
    assert 'sum of 9 value(s)' in html


def test_status_codelist_covers_the_schema_statuses():
    ttl = STATUS_CODELIST.read_text(encoding='utf-8')
    schema = (REPO_ROOT / '_sources/cadastral-report/schema.yaml').read_text(encoding='utf-8')
    statuses = ['reported', 'derived', 'documented', 'configured', 'not-supplied', 'unresolved',
                'invalid', 'conflicting']
    for status in statuses:
        assert f'skos:notation "{status}"' in ttl
        assert f'- {status}' in schema
