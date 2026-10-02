# Transform: WA 3D CSDM CSD (JSON) -> Scheme Composition Report (HTML).
# Composition only: facts -> complete (via `to-scheme-composition-report`) -> the report block's `to-html`.
to_report = get_transformer('csdm.reporting.adapters.wa-csdm', 'to-scheme-composition-report')
to_html = get_transformer('csdm.reporting.reports.scheme-composition', 'to-html')
output_data = to_html(to_report(input_data))
