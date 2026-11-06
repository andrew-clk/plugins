# Global instructions (Codex)

## Engineering style

For any non-trivial engineering work in a git repo, load the `andrew-mode` skill from the andrew-stack plugin before you start, and follow it. It layers on pstack and tells you how to read pstack's Cursor-named skills from Codex. A question, a one-line edit, or work outside a repo does not need it.

The repo's own `AGENTS.md` wins over this file and over andrew-mode for its verify gate, deploy runbook, and `progress.md` rules.

## Git and GitHub workflow (all projects)

**Start of session.** In a git repo, run `git fetch` first. If local `main` has diverged from `origin/main`, has unpushed commits, or the fetch failed, tell Andrew and resolve it before starting work. Fast-forward `main` when GitHub is simply ahead.

**After finishing a bug fix or a bigger change, push it to GitHub `main` without waiting to be asked.** This is standing authorization to commit and push straight to `main`. No feature branch or PR is needed. Before pushing:

1. Verify the work with whatever the project has (build, lint, tests, `npm run verify`). Pushing to `main` may trigger a production deploy, so never push something that doesn't build.
2. Run `git pull --ff-only` in case GitHub moved during the session. If it can't fast-forward, stop and ask.
3. Commit only the files that belong to the change, with a clear message. Don't sweep in unrelated local edits or secrets (`.env`, keys).
4. If the work is on another branch or worktree, bring it up to date with `origin/main` and push it as a fast-forward (`git push origin HEAD:main`).

Don't push half-finished or unverified work, and never force-push `main`. Small tweaks can wait and go out with the next meaningful change. After pushing, report the commit hash and what went out.

## Irreversible actions

The andrew-stack guard hook denies force-pushes to `main`, production deploys, writes to live Bukku or Lalamove APIs, and destructive SQL. When it denies a command, stop and hand Andrew the exact command. Do not rephrase, split, or script around it. The same pause applies to anything that does those things through code the hook cannot see, and to sending messages to customers or staff.
