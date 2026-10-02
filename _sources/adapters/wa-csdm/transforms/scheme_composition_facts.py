# Transform: WA 3D CSDM CSD (JSON) -> facts-stage Scheme Composition Report (JSON).
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# The scheme, its members and the membership checks come from the shared `resolve-scheme` transform.
# This transform adds, for each member lot, the facts the composition report needs: its geometry
# (topology) type, its representation status, and each component solid it references, with whether that
# solid is present in the dataset. Derived values (whether a member is spatially resolved, the summary)
# are added by the report block's `complete`.
import json

ADAPTER_BBLOCK = 'csdm.reporting.adapters.wa-csdm'
REPORT_TYPE = 'csdm.reporting.reports.scheme-composition'


def _pointer(*parts):
    """JSON Pointer (RFC 6901) from path segments."""
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def _ref(pointer, object_id=None):
    ref = {'dataset': dataset_id, 'pointer': pointer}
    if object_id:
        ref['id'] = object_id
    return ref


def _value(status, value=None, refs=(), note=None):
    result = {'value': value, 'status': status}
    if refs:
        result['sourceRefs'] = list(refs)
    if note:
        result['note'] = note
    return result


def _resolve(document, pointer):
    target = document
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        target = target[int(token)] if isinstance(target, list) else target[token]
    return target


def _targeted(check, position):
    """A resolve-scheme check with its member ids turned into pointers to this report's members."""
    check = dict(check)
    members = check.pop('targetMembers', [])
    if members:
        check['targets'] = [f'/content/members/{position[m]}' for m in members if m in position]
    return check


def _member_facts(member):
    if member['pointer'] is None:
        unresolved = _value('unresolved', refs=[member['ref']], note=member['note'])
        return {'geometryType': unresolved, 'representationStatus': unresolved, 'components': []}
    ptr, feature = member['pointer'], _resolve(csd, member['pointer'])
    topology = feature.get('topology') or {}
    geometry_type = (_value('reported', topology['type'], [_ref(ptr + _pointer('topology', 'type'))])
                     if topology.get('type') else
                     _value('not-supplied', refs=[_ref(ptr)], note='The lot has no topology type'))
    definitions = (feature.get('properties') or {}).get('spatialRepresentationDefinitions')
    status = definitions.get('representationStatus') if isinstance(definitions, dict) else None
    representation_status = (
        _value('reported', status, [_ref(ptr + _pointer('properties', 'spatialRepresentationDefinitions',
                                                         'representationStatus'))])
        if status else
        _value('not-supplied', refs=[_ref(ptr + _pointer('properties'))],
               note='The lot has no spatialRepresentationDefinitions.representationStatus'))
    components = []
    for index, component_id in enumerate(topology.get('references') or []):
        if component_id in solids:
            components.append({'ref': _ref(solids[component_id], component_id), 'found': True})
        else:
            components.append({'ref': _ref(ptr + _pointer('topology', 'references', index), component_id),
                               'found': False})
    return {'geometryType': geometry_type, 'representationStatus': representation_status,
            'components': components}


csd = json.loads(input_data)
dataset_id = csd.get('id') or csd.get('name') or 'source'
solids = {feature.get('id'): _pointer('solids', ci, 'features', fi)
          for ci, collection in enumerate(csd.get('solids') or [])
          for fi, feature in enumerate((collection or {}).get('features') or []) if feature.get('id')}

resolution = json.loads(get_transformer(ADAPTER_BBLOCK, 'resolve-scheme')(input_data))
members = [{'ref': m['ref'], 'lotNumber': m['lotNumber'], 'membershipEvidence': m['membershipEvidence'],
            **_member_facts(m)} for m in resolution['members']]
position = {m['id']: i for i, m in enumerate(resolution['members'])}

report = {
    'reportType': REPORT_TYPE,
    'stage': 'facts',
    'generatedBy': [{'bblock': ADAPTER_BBLOCK, 'transform': 'to-scheme-composition-facts'}],
    'subject': {'kind': 'strata-scheme', 'label': resolution['scheme']['label'], 'ref': resolution['scheme']['ref']},
    'sources': [resolution['source']],
    'content': {
        'scheme': {'schemeNumber': resolution['scheme']['schemeNumber'], 'ref': resolution['scheme']['ref']},
        'members': members,
    },
    'checks': [_targeted(check, position) for check in resolution['checks']],
}
if report['subject']['label'] is None:
    del report['subject']['label']

output_data = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
