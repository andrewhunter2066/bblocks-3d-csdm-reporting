"""Stage 2 tests: source extraction (adapter, facts stage) separated from report semantics (complete).

Run from the repository root:  python3 -m pytest tests-py
"""
import json
import re

import pytest

from harness import REPO_ROOT, plain, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
ADAPTER_DIR = REPO_ROOT / '_sources/adapters/wa-csdm'
REPORT_DIR = REPO_ROOT / '_sources/reports/strata-entitlement'
FIXTURE = ADAPTER_DIR / 'examples/sp83687-entitlement.json'
FACTS_EXAMPLE = REPORT_DIR / 'examples/sp83687-facts.json'
COMPLETE_EXAMPLE = REPORT_DIR / 'examples/sp83687-report.json'

FACTS_STEP = {'bblock': ADAPTER, 'transform': 'to-strata-entitlement-facts'}
COMPLETE_STEP = {'bblock': REPORT, 'transform': 'complete'}
SUMMARISE_STEP = {'bblock': 'csdm.reporting.cadastral-report', 'transform': 'summarise-checks'}


def derived(totals):
    """The derived totals only (Stage 4 adds the declared total, a source fact, alongside them)."""
    return {k: v for k, v in totals.items() if k in ('calculated', 'lotCount')}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def complete(report) -> dict:
    return json.loads(run_transform(REPORT, 'complete', json.dumps(report)))


@pytest.fixture(scope='module')
def facts():
    return json.loads(run_transform(ADAPTER, 'to-strata-entitlement-facts', FIXTURE.read_text(encoding='utf-8')))


def reported(value):
    return {'value': value, 'status': 'reported', 'sourceRefs': [{'dataset': 'd', 'pointer': '/x'}]}


def minimal_facts(*entitlements):
    """A facts-stage report built by hand: `complete` must not need any source data."""
    return {
        'reportType': REPORT, 'stage': 'facts', 'generatedBy': [{'bblock': 'other.adapter', 'transform': 'x'}],
        'subject': {'kind': 'strata-scheme', 'ref': {'dataset': 'd', 'pointer': '/s'}},
        'sources': [{'id': 'd'}],
        'content': {'scheme': {'schemeNumber': reported('SP1')},
                    'lots': [{'lotNumber': reported(str(i + 1)),
                              'entitlement': reported(e) if e is not None else {'value': None, 'status': 'not-supplied'}}
                             for i, e in enumerate(entitlements)]},
    }


# --- Adapter: facts only ----------------------------------------------------------------------------

def test_adapter_emits_facts_stage_without_derived_values(facts):
    assert facts['stage'] == 'facts'
    assert not derived(facts['content'].get('totals', {}))
    assert 'status' not in facts
    assert facts['generatedBy'] == [FACTS_STEP]
    assert len(facts['content']['lots']) == 9


def test_adapter_contains_no_calculation_code():
    code = (ADAPTER_DIR / 'transforms/strata_entitlement_facts.py').read_text(encoding='utf-8')
    code_only = '\n'.join(line.split('#', 1)[0] for line in code.splitlines())
    assert not re.search(r'\bsum\(|calculated|lotCount', code_only)


def test_facts_example_is_the_adapter_output(facts):
    assert facts == load(FACTS_EXAMPLE)


# --- Report block: complete -------------------------------------------------------------------------

def test_complete_adds_derived_values_and_records_the_step(facts):
    report = complete(facts)
    assert report['stage'] == 'complete'
    assert plain(derived(report['content']['totals'])) == {'calculated': 1000, 'lotCount': 9}
    assert report['generatedBy'] == [FACTS_STEP, COMPLETE_STEP, SUMMARISE_STEP]
    assert report['content']['lots'] == facts['content']['lots']  # facts are not altered


def test_complete_of_facts_example_is_the_complete_example():
    assert complete(load(FACTS_EXAMPLE)) == load(COMPLETE_EXAMPLE)


def test_complete_is_idempotent():
    report = load(COMPLETE_EXAMPLE)
    assert complete(report) == report


def test_complete_is_source_independent():
    report = complete(minimal_facts(10, None, 5))
    assert plain(derived(report['content']['totals'])) == {'calculated': 15, 'lotCount': 3}
    assert report['generatedBy'][-2:] == [COMPLETE_STEP, SUMMARISE_STEP]


@pytest.mark.parametrize('field, value, message', [
    ('reportType', 'csdm.reporting.reports.other', 'Expected a'),
    ('stage', 'draft', 'Unknown report stage'),
])
def test_complete_rejects_other_reports(field, value, message):
    report = minimal_facts(1)
    report[field] = value
    with pytest.raises(ValueError, match=message):
        complete(report)


# --- Composition ------------------------------------------------------------------------------------

def test_report_transform_is_facts_then_complete(facts):
    composed = json.loads(run_transform(ADAPTER, 'to-strata-entitlement-report', FIXTURE.read_text(encoding='utf-8')))
    assert composed == complete(facts)


def test_complete_report_equals_stage1_output_apart_from_stage_and_pipeline():
    """Stage 2 criterion, still true in Stage 3 once ReportValues are reduced to their values."""
    report = load(COMPLETE_EXAMPLE)
    stage1 = plain({k: v for k, v in report.items()
                    if k not in ('stage', 'generatedBy', 'checks', 'status', 'statusSummary',
                                 'documents', 'annotations')})
    stage1['sources'] = [{k: v for k, v in stage1['sources'][0].items() if k != 'kind'}]  # Stage 5 additions
    stage1['content'].pop('basis'), stage1['content'].pop('legislativeBasis')  # Stage 5 additions
    stage1['content']['scheme'].pop('schemeName'), stage1['content']['scheme'].pop('address')
    stage1['content']['totals'].pop('declared')  # Stage 4 addition (a source fact)
    for lot in stage1['content']['lots']:
        lot.pop('membershipEvidence')  # Stage 4 addition
    stage1_expected = {
        'reportType': REPORT,
        'subject': report['subject'], 'sources': stage1['sources'],
        'content': {'scheme': {'schemeNumber': 'SP83687', 'ref': report['content']['scheme']['ref']},
                    'lots': stage1['content']['lots'],
                    'totals': {'calculated': 1000, 'lotCount': 9}},
    }
    assert stage1 == stage1_expected


# --- Presentation of either stage -------------------------------------------------------------------

def test_html_of_facts_stage_says_total_not_calculated(facts):
    html = run_transform(REPORT, 'to-html', json.dumps(facts))
    assert 'not calculated (facts-stage report)' in html
    rows = table_rows(html)
    assert len(rows) == 1 + 9 + 2  # header, nine lots, calculated and declared totals
    assert rows[-1] == ('Declared total', '1000')  # a source fact, so shown at the facts stage too
    assert 'not yet assessed' in html


def test_html_of_complete_stage_shows_total(facts):
    html = run_transform(REPORT, 'to-html', json.dumps(complete(facts)))
    assert ('Calculated total (9 lots)', '1000') in table_rows(html)
    assert 'not calculated' not in html
