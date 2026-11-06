### Scheduled automation

**You own every unattended run. A run must be safe to repeat, and it must say what it did.** For cron jobs, scheduled agent runs, triage bots that read a deck or inbox and act, and sync loops.

1. **State one run's contract.** What it reads, what it may change, and its exit predicate. List the actions it must never take unattended. Those come from the irreversible list in andrew-mode's gates.
2. **Key items by stable ID.** Track items by their system ID (a Slides `objectId`, a message ID, an order ID), never by position or display number. Test this by reordering or renumbering the input and rerunning. Nothing may move to the wrong item.
3. **Make it idempotent.** Keep a state file (such as `seen.json`) recording what was handled and the outcome. Write state only after the side effect succeeds, so a crash means a retry, not a skip. Rerunning on the same input must change nothing (pstack **principle-make-operations-idempotent**).
4. **Add a dry run** that prints the planned actions and changes nothing. Use it for the first live run.
5. **Test the refusal paths.** Feed it inputs it must refuse: ambiguous, already handled, outside its allowed actions. Show it refuses each one and records why.
6. **Leave a trail per run.** Record what it saw, what it did, what it skipped and why. Use the repo's log or `progress.md`. Silence is not success.
7. **Prove it with two consecutive real runs.** The first does the work. The second is a no-op. Paste both outputs.

**Reply:** the run contract, the dry-run and two-run evidence, the refusal cases tested, and where each run's trail lives.
