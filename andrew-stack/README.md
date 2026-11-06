# andrew-stack

My engineering style, layered on [pstack](../pstack/), for Claude Code and Codex. pstack does the heavy lifting: principles, playbooks, and the review skills. andrew-stack changes what pstack gets wrong for how I work, and adds the guardrails my repos need.

## Install

```bash
git clone https://github.com/andrew-clk/plugins && cd plugins
bash andrew-stack/scripts/install.sh            # add --dry-run to preview
```

The script is safe to rerun. It:

- adds this repo as the `andrew-plugins` marketplace in both CLIs and installs `pstack` and `andrew-stack`;
- adds a short block to `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` that points non-trivial repo work at `andrew-mode`;
- registers the guard as a global Codex hook in `~/.codex/hooks.json`.

Restart both CLIs afterwards. Codex asks you to trust the changed hooks once.

## What's in it

| Piece | What it does |
|---|---|
| [`andrew-mode`](./skills/andrew-mode/SKILL.md) | Router over pstack's `poteto-mode`. Rigor tiers (lite, standard, deep), repo runbooks first, and the gates below. Claude Code loads it on its own for repo work. You can also type `/andrew-stack:andrew-mode`. |
| [`ship-to-main`](./skills/andrew-mode/playbooks/ship-to-main.md) | Replaces pstack's PR, babysit, and shipping playbooks. Gate, review, `pull --ff-only`, stage only the change, push, watch the deploy, record it in `progress.md`. |
| [`live-money-integration`](./skills/andrew-mode/playbooks/live-money-integration.md) | Bukku, Lalamove, payments. Integer cents, stable IDs, read path proven to the cent before any write, dry runs, sandbox or approved draft-then-void. |
| [`scheduled-automation`](./skills/andrew-mode/playbooks/scheduled-automation.md) | Cron and triage bots. Stable IDs, idempotent state, refusal paths, two-run proof. |
| [`report-or-deck`](./skills/andrew-mode/playbooks/report-or-deck.md) | Ads reports and decks. Sourced, reconciled, short. |
| [`cross-review`](./skills/cross-review/SKILL.md) | A second opinion from the other model family. Claude Code asks Codex, and Codex asks Claude, both read-only. You then verify each finding by running it. |
| [`guard.py`](./hooks/guard.py) | PreToolUse hook. Stops force-push or delete of `main`, production deploys (`vercel --prod`, `railway up`), writes to live Bukku or Lalamove APIs, and destructive SQL. Claude Code asks you to confirm. Codex denies and hands you the command. |

## The gates andrew-mode adds over poteto-mode

- **Push to main, verified.** No PRs unless a repo or I ask for one.
- **Repo rules win.** A repo's `AGENTS.md` deploy runbook, verify gate, and `progress.md` rules are the procedure.
- **Irreversible means me.** The guard covers the shell forms. Code paths the hook cannot see get the same pause.
- **Money is integer cents, keyed by stable IDs.**
- **`progress.md` is the trail.** One trail, not two.
- **Cross-model review on deep work.**

## Limits

- The guard is a speed bump for a cooperative agent, not a sandbox. It parses the common shell forms (pipelines, `bash -lc`, line continuations, heredocs, curl's short and long options, per-refspec force) and allows what it cannot parse. Two rounds of Codex cross-review found 28 gaps. All but one are fixed and pinned in `tests/test_guard.py`. The open one is a bare `git push --force` under `push.default=matching`.
- The guard sees shell commands only. `node scripts/x.mjs` that writes to Bukku is not caught. andrew-mode's gate covers it in prose.
- In Codex the guard can only deny, because Codex rejects `ask`. You run the denied command yourself.
- Under `--dangerously-skip-permissions` or `bypassPermissions`, Claude Code may not show the confirm prompt. I have not tested that mode.

## Develop

```bash
python3 -I andrew-stack/tests/test_guard.py      # guard rules
claude plugin validate andrew-stack
claude --plugin-dir andrew-stack                 # try changes without installing
```

Keep pstack untouched so upstream merges stay clean. Sync with `git fetch upstream && git merge --ff-only upstream/main`, where `upstream` is `cursor/plugins`. Put changes here instead.
