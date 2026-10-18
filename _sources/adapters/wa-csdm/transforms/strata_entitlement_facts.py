# Transform: WA 3D CSDM CSD (JSON) -> facts-stage Strata Scheme Entitlement Report (JSON).
# Runs as an OGC Building Blocks `python` transform: reads `input_data`, assigns `output_data`.
#
# Extracts source facts only: the scheme (number, name, address), each member lot's number and unit
# entitlement, the declared total, and the basis of the schedule (the lodged schedule document, its
# approved form, the valuer's certification and the legislation). Derived values (calculated totals) are
# added by the report block's `complete` transform, so they are calculated the same way whatever the
# source format. The one value derived here is the formatted address, because formatting interprets the
# source's address parts.
#
# Every value is a ReportValue (see csdm.reporting.cadastral-report): its status says where it came from,
# or why there is no usable value, and sourceRefs point at the exact source property (JSON Pointer).
# Missing or unusable source data never stops the transform; only an unidentifiable scheme does (D5).
#
# Interpretation rules (see this block's description.md):
# - scheme and members: from the shared `resolve-scheme` transform (D4, D5)
# - entitlement: the lot parcel's properties.entitlementPortion, coerced to a positive integer (D7)
# - declared total: the scheme parcel's properties.entitlementTotal (D10)
#   Both are parcel properties, not interests (WA vocabulary review decision D7): the
#   wa-interest-type:strata-lot and strata-scheme interest types are retired. A value found only in such
#   an interest is not read; the not-supplied value's note says where it is.
# - address: schemeAddress.hasPart; road label from the apt:road value's `label`, locality label from the
#   wa-locality vocabulary (D8)
# - schedule: supportingDocuments[role = wa-survey-documentation-type:scheme-ue]; its
#   conformsTo names the approved form, whose label, validity, source and legislation (scope note) come
#   from the wa-approved-form vocabulary
# - certification: annotations[role = wa-annotation:licensed-valuer-certification] (D9)
#
# Vocabulary labels come from this block's `vocabulary-labels` transform; a value found there is
# `reported` with the vocabulary concept as its source.
#
# Scheme identification, membership and their checks come from the shared `resolve-scheme` transform;
# this transform adds the entitlement-specific facts and the source datatype check. Report-level checks
# are added by the report block's `complete`.
import json
import re

ADAPTER_BBLOCK = 'csdm.reporting.adapters.wa-csdm'
REPORT_TYPE = 'csdm.reporting.reports.strata-entitlement'
# Interest types that held entitlements before WA vocabulary review D7; read only to explain a gap.
RETIRED_LOT_INTEREST_TYPE = 'wa-interest-type:strata-lot'
RETIRED_SCHEME_INTEREST_TYPE = 'wa-interest-type:strata-scheme'
# The published Schedule of Unit Entitlements document type; the draft unitEntitlementSchedule was merged into
# it (WA vocabulary review crosswalk).
SCHEDULE_ROLE = 'wa-survey-documentation-type:scheme-ue'
# Source property IRIs, from the source profile's JSON-LD context. The WA profile maps
# interests[].entitlementPortion to the LADM land-parcels term it inherits; the same term is used for the
# lot parcel's entitlementPortion, which the context does not map yet (built-strata decision register
# items 9 and 10).
SOURCE_PROPERTIES = {'entitlementPortion': 'https://w3id.org/ogc/ladm/parcels/entitlementPortion'}
# wa-annotation is the current prefix; the wa-core context keeps wa-annotation-role as an alias for the same
# namespace, so both name the same concept.
CERTIFICATION_ROLES = ('wa-annotation:licensed-valuer-certification',
                       'wa-annotation-role:licensed-valuer-certification')


def _pointer(*parts):
    """JSON Pointer (RFC 6901) from path segments."""
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def _lexical(raw):
    return raw if isinstance(raw, str) else json.dumps(raw)


def _ref(pointer, object_id=None):
    ref = {'dataset': dataset_id, 'pointer': pointer}
    if object_id:
        ref['id'] = object_id
    source_property = SOURCE_PROPERTIES.get(pointer.rsplit('/', 1)[-1])
    if source_property:
        ref['property'] = source_property
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


