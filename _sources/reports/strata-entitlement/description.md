# Strata Scheme Entitlement Report

A structured, machine-readable report of the unit entitlement of every lot in a strata scheme. It
captures the semantic content of a lodged *Schedule of Unit Entitlements* (in WA, approved form
2021-47738), not its layout.

This block knows nothing about the source data format. Source adapters (such as
`csdm.reporting.adapters.wa-csdm`) produce the report; this block's transforms present it.

## Stages

A report passes through two stages, both validated by this block's schema:

1. **`facts`:** produced by a source adapter. Source facts only; `content.totals` is not allowed.
2. **`complete`:** produced by this block's `complete` transform. Adds the derived values; `content.totals`
   is required.

Keeping all calculation here means every source adapter gets the same totals.

## Content

Every value is a `ReportValue` (see `csdm.reporting.cadastral-report`): the value, its status and its
provenance. Source values point at the exact source property; derived values list the report values they
were calculated from.

| Property | Stage | Status | Meaning |
|---|---|---|---|
| `content.scheme.schemeNumber` | facts | reported / not-supplied | Scheme (plan) number, e.g. `SP83687` |
| `content.scheme.schemeName` | facts | reported / not-supplied | Scheme name |
| `content.scheme.address.parts[]` | facts | | Address parts as supplied (`partType`, `value`), with a `label` for the road and locality |
| `content.scheme.address.formatted` | facts | derived (`format-address`) / unresolved / not-supplied | e.g. "281 Belmont Avenue, Cloverdale" |
| `content.lots[].lotNumber` | facts | reported / not-supplied / unresolved | Lot number as in the source |
| `content.lots[].entitlement` | facts | reported / not-supplied / invalid / conflicting / unresolved | Unit entitlement, a positive whole number |
| `content.lots[].ref` | facts | | The lot parcel in the source |
| `content.lots[].membershipEvidence` | facts | | The source links that associate the lot with the scheme (authoritative first) |
| `content.totals.declared` | facts | reported / not-supplied / invalid / conflicting | Total unit entitlement declared by the source |
| `content.basis.schedule` | facts | | The lodged schedule (`documentRef` into `documents`) and the approved form it `conformsTo` |
| `content.basis.form` | facts | reported / unresolved / not-supplied | The approved form: `label`, `validFrom` (effective for use from), `source` |
| `content.basis.certification` | facts | reported / not-supplied | The licensed valuer's certification: `certifier` (first and last name, licence number), `dateCertified`, the `annotationRef` holding the verbatim statement, and the `documentRef` it certifies |
| `content.legislativeBasis[]` | facts | reported / unresolved | The legislation the approved form is made under |
| `content.totals.calculated` | complete | derived (`sum`) | Sum of the lots with a usable entitlement; a `note` says when some lots were left out |
| `content.totals.lotCount` | complete | derived (`count`) | Number of member lots |

A lot whose entitlement is missing or unusable stays in the report with that status, and a scheme whose
members cannot be identified still produces a report (with no lots). Such problems are recorded as
check failures, not schema errors.

## Semantics (RDF)

`context.jsonld` maps the content to the strata entitlement vocabulary (`ontology.ttl`, prefix
`se:` = `https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/`); the
envelope, report values, checks and documents use the generic mapping of
`csdm.reporting.cadastral-report`. Address part types are kept as ICSM address part type concepts
(`apt:road`, …), and the parts' supplied values as JSON literals. `se:unitEntitlement` is a close match of
LADM's `entitlementPortion`, and each entitlement's source reference names that LADM property, so the RDF
says exactly which source property every entitlement was read from.

`shapes.shacl` adds the report's cross-field rules, checked after uplift:

- **`se:CalculatedTotalIsTheSumOfTheLots`:** the calculated total equals the sum of the lots' unit
  entitlements.
- **`se:LotCountIsTheNumberOfLots`:** the lot count equals the number of lots.

The `-fail` tests `calculated-total-not-the-sum`, `lot-count-not-the-number-of-lots` and
`document-ref-unresolved` are valid JSON that only these rules reject.

## Checks

The source adapter records the source-specific checks (scheme identification, membership, source
datatypes). `complete` adds these report-level checks:

| Check | Severity | Fails when |
|---|---|---|
| `lot-numbers-present` | warning | a lot has no lot number |
| `lot-numbers-unique` | error | two lots share a lot number |
| `entitlements-present` | warning | a lot's entitlement is not supplied or unresolved |
| `entitlements-valid` | error | a lot's entitlement is invalid or conflicting |
| `total-covers-all-lots` | warning | the calculated total leaves out a lot |
| `declared-total-present` | warning | the source declares no usable total |
| `total-matches-declared` | error | the calculated total differs from the declared total (not evaluated when either is incomplete) |
| `schedule-document-referenced` | warning | no schedule of unit entitlements is referenced |
| `valuer-certification-present` | warning | no certification, or it lacks the valuer's last name, licence number or date |
| `certification-linked-to-schedule` | info | the certification links to a different document (not applicable when either is missing) |
| `document-hrefs-resolvable` | info | not evaluated: links are not resolved during generation, and relative links have no base (D12) |

So a missing entitlement makes a report `incomplete`, while a wrong one, or a total that does not match,
makes it `invalid`.

The report deliberately does not reproduce the lodged form's wording, signature, logos or QR code (D6):
it is a derived report that cites the form and the lodged schedule.

## Transforms

- **`complete`:** facts-stage report → complete report: calculated total and lot count, the report-level
  checks, and the overall status (via `summarise-checks` of `csdm.reporting.cadastral-report`). Idempotent.
- **`to-html`:** renders a report as a standalone HTML page: the scheme's number, name and address, the
  lots and totals, the basis of the schedule (document, approved form, legislation) and the valuer's
  certification. Template only: `transforms/to_html.py` holds the Jinja2 body and passes it to the generic
  `render-html` of `csdm.reporting.cadastral-report`, which adds the report status, status markers and
  legend, the documents relied on, the check results and the pipeline. For a facts-stage report, the total
  row says it has not been calculated yet.
- **`to-csv`:** the lots as CSV, one row per lot: scheme number, lot number, unit entitlement, the status
  of each, the entitlement's source pointer and the parcel id. A missing entitlement is an empty value with
  status `not-supplied`.
