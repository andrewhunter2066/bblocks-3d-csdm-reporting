"""Stage 4 tests: check results in the report and the overall report status.

Run from the repository root:  python3 -m pytest tests-py
"""
import copy
import json

import pytest

from harness import REPO_ROOT, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
GENERIC = 'csdm.reporting.cadastral-report'
EXAMPLES = REPO_ROOT / '_sources/adapters/wa-csdm/examples'
FIXTURE = EXAMPLES / 'sp83687-entitlement.json'
NO_SCHEME = REPO_ROOT / 'tests-py/fixtures/no-scheme.json'

# The check table of the investigation (section 6), with the outcome expected for SP83687, as of Stage 5:
# the document and certification checks are now evaluated, and scheme-number-consistent was added.
SECTION_6 = {
    # id: (defined by, category, severity, outcome on SP83687)
    'scheme-identified': (ADAPTER, 'generation', 'error', 'pass'),
    'membership-parcel-aggregate': (ADAPTER, 'domain', 'error', 'pass'),
    'membership-references-resolve': (ADAPTER, 'domain', 'error', 'pass'),
    'membership-back-links': (ADAPTER, 'domain', 'warning', 'pass'),
    'membership-unreferenced-claimants': (ADAPTER, 'domain', 'warning', 'pass'),
    'entitlement-source-datatype': (ADAPTER, 'source-conformance', 'info', 'fail'),
    'lot-numbers-present': (REPORT, 'domain', 'warning', 'pass'),
    'lot-numbers-unique': (REPORT, 'domain', 'error', 'pass'),
    'entitlements-present': (REPORT, 'domain', 'warning', 'pass'),
    'entitlements-valid': (REPORT, 'domain', 'error', 'pass'),
    'total-covers-all-lots': (REPORT, 'domain', 'warning', 'pass'),
    'declared-total-present': (REPORT, 'domain', 'warning', 'pass'),
    'total-matches-declared': (REPORT, 'domain', 'error', 'pass'),
    'scheme-number-consistent': (ADAPTER, 'domain', 'warning', 'pass'),
    'schedule-document-referenced': (REPORT, 'domain', 'warning', 'pass'),
    'document-hrefs-resolvable': (REPORT, 'generation', 'info', 'not-evaluated'),
    'valuer-certification-present': (REPORT, 'domain', 'warning', 'pass'),
    'certification-linked-to-schedule': (REPORT, 'domain', 'info', 'pass'),
}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def to_report(csd, transform='to-strata-entitlement-report'):
    text = csd if isinstance(csd, str) else json.dumps(csd)
    return json.loads(run_transform(ADAPTER, transform, text))


def checks_by_id(report):
    return {c['id']: c for c in report['checks']}


def outcome(report, check_id):
    return checks_by_id(report)[check_id]['outcome']


def resolve(document, pointer):
    target = document
    for token in pointer.split('/')[1:]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    return target


def features(csd):
    return csd['parcels'][0]['features']


