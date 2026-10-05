
# Cadastral reporting vocabulary (Model)

`csdm.reporting.cadastral-report-ontology` *v0.1*

RDF vocabulary for cadastral reports: the classes and properties a generic cadastral report needs that existing vocabularies do not provide, and the SKOS codelists for report stage, report status, value status and check category. Reused terms (RDF, RDFS, Dublin Core, PROV-O, EARL, SHACL, schema.org) are not redefined.

[*Status*](http://www.opengis.net/def/status): Under development

## Description

# Cadastral reporting vocabulary

The [RDF](https://www.w3.org/TR/rdf11-concepts/) vocabulary behind cadastral reports.
It defines only what existing vocabularies do not provide; the [JSON-LD](https://www.w3.org/TR/json-ld11/) context of `csdm.reporting.cadastral-report` maps everything else to reused terms.

| Report element | RDF |
|---|---|
| Report | `cr:CadastralReport` (a [`prov:Entity`](https://www.w3.org/TR/prov-o/)); `cr:reportType`, `cr:stage`, `cr:reportStatus`, `cr:content` |
| Report value | `cr:ReportValue`: `rdf:value`, `cr:valueStatus`, `cr:sourceRef`, `cr:derivation`, `cr:lexicalValue`, `rdfs:comment` |
| Source reference | `cr:SourceReference`: `cr:sourceDataset`, `cr:jsonPointer`, `cr:sourceObject`, `cr:sourceProperty` (the source's own property IRI, e.g. [LADM](https://ogcincubator.github.io/bblocks-land-parcels/bblock/ogc.ladm.land-parcels.ontology) `entitlementPortion`) |
| Check result | `cr:CheckResult` (close to [`earl:Assertion`](https://www.w3.org/TR/EARL10-Schema/)): `earl:outcome` (`earl:passed`, `failed`, `untested`, `inapplicable`), [`sh:resultSeverity`](https://www.w3.org/TR/shacl/#results-severity) (`sh:Violation`, `Warning`, `Info`), `cr:checkCategory`, [`dcterms:description`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) |
| Documents, annotations | `dcterms:references` → `cr:DocumentReference` (`dcterms:title`, [`schema:url`](https://schema.org/url), `dcterms:format`, `dcterms:conformsTo`); `cr:annotation` → `cr:AnnotationReference` |
| Sources, pipeline | `dcterms:source`; `prov:wasGeneratedBy` → `cr:PipelineStep` (`cr:buildingBlock`, `cr:transform`) |

Codelists (`data.ttl`, [SKOS](https://www.w3.org/TR/skos-reference/)): report stage, report status, report value status, check category.
Each concept's `skos:notation` is the value used in JSON reports.

Namespaces: `cr:` = `https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/`; codelists under `…/def/report-stage/`, `…/def/report-status/`, `…/def/value-status/` and `…/def/check-category/`.
These resolve once the register is published on the ogcincubator GitHub Pages site.

Report-type specific terms are defined with their report type (for example the `se:` terms of `csdm.reporting.reports.strata-entitlement`).

## Examples

### A report value and a check result (SP83687)
Lot 1's unit entitlement in the SP83687 Strata Scheme Entitlement Report, and one of its check
results, as RDF. The value is `reported`, and its source reference names the LADM land-parcels
property it was read from. The check outcome and severity reuse EARL and SHACL terms.

#### turtle
```turtle
@prefix cr: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/> .
@prefix ccat: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/check-category/> .
@prefix rstage: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-stage/> .
@prefix rstatus: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/report-status/> .
@prefix vs: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/value-status/> .
@prefix se: <https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix earl: <http://www.w3.org/ns/earl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

[] cr:reportType "csdm.reporting.reports.strata-entitlement" ;
   cr:stage rstage:complete ;
   cr:reportStatus rstatus:complete ;
   cr:content [ se:lot [ se:unitEntitlement [
       rdf:value 117 ;
       cr:valueStatus vs:reported ;
       cr:sourceRef [
           cr:sourceDataset "SP-83687-1-1-0.00" ;
           cr:jsonPointer "/parcels/0/features/2/properties/interests/0/entitlementPortion" ;
           cr:sourceProperty <https://w3id.org/ogc/ladm/parcels/entitlementPortion> ] ] ] ] ;
   cr:check [
       dcterms:identifier "total-matches-declared" ;
       cr:definedBy "csdm.reporting.reports.strata-entitlement" ;
       cr:checkCategory ccat:domain ;
       sh:resultSeverity sh:Violation ;
       earl:outcome earl:passed ;
       dcterms:description "Calculated total 1000 equals the declared total 1000" ] .

```

## Sources

* [csdm.reporting.cadastral-report schema (definitions of the owned elements)](https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting/tree/master/_sources/cadastral-report)
* [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/)
* [Evaluation and Report Language (EARL) 1.0 Schema](https://www.w3.org/TR/EARL10-Schema/)
* [Shapes Constraint Language (SHACL), validation results and severities](https://www.w3.org/TR/shacl/#results-validation-result)
* [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
* [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/)
* [RFC 6901 JavaScript Object Notation (JSON) Pointer](https://www.rfc-editor.org/rfc/rfc6901)

# For developers

The source code for this Building Block can be found in the following repository:

* URL: [https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting](https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting)
* Path: `_sources/cadastral-report-ontology`

