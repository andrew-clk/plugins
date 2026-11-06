### Live money integration

**You own correctness to the cent. A write you never ran against the real API is unproven, and the reply says so.** For accounting (Bukku), delivery (Lalamove), payment, invoice, and payout work. Always deep tier.

1. **Name the money shape.** Amounts are integer cents (sen) with an explicit currency, sign convention, and rounding owner. Give each external ID its own type (pstack **principle-type-system-discipline**: brand the primitives) so an invoice ID cannot be passed where a payment ID belongs. Write down which system owns each figure, such as "Bukku owns finance-recorded payments, singsong owns sales-recorded ones". When the repo has an `INTEGRATION.md` or a contract file, the shape goes there.
2. **Read the API's own spec,** not memory. Note what the API rounds before you receive it. A figure the API rounds is the API's figure, so display it as received and do not re-round it.
3. **Prove the read path first.** Build a reconcile script (pstack **principle-build-the-lever**) that pulls real records by stable ID and compares them field by field with local state. Run it on at least three real records and paste the output. No write path is built until the read path reproduces the source to the cent.
4. **Make writes idempotent.** Each write carries a key that makes a retry a no-op (an idempotency header, or look up by external reference before create). Answer pstack's two questions in the design: what happens if it runs twice, and what happens if it crashed halfway.
5. **Add a dry run.** Every write path gets a mode that prints the exact requests it would send and sends nothing. Ship with the dry run exercised on real data.
6. **Test writes in a sandbox** when the provider has one (Lalamove does). When it has none (Bukku), the only live test is a draft-then-void that Andrew approves in this turn, run with him watching, and the void is checked afterward. Without that approval the write ships unexercised and the reply says "write path not run against the live API".
7. **Reconcile after shipping.** Run the reconcile script against production after the deploy and record the result in `progress.md`.

**Reply:** the money shape and owners, the reconcile output (records checked, mismatches), what is proven and what is not, and the exact test still waiting on Andrew, if any.
