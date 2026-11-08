### Ship to main

**You own the push. Nothing reaches `main` unverified.** Replaces pstack's Opening a PR, Babysit, and Shipping. In most of Andrew's repos a push to `main` deploys production (Vercel or Railway), so the gate before the push is the real review.

If the repo's `AGENTS.md` has a deploy or release runbook, that runbook is this playbook. Follow it step by step, and use the steps below only for what it does not cover.

1. **Gate.** Run the repo's verify command (`npm run verify` where it exists). Otherwise run each of build, typecheck, lint, and tests that the repo has. For a user-visible change, also exercise the changed flow on the real surface. A red gate stops the ship. Fix what the change broke. Report failures that existed before the change, with output, without fixing them silently.
2. **Review.** Read your own `git diff` end to end for slop, stray debug output, and unrelated edits. Deep tier: run the **cross-review** skill and verify its findings first.
3. **Integrate.** Follow `../../../policy/engineering.md`. Use `git pull --ff-only` only on exclusively owned main. In an isolated task worktree, fetch and integrate current origin/main into your own branch, then rerun the repo gate. Never alter another session's checkout or rebase its commits. A push race requires another integration and verification, not an automatic escalation.
4. **Stage only the change.** `git add <paths>`, never `git add -A` on a dirty tree. Check `git diff --cached --stat`. No `.env`, keys, tokens, local screenshots, or scratch scripts.
5. **Release notes and version.** When the repo keeps a changelog or `releases.ts`, update it in the same commit for user-visible work, per its rules.
6. **Commit.** A Conventional Commits title (`fix(invoices): keep paid_cents in sync after Bukku pull`). A body of one to three lines on why and how it was verified. End it with the harness's attribution line when the session gives one.
7. **Rollback point.** When the repo defines one (for example a `rollback/pre-<version>-<YYYYMMDD-HHMM>` branch at the current `origin/main`), create and push it before the release.
8. **Push.** `git push origin HEAD:main` from `main` or from a worktree branch that is up to date with `origin/main`. Never `--force`. Protected-branch rewrites are forbidden. Normal fast-forward pushes are allowed.
9. **Watch the deploy** when the push deploys. Check the platform status (`vercel ls`, `vercel inspect`, `railway logs`) until it is live or failed. Then recheck the changed behavior in production when that can be done without writing live data. A failed deploy is the next bug fix, not a footnote.
10. **Record.** Add the commit, the deploy ID, and the rollback point to `progress.md` when the repo keeps one, within its size rules.

**Reply:** the commit hash, what went out in plain words, the gate output, the deploy result, and anything not verified, with the reason.
