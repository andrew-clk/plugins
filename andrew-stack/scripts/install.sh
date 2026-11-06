#!/usr/bin/env bash
# Installs pstack + andrew-stack into Claude Code and Codex. Safe to rerun.
#   install.sh [--dry-run] [--source <owner/repo | local path>]
# Default source is andrew-clk/plugins on GitHub. --source . installs from this clone.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stack="$(cd "$here/.." && pwd)"
source_ref="andrew-clk/plugins"
dry=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry=1; shift ;;
    --source) source_ref="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 64 ;;
  esac
done
[[ -d "$source_ref" ]] && source_ref="$(cd "$source_ref" && pwd)"
market="andrew-plugins"

run() {
  echo "+ $*"
  [[ $dry -eq 1 ]] || "$@"
}

managed_block() {
  # managed_block <file> <block-file>: replace or append the andrew-stack block in <file>.
  run python3 -I - "$1" "$2" <<'PY'
import pathlib, re, sys
target, block = pathlib.Path(sys.argv[1]).expanduser(), pathlib.Path(sys.argv[2]).read_text().strip()
begin, end = "<!-- andrew-stack:begin -->", "<!-- andrew-stack:end -->"
wrapped = f"{begin}\n{block}\n{end}"
text = target.read_text() if target.exists() else ""
pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
if pattern.search(text):
    text = pattern.sub(lambda _: wrapped, text)
elif text.strip():
    text = text.rstrip() + "\n\n" + wrapped + "\n"
else:
    text = wrapped + "\n"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(text)
print(f"  wrote andrew-stack block in {target}")
PY
}

echo "== Claude Code"
if command -v claude >/dev/null; then
  if claude plugin marketplace list 2>/dev/null | grep -q "$market"; then
    run claude plugin marketplace update "$market"
  else
    run claude plugin marketplace add "$source_ref"
  fi
  run claude plugin install "pstack@$market"
  run claude plugin install "andrew-stack@$market"
  claude_block="$(mktemp)"
  cat >"$claude_block" <<'EOF'
## Engineering style (andrew-stack)

For any non-trivial engineering work in a git repo, load the `andrew-stack:andrew-mode` skill before you start, and follow it. It layers on pstack. A question, a one-line edit, or work outside a repo does not need it. The repo's own `AGENTS.md` and `CLAUDE.md` win over it for verify, deploy, and `progress.md` rules.
EOF
  managed_block "$HOME/.claude/CLAUDE.md" "$claude_block"
else
  echo "  claude CLI not found, skipped"
fi

echo "== Codex"
if command -v codex >/dev/null; then
  if codex plugin marketplace list 2>/dev/null | grep -q "^$market "; then
    run codex plugin marketplace upgrade "$market"
  else
    run codex plugin marketplace add "$source_ref"
  fi
  run codex plugin add "pstack@$market"
  run codex plugin add "andrew-stack@$market"
  managed_block "$HOME/.codex/AGENTS.md" "$stack/codex/AGENTS.md"

  # Register the guard as a global Codex hook too, from a stable path, so it does not
  # depend on Codex loading plugin hooks or on the plugin cache's version folder.
  run install -m 0755 "$stack/hooks/guard.py" "$HOME/.codex/hooks/andrew_guard.py"
  run python3 -I - "$HOME/.codex/hooks.json" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
config = json.loads(path.read_text()) if path.exists() else {}
pre = config.setdefault("hooks", {}).setdefault("PreToolUse", [])
command = 'python3 -I "$HOME/.codex/hooks/andrew_guard.py"'
pre[:] = [g for g in pre if not any(h.get("command") == command for h in g.get("hooks", []))]
pre.append({"matcher": "Bash", "hooks": [{"type": "command", "command": command, "timeout": 10,
                                          "statusMessage": "andrew-stack guard"}]})
path.write_text(json.dumps(config, indent=2) + "\n")
print(f"  registered andrew-stack guard in {path}")
PY
else
  echo "  codex CLI not found, skipped"
fi

echo
echo "Done. Restart Claude Code and Codex. Codex asks you to trust the changed hooks on its next start."
