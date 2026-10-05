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
