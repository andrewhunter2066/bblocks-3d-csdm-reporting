# Transform: WA 3D CSDM CSD (JSON) -> the resolved strata scheme and its members (JSON).
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Shared source interpretation for every strata report built from a WA 3D CSDM dataset. Promoted out of
# `to-strata-entitlement-facts` in Stage 8, when the Scheme Composition Report needed the same scheme
# resolution (the trigger recorded in the investigation, section 3). Report transforms call it with
# get_transformer('csdm.reporting.adapters.wa-csdm', 'resolve-scheme').
#
# Rules (see this block's description.md):
# - scheme:  the one parcel with parcelPurpose = wa-parcel-purpose:strata-scheme (D5); otherwise this
#   transform raises, which stops report generation
# - members: the scheme's topology.references where topology.type = ParcelAggregate (D4); each member's
#   containingPrimaryParcel and schemeRef are recorded as corroborating membership evidence
#
# Output: {source, scheme {pointer, id, label, ref, schemeNumber}, members [{id, pointer, ref, lotNumber,
# membershipEvidence, note?}] sorted by lot number, checks [...]}. A member whose reference cannot be
# followed has `pointer: null`. Checks about particular members carry `targetMembers` (member ids)
# instead of report pointers; the calling report turns them into `targets` for its own content layout.
import json

ADAPTER_BBLOCK = 'csdm.reporting.adapters.wa-csdm'
SOURCE_PROFILE = 'icsm.profiles.wa.wa-3d'
SCHEME_PURPOSE = 'wa-parcel-purpose:strata-scheme'
LOT_PURPOSE = 'wa-parcel-purpose:strata-lot'


def _pointer(*parts):
    """JSON Pointer (RFC 6901) from path segments."""
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def _lexical(raw):
    return raw if isinstance(raw, str) else json.dumps(raw)


def _ref(pointer, object_id=None):
    ref = {'dataset': dataset_id, 'pointer': pointer}
    if object_id:
        ref['id'] = object_id
    return ref


def _value(status, value=None, refs=(), lexical=None, note=None):
    result = {'value': value, 'status': status}
    if refs:
        result['sourceRefs'] = list(refs)
    if lexical is not None:
        result['lexicalValue'] = lexical
    if note:
        result['note'] = note
    return result


def _check(check_id, category, severity, passed, message, targets=(), evidence=None, target_members=()):
    check = {'id': check_id, 'definedBy': ADAPTER_BBLOCK, 'category': category, 'severity': severity,
             'outcome': 'pass' if passed else 'fail', 'message': message}
    if targets:
        check['targets'] = list(targets)
    if target_members:
        check['targetMembers'] = list(target_members)
    if evidence:
        check['evidence'] = evidence
    return check


def _parcel_features(csd):
    """Yield (pointer, feature) for every feature in every parcel collection."""
    for ci, collection in enumerate(csd.get('parcels') or []):
        for fi, feature in enumerate((collection or {}).get('features') or []):
            yield _pointer('parcels', ci, 'features', fi), feature


def _lot_number(ptr, feature):
    appellation = (feature.get('properties') or {}).get('appellation') or {}
    for i, part in enumerate(appellation.get('hasPart') or []):
        label = part.get('label')
        if part.get('type') == 'lotNumber' and label not in (None, ''):
            refs = [_ref(ptr + _pointer('properties', 'appellation', 'hasPart', i, 'label'))]
            return _value('reported', str(label), refs, lexical=None if isinstance(label, str) else _lexical(label))
    return _value('not-supplied', refs=[_ref(ptr + _pointer('properties', 'appellation'))],
                  note='No appellation part with type lotNumber')


def _back_links(feature):
    """(containingPrimaryParcel hrefs, schemeRef) recorded on a lot."""
    relationships = (feature.get('topology') or {}).get('relationships') or []
    containing = [r.get('href') for r in relationships if r.get('role') == 'containingPrimaryParcel']
    return containing, (feature.get('properties') or {}).get('schemeRef')


def _normalised(number):
    return ''.join(str(number).split()).upper() if number not in (None, '') else None


def _sort_key(member):
    number = member['lotNumber']['value']
    if number is not None and number.isdigit():
        return 0, int(number), number
    return 1, 0, number or ''


csd = json.loads(input_data)
dataset_id = csd.get('id') or csd.get('name') or 'source'
features = list(_parcel_features(csd))

schemes = [(ptr, f) for ptr, f in features
           if (f.get('properties') or {}).get('parcelPurpose') == SCHEME_PURPOSE]
if len(schemes) != 1:
    raise ValueError(f'Expected exactly one strata scheme parcel (parcelPurpose = {SCHEME_PURPOSE}), '
                     f'found {len(schemes)}')
scheme_ptr, scheme = schemes[0]
scheme_id = scheme.get('id')
scheme_props = scheme.get('properties') or {}
topology = scheme.get('topology') or {}
is_aggregate = topology.get('type') == 'ParcelAggregate'
member_ids = (topology.get('references') or []) if is_aggregate else []
by_id = {f.get('id'): (ptr, f) for ptr, f in features if f.get('id')}

