# Transform: facts-stage Strata Scheme Entitlement Report -> complete report.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Adds the derived values (calculated total, lot count) and the report-level checks (lots, entitlements,
# totals, and the schedule document and certification it rests on) to the source facts
# produced by any source adapter, then sets the overall report status with the generic `summarise-checks`
# transform of csdm.reporting.cadastral-report. Knows nothing about the source format. Each derived value
# is a ReportValue with status `derived` whose derivation lists the report values it was calculated from.
# Idempotent: completing an already complete report recalculates it and returns the same report.
import json

REPORT_TYPE = 'csdm.reporting.reports.strata-entitlement'
STEP = {'bblock': REPORT_TYPE, 'transform': 'complete'}
SUMMARISE = ('csdm.reporting.cadastral-report', 'summarise-checks')
SUMMARISE_STEP = {'bblock': SUMMARISE[0], 'transform': SUMMARISE[1]}
MISSING = ('not-supplied', 'unresolved')
UNUSABLE = ('invalid', 'conflicting')


def _check(check_id, severity, outcome, message, targets=(), evidence=None, category='domain'):
    check = {'id': check_id, 'definedBy': REPORT_TYPE, 'category': category, 'severity': severity,
             'outcome': outcome, 'message': message}
    if targets:
        check['targets'] = list(targets)
    if evidence:
        check['evidence'] = evidence
    return check


def _passed(ok):
    return 'pass' if ok else 'fail'


report = json.loads(input_data)
if report.get('reportType') != REPORT_TYPE:
    raise ValueError(f'Expected a {REPORT_TYPE} report, got reportType = {report.get("reportType")!r}')
if report.get('stage') not in ('facts', 'complete'):
    raise ValueError(f'Unknown report stage {report.get("stage")!r}')

content = report['content']
lots = content.get('lots') or []
totals = content.get('totals') or {}

# --- Derived values -------------------------------------------------------------------------------------
summed = [(index, lot['entitlement']['value']) for index, lot in enumerate(lots)
          if (lot.get('entitlement') or {}).get('value') is not None]
calculated = {
    'value': sum(value for _, value in summed),
    'status': 'derived',
    'derivation': {
        'method': 'sum',
        'inputs': [f'/content/lots/{index}/entitlement' for index, _ in summed],
    },
}
if len(summed) < len(lots):
    calculated['note'] = (f'Sum of {len(summed)} of {len(lots)} lots; '
                          f'{len(lots) - len(summed)} lot(s) have no usable entitlement')
content['totals'] = {
    **({'declared': totals['declared']} if 'declared' in totals else {}),
    'calculated': calculated,
    'lotCount': {
        'value': len(lots),
        'status': 'derived',
        'derivation': {'method': 'count', 'inputs': ['/content/lots']},
    },
}

# --- Report-level checks ----------------------------------------------------------------------------------
checks = []

no_number = [i for i, lot in enumerate(lots) if lot['lotNumber'].get('value') is None]
checks.append(_check(
    'lot-numbers-present', 'warning', _passed(not no_number),
    'Every lot has a lot number' if not no_number else f'{len(no_number)} lot(s) have no lot number',
    targets=[f'/content/lots/{i}/lotNumber' for i in no_number]))

numbers = [lot['lotNumber']['value'] for lot in lots if lot['lotNumber'].get('value') is not None]
duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
checks.append(_check(
    'lot-numbers-unique', 'error', _passed(not duplicates),
    'Lot numbers are unique' if not duplicates else f'Duplicate lot numbers: {", ".join(duplicates)}',
    targets=[f'/content/lots/{i}/lotNumber' for i, lot in enumerate(lots)
             if lot['lotNumber'].get('value') in duplicates],
    evidence={'duplicates': duplicates} if duplicates else None))

missing = [i for i, lot in enumerate(lots) if lot['entitlement']['status'] in MISSING]
checks.append(_check(
    'entitlements-present', 'warning', _passed(not missing),
    f'All {len(lots)} lots have a unit entitlement' if not missing
    else f'{len(missing)} of {len(lots)} lots have no unit entitlement',
    targets=[f'/content/lots/{i}/entitlement' for i in missing]))

