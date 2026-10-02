# Cadastral reporting vocabulary

The RDF vocabulary behind cadastral reports.
It defines only what existing vocabularies do not provide; the [JSON-LD](https://www.w3.org/TR/json-ld11/) context of `csdm.reporting.cadastral-report` maps everything else to reused terms.

| Report element | RDF |
|---|---|
| Report | `cr:CadastralReport` (a [`prov:Entity`](https://www.w3.org/TR/prov-o/)); `cr:reportType`, `cr:stage`, `cr:reportStatus`, `cr:content` |
| Report value | `cr:ReportValue`: `rdf:value`, `cr:valueStatus`, `cr:sourceRef`, `cr:derivation`, `cr:lexicalValue`, `rdfs:comment` |
| Source reference | `cr:SourceReference`: `cr:sourceDataset`, `cr:jsonPointer`, `cr:sourceObject`, `cr:sourceProperty` (the source's own property IRI, e.g. [LADM](https://ogcincubator.github.io/bblocks-land-parcels/bblock/ogc.ladm.land-parcels.ontology) `entitlementPortion`) |
| Check result | `cr:CheckResult` (close to [`earl:Assertion`](https://www.w3.org/TR/EARL10-Schema/)): `earl:outcome` (`earl:passed`, `failed`, `untested`, `inapplicable`), `sh:resultSeverity` (`sh:Violation`, `Warning`, `Info`), `cr:checkCategory`, `dcterms:description` |
| Documents, annotations | `dcterms:references` → `cr:DocumentReference` (`dcterms:title`, `schema:url`, `dcterms:format`, `dcterms:conformsTo`); `cr:annotation` → `cr:AnnotationReference` |
| Sources, pipeline | `dcterms:source`; `prov:wasGeneratedBy` → `cr:PipelineStep` (`cr:buildingBlock`, `cr:transform`) |

Codelists (`data.ttl`, [SKOS](https://www.w3.org/TR/skos-reference/)): report stage, report status, report value status, check category.
Each concept's `skos:notation` is the value used in JSON reports.

Namespaces: `cr:` = `https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/`; codelists under `…/def/report-stage/`, `…/def/report-status/`, `…/def/value-status/` and `…/def/check-category/`.
These resolve once the register is published on the ogcincubator GitHub Pages site.

Report-type specific terms are defined with their report type (for example the `se:` terms of `csdm.reporting.reports.strata-entitlement`).
