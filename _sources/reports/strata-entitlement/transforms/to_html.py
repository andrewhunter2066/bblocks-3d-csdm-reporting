# Transform: Strata Scheme Entitlement Report (JSON) -> standalone HTML page.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Template only: the page frame, status markers, legend, documents and check results come from the
# generic `render-html` transform of csdm.reporting.cadastral-report. This file holds the
# entitlement-specific body as a Jinja2 template and passes it to that transform.
TEMPLATE = r'''{% extends "base.html" %}
{% block title %}Unit Entitlement Report: {{ content.scheme.schemeNumber.value or 'scheme number not supplied' }}{% endblock %}
{% block heading %}Unit Entitlement Report{% endblock %}
{% block body %}
  <p><strong>Scheme number:</strong> <span id="scheme-number">{{ rv(content.scheme.schemeNumber) }}</span></p>
  {% call dl('scheme') %}{{ dt_dd('Scheme name', content.scheme.schemeName, 'scheme-name') }}{{ dt_dd('Scheme address', content.scheme.address and content.scheme.address.formatted, 'scheme-address') }}{% endcall %}
  <h2>Unit entitlements</h2>
  <table id="lots">
    <thead>
      <tr><th>Lot number</th><th>Unit entitlement</th></tr>
    </thead>
    <tbody>
      {% for lot in content.lots %}<tr><td>{{ rv(lot.lotNumber) }}</td><td class="num">{{ rv(lot.entitlement) }}</td></tr>
      {% endfor %}
    </tbody>
    <tfoot>
      {% set totals = content.totals or {} %}
      {% if totals.calculated %}<tr><td>Calculated total ({{ rv(totals.lotCount) }} lots)</td><td id="calculated-total" class="num">{{ rv(totals.calculated) }}</td></tr>
      {% else %}<tr><td>Calculated total ({{ content.lots | length }} lots)</td><td id="calculated-total" class="num"><span class="missing">not calculated ({{ report.stage }}-stage report)</span></td></tr>
      {% endif %}
      {% if totals.declared %}<tr><td>Declared total</td><td id="declared-total" class="num">{{ rv(totals.declared) }}</td></tr>{% endif %}
    </tfoot>
  </table>
  {% set basis = content.basis or {} %}
  <h2>Basis of the schedule</h2>
  {% call dl('basis') %}
    {%- if basis.schedule %}    <dt>Schedule document</dt><dd id="schedule-document">{{ doc_link(basis.schedule.documentRef) }}</dd>
    {% else %}    <dt>Schedule</dt><dd><span class="missing">not referenced</span></dd>
    {% endif -%}
    {%- if basis.form %}    <dt>Approved form</dt><dd id="approved-form"><code>{{ basis.form.id }}</code></dd>
    {{ dt_dd('Form', basis.form.label) }}{{ dt_dd('Effective for use from', basis.form.validFrom, 'form-valid-from') }}{{ dt_dd('Form published at', basis.form.source) }}
    {%- endif -%}
    {%- for law in content.legislativeBasis or [] %}{{ dt_dd('Legislation', law, 'legislation-' ~ loop.index) }}{% endfor %}
  {% endcall %}
  <h2>Certificate of licensed valuer</h2>
  {% call dl('certification') %}
    {%- set certification = basis.certification -%}
    {%- if certification -%}
    {{ dt_dd('Valuer first name', certification.certifier.firstName) }}{{ dt_dd('Valuer last name', certification.certifier.lastName) }}{{ dt_dd('Licensed valuer number', certification.certifier.licensedValuerNumber, 'valuer-number') }}{{ dt_dd('Date certified', certification.dateCertified, 'date-certified') }}
    {%- set annotation = annotations.get(certification.annotationRef) -%}
    {%- if annotation and annotation.statement %}    <dt>Statement</dt><dd id="certification-statement">{{ annotation.statement }}</dd>
    {% endif -%}
    {%- if certification.documentRef %}    <dt>Certifies</dt><dd>{{ doc_link(certification.documentRef) }}</dd>
    {% endif -%}
    {%- else %}    <dt>Certification</dt><dd><span class="missing">not recorded</span></dd>
    {% endif -%}
  {% endcall %}
{% endblock %}
'''

render_html = get_transformer('csdm.reporting.cadastral-report', 'render-html')
output_data = render_html(input_data, extra_metadata={'template': TEMPLATE})
