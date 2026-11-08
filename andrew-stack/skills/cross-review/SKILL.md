---
name: cross-review
description: "Second opinion from the other model family: from Claude Code, ask Codex; from Codex, ask Claude. Same brief, read-only, then you verify each finding by running it. Use for /cross-review, 'second opinion', 'get codex to check this', 'get claude to check this', or andrew-mode's pre-ship review."
---

# Cross-review

pstack's rule is that a second opinion is the same prompt on a different model. In Claude Code the subagent tool only offers Claude models, and in Codex only GPT models, so the other family has to come from the other CLI. This skill runs it.

## Steps

1. **Scope.** What the user names, else the change about to ship: `git diff $(git merge-base origin/main HEAD)` plus the working tree. On `main` with unpushed commits, `git diff origin/main`.
2. **Intent.** One paragraph: what the change is for and who notices it. The reviewer challenges whether the change meets the intent, not the intent itself.
3. **Write the prompt** to a unique file from `mktemp`, so concurrent sessions cannot overwrite each other's review. Include the intent, the scope command to run (not the diff pasted in, the reviewer reads the repo itself), the repo's `AGENTS.md` deploy and verify rules if it has them, and this brief verbatim:

   > Break this change. Find inputs, states, or sequences where it does the wrong thing against the intent, and point at the exact file and line. For each finding give a title, why it breaks the intent, and the command or test that would show it failing. Do not report style, naming, or risks that need a future change to matter. You are read-only, so do not edit files, synchronize branches, commit, push, or invoke another cross-review. "No findings" is a valid result.

4. **Run the other harness.** The reviewer is the family you are not:
   - In Claude Code: `bash <this skill dir>/scripts/cross-review.sh codex <prompt-file> <repo>`
   - In Codex: `bash <this skill dir>/scripts/cross-review.sh claude <prompt-file> <repo>`

   It runs read-only (Codex `--sandbox read-only`, Claude `--permission-mode plan`) and saves the review beside the prompt. A run takes a few minutes. Run it in the background and keep working.
5. **Verify every finding yourself.** Run the command it gives, or write the smallest repro. Keep a finding only when the run shows the failure and the failure breaks the intent. A reviewer's claim is a hypothesis, not a result (pstack **prove-it-works**).
6. **Report** in this shape:
   - **Reviewer.** Which CLI and model reviewed it.
   - **Verified.** Each finding with the command, its output, and the fix you made or propose.
   - **Dropped.** One line each, with the reason (did not reproduce, out of scope, style).

## When the other CLI is missing or fails

Say so in one line, run pstack's **interrogate** with the models this harness has, and carry on. Never block a ship on the reviewer being unavailable. A failed review is not a pass, so write `cross-review: not run (<reason>)` in the reply.
