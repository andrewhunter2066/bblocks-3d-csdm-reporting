"""Stage 1 tests: CSDM -> Strata Scheme Entitlement Report -> HTML.

Run from the repository root:  python3 -m pytest tests-py
"""
import json
import re

import pytest

from harness import REPO_ROOT, plain, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
FIXTURE = REPO_ROOT / '_sources/adapters/wa-csdm/examples/sp83687-entitlement.json'
EXPECTED_REPORT = REPO_ROOT / '_sources/reports/strata-entitlement/examples/sp83687-report.json'

# Values printed on the lodged Schedule of Unit Entitlements for SP83687 (the requirements source, see docs/).
LODGED_SCHEDULE = {'1': 117, '2': 108, '3': 113, '4': 108, '5': 108,
                   '6': 113, '7': 108, '8': 108, '9': 117}


def derived(totals):
    """The derived totals only (Stage 4 adds the declared total alongside them)."""
    return {k: v for k, v in totals.items() if k in ('calculated', 'lotCount')}


def to_report(csd) -> dict:
    """The complete report with every ReportValue flattened to its value (Stage 3 adds statuses)."""
    data = csd if isinstance(csd, str) else json.dumps(csd)
    return plain(json.loads(run_transform(ADAPTER, 'to-strata-entitlement-report', data)))


def lot(lot_id, number, entitlement=None, purpose='wa-parcel-purpose:strata-lot', **props):
    interests = [] if entitlement is None else [
        {'interestLink': f'x:{lot_id}', 'interestType': 'wa-interest-type:strata-lot',
         'entitlementPortion': entitlement}]
    appellation = {'label': f'Lot {number}', 'hasPart': [{'type': 'lotNumber', 'label': number}]}
    return {'id': lot_id, 'type': 'Feature', 'properties': {
        'appellation': appellation, 'parcelPurpose': purpose, 'interests': interests, **props}}


def csd(*features, members=None, extra_schemes=0):
    scheme = {'id': 'scheme', 'type': 'Feature',
              'topology': {'type': 'ParcelAggregate',
                           'references': members if members is not None else [f['id'] for f in features]},
              'properties': {'parcelPurpose': 'wa-parcel-purpose:strata-scheme', 'schemeNumber': 'SP1',
                             'appellation': {'label': 'Lots on Plan SP 1'}}}
    others = [{**scheme, 'id': f'scheme-{i}'} for i in range(extra_schemes)]
    return {'id': 'csd-1', 'name': 'SP1', 'time': {'date': '2026-01-01'},
            'parcels': [{'type': 'FeatureCollection', 'features': [scheme, *others, *features]}]}


# --- SP83687 vertical slice -------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sp83687():
    return to_report(FIXTURE.read_text(encoding='utf-8'))


def test_sp83687_matches_lodged_schedule(sp83687):
    content = sp83687['content']
    assert content['scheme']['schemeNumber'] == 'SP83687'
    assert {l['lotNumber']: l['entitlement'] for l in content['lots']} == LODGED_SCHEDULE
    assert [l['lotNumber'] for l in content['lots']] == [str(n) for n in range(1, 10)]
    assert derived(content['totals']) == {'calculated': 1000, 'lotCount': 9}
    assert content['totals']['declared'] == 1000


def test_sp83687_matches_expected_report_example(sp83687):
    assert sp83687 == plain(json.loads(EXPECTED_REPORT.read_text(encoding='utf-8')))


def test_sp83687_references_point_back_into_the_source(sp83687):
    source = json.loads(FIXTURE.read_text(encoding='utf-8'))
    for entry in sp83687['content']['lots']:
        _, parcels, collection, features, index = entry['ref']['pointer'].split('/')
        feature = source[parcels][int(collection)][features][int(index)]
        assert feature['id'] == entry['ref']['id']
    assert sp83687['subject']['ref']['id'] == 'uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e'
    assert sp83687['sources'][0] == {'id': 'SP-83687-1-1-0.00', 'kind': 'dataset', 'name': 'SP83687',
                                     'date': '2023-02-06', 'conformsTo': 'icsm.profiles.wa.wa-3d'}


