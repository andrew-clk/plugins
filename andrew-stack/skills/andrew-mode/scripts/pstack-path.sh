#!/usr/bin/env bash
# Resolve the companion pstack package, including installations in custom config roots.
set -eu
python3 -I - "${BASH_SOURCE[0]}" <<'PY'
import os
import re
import sys
from pathlib import Path

plugin = Path(sys.argv[1]).resolve().parents[3]
home = Path.home()
claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or home / ".claude")
codex = Path(os.environ.get("CODEX_HOME") or home / ".codex")

def version_key(path):
    return [int(n) for n in re.findall(r"\d+", path.name)]

for candidates in (
    (plugin.parent.parent / "pstack").glob("*"),
    [*claude.glob("plugins/cache/*/pstack/*"), *codex.glob("plugins/cache/*/pstack/*")],
    [plugin.parent / "harness/pstack/claude-code"],
):
    for candidate in sorted(candidates, key=version_key, reverse=True):
        if (candidate / "skills/poteto-mode/SKILL.md").is_file():
            print(candidate.resolve())
            sys.exit(0)
sys.exit(1)
PY