# --- Members ------------------------------------------------------------------------------------------
members = []
for index, member_id in enumerate(member_ids):
    ptr, lot = by_id.get(member_id, (None, None))
    if lot is None:
        # The scheme references a lot that is not in the dataset: keep it visible as unresolved.
        reference = _ref(scheme_ptr + _pointer('topology', 'references', index), member_id)
        note = f'Scheme member {member_id} is not a feature of this dataset'
        members.append({'id': member_id, 'pointer': None, 'ref': reference,
                        'lotNumber': _value('unresolved', refs=[reference], note=note),
                        'membershipEvidence': ['references'], 'note': note})
        continue
    containing, scheme_ref = _back_links(lot)
    evidence = ['references']
    if scheme_id in containing:
        evidence.append('containingPrimaryParcel')
    if scheme_ref == scheme_id:
        evidence.append('schemeRef')
    members.append({'id': member_id, 'pointer': ptr, 'ref': _ref(ptr, member_id),
                    'lotNumber': _lot_number(ptr, lot), 'membershipEvidence': evidence})
members.sort(key=_sort_key)

# --- Checks -------------------------------------------------------------------------------------------
checks = [_check('scheme-identified', 'generation', 'error', True,
                 f'One strata scheme parcel identified ({scheme_id})', evidence={'schemeId': scheme_id})]

checks.append(_check(
    'membership-parcel-aggregate', 'domain', 'error', is_aggregate and bool(member_ids),
    f'The scheme topology is ParcelAggregate with {len(member_ids)} member reference(s)' if is_aggregate
    else f'The scheme topology type is {topology.get("type")!r}, not ParcelAggregate, so it lists no members',
    evidence={'topologyType': topology.get('type'), 'references': len(member_ids)}))

not_lots = []
for member_id in member_ids:
    _, feature = by_id.get(member_id, (None, None))
    if feature is None or (feature.get('properties') or {}).get('parcelPurpose') != LOT_PURPOSE:
        not_lots.append(member_id)
checks.append(_check(
    'membership-references-resolve', 'domain', 'error', not not_lots,
    f'All {len(member_ids)} references resolve to strata-lot parcels' if not not_lots
    else f'{len(not_lots)} of {len(member_ids)} references do not resolve to a strata-lot parcel',
    target_members=not_lots, evidence={'unresolved': not_lots} if not_lots else None))

broken = []
for member_id in member_ids:
    _, feature = by_id.get(member_id, (None, None))
    if feature is None:
        continue
    containing, scheme_ref = _back_links(feature)
    problems = []
    if scheme_id not in containing:
        problems.append('containingPrimaryParcel missing or not the scheme')
    if scheme_ref is not None and scheme_ref != scheme_id:
        problems.append('schemeRef is not the scheme')
    if problems:
        broken.append({'lot': member_id, 'problems': problems})
checks.append(_check(
    'membership-back-links', 'domain', 'warning', not broken,
    'Every member lot links back to the scheme' if not broken
    else f'{len(broken)} member lot(s) do not link back to the scheme consistently',
    target_members=[b['lot'] for b in broken], evidence={'lots': broken} if broken else None))

claimants = []
for ptr, feature in features:
    if (feature.get('properties') or {}).get('parcelPurpose') != LOT_PURPOSE or feature.get('id') in member_ids:
        continue
    containing, scheme_ref = _back_links(feature)
    if scheme_id in containing or scheme_ref == scheme_id:
        claimants.append({'id': feature.get('id'), 'pointer': ptr})
checks.append(_check(
    'membership-unreferenced-claimants', 'domain', 'warning', not claimants,
    'No strata lot claims the scheme without being one of its references' if not claimants
    else f'{len(claimants)} strata lot(s) link to the scheme but are not in its references, so are not members',
    evidence={'lots': claimants} if claimants else None))

survey_number = next((p.get('label') for p in (scheme_props.get('appellation') or {}).get('hasPart') or []
                      if p.get('type') == 'surveyNumber'), None)
spellings = {'schemeNumber': scheme_props.get('schemeNumber'), 'csdName': csd.get('name'),
             'appellationSurveyNumber': survey_number}
present = {k: v for k, v in spellings.items() if v not in (None, '')}
agree = len({_normalised(v) for v in present.values()}) <= 1 and 'schemeNumber' in present
checks.append(_check(
    'scheme-number-consistent', 'domain', 'warning', agree,
    ('The scheme number agrees with ' + ' and '.join(k for k in present if k != 'schemeNumber')
     + ' (ignoring spaces)') if agree
    else 'The scheme number is missing or differs from the CSD name or appellation survey number',
    targets=['/content/scheme/schemeNumber'], evidence=present))

if scheme_props.get('schemeNumber') not in (None, ''):
    scheme_number = _value('reported', str(scheme_props['schemeNumber']),
                           [_ref(scheme_ptr + _pointer('properties', 'schemeNumber'))])
else:
    scheme_number = _value('not-supplied', refs=[_ref(scheme_ptr + _pointer('properties'))],
                           note='The scheme parcel has no schemeNumber')

source = {'id': dataset_id, 'kind': 'dataset', 'name': csd.get('name'),
          'date': (csd.get('time') or {}).get('date'), 'conformsTo': SOURCE_PROFILE}
output_data = json.dumps({
    'source': {k: v for k, v in source.items() if v is not None},
    'scheme': {
        'pointer': scheme_ptr,
        'id': scheme_id,
        'label': (scheme_props.get('appellation') or {}).get('label') or scheme_props.get('schemeNumber'),
        'ref': _ref(scheme_ptr, scheme_id),
        'schemeNumber': scheme_number,
    },
    'members': members,
    'checks': checks,
}, ensure_ascii=False)
