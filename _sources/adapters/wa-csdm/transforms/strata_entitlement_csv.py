# Transform: WA 3D CSDM CSD (JSON) -> Strata Scheme Entitlement Report lots (CSV).
# Composition only: facts -> complete (via `to-strata-entitlement-report`) -> the report block's `to-csv`.
to_report = get_transformer('csdm.reporting.adapters.wa-csdm', 'to-strata-entitlement-report')
to_csv = get_transformer('csdm.reporting.reports.strata-entitlement', 'to-csv')
output_data = to_csv(to_report(input_data))