def test_sp83687_html_via_composition(sp83687):
    html = run_transform(ADAPTER, 'to-strata-entitlement-html', FIXTURE.read_text(encoding='utf-8'))
    assert html == run_transform(REPORT, 'to-html', EXPECTED_REPORT.read_text(encoding='utf-8'))
    assert re.search(r'<span id="scheme-number">.*?>SP83687<sup', html)
    rows = table_rows(html)
    assert rows[0] == ('Lot number', 'Unit entitlement')
    assert rows[1:10] == [(n, str(e)) for n, e in LODGED_SCHEDULE.items()]
    assert rows[10] == ('Calculated total (9 lots)', '1000')
    assert rows[11] == ('Declared total', '1000')


# --- Membership (D4) and scheme identification (D5) -------------------------------------------------

def test_members_are_the_parcelaggregate_references_only():
    report = to_report(csd(lot('a', '1', 10), lot('b', '2', 20), lot('c', '3', 30, schemeRef='scheme'),
                           members=['a', 'b']))
    assert [l['lotNumber'] for l in report['content']['lots']] == ['1', '2']
    assert derived(report['content']['totals']) == {'calculated': 30, 'lotCount': 2}


def test_unresolved_reference_is_kept_not_dropped():
    report = to_report(csd(lot('a', '1', 10), members=['a', 'missing']))
    lots = report['content']['lots']
    assert len(lots) == 2 and [(l['lotNumber'], l['entitlement']) for l in lots] == [('1', 10), (None, None)]
    assert derived(report['content']['totals']) == {'calculated': 10, 'lotCount': 2}


@pytest.mark.parametrize('extra_schemes', [None, 1])
def test_zero_or_several_schemes_is_a_generation_error(extra_schemes):
    data = csd(lot('a', '1', 10), extra_schemes=extra_schemes or 0)
    if extra_schemes is None:
        data['parcels'][0]['features'] = [f for f in data['parcels'][0]['features'] if f['id'] != 'scheme']
    with pytest.raises(ValueError, match='exactly one strata scheme'):
        to_report(data)


# --- Entitlement extraction (D7) --------------------------------------------------------------------

@pytest.mark.parametrize('raw, expected', [
    (117, 117), ('117', 117), (' 42 ', 42),
    (0, None), (-5, None), ('12.5', None), (12.5, None), (True, None), ('abc', None), (None, None),
])
def test_entitlement_coercion(raw, expected):
    feature = lot('a', '1')
    feature['properties']['interests'] = [{'interestType': 'wa-interest-type:strata-lot',
                                           'entitlementPortion': raw}]
    assert to_report(csd(feature))['content']['lots'][0]['entitlement'] == expected


def test_missing_entitlement_is_null_and_left_out_of_the_total():
    report = to_report(csd(lot('a', '1', 10), lot('b', '2')))
    assert report['content']['lots'][1]['entitlement'] is None
    assert derived(report['content']['totals']) == {'calculated': 10, 'lotCount': 2}


def test_lots_are_sorted_numerically():
    report = to_report(csd(lot('a', '10', 1), lot('b', '9', 1), lot('c', '2', 1)))
    assert [l['lotNumber'] for l in report['content']['lots']] == ['2', '9', '10']


# --- HTML presentation ------------------------------------------------------------------------------

def test_html_escapes_values_and_marks_missing_data():
    data = csd(lot('a', '<1>', 10), lot('b', '2'))
    data['parcels'][0]['features'][0]['properties']['schemeNumber'] = 'SP<&>'
    html = run_transform(ADAPTER, 'to-strata-entitlement-html', json.dumps(data))
    assert 'SP&lt;&amp;&gt;' in html and '<1>' not in html and '&lt;1&gt;' in html
    assert '<span class="missing">not supplied</span>' in html
    assert '<sup class="status status-not-supplied"' in html
