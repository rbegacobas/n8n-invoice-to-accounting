# Invoice PDF to QuickBooks with confidence scoring and human review queue

An n8n workflow that turns supplier invoice PDFs arriving by email into accounting
entries — built to handle the edge cases that break most invoice templates.

## The problem

Invoices arrive by email as PDFs. Extracting them by hand is slow and error-prone.
Naive automation is worse: it duplicates entries, trusts guessed amounts, and leaves
no trace of what it decided. This flow is built by someone who verified payments by
hand for three years, so it treats money data like money data.

## The chain

1. **Gmail/IMAP trigger** — filtered by label or sender.
2. **Extract attachment** — PDFs only; drop signatures and inline images.
3. **File hash** — SHA-256 of the binary. First anti-duplicate barrier.
4. **LLM extraction to JSON** — supplier, tax id, invoice number, issue/due date,
   currency, subtotal, tax, total, line items. Strict JSON output, no prose.
5. **Arithmetic validation** — line items + tax must equal total. If not, it stops.
6. **Deduplication** — composite key (supplier + number + amount) plus the step-3 hash.
7. **Confidence gate** — any critical field below threshold goes to the human review
   queue instead of posting.
8. **Post to accounting** — QuickBooks or Xero. No sandbox? A Google Sheet with the
   same schema.
9. **Archive PDF** — to Drive, renamed `YYYY-MM-DD_supplier_number.pdf`.
10. **Audit log** — one row per invoice: decision, confidence, timestamp, destination.

## Edge cases handled

| Edge case | Why it matters |
| --- | --- |
| Confidence gate | A system that guesses amounts never reaches production anywhere |
| Dedup by key *and* hash | The same invoice forwarded three times is entered once |
| Idempotency | A retried run does not double-post the accounting entry |
| Audit log | You can reconstruct what the system decided, and when |

## Test data

See [`data/`](data/). 15 invoice PDFs: 2 exact duplicates, 1 duplicate with a
different filename, 1 with a broken line-item sum, 1 skewed scan to force low
confidence.

## Demo

`demo/` — 2-minute screen recording of a run, subtitled. (no voice needed)

## Usage

Import [`workflow.json`](workflow.json) into n8n, set credentials, point the trigger
at your inbox label.
