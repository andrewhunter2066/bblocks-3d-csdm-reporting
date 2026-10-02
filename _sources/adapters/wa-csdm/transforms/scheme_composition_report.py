# Transform: WA 3D CSDM CSD (JSON) -> complete Scheme Composition Report (JSON).
# Composition only: this block's `to-scheme-composition-facts`, then the report block's `complete`.
to_facts = get_transformer('csdm.reporting.adapters.wa-csdm', 'to-scheme-composition-facts')
complete = get_transformer('csdm.reporting.reports.scheme-composition', 'complete')
output_data = complete(to_facts(input_data))