def scheme_of(csd):
    return next(f for f in features(csd) if f['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-scheme')


def lot_of(csd, number):
    return next(f for f in features(csd)
                if f['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-lot'
                and f['properties']['appellation']['hasPart'][3]['label'] == number)


@pytest.fixture
def csd():
    return load(FIXTURE)


@pytest.fixture(scope='module')
def sp83687():
    return to_report(FIXTURE.read_text(encoding='utf-8'))


# --- Stage 4 done-when criterion: every row of the check table, with its stated outcome ----------------

def test_every_section_6_check_is_in_the_report_with_its_outcome(sp83687):
    found = {c['id']: (c['definedBy'], c['category'], c['severity'], c['outcome']) for c in sp83687['checks']}
    assert found == SECTION_6
    assert len(sp83687['checks']) == len(SECTION_6)  # no duplicates


def test_sp83687_status_is_complete(sp83687):
    assert sp83687['status'] == 'complete'
    assert sp83687['statusSummary'] == {'checks': 18, 'failedErrors': 0, 'failedWarnings': 0,
                                        'unevaluatedErrors': 0}


def test_check_targets_point_at_report_values(sp83687):
    for check in sp83687['checks']:
        for target in check.get('targets', []):
            resolve(sp83687, target)  # raises if the target does not exist


def test_facts_stage_carries_only_the_adapter_checks_and_no_status():
    facts = to_report(FIXTURE.read_text(encoding='utf-8'), 'to-strata-entitlement-facts')
    assert {c['definedBy'] for c in facts['checks']} == {ADAPTER}
    assert 'status' not in facts and 'statusSummary' not in facts
    assert facts['content']['totals'] == {'declared': {
        'value': 1000, 'status': 'reported',
        'sourceRefs': [{'dataset': 'SP-83687-1-1-0.00',
                        'pointer': '/parcels/0/features/1/properties/interests/0/entitlementTotal'}]}}


def test_membership_evidence_records_all_three_links(sp83687):
    assert {tuple(lot['membershipEvidence']) for lot in sp83687['content']['lots']} == {
        ('references', 'containingPrimaryParcel', 'schemeRef')}


def test_complete_is_idempotent_and_does_not_duplicate_checks(sp83687):
    again = json.loads(run_transform(REPORT, 'complete', json.dumps(sp83687)))
    assert again == sp83687


# --- The planned Stage 4 example outcomes -------------------------------------------------------------

def test_total_mismatch_is_invalid():
    report = to_report((EXAMPLES / 'total-mismatch.json').read_text(encoding='utf-8'))
    check = checks_by_id(report)['total-matches-declared']
    assert (check['outcome'], check['severity']) == ('fail', 'error')
    assert check['evidence'] == {'calculated': 1000, 'declared': 1100}
    assert report['status'] == 'invalid'


def test_missing_entitlement_is_incomplete_not_invalid():
    report = to_report((EXAMPLES / 'missing-entitlement.json').read_text(encoding='utf-8'))
    assert outcome(report, 'entitlements-present') == 'fail'
    assert checks_by_id(report)['entitlements-present']['targets'] == ['/content/lots/3/entitlement']
    assert outcome(report, 'total-covers-all-lots') == 'fail'
    assert outcome(report, 'total-matches-declared') == 'not-evaluated'  # a partial sum is not compared
    assert outcome(report, 'entitlements-valid') == 'pass'
    assert report['status'] == 'incomplete'


def test_no_scheme_is_a_generation_error():
    with pytest.raises(ValueError, match='Expected exactly one strata scheme parcel .* found 0'):
        to_report(NO_SCHEME.read_text(encoding='utf-8'))


def test_two_schemes_is_a_generation_error(csd):
    second = copy.deepcopy(scheme_of(csd))
    second['id'] = 'uuid:second-scheme'
    features(csd).append(second)
    with pytest.raises(ValueError, match='found 2'):
        to_report(csd)


# --- Membership checks (D4) ---------------------------------------------------------------------------

def test_reference_to_a_non_lot_parcel_fails_resolution(csd):
    former_tenure = features(csd)[0]
    scheme_of(csd)['topology']['references'].append(former_tenure['id'])
    report = to_report(csd)
    check = checks_by_id(report)['membership-references-resolve']
    assert check['outcome'] == 'fail' and check['evidence'] == {'unresolved': [former_tenure['id']]}
    assert report['status'] == 'invalid'


def test_unresolvable_reference_fails_resolution(csd):
    scheme_of(csd)['topology']['references'].append('uuid:not-in-dataset')
    report = to_report(csd)
    assert outcome(report, 'membership-references-resolve') == 'fail'
    assert report['content']['lots'][-1]['membershipEvidence'] == ['references']


def test_lot_claiming_the_scheme_without_being_referenced_is_reported_not_added(csd):
    lot9 = lot_of(csd, '9')
    scheme_of(csd)['topology']['references'].remove(lot9['id'])
    report = to_report(csd)
    check = checks_by_id(report)['membership-unreferenced-claimants']
    assert check['outcome'] == 'fail' and check['evidence']['lots'][0]['id'] == lot9['id']
    assert len(report['content']['lots']) == 8
    # Lot 9's entitlement is no longer counted, so the total also differs from the declared 1000.
    assert outcome(report, 'total-matches-declared') == 'fail'
    assert report['status'] == 'invalid'


def test_inconsistent_back_links_are_a_warning(csd):
    lot2 = lot_of(csd, '2')
    lot2['properties']['schemeRef'] = 'uuid:some-other-scheme'
    lot2['topology']['relationships'] = []
    report = to_report(csd)
    check = checks_by_id(report)['membership-back-links']
    assert (check['outcome'], check['severity']) == ('fail', 'warning')
    assert check['evidence']['lots'][0]['problems'] == ['containingPrimaryParcel missing or not the scheme',
                                                        'schemeRef is not the scheme']
    lot = next(l for l in report['content']['lots'] if l['ref']['id'] == lot2['id'])
    assert lot['membershipEvidence'] == ['references']
    assert report['status'] == 'incomplete'


def test_missing_schemeref_is_acceptable(csd):
    for feature in features(csd):
        feature['properties'].pop('schemeRef', None)
    report = to_report(csd)
    assert outcome(report, 'membership-back-links') == 'pass'
    assert report['status'] == 'complete'


def test_scheme_without_parcelaggregate_topology_still_produces_an_invalid_report(csd):
    scheme_of(csd)['topology']['type'] = 'Ring'
    report = to_report(csd)
    assert report['content']['lots'] == []  # no authoritative member list, so no members (D4)
    assert outcome(report, 'membership-parcel-aggregate') == 'fail'
    # the nine lots still link to the scheme, so they are reported as unreferenced claimants
    assert len(checks_by_id(report)['membership-unreferenced-claimants']['evidence']['lots']) == 9
    assert report['status'] == 'invalid'
    html = run_transform(REPORT, 'to-html', json.dumps(report))
    assert ('Calculated total (0 lots)', '0') in table_rows(html)


# --- Report-level checks ------------------------------------------------------------------------------

def test_duplicate_lot_numbers_are_invalid(csd):
    lot_of(csd, '2')['properties']['appellation']['hasPart'][3]['label'] = '1'
    report = to_report(csd)
    assert checks_by_id(report)['lot-numbers-unique']['evidence'] == {'duplicates': ['1']}
    assert report['status'] == 'invalid'


def test_invalid_entitlement_is_invalid(csd):
    lot_of(csd, '5')['properties']['interests'][0]['entitlementPortion'] = '12.5'
    report = to_report(csd)
    assert outcome(report, 'entitlements-valid') == 'fail'
    assert outcome(report, 'entitlements-present') == 'pass'
    assert report['status'] == 'invalid'


def test_missing_declared_total_is_incomplete(csd):
    scheme_of(csd)['properties']['interests'] = []
    report = to_report(csd)
    assert report['content']['totals']['declared']['status'] == 'not-supplied'
    assert outcome(report, 'declared-total-present') == 'fail'
    assert outcome(report, 'total-matches-declared') == 'not-evaluated'
    assert report['status'] == 'incomplete'


def test_string_entitlements_pass_the_source_datatype_check(csd):
    for number in map(str, range(1, 10)):
        interest = lot_of(csd, number)['properties']['interests'][0]
        interest['entitlementPortion'] = str(interest['entitlementPortion'])
    report = to_report(csd)
    assert outcome(report, 'entitlement-source-datatype') == 'pass'
    assert report['content']['totals']['calculated']['value'] == 1000


# --- Generic status roll-up (summarise-checks) --------------------------------------------------------

def summarise(checks, report_type='any.report-type'):
    report = {'reportType': report_type, 'stage': 'complete', 'subject': {}, 'sources': [], 'content': {},
              'checks': [{'id': f'c{i}', 'definedBy': 'x', 'category': 'domain', 'severity': s, 'outcome': o,
                          'message': 'm'} for i, (s, o) in enumerate(checks)]}
    return json.loads(run_transform(GENERIC, 'summarise-checks', json.dumps(report)))


@pytest.mark.parametrize('checks, status', [
    ([], 'complete'),
    ([('error', 'pass'), ('warning', 'pass'), ('info', 'fail')], 'complete'),
    ([('warning', 'not-evaluated'), ('info', 'not-evaluated')], 'complete'),
    ([('warning', 'fail')], 'incomplete'),
    ([('error', 'not-evaluated')], 'incomplete'),
    ([('error', 'not-applicable')], 'complete'),
    ([('error', 'fail'), ('warning', 'fail')], 'invalid'),
])
def test_status_rules(checks, status):
    assert summarise(checks)['status'] == status


def test_summarise_is_generic_and_records_its_counts():
    report = summarise([('error', 'fail'), ('warning', 'fail'), ('error', 'not-evaluated')], 'other.report')
    assert report['statusSummary'] == {'checks': 3, 'failedErrors': 1, 'failedWarnings': 1, 'unevaluatedErrors': 1}
    assert report['generatedBy'] == [{'bblock': GENERIC, 'transform': 'summarise-checks'}]


def test_summarise_produces_no_output_for_a_facts_stage_report():
    report = {'reportType': 'x', 'stage': 'facts', 'subject': {}, 'sources': [], 'content': {}, 'checks': []}
    assert run_transform(GENERIC, 'summarise-checks', json.dumps(report)) is None


def test_summarise_produces_no_output_for_a_non_report():
    assert run_transform(GENERIC, 'summarise-checks', json.dumps({'value': 1, 'status': 'reported'})) is None


# --- Presentation -------------------------------------------------------------------------------------

def test_html_shows_status_and_every_check(sp83687):
    html = run_transform(REPORT, 'to-html', json.dumps(sp83687))
    assert 'Report status: <strong>complete</strong>' in html
    rows = table_rows(html, 'checks')
    assert rows[0] == ('Outcome', 'Severity', 'Category', 'Check', 'Message')
    assert {row[3] for row in rows[1:]} == set(SECTION_6)


def test_html_shows_an_invalid_report_and_why():
    html = run_transform(ADAPTER, 'to-strata-entitlement-html',
                         (EXAMPLES / 'total-mismatch.json').read_text(encoding='utf-8'))
    assert 'class="report-status status-invalid"' in html
    assert ('Declared total', '1100') in table_rows(html)
    assert ('fail', 'error', 'domain', 'total-matches-declared',
            'Calculated total 1000 differs from the declared total 1100') in table_rows(html, 'checks')
