---
name: andrew-mode
description: >-
  Andrew's engineering style on top of pstack, for Claude Code and Codex. Use
  for any non-trivial engineering work in a git repo (a bug, a feature, a
  refactor, an integration, an automation, "make this runnable"), for
  /andrew-mode, or when asked to work in Andrew's style. Routes to pstack's
  poteto-mode playbooks with Andrew's gates on top: verified push to main
  instead of PRs, repo runbooks first, money and live-data safety,
  progress.md as the trail, and a cross-model review from the other CLI.
---

# Andrew mode

A thin router over pstack's `poteto-mode`. Principles, playbooks, and workflow skills live in pstack. Read them there and do not restate them here. The gates below win on conflict.

## Find pstack

Run `bash <this skill dir>/scripts/pstack-path.sh`. It prints the pstack folder that holds `skills/` and `docs/`. Call it `<pstack>`. If it prints nothing, pstack is not installed. Stop and tell Andrew to run `andrew-stack/scripts/install.sh` from his plugins clone.

pstack skills are mostly slash-only, so read them as files: `<pstack>/skills/<name>/SKILL.md`, playbooks at `<pstack>/skills/poteto-mode/playbooks/<name>.md`, principles at `<pstack>/skills/principle-<name>/SKILL.md`.

pstack is written in Cursor names. Translate them before you act:

- **Claude Code.** Read `<pstack>/docs/harness/claude-code.md` once per session and follow its tables. For subagents inside a playbook step, use `subagent_type: "andrew-stack:andrew-agent"` where pstack says `poteto-agent`.
- **Codex.** `Task` is your subagent tool when the session has one. Without one, do the step yourself and say so. A todolist is the `update_plan` tool. `AskQuestion` is a plain question in your reply. Drop every model slug, because Codex runs on its configured model. The other model family comes from the **cross-review** skill. Skip `/setup-pstack`.
- **Both.** `cursor-team-kit` is not installed. For `deslop`, review your own diff for slop before commit (Claude Code can run `/simplify`). For `control-ui`, drive the app with the repo's Playwright setup or a browser tool. For `control-cli`, run the CLI and read its real output. Bugbot, Cursor automations, cloud agents, and `/loop` do not exist here. Skip a step that needs one with `Skipped: <step>. <reason>.` and go on.

## Order of authority

1. What Andrew says in this conversation.
2. The repo's `AGENTS.md` and `CLAUDE.md`. Their verify gate, deploy runbook, release-notes rule, and `progress.md` rules are the procedure. This skill and pstack fill gaps only.
3. The gates below.
4. pstack `poteto-mode`.

## Start

1. **Read the repo.** `AGENTS.md`, `CLAUDE.md`, and `progress.md` when they exist. `git status` and `git log --oneline -5`. If local `main` and `origin/main` diverged, or the tree holds someone else's uncommitted work, say so before you change anything.
2. **Triage the rigor tier.** Say the tier and why in one line.
   - **Lite.** A question, one or two obvious edits, an app that will not start with a clear cause, an ops chore. No playbook ceremony. Still reproduce, verify, and ship per the gates.
   - **Standard.** Match a pstack playbook and copy its steps into the todolist verbatim. A skipped step stays as `skip: <reason>`.
   - **Deep.** Money, accounting, or delivery integrations, schema or data migrations, cross-repo contracts, and anything that runs unattended. Route to pstack **figure-it-out** or a deep playbook here, and always run **cross-review** before shipping.

   Work that touches money, live customer data, or production state is never lite.
3. **Restate the goal** per poteto-mode's first trigger. Andrew's asks are short ("fix it", "make it runnable"), so name what done looks like in a checkable way before you start.
4. **Read the Principles section** of `poteto-mode` (standard and deep tiers). Cite a principle only with the concrete choice it changed.

## Playbooks

A playbook here replaces or extends the pstack playbook of the same job. Read the pstack one first when it exists, then this one.

| Job | Playbook |
|---|---|
| End of every code playbook. Replaces pstack's Opening a PR, Babysit, and Shipping | `playbooks/ship-to-main.md` |
| Bukku, Lalamove, payments, invoices, anything that moves or records money | `playbooks/live-money-integration.md` |
| Cron jobs, scheduled agent runs, triage bots, sync loops | `playbooks/scheduled-automation.md` |
| Ads reports, decks, docs, analyses where the deliverable is not code | `playbooks/report-or-deck.md` |

Use pstack's PR playbooks only when the repo's `AGENTS.md` asks for PRs or Andrew asks for one.

## Andrew gates

- **Push to main, verified.** After a bug fix or a bigger change, ship it to `main` without being asked, per `playbooks/ship-to-main.md`. Never push something that has not passed the repo's gate. Never force-push `main`. Small tweaks can wait and go out with the next meaningful change.
- **Irreversible means Andrew.** Pause for production deploys outside the repo's runbook, writes to live accounting or delivery APIs, sending messages to customers or staff (WhatsApp included), deleting or bulk-updating production data, and destructive migrations. The andrew-stack guard hook stops the shell forms of these. A script that does the same thing through code (`node scripts/x.mjs`, `railway run ...`) is not caught by the hook and needs the same pause. Reversible work proceeds without asking.
- **Money is integer cents.** Never floats for amounts. Name the owner of each figure (which system computes it, who rounds) and reconcile against the source to the cent before calling it correct.
- **Key by stable IDs.** Resolve records by their system ID (an invoice ID, a Slides `objectId`, an order ID), never by a position, display number, or slide number. Numbers renumber. IDs do not.
- **The trail is `progress.md`.** Follow the repo's own `progress.md` rules for what to record and its size cap. A deep or unattended run can keep a local `show-me-your-work` TSV, then summarize it into `progress.md`. Do not keep two committed trails.
- **Decided means decided.** When `progress.md` or Andrew's notes record a decision, act on it. Do not re-derive it or ask again.
- **Second opinion from the other family.** Run **cross-review** on deep-tier changes and on any contested design. Verify each finding by running it before you act on it.

## Writing the reply

pstack's **Writing the reply** and the **unslop** rules apply. On top of them:

- Lead with the outcome in one or two sentences: what works now, or what is still broken.
- Then the evidence: the command and its real output, the numbers, the commit hash.
- Then anything waiting on Andrew, each item decidable from the reply alone.
- Keep reports short. Tables for comparisons. No preamble.
