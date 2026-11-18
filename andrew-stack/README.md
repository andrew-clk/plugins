# andrew-stack

My engineering style, layered on [pstack](../pstack/), for app development. pstack does the heavy lifting: principles, playbooks, and the review skills. andrew-stack changes what pstack gets wrong for how I work, and adds the guardrails my repos need.

## Install

```bash
git clone https://github.com/andrew-clk/plugins && cd plugins
bash andrew-stack/scripts/install.sh            # add --dry-run to preview
```

Run the script once per device with Git, Bash, Python 3, curl and uv available. The installer uses uv to provision Python 3.13 and the pinned Graphify CLI. In Claude Code, `/plugin install andrew-stack --marketplace andrew-clk/plugins` loads the plugin in that harness. The script also installs the shared tools and global policy.

| Agent | What setup does |
|---|---|
| Claude Code and Codex | Installs or updates pstack and Andrew Stack and writes the managed global policy. Registers the Codex shell guard and updates recognized legacy Claude startup hooks. |
| Gemini CLI and Hermes | Writes the same policy into the detected agent's global instructions. |
| Grok Bot desktop | Exports `~/.agents/skills/andrew-stack/SKILL.md`. Add its contents to each coding bot through that profile's Skills settings. Local tool use requires access to the Mac where the installer ran. |
| OpenClaw, Docker Agent (default/coder), and other agents with shared skill discovery | Makes Andrew Stack, Ponytail and Graphify available under `~/.agents/skills/`. Activation depends on the agent. |

Start a new session after setup. Codex may prompt you to trust updated hooks. Global policy blocks preserve surrounding instructions. Existing application repositories need no setup commits. For an update, use a current checkout of this repository and rerun the installer.

## 0.3.0

Adds Ponytail 5.3.3 for implementation and review and Graphify 0.9.112 for local codebase exploration. Small changes can go straight to source. The marketplace retains pstack and its generated harness while dropping unrelated Cursor catalogue entries.

## What's in it

| Piece | What it does |
|---|---|
| [`andrew-mode`](./skills/andrew-mode/SKILL.md) | Router over pstack's `poteto-mode`. Rigor tiers (lite, standard, deep), repo runbooks first, and the gates below. Claude Code loads it on its own for repo work. You can also type `/andrew-stack:andrew-mode`. |
| [`ship-to-main`](./skills/andrew-mode/playbooks/ship-to-main.md) | Replaces pstack's PR, babysit, and shipping playbooks. Gate, review, integrate current main in the owned worktree, stage only the change, push, watch the deploy, record it in `progress.md`. |
| [`live-money-integration`](./skills/andrew-mode/playbooks/live-money-integration.md) | Bukku, Lalamove, payments. Integer cents, stable IDs, read path proven to the cent before any write, dry runs, sandbox or approved draft-then-void. |
| [`scheduled-automation`](./skills/andrew-mode/playbooks/scheduled-automation.md) | Cron and triage bots. Stable IDs, idempotent state, refusal paths, two-run proof. |
| [`report-or-deck`](./skills/andrew-mode/playbooks/report-or-deck.md) | Ads reports and decks. Sourced, reconciled, short. |
| [`cross-review`](./skills/cross-review/SKILL.md) | A second opinion from the other model family. Claude Code asks Codex, and Codex asks Claude, both read-only. You then verify each finding by running it. |
| [`guard.py`](./hooks/guard.py) | PreToolUse hook. Stops force-push or delete of `main`, production deploys (`vercel --prod`; Railway shutdown/deletion), writes to live Bukku or Lalamove APIs, and destructive SQL. Claude Code asks you to confirm. Codex denies and hands you the command. |

## The gates andrew-mode adds over poteto-mode

- **Push to main, verified.** No PRs unless a repo or I ask for one.
- **Repo rules win.** A repo's `AGENTS.md` deploy runbook, verify gate, and `progress.md` rules are the procedure.
- **Authorization follows the action.** Existing explicit authorization and repo runbooks count. Railway up/redeploy proceed under the repo runbook without guard approval; shutdown/deletion and direct Vercel production commands remain gated. Normal verified pushes and their configured automatic deploys are allowed.
- **Concurrent work is isolated.** Separate worktrees and task branches for Claude and Codex; integrate and reverify before a fast-forward push to main. Startup hooks never mutate another session's checkout.
- **A denial stops the action.** Continue unrelated permitted work. Do not wrap or reroute a rejected action. Authorized policy maintenance can fix a reproduced false positive, then retry after installation and verification.
- **Money is integer cents, keyed by stable IDs.**
- **`progress.md` is the trail.** One trail, not two.
- **Cross-model review on deep work.**

## Limits

- The guard is a speed bump for a cooperative agent, not a sandbox. It parses the common shell forms (pipelines, `bash -lc`, line continuations, heredocs, curl's short and long options, per-refspec force) and allows what it cannot parse. Tests cover read-only deploy help (including the originally reported compound command), mixed help/mutations, Git matching pushes, and command/workdir payload variants. Unknown wrappers, dynamic shell evaluation and code-side effects remain outside its guarantees.
- The guard sees shell commands only. `node scripts/x.mjs` that writes to Bukku is not caught. andrew-mode's gate covers it in prose.
- The current Codex adapter emits `deny` rather than relying on `ask`. For a real guarded mutation, use the harness approval route if available; otherwise the user runs the exact command. A prose authorization is not a technical bypass. The installed global matcher is `Bash`; support for `cmd` payloads does not prove every Codex tool dispatch invokes the hook.
- Under `--dangerously-skip-permissions` or `bypassPermissions`, Claude Code may not show the confirm prompt. I have not tested that mode.

## Develop

```bash
python3 -I -m unittest discover -s andrew-stack/tests -p 'test_*.py'
claude plugin validate andrew-stack
claude --plugin-dir andrew-stack                 # try changes without installing
```

Keep pstack untouched so upstream merges stay clean. Review upstream changes in an isolated task branch; this fork has its own commits, so upstream updates generally require integration and verification rather than a fast-forward. Put changes here instead.

## 0.2.0 (2026-11-09)

Fixed Railway/Vercel help being mistaken for deployment, while retaining checks
for real mutations beside it. Closed the matching-force-push gap and added
Codex command/workdir payload coverage. Unified both harnesses' global policy,
made concurrency use isolated worktrees, and made the recognized Git startup
hook observational. The installer now updates existing Claude plugins.

This release does not disable production guards or grant broad live-data writes.

## 0.2.1 (2026-11-15)

Allow Railway up and redeploy without a guard prompt. Repository verification
and rollback requirements still apply. Retain shutdown/deletion, destructive SQL,
live financial API and protected-branch protections.
