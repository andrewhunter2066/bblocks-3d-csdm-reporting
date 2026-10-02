#!/usr/bin/env python3
"""Generate synthetic variants of the SP83687 reporting fixture, used as adapter examples.

Each variant changes one thing in the trimmed SP83687 fixture so a report behaviour can be shown and
tested on otherwise realistic data. They are synthetic: they are not lodged survey data.

Usage (from the repository root):
    python3 scripts/make_fixture_variants.py
"""
import copy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / '_sources/adapters/wa-csdm/examples'
TEST_FIXTURES = REPO / 'tests-py/fixtures'
BASE = EXAMPLES / 'sp83687-entitlement.json'
LOT_INTEREST_TYPE = 'wa-interest-type:strata-lot'


def lot_feature(csd, lot_number):
    for collection in csd['parcels']:
        for feature in collection['features']:
            props = feature['properties']
            parts = props.get('appellation', {}).get('hasPart', [])
            if (props.get('parcelPurpose') == 'wa-parcel-purpose:strata-lot'
                    and any(p.get('type') == 'lotNumber' and p.get('label') == lot_number for p in parts)):
                return feature
    raise KeyError(f'Lot {lot_number} not found')


def missing_entitlement(csd):
    """Lot 4 has its strata-lot interest but no entitlementPortion."""
    for interest in lot_feature(csd, '4')['properties']['interests']:
        if interest.get('interestType') == LOT_INTEREST_TYPE:
            del interest['entitlementPortion']
    return csd


def total_mismatch(csd):
    """The scheme declares a total of 1100, but the lot entitlements sum to 1000."""
    for collection in csd['parcels']:
        for feature in collection['features']:
            if feature['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-scheme':
                for interest in feature['properties']['interests']:
                    if interest.get('interestType') == 'wa-interest-type:strata-scheme':
                        interest['entitlementTotal'] = 1100
    return csd


def no_scheme(csd):
    """No parcel is a strata scheme: the report cannot be generated (a generation error)."""
    for collection in csd['parcels']:
        for feature in collection['features']:
            if feature['properties'].get('parcelPurpose') == 'wa-parcel-purpose:strata-scheme':
                feature['properties']['parcelPurpose'] = 'wa-parcel-purpose:lot'
    return csd


# Adapter examples are run through the adapter's transforms on every build, so a variant whose
# transform is expected to raise (no-scheme) is a test fixture instead: a failing example would log
# a warning on every build.
VARIANTS = {
    EXAMPLES / 'missing-entitlement.json': missing_entitlement,
    EXAMPLES / 'total-mismatch.json': total_mismatch,
    TEST_FIXTURES / 'no-scheme.json': no_scheme,
}


def main():
    base = json.loads(BASE.read_text(encoding='utf-8'))
    for path, make in VARIANTS.items():
        variant = make(copy.deepcopy(base))
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(variant, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f'wrote {path.relative_to(REPO)}')


if __name__ == '__main__':
    main()
