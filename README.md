# Cadastral Reporting Building Blocks

[OGC Building Blocks](https://ogcincubator.github.io/bblocks-docs/) for transforming cadastral data into structured, validated cadastral reports.
The first report is the **Strata Scheme Entitlement Report**, generated from datasets that follow the [WA profile of the 3D CSDM](https://surroundaustralia.github.io/3d-csdm-profile-wa/).

Source adapters interpret cadastral source data into a facts-stage report.
Report blocks add derived values and domain checks, and a generic `cadastral-report` block carries provenance, status and presentation (HTML, CSV).
The architecture, decisions and staged plan are in [docs/cadastral-reporting-investigation-and-plan.md](docs/cadastral-reporting-investigation-and-plan.md).

## Building blocks

Identifier prefix: `csdm.reporting.`

| Block                                       | Purpose                                                                                                                                                                                                                                                                                                 | Status                                                                                                                                                                                                                                                               |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `csdm.reporting.cadastral-report-ontology`  | RDF vocabulary (`cr:`) and [SKOS](https://www.w3.org/TR/skos-reference/) codelists for cadastral reports; shapes for its own terms                                                                                                                                                                      | Stage 8                                                                                                                                                                                                                                                              |
| `csdm.reporting.cadastral-report`           | Generic report envelope (report type, stage, status, checks, subject, sources, documents, annotations, content), `ReportValue`, `summarise-checks`, the generic Jinja2 `render-html`, a [JSON-LD](https://www.w3.org/TR/json-ld11/) context and cross-field [SHACL](https://www.w3.org/TR/shacl/) rules | Stage 8                                                                                                                                                                                                                                                              |
| `csdm.reporting.reports.strata-entitlement` | Strata Scheme Entitlement Report schema; `complete` (derived values), `to-html` (a template) and `to-csv`                                                                                                                                                                                               | Stage 8: scheme number, name and address; lots and entitlements; declared and calculated totals; the schedule document, approved form, legislation and valuer certification; all with provenance, checks and report status; RDF via `se:` vocabulary and SHACL rules |
| `csdm.reporting.reports.scheme-composition` | Scheme Composition Report: member lots, their spatial representation, and a summary; `complete` and `to-html` (a template)                                                                                                                                                                              | Stage 8: second report type, built on the unchanged generic blocks                                                                                                                                                                                                   |
| `csdm.reporting.adapters.wa-csdm`           | Interprets WA 3D CSDM datasets: shared `resolve-scheme`; facts transforms and compositions for both reports; the generated `vocabulary-labels`                                                                                                                                                          | Stage 8                                                                                                                                                                                                                                                              |

## Repository layout

| Path             | Contents                                                                                                                                                                               |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `_sources/`      | Building block sources                                                                                                                                                                 |
| `data/examples/` | The full SP83687 CSDM dataset (depersonalised). The lodged schedule of unit entitlements that served as the requirements source is not distributed; its content is analysed in `docs/` |
| `docs/`          | Investigation report and implementation plan; the Stage 8 generalisation check                                                                                                         |
| `scripts/`       | Helper scripts (fixture trimming and variants, vocabulary label table, source-conformance check)                                                                                       |
| `tests-py/`      | Local pytest suite that runs the Python transforms without Docker                                                                                                                      |
| `build/`         | [Postprocessor](https://github.com/opengeospatial/bblocks-postprocess) output published by CI. Never edit by hand                                                                      |

## Building and testing locally

Requires Docker.

```bash
./build.sh                                 # postprocess all blocks into build-local/
./view.sh                                  # browse the result at http://localhost:9090
scripts/check_source_conformance.sh        # validate the full CSDM dataset against the WA profile
python3 -m pytest tests-py                 # run the transform logic tests (no Docker needed)
```

For general guidance on authoring and using OGC Building Blocks, see the [OGC Building Blocks documentation](https://ogcincubator.github.io/bblocks-docs/).

## Licence

Licensed under the [Apache License, Version 2.0](LICENSE).
