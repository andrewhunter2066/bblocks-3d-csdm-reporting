#!/bin/bash
# Check a cadastral source dataset against a published source-profile building block.
#
# Builds a throwaway register in a temporary directory containing one block whose schema is
# just `$ref: bblocks://<profile>`, with the dataset as a test resource. The OGC Building Blocks
# postprocessor then validates it exactly as the profile's own register would: JSON Schema,
# semantic uplift with the profile's JSON-LD context, and the profile's (inherited) SHACL shapes.
#
# Usage:
#   scripts/check_source_conformance.sh [DATASET.json] [PROFILE_ID] [REPORT_DIR]
# Defaults:
#   DATASET.json  data/examples/json/built-strata-example-1.json
#   PROFILE_ID    icsm.profiles.wa.wa-3d   (switch to the wa-built-strata block once published)
#   REPORT_DIR    build-local/source-conformance
#
# Exit status: 0 = dataset conforms, 1 = dataset does not conform, 2 = the check itself failed.
# Requires Docker.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATASET="${1:-$REPO_ROOT/data/examples/json/built-strata-example-1.json}"
PROFILE_ID="${2:-icsm.profiles.wa.wa-3d}"
REPORT_DIR="${3:-$REPO_ROOT/build-local/source-conformance}"
IMAGE="ghcr.io/opengeospatial/bblocks-postprocess:${BBP_IMAGE_TAG:-latest}"
WA_REGISTER="https://surroundaustralia.github.io/3d-csdm-profile-wa/build/register.json"

if [ ! -f "$DATASET" ]; then
  echo "Dataset not found: $DATASET" >&2
  exit 2
fi

WORK="$(mktemp -d)"
# The container writes root-owned files on Linux/WSL, so clean up through Docker as well.
cleanup() {
  docker run --rm -v "$WORK:/work" --entrypoint sh "$IMAGE" -c 'rm -rf /work/* /work/.[!.]*' >/dev/null 2>&1 || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT
NAME="$(basename "$DATASET" .json)"

mkdir -p "$WORK/_sources/source/tests"
cp "$DATASET" "$WORK/_sources/source/tests/$NAME.json"

cat > "$WORK/bblocks-config.yaml" <<EOF
name: Source conformance check (temporary)
identifier-prefix: csdm.conformance.
imports:
  - default
  - $WA_REGISTER
EOF

cat > "$WORK/_sources/source/bblock.json" <<EOF
{
  "name": "Source conformance check against $PROFILE_ID",
  "abstract": "Temporary block used only to validate a source dataset against $PROFILE_ID.",
  "status": "under-development",
  "dateTimeAddition": "2026-10-01T00:00:00Z",
  "itemClass": "schema",
  "version": "0.1"
}
EOF

cat > "$WORK/_sources/source/schema.yaml" <<EOF
\$schema: https://json-schema.org/draft/2020-12/schema
\$ref: bblocks://$PROFILE_ID
EOF

echo "Validating $(basename "$DATASET") against $PROFILE_ID ..."
if ! docker run --rm --workdir /workspace -v "$WORK:/workspace" "$IMAGE" \
    --steps annotate,jsonld,tests,register --fail-on-error false --skip-permissions true \
    > "$WORK/postprocess.log" 2>&1; then
  echo "Postprocessor run failed; log follows:" >&2
  cat "$WORK/postprocess.log" >&2
  exit 2
fi

mkdir -p "$REPORT_DIR"
rm -rf "${REPORT_DIR:?}/"*
cp -r "$WORK/build-local/tests/." "$REPORT_DIR/"
cp "$WORK/postprocess.log" "$REPORT_DIR/postprocess.log"

echo
set +e
docker run --rm -v "$REPORT_DIR:/report" -v "$(dirname "$DATASET"):/dataset:ro" \
  -v "$REPO_ROOT/scripts:/scripts:ro" --entrypoint /venv/bin/python "$IMAGE" \
  /scripts/summarise_conformance.py /report/report.json "/dataset/$(basename "$DATASET")" "$PROFILE_ID" \
  "$WA_REGISTER" https://opengeospatial.github.io/bblocks/register.json \
  | tee "$REPORT_DIR/summary.txt"
STATUS=${PIPESTATUS[0]}
set -e
echo "Full report: $REPORT_DIR/report.html (summary saved to $REPORT_DIR/summary.txt)"
exit "$STATUS"
