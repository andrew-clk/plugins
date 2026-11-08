#!/usr/bin/env bash
# andrew-stack SessionStart: fetch remote refs without changing shared local work.
set -uo pipefail

input=$(cat)
dir=$(printf '%s' "$input" | python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("cwd", ""))' 2>/dev/null) || dir=""
cd "${dir:-${CLAUDE_PROJECT_DIR:-$PWD}}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

report() {
  python3 -I - "$1" <<'PY'
import json, sys
message = "GitHub sync: " + sys.argv[1]
print(json.dumps({"systemMessage": message, "hookSpecificOutput": {
    "hookEventName": "SessionStart", "additionalContext": message}}))
PY
  exit 0
}

export GIT_TERMINAL_PROMPT=0 GIT_OPTIONAL_LOCKS=0
if ! git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=10 fetch --quiet --no-tags origin '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null; then
  report "fetch failed. Local work is untouched. Independent local investigation can continue; verify origin before publishing."
fi
primary=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null) || primary="origin/main"
git rev-parse --verify --quiet "$primary" >/dev/null || report "fetched remote refs. No default remote branch found; local work is untouched."
counts=$(git rev-list --left-right --count "HEAD...$primary" 2>/dev/null) || report "fetched remote refs. Local work is untouched."
read -r ahead behind <<<"$counts"
dirty=$(git status --porcelain | wc -l | tr -d ' ')
report "fetched $primary. Current HEAD has $ahead local-only and $behind remote-only commit(s); $dirty uncommitted path(s). No checkout, local branch, or index was changed. Continue independent work in an owned worktree; integrate and verify before publishing."
