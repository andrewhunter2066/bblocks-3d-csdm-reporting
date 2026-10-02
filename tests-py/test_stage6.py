"""Stage 6 tests: generic presentation (Jinja2 `render-html`), a template-only `to-html`, and CSV.

Run from the repository root:  python3 -m pytest tests-py
"""
import ast
import csv
import io
import json
import re

import pytest

from harness import REPO_ROOT, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
REPORT = 'csdm.reporting.reports.strata-entitlement'
GENERIC = 'csdm.reporting.cadastral-report'
EXAMPLES = REPO_ROOT / '_sources/adapters/wa-csdm/examples'
TO_HTML = REPO_ROOT / '_sources/reports/strata-entitlement/transforms/to_html.py'
ENVELOPE_EXAMPLE = REPO_ROOT / '_sources/cadastral-report/examples.yaml'

LODGED = [('1', '117'), ('2', '108'), ('3', '113'), ('4', '108'), ('5', '108'),
          ('6', '113'), ('7', '108'), ('8', '108'), ('9', '117')]


def report_for(example):
    return run_transform(ADAPTER, 'to-strata-entitlement-report', (EXAMPLES / example).read_text(encoding='utf-8'))


def page_text(html):
    """Visible text of a page, without status markers."""
    html = re.sub(r'<style>.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<sup.*?</sup>', '', html, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def minimal_report(**extra):
    return {'reportType': 'example.parcel-report', 'stage': 'complete', 'status': 'complete', 'checks': [],
            'subject': {'kind': 'parcel', 'label': 'Lot 1 on DP 1', 'ref': {'dataset': 'd', 'pointer': '/p'}},
            'sources': [{'id': 'd', 'kind': 'dataset', 'name': 'DP 1'}], 'content': {}, **extra}


@pytest.fixture(scope='module')
def sp83687_html():
    return run_transform(REPORT, 'to-html', report_for('sp83687-entitlement.json'))


# --- Done-when criterion: the report-specific code is template-only ----------------------------------

def test_to_html_is_a_template_and_a_call_to_the_generic_renderer():
    tree = ast.parse(TO_HTML.read_text(encoding='utf-8'))
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    assigned = [t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets]
    assert assigned == ['TEMPLATE', 'render_html', 'output_data']
    code = TO_HTML.read_text(encoding='utf-8')
    assert "get_transformer('csdm.reporting.cadastral-report', 'render-html')" in code
    assert "extra_metadata={'template': TEMPLATE}" in code


def test_the_standard_library_renderer_is_gone():
    code = TO_HTML.read_text(encoding='utf-8')
    assert 'from html import' not in code and 'def _value' not in code and '<style>' not in code


def test_render_html_declares_its_jinja2_dependency():
    yaml_text = (REPO_ROOT / '_sources/cadastral-report/transforms.yaml').read_text(encoding='utf-8')
    block = yaml_text[yaml_text.index('- id: render-html'):]
    assert 'pip: jinja2>=3.1' in block


# --- The generic renderer ----------------------------------------------------------------------------

def test_generic_renderer_without_a_template_shows_the_envelope():
    report = minimal_report(status='incomplete', statusSummary={'checks': 1, 'failedErrors': 0,
                                                                 'failedWarnings': 1, 'unevaluatedErrors': 0},
                            checks=[{'id': 'area-present', 'definedBy': 'x', 'category': 'domain',
                                     'severity': 'warning', 'outcome': 'fail', 'message': 'No area'}])
    html = run_transform(GENERIC, 'render-html', json.dumps(report))
    assert '<title>Cadastral report: Lot 1 on DP 1</title>' in html
    assert 'class="report-status status-incomplete"' in html
    assert table_rows(html, 'checks')[1] == ('fail', 'warning', 'domain', 'area-present', 'No area')
    assert 'Source: DP 1' in page_text(html)


def test_generic_renderer_renders_another_report_type_from_its_own_template():
    """The reuse the generic block exists for: a different report type needs only a template."""
    report = minimal_report(content={'area': {'value': 1639, 'status': 'reported',
                                              'sourceRefs': [{'dataset': 'd', 'pointer': '/p/area'}]}})
    template = ('{% extends "base.html" %}{% block heading %}Parcel report{% endblock %}'
                '{% block body %}{% call dl("parcel") %}{{ dt_dd("Area (m²)", content.area, "area") }}'
                '{% endcall %}{% endblock %}')
    html = run_transform(GENERIC, 'render-html', json.dumps(report), _stack=(('test', 'caller'),),
                         extra_metadata={'template': template})
    assert '<h1>Parcel report</h1>' in html
    assert '<dd id="area"><span class="rv" data-status="reported">1639<sup' in html
    assert 'source: /p/area' in html and 'Reported from the source' in html  # marker tooltip and legend


def test_generic_renderer_escapes_report_text():
    report = minimal_report(subject={'kind': 'parcel', 'label': '<script>alert(1)</script>',
                                     'ref': {'dataset': 'd', 'pointer': '/p'}})
    html = run_transform(GENERIC, 'render-html', json.dumps(report))
    assert '<script>' not in html and '&lt;script&gt;' in html


def test_generic_renderer_ignores_input_that_is_not_a_report():
    assert run_transform(GENERIC, 'render-html', json.dumps({'value': 1, 'status': 'reported'})) is None


# --- Entitlement report HTML -------------------------------------------------------------------------

def test_sp83687_html_has_every_section(sp83687_html):
    text = page_text(sp83687_html)
    for expected in ('Unit Entitlement Report', 'Report status: complete (18 checks',
                     'Scheme address 281 Belmont Avenue, Cloverdale', 'Effective for use from 2021-07-07',
                     'Licensed valuer number 00000', 'Documents relied on Schedule of Unit Entitlements - SP83687',
                     'Generated by: csdm.reporting.adapters.wa-csdm to-strata-entitlement-facts'):
        assert expected in text, expected
    assert table_rows(sp83687_html)[1:10] == LODGED
    assert table_rows(sp83687_html)[10:] == [('Calculated total (9 lots)', '1000'), ('Declared total', '1000')]
    assert len(table_rows(sp83687_html, 'checks')) == 1 + 18


def test_missing_entitlement_html_shows_the_gap_and_status():
    html = run_transform(ADAPTER, 'to-strata-entitlement-html',
                         (EXAMPLES / 'missing-entitlement.json').read_text(encoding='utf-8'))
    assert 'class="report-status status-incomplete"' in html
    assert table_rows(html)[4] == ('4', 'not supplied')
    assert ('Calculated total (9 lots)', '892') in table_rows(html)
    assert 'Sum of 8 of 9 lots' in html


def test_facts_stage_page_is_marked_not_yet_assessed():
    facts = run_transform(ADAPTER, 'to-strata-entitlement-facts',
                          (EXAMPLES / 'sp83687-entitlement.json').read_text(encoding='utf-8'))
    html = run_transform(REPORT, 'to-html', facts)
    assert 'not yet assessed' in html and 'not calculated (facts-stage report)' in html


# --- CSV ---------------------------------------------------------------------------------------------

def read_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_csv_has_one_row_per_lot_with_statuses():
    rows = read_csv(run_transform(REPORT, 'to-csv', report_for('sp83687-entitlement.json')))
    assert len(rows) == 9
    assert [(r['lot_number'], r['unit_entitlement']) for r in rows] == LODGED
    assert {r['scheme_number'] for r in rows} == {'SP83687'}
    assert {r['unit_entitlement_status'] for r in rows} == {'reported'}
    assert rows[0]['unit_entitlement_source'] == '/parcels/0/features/2/properties/interests/0/entitlementPortion'
    assert rows[0]['parcel_id'] == 'uuid:e62621ed-1334-4890-964f-608ff68f7a17'


def test_csv_keeps_a_missing_entitlement_explicit():
    rows = read_csv(run_transform(REPORT, 'to-csv', report_for('missing-entitlement.json')))
    lot4 = rows[3]
    assert (lot4['lot_number'], lot4['unit_entitlement'], lot4['unit_entitlement_status']) == ('4', '', 'not-supplied')


def test_adapter_csv_composition_equals_report_csv():
    source = (EXAMPLES / 'sp83687-entitlement.json').read_text(encoding='utf-8')
    assert run_transform(ADAPTER, 'to-strata-entitlement-csv', source) == run_transform(
        REPORT, 'to-csv', run_transform(ADAPTER, 'to-strata-entitlement-report', source))
