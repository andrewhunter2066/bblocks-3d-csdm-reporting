
# Scheme Composition Report (Schema)

`csdm.reporting.reports.scheme-composition` *v0.1*

Structured report of what a strata scheme is made of: its member lots, how each is spatially represented, and a summary (member count, geometry types, representation statuses, whether every member is spatially resolved). The second report type of the register, built to test that the generic cadastral-report block serves more than one report.

[*Status*](http://www.opengis.net/def/status): Under development

## Description

# Scheme Composition Report

What a strata scheme is made of: its member lots, how each one is spatially represented, and a summary
for the scheme. It produces the `members` and `spatialRepresentationSummary` that the WA built-strata
scope note says should be "generated via a reporting transform", without adding them to the source model.

This is the register's second report type. It was built in Stage 8 to test that the generic
`csdm.reporting.cadastral-report` block serves more than one report: it uses the same envelope,
`ReportValue`, checks, `summarise-checks`, `render-html`, vocabulary and SHACL rules as the Strata Scheme
Entitlement Report, and the WA 3D CSDM adapter's shared `resolve-scheme` transform.

## Content

| Property | Stage | Meaning |
|---|---|---|
| `content.scheme.schemeNumber` | facts | Scheme (plan) number |
| `content.members[]` | facts | Member lots, ordered by lot number: `lotNumber`, `membershipEvidence`, `geometryType` (e.g. `AggregateSolid`), `representationStatus` (the source's code, e.g. `representation-status:d3d`), and `components` (each referenced component solid, with `found`: whether it is present in the source) |
| `content.members[].spatiallyResolved` | complete | derived: the member has components and every one is present |
| `content.summary.memberParcelCount` | complete | derived: number of members |
| `content.summary.geometryTypes` | complete | derived: the members' distinct geometry types |
| `content.summary.memberRepresentationStatuses` | complete | derived: the members' distinct representation statuses (supplied ones only) |
| `content.summary.allMemberParcelsSpatiallyResolved` | complete | derived: every member is spatially resolved |

A summary value reports what the source says, not a default. If no member has a representation status,
`memberRepresentationStatuses` is empty and the `representation-status-present` check fails.

## Checks

The adapter's shared membership checks, plus:

| Check | Severity | Fails when |
|---|---|---|
| `members-present` | error | the scheme has no member lots |
| `representation-status-present` | warning | a member has no representation status |
| `component-references-resolve` | warning | a member references a component that is not in the source |
| `all-members-spatially-resolved` | warning | a member has no components, or some are missing |

For SP83687 the report is `incomplete`. Lots 1 and 2 are spatially resolved (all 4 and 5 of their
component solids are present), Lots 3 to 9 have no component solids yet, and no lot carries a
representation status. That is an accurate picture of the dataset.

## Semantics

`context.jsonld` maps the content to `ontology.ttl` (prefix `sc:` =
`https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/`); the list-valued
summaries are RDF lists. `shapes.shacl` adds `sc:MemberParcelCountIsTheNumberOfMembers`.

## Transforms

- **`complete`:** facts-stage report → complete report (derived values, checks, status). Idempotent.
- **`to-html`:** template only, rendered by the generic `render-html`.

## Examples

### SP83687 facts-stage composition
The source facts for strata plan SP83687 as extracted by the WA 3D CSDM adapter: each member lot's
geometry type, representation status and component solids (with whether each is in the dataset).

#### json
```json
{
  "reportType": "csdm.reporting.reports.scheme-composition",
  "stage": "facts",
  "generatedBy": [
    {
      "bblock": "csdm.reporting.adapters.wa-csdm",
      "transform": "to-scheme-composition-facts"
    }
  ],
  "subject": {
    "kind": "strata-scheme",
    "label": "Lots 1 to 9 on Plan SP 83687",
    "ref": {
      "dataset": "SP-83687-1-1-0.00",
      "pointer": "/parcels/0/features/1",
      "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
    }
  },
  "sources": [
    {
      "id": "SP-83687-1-1-0.00",
      "kind": "dataset",
      "name": "SP83687",
      "date": "2023-02-06",
      "conformsTo": "icsm.profiles.wa.wa-3d"
    }
  ],
  "content": {
    "scheme": {
      "schemeNumber": {
        "value": "SP83687",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/schemeNumber"
          }
        ]
      },
      "ref": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/parcels/0/features/1",
        "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    "members": [
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/2",
          "id": "uuid:e62621ed-1334-4890-964f-608ff68f7a17"
        },
        "lotNumber": {
          "value": "1",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/1",
              "id": "uuid:bebe0853-7b46-4ee0-a2d2-b60a445f6b2d"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/2",
              "id": "uuid:93f32e94-6a66-4405-9763-bf9d9771e654"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/5",
              "id": "uuid:8834fa5e-529b-4258-9537-a01bea709001"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/12",
              "id": "uuid:e1102530-0aae-4a27-87a1-ad9dbe7372e9"
            },
            "found": true
          }
        ]
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/3",
          "id": "uuid:8e5ca9ad-b00d-4871-a723-19b6456480f9"
        },
        "lotNumber": {
          "value": "2",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/3",
              "id": "uuid:720d46e0-f6b3-4348-a932-da6191a5efa3"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/4",
              "id": "uuid:ab63e7a8-93a3-4f90-848f-4f247ab771fe"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/6",
              "id": "uuid:fa342e93-b1c6-4254-ad40-45f1d756702d"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/13",
              "id": "uuid:6077a08d-0df0-46c4-90a7-ef94a5daebd2"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/14",
              "id": "uuid:c6cc1caf-1246-4ac1-aee6-a9980a93b393"
            },
            "found": true
          }
        ]
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/4",
          "id": "uuid:85da01f8-9625-4b1e-9f4d-a34c11313512"
        },
        "lotNumber": {
          "value": "3",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/5",
          "id": "uuid:5e2823d1-2473-4417-8045-1089d2e86e64"
        },
        "lotNumber": {
          "value": "4",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/6",
          "id": "uuid:b46b34d5-03dd-49d2-b677-31042c5ab3f3"
        },
        "lotNumber": {
          "value": "5",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/7",
          "id": "uuid:c1a7f52f-1b21-4266-8167-d5f3169c6078"
        },
        "lotNumber": {
          "value": "6",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/8",
          "id": "uuid:0df5a108-f5fe-433a-9934-b0162115248f"
        },
        "lotNumber": {
          "value": "7",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/9",
          "id": "uuid:15e3af06-3035-4c0a-89c2-57c71b254ad5"
        },
        "lotNumber": {
          "value": "8",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/10",
          "id": "uuid:79015221-adeb-482f-988b-ed47e57bc2a4"
        },
        "lotNumber": {
          "value": "9",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": []
      }
    ]
  },
  "checks": [
    {
      "id": "scheme-identified",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "generation",
      "severity": "error",
      "outcome": "pass",
      "message": "One strata scheme parcel identified (uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e)",
      "evidence": {
        "schemeId": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    {
      "id": "membership-parcel-aggregate",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "The scheme topology is ParcelAggregate with 9 member reference(s)",
      "evidence": {
        "topologyType": "ParcelAggregate",
        "references": 9
      }
    },
    {
      "id": "membership-references-resolve",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "All 9 references resolve to strata-lot parcels"
    },
    {
      "id": "membership-back-links",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "Every member lot links back to the scheme"
    },
    {
      "id": "membership-unreferenced-claimants",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "No strata lot claims the scheme without being one of its references"
    },
    {
      "id": "scheme-number-consistent",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "The scheme number agrees with csdName and appellationSurveyNumber (ignoring spaces)",
      "targets": [
        "/content/scheme/schemeNumber"
      ],
      "evidence": {
        "schemeNumber": "SP83687",
        "csdName": "SP83687",
        "appellationSurveyNumber": "SP 83687"
      }
    }
  ]
}

```


### SP83687 complete composition
The complete Scheme Composition Report for SP83687. Lots 1 and 2 are spatially resolved (all 4 and 5
of their component solids are present); Lots 3 to 9 have no component solids yet, and no lot carries
a representation status, so the report is `incomplete`: an honest picture of the dataset, not a
failure of the report.

#### json
```json
{
  "reportType": "csdm.reporting.reports.scheme-composition",
  "stage": "complete",
  "generatedBy": [
    {
      "bblock": "csdm.reporting.adapters.wa-csdm",
      "transform": "to-scheme-composition-facts"
    },
    {
      "bblock": "csdm.reporting.reports.scheme-composition",
      "transform": "complete"
    },
    {
      "bblock": "csdm.reporting.cadastral-report",
      "transform": "summarise-checks"
    }
  ],
  "subject": {
    "kind": "strata-scheme",
    "label": "Lots 1 to 9 on Plan SP 83687",
    "ref": {
      "dataset": "SP-83687-1-1-0.00",
      "pointer": "/parcels/0/features/1",
      "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
    }
  },
  "sources": [
    {
      "id": "SP-83687-1-1-0.00",
      "kind": "dataset",
      "name": "SP83687",
      "date": "2023-02-06",
      "conformsTo": "icsm.profiles.wa.wa-3d"
    }
  ],
  "content": {
    "scheme": {
      "schemeNumber": {
        "value": "SP83687",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/schemeNumber"
          }
        ]
      },
      "ref": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/parcels/0/features/1",
        "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    "members": [
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/2",
          "id": "uuid:e62621ed-1334-4890-964f-608ff68f7a17"
        },
        "lotNumber": {
          "value": "1",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/1",
              "id": "uuid:bebe0853-7b46-4ee0-a2d2-b60a445f6b2d"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/2",
              "id": "uuid:93f32e94-6a66-4405-9763-bf9d9771e654"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/5",
              "id": "uuid:8834fa5e-529b-4258-9537-a01bea709001"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/12",
              "id": "uuid:e1102530-0aae-4a27-87a1-ad9dbe7372e9"
            },
            "found": true
          }
        ],
        "spatiallyResolved": {
          "value": true,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/0/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/3",
          "id": "uuid:8e5ca9ad-b00d-4871-a723-19b6456480f9"
        },
        "lotNumber": {
          "value": "2",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/3",
              "id": "uuid:720d46e0-f6b3-4348-a932-da6191a5efa3"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/4",
              "id": "uuid:ab63e7a8-93a3-4f90-848f-4f247ab771fe"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/6",
              "id": "uuid:fa342e93-b1c6-4254-ad40-45f1d756702d"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/13",
              "id": "uuid:6077a08d-0df0-46c4-90a7-ef94a5daebd2"
            },
            "found": true
          },
          {
            "ref": {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/solids/0/features/14",
              "id": "uuid:c6cc1caf-1246-4ac1-aee6-a9980a93b393"
            },
            "found": true
          }
        ],
        "spatiallyResolved": {
          "value": true,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/1/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/4",
          "id": "uuid:85da01f8-9625-4b1e-9f4d-a34c11313512"
        },
        "lotNumber": {
          "value": "3",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/2/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/5",
          "id": "uuid:5e2823d1-2473-4417-8045-1089d2e86e64"
        },
        "lotNumber": {
          "value": "4",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/3/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/6",
          "id": "uuid:b46b34d5-03dd-49d2-b677-31042c5ab3f3"
        },
        "lotNumber": {
          "value": "5",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/4/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/7",
          "id": "uuid:c1a7f52f-1b21-4266-8167-d5f3169c6078"
        },
        "lotNumber": {
          "value": "6",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/5/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/8",
          "id": "uuid:0df5a108-f5fe-433a-9934-b0162115248f"
        },
        "lotNumber": {
          "value": "7",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/6/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/9",
          "id": "uuid:15e3af06-3035-4c0a-89c2-57c71b254ad5"
        },
        "lotNumber": {
          "value": "8",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/7/components"
            ]
          }
        }
      },
      {
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/10",
          "id": "uuid:79015221-adeb-482f-988b-ed47e57bc2a4"
        },
        "lotNumber": {
          "value": "9",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties/appellation/hasPart/3/label"
            }
          ]
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ],
        "geometryType": {
          "value": "AggregateSolid",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/topology/type"
            }
          ]
        },
        "representationStatus": {
          "value": null,
          "status": "not-supplied",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties"
            }
          ],
          "note": "The lot has no spatialRepresentationDefinitions.representationStatus"
        },
        "components": [],
        "spatiallyResolved": {
          "value": false,
          "status": "derived",
          "derivation": {
            "method": "all-components-found",
            "inputs": [
              "/content/members/8/components"
            ]
          }
        }
      }
    ],
    "summary": {
      "memberParcelCount": {
        "value": 9,
        "status": "derived",
        "derivation": {
          "method": "count",
          "inputs": [
            "/content/members"
          ]
        }
      },
      "geometryTypes": {
        "value": [
          "AggregateSolid"
        ],
        "status": "derived",
        "derivation": {
          "method": "distinct-values",
          "inputs": [
            "/content/members/0/geometryType",
            "/content/members/1/geometryType",
            "/content/members/2/geometryType",
            "/content/members/3/geometryType",
            "/content/members/4/geometryType",
            "/content/members/5/geometryType",
            "/content/members/6/geometryType",
            "/content/members/7/geometryType",
            "/content/members/8/geometryType"
          ]
        }
      },
      "memberRepresentationStatuses": {
        "value": [],
        "status": "derived",
        "derivation": {
          "method": "distinct-values",
          "inputs": [
            "/content/members/0/representationStatus",
            "/content/members/1/representationStatus",
            "/content/members/2/representationStatus",
            "/content/members/3/representationStatus",
            "/content/members/4/representationStatus",
            "/content/members/5/representationStatus",
            "/content/members/6/representationStatus",
            "/content/members/7/representationStatus",
            "/content/members/8/representationStatus"
          ]
        }
      },
      "allMemberParcelsSpatiallyResolved": {
        "value": false,
        "status": "derived",
        "derivation": {
          "method": "all",
          "inputs": [
            "/content/members/0/spatiallyResolved",
            "/content/members/1/spatiallyResolved",
            "/content/members/2/spatiallyResolved",
            "/content/members/3/spatiallyResolved",
            "/content/members/4/spatiallyResolved",
            "/content/members/5/spatiallyResolved",
            "/content/members/6/spatiallyResolved",
            "/content/members/7/spatiallyResolved",
            "/content/members/8/spatiallyResolved"
          ]
        }
      }
    }
  },
  "checks": [
    {
      "id": "scheme-identified",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "generation",
      "severity": "error",
      "outcome": "pass",
      "message": "One strata scheme parcel identified (uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e)",
      "evidence": {
        "schemeId": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    {
      "id": "membership-parcel-aggregate",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "The scheme topology is ParcelAggregate with 9 member reference(s)",
      "evidence": {
        "topologyType": "ParcelAggregate",
        "references": 9
      }
    },
    {
      "id": "membership-references-resolve",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "All 9 references resolve to strata-lot parcels"
    },
    {
      "id": "membership-back-links",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "Every member lot links back to the scheme"
    },
    {
      "id": "membership-unreferenced-claimants",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "No strata lot claims the scheme without being one of its references"
    },
    {
      "id": "scheme-number-consistent",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "The scheme number agrees with csdName and appellationSurveyNumber (ignoring spaces)",
      "targets": [
        "/content/scheme/schemeNumber"
      ],
      "evidence": {
        "schemeNumber": "SP83687",
        "csdName": "SP83687",
        "appellationSurveyNumber": "SP 83687"
      }
    },
    {
      "id": "members-present",
      "definedBy": "csdm.reporting.reports.scheme-composition",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "The scheme has 9 member lot(s)",
      "targets": [
        "/content/members"
      ]
    },
    {
      "id": "representation-status-present",
      "definedBy": "csdm.reporting.reports.scheme-composition",
      "category": "domain",
      "severity": "warning",
      "outcome": "fail",
      "message": "9 of 9 member(s) have no representation status",
      "targets": [
        "/content/members/0/representationStatus",
        "/content/members/1/representationStatus",
        "/content/members/2/representationStatus",
        "/content/members/3/representationStatus",
        "/content/members/4/representationStatus",
        "/content/members/5/representationStatus",
        "/content/members/6/representationStatus",
        "/content/members/7/representationStatus",
        "/content/members/8/representationStatus"
      ]
    },
    {
      "id": "component-references-resolve",
      "definedBy": "csdm.reporting.reports.scheme-composition",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "Every component a member references is present in the source"
    },
    {
      "id": "all-members-spatially-resolved",
      "definedBy": "csdm.reporting.reports.scheme-composition",
      "category": "domain",
      "severity": "warning",
      "outcome": "fail",
      "message": "7 of 9 member(s) are not spatially resolved (no component solids, or some are missing)",
      "targets": [
        "/content/members/2/spatiallyResolved",
        "/content/members/3/spatiallyResolved",
        "/content/members/4/spatiallyResolved",
        "/content/members/5/spatiallyResolved",
        "/content/members/6/spatiallyResolved",
        "/content/members/7/spatiallyResolved",
        "/content/members/8/spatiallyResolved"
      ]
    }
  ],
  "status": "incomplete",
  "statusSummary": {
    "checks": 10,
    "failedErrors": 0,
    "failedWarnings": 2,
    "unevaluatedErrors": 0
  }
}

```

## Schema

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
description: 'Scheme Composition Report. Extends the generic cadastral report envelope
  with the scheme''s member lots,

  how each is spatially represented, and a summary. It provides the `members` and

  `spatialRepresentationSummary` that the WA built-strata scope note says should be
  generated by a

  reporting transform.


  A `facts` stage report (source adapter output) holds source facts only: no `summary`
  and no member

  `spatiallyResolved`. A `complete` stage report (output of this block''s `complete`)
  must carry both.

  '
allOf:
- $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml
- type: object
  properties:
    reportType:
      const: csdm.reporting.reports.scheme-composition
    content:
      type: object
      required:
      - scheme
      - members
      properties:
        scheme:
          type: object
          required:
          - schemeNumber
          properties:
            schemeNumber:
              $ref: '#/$defs/TextValue'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/schemeNumber
            ref:
              $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#SourceRef
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/scheme
        members:
          description: The scheme's member lots, ordered by lot number. May be empty.
          type: array
          items:
            type: object
            required:
            - lotNumber
            - geometryType
            - representationStatus
            - components
            properties:
              ref:
                $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#SourceRef
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
              lotNumber:
                $ref: '#/$defs/TextValue'
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/lotNumber
              membershipEvidence:
                type: array
                items:
                  type: string
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/membershipEvidence
                x-jsonld-container: '@set'
              geometryType:
                description: The member's geometry (topology) type, for example AggregateSolid.
                $ref: '#/$defs/TextValue'
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/geometryType
              representationStatus:
                description: How the member is spatially represented, as a code of
                  the source (for example representation-status:d3d).
                $ref: '#/$defs/TextValue'
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/representationStatus
              components:
                description: The component solids the member references, and whether
                  each is present in the source.
                type: array
                items:
                  type: object
                  required:
                  - ref
                  - found
                  properties:
                    ref:
                      $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#SourceRef
                      x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
                    found:
                      type: boolean
                      x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/componentFound
                      x-jsonld-type: http://www.w3.org/2001/XMLSchema#boolean
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/component
                x-jsonld-container: '@set'
              spatiallyResolved:
                description: Whether the member has components and every one is present
                  (derived).
                $ref: '#/$defs/BooleanValue'
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/spatiallyResolved
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/member
          x-jsonld-container: '@set'
        summary:
          description: The spatial representation summary of the scheme (derived by
            `complete`).
          type: object
          required:
          - memberParcelCount
          - geometryTypes
          - memberRepresentationStatuses
          - allMemberParcelsSpatiallyResolved
          properties:
            memberParcelCount:
              $ref: '#/$defs/DerivedCount'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/memberParcelCount
            geometryTypes:
              $ref: '#/$defs/DerivedList'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/geometryTypes
            memberRepresentationStatuses:
              $ref: '#/$defs/DerivedList'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/memberRepresentationStatuses
            allMemberParcelsSpatiallyResolved:
              $ref: '#/$defs/BooleanValue'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/allMemberParcelsSpatiallyResolved
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/summary
- if:
    required:
    - stage
    properties:
      stage:
        const: complete
  then:
    properties:
      content:
        required:
        - summary
        properties:
          members:
            items:
              required:
              - spatiallyResolved
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/member
            x-jsonld-container: '@set'
  else:
    properties:
      content:
        not:
          required:
          - summary
        properties:
          members:
            items:
              not:
                required:
                - spatiallyResolved
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/member
            x-jsonld-container: '@set'
$defs:
  DerivedCount:
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - properties:
        status:
          const: derived
        value:
          type: integer
          minimum: 0
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
  TextValue:
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - properties:
        value:
          type:
          - string
          - 'null'
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
  BooleanValue:
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - properties:
        status:
          const: derived
        value:
          type: boolean
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
  DerivedList:
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - properties:
        status:
          const: derived
        value:
          type: array
          items:
            type: string
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
          x-jsonld-container: '@list'
x-jsonld-prefixes:
  cr: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  sc: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/

```

Links to the schema:

* YAML version: [schema.yaml](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/reports/scheme-composition/schema.json)
* JSON version: [schema.json](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/reports/scheme-composition/schema.yaml)


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
    "scheme": {
      "@context": {
        "schemeNumber": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:schemeNumber"
        },
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
      "@id": "sc:scheme"
    },
    "members": {
      "@context": {
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
        },
        "lotNumber": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:lotNumber"
        },
        "membershipEvidence": {
          "@id": "sc:membershipEvidence",
          "@container": "@set"
        },
        "geometryType": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:geometryType"
        },
        "representationStatus": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:representationStatus"
        },
        "components": {
          "@context": {
            "found": {
              "@id": "sc:componentFound",
              "@type": "xsd:boolean"
            }
          },
          "@id": "sc:component",
          "@container": "@set"
        },
        "spatiallyResolved": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:spatiallyResolved"
        }
      },
      "@id": "sc:member",
      "@container": "@set"
    },
    "summary": {
      "@context": {
        "memberParcelCount": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:memberParcelCount"
        },
        "geometryTypes": {
          "@context": {
            "value": {
              "@id": "rdf:value",
              "@container": "@list"
            },
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:geometryTypes"
        },
        "memberRepresentationStatuses": {
          "@context": {
            "value": {
              "@id": "rdf:value",
              "@container": "@list"
            },
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:memberRepresentationStatuses"
        },
        "allMemberParcelsSpatiallyResolved": {
          "@context": {
            "sourceRefs": {
              "@context": {
                "dataset": "cr:sourceDataset",
                "pointer": "cr:jsonPointer",
                "id": "cr:sourceObject",
                "property": {
                  "@id": "cr:sourceProperty",
                  "@type": "@id"
                }
              },
              "@id": "cr:sourceRef",
              "@container": "@set"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "sc:allMemberParcelsSpatiallyResolved"
        }
      },
      "@id": "sc:summary"
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
    "sc": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/scheme-composition/",
    "@version": 1.1
  }
}
```

You can find the full JSON-LD context here:
[context.jsonld](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting-clean/build/annotated/reporting/reports/scheme-composition/context.jsonld)

## Sources

* [Built strata bblock scope note (members and spatialRepresentationSummary, "generate via a reporting transform")](https://github.com/surroundaustralia/3d-csdm-profile-wa/tree/main/proposals/development/built-strata)

# For developers

The source code for this Building Block can be found in the following repository:

* URL: [https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting-clean](https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting-clean)
* Path: `_sources/reports/scheme-composition`

