# Transform: Strata Scheme Entitlement Report (JSON) -> CSV, one row per lot.
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
# Standard library only. Each value is followed by its status, so missing or unusable values are explicit
# (an empty value with status `not-supplied`, for example), and the source pointer keeps the row traceable.
import csv
import io
import json

COLUMNS = ['scheme_number', 'lot_number', 'lot_number_status', 'unit_entitlement', 'unit_entitlement_status',
           'unit_entitlement_source', 'parcel_id']

report = json.loads(input_data)
content = report['content']
scheme_number = content['scheme']['schemeNumber'].get('value') or ''

buffer = io.StringIO()
writer = csv.writer(buffer, lineterminator='\n')
writer.writerow(COLUMNS)
for lot in content['lots']:
    entitlement = lot['entitlement']
    writer.writerow([
        scheme_number,
        lot['lotNumber'].get('value') or '',
        lot['lotNumber']['status'],
        '' if entitlement.get('value') is None else entitlement['value'],
        entitlement['status'],
        ' '.join(ref['pointer'] for ref in entitlement.get('sourceRefs') or []),
        (lot.get('ref') or {}).get('id', ''),
    ])
output_data = buffer.getvalue()
