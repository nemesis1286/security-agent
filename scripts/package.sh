#!/usr/bin/env bash
#
# Package the Travel Anomaly Triage Agent for Security Store submission.
# Produces a .zip file that conforms to the Security Store package schema.
#
# Usage: ./scripts/package.sh [version]
# Example: ./scripts/package.sh 1.0.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION="${1:-1.0.0}"

# Validate semantic versioning format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: Version must follow semantic versioning (X.Y.Z). Got: $VERSION"
    exit 1
fi

BUILD_DIR="$PROJECT_ROOT/build"
PACKAGE_DIR="$BUILD_DIR/TravelAnomalyTriageAgent-$VERSION"
OUTPUT_FILE="$BUILD_DIR/TravelAnomalyTriageAgent-$VERSION.zip"

echo "=== Packaging Travel Anomaly Triage Agent v$VERSION ==="

# Clean previous build
rm -rf "$PACKAGE_DIR" "$OUTPUT_FILE"
mkdir -p "$PACKAGE_DIR"

# ---- Copy agent manifest ----
cp "$PROJECT_ROOT/manifest/AgentManifest.yaml" "$PACKAGE_DIR/AgentManifest.yaml"

# ---- Copy OpenAPI specs ----
cp "$PROJECT_ROOT/manifest/skills/openapispec_1.yaml" "$PACKAGE_DIR/openapispec_1.yaml"
cp "$PROJECT_ROOT/manifest/skills/openapispec_2.yaml" "$PACKAGE_DIR/openapispec_2.yaml"

# ---- Copy KQL template ----
# Security Store expects template files named template_<N>.txt
cp "$PROJECT_ROOT/manifest/skills/kql/analyze_signin_history.kql" "$PACKAGE_DIR/template_1.txt"

# ---- Create the zip ----
cd "$BUILD_DIR"
zip -r "$OUTPUT_FILE" "TravelAnomalyTriageAgent-$VERSION/"

echo ""
echo "=== Package contents ==="
unzip -l "$OUTPUT_FILE"

echo ""
echo "=== Done ==="
echo "Package: $OUTPUT_FILE"
echo "Version: $VERSION"
echo ""
echo "Next steps:"
echo "  1. Test by uploading AgentManifest.yaml to Security Copilot standalone"
echo "  2. Submit $OUTPUT_FILE via Partner Center as a SaaS offer"
