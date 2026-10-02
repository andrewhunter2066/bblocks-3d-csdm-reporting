# Transform: Scheme Composition Report (JSON) -> standalone HTML page.
# Template only: the page frame, status markers, legend and check results come from the generic
# `render-html` transform of csdm.reporting.cadastral-report.
TEMPLATE = r'''{% extends "base.html" %}
{% block title %}Scheme Composition Report: {{ content.scheme.schemeNumber.value or 'scheme number not supplied' }}{% endblock %}
{% block heading %}Scheme Composition Report{% endblock %}
{% block body %}
  <p><strong>Scheme number:</strong> <span id="scheme-number">{{ rv(content.scheme.schemeNumber) }}</span></p>
  {% if content.summary %}
  <h2>Spatial representation summary</h2>
  {% call dl('summary') %}{{ dt_dd('Member parcels', content.summary.memberParcelCount, 'member-count') }}{{ dt_dd('Geometry types', content.summary.geometryTypes, 'geometry-types') }}{{ dt_dd('Representation statuses', content.summary.memberRepresentationStatuses, 'representation-statuses') }}{{ dt_dd('All members spatially resolved', content.summary.allMemberParcelsSpatiallyResolved, 'all-resolved') }}{% endcall %}
  {% endif %}
  <h2>Members</h2>
  <table id="members">
    <thead>
      <tr><th>Lot number</th><th>Geometry type</th><th>Representation status</th><th>Components found</th><th>Spatially resolved</th></tr>
    </thead>
    <tbody>
      {% for m in content.members %}<tr><td>{{ rv(m.lotNumber) }}</td><td>{{ rv(m.geometryType) }}</td><td>{{ rv(m.representationStatus) }}</td><td class="num">{{ m.components | selectattr('found') | list | length }} of {{ m.components | length }}</td><td>{% if m.spatiallyResolved %}{{ rv(m.spatiallyResolved) }}{% else %}<span class="missing">not assessed ({{ report.stage }}-stage report)</span>{% endif %}</td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
'''

render_html = get_transformer('csdm.reporting.cadastral-report', 'render-html')
output_data = render_html(input_data, extra_metadata={'template': TEMPLATE})
