#!/usr/bin/env bash
# Install shared skills outside application repositories. Requires uv, Python and curl.
set -euo pipefail
for tool in uv python3 curl; do
  command -v "$tool" >/dev/null || { echo "Missing $tool; install it and rerun Andrew Stack setup." >&2; exit 1; }
done

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
uv tool install --python 3.13 'graphifyy==0.9.112'
graphify_bin="$(uv tool dir --bin)/graphify"
# Graphify replaces references/ wholesale. Only let it do that in our staging area.
(cd "$stage" && "$graphify_bin" install --project --platform agents >/dev/null)
if ! command -v graphify >/dev/null; then
  echo "Add $(dirname "$graphify_bin") to PATH to invoke graphify in new sessions."
fi

curl -fsSL --retry 3 https://registry.npmjs.org/@dietrichgebert/ponytail/-/ponytail-5.3.3.tgz -o "$stage/ponytail.tgz"
python3 -I - "$stage" <<'PY'
import base64
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

stage = Path(sys.argv[1])
archive = stage / "ponytail.tgz"
expected = "Gq0ESMi1ZkcY+dvH1dyhOzR3+pYQ/LGW39E4dExcCzhaLe1AMPE43sPrW/JbEiaC986dUWeSzs97WfTABLkdDg=="
if base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode() != expected:
    sys.exit("Ponytail download failed integrity verification.")

staged = stage / ".agents/skills"
names = ["ponytail", "ponytail-audit", "ponytail-debt", "ponytail-gain", "ponytail-help", "ponytail-review"]
with tarfile.open(archive) as package:
    for name in names:
        dest = staged / name / "SKILL.md"
        dest.parent.mkdir()
        dest.write_bytes(package.extractfile(f"package/skills/{name}/SKILL.md").read())
    (staged / "ponytail/LICENSE").write_bytes(package.extractfile("package/LICENSE").read())

shared = Path.home() / ".agents/skills"
records = shared.parent / "andrew-stack/skill-hashes.json"
previous = json.loads(records.read_text()) if records.exists() else {}
installed = previous.copy()


def replace_file(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(contents)
    os.replace(tmp.name, path)


# Track only files matching our packages. Refresh those on upgrade while keeping
# user edits, alternate installations, and extra files alongside the skill.
for src in sorted(staged.rglob("*")):
    if not src.is_file():
        continue
    relative = src.relative_to(staged)
    dest = shared / relative
    key = str(relative)
    if any((shared / part).is_symlink() for part in (relative, *relative.parents) if part.parts):
        continue
    if any((shared / part).exists() and not (shared / part).is_dir() for part in relative.parents):
        print(f"Preserving existing non-directory in {dest}", file=sys.stderr)
        continue
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if dest.exists():
        current = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.is_file() else None
        if current == digest:
            installed[key] = digest
            continue
        if current is None or current != previous.get(key):
            print(f"Preserving existing {dest}", file=sys.stderr)
            continue
    replace_file(dest, data)
    installed[key] = digest

if installed != previous:
    replace_file(records, (json.dumps(installed, indent=2, sort_keys=True) + "\n").encode())

claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
if claude.is_dir() or shutil.which("claude"):
    for name in [*names, "graphify"]:
        source = shared / name
        dest = claude / "skills" / name
        if dest.resolve() == source.resolve():
            continue
        if dest.exists() or dest.is_symlink():
            print(f"Preserving existing Claude skill at {dest}", file=sys.stderr)
            continue
        if (source / "SKILL.md").is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(source, target_is_directory=True)
print(f"Shared coding skills ready in {shared}")
PY
