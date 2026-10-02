# Transform: WA 3D CSDM CSD (JSON) -> complete Strata Scheme Entitlement Report (JSON).
# Composition only: this block's `to-strata-entitlement-facts` (source interpretation), then the
# report block's `complete` (derived values). No calculation happens in the adapter.
to_facts = get_transformer('csdm.reporting.adapters.wa-csdm', 'to-strata-entitlement-facts')
complete = get_transformer('csdm.reporting.reports.strata-entitlement', 'complete')
output_data = complete(to_facts(input_data))
