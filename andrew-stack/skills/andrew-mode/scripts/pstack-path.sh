#!/usr/bin/env bash
# Prints the installed pstack folder (the one holding skills/ and docs/).
# Prefers the pstack that sits beside this andrew-stack install, then the newest
# pstack in either harness's plugin cache, then a dev checkout of the repo.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_root="$(cd "$here/../../.." && pwd)"

newest() {
  local dir best=""
  for dir in "$@"; do
    [[ -f "$dir/skills/poteto-mode/SKILL.md" ]] || continue
    best="$dir"
  done
  [[ -n "$best" ]] && printf '%s\n' "${best%/}"
}

sibling="$(newest $(ls -d "$plugin_root"/../../pstack/*/ 2>/dev/null | sort -V))"
[[ -n "$sibling" ]] && { (cd "$sibling" && pwd); exit 0; }

cached="$(newest $(ls -d "$HOME"/.claude/plugins/cache/*/pstack/*/ "$HOME"/.codex/plugins/cache/*/pstack/*/ 2>/dev/null | sort -V))"
[[ -n "$cached" ]] && { printf '%s\n' "$cached"; exit 0; }

dev="$(newest "$plugin_root/../harness/pstack/claude-code")"
[[ -n "$dev" ]] && { (cd "$dev" && pwd); exit 0; }
exit 1
