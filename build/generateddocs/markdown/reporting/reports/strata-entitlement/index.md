
# Strata Scheme Entitlement Report (Schema)

`csdm.reporting.reports.strata-entitlement` *v0.1*

Structured report of the unit entitlement of every lot in a strata scheme, with the calculated total. Independent of the source data format: source adapters produce it, and its own transforms present it.

[*Status*](http://www.opengis.net/def/status): Under development

## Description

# Strata Scheme Entitlement Report

A structured, machine-readable report of the unit entitlement of every lot in a strata scheme.
It captures the semantic content of a lodged *Schedule of Unit Entitlements* (in WA, approved form 2021-47738), not its layout.

This block knows nothing about the source data format.
Source adapters (such as `csdm.reporting.adapters.wa-csdm`) produce the report; this block's transforms present it.

## Stages

A report passes through two stages, both validated by this block's schema:

1. **`facts`:** produced by a source adapter.
   Source facts only; `content.totals` is not allowed.
2. **`complete`:** produced by this block's `complete` transform.
   Adds the derived values; `content.totals` is required.

Keeping all calculation here means every source adapter gets the same totals.

## Content

Every value is a `ReportValue` (see `csdm.reporting.cadastral-report`): the value, its status and its provenance.
Source values point at the exact source property; derived values list the report values they were calculated from.

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

A lot whose entitlement is missing or unusable stays in the report with that status, and a scheme whose members cannot be identified still produces a report (with no lots).
Such problems are recorded as check failures, not schema errors.

## Semantics (RDF)

`context.jsonld` maps the content to the strata entitlement vocabulary (`ontology.ttl`, prefix `se:` = `https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/`); the envelope, report values, checks and documents use the generic mapping of `csdm.reporting.cadastral-report`.
Address part types are kept as ICSM address part type concepts (`apt:road`, …), and the parts' supplied values as JSON literals.
`se:unitEntitlement` is a close match of [LADM](https://ogcincubator.github.io/bblocks-land-parcels/bblock/ogc.ladm.land-parcels.ontology)'s `entitlementPortion`, and each entitlement's source reference names that LADM property, so the RDF says exactly which source property every entitlement was read from.

`shapes.shacl` adds the report's cross-field rules, checked after uplift:

- **`se:CalculatedTotalIsTheSumOfTheLots`:** the calculated total equals the sum of the lots' unit entitlements.
- **`se:LotCountIsTheNumberOfLots`:** the lot count equals the number of lots.

The `-fail` tests `calculated-total-not-the-sum`, `lot-count-not-the-number-of-lots` and `document-ref-unresolved` are valid JSON that only these rules reject.

## Checks

The source adapter records the source-specific checks (scheme identification, membership, source datatypes).
`complete` adds these report-level checks:

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

So a missing entitlement makes a report `incomplete`, while a wrong one, or a total that does not match, makes it `invalid`.

The report deliberately does not reproduce the lodged form's wording, signature, logos or QR code (D6): it is a derived report that cites the form and the lodged schedule.

## Transforms

- **`complete`:** facts-stage report → complete report: calculated total and lot count, the report-level checks, and the overall status (via `summarise-checks` of `csdm.reporting.cadastral-report`).
  Idempotent.
- **`to-html`:** renders a report as a standalone HTML page: the scheme's number, name and address, the lots and totals, the basis of the schedule (document, approved form, legislation) and the valuer's certification.
  Template only: `transforms/to_html.py` holds the Jinja2 body and passes it to the generic `render-html` of `csdm.reporting.cadastral-report`, which adds the report status, status markers and legend, the documents relied on, the check results and the pipeline.
  For a facts-stage report, the total row says it has not been calculated yet.
- **`to-csv`:** the lots as CSV, one row per lot: scheme number, lot number, unit entitlement, the status of each, the entitlement's source pointer and the parcel id.
  A missing entitlement is an empty value with status `not-supplied`.

## Examples

### SP83687 facts-stage report
The source facts for strata plan SP83687 as extracted by the WA 3D CSDM adapter (`stage: facts`):
the scheme number and each lot's number and unit entitlement, with references back to the source
parcels. It carries no derived values. This block's `complete` transform turns it into the complete
report in the next example.

#### json
```json
{
  "reportType": "csdm.reporting.reports.strata-entitlement",
  "stage": "facts",
  "generatedBy": [
    {
      "bblock": "csdm.reporting.adapters.wa-csdm",
      "transform": "to-strata-entitlement-facts"
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
    },
    {
      "id": "https://linked.data.gov.au/def/csdm/wa-approved-form",
      "kind": "vocabulary",
      "name": "wa-approved-form"
    },
    {
      "id": "https://linked.data.gov.au/def/csdm/wa-locality",
      "kind": "vocabulary",
      "name": "WA Localities"
    }
  ],
  "documents": [
    {
      "id": "unit-entitlement-schedule",
      "title": "Schedule of Unit Entitlements - SP83687",
      "href": "documents/SP83687-unit-entitlement-schedule.pdf",
      "mediaType": "application/pdf",
      "role": "wa-survey-documentation-type:unitEntitlementSchedule",
      "conformsTo": "wa-approved-form:2021-47738",
      "sourceRef": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/supportingDocuments/3"
      }
    }
  ],
  "annotations": [
    {
      "id": "licensed-valuer-certification",
      "role": "wa-annotation-role:licensed-valuer-certification",
      "statement": "Schedule of Unit Entitlements certified by Jordan Example AAPI, Licensed Valuer No. 00000, dated 17 May 2022.",
      "href": "documents/SP83687-unit-entitlement-schedule.pdf",
      "rel": "via",
      "documentRef": "unit-entitlement-schedule",
      "sourceRef": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/annotations/2"
      }
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
      "schemeName": {
        "value": "281 Belmont Avenue, Cloverdale",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/schemeName"
          }
        ]
      },
      "address": {
        "parts": [
          {
            "partType": "apt:addressNumberFirst",
            "value": 281
          },
          {
            "partType": "apt:road",
            "value": {
              "@id": "https://example.com/road/belmont-avenue",
              "label": "Belmont Avenue"
            },
            "label": {
              "value": "Belmont Avenue",
              "status": "reported",
              "sourceRefs": [
                {
                  "dataset": "SP-83687-1-1-0.00",
                  "pointer": "/parcels/0/features/1/properties/schemeAddress/hasPart/1/value/label"
                }
              ]
            }
          },
          {
            "partType": "apt:locality",
            "value": "wa-locality:cloverdale",
            "label": {
              "value": "Cloverdale",
              "status": "reported",
              "sourceRefs": [
                {
                  "dataset": "https://linked.data.gov.au/def/csdm/wa-locality",
                  "pointer": "",
                  "id": "https://linked.data.gov.au/def/csdm/wa-locality/cloverdale"
                }
              ]
            }
          },
          {
            "partType": "apt:stateOrTerritory",
            "value": {
              "@id": "https://linked.data.gov.au/dataset/asgsed3/STE/5"
            }
          },
          {
            "partType": "apt:postcode",
            "value": 6105
          },
          {
            "partType": "apt:country",
            "value": {
              "@id": "https://linked.data.gov.au/dataset/asgsed3/AUS/AUS"
            }
          }
        ],
        "formatted": {
          "value": "281 Belmont Avenue, Cloverdale",
          "status": "derived",
          "derivation": {
            "method": "format-address",
            "inputs": [
              "/content/scheme/address/parts/0/value",
              "/content/scheme/address/parts/1/label",
              "/content/scheme/address/parts/2/label"
            ]
          }
        }
      },
      "ref": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/parcels/0/features/1",
        "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    "lots": [
      {
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
        "entitlement": {
          "value": 117,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/2",
          "id": "uuid:e62621ed-1334-4890-964f-608ff68f7a17"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/3",
          "id": "uuid:8e5ca9ad-b00d-4871-a723-19b6456480f9"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 113,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/4",
          "id": "uuid:85da01f8-9625-4b1e-9f4d-a34c11313512"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/5",
          "id": "uuid:5e2823d1-2473-4417-8045-1089d2e86e64"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/6",
          "id": "uuid:b46b34d5-03dd-49d2-b677-31042c5ab3f3"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 113,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/7",
          "id": "uuid:c1a7f52f-1b21-4266-8167-d5f3169c6078"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/8",
          "id": "uuid:0df5a108-f5fe-433a-9934-b0162115248f"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/9",
          "id": "uuid:15e3af06-3035-4c0a-89c2-57c71b254ad5"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 117,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/10",
          "id": "uuid:79015221-adeb-482f-988b-ed47e57bc2a4"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      }
    ],
    "basis": {
      "schedule": {
        "documentRef": "unit-entitlement-schedule",
        "conformsTo": "wa-approved-form:2021-47738"
      },
      "form": {
        "id": "wa-approved-form:2021-47738",
        "label": {
          "value": "Approved Schedule of Unit Entitlements Form number 2021-47738",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ]
        },
        "validFrom": {
          "value": "2021-07-07",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ],
          "lexicalValue": "2021-07-07/.."
        },
        "source": {
          "value": "wa-leg:mrdoc_48587.pdf",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ]
        }
      },
      "certification": {
        "annotationRef": "licensed-valuer-certification",
        "certifier": {
          "firstName": {
            "value": "Jordan",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/firstName"
              }
            ]
          },
          "lastName": {
            "value": "Example",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/lastName"
              }
            ]
          },
          "licensedValuerNumber": {
            "value": "00000",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/licensedValuerNumber"
              }
            ]
          }
        },
        "dateCertified": {
          "value": "2022-05-17",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/annotations/2/dateCertified"
            }
          ]
        },
        "documentRef": "unit-entitlement-schedule"
      }
    },
    "legislativeBasis": [
      {
        "value": "Approved under section 37, Schedule 2A clause 21T(1)(d) and Schedule 2A clause 31E(1)(c) of the Strata Titles Act 1985.",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
            "pointer": "",
            "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
          }
        ]
      }
    ],
    "totals": {
      "declared": {
        "value": 1000,
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/interests/0/entitlementTotal"
          }
        ]
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
      "id": "entitlement-source-datatype",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "source-conformance",
      "severity": "info",
      "outcome": "fail",
      "message": "9 entitlementPortion value(s) are numbers; icsm.profiles.wa.wa-3d types them as strings (converted to integers here)",
      "targets": [
        "/content/lots/0/entitlement",
        "/content/lots/1/entitlement",
        "/content/lots/2/entitlement",
        "/content/lots/3/entitlement",
        "/content/lots/4/entitlement",
        "/content/lots/5/entitlement",
        "/content/lots/6/entitlement",
        "/content/lots/7/entitlement",
        "/content/lots/8/entitlement"
      ]
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


### SP83687 complete report
The complete report for strata plan SP83687 (Lots 1 to 9, 281 Belmont Avenue, Cloverdale). The lot
numbers, unit entitlements and total (1000) match the lodged Schedule of Unit Entitlements. The
`to-html` transform renders this example as an HTML page.

#### json
```json
{
  "reportType": "csdm.reporting.reports.strata-entitlement",
  "stage": "complete",
  "generatedBy": [
    {
      "bblock": "csdm.reporting.adapters.wa-csdm",
      "transform": "to-strata-entitlement-facts"
    },
    {
      "bblock": "csdm.reporting.reports.strata-entitlement",
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
    },
    {
      "id": "https://linked.data.gov.au/def/csdm/wa-approved-form",
      "kind": "vocabulary",
      "name": "wa-approved-form"
    },
    {
      "id": "https://linked.data.gov.au/def/csdm/wa-locality",
      "kind": "vocabulary",
      "name": "WA Localities"
    }
  ],
  "documents": [
    {
      "id": "unit-entitlement-schedule",
      "title": "Schedule of Unit Entitlements - SP83687",
      "href": "documents/SP83687-unit-entitlement-schedule.pdf",
      "mediaType": "application/pdf",
      "role": "wa-survey-documentation-type:unitEntitlementSchedule",
      "conformsTo": "wa-approved-form:2021-47738",
      "sourceRef": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/supportingDocuments/3"
      }
    }
  ],
  "annotations": [
    {
      "id": "licensed-valuer-certification",
      "role": "wa-annotation-role:licensed-valuer-certification",
      "statement": "Schedule of Unit Entitlements certified by Jordan Example AAPI, Licensed Valuer No. 00000, dated 17 May 2022.",
      "href": "documents/SP83687-unit-entitlement-schedule.pdf",
      "rel": "via",
      "documentRef": "unit-entitlement-schedule",
      "sourceRef": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/annotations/2"
      }
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
      "schemeName": {
        "value": "281 Belmont Avenue, Cloverdale",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/schemeName"
          }
        ]
      },
      "address": {
        "parts": [
          {
            "partType": "apt:addressNumberFirst",
            "value": 281
          },
          {
            "partType": "apt:road",
            "value": {
              "@id": "https://example.com/road/belmont-avenue",
              "label": "Belmont Avenue"
            },
            "label": {
              "value": "Belmont Avenue",
              "status": "reported",
              "sourceRefs": [
                {
                  "dataset": "SP-83687-1-1-0.00",
                  "pointer": "/parcels/0/features/1/properties/schemeAddress/hasPart/1/value/label"
                }
              ]
            }
          },
          {
            "partType": "apt:locality",
            "value": "wa-locality:cloverdale",
            "label": {
              "value": "Cloverdale",
              "status": "reported",
              "sourceRefs": [
                {
                  "dataset": "https://linked.data.gov.au/def/csdm/wa-locality",
                  "pointer": "",
                  "id": "https://linked.data.gov.au/def/csdm/wa-locality/cloverdale"
                }
              ]
            }
          },
          {
            "partType": "apt:stateOrTerritory",
            "value": {
              "@id": "https://linked.data.gov.au/dataset/asgsed3/STE/5"
            }
          },
          {
            "partType": "apt:postcode",
            "value": 6105
          },
          {
            "partType": "apt:country",
            "value": {
              "@id": "https://linked.data.gov.au/dataset/asgsed3/AUS/AUS"
            }
          }
        ],
        "formatted": {
          "value": "281 Belmont Avenue, Cloverdale",
          "status": "derived",
          "derivation": {
            "method": "format-address",
            "inputs": [
              "/content/scheme/address/parts/0/value",
              "/content/scheme/address/parts/1/label",
              "/content/scheme/address/parts/2/label"
            ]
          }
        }
      },
      "ref": {
        "dataset": "SP-83687-1-1-0.00",
        "pointer": "/parcels/0/features/1",
        "id": "uuid:76177f2a-1b7f-47cb-8a02-9e0d501b6a6e"
      }
    },
    "lots": [
      {
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
        "entitlement": {
          "value": 117,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/2/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/2",
          "id": "uuid:e62621ed-1334-4890-964f-608ff68f7a17"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/3/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/3",
          "id": "uuid:8e5ca9ad-b00d-4871-a723-19b6456480f9"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 113,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/4/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/4",
          "id": "uuid:85da01f8-9625-4b1e-9f4d-a34c11313512"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/5/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/5",
          "id": "uuid:5e2823d1-2473-4417-8045-1089d2e86e64"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/6/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/6",
          "id": "uuid:b46b34d5-03dd-49d2-b677-31042c5ab3f3"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 113,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/7/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/7",
          "id": "uuid:c1a7f52f-1b21-4266-8167-d5f3169c6078"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/8/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/8",
          "id": "uuid:0df5a108-f5fe-433a-9934-b0162115248f"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 108,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/9/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/9",
          "id": "uuid:15e3af06-3035-4c0a-89c2-57c71b254ad5"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      },
      {
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
        "entitlement": {
          "value": 117,
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/parcels/0/features/10/properties/interests/0/entitlementPortion",
              "property": "https://w3id.org/ogc/ladm/parcels/entitlementPortion"
            }
          ]
        },
        "ref": {
          "dataset": "SP-83687-1-1-0.00",
          "pointer": "/parcels/0/features/10",
          "id": "uuid:79015221-adeb-482f-988b-ed47e57bc2a4"
        },
        "membershipEvidence": [
          "references",
          "containingPrimaryParcel",
          "schemeRef"
        ]
      }
    ],
    "basis": {
      "schedule": {
        "documentRef": "unit-entitlement-schedule",
        "conformsTo": "wa-approved-form:2021-47738"
      },
      "form": {
        "id": "wa-approved-form:2021-47738",
        "label": {
          "value": "Approved Schedule of Unit Entitlements Form number 2021-47738",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ]
        },
        "validFrom": {
          "value": "2021-07-07",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ],
          "lexicalValue": "2021-07-07/.."
        },
        "source": {
          "value": "wa-leg:mrdoc_48587.pdf",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
              "pointer": "",
              "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
            }
          ]
        }
      },
      "certification": {
        "annotationRef": "licensed-valuer-certification",
        "certifier": {
          "firstName": {
            "value": "Jordan",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/firstName"
              }
            ]
          },
          "lastName": {
            "value": "Example",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/lastName"
              }
            ]
          },
          "licensedValuerNumber": {
            "value": "00000",
            "status": "reported",
            "sourceRefs": [
              {
                "dataset": "SP-83687-1-1-0.00",
                "pointer": "/annotations/2/certifier/licensedValuerNumber"
              }
            ]
          }
        },
        "dateCertified": {
          "value": "2022-05-17",
          "status": "reported",
          "sourceRefs": [
            {
              "dataset": "SP-83687-1-1-0.00",
              "pointer": "/annotations/2/dateCertified"
            }
          ]
        },
        "documentRef": "unit-entitlement-schedule"
      }
    },
    "legislativeBasis": [
      {
        "value": "Approved under section 37, Schedule 2A clause 21T(1)(d) and Schedule 2A clause 31E(1)(c) of the Strata Titles Act 1985.",
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "https://linked.data.gov.au/def/csdm/wa-approved-form",
            "pointer": "",
            "id": "https://linked.data.gov.au/def/csdm/wa-approved-form/2021-47738"
          }
        ]
      }
    ],
    "totals": {
      "declared": {
        "value": 1000,
        "status": "reported",
        "sourceRefs": [
          {
            "dataset": "SP-83687-1-1-0.00",
            "pointer": "/parcels/0/features/1/properties/interests/0/entitlementTotal"
          }
        ]
      },
      "calculated": {
        "value": 1000,
        "status": "derived",
        "derivation": {
          "method": "sum",
          "inputs": [
            "/content/lots/0/entitlement",
            "/content/lots/1/entitlement",
            "/content/lots/2/entitlement",
            "/content/lots/3/entitlement",
            "/content/lots/4/entitlement",
            "/content/lots/5/entitlement",
            "/content/lots/6/entitlement",
            "/content/lots/7/entitlement",
            "/content/lots/8/entitlement"
          ]
        }
      },
      "lotCount": {
        "value": 9,
        "status": "derived",
        "derivation": {
          "method": "count",
          "inputs": [
            "/content/lots"
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
      "id": "entitlement-source-datatype",
      "definedBy": "csdm.reporting.adapters.wa-csdm",
      "category": "source-conformance",
      "severity": "info",
      "outcome": "fail",
      "message": "9 entitlementPortion value(s) are numbers; icsm.profiles.wa.wa-3d types them as strings (converted to integers here)",
      "targets": [
        "/content/lots/0/entitlement",
        "/content/lots/1/entitlement",
        "/content/lots/2/entitlement",
        "/content/lots/3/entitlement",
        "/content/lots/4/entitlement",
        "/content/lots/5/entitlement",
        "/content/lots/6/entitlement",
        "/content/lots/7/entitlement",
        "/content/lots/8/entitlement"
      ]
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
      "id": "lot-numbers-present",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "Every lot has a lot number"
    },
    {
      "id": "lot-numbers-unique",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "Lot numbers are unique"
    },
    {
      "id": "entitlements-present",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "All 9 lots have a unit entitlement"
    },
    {
      "id": "entitlements-valid",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "Every supplied unit entitlement is a single positive whole number"
    },
    {
      "id": "total-covers-all-lots",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "The calculated total includes all 9 lots",
      "targets": [
        "/content/totals/calculated"
      ]
    },
    {
      "id": "declared-total-present",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "The source declares a total of 1000",
      "targets": [
        "/content/totals/declared"
      ]
    },
    {
      "id": "total-matches-declared",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "error",
      "outcome": "pass",
      "message": "Calculated total 1000 equals the declared total 1000",
      "targets": [
        "/content/totals/calculated",
        "/content/totals/declared"
      ],
      "evidence": {
        "calculated": 1000,
        "declared": 1000
      }
    },
    {
      "id": "schedule-document-referenced",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "The schedule of unit entitlements is referenced: Schedule of Unit Entitlements - SP83687",
      "targets": [
        "/content/basis/schedule"
      ]
    },
    {
      "id": "document-hrefs-resolvable",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "generation",
      "severity": "info",
      "outcome": "not-evaluated",
      "message": "Not evaluated: document links are not resolved while the report is generated, and relative links have no defined base (D12)",
      "evidence": {
        "hrefs": [
          "documents/SP83687-unit-entitlement-schedule.pdf"
        ]
      }
    },
    {
      "id": "valuer-certification-present",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "warning",
      "outcome": "pass",
      "message": "Certified by licensed valuer Jordan Example (No. 00000) on 2022-05-17",
      "targets": [
        "/content/basis/certification"
      ]
    },
    {
      "id": "certification-linked-to-schedule",
      "definedBy": "csdm.reporting.reports.strata-entitlement",
      "category": "domain",
      "severity": "info",
      "outcome": "pass",
      "message": "The certification links to the schedule document",
      "targets": [
        "/content/basis/certification"
      ]
    }
  ],
  "status": "complete",
  "statusSummary": {
    "checks": 18,
    "failedErrors": 0,
    "failedWarnings": 0,
    "unevaluatedErrors": 0
  }
}

```

## Schema

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
description: 'Strata Scheme Entitlement Report. Extends the generic cadastral report
  envelope with the scheme, its

  lots and their unit entitlements, the declared and calculated totals, and the basis
  of the schedule

  (the lodged schedule document, its approved form, the valuer''s certification and
  the legislation).

  Stage 5 of the implementation plan: every value is a `ReportValue` carrying its
  status and provenance,

  and check results are recorded in `checks`.


  A `facts` stage report (source adapter output) holds source facts only and must
  not carry the derived

  totals (`calculated`, `lotCount`); a `complete` stage report (output of this block''s
  `complete`

  transform) must carry them.

  '
allOf:
- $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml
- type: object
  properties:
    reportType:
      const: csdm.reporting.reports.strata-entitlement
    content:
      type: object
      required:
      - scheme
      - lots
      properties:
        scheme:
          type: object
          required:
          - schemeNumber
          properties:
            schemeNumber:
              description: Scheme (plan) number, e.g. SP83687.
              allOf:
              - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
              - properties:
                  value:
                    type:
                    - string
                    - 'null'
                    minLength: 1
                    x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/schemeNumber
            schemeName:
              description: Name of the scheme.
              $ref: '#/$defs/TextValue'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/schemeName
            address:
              description: Address of the scheme.
              type: object
              properties:
                parts:
                  description: The address parts as supplied, in order, with a label
                    where one is needed.
                  type: array
                  items:
                    type: object
                    required:
                    - partType
                    properties:
                      partType:
                        description: Address part type (an IRI or CURIE, e.g. `apt:road`).
                        type: string
                        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/addressPartType
                        x-jsonld-type: '@vocab'
                      value:
                        description: The part's value as supplied (a literal, a code
                          or an `@id` object).
                        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/addressPartValue
                        x-jsonld-type: '@json'
                      label:
                        description: Human-readable label of a coded value (road name,
                          locality name).
                        $ref: '#/$defs/TextValue'
                        x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/addressPartLabel
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/addressPart
                  x-jsonld-container: '@list'
                formatted:
                  description: Single-line address, derived from the parts (e.g. "281
                    Belmont Avenue, Cloverdale").
                  $ref: '#/$defs/TextValue'
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/formattedAddress
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/address
            ref:
              $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#SourceRef
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/scheme
        lots:
          description: 'One entry per member lot of the scheme, ordered by lot number.
            May be empty: a scheme whose

            members cannot be identified still produces a report, which its checks
            mark `invalid`.

            '
          type: array
          items:
            type: object
            required:
            - lotNumber
            - entitlement
            properties:
              lotNumber:
                description: Lot number as it appears in the source.
                allOf:
                - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
                - properties:
                    value:
                      type:
                      - string
                      - 'null'
                      x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/lotNumber
              entitlement:
                description: Unit entitlement of the lot, a positive whole number.
                allOf:
                - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
                - properties:
                    value:
                      type:
                      - integer
                      - 'null'
                      minimum: 1
                      x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/unitEntitlement
              ref:
                description: The lot parcel in the source (or, if it could not be
                  found, the reference to it).
                $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#SourceRef
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/sourceRef
              membershipEvidence:
                description: 'The source links that associate the lot with the scheme.
                  The first is the authoritative

                  one that made it a member; the others corroborate it. Values are
                  defined by the source

                  adapter (for the WA 3D CSDM: `references`, `containingPrimaryParcel`,
                  `schemeRef`).

                  '
                type: array
                items:
                  type: string
                x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/membershipEvidence
                x-jsonld-container: '@set'
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/lot
          x-jsonld-container: '@set'
        basis:
          description: What the unit entitlements rest on.
          type: object
          properties:
            schedule:
              description: The lodged schedule of unit entitlements.
              type: object
              required:
              - documentRef
              properties:
                documentRef:
                  description: The schedule document's `id` in the report's `documents`.
                  type: string
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/documentRef
                conformsTo:
                  description: The approved form the schedule follows (an IRI or CURIE).
                  type: string
                  x-jsonld-id: http://purl.org/dc/terms/conformsTo
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/schedule
            form:
              description: The approved form named by the schedule's `conformsTo`.
              type: object
              required:
              - id
              properties:
                id:
                  description: The form, as named by the source (an IRI or CURIE).
                  type: string
                  x-jsonld-id: http://purl.org/dc/terms/identifier
                label:
                  $ref: '#/$defs/TextValue'
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/formLabel
                validFrom:
                  description: Date from which the form is approved for use.
                  $ref: '#/$defs/TextValue'
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/formValidFrom
                source:
                  description: Where the approved form is published.
                  $ref: '#/$defs/TextValue'
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/formPublishedAt
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/approvedForm
            certification:
              description: The licensed valuer's certification of the schedule.
              type: object
              required:
              - annotationRef
              properties:
                annotationRef:
                  description: The certification's `id` in the report's `annotations`.
                  type: string
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/annotationRef
                certifier:
                  type: object
                  properties:
                    firstName:
                      $ref: '#/$defs/TextValue'
                      x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/certifierFirstName
                    lastName:
                      $ref: '#/$defs/TextValue'
                      x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/certifierLastName
                    licensedValuerNumber:
                      $ref: '#/$defs/TextValue'
                      x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/licensedValuerNumber
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/certifier
                dateCertified:
                  $ref: '#/$defs/TextValue'
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/dateCertified
                documentRef:
                  description: The document the certification links to (its `id` in
                    `documents`), if any.
                  type: string
                  x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/documentRef
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/certification
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/basis
        legislativeBasis:
          description: The legislation the schedule is made under, as stated for its
            approved form.
          type: array
          items:
            $ref: '#/$defs/TextValue'
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/legislativeBasis
          x-jsonld-container: '@set'
        totals:
          description: 'The declared total (a source fact) and the derived values
            added by the `complete` transform.

            '
          type: object
          properties:
            declared:
              description: Total unit entitlement declared by the source for the scheme.
              allOf:
              - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
              - properties:
                  value:
                    type:
                    - integer
                    - 'null'
                    minimum: 1
                    x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/declaredTotal
            calculated:
              description: Sum of the entitlements of all lots that have a usable
                one.
              allOf:
              - $ref: '#/$defs/DerivedCount'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/calculatedTotal
            lotCount:
              description: Number of member lots.
              allOf:
              - $ref: '#/$defs/DerivedCount'
              x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/lotCount
          x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/totals
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
        - totals
        properties:
          totals:
            required:
            - calculated
            - lotCount
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/totals
  else:
    properties:
      content:
        properties:
          totals:
            not:
              anyOf:
              - required:
                - calculated
              - required:
                - lotCount
            x-jsonld-id: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/totals
$defs:
  TextValue:
    description: A ReportValue whose value is text.
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - properties:
        value:
          type:
          - string
          - 'null'
          minLength: 1
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
  DerivedCount:
    allOf:
    - $ref: https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/cadastral-report/schema.yaml#ReportValue
    - required:
      - value
      properties:
        status:
          const: derived
        value:
          type: integer
          minimum: 0
          x-jsonld-id: http://www.w3.org/1999/02/22-rdf-syntax-ns#value
x-jsonld-prefixes:
  cr: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/cadastral-report/
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  dcterms: http://purl.org/dc/terms/
  se: https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/
  apt: https://linked.data.gov.au/def/addr-part-types/

```

Links to the schema:

* YAML version: [schema.yaml](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/reports/strata-entitlement/schema.json)
* JSON version: [schema.json](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/reports/strata-entitlement/schema.yaml)


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
          "@id": "se:schemeNumber"
        },
        "schemeName": {
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
          "@id": "se:schemeName"
        },
        "address": {
          "@context": {
            "parts": {
              "@context": {
                "partType": {
                  "@id": "se:addressPartType",
                  "@type": "@vocab"
                },
                "value": {
                  "@id": "se:addressPartValue",
                  "@type": "@json"
                },
                "label": {
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
                  "@id": "se:addressPartLabel"
                }
              },
              "@id": "se:addressPart",
              "@container": "@list"
            },
            "formatted": {
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
              "@id": "se:formattedAddress"
            }
          },
          "@id": "se:address"
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
      "@id": "se:scheme"
    },
    "lots": {
      "@context": {
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
          "@id": "se:lotNumber"
        },
        "entitlement": {
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
          "@id": "se:unitEntitlement"
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
        },
        "membershipEvidence": {
          "@id": "se:membershipEvidence",
          "@container": "@set"
        }
      },
      "@id": "se:lot",
      "@container": "@set"
    },
    "basis": {
      "@context": {
        "schedule": {
          "@context": {
            "documentRef": "cr:documentRef",
            "conformsTo": "dcterms:conformsTo"
          },
          "@id": "se:schedule"
        },
        "form": {
          "@context": {
            "id": "dcterms:identifier",
            "label": {
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
              "@id": "se:formLabel"
            },
            "validFrom": {
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
              "@id": "se:formValidFrom"
            },
            "source": {
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
              "@id": "se:formPublishedAt"
            }
          },
          "@id": "se:approvedForm"
        },
        "certification": {
          "@context": {
            "certifier": {
              "@context": {
                "firstName": {
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
                    }
                  },
                  "@id": "se:certifierFirstName"
                },
                "lastName": {
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
                    }
                  },
                  "@id": "se:certifierLastName"
                },
                "licensedValuerNumber": {
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
                    }
                  },
                  "@id": "se:licensedValuerNumber"
                }
              },
              "@id": "se:certifier"
            },
            "dateCertified": {
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
                }
              },
              "@id": "se:dateCertified"
            },
            "documentRef": "cr:documentRef"
          },
          "@id": "se:certification"
        }
      },
      "@id": "se:basis"
    },
    "legislativeBasis": {
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
      "@id": "se:legislativeBasis",
      "@container": "@set"
    },
    "totals": {
      "@context": {
        "declared": {
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
          "@id": "se:declaredTotal"
        },
        "calculated": {
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
          "@id": "se:calculatedTotal"
        },
        "lotCount": {
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
          "@id": "se:lotCount"
        }
      },
      "@id": "se:totals"
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
    "se": "https://ogcincubator.github.io/bblocks-3d-csdm-reporting/def/strata-entitlement/",
    "apt": "https://linked.data.gov.au/def/addr-part-types/",
    "@version": 1.1
  }
}
```

You can find the full JSON-LD context here:
[context.jsonld](https://andrewhunter2066.github.io/bblocks-3d-csdm-reporting/build/annotated/reporting/reports/strata-entitlement/context.jsonld)


# For developers

The source code for this Building Block can be found in the following repository:

* URL: [https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting](https://github.com/andrewhunter2066/bblocks-3d-csdm-reporting)
* Path: `_sources/reports/strata-entitlement`