def _positive_integer(raw):
    """The unit entitlement as a positive integer, or None when the supplied value is not one."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, str) and re.fullmatch(r'\s*[0-9]+\s*', raw):
        return int(raw) if int(raw) > 0 else None
    return None


def _parcel_number(ptr, feature, key, retired_interest_type):
    """A positive whole number held by the parcel's own property `key`."""
    props = feature.get('properties') or {}
    raw = props.get(key)
    if raw is None:
        refs, note = [_ref(ptr + _pointer('properties'))], f'The parcel has no {key}'
        retired = [i for i, interest in enumerate(props.get('interests') or [])
                   if isinstance(interest, dict) and interest.get('interestType') == retired_interest_type
                   and interest.get(key) is not None]
        if retired:
            refs += [_ref(ptr + _pointer('properties', 'interests', i)) for i in retired]
            note += (f'; a {retired_interest_type} interest holds one, but {key} is a parcel property, '
                     'not an interest (WA vocabulary review D7)')
        return _value('not-supplied', refs=refs, note=note)

    pointer = ptr + _pointer('properties', key)
    value = _positive_integer(raw)
    if value is None:
        return _value('invalid', refs=[_ref(pointer)], lexical=_lexical(raw), note='Not a positive whole number')
    lexical = None if isinstance(raw, int) and not isinstance(raw, bool) else _lexical(raw)
    return _value('reported', value, [_ref(pointer)], lexical=lexical)


def _resolve(document, pointer):
    """The object at a JSON Pointer."""
    target = document
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        target = target[int(token)] if isinstance(target, list) else target[token]
    return target


def _targeted(check, position):
    """A resolve-scheme check with its member ids turned into pointers to this report's lots."""
    check = dict(check)
    members = check.pop('targetMembers', [])
    if members:
        check['targets'] = [f'/content/lots/{position[m]}' for m in members if m in position]
    return check


def _check(check_id, category, severity, passed, message, targets=(), evidence=None, outcome=None):
    check = {'id': check_id, 'definedBy': ADAPTER_BBLOCK, 'category': category, 'severity': severity,
             'outcome': outcome or ('pass' if passed else 'fail'), 'message': message}
    if targets:
        check['targets'] = list(targets)
    if evidence:
        check['evidence'] = evidence
    return check


def _vocabulary_value(code, key, pointer, what):
    """A ReportValue for property `key` of the vocabulary concept named by `code` (a CURIE)."""
    prefix, _, name = code.partition(':') if isinstance(code, str) else ('', '', '')
    vocabulary = VOCABULARIES.get(prefix)
    concept = (vocabulary or {}).get('concepts', {}).get(name) if name else None
    if concept is None:
        return _value('unresolved', refs=[_ref(pointer)],
                      note=f'{code!r} is not a concept of an available vocabulary')
    used_vocabularies[prefix] = vocabulary
    concept_ref = {'dataset': vocabulary['scheme'], 'pointer': '', 'id': vocabulary['namespace'] + name}
    if not concept.get(key):
        return _value('not-supplied', refs=[concept_ref], note=f'The vocabulary gives {code} no {what}')
    return _value('reported', concept[key], [concept_ref])


def _text(container, key, pointer, what):
    """A ReportValue for a text property of a source object."""
    raw = (container or {}).get(key)
    if raw in (None, ''):
        return _value('not-supplied', refs=[_ref(pointer)], note=f'No {what}')
    return _value('reported', str(raw), [_ref(pointer + _pointer(key))],
                  lexical=None if isinstance(raw, str) else _lexical(raw))


