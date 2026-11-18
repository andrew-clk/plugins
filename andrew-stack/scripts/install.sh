#!/usr/bin/env bash
# Installs Andrew Stack tools and policy for local coding agents. Safe to rerun.
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
# Match whole lines only. An orphan begin marker belongs to the existing file
# and must never consume user text through a later, complete managed block.
pattern = re.compile(rf"^{re.escape(begin)}$\n(?:(?!^{re.escape(begin)}$).)*?^{re.escape(end)}$", re.M | re.S)
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

echo "== Project tools"
run bash "$here/install-project-tools.sh"

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
  claude_config="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  managed_block "$claude_config/CLAUDE.md" "$stack/policy/engineering.md"
  sync_hook="$claude_config/hooks/git-sync-on-start.sh"
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
  codex_config="${CODEX_HOME:-$HOME/.codex}"
  managed_block "$codex_config/AGENTS.md" "$stack/policy/engineering.md"

  # Register the guard as a global Codex hook too, from a stable path, so it does not
  # depend on Codex loading plugin hooks or on the plugin cache's version folder.
  run mkdir -p "$codex_config/hooks"
  run install -m 0755 "$stack/hooks/guard.py" "$codex_config/hooks/andrew_guard.py"
  run python3 -I - "$codex_config/hooks.json" <<'PY'
import json, pathlib, shlex, sys
path = pathlib.Path(sys.argv[1])
config = json.loads(path.read_text()) if path.exists() else {}
pre = config.setdefault("hooks", {}).setdefault("PreToolUse", [])
default_command = 'python3 -I "$HOME/.codex/hooks/andrew_guard.py"'
command = default_command
if path.parent.resolve() != (pathlib.Path.home() / ".codex").resolve():
    guard = path.parent.resolve() / "hooks/andrew_guard.py"
    command = f"python3 -I {shlex.quote(str(guard))}"
for group in pre:
    group["hooks"] = [hook for hook in group.get("hooks", []) if hook.get("command") not in {command, default_command}]
pre[:] = [group for group in pre if group.get("hooks")]
pre.append({"matcher": "Bash", "hooks": [{"type": "command", "command": command, "timeout": 10,
                                          "statusMessage": "andrew-stack guard"}]})
path.write_text(json.dumps(config, indent=2) + "\n")
print(f"  registered andrew-stack guard in {path}")
PY
else
  echo "  codex CLI not found, skipped"
fi

if command -v gemini >/dev/null || [[ -d "$HOME/.gemini" ]]; then
  managed_block "$HOME/.gemini/GEMINI.md" "$stack/policy/engineering.md"
fi
hermes_config="${HERMES_HOME:-$HOME/.hermes}"
if command -v hermes >/dev/null || [[ -d "$hermes_config" ]]; then
  managed_block "$hermes_config/SOUL.md" "$stack/policy/engineering.md"
  if [[ "$(basename "$(dirname "$hermes_config")")" != profiles && -f "$hermes_config/active_profile" ]]; then
    profile="$(tr '[:upper:]' '[:lower:]' < "$hermes_config/active_profile")"
    if [[ "$profile" != default && "$profile" =~ ^[a-z0-9][a-z0-9_-]{0,63}$ && -d "$hermes_config/profiles/$profile" ]]; then
      managed_block "$hermes_config/profiles/$profile/SOUL.md" "$stack/policy/engineering.md"
    fi
  fi
fi

# Grok Bot stores skills per agent. Export a standalone file for its Skills UI.
grok_skill="$HOME/.agents/skills/andrew-stack/SKILL.md"
run mkdir -p "$(dirname "$grok_skill")"
run python3 -I - "$stack/policy/engineering.md" "$grok_skill" <<'PYTHON'
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:])
header = "---\nname: andrew-stack\ndescription: Apply Andrew's engineering policy when working on an app project.\n---\n"
if target.exists() and not target.read_text().startswith(header):
    raise SystemExit(f"Custom skill already exists at {target}. Preserved it.")
target.write_text(header + "\n" + source.read_text())
PYTHON

echo "Grok Bot: add the exported skill to each coding agent in its Skills settings: $grok_skill"
echo "Restart your coding agents. Codex asks you to trust changed hooks on its next start."
