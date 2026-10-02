# Transform: any cadastral report (JSON) -> the same report with its overall `status` set.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Generic: knows only the report envelope, so every report type can call it (via get_transformer) when
# it completes a report. Rules:
#   invalid     any check with severity `error` and outcome `fail`
#   incomplete  otherwise, any `warning` check that fails, or any `error` check that was not evaluated
#   complete    otherwise
# The rule counts are recorded in `statusSummary`. Only a `complete` stage report has a status, so a
# facts-stage report, like input that is not a report, produces no output.
import json

STEP = {'bblock': 'csdm.reporting.cadastral-report', 'transform': 'summarise-checks'}

report = json.loads(input_data)
if not (isinstance(report, dict) and 'reportType' in report and 'content' in report) \
        or report.get('stage') != 'complete':
    output_data = None
else:
    checks = report.get('checks') or []

    def count(severity, outcome):
        return sum(1 for c in checks if c.get('severity') == severity and c.get('outcome') == outcome)

    failed_errors = count('error', 'fail')
    failed_warnings = count('warning', 'fail')
    unevaluated_errors = count('error', 'not-evaluated')
    if failed_errors:
        status = 'invalid'
    elif failed_warnings or unevaluated_errors:
        status = 'incomplete'
    else:
        status = 'complete'

    report['status'] = status
    report['statusSummary'] = {
        'checks': len(checks),
        'failedErrors': failed_errors,
        'failedWarnings': failed_warnings,
        'unevaluatedErrors': unevaluated_errors,
    }
    report['generatedBy'] = [s for s in report.get('generatedBy') or [] if s != STEP] + [STEP]
    output_data = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
