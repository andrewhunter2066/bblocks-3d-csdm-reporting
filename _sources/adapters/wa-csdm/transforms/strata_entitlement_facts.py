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
# - entitlement: interests[interestType = wa-interest-type:strata-lot].entitlementPortion (D7)
# - declared total: the scheme's interests[interestType = wa-interest-type:strata-scheme].entitlementTotal (D10)
# - address: schemeAddress.hasPart; road label from the apt:road value's `label`, locality label from the
#   wa-locality vocabulary (D8)
# - schedule: supportingDocuments[role = wa-survey-documentation-type:unitEntitlementSchedule]; its
#   conformsTo names the approved form, whose label, validity, source and legislation (scope note) come
#   from the wa-approved-form vocabulary
# - certification: annotations[role = wa-annotation-role:licensed-valuer-certification] (D9)
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
SOURCE_PROFILE = 'icsm.profiles.wa.wa-3d'
LOT_INTEREST_TYPE = 'wa-interest-type:strata-lot'
SCHEME_INTEREST_TYPE = 'wa-interest-type:strata-scheme'
SCHEDULE_ROLE = 'wa-survey-documentation-type:unitEntitlementSchedule'
# Source property IRIs, from the source profile's JSON-LD context (only those it defines). The WA profile
# maps interests[].entitlementPortion to the LADM land-parcels term it inherits.
SOURCE_PROPERTIES = {'entitlementPortion': 'https://w3id.org/ogc/ladm/parcels/entitlementPortion'}
CERTIFICATION_ROLE = 'wa-annotation-role:licensed-valuer-certification'


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


def _interest_number(ptr, feature, interest_type, key):
    """A positive whole number held by the feature's interests of `interest_type` under `key`."""
    candidates = []
    for i, interest in enumerate((feature.get('properties') or {}).get('interests') or []):
        if interest.get('interestType') == interest_type and interest.get(key) is not None:
            candidates.append((ptr + _pointer('properties', 'interests', i, key), interest[key]))
    if not candidates:
        return _value('not-supplied', refs=[_ref(ptr + _pointer('properties', 'interests'))],
                      note=f'No {interest_type} interest with {key}')

    usable = {_positive_integer(raw) for _, raw in candidates} - {None}
    if len(candidates) > 1 and len({_lexical(raw) for _, raw in candidates}) > 1:
        return _value('conflicting', refs=[_ref(p) for p, _ in candidates],
                      note=f'{len(candidates)} {interest_type} interests give different values of {key}')

    pointer, raw = candidates[0]
    if not usable:
        return _value('invalid', refs=[_ref(pointer)], lexical=_lexical(raw),
                      note='Not a positive whole number')
    value = usable.pop()
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
        entitlement = _interest_number(member['pointer'], _resolve(csd, member['pointer']),
                                       LOT_INTEREST_TYPE, 'entitlementPortion')
    lots.append({'lotNumber': member['lotNumber'], 'entitlement': entitlement, 'ref': member['ref'],
                 'membershipEvidence': member['membershipEvidence']})
position = {member['id']: i for i, member in enumerate(resolution['members'])}

# --- Source-specific checks ---------------------------------------------------------------------------
checks = [_targeted(check, position) for check in resolution['checks']]
non_strings = [f'/content/lots/{i}/entitlement' for i, lot in enumerate(lots)
               if lot['entitlement']['status'] == 'reported' and 'lexicalValue' not in lot['entitlement']]
checks.insert(-1, _check(  # before scheme-number-consistent, which resolve-scheme reports last
    'entitlement-source-datatype', 'source-conformance', 'info', not non_strings,
    f'Every entitlementPortion is a string, as {SOURCE_PROFILE} requires' if not non_strings
    else f'{len(non_strings)} entitlementPortion value(s) are numbers; {SOURCE_PROFILE} types them as strings '
         '(converted to integers here)',
    targets=non_strings))

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
                         if isinstance(a, dict) and a.get('role') == CERTIFICATION_ROLE), None)
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
            'declared': _interest_number(scheme_ptr, scheme, SCHEME_INTEREST_TYPE, 'entitlementTotal'),
        },
    },
    'checks': checks,
}
# Drop empty optional fields so the report never carries nulls it does not need.
if report['subject']['label'] is None:
    del report['subject']['label']

output_data = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