def _address(scheme_ptr, props):
    base = scheme_ptr + _pointer('properties', 'schemeAddress')
    address = props.get('schemeAddress')
    if not isinstance(address, dict) or not address.get('hasPart'):
        return {'parts': [], 'formatted': _value('not-supplied', refs=[_ref(scheme_ptr + _pointer('properties'))],
                                                 note='The scheme parcel has no schemeAddress')}
    parts, where = [], {}
    for i, part in enumerate(address['hasPart']):
        ptr = base + _pointer('hasPart', i)
        part_type, value = part.get('partType'), part.get('value')
        entry = {'partType': part_type, 'value': value}
        if part_type == 'apt:road':
            entry['label'] = (_value('reported', str(value['label']), [_ref(ptr + _pointer('value', 'label'))])
                              if isinstance(value, dict) and value.get('label') else
                              _value('unresolved', refs=[_ref(ptr + _pointer('value'))], note='The road has no label'))
        elif part_type == 'apt:locality':
            entry['label'] = _vocabulary_value(value, 'prefLabel', ptr + _pointer('value'), 'label')
        where.setdefault(part_type, i)
        parts.append(entry)

    missing = [t for t in ('apt:road', 'apt:locality') if t not in where]
    if missing:
        formatted = _value('not-supplied', refs=[_ref(base)], note=f'No {" or ".join(missing)} part')
    else:
        labels = [parts[where[t]]['label'] for t in ('apt:road', 'apt:locality')]
        unusable = [label for label in labels if label['value'] is None]
        if unusable:
            formatted = _value('unresolved', refs=[r for label in unusable for r in label.get('sourceRefs', [])],
                               note='A road or locality label is not available')
        else:
            inputs, number = [], ''
            if 'apt:addressNumberFirst' in where:
                index = where['apt:addressNumberFirst']
                number = str(parts[index]['value'])
                inputs.append(f'/content/scheme/address/parts/{index}/value')
                if 'apt:addressNumberLast' in where:
                    index = where['apt:addressNumberLast']
                    number += f'-{parts[index]["value"]}'
                    inputs.append(f'/content/scheme/address/parts/{index}/value')
            inputs += [f'/content/scheme/address/parts/{where[t]}/label' for t in ('apt:road', 'apt:locality')]
            text = f'{number} {labels[0]["value"]}, {labels[1]["value"]}'.strip()
            formatted = {'value': text, 'status': 'derived',
                         'derivation': {'method': 'format-address', 'inputs': inputs}}
    return {'parts': parts, 'formatted': formatted}


def _document(index, doc, doc_id):
    reference = {'id': doc_id, 'title': doc.get('title'), 'href': doc.get('href'), 'mediaType': doc.get('type'),
                 'role': doc.get('role'), 'conformsTo': doc.get('conformsTo'),
                 'sourceRef': _ref(_pointer('supportingDocuments', index))}
    return {k: v for k, v in reference.items() if v is not None}


csd = json.loads(input_data)
dataset_id = csd.get('id') or csd.get('name') or 'source'
VOCABULARIES = json.loads(get_transformer(ADAPTER_BBLOCK, 'vocabulary-labels')('{}'))
used_vocabularies = {}

# Scheme, members and the source-specific membership checks are shared with the other WA strata reports.
resolution = json.loads(get_transformer(ADAPTER_BBLOCK, 'resolve-scheme')(input_data))
scheme_ptr = resolution['scheme']['pointer']
scheme = _resolve(csd, scheme_ptr)
scheme_props = scheme.get('properties') or {}
scheme_number = resolution['scheme']['schemeNumber']

lots = []
for member in resolution['members']:
    if member['pointer'] is None:
        entitlement = _value('unresolved', refs=[member['ref']], note=member['note'])
    else:
        entitlement = _parcel_number(member['pointer'], _resolve(csd, member['pointer']),
                                     'entitlementPortion', RETIRED_LOT_INTEREST_TYPE)
    lots.append({'lotNumber': member['lotNumber'], 'entitlement': entitlement, 'ref': member['ref'],
                 'membershipEvidence': member['membershipEvidence']})
position = {member['id']: i for i, member in enumerate(resolution['members'])}

# --- Source-specific checks ---------------------------------------------------------------------------
checks = [_targeted(check, position) for check in resolution['checks']]
non_integers = [f'/content/lots/{i}/entitlement' for i, lot in enumerate(lots)
                if lot['entitlement']['status'] == 'reported' and 'lexicalValue' in lot['entitlement']]
checks.insert(-1, _check(  # before scheme-number-consistent, which resolve-scheme reports last
    'entitlement-source-datatype', 'source-conformance', 'info', not non_integers,
    'Every entitlementPortion is an integer, as the WA built-strata scope note requires' if not non_integers
    else f'{len(non_integers)} entitlementPortion value(s) are strings; the WA built-strata scope note types '
         'them as integers (converted to integers here)',
    targets=non_integers))

