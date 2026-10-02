"""Stage 8 tests: the generalisation check, with a second report type (Scheme Composition).

Run from the repository root:  python3 -m pytest tests-py
"""
import copy
import json
import re

import pytest

from harness import REPO_ROOT, run_transform, table_rows

ADAPTER = 'csdm.reporting.adapters.wa-csdm'
COMPOSITION = 'csdm.reporting.reports.scheme-composition'
GENERIC = 'csdm.reporting.cadastral-report'
ADAPTER_DIR = REPO_ROOT / '_sources/adapters/wa-csdm'
EXAMPLES = ADAPTER_DIR / 'examples'
FIXTURE = EXAMPLES / 'sp83687-entitlement.json'
COMPOSITION_DIR = REPO_ROOT / '_sources/reports/scheme-composition'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def composition(csd, transform='to-scheme-composition-report'):
    text = csd if isinstance(csd, str) else json.dumps(csd)
    return json.loads(run_transform(ADAPTER, transform, text))


def outcome(report, check_id):
    return next(c['outcome'] for c in report['checks'] if c['id'] == check_id)


def lot(csd, number):
    return next(f for f in csd['parcels'][0]['features']
                if f['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-lot'
                and f['properties']['appellation']['hasPart'][3]['label'] == number)


@pytest.fixture
def csd():
    return load(FIXTURE)


@pytest.fixture(scope='module')
def sp83687():
    return composition(FIXTURE.read_text(encoding='utf-8'))


# --- The second report works end to end on SP83687 ---------------------------------------------------

def test_composition_summary_for_sp83687(sp83687):
    summary = {k: v['value'] for k, v in sp83687['content']['summary'].items()}
    assert summary == {'memberParcelCount': 9, 'geometryTypes': ['AggregateSolid'],
                       'memberRepresentationStatuses': [], 'allMemberParcelsSpatiallyResolved': False}
    resolved = [m['spatiallyResolved']['value'] for m in sp83687['content']['members']]
    assert resolved == [True, True] + [False] * 7
    found = [(sum(c['found'] for c in m['components']), len(m['components'])) for m in sp83687['content']['members']]
    assert found[:2] == [(4, 4), (5, 5)] and set(found[2:]) == {(0, 0)}


def test_composition_is_incomplete_for_honest_reasons(sp83687):
    assert sp83687['status'] == 'incomplete'
    failing = {c['id'] for c in sp83687['checks'] if c['outcome'] == 'fail' and c['severity'] != 'info'}
    assert failing == {'representation-status-present', 'all-members-spatially-resolved'}
    assert all(m['representationStatus']['status'] == 'not-supplied' for m in sp83687['content']['members'])


def test_composition_reuses_the_generic_envelope_checks_and_status(sp83687):
    assert [s['transform'] for s in sp83687['generatedBy']] == ['to-scheme-composition-facts', 'complete',
                                                                'summarise-checks']
    adapter_checks = [c['id'] for c in sp83687['checks'] if c['definedBy'] == ADAPTER]
    assert adapter_checks == ['scheme-identified', 'membership-parcel-aggregate', 'membership-references-resolve',
                              'membership-back-links', 'membership-unreferenced-claimants',
                              'scheme-number-consistent']


def test_complete_is_idempotent(sp83687):
    assert json.loads(run_transform(COMPOSITION, 'complete', json.dumps(sp83687))) == sp83687


def test_examples_are_the_adapter_output():
    source = FIXTURE.read_text(encoding='utf-8')
    assert composition(source, 'to-scheme-composition-facts') == load(COMPOSITION_DIR / 'examples/sp83687-facts.json')
    assert composition(source) == load(COMPOSITION_DIR / 'examples/sp83687-report.json')


# --- Behaviour on other data -------------------------------------------------------------------------

def test_a_missing_component_solid_is_reported(csd):
    lot(csd, '1')['topology']['references'].append('uuid:not-a-solid')
    report = composition(csd)
    member = report['content']['members'][0]
    assert member['components'][-1] == {'ref': {'dataset': 'SP-83687-1-1-0.00',
                                                'pointer': '/parcels/0/features/2/topology/references/4',
                                                'id': 'uuid:not-a-solid'}, 'found': False}
    assert member['spatiallyResolved']['value'] is False
    assert outcome(report, 'component-references-resolve') == 'fail'


def test_representation_status_is_reported_when_supplied(csd):
    for number in ('1', '2'):
        lot(csd, number)['properties']['spatialRepresentationDefinitions'] = {'representationStatus': 'representation-status:d3d'}
    report = composition(csd)
    assert report['content']['members'][0]['representationStatus']['status'] == 'reported'
    assert report['content']['summary']['memberRepresentationStatuses']['value'] == ['representation-status:d3d']
    assert outcome(report, 'representation-status-present') == 'fail'  # lots 3-9 still have none


def test_every_lot_resolved_and_represented_is_complete(csd):
    solid = next(iter(f['id'] for f in csd['solids'][0]['features']))
    for number in map(str, range(1, 10)):
        feature = lot(csd, number)
        feature['properties']['spatialRepresentationDefinitions'] = {'representationStatus': 'representation-status:d3d'}
        feature['topology']['references'] = feature['topology']['references'] or [solid]
    report = composition(csd)
    assert report['content']['summary']['allMemberParcelsSpatiallyResolved']['value'] is True
    assert report['status'] == 'complete'


def test_no_scheme_stops_both_reports():
    no_scheme = (REPO_ROOT / 'tests-py/fixtures/no-scheme.json').read_text(encoding='utf-8')
    for transform in ('to-scheme-composition-report', 'to-strata-entitlement-report'):
        with pytest.raises(ValueError, match='Expected exactly one strata scheme parcel'):
            run_transform(ADAPTER, transform, no_scheme)


# --- Duplication: shared source interpretation (the section 3 trigger) -------------------------------

def test_both_reports_get_scheme_and_membership_from_resolve_scheme():
    for name in ('strata_entitlement_facts.py', 'scheme_composition_facts.py'):
        code = '\n'.join(line.split('#', 1)[0] for line in
                         (ADAPTER_DIR / 'transforms' / name).read_text(encoding='utf-8').splitlines())
        assert "get_transformer(ADAPTER_BBLOCK, 'resolve-scheme')" in code, name
        # The scheme and membership rules live only in resolve-scheme (comments ignored).
        for rule in ('wa-parcel-purpose:strata-scheme', 'containingPrimaryParcel', 'def _back_links',
                     'def _lot_number', "'membership-back-links'", "'scheme-identified'"):
            assert rule not in code, f'{name} still contains {rule}'


def test_resolve_scheme_returns_members_and_checks_without_report_pointers(csd):
    lot(csd, '2')['topology']['relationships'] = []
    resolution = json.loads(run_transform(ADAPTER, 'resolve-scheme', json.dumps(csd)))
    assert [m['lotNumber']['value'] for m in resolution['members']] == [str(n) for n in range(1, 10)]
    back_links = next(c for c in resolution['checks'] if c['id'] == 'membership-back-links')
    assert back_links['targetMembers'] == [lot(csd, '2')['id']] and 'targets' not in back_links
    # each report turns member ids into pointers to its own content
    entitlement = json.loads(run_transform(ADAPTER, 'to-strata-entitlement-report', json.dumps(csd)))
    composition_report = composition(csd)
    for report, collection in ((entitlement, 'lots'), (composition_report, 'members')):
        check = next(c for c in report['checks'] if c['id'] == 'membership-back-links')
        assert check['targets'] == [f'/content/{collection}/1'] and 'targetMembers' not in check


# --- The one generic change: list and boolean values in render-html -----------------------------------

def test_generic_renderer_shows_lists_and_booleans_readably():
    report = {'reportType': 'example.report', 'stage': 'complete', 'status': 'complete', 'checks': [],
              'subject': {'kind': 'x', 'ref': {'dataset': 'd', 'pointer': '/x'}}, 'sources': [{'id': 'd'}],
              'content': {'a': {'value': ['x', 'y'], 'status': 'derived', 'derivation': {'method': 'm', 'inputs': []}},
                          'b': {'value': [], 'status': 'derived', 'derivation': {'method': 'm', 'inputs': []}},
                          'c': {'value': True, 'status': 'derived', 'derivation': {'method': 'm', 'inputs': []}},
                          'd': {'value': False, 'status': 'derived', 'derivation': {'method': 'm', 'inputs': []}}}}
    template = ('{% extends "base.html" %}{% block body %}{% call dl("v") %}'
                '{{ dt_dd("A", content.a, "a") }}{{ dt_dd("B", content.b, "b") }}{{ dt_dd("C", content.c, "c") }}'
                '{{ dt_dd("D", content.d, "d") }}{% endcall %}{% endblock %}')
    html = run_transform(GENERIC, 'render-html', json.dumps(report), _stack=(('t', 't'),),
                         extra_metadata={'template': template})
    shown = dict(re.findall(r'<dd id="(\w)"><span class="rv" data-status="derived">([^<]*)<sup', html))
    assert shown == {'a': 'x, y', 'b': 'none', 'c': 'yes', 'd': 'no'}


def test_composition_html(sp83687):
    html = run_transform(COMPOSITION, 'to-html', json.dumps(sp83687))
    rows = table_rows(html, 'members')
    assert rows[0] == ('Lot number', 'Geometry type', 'Representation status', 'Components found', 'Spatially resolved')
    assert rows[1] == ('1', 'AggregateSolid', 'not supplied', '4 of 4', 'yes')
    assert rows[3] == ('3', 'AggregateSolid', 'not supplied', '0 of 0', 'no')
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<sup.*?</sup>', '', html, flags=re.S)))
    assert 'Geometry types AggregateSolid' in text and 'Representation statuses none' in text
    assert 'All members spatially resolved no' in text


def test_composition_template_is_template_only():
    code = (COMPOSITION_DIR / 'transforms/to_html.py').read_text(encoding='utf-8')
    assert 'import' not in code and "get_transformer('csdm.reporting.cadastral-report', 'render-html')" in code
