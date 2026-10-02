# Transform: WA 3D CSDM CSD (JSON) -> Strata Scheme Entitlement Report (HTML).
# Composition only: facts -> complete (via `to-strata-entitlement-report`) -> the report block's `to-html`.
to_report = get_transformer('csdm.reporting.adapters.wa-csdm', 'to-strata-entitlement-report')
to_html = get_transformer('csdm.reporting.reports.strata-entitlement', 'to-html')
output_data = to_html(to_report(input_data))
