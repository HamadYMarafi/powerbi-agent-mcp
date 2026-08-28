#!/usr/bin/env bash
# Install the powerbi-dashboard-* skills into a Claude Code skills directory.
#
# Usage:
#   bash skills/install.sh                    # installs to ~/.claude/skills
#   CLAUDE_SKILLS_DIR=/some/dir bash skills/install.sh
#
# Safe to re-run: it only ever writes the three skill folders below.
set -euo pipefail

# Resolve this script's own directory so it works from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

SKILLS=(
  powerbi-dashboard-build
  powerbi-dashboard-review
  powerbi-dashboard-verify
)

mkdir -p "$DEST_DIR"

echo "Installing skills to: $DEST_DIR"
for skill in "${SKILLS[@]}"; do
  src="$SCRIPT_DIR/$skill"
  if [ ! -d "$src" ]; then
    echo "  skip: $skill (no such folder next to install.sh: $src)" >&2
    continue
  fi
  cp -R "$src" "$DEST_DIR/"
  echo "  installed: $DEST_DIR/$skill"
done

cat <<'EOF'

Next steps:
  1. Install Microsoft's Power BI / Fabric skills (PBIR and semantic-model
     detail these skills rely on for authoring mechanics):
       /plugin marketplace add microsoft/skills-for-fabric
       /plugin install powerbi-authoring@fabric-collection
  2. Copy this repo's rules/CLAUDE.md into your own project's CLAUDE.md so the
     guardrails (never touch an item you did not create, model is read-only,
     no refresh triggers, theme lock once approved) apply automatically.
EOF
