#!/usr/bin/env bash
# SCP transfer of the audited deploy bundle + checksum verification on target.
# Usage: bash scripts/deploy_bundle_scp.sh user@host /opt/scp-staging
set -euo pipefail
TARGET="${1:?usage: deploy_bundle_scp.sh user@host /dest/dir}"
DEST="${2:?usage: deploy_bundle_scp.sh user@host /dest/dir}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$HERE/reports/deploy-bundle"
scp -r "$BUNDLE" "$TARGET:$DEST/"
ssh "$TARGET" "cd '$DEST/deploy-bundle' && sha256sum -c SHA256SUMS.txt"
echo "[OK] bundle transferred and checksums verified on $TARGET:$DEST/deploy-bundle"
