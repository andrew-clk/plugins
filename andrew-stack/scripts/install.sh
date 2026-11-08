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
    --source) [[ $# -ge 2 ]] || { echo "--source requires a value" >&2; exit 64; }; source_ref="$2"; shift 2 ;;
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
outside = pattern.sub("", text)
if any(phrase in outside for phrase in ("git-sync-on-start", "git pull --ff-only", "resolve it before starting work")):
    print(f"  WARNING: legacy Git policy outside the managed block in {target}; review it for conflicts. Preserved unchanged.", file=sys.stderr)
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
  installed="$(claude plugin list --json)"
  for plugin in pstack andrew-stack; do
    action="$(printf '%s' "$installed" | python3 -I -c '
import json, sys
entries = json.load(sys.stdin)
print("update" if any(p.get("id") == sys.argv[1] and p.get("scope") == "user" for p in entries) else "install")
' "$plugin@$market")"
    run claude plugin "$action" "$plugin@$market" --scope user
  done
  managed_block "$HOME/.claude/CLAUDE.md" "$stack/policy/engineering.md"
  sync_hook="$HOME/.claude/hooks/git-sync-on-start.sh"
  if [[ -f "$sync_hook" ]]; then
    if grep -Fxq '# Claude Code SessionStart hook: sync with GitHub before any work starts.' "$sync_hook" ||
       grep -Fxq '# andrew-stack SessionStart: fetch remote refs without changing shared local work.' "$sync_hook"; then
      run install -m 0755 "$stack/hooks/git-sync-on-start.sh" "$sync_hook"
    else
      echo "  WARNING: custom SessionStart hook preserved at $sync_hook; review shared-checkout mutations."
    fi
  fi
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
  managed_block "$HOME/.codex/AGENTS.md" "$stack/policy/engineering.md"

  # Register the guard as a global Codex hook too, from a stable path, so it does not
  # depend on Codex loading plugin hooks or on the plugin cache's version folder.
  run mkdir -p "$HOME/.codex/hooks"
  run install -m 0755 "$stack/hooks/guard.py" "$HOME/.codex/hooks/andrew_guard.py"
  run python3 -I - "$HOME/.codex/hooks.json" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
config = json.loads(path.read_text()) if path.exists() else {}
pre = config.setdefault("hooks", {}).setdefault("PreToolUse", [])
command = 'python3 -I "$HOME/.codex/hooks/andrew_guard.py"'
for group in pre:
    group["hooks"] = [hook for hook in group.get("hooks", []) if hook.get("command") != command]
pre[:] = [group for group in pre if group.get("hooks")]
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
