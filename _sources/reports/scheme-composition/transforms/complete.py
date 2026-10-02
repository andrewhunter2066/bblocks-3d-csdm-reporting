# Transform: facts-stage Scheme Composition Report -> complete report.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Adds the derived values (whether each member is spatially resolved, and the scheme's spatial
# representation summary) and the report-level checks, then sets the overall status with the generic
# `summarise-checks` of csdm.reporting.cadastral-report. Knows nothing about the source format.
# Idempotent: completing a complete report returns the same report.
import json

REPORT_TYPE = 'csdm.reporting.reports.scheme-composition'
STEP = {'bblock': REPORT_TYPE, 'transform': 'complete'}
SUMMARISE = ('csdm.reporting.cadastral-report', 'summarise-checks')
SUMMARISE_STEP = {'bblock': SUMMARISE[0], 'transform': SUMMARISE[1]}


def _derived(value, method, inputs):
    return {'value': value, 'status': 'derived', 'derivation': {'method': method, 'inputs': inputs}}


def _check(check_id, severity, passed, message, targets=()):
    check = {'id': check_id, 'definedBy': REPORT_TYPE, 'category': 'domain', 'severity': severity,
             'outcome': 'pass' if passed else 'fail', 'message': message}
    if targets:
        check['targets'] = list(targets)
    return check


report = json.loads(input_data)
if report.get('reportType') != REPORT_TYPE:
    raise ValueError(f'Expected a {REPORT_TYPE} report, got reportType = {report.get("reportType")!r}')
if report.get('stage') not in ('facts', 'complete'):
    raise ValueError(f'Unknown report stage {report.get("stage")!r}')

content = report['content']
members = content.get('members') or []

# --- Derived values -------------------------------------------------------------------------------------
for index, member in enumerate(members):
    components = member.get('components') or []
    member['spatiallyResolved'] = _derived(bool(components) and all(c['found'] for c in components),
                                           'all-components-found', [f'/content/members/{index}/components'])


def _distinct(field):
    values = sorted({m[field]['value'] for m in members if m[field].get('value') is not None})
    return _derived(values, 'distinct-values', [f'/content/members/{i}/{field}' for i in range(len(members))])


content['summary'] = {
    'memberParcelCount': _derived(len(members), 'count', ['/content/members']),
    'geometryTypes': _distinct('geometryType'),
    'memberRepresentationStatuses': _distinct('representationStatus'),
    'allMemberParcelsSpatiallyResolved': _derived(
        bool(members) and all(m['spatiallyResolved']['value'] for m in members), 'all',
        [f'/content/members/{i}/spatiallyResolved' for i in range(len(members))]),
}

# --- Report-level checks ----------------------------------------------------------------------------------
no_status = [i for i, m in enumerate(members) if m['representationStatus'].get('value') is None]
unresolved = [i for i, m in enumerate(members) if not m['spatiallyResolved']['value']]
missing_components = [(i, c['ref'].get('id')) for i, m in enumerate(members)
                      for c in m.get('components') or [] if not c['found']]
checks = [
    _check('members-present', 'error', bool(members),
           f'The scheme has {len(members)} member lot(s)' if members else 'The scheme has no member lots',
           targets=['/content/members']),
    _check('representation-status-present', 'warning', not no_status,
           'Every member has a representation status' if not no_status
           else f'{len(no_status)} of {len(members)} member(s) have no representation status',
           targets=[f'/content/members/{i}/representationStatus' for i in no_status]),
    _check('component-references-resolve', 'warning', not missing_components,
           'Every component a member references is present in the source' if not missing_components
           else f'{len(missing_components)} referenced component(s) are not present in the source',
           targets=sorted({f'/content/members/{i}/components' for i, _ in missing_components})),
    _check('all-members-spatially-resolved', 'warning', not unresolved,
           'Every member is spatially resolved' if not unresolved
           else f'{len(unresolved)} of {len(members)} member(s) are not spatially resolved '
                '(no component solids, or some are missing)',
           targets=[f'/content/members/{i}/spatiallyResolved' for i in unresolved]),
]

report['checks'] = [c for c in report.get('checks') or [] if c.get('definedBy') != REPORT_TYPE] + checks
report['stage'] = 'complete'
report['generatedBy'] = [step for step in report.get('generatedBy') or []
                         if step not in (STEP, SUMMARISE_STEP)] + [STEP]

summarise = get_transformer(*SUMMARISE)
output_data = summarise(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
