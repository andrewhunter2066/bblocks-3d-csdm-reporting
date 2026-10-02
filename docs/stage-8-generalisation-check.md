# Stage 8: generalisation check

Last updated: 2026-10-02

**Result:** a second report type, the Scheme Composition Report, was added using the generic
`csdm.reporting.cadastral-report` block as it stood after Stage 7. It needed **one** change there: the
generic HTML renderer now displays list and boolean values readably. No strata assumption had leaked into
the generic blocks. On the adapter side, the duplication trigger recorded in the investigation (section 3)
fired, and the shared source interpretation was promoted to a `resolve-scheme` transform.

## What was built

| Block | Change |
|---|---|
| `csdm.reporting.reports.scheme-composition` (new) | Schema (envelope + content), `complete`, template-only `to-html`, JSON-LD context, `sc:` vocabulary, one SHACL rule, SP83687 facts and complete examples, 6 must-fail tests |
| `csdm.reporting.adapters.wa-csdm` | New `resolve-scheme` (shared), `to-scheme-composition-facts`, and `-report`/`-html` compositions. `to-strata-entitlement-facts` now uses `resolve-scheme`; its outputs are byte-identical to Stage 7 |
| `csdm.reporting.cadastral-report` | `render-html` shows lists comma-separated (empty: "none") and booleans as yes/no |
| `scripts/trim_csdm_fixture.py` | Keeps the `solids` collection (7 KB), which the composition report needs; the entitlement outputs are unchanged |

## Did the second report need changes to the generic blocks?

| Generic element | Change needed? | Notes |
|---|---|---|
| Envelope schema (`reportType`, `stage`, `status`, `checks`, `subject`, `sources`, `content`) | No | |
| `ReportValue`, `SourceRef`, `Check` | No | List- and boolean-valued `ReportValue`s worked unchanged: `value` was never restricted to text or numbers |
| `summarise-checks` | No | |
| JSON-LD context, vocabulary, codelists, SHACL rules | No | The composition report's own context and `sc:` terms sit beside them |
| `render-html` | **Yes** | It printed Python representations (`['AggregateSolid']`, `[]`, `True`). Now `AggregateSolid`, `none` and `yes`. A generic fix, because any report type can have such values; the entitlement HTML is byte-identical |

No strata or WA assumption was found in the generic blocks: "strata" appears there only in "for example"
text in descriptions.

## Adapter duplication, measured against the section 3 trigger

The trigger: "when two adapter transforms repeat the same extraction (scheme resolution, membership,
document index), promote it to a shared `resolve-scheme` transform".

The composition report needed exactly that extraction: identifying the scheme (and stopping when there is
not exactly one), resolving members from the `ParcelAggregate` references with their evidence and lot
numbers, the five membership checks, and the scheme-number cross-check. That is about 150 lines of
`to-strata-entitlement-facts`, so the trigger fired.

| | Lines |
|---|---|
| `to-strata-entitlement-facts` before | 465 |
| `resolve-scheme` (shared) | 227 |
| `to-strata-entitlement-facts` after | 342 |
| `to-scheme-composition-facts` | 107 |

Checks about particular members come back from `resolve-scheme` with member ids (`targetMembers`), and
each report turns them into pointers to its own content (`/content/lots/N` or `/content/members/N`).

**Remaining duplication:** small helpers (`_pointer`, `_ref`, `_value`, about 30 lines) repeat in the three
adapter transforms, because `python` transforms cannot import each other and a transform is the only
reuse mechanism (`get_transformer()`, text in and text out). This is accepted: wrapping helper functions in
transforms would cost more than it saves.

## Findings for later (deferred)

- **Shared strata vocabulary:** the `se:` and `sc:` vocabularies both define `scheme`, `schemeNumber`,
  `lotNumber` and `membershipEvidence`. Promote them to a shared strata vocabulary when a third strata
  report needs them (the same rule as `resolve-scheme`).
- **Representation status:** the scope note expects members to default to `representation-status:d3d`. The
  report does not assume a default: SP83687 lots carry no `spatialRepresentationDefinitions`, so the
  summary is empty and a check fails. A default belongs in the source profile, not the report.
- **`components[].found`** is a plain boolean, not a `ReportValue`. That was enough here; if components
  ever need their own provenance or status, it should become one.