unusable = [i for i, lot in enumerate(lots) if lot['entitlement']['status'] in UNUSABLE]
checks.append(_check(
    'entitlements-valid', 'error', _passed(not unusable),
    'Every supplied unit entitlement is a single positive whole number' if not unusable
    else f'{len(unusable)} lot(s) have an invalid or conflicting unit entitlement',
    targets=[f'/content/lots/{i}/entitlement' for i in unusable]))

covers_all = len(summed) == len(lots)
checks.append(_check(
    'total-covers-all-lots', 'warning', _passed(covers_all),
    f'The calculated total includes all {len(lots)} lots' if covers_all else calculated['note'],
    targets=['/content/totals/calculated']))

declared = totals.get('declared') or {}
declared_value = declared.get('value')
checks.append(_check(
    'declared-total-present', 'warning', _passed(declared_value is not None),
    f'The source declares a total of {declared_value}' if declared_value is not None
    else f'The source declares no usable total ({declared.get("status", "not-supplied")})',
    targets=['/content/totals/declared'] if declared else []))

if declared_value is None:
    outcome, message = 'not-evaluated', 'No declared total to compare with'
elif not covers_all:
    outcome, message = 'not-evaluated', 'The calculated total does not include every lot, so it cannot be compared'
else:
    outcome = _passed(calculated['value'] == declared_value)
    message = (f'Calculated total {calculated["value"]} equals the declared total {declared_value}'
               if outcome == 'pass'
               else f'Calculated total {calculated["value"]} differs from the declared total {declared_value}')
checks.append(_check(
    'total-matches-declared', 'error', outcome, message,
    targets=['/content/totals/calculated', '/content/totals/declared'],
    evidence={'calculated': calculated['value'], 'declared': declared_value}))

# --- Basis of the schedule: document and certification ------------------------------------------------
documents = {d['id']: d for d in report.get('documents') or []}
annotations = {a['id']: a for a in report.get('annotations') or []}
basis = content.get('basis') or {}
schedule_ref = (basis.get('schedule') or {}).get('documentRef')
schedule = documents.get(schedule_ref)
checks.append(_check(
    'schedule-document-referenced', 'warning', _passed(schedule is not None),
    f'The schedule of unit entitlements is referenced: {schedule.get("title") or schedule["href"]}'
    if schedule else 'No schedule of unit entitlements is referenced',
    targets=['/content/basis/schedule'] if 'schedule' in basis else []))

checks.append(_check(
    'document-hrefs-resolvable', 'info', 'not-evaluated',
    'Not evaluated: document links are not resolved while the report is generated, and relative links '
    'have no defined base (D12)',
    evidence={'hrefs': [d['href'] for d in documents.values()]} if documents else None, category='generation'))

certification = basis.get('certification') or {}
annotation = annotations.get(certification.get('annotationRef'))
certifier = certification.get('certifier') or {}
named = all((certifier.get(k) or {}).get('value') for k in ('lastName', 'licensedValuerNumber'))
dated = (certification.get('dateCertified') or {}).get('value') is not None
if annotation is None:
    outcome, message = 'fail', 'No licensed valuer certification is recorded'
elif not (named and dated):
    outcome = 'fail'
    message = 'The licensed valuer certification does not name the valuer, licence number and date'
else:
    outcome = 'pass'
    message = (f'Certified by licensed valuer {certifier.get("firstName", {}).get("value") or ""} '
               f'{certifier["lastName"]["value"]} (No. {certifier["licensedValuerNumber"]["value"]}) '
               f'on {certification["dateCertified"]["value"]}').replace('  ', ' ')
checks.append(_check('valuer-certification-present', 'warning', outcome, message,
                     targets=['/content/basis/certification'] if certification else []))

if annotation is None or schedule is None:
    outcome, message = 'not-applicable', 'There is no certification or no schedule document to link'
elif certification.get('documentRef') == schedule_ref:
    outcome, message = 'pass', 'The certification links to the schedule document'
else:
    outcome, message = 'fail', 'The certification does not link to the schedule document'
checks.append(_check('certification-linked-to-schedule', 'info', outcome, message,
                     targets=['/content/basis/certification'] if certification else []))

report['checks'] = [c for c in report.get('checks') or [] if c.get('definedBy') != REPORT_TYPE] + checks
report['stage'] = 'complete'
report['generatedBy'] = [step for step in report.get('generatedBy') or []
                         if step not in (STEP, SUMMARISE_STEP)] + [STEP]

summarise = get_transformer(*SUMMARISE)
output_data = summarise(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
