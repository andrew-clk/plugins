#!/usr/bin/env python3
"""Run with: python3 -I andrew-stack/tests/test_guard.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "guard.py")


def run(command, cwd, extra=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": cwd, "tool_input": {"command": command}}
    payload.update(extra or {})
    env = {k: v for k, v in os.environ.items() if k != "ANDREW_GUARD_HARNESS"}
    out = subprocess.run([sys.executable, "-I", GUARD], input=json.dumps(payload), capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)["hookSpecificOutput"] if out.stdout.strip() else None


def repo_on(branch):
    path = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", branch, path], check=True)
    os.mkdir(os.path.join(path, "app"))
    return path


class Guard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = repo_on("main")
        cls.feature = repo_on("feature/x")

    def assertGuarded(self, command, cwd=None):
        result = run(command, cwd or self.feature)
        self.assertIsNotNone(result, f"should be guarded: {command}")
        self.assertEqual(result["permissionDecision"], "ask")

    def assertAllowed(self, command, cwd=None):
        self.assertIsNone(run(command, cwd or self.feature), f"should be allowed: {command}")

    def test_force_push_to_main_is_guarded(self):
        for cmd in [
            "git push --force origin main",
            "git push -f origin HEAD:main",
            "git push origin +main",
            "git push --force-with-lease origin main",
            "git push -uf origin master",
            "cd app && git push --force",
            "git push --delete origin main",
            "git push origin :main",
            "git push --mirror",
        ]:
            self.assertGuarded(cmd, self.main)

    def test_normal_pushes_are_allowed(self):
        for cmd in [
            "git push origin main",
            "git push origin HEAD:main",
            "git push -u origin rollback/pre-1.2.0-20261107-1200",
            "git push",
            "git pull --ff-only && git push origin HEAD:main",
        ]:
            self.assertAllowed(cmd, self.main)
        self.assertAllowed("git push --force-with-lease")
        self.assertAllowed("git push -f origin feature/x")

    def test_bare_force_push_depends_on_current_branch(self):
        self.assertGuarded("git push -f", self.main)
        self.assertAllowed("git push -f", self.feature)

    def test_production_deploys_are_guarded(self):
        for cmd in [
            "vercel --prod",
            "npx vercel deploy --prod --yes",
            "vercel deploy --target production",
            "vercel promote https://x.vercel.app",
            "vercel rollback",
            "railway up /tmp/mcp --path-as-root",
            "railway redeploy --service web",
        ]:
            self.assertGuarded(cmd)

    def test_non_production_tooling_is_allowed(self):
        for cmd in [
            "vercel",
            "vercel env pull .env.local",
            "vercel logs https://x.vercel.app",
            "railway run --service rmc-web -- node scripts/grant-api-key-scope.mjs a",
            "railway logs --service web",
            "railway status",
        ]:
            self.assertAllowed(cmd)

    def test_writes_to_live_money_apis_are_guarded(self):
        for cmd in [
            "curl -X POST https://api.bukku.my/sales/payments -d @p.json",
            "curl -XDELETE https://api.bukku.my/sales/invoices/9",
            "curl --json '{\"a\":1}' https://api.bukku.my/sales/payments",
            "curl -H 'Authorization: x' -d '{}' https://rest.lalamove.com/v3/orders",
            "http POST api.bukku.my/sales/payments amount=1",
            "wget --post-data='a=1' https://api.bukku.my/x",
        ]:
            self.assertGuarded(cmd)

    def test_reads_and_sandbox_writes_are_allowed(self):
        for cmd in [
            "curl https://api.bukku.my/sales/invoices?page=1",
            "curl -s -H 'Authorization: Bearer x' https://api.bukku.my/sales/payments | jq .",
            "curl -X POST https://rest.sandbox.lalamove.com/v3/quotations -d '{}'",
            "curl https://developers.bukku.my/specs/bukku-sales-api.yaml",
            "curl -X POST https://example.com/bukku.my -d x",
        ]:
            self.assertAllowed(cmd)

    def test_destructive_sql_is_guarded(self):
        for cmd in [
            "psql $DATABASE_URL -c 'DROP TABLE invoices'",
            "psql \"$DATABASE_URL\" -c \"DELETE FROM invoice_payments;\"",
            "echo 'TRUNCATE orders' | psql $DATABASE_URL",
            "psql $DATABASE_URL <<'SQL'\nUPDATE invoices SET paid_cents = 0;\nSQL",
            "railway connect Postgres -c 'drop database railway'",
            "dropdb rmc",
            "npx prisma migrate reset --force",
            "npx drizzle-kit push --force",
        ]:
            self.assertGuarded(cmd)

    def test_safe_sql_and_mentions_are_allowed(self):
        for cmd in [
            "psql $DATABASE_URL -c 'DELETE FROM sessions WHERE expires_at < now()'",
            "psql $DATABASE_URL -c 'UPDATE invoices SET paid_cents = 100 WHERE id = 7'",
            "psql $DATABASE_URL -c 'select count(*) from invoices'",
            "grep -rn 'DROP TABLE' scripts/",
            "git commit -m 'drop the TRUNCATE path from the cleanup job'",
            "npx drizzle-kit push",
            "sqlite3 /tmp/scratch.db 'DROP TABLE t'",
        ]:
            self.assertAllowed(cmd)

    def test_cross_review_bypasses_are_guarded(self):
        for cmd in [
            "echo ready # next\nrailway up",
            "sudo -n railway up",
            "if true; then railway up; fi",
            "git push origin '+refs/heads/*:refs/heads/*'",
            "git -c remote.origin.push=+HEAD:main push origin",
            "vercel --scope my-team promote https://x.vercel.app",
            "curl -d{} https://api.bukku.my/sales/payments",
            "curl -sX POST https://rest.lalamove.com/v3/orders",
            "curl -X GET -X POST https://api.bukku.my/sales/payments",
            "curl -X GET https://example.com --next -X DELETE https://api.bukku.my/sales/invoices/9",
            "curl -X DELETE HTTPS://api.bukku.my/sales/invoices/9",
            "psql db -c 'DROP/**/TABLE invoices;'",
            "psql db -c 'DELETE FROM invoices RETURNING *;'",
            "psql db -c \"UPDATE invoices SET remark = 'WHERE';\"",
            "curl -d '#1' https://api.bukku.my/sales/payments",
            "psql db --set ON_ERROR_STOP=1 -c 'DROP TABLE invoices'",
            "psql db <<'SQL'\n-- wipe it\nDROP TABLE invoices;\nSQL",
        ]:
            self.assertGuarded(cmd, self.main)

    def test_cross_review_false_positives_are_allowed(self):
        for cmd in [
            "psql db -c \"SELECT 'DROP TABLE invoices';\"",
            "echo 'DROP TABLE invoices'; psql db -c 'SELECT 1'",
            "vercel build --prod",
            "git push origin +feature:feature main:main",
            "git push --dry-run --force origin main",
            "curl --get --data page=1 https://api.bukku.my/sales/invoices",
            "railway status # then railway up later",
            "psql db -c \"SELECT 1 -- DROP TABLE x\"",
        ]:
            self.assertAllowed(cmd, self.main)

    def test_round_two_bypasses_are_guarded(self):
        for cmd in [
            "vercel \\\n  --prod",
            "curl -sS \\\n  -X POST \\\n  https://api.bukku.my/sales/invoices -d @invoice.json",
            "pnpm exec vercel --prod",
            "npm exec -- vercel --prod",
            "bash -lc 'railway up --service web'",
            "mysql db -e 'DELETE FROM `invoices`;'",
            "mysql db -e 'UPDATE `invoices` SET paid_cents = 0;'",
            "git switch main && git push --force",
            "psql db -c 'UPDATE invoices SET paid_cents = (SELECT amount FROM payments WHERE id = 7);'",
            "psql db <<'SQL'\nUPDATE invoices SET remark = 'Please confirm WHERE delivery is required';\nSQL",
            "wget --method DELETE https://api.bukku.my/sales/invoices/9",
            "git push origin +:",
        ]:
            self.assertGuarded(cmd, self.feature)

    def test_round_two_false_positives_are_allowed(self):
        for cmd in [
            "http GET api.bukku.my/sales/invoices page==1",
            "psql db <<'SQL'\nSELECT 'DROP TABLE invoices';\nSQL",
            "psql db <<'SQL'\nSELECT 1;\nSQL\nrg 'DROP TABLE' migrations/",
            "git push origin '+refs/tags/*:refs/tags/*'",
            "git push origin '+refs/heads/feature/*:refs/heads/feature/*'",
        ]:
            self.assertAllowed(cmd, self.feature)
        self.assertAllowed("git push --force origin --tags", self.main)

    def test_codex_gets_deny_with_the_command_handed_back(self):
        result = run("vercel --prod", self.feature, {"turn_id": "t1"})
        self.assertEqual(result["permissionDecision"], "deny")
        self.assertIn("vercel --prod", result["permissionDecisionReason"])

    def test_codex_array_command_shape(self):
        result = run(["bash", "-lc", "railway up"], self.feature, {"turn_id": "t1"})
        self.assertEqual(result["permissionDecision"], "deny")

    def test_large_nested_input_finishes_fast(self):
        import time
        nested = "psql db -c 'UPDATE t SET a = " + "(" * 400 + "1" + ")" * 400 + " WHERE id = 1'"
        sprawl = " && ".join(f"curl -s https://api.bukku.my/x/{i} -H 'h: ({i})'" for i in range(300))
        for cmd in (nested, sprawl, "x" * 50000):
            start = time.monotonic()
            run(cmd, self.feature)
            self.assertLess(time.monotonic() - start, 3, cmd[:40])

    def test_garbage_input_fails_open(self):
        out = subprocess.run([sys.executable, "-I", GUARD], input="not json", capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "")
        self.assertAllowed("echo 'unbalanced")


if __name__ == "__main__":
    unittest.main(verbosity=1)
