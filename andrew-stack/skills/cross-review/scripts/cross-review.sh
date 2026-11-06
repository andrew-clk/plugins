#!/usr/bin/env bash
# Usage: cross-review.sh <codex|claude> <prompt-file> [repo-dir]
# Runs the other harness read-only on the prompt and prints its review.
# The review is also saved next to the prompt as <prompt-file>.<reviewer>.md.
set -euo pipefail

reviewer="${1:-}"
prompt="${2:-}"
repo="${3:-$PWD}"

if [[ -z "$reviewer" || ! -f "$prompt" ]]; then
  echo "usage: cross-review.sh <codex|claude> <prompt-file> [repo-dir]" >&2
  exit 64
fi
out="$prompt.$reviewer.md"

case "$reviewer" in
  codex)
    command -v codex >/dev/null || { echo "codex CLI not found" >&2; exit 69; }
    codex exec --sandbox read-only --ephemeral --skip-git-repo-check -C "$repo" -o "$out" - <"$prompt" >/dev/null
    ;;
  claude)
    command -v claude >/dev/null || { echo "claude CLI not found" >&2; exit 69; }
    (cd "$repo" && claude -p --permission-mode plan --no-session-persistence \
      --allowedTools "Read" "Grep" "Glob" "Bash(git diff:*)" "Bash(git log:*)" "Bash(git show:*)" \
      <"$prompt") >"$out"
    ;;
  *)
    echo "reviewer must be codex or claude" >&2
    exit 64
    ;;
esac

[[ -s "$out" ]] || { echo "$reviewer returned an empty review" >&2; exit 70; }
cat "$out"
