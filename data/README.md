# Test data — 15 invoice PDFs

`pip install reportlab` then `python3 generate.py` writes 15 PDFs + `manifest.csv`.

Deterministic. The mix proves the edge cases, not the looks:

| Count | Files | Expected outcome |
| --- | --- | --- |
| 10 | `inv_01..10.pdf` | posted |
| 2 | `inv_01_resend_*.pdf` | duplicate (byte-identical → SHA-256 match) |
| 1 | `scan_from_vendor.pdf` | duplicate (renamed `inv_02` → composite-key match) |
| 1 | `inv_broken.pdf` | rejected (lines + tax ≠ total) |
| 1 | `inv_skewed.pdf` | review (crooked, faint → low confidence) |

`manifest.csv` lists each file + its expected call, so the demo video can show the
system decided right on every one. PDFs and manifest are regenerated from the script,
so they're gitignored.
