# Scheme Composition Report

What a strata scheme is made of: its member lots, how each one is spatially represented, and a summary for the scheme.
It produces the `members` and `spatialRepresentationSummary` that the WA built-strata scope note says should be "generated via a reporting transform", without adding them to the source model.

This is the register's second report type.
It was built in Stage 8 to test that the generic `csdm.reporting.cadastral-report` block serves more than one report: it uses the same envelope, `ReportValue`, checks, `summarise-checks`, `render-html`, vocabulary and [SHACL](https://www.w3.org/TR/shacl/) rules as the Strata Scheme Entitlement Report, and the WA 3D CSDM adapter's shared `resolve-scheme` transform.

## Content

| Property | Stage | Meaning |
|---|---|---|
| `content.scheme.schemeNumber` | facts | Scheme (plan) number |
| `content.members[]` | facts | Member lots, ordered by lot number: `lotNumber`, `membershipEvidence`, `geometryType` (e.g. [`AggregateSolid`](https://ogcincubator.github.io/topo-feature/bblock/ogc.geo.topo.features.topo-aggregate-solid)), `representationStatus` (the source's code, e.g. `representation-status:d3d`), and `components` (each referenced component solid, with `found`: whether it is present in the source) |
| `content.members[].spatiallyResolved` | complete | derived: the member has components and every one is present |
| `content.summary.memberParcelCount` | complete | derived: number of members |
| `content.summary.geometryTypes` | complete | derived: the members' distinct geometry types |
| `content.summary.memberRepresentationStatuses` | complete | derived: the members' distinct representation statuses (supplied ones only) |
| `content.summary.allMemberParcelsSpatiallyResolved` | complete | derived: every member is spatially resolved |

A summary value reports what the source says, not a default.
If no member has a representation status, `memberRepresentationStatuses` is empty and the `representation-status-present` check fails.

## Checks

The adapter's shared membership checks, plus:

| Check | Severity | Fails when |
|---|---|---|
| `members-present` | error | the scheme has no member lots |
| `representation-status-present` | warning | a member has no representation status |
| `component-references-resolve` | warning | a member references a component that is not in the source |
| `all-members-spatially-resolved` | warning | a member has no components, or some are missing |

For SP83687 the report is `incomplete`.
Lots 1 and 2 are spatially resolved (all 4 and 5 of their component solids are present), Lots 3 to 9 have no component solids yet, and no lot carries a representation status.
That is an accurate picture of the dataset.

## Semantics

`context.jsonld` maps the content to `ontology.ttl` (prefix `sc:` = `https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/`); the list-valued summaries are [RDF lists](https://www.w3.org/TR/rdf11-mt/#rdf-collections).
`shapes.shacl` adds `sc:MemberParcelCountIsTheNumberOfMembers`.

## Transforms

- **`complete`:** facts-stage report → complete report (derived values, checks, status).
  Idempotent.
- **`to-html`:** template only, rendered by the generic `render-html`.
