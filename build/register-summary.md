# Cadastral Reporting Building Blocks

Reusable building blocks for transforming cadastral data into structured, validated cadastral reports,
proven first with a Strata Scheme Entitlement Report generated from the WA profile of the 3D CSDM.


Cadastral source data is interpreted by **source adapters**, which produce a facts-stage report.
Report-type blocks complete the report (derived values and domain checks) and generic
**cadastral-report** components carry provenance, status and presentation (HTML, CSV).
See `docs/cadastral-reporting-investigation-and-plan.md` in the repository for the architecture and plan.


## Building Blocks

### `csdm.reporting.cadastral-report-ontology` — Cadastral reporting vocabulary

**Type:** model

RDF vocabulary for cadastral reports: the classes and properties a generic cadastral report needs that existing vocabularies do not provide, and the SKOS codelists for report stage, report status, value status and check category. Reused terms (RDF, RDFS, Dublin Core, PROV-O, EARL, SHACL, schema.org) are not redefined.

### `csdm.reporting.cadastral-report` — Cadastral report

**Type:** schema

Generic envelope for structured cadastral reports: report type, subject, source datasets and a report-specific content section. Report-type building blocks extend it; it knows nothing about any jurisdiction, source format or report type.

### `csdm.reporting.reports.scheme-composition` — Scheme Composition Report

**Type:** schema

Structured report of what a strata scheme is made of: its member lots, how each is spatially represented, and a summary (member count, geometry types, representation statuses, whether every member is spatially resolved). The second report type of the register, built to test that the generic cadastral-report block serves more than one report.

### `csdm.reporting.reports.strata-entitlement` — Strata Scheme Entitlement Report

**Type:** schema

Structured report of the unit entitlement of every lot in a strata scheme, with the calculated total. Independent of the source data format: source adapters produce it, and its own transforms present it.

### `csdm.reporting.adapters.wa-csdm` — WA 3D CSDM reporting adapter

**Type:** schema

Interprets cadastral survey datasets that follow the WA profile of the 3D CSDM (built strata) and extracts the source facts needed by cadastral reports. This is the only reporting block that knows CSDM paths and WA vocabularies.