# --- Basis of the schedule: schedule document, approved form, certification, legislation ---------------
documents, annotations, basis, legislative_basis = [], [], {}, []
supporting = [d for d in csd.get('supportingDocuments') or [] if isinstance(d, dict)]
schedule_index = next((i for i, d in enumerate(supporting) if d.get('role') == SCHEDULE_ROLE), None)
if schedule_index is not None:
    schedule = supporting[schedule_index]
    documents.append(_document(schedule_index, schedule, 'unit-entitlement-schedule'))
    basis['schedule'] = {'documentRef': 'unit-entitlement-schedule'}
    form = schedule.get('conformsTo')
    if form:
        basis['schedule']['conformsTo'] = form
        form_ptr = _pointer('supportingDocuments', schedule_index, 'conformsTo')
        valid = _vocabulary_value(form, 'valid', form_ptr, 'validity')
        if valid['value'] is not None:  # dcterms:valid is a period such as "2021-07-07/.."; keep its start
            valid = {**valid, 'value': valid['value'].split('/')[0], 'lexicalValue': valid['value']}
        basis['form'] = {
            'id': form,
            'label': _vocabulary_value(form, 'prefLabel', form_ptr, 'label'),
            'validFrom': valid,
            'source': _vocabulary_value(form, 'source', form_ptr, 'source'),
        }
        legislative_basis.append(_vocabulary_value(form, 'scopeNote', form_ptr, 'legislation (scope note)'))

annotation_index = next((i for i, a in enumerate(csd.get('annotations') or [])
                         if isinstance(a, dict) and a.get('role') in CERTIFICATION_ROLES), None)
if annotation_index is not None:
    annotation = csd['annotations'][annotation_index]
    annotation_ptr = _pointer('annotations', annotation_index)
    linked = None
    if annotation.get('href'):
        linked_index = next((i for i, d in enumerate(supporting) if d.get('href') == annotation['href']), None)
        if linked_index is not None:
            linked = next((d['id'] for d in documents if d['sourceRef']['pointer'] == _pointer('supportingDocuments', linked_index)), None)
            if linked is None:
                linked = f'document-{linked_index + 1}'
                documents.append(_document(linked_index, supporting[linked_index], linked))
    reference = {'id': 'licensed-valuer-certification', 'role': annotation.get('role'),
                 'statement': annotation.get('description'), 'href': annotation.get('href'),
                 'rel': annotation.get('rel'), 'documentRef': linked, 'sourceRef': _ref(annotation_ptr)}
    annotations.append({k: v for k, v in reference.items() if v is not None})
    certifier = annotation.get('certifier') if isinstance(annotation.get('certifier'), dict) else {}
    certifier_ptr = annotation_ptr + _pointer('certifier')
    basis['certification'] = {
        'annotationRef': 'licensed-valuer-certification',
        'certifier': {
            'firstName': _text(certifier, 'firstName', certifier_ptr, "certifier's first name"),
            'lastName': _text(certifier, 'lastName', certifier_ptr, "certifier's last name"),
            'licensedValuerNumber': _text(certifier, 'licensedValuerNumber', certifier_ptr, 'licensed valuer number'),
        },
        'dateCertified': _text(annotation, 'dateCertified', annotation_ptr, 'certification date'),
    }
    if linked:
        basis['certification']['documentRef'] = linked

address = _address(scheme_ptr, scheme_props)
sources = [resolution['source']]
sources += [{'id': v['scheme'], 'kind': 'vocabulary', 'name': v.get('title') or prefix}
            for prefix, v in sorted(used_vocabularies.items())]

report = {
    'reportType': REPORT_TYPE,
    'stage': 'facts',
    'generatedBy': [{'bblock': ADAPTER_BBLOCK, 'transform': 'to-strata-entitlement-facts'}],
    'subject': {
        'kind': 'strata-scheme',
        'label': resolution['scheme']['label'],
        'ref': resolution['scheme']['ref'],
    },
    'sources': [{k: v for k, v in source.items() if v is not None} for source in sources],
    'documents': documents,
    'annotations': annotations,
    'content': {
        'scheme': {
            'schemeNumber': scheme_number,
            'schemeName': _text(scheme_props, 'schemeName', scheme_ptr + _pointer('properties'), 'schemeName'),
            'address': address,
            'ref': resolution['scheme']['ref'],
        },
        'lots': lots,
        'basis': basis,
        'legislativeBasis': legislative_basis,
        'totals': {
            'declared': _parcel_number(scheme_ptr, scheme, 'entitlementTotal', RETIRED_SCHEME_INTEREST_TYPE),
        },
    },
    'checks': checks,
}
# Drop empty optional fields so the report never carries nulls it does not need.
if report['subject']['label'] is None:
    del report['subject']['label']

output_data = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
