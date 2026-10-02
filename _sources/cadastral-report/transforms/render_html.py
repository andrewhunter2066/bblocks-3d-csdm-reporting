# Transform: any cadastral report (JSON) -> standalone HTML page, rendered with Jinja2.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Generic: it knows only the report envelope. It renders the page frame (title, report status, sources),
# the documents and annotations the report relies on, a status marker for every ReportValue, a legend,
# the check results and the pipeline that produced the report. A report type supplies the body as a Jinja2
# template in the transform metadata (`template`), usually through get_transformer(...)(report,
# extra_metadata={'template': ...}); the template can use these macros and helpers:
#
#   {{ rv(value) }}            a ReportValue: its value (or why there is none) and a status marker
#   {{ doc_link(id) }}         a link to a document in `documents`
#   {% call dl('id') %}...{% endcall %} / {{ dt_dd('Label', value, 'id') }}   a definition list of values
#   report, content, documents (by id), annotations (by id)
#
# Without a template, the page shows the envelope only. Input that is not a report produces no output.
import json

import jinja2

STATUS = {
    'reported': ('R', 'Reported from the source'),
    'derived': ('D', 'Derived by the report'),
    'documented': ('Doc', 'From a supporting document'),
    'configured': ('C', 'Report-type constant'),
    'not-supplied': ('N', 'Not supplied by the source'),
    'unresolved': ('U', 'Reference could not be resolved'),
    'invalid': ('I', 'Supplied but not usable'),
    'conflicting': ('X', 'Sources disagree'),
}
NO_VALUE_TEXT = {'not-supplied': 'not supplied', 'unresolved': 'unresolved',
                 'invalid': 'invalid', 'conflicting': 'conflicting'}

