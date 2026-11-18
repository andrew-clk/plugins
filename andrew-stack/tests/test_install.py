#!/usr/bin/env python3
"""Exercise installation without touching real CLI configuration or networks."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

STACK = Path(__file__).resolve().parents[1]
SYNC = STACK / "hooks/git-sync-on-start.sh"
GUARD_COMMAND = 'python3 -I "$HOME/.codex/hooks/andrew_guard.py"'


class Installer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Run the real policy installer while stubbing the network dependency installer.
        fixture = self.root / "stack"
        shutil.copytree(STACK, fixture)
        self.install = fixture / "scripts/install.sh"
        (fixture / "scripts/install-project-tools.sh").write_text('echo "tools" >> "$CALLS.tools"\n')
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
        for name in ("claude", "codex", "gemini", "hermes"):
            path = bindir / name
            path.write_text(cli)
            path.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(bindir) + os.pathsep + os.environ["PATH"], "CALLS": str(self.root / "calls")}

        for key in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "HERMES_HOME"):
            self.env.pop(key, None)

    def run_install(self, *args):
        result = subprocess.run(["bash", str(self.install), *args], env=self.env, capture_output=True, text=True)
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
        self.assertTrue((self.root / "calls.tools").is_file())
        for path in (".gemini/GEMINI.md", ".hermes/SOUL.md", ".agents/skills/andrew-stack/SKILL.md"):
            self.assertIn((STACK / "policy/engineering.md").read_text().strip(), (self.home / path).read_text())
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
        self.assertFalse((self.root / "calls.tools").exists())
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".codex").exists())
        for call in self.calls():
            self.assertIn(call[1:], [["plugin", "marketplace", "list"], ["plugin", "list", "--json"]])

    def test_profile_policy_preserves_agent_identity_and_custom_instructions(self):
        self.env["HERMES_HOME"] = str(self.home / "hermes-profile")
        targets = [self.home / "hermes-profile/SOUL.md", self.home / ".gemini/GEMINI.md"]
        for target in targets:
            target.parent.mkdir()
            target.write_text("Existing agent instructions.\n")
        self.run_install()
        first = [target.read_text() for target in targets]
        self.run_install()
        self.assertEqual(first, [target.read_text() for target in targets])
        for content in first:
            self.assertTrue(content.startswith("Existing agent instructions.\n"))
            self.assertEqual(content.count("<!-- andrew-stack:begin -->"), 1)
        self.assertFalse((self.home / ".hermes").exists())

    def test_custom_claude_and_codex_profiles_include_working_guard(self):
        claude = self.home / "Claude Profile"
        codex = self.home / "Codex's $Profile"
        self.env.update(CLAUDE_CONFIG_DIR=str(claude), CODEX_HOME=str(codex))
        sync = claude / "hooks/git-sync-on-start.sh"
        sync.parent.mkdir(parents=True)
        sync.write_text("# Claude Code SessionStart hook: sync with GitHub before any work starts.\n")
        self.run_install()
        self.run_install()
        self.assertEqual(sync.read_bytes(), SYNC.read_bytes())
        for policy in (claude / "CLAUDE.md", codex / "AGENTS.md"):
            self.assertEqual(policy.read_text().count("<!-- andrew-stack:begin -->"), 1)
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".codex").exists())
        groups = json.loads((codex / "hooks.json").read_text())["hooks"]["PreToolUse"]
        commands = [hook["command"] for group in groups for hook in group["hooks"]]
        self.assertEqual(len(commands), 1)
        result = subprocess.run(
            ["sh", "-c", commands[0]], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}}),
            env=self.env, capture_output=True, text=True, cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_incomplete_managed_block_preserves_original_text_on_rerun(self):
        soul = self.home / ".hermes/SOUL.md"
        soul.parent.mkdir()
        original = "Identity\n<!-- andrew-stack:begin -->\nMy rule\n"
        soul.write_text(original)
        self.run_install()
        first = soul.read_text()
        self.run_install()
        self.assertTrue(first.startswith(original))
        self.assertEqual(soul.read_text(), first)

    def test_active_hermes_profile_receives_policy(self):
        base = self.home / ".hermes"
        profile = base / "profiles/coder"
        profile.mkdir(parents=True)
        (base / "active_profile").write_text("coder\n")
        self.run_install()
        self.assertIn("andrew-stack:begin", (profile / "SOUL.md").read_text())

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
