#!/usr/bin/env python3
"""Exercise installation without touching real CLI configuration or networks."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

STACK = Path(__file__).resolve().parents[1]
INSTALL = STACK / "scripts/install.sh"
SYNC = STACK / "hooks/git-sync-on-start.sh"
GUARD_COMMAND = 'python3 -I "$HOME/.codex/hooks/andrew_guard.py"'


class Installer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        bindir = self.root / "bin"
        bindir.mkdir()
        cli = '''#!/usr/bin/env python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps([name, *args]) + '\\n')
if args == ['plugin', 'marketplace', 'list']:
    print('andrew-plugins github')
elif args == ['plugin', 'list', '--json']:
    print(os.environ.get('INSTALLED', '[]'))
'''
        for name in ("claude", "codex"):
            path = bindir / name
            path.write_text(cli)
            path.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(bindir) + os.pathsep + os.environ["PATH"], "CALLS": str(self.root / "calls")}

    def run_install(self, *args):
        result = subprocess.run(["bash", str(INSTALL), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def calls(self):
        return [json.loads(line) for line in (self.root / "calls").read_text().splitlines()]

    def test_fresh_install_creates_hook_directory_and_shared_policy(self):
        self.run_install()
        for app, filename in ((".claude", "CLAUDE.md"), (".codex", "AGENTS.md")):
            text = (self.home / app / filename).read_text()
            self.assertIn((STACK / "policy/engineering.md").read_text().strip(), text)
            self.assertEqual(text.count("<!-- andrew-stack:begin -->"), 1)
        self.assertEqual((self.home / ".codex/hooks/andrew_guard.py").read_bytes(), (STACK / "hooks/guard.py").read_bytes())
        self.assertIn(["claude", "plugin", "install", "andrew-stack@andrew-plugins", "--scope", "user"], self.calls())

    def test_update_is_idempotent_and_preserves_custom_content(self):
        self.env["INSTALLED"] = json.dumps([{"id": f"{name}@andrew-plugins", "scope": "user"} for name in ("pstack", "andrew-stack")])
        claude_dir = self.home / ".claude"
        claude_dir.mkdir()
        policy = claude_dir / "CLAUDE.md"
        policy.write_text("My policy. git pull --ff-only\n\n<!-- andrew-stack:begin -->\nstale\n<!-- andrew-stack:end -->\nTail.\n")
        codex_dir = self.home / ".codex"
        codex_dir.mkdir()
        hooks = codex_dir / "hooks.json"
        hooks.write_text(json.dumps({"custom": 7, "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": GUARD_COMMAND}, {"command": "custom-check"}]}]}}))
        result = self.run_install()
        first = policy.read_text()
        first_hooks = hooks.read_text()
        self.run_install()
        self.assertEqual(first, policy.read_text())
        self.assertEqual(first_hooks, hooks.read_text())
        self.assertTrue(first.startswith("My policy. git pull --ff-only\n"))
        self.assertTrue(first.endswith("\nTail.\n"))
        self.assertIn("legacy Git policy", result.stderr)
        config = json.loads(first_hooks)
        self.assertEqual(config["custom"], 7)
        commands = [h["command"] for g in config["hooks"]["PreToolUse"] for h in g["hooks"]]
        self.assertEqual(commands.count(GUARD_COMMAND), 1)
        self.assertIn("custom-check", commands)
        self.assertIn(["claude", "plugin", "update", "andrew-stack@andrew-plugins", "--scope", "user"], self.calls())

    def test_dry_run_never_mutates_configuration_or_calls_mutating_cli(self):
        self.run_install("--dry-run")
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".codex").exists())
        for call in self.calls():
            self.assertIn(call[1:], [["plugin", "marketplace", "list"], ["plugin", "list", "--json"]])

    def test_only_known_startup_hook_is_replaced(self):
        path = self.home / ".claude/hooks/git-sync-on-start.sh"
        path.parent.mkdir(parents=True)
        path.write_text("#!/bin/sh\necho custom\n")
        self.run_install()
        self.assertEqual(path.read_text(), "#!/bin/sh\necho custom\n")
        path.write_text("#!/bin/sh\n# Claude Code SessionStart hook: sync with GitHub before any work starts.\necho legacy\n")
        self.run_install()
        self.assertEqual(path.read_bytes(), SYNC.read_bytes())


class Startup(unittest.TestCase):
    def test_fetch_leaves_dirty_checkout_and_local_branch_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote, seed, work = (root / name for name in ("remote.git", "seed", "work"))
            def git(*args, cwd=root):
                result = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()
            git("init", "--bare", "--initial-branch=main", remote)
            git("clone", remote, seed)
            git("config", "user.name", "Test", cwd=seed)
            git("config", "user.email", "test@example.invalid", cwd=seed)
            (seed / "file").write_text("one\n")
            git("add", "file", cwd=seed)
            git("commit", "-m", "initial", cwd=seed)
            git("push", "origin", "main", cwd=seed)
            git("clone", remote, work)
            old = git("rev-parse", "HEAD", cwd=work)
            (work / "file").write_text("uncommitted user work\n")
            before_status = git("status", "--porcelain", cwd=work)
            before_index = (work / ".git/index").read_bytes()
            (seed / "file").write_text("remote change\n")
            git("commit", "-am", "remote", cwd=seed)
            git("push", "origin", "main", cwd=seed)
            result = subprocess.run(["bash", str(SYNC)], input=json.dumps({"cwd": str(work)}), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 remote-only", json.loads(result.stdout)["systemMessage"])
            self.assertEqual((work / ".git/index").read_bytes(), before_index)
            self.assertEqual(git("rev-parse", "HEAD", cwd=work), old)
            self.assertEqual(git("rev-parse", "main", cwd=work), old)
            self.assertEqual(git("status", "--porcelain", cwd=work), before_status)
            self.assertEqual((work / "file").read_text(), "uncommitted user work\n")
            self.assertEqual(git("rev-parse", "origin/main", cwd=work), git("rev-parse", "HEAD", cwd=seed))


if __name__ == "__main__":
    unittest.main()
