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

Run `bash <this skill dir>/scripts/pstack-path.sh`. It prints the pstack folder that holds `skills/` and `docs/`. Call it `<pstack>`. If it prints nothing, report that pstack is unavailable and continue with the repo runbook and these gates. Repair installation when that is in scope; do not block ordinary engineering on optional workflow tooling.

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

1. **Read the repo.** `AGENTS.md`, `CLAUDE.md`, and `progress.md` when they exist. Fetch origin, inspect status, history and worktrees. Apply `../../policy/engineering.md` for shared-checkout ownership and isolation. Another session's uncommitted work or diverged local main is a reason to isolate, not stop all work.
2. **Triage the rigor tier.** Say the tier and why in one line.
   - **Lite.** A question, one or two obvious edits, an app that will not start with a clear cause, an ops chore. No playbook ceremony. Still reproduce, verify, and ship per the gates.
   - **Standard.** Match a pstack playbook, then make a short task-specific plan. Keep its applicable verification steps. Skip unavailable Cursor tooling and duplicate ceremony with a brief reason; no verbatim checklist is required.
   - **Deep.** Money, accounting, delivery integrations, schema/data migrations, cross-repo contracts, unattended execution and authorization hooks. Use a focused plan and run **cross-review** before shipping. Use **figure-it-out** for substantial work with no suitable playbook, not as mandatory overhead for a small fix.

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
- **Authorization follows the action.** Apply the Guard and authorization section of `../../policy/engineering.md`. Existing explicit authorization and repo runbooks count; hook denials still stand. Stop the rejected action, continue independent work, and never work around a denial. Read-only help and diagnostics need no confirmation. Normal verified pushes and their configured auto-deploys are authorized.
- **Money is integer cents.** Never floats for amounts. Name the owner of each figure (which system computes it, who rounds) and reconcile against the source to the cent before calling it correct.
- **Key by stable IDs.** Resolve records by their system ID (an invoice ID, a Slides `objectId`, an order ID), never by a position, display number, or slide number. Numbers renumber. IDs do not.
- **The trail is `progress.md`.** Follow the repo's own `progress.md` rules for what to record and its size cap. A deep or unattended run can keep a local `show-me-your-work` TSV, then summarize it into `progress.md`. Do not keep two committed trails.
- **Decided means decided.** When `progress.md` or Andrew's notes record a decision, act on it. Do not re-derive it or ask again.
- **Second opinion from the other family.** Run **cross-review** on deep-tier changes and on any contested design. Verify each finding by running it before you act on it.

## Concurrent agents and workflow scope

Follow `../../policy/engineering.md` for worktree isolation and integration. Do not switch or synchronize another session's checkout. Delegates own only their assigned paths and do not publish unless explicitly assigned. Cross-review is read-only and must not start another review recursively.

Use delegation when it provides an independent investigation or review, not merely because an upstream playbook names a model. Use available models; do not install Cursor tools or change model settings to satisfy a playbook. Andrew's message-authorization rule overrides pstack's generic permission to send team messages.

## Writing the reply

pstack's **Writing the reply** and the **unslop** rules apply. On top of them:

- Lead with the outcome in one or two sentences: what works now, or what is still broken.
- Then the evidence: the command and its real output, the numbers, the commit hash.
- Then anything waiting on Andrew, each item decidable from the reply alone.
- Keep reports short. Tables for comparisons. No preamble.
