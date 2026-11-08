# Andrew's engineering policy (Claude Code and Codex)

## Scope and authority

For non-trivial engineering in a git repo, load `andrew-stack:andrew-mode` (Codex may expose it as `andrew-mode`). Questions and obvious small edits need no playbook ceremony. Andrew's current instructions take precedence. The repo's `AGENTS.md` and `CLAUDE.md` own verification, release, deploy and progress-log procedures. This policy fills gaps.

## Start and concurrent work

Fetch `origin`, then inspect status, branch, worktrees and ahead/behind counts. Fetch failure blocks publishing until synchronization can be verified; it does not block local diagnosis or tests. Report unpushed or diverged shared `main` without resetting, rebasing, stashing or committing someone else's work.

Claude Code and Codex may be working simultaneously. For concurrent or uncertain ownership, create a separate worktree with a unique `codex/<task>` or `claude/<task>` branch from `origin/main`. This is isolation, not a requirement to open a PR. Leave the shared checkout and its local `main` alone. A clean checkout is not proof that no other session owns it. Use separate dev-server ports, test databases and generated output. Coordinate changes to shared release files and contracts when integrating.

Fast-forward local `main` only when the current checkout is clean and exclusively owned. Startup hooks must not switch branches, merge, or advance local branch refs. Unrelated dirty files or a stale shared `main` do not prevent isolated work from `origin/main`. Ask only when ownership or conflicting intent cannot be resolved from evidence.

## Verify and publish

Standing authorization: after a complete bug fix or meaningful change, commit and push to GitHub `main` without asking again. Follow the repo's verify/release/rollback runbook. A normal verified fast-forward push, including its configured automatic deployment, is authorized. No PR unless Andrew or the repo requires one.

1. Stage explicit paths or hunks belonging to this task. Inspect the staged diff; never sweep in another session's work, secrets, or scratch output.
2. Run the repo's required checks and focused behavior checks. Never publish an unverified integration.
3. On exclusively owned `main`, use `git pull --ff-only` before committing. If it fails, leave that checkout untouched; use an isolated integration worktree or ask if the history's ownership is unclear.
4. From an isolated task branch, fetch `origin` and integrate current `origin/main` into that branch. Rebase only your own unpublished commits; otherwise merge. Resolve routine conflicts when both changes' intent is clear. Ask about conflicting product decisions, not mechanical Git work. Rerun affected checks after integration, including the repo's release gate.
5. Push `git push origin HEAD:main`, never force. If another session wins the race, fetch, integrate and verify again. A non-fast-forward rejection is normal concurrency, not permission to overwrite remote history.
6. Follow the repo's deploy observation and progress-log rules. Report commit, checks, deployed result if applicable, and any remaining limitations.

## Guard and authorization

Help, logs, status, diffs and other read-only inspection proceed without approval. Apply guards to each actual command; a help command does not authorize a mutation beside it.

Never force-push or delete protected `main`/`master`. Direct production deployment commands, live accounting/delivery API writes, destructive database work and customer/staff messages need explicit authorization for that action or an applicable repo runbook. A goal to fix code alone does not authorize live data changes or messages. Do not ask again for authorization already present, but do not bypass a hook that still denies execution.

When a hook rejects a command, stop that command. Explain which hook rejected it and why. Do not rephrase, split, wrap, or switch tools to execute the rejected action. Continue independent permitted work. For a false positive, retain the input, diagnose with synthetic hook tests, and fix/update the guard only when policy maintenance is authorized. Retry only after the correction is installed and verified, or the harness provides its approval path. Do not disable the guard to unblock a task.

The shell guard cannot read conversation authorization or prove a production target from every CLI command. It conservatively gates direct deploy commands even when the prose runbook authorizes them. If the harness cannot approve one, give Andrew the exact command to run; do not invent an override. Code and API tools that perform the same effects obey the same authorization boundary. A hook pass is not permission.
