#!/usr/bin/env python3
"""Derive a small reporting fixture from a full WA 3D CSDM CSD (JSON) file.

The topological geometry collections (points, edges, rings, faces, shells, occupation
features) make up >95% of a CSD but are not read by the reports. This script keeps every
collection's own metadata but empties its `features`, so the fixture keeps the CSD
structure while staying small enough to run through the postprocessor on every build.

Parcels, solids (small, and needed by the Scheme Composition Report to tell whether a
lot's component solids exist), supporting documents, annotations and provenance are kept
unchanged. Solids still reference the removed shells, so the fixture is NOT expected to
conform to the WA profile.

Usage:
    python3 scripts/trim_csdm_fixture.py SOURCE.json TARGET.json
"""
import json
import sys

GEOMETRY_COLLECTIONS = ('points', 'vectorObservations', 'edges', 'rings', 'faces',
                        'shells', 'occupationFeatures')


def trim(csd: dict) -> dict:
    trimmed = dict(csd)
    for key in GEOMETRY_COLLECTIONS:
        value = trimmed.get(key)
        if not isinstance(value, list):
            continue
        trimmed[key] = [
            {**collection, 'features': []} if isinstance(collection, dict) and 'features' in collection
            else collection
            for collection in value
        ]
    return trimmed


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding='utf-8') as f:
        csd = json.load(f)
    with open(argv[2], 'w', encoding='utf-8', newline='\n') as f:
        json.dump(trim(csd), f, indent=2, ensure_ascii=False)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