BASE = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Cadastral report: {{ report.subject.label or report.reportType }}{% endblock %}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; max-width: 60rem; }
    table { border-collapse: collapse; min-width: 18rem; }
    th, td { border: 1px solid #999; padding: 0.3rem 0.8rem; }
    th { background: #eee; text-align: left; }
    td.num, tfoot td { text-align: right; }
    .missing { color: #a00; font-style: italic; }
    .meta { color: #555; }
    sup.status { font-size: 0.65em; margin-left: 0.2em; padding: 0 0.25em; border-radius: 0.3em;
                 background: #e6e6e6; color: #333; cursor: help; }
    sup.status-derived { background: #dbe9ff; }
    sup.status-not-supplied, sup.status-unresolved, sup.status-invalid, sup.status-conflicting {
      background: #ffd9d9; color: #800; }
    ul.legend { list-style: none; padding: 0; color: #555; font-size: 0.9em; }
    dl.details { display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; }
    dl.details dt { font-weight: bold; }
    dl.details dd { margin: 0; }
    .report-status { padding: 0.4rem 0.8rem; border-radius: 0.3rem; background: #eee; display: inline-block; }
    .report-status.status-complete { background: #dff3df; }
    .report-status.status-incomplete { background: #fff1cc; }
    .report-status.status-invalid { background: #ffd9d9; }
    table#checks { margin-top: 0.5rem; font-size: 0.9em; }
    tr.outcome-fail td:first-child { color: #a00; font-weight: bold; }
    tr.outcome-not-evaluated td:first-child { color: #8a6d00; }
  </style>
</head>
<body>
  <h1>{% block heading %}Cadastral report{% endblock %}</h1>
  {% if report.status -%}
  <p id="report-status" class="report-status status-{{ report.status }}">Report status: <strong>{{ report.status }}</strong>
  {%- if report.statusSummary %} ({{ report.statusSummary.checks }} checks: {{ report.statusSummary.failedErrors }} failed errors, {{ report.statusSummary.failedWarnings }} failed warnings, {{ report.statusSummary.unevaluatedErrors }} unevaluated errors){% endif %}</p>
  {%- else -%}
  <p id="report-status" class="report-status">Report status: <strong>not yet assessed</strong> ({{ report.stage }}-stage report)</p>
  {%- endif %}
  <p class="meta" id="sources">Source: {{ datasets | join(', ') }}
  {%- if vocabularies %}; vocabularies: {% for v in vocabularies %}<a href="{{ v.id }}">{{ v.name or v.id }}</a>{{ ', ' if not loop.last }}{% endfor %}{% endif %}</p>
{% block body %}{% endblock %}
  {% if documents %}
  <h2>Documents relied on</h2>
  <ul id="documents">
    {% for d in documents.values() %}<li>{{ doc_link(d.id) }}{% if d.role %} <span class="meta">({{ d.role }})</span>{% endif %}</li>
    {% endfor %}
  </ul>
  {% endif %}
  {% if used_statuses %}
  <p class="meta">Value status (hover a marker for its source or derivation):</p>
  <ul class="legend">
    {% for key in status_order if key in used_statuses %}<li><sup class="status status-{{ key }}">{{ STATUS[key][0] }}</sup> {{ STATUS[key][1] }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  <h2>Checks</h2>
  <table id="checks">
    <thead>
      <tr><th>Outcome</th><th>Severity</th><th>Category</th><th>Check</th><th>Message</th></tr>
    </thead>
    <tbody>
      {% for c in report.checks or [] %}<tr class="outcome-{{ c.outcome }}"><td>{{ c.outcome }}</td><td>{{ c.severity }}</td><td>{{ c.category }}</td><td><code>{{ c.id }}</code></td><td>{{ c.message }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
  <p class="meta" id="generated-by">Generated by: {% for s in report.generatedBy or [] %}<code>{{ s.bblock }}</code> {{ s.transform }}{{ ' → ' if not loop.last }}{% endfor %}</p>
</body>
</html>
'''

MACROS = r'''{% macro dl(id) -%}
<dl class="details" id="{{ id }}">
{{ caller() }}</dl>
{%- endmacro %}
{% macro dt_dd(label, value, id=None) -%}
{% if value %}    <dt>{{ label }}</dt><dd{% if id %} id="{{ id }}"{% endif %}>{{ rv(value) }}</dd>
{% endif %}
{%- endmacro %}
'''


def _provenance(value):
    status = value.get('status')
    parts = [STATUS.get(status, (status, status))[1]]
    if value.get('sourceRefs'):
        parts.append('source: ' + ', '.join(ref['pointer'] or ref.get('id') or ref['dataset']
                                            for ref in value['sourceRefs']))
    if value.get('derivation'):
        inputs = value['derivation'].get('inputs') or []
        parts.append(f'{value["derivation"]["method"]} of {len(inputs)} value(s)')
    if value.get('lexicalValue') is not None:
        parts.append(f'as supplied: {value["lexicalValue"]!r}')
    if value.get('note'):
        parts.append(value['note'])
    return '; '.join(parts)


def _display(value):
    """A value as text: lists comma-separated (an empty list as "none"), booleans as yes/no."""
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, list):
        return ', '.join(_display(item) for item in value) if value else 'none'
    return str(value)


def _rv(value):
    """Render a ReportValue: the value (or its absence) followed by a status marker."""
    status = value.get('status', 'unknown')
    letter = STATUS.get(status, ('?', status))[0]
    escape = jinja2.utils.markupsafe.escape
    text = (f'<span class="missing">{escape(NO_VALUE_TEXT.get(status, "no value"))}</span>'
            if value.get('value') is None else str(escape(_display(value['value']))))
    return jinja2.utils.markupsafe.Markup(
        f'<span class="rv" data-status="{escape(status)}">{text}'
        f'<sup class="status status-{escape(status)}" title="{escape(_provenance(value))}">{escape(letter)}</sup></span>')


def _statuses(node):
    if isinstance(node, dict):
        if 'status' in node and 'value' in node:
            yield node['status']
        else:
            for child in node.values():
                yield from _statuses(child)
    elif isinstance(node, list):
        for child in node:
            yield from _statuses(child)


report = json.loads(input_data)
if not (isinstance(report, dict) and 'reportType' in report and 'content' in report):
    output_data = None
else:
    documents = {d['id']: d for d in report.get('documents') or []}
    annotations = {a['id']: a for a in report.get('annotations') or []}
    escape = jinja2.utils.markupsafe.escape

    def _doc_link(doc_id):
        document = documents.get(doc_id)
        if not document:
            return jinja2.utils.markupsafe.Markup('<span class="missing">not referenced</span>')
        kind = f' ({escape(document["mediaType"])})' if document.get('mediaType') else ''
        return jinja2.utils.markupsafe.Markup(
            f'<a href="{escape(document["href"])}">{escape(document.get("title") or document["href"])}</a>{kind}')

    metadata = getattr(transform_metadata, 'metadata', None) or {}
    template = metadata.get('template') or '{% extends "base.html" %}'
    environment = jinja2.Environment(
        loader=jinja2.DictLoader({'base.html': BASE, 'macros.html': MACROS, 'report.html': template}),
        autoescape=True, trim_blocks=False, lstrip_blocks=False)
    environment.globals.update(rv=_rv, doc_link=_doc_link, STATUS=STATUS, status_order=list(STATUS))
    macros = environment.get_template('macros.html').module
    environment.globals.update(dl=macros.dl, dt_dd=macros.dt_dd)
    sources = report.get('sources') or []
    output_data = environment.get_template('report.html').render(
        report=report,
        content=report['content'],
        documents=documents,
        annotations=annotations,
        datasets=[s.get('name') or s['id'] for s in sources if s.get('kind') != 'vocabulary'],
        vocabularies=[s for s in sources if s.get('kind') == 'vocabulary'],
        used_statuses=set(_statuses(report['content'])),
    )
