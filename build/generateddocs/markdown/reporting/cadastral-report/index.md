
# Cadastral report (Schema)

`csdm.reporting.cadastral-report` *v0.1*

Generic envelope for structured cadastral reports: report type, subject, source datasets and a report-specific content section. Report-type building blocks extend it; it knows nothing about any jurisdiction, source format or report type.

[*Status*](http://www.opengis.net/def/status): Under development

## Description

# Cadastral report

The generic envelope shared by every cadastral report type in this register.
It records:

- **`reportType`:** the report-type building block that defines `content` (for example `csdm.reporting.reports.strata-entitlement`).
- **`stage`:** `facts` when the report holds source facts only (the output of a source adapter), or `complete` once the report-type block has added derived values.
  One schema covers both stages, so the boundary between source interpretation and report semantics is checked by validation.
- **`subject`:** the cadastral object the report is about, with a reference back into the source dataset.
- **`sources`:** what the report draws on: the source dataset (`kind: dataset`, with the profile it follows) and any vocabularies used to label its codes (`kind: vocabulary`).
- **`documents`:** the supporting documents the report relies on (`DocumentReference`: title, href, media type, role, the form it conforms to, and where the source lists it).
- **`annotations`:** the source annotations the report relies on, such as a certification (`AnnotationReference`: role, verbatim statement, link, and the document it links to).
- **`checks`:** the result of every check run while generating the report.
- **`status`:** the overall result (`complete`, `incomplete` or `invalid`), set from the checks.
- **`generatedBy`:** the pipeline steps (building block + transform) that produced the report.
- **`content`:** report-type specific content.

Source references use a dataset identifier plus a [JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901), so any value can be traced back to the object it came from, whatever the source format.
A value taken from a vocabulary names the concept scheme as its `dataset`, the concept IRI as its `id`, and an empty `pointer`.

## Report values: provenance and status

Report types use `ReportValue` (`#/$defs/ReportValue`, anchor `ReportValue`) for every value whose origin matters.
A `ReportValue` holds the `value` and its `status`, plus the provenance that status needs:

| Status | Meaning | Value | Provenance required |
|---|---|---|---|
| `reported` | Read from the source (original kept as `lexicalValue` if converted) | yes | `sourceRefs` |
| `derived` | Calculated from other report values | yes | `derivation` (`method`, `inputs` as report pointers) |
| `documented` | Known only from a referenced supporting document | yes | `documentRef` |
| `configured` | A constant of the report type | yes | |
| `not-supplied` | Expected but absent from the source | no | (`sourceRefs` say where it was looked for) |
| `unresolved` | A reference to it could not be followed | no | `sourceRefs` |
| `invalid` | Supplied, but not usable as the required kind of value | no | `sourceRefs`, `lexicalValue` |
| `conflicting` | Sources disagree | no | at least two `sourceRefs` |

Missing or unusable data is therefore never silent, and never a reason to stop generating a report: it appears in the report with its status.
The statuses are published as a [SKOS](https://www.w3.org/TR/skos-reference/) codelist in `csdm.reporting.cadastral-report-ontology`.
`invalid` is an addition to the statuses proposed in the investigation, for supplied values that cannot be used (for example a fractional unit entitlement).

## Checks and report status

Each `Check` records who defined it (`definedBy`), its `category` (`source-conformance`, `generation` or `domain`), its `severity` (`error`, `warning`, `info`), its `outcome` (`pass`, `fail`, `not-evaluated`, `not-applicable`), a message, and pointers to the report values it concerns (`targets`).

The generic `summarise-checks` transform sets the report `status` from the checks, the same way for every report type:

| Status | When |
|---|---|
| `invalid` | any `error` check fails: the report's information is wrong or inconsistent |
| `incomplete` | otherwise, any `warning` check fails, or an `error` check could not be evaluated: information is missing |
| `complete` | otherwise (`info` results never change the status) |

The counts behind the status are kept in `statusSummary`.
A completed report must have `status` and `checks`; a facts-stage report may carry checks (from the source adapter) but no `status`.

## Transforms

- **`summarise-checks`:** sets `status` and `statusSummary` from `checks` on a complete-stage report.
  Report-type blocks call it with `get_transformer()` when they complete a report.
- **`render-html`:** renders any report as a standalone HTML page with Jinja2.
  It draws everything that is common to report types: the title and report status, the sources (datasets and vocabularies), a status marker for every `ReportValue` (hover it for the source pointer, vocabulary concept or derivation) and a legend, the documents relied on, the check results, and the pipeline (`generatedBy`).
  A report type adds only its body, as a Jinja2 template passed in the transform metadata:

  ```python
  render_html = get_transformer('csdm.reporting.cadastral-report', 'render-html')
  output_data = render_html(input_data, extra_metadata={'template': TEMPLATE})
  ```

  The template extends `base.html` (blocks `title`, `heading`, `body`) and can use `rv(value)`, `doc_link(id)`, `dl(id)` with `dt_dd(label, value, id)`, and the variables `report`, `content`, `documents` and `annotations` (by id).
  Without a template the page shows the envelope only.
  Values are shown as text: lists comma-separated (an empty list as "none") and booleans as yes/no.
  Needs `jinja2` (declared as the transform's pip dependency).

## Semantics (RDF)

Reports uplift to [RDF](https://www.w3.org/TR/rdf11-concepts/) with this block's `context.jsonld`.
It reuses standard terms where they fit and uses the cadastral reporting vocabulary (`csdm.reporting.cadastral-report-ontology`, prefix `cr:`) for the rest:

| JSON | RDF |
|---|---|
| `reportType`, `stage`, `status` | `cr:reportType`; `cr:stage` and `cr:reportStatus` (codelist concepts) |
| `checks[]` | `cr:check`: [`earl:outcome`](https://www.w3.org/TR/EARL10-Schema/) (`earl:passed`, `failed`, `untested`, `inapplicable`), [`sh:resultSeverity`](https://www.w3.org/TR/shacl/#results-severity) (`sh:Violation`, `Warning`, `Info`), `cr:checkCategory`, [`dcterms:description`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) |
| a `ReportValue` | `rdf:value`, `cr:valueStatus` (codelist concept), `cr:sourceRef`, `cr:derivation`, `cr:lexicalValue`, `rdfs:comment` |
| `SourceRef` | `cr:sourceDataset`, `cr:jsonPointer`, `cr:sourceObject`, `cr:sourceProperty` |
| `sources`, `documents`, `annotations`, `generatedBy` | `dcterms:source`, `dcterms:references`, `cr:annotation`, [`prov:wasGeneratedBy`](https://www.w3.org/TR/prov-o/) |

`SourceRef.property` names the source property a value was read from, using the source's own semantics: for example a strata lot's unit entitlement links to [LADM](https://ogcincubator.github.io/bblocks-land-parcels/bblock/ogc.ladm.land-parcels.ontology)'s `https://w3id.org/ogc/ladm/parcels/entitlementPortion`.
Adapters set it only where the source profile defines the property's IRI.

`shapes.shacl` holds the cross-field rules every report must meet, checked after uplift:

- **`cr:ReportStatusFollowsFromChecks`:** the report `status` is the one its check results imply.
- **`cr:DocumentAndAnnotationReferencesResolve`:** every `documentRef` and `annotationRef` names a document or annotation the report carries.

The vocabulary block adds shapes for its own terms (codelist membership, cardinalities).

This block is deliberately free of jurisdiction, source-format and report-type knowledge.

## Examples

### Minimal report envelope
The smallest valid complete report: a report type, its stage and status, its check results, a
subject that points back into its source dataset, one source dataset and an (empty) report-specific
`content` section. The `summarise-checks` transform recalculates `status` from the checks: one
`warning` check failed, so the report is `incomplete`.

#### json
```json
{
  "reportType": "example.report-type",
  "stage": "complete",
  "status": "incomplete",
  "checks": [
    {"id": "subject-identified", "definedBy": "example.adapter", "category": "generation",
     "severity": "error", "outcome": "pass", "message": "One parcel identified as the subject"},
    {"id": "area-present", "definedBy": "example.report-type", "category": "domain",
     "severity": "warning", "outcome": "fail", "message": "The parcel has no area",
     "targets": ["/content"]}
  ],
  "subject": {
    "kind": "parcel",
    "label": "Lot 1 on Plan DP 1",
    "ref": {"dataset": "example-dataset", "pointer": "/parcels/0/features/0", "id": "uuid:parcel-1"}
  },
  "sources": [{"id": "example-dataset", "name": "DP 1", "conformsTo": "example.profile"}],
  "content": {}
}

```


### Report values with their statuses
A minimal facts-stage report whose content holds four `ReportValue`s, one per common status:
`reported` (read from the source; the supplied text `"117"` is kept as `lexicalValue` because the
report holds an integer), `derived` (calculated from other report values, which `derivation.inputs`
points at), `not-supplied` (expected but absent; `sourceRefs` says where it was looked for) and
`invalid` (supplied but unusable; the supplied value is kept). The content keys are illustrative:
report types define (and map to RDF) their own content.

#### json
```json
{
  "reportType": "example.report-type",
  "stage": "facts",
  "subject": {"kind": "strata-scheme", "ref": {"dataset": "SP-1", "pointer": "/parcels/0/features/1"}},
  "sources": [{"id": "SP-1", "kind": "dataset"}],
  "content": {
    "reportedValue": {
      "value": 117, "status": "reported", "lexicalValue": "117",
      "sourceRefs": [{"dataset": "SP-1", "pointer": "/parcels/0/features/2/properties/interests/0/entitlementPortion"}]
    },
    "derivedValue": {
      "value": 225, "status": "derived",
      "derivation": {"method": "sum", "inputs": ["/content/reportedValue", "/content/invalidValue"]}
    },
    "notSuppliedValue": {
      "value": null, "status": "not-supplied",
      "sourceRefs": [{"dataset": "SP-1", "pointer": "/parcels/0/features/5"}],
      "note": "No interest with interestType wa-interest-type:strata-lot and an entitlementPortion"
    },
    "invalidValue": {
      "value": null, "status": "invalid", "lexicalValue": "12.5",
      "sourceRefs": [{"dataset": "SP-1", "pointer": "/parcels/0/features/3/properties/interests/0/entitlementPortion"}],
      "note": "Not a positive whole number"
    }
  }
}

```

## Schema

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
description: 'Generic cadastral report envelope. Report-type building blocks extend
  this schema and define

  `content`, using `ReportValue` for every value whose provenance matters, `Check`
  for every check result,

  and `DocumentReference` / `AnnotationReference` for the supporting documents and
  annotations the report

  relies on. Stage 5 of the implementation plan.

  '
type: object
required:
- reportType
- stage
- subject
- sources
- content
properties:
  reportType:
    description: Identifier of the report-type building block that defines `content`.
    type: string
    minLength: 1
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/reportType
  stage:
    description: '`facts`: source facts only, as produced by a source adapter. `complete`:
      derived values added by

      the report-type building block. Both stages share this schema; report types
      state which members

      each stage requires.

      '
    enum:
    - facts
    - complete
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/stage
    x-jsonld-type: '@vocab'
    x-jsonld-vocab: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-stage/
  status:
    description: 'Overall report status, set from the check results by the generic
      `summarise-checks` transform when

      the report is completed: `invalid` if any `error` check fails; otherwise `incomplete`
      if any

      `warning` check fails or any `error` check could not be evaluated; otherwise
      `complete`.

      '
    enum:
    - complete
    - incomplete
    - invalid
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/reportStatus
    x-jsonld-type: '@vocab'
    x-jsonld-vocab: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-status/
  statusSummary:
    description: Counts behind `status`, recorded by `summarise-checks`.
    type: object
    properties:
      checks:
        type: integer
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/checkCount
      failedErrors:
        type: integer
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/failedErrors
      failedWarnings:
        type: integer
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/failedWarnings
      unevaluatedErrors:
        type: integer
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/unevaluatedErrors
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/statusSummary
  checks:
    description: Results of the checks run while generating the report (source adapter
      and report type).
    type: array
    items:
      $ref: '#/$defs/Check'
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/check
    x-jsonld-container: '@set'
  generatedBy:
    description: Pipeline steps that produced this report, in order.
    type: array
    items:
      type: object
      required:
      - bblock
      - transform
      properties:
        bblock:
          type: string
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/buildingBlock
        transform:
          type: string
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/transform
    x-jsonld-id: http://www.w3.org/ns/prov#wasGeneratedBy
    x-jsonld-container: '@list'
  subject:
    description: The cadastral object the report is about (for example a strata scheme
      or a parcel).
    type: object
    required:
    - kind
    - ref
    properties:
      kind:
        description: Kind of subject, for example `strata-scheme`.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/kind
      label:
        type: string
        x-jsonld-id: http://www.w3.org/2000/01/rdf-schema#label
      ref:
        $ref: '#/$defs/SourceRef'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
    x-jsonld-id: http://purl.org/dc/terms/subject
  sources:
    description: Source datasets the report was generated from.
    type: array
    minItems: 1
    items:
      $ref: '#/$defs/SourceDataset'
    x-jsonld-id: http://purl.org/dc/terms/source
    x-jsonld-container: '@set'
  documents:
    description: Supporting documents the report relies on (not every document of
      the source dataset).
    type: array
    items:
      $ref: '#/$defs/DocumentReference'
    x-jsonld-id: http://purl.org/dc/terms/references
    x-jsonld-container: '@set'
  annotations:
    description: Source annotations the report relies on (for example a certification).
    type: array
    items:
      $ref: '#/$defs/AnnotationReference'
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/annotation
    x-jsonld-container: '@set'
  content:
    description: Report-type specific content, defined by the report-type building
      block.
    type: object
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/content
    x-jsonld-extra-terms:
      status:
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/valueStatus
        x-jsonld-type: '@vocab'
        x-jsonld-context:
          '@vocab': https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/value-status/
allOf:
- if:
    required:
    - stage
    properties:
      stage:
        const: complete
  then:
    required:
    - status
    - checks
  else:
    not:
      required:
      - status
$defs:
  Check:
    $anchor: Check
    description: The result of one check on the source data or the report.
    type: object
    x-jsonld-extra-terms:
      pass: http://www.w3.org/ns/earl#passed
      fail: http://www.w3.org/ns/earl#failed
      not-evaluated: http://www.w3.org/ns/earl#untested
      not-applicable: http://www.w3.org/ns/earl#inapplicable
      error: http://www.w3.org/ns/shacl#Violation
      warning: http://www.w3.org/ns/shacl#Warning
      info: http://www.w3.org/ns/shacl#Info
    required:
    - id
    - definedBy
    - category
    - severity
    - outcome
    - message
    properties:
      id:
        description: Identifier of the check, unique within the building block that
          defines it.
        type: string
        pattern: ^[a-z][a-z0-9-]*$
        x-jsonld-id: http://purl.org/dc/terms/identifier
      definedBy:
        description: Identifier of the building block that defines (and ran) the check.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/definedBy
      category:
        description: '`source-conformance`: the source against its own profile. `generation`:
          what the report needs

          to be generated. `domain`: business rules of the report type.

          '
        enum:
        - source-conformance
        - generation
        - domain
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/checkCategory
        x-jsonld-type: '@vocab'
        x-jsonld-vocab: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/check-category/
      severity:
        enum:
        - error
        - warning
        - info
        x-jsonld-id: http://www.w3.org/ns/shacl#resultSeverity
        x-jsonld-type: '@vocab'
      outcome:
        enum:
        - pass
        - fail
        - not-evaluated
        - not-applicable
        x-jsonld-id: http://www.w3.org/ns/earl#outcome
        x-jsonld-type: '@vocab'
      message:
        type: string
        minLength: 1
        x-jsonld-id: http://purl.org/dc/terms/description
      targets:
        description: Pointers to the report values the check is about.
        type: array
        items:
          $ref: '#/$defs/ReportPointer'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/target
        x-jsonld-container: '@set'
      evidence:
        description: Small structured detail, for example the expected and actual
          values.
        type: object
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/evidence
        x-jsonld-type: '@json'
  SourceRef:
    $anchor: SourceRef
    description: Reference to an object in a source dataset.
    type: object
    required:
    - dataset
    - pointer
    properties:
      dataset:
        description: Identifier of the source dataset (matches a `sources[].id`).
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceDataset
      pointer:
        description: JSON Pointer (RFC 6901) to the object within the source dataset.
        type: string
        pattern: ^(/([^/~]|~[01])*)*$
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/jsonPointer
      id:
        description: Identifier of the object in the source dataset, when it has one.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceObject
      property:
        description: 'IRI of the source property the value was read from, as defined
          by the source dataset''s own

          semantics (for example `https://w3id.org/ogc/ladm/parcels/entitlementPortion`).
          Given only when

          the source profile defines one.

          '
        type: string
        format: iri
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceProperty
        x-jsonld-type: '@id'
  SourceDataset:
    $anchor: SourceDataset
    description: 'A source the report draws on: the cadastral dataset itself, or a
      vocabulary used to label its codes.

      `SourceRef.dataset` refers to `id`. For a vocabulary, `id` is the concept scheme
      IRI and a

      `SourceRef` names the concept in `id` (with an empty `pointer`).

      '
    type: object
    required:
    - id
    properties:
      id:
        type: string
        x-jsonld-id: http://purl.org/dc/terms/identifier
      kind:
        enum:
        - dataset
        - vocabulary
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/kind
      name:
        type: string
        x-jsonld-id: http://www.w3.org/2000/01/rdf-schema#label
      date:
        type: string
        x-jsonld-id: http://purl.org/dc/terms/date
      conformsTo:
        description: Identifier of the profile or specification the dataset follows.
        type: string
        x-jsonld-id: http://purl.org/dc/terms/conformsTo
  DocumentReference:
    $anchor: DocumentReference
    description: A supporting document referenced by the source dataset.
    type: object
    required:
    - id
    - href
    - sourceRef
    properties:
      id:
        description: Identifier of the document within this report (used by `documentRef`).
        type: string
        pattern: ^[A-Za-z][A-Za-z0-9._-]*$
        x-jsonld-id: http://purl.org/dc/terms/identifier
      title:
        type: string
        x-jsonld-id: http://purl.org/dc/terms/title
      href:
        description: Link to the document, as given by the source (may be relative).
        type: string
        x-jsonld-id: https://schema.org/url
      mediaType:
        type: string
        x-jsonld-id: http://purl.org/dc/terms/format
      role:
        description: Role of the document, as given by the source (an IRI or CURIE).
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/role
      conformsTo:
        description: Specification or approved form the document follows (an IRI or
          CURIE).
        type: string
        x-jsonld-id: http://purl.org/dc/terms/conformsTo
      sourceRef:
        $ref: '#/$defs/SourceRef'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
  AnnotationReference:
    $anchor: AnnotationReference
    description: An annotation of the source dataset (a statement made on the plan
      or survey).
    type: object
    required:
    - id
    - role
    - sourceRef
    properties:
      id:
        description: Identifier of the annotation within this report (used by `annotationRef`).
        type: string
        pattern: ^[A-Za-z][A-Za-z0-9._-]*$
        x-jsonld-id: http://purl.org/dc/terms/identifier
      role:
        description: Role of the annotation, as given by the source (an IRI or CURIE).
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/role
      statement:
        description: The annotation text, verbatim.
        type: string
        x-jsonld-id: http://purl.org/dc/terms/description
      href:
        type: string
        x-jsonld-id: https://schema.org/url
      rel:
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/linkRelation
      documentRef:
        description: The document in `documents` that the annotation links to, if
          any.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/documentRef
      sourceRef:
        $ref: '#/$defs/SourceRef'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
  ReportPointer:
    $anchor: ReportPointer
    description: JSON Pointer (RFC 6901) to a value within this report.
    type: string
    pattern: ^(/([^/~]|~[01])*)*$
  ReportValue:
    $anchor: ReportValue
    description: 'A report value together with its provenance and status. Report-type
      building blocks constrain

      `value` (for example to a positive integer); this definition fixes which provenance
      each status

      needs:


      | status | value | also required |

      |---|---|---|

      | `reported` | present | `sourceRefs`: where the value was read |

      | `derived` | present | `derivation`: method and the report values it was calculated
      from |

      | `documented` | present | `documentRef`: the supporting document it comes from
      |

      | `configured` | present | (a report-type constant) |

      | `not-supplied` | null or absent | (`sourceRefs`, when given, say where it
      was looked for) |

      | `unresolved` | null or absent | `sourceRefs`: the reference that could not
      be followed |

      | `invalid` | null or absent | `sourceRefs` and `lexicalValue`: the unusable
      value as supplied |

      | `conflicting` | null or absent | at least two `sourceRefs` that disagree |

      '
    type: object
    required:
    - status
    properties:
      value:
        description: The value, or null when there is no usable value (see `status`).
        x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
      status:
        description: Where the value comes from, or why there is none. Codelist in
          this block's `data.ttl`.
        enum:
        - reported
        - derived
        - documented
        - configured
        - not-supplied
        - unresolved
        - invalid
        - conflicting
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/reportStatus
        x-jsonld-type: '@vocab'
        x-jsonld-vocab: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-status/
      sourceRefs:
        type: array
        minItems: 1
        items:
          $ref: '#/$defs/SourceRef'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
        x-jsonld-container: '@set'
      derivation:
        type: object
        required:
        - method
        - inputs
        properties:
          method:
            description: How the value was calculated, for example `sum` or `count`.
            type: string
            minLength: 1
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivationMethod
          inputs:
            description: Pointers to the report values the calculation used.
            type: array
            items:
              $ref: '#/$defs/ReportPointer'
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivationInput
            x-jsonld-container: '@set'
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivation
      documentRef:
        description: Identifier of the supporting document the value was obtained
          from.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/documentRef
      lexicalValue:
        description: The value exactly as it appears in the source, when it differs
          from `value`.
        type: string
        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/lexicalValue
      note:
        type: string
        x-jsonld-id: http://www.w3.org/2000/01/rdf-schema#comment
    allOf:
    - if:
        properties:
          status:
            enum:
            - reported
            - derived
            - documented
            - configured
      then:
        required:
        - value
        properties:
          value:
            not:
              type: 'null'
            x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
      else:
        properties:
          value:
            type: 'null'
            x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
    - if:
        properties:
          status:
            const: reported
      then:
        required:
        - sourceRefs
    - if:
        properties:
          status:
            const: derived
      then:
        required:
        - derivation
    - if:
        properties:
          status:
            const: documented
      then:
        required:
        - documentRef
    - if:
        properties:
          status:
            const: unresolved
      then:
        required:
        - sourceRefs
    - if:
        properties:
          status:
            const: invalid
      then:
        required:
        - sourceRefs
        - lexicalValue
    - if:
        properties:
          status:
            const: conflicting
      then:
        required:
        - sourceRefs
        properties:
          sourceRefs:
            minItems: 2
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
            x-jsonld-container: '@set'
x-jsonld-extra-terms:
  annotationRef: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/annotationRef
  value: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
  derivation: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivation
  method: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivationMethod
  inputs:
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/derivationInput
    x-jsonld-container: '@set'
  lexicalValue: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/lexicalValue
  note: http://www.w3.org/2000/01/rdf-schema#comment
  sourceRefs:
    x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
    x-jsonld-container: '@set'
x-jsonld-prefixes:
  cr: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/
  sh: http://www.w3.org/ns/shacl#
  earl: http://www.w3.org/ns/earl#
  dcterms: http://purl.org/dc/terms/
  prov: http://www.w3.org/ns/prov#
  rdfs: http://www.w3.org/2000/01/rdf-schema#
  schema: https://schema.org/
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  xsd: http://www.w3.org/2001/XMLSchema#

```

Links to the schema:

* YAML version: [schema.yaml](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.json)
* JSON version: [schema.json](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml)


# JSON-LD Context

```jsonld
{
  "@context": {
    "annotationRef": "cr:annotationRef",
    "value": "rdf:value",
    "derivation": "cr:derivation",
    "method": "cr:derivationMethod",
    "inputs": {
      "@id": "cr:derivationInput",
      "@container": "@set"
    },
    "lexicalValue": "cr:lexicalValue",
    "note": "rdfs:comment",
    "sourceRefs": {
      "@id": "cr:sourceRef",
      "@container": "@set"
    },
    "reportType": "cr:reportType",
    "stage": {
      "@context": {
        "@vocab": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-stage/"
      },
      "@id": "cr:stage",
      "@type": "@vocab"
    },
    "status": {
      "@context": {
        "@vocab": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-status/"
      },
      "@id": "cr:reportStatus",
      "@type": "@vocab"
    },
    "statusSummary": {
      "@context": {
        "checks": "cr:checkCount",
        "failedErrors": "cr:failedErrors",
        "failedWarnings": "cr:failedWarnings",
        "unevaluatedErrors": "cr:unevaluatedErrors"
      },
      "@id": "cr:statusSummary"
    },
    "checks": {
      "@context": {
        "pass": "earl:passed",
        "fail": "earl:failed",
        "not-evaluated": "earl:untested",
        "not-applicable": "earl:inapplicable",
        "error": "sh:Violation",
        "warning": "sh:Warning",
        "info": "sh:Info",
        "id": "dcterms:identifier",
        "definedBy": "cr:definedBy",
        "category": {
          "@context": {
            "@vocab": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/check-category/"
          },
          "@id": "cr:checkCategory",
          "@type": "@vocab"
        },
        "severity": {
          "@id": "sh:resultSeverity",
          "@type": "@vocab"
        },
        "outcome": {
          "@id": "earl:outcome",
          "@type": "@vocab"
        },
        "message": "dcterms:description",
        "targets": {
          "@id": "cr:target",
          "@container": "@set"
        },
        "evidence": {
          "@id": "cr:evidence",
          "@type": "@json"
        }
      },
      "@id": "cr:check",
      "@container": "@set"
    },
    "generatedBy": {
      "@context": {
        "bblock": "cr:buildingBlock",
        "transform": "cr:transform"
      },
      "@id": "prov:wasGeneratedBy",
      "@container": "@list"
    },
    "subject": {
      "@context": {
        "kind": "cr:kind",
        "label": "rdfs:label",
        "ref": {
          "@context": {
            "dataset": "cr:sourceDataset",
            "pointer": "cr:jsonPointer",
            "id": "cr:sourceObject",
            "property": {
              "@id": "cr:sourceProperty",
              "@type": "@id"
            }
          },
          "@id": "cr:sourceRef"
        }
      },
      "@id": "dcterms:subject"
    },
    "sources": {
      "@context": {
        "id": "dcterms:identifier",
        "kind": "cr:kind",
        "name": "rdfs:label",
        "date": "dcterms:date",
        "conformsTo": "dcterms:conformsTo"
      },
      "@id": "dcterms:source",
      "@container": "@set"
    },
    "documents": {
      "@context": {
        "id": "dcterms:identifier",
        "title": "dcterms:title",
        "href": "schema:url",
        "mediaType": "dcterms:format",
        "role": "cr:role",
        "conformsTo": "dcterms:conformsTo",
        "sourceRef": {
          "@context": {
            "dataset": "cr:sourceDataset",
            "pointer": "cr:jsonPointer",
            "id": "cr:sourceObject",
            "property": {
              "@id": "cr:sourceProperty",
              "@type": "@id"
            }
          },
          "@id": "cr:sourceRef"
        }
      },
      "@id": "dcterms:references",
      "@container": "@set"
    },
    "annotations": {
      "@context": {
        "id": "dcterms:identifier",
        "role": "cr:role",
        "statement": "dcterms:description",
        "href": "schema:url",
        "rel": "cr:linkRelation",
        "documentRef": "cr:documentRef",
        "sourceRef": {
          "@context": {
            "dataset": "cr:sourceDataset",
            "pointer": "cr:jsonPointer",
            "id": "cr:sourceObject",
            "property": {
              "@id": "cr:sourceProperty",
              "@type": "@id"
            }
          },
          "@id": "cr:sourceRef"
        }
      },
      "@id": "cr:annotation",
      "@container": "@set"
    },
    "content": {
      "@context": {
        "status": {
          "@id": "cr:valueStatus",
          "@type": "@vocab",
          "@context": {
            "@vocab": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/value-status/"
          }
        }
      },
      "@id": "cr:content"
    },
    "cr": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/",
    "sh": "http://www.w3.org/ns/shacl#",
    "earl": "http://www.w3.org/ns/earl#",
    "dcterms": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema": "https://schema.org/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "@version": 1.1
  }
}
```

You can find the full JSON-LD context here:
[context.jsonld](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/context.jsonld)


# For developers

The source code for this Building Block can be found in the following repository:

* URL: [https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting](https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting)
* Path: `_sources/cadastral-report`

