#!/usr/bin/env python3
"""Generate 15 supplier-invoice PDFs + manifest.csv for the invoice flow.

Mix (the point is to prove the edge cases, not to look pretty):
  10 clean distinct      -> posted
   2 exact duplicates    -> duplicate  (byte-identical copy of inv_01; SHA-256 catches it)
   1 renamed duplicate   -> duplicate  (same content as inv_02, different filename; key catches it)
   1 broken line sum     -> rejected   (lines + tax != total)
   1 skewed scan         -> review     (rotated + faint; low confidence)

Deterministic (fixed seed) so the demo repeats. Needs: pip install reportlab
"""
import csv
import random
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

random.seed(7)
W, H = A4
SUPPLIERS = [("Northwind Supplies LLC", "US-82-1194837"),
             ("Acme Office Co", "US-47-8820114"),
             ("Blue Harbor Freight", "US-33-5519002")]


def draw(path, number, supplier, taxid, lines, subtotal, tax, total, skew=False):
    c = canvas.Canvas(path, pagesize=A4)
    if skew:                       # simulate a crooked, faint scan -> low confidence
        c.translate(60, 40)
        c.rotate(4)
        c.setFillGray(0.45)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, H - 70, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(60, H - 95, f"{supplier}   Tax ID: {taxid}")
    c.drawString(60, H - 110, f"Invoice #: {number}")
    c.drawString(60, H - 125, "Issue: 2026-01-15    Due: 2026-02-14    Currency: USD")
    y = H - 165
    c.drawString(60, y, "Description")
    c.drawString(400, y, "Amount")
    for desc, amt in lines:
        y -= 18
        c.drawString(60, y, desc)
        c.drawRightString(470, y, f"{amt:.2f}")
    y -= 28
    c.drawRightString(400, y, "Subtotal:"); c.drawRightString(470, y, f"{subtotal:.2f}")
    y -= 16
    c.drawRightString(400, y, "Tax (10%):"); c.drawRightString(470, y, f"{tax:.2f}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(400, y, "Total:"); c.drawRightString(470, y, f"{total:.2f}")
    c.save()


def make_invoice(path, number, broken=False, skew=False):
    supplier, taxid = random.choice(SUPPLIERS)
    n = random.randint(2, 4)
    lines = [(f"Item {i+1}", round(random.uniform(20, 400), 2)) for i in range(n)]
    subtotal = round(sum(a for _, a in lines), 2)
    tax = round(subtotal * 0.10, 2)
    total = round(subtotal + tax, 2)
    if broken:
        total = round(total + 13.00, 2)      # lines + tax != total on purpose
    draw(path, number, supplier, taxid, lines, subtotal, tax, total, skew=skew)
    return {"invoice_number": number, "total": f"{total:.2f}"}


def main():
    manifest = []

    # 10 clean distinct
    for i in range(1, 11):
        info = make_invoice(f"inv_{i:02d}.pdf", f"INV-2026-{i:04d}")
        manifest.append({"filename": f"inv_{i:02d}.pdf", "expected": "posted", **info,
                         "note": "clean"})

    # 2 exact duplicates of inv_01 — copy bytes so SHA-256 matches exactly
    for tag in ("resend_a", "resend_b"):
        name = f"inv_01_{tag}.pdf"
        shutil.copyfile("inv_01.pdf", name)
        manifest.append({"filename": name, "expected": "duplicate",
                         "invoice_number": "INV-2026-0001", "total": manifest[0]["total"],
                         "note": "exact byte duplicate of inv_01 -> hash match"})

    # 1 re-exported duplicate of inv_02: same invoice, different bytes, so the
    # hash barrier misses it and only the composite key (supplier+number+total)
    # can catch it. Trailing comment after %%EOF keeps the PDF valid.
    shutil.copyfile("inv_02.pdf", "scan_from_vendor.pdf")
    with open("scan_from_vendor.pdf", "ab") as f:
        f.write(b"\n% re-exported by vendor portal\n")
    manifest.append({"filename": "scan_from_vendor.pdf", "expected": "duplicate",
                     "invoice_number": "INV-2026-0002", "total": manifest[1]["total"],
                     "note": "renamed duplicate of inv_02 -> composite-key match"})

    # 1 broken line sum
    info = make_invoice("inv_broken.pdf", "INV-2026-9001", broken=True)
    manifest.append({"filename": "inv_broken.pdf", "expected": "rejected", **info,
                     "note": "lines + tax != total -> arithmetic validation fails"})

    # 1 skewed scan
    info = make_invoice("inv_skewed.pdf", "INV-2026-9002", skew=True)
    manifest.append({"filename": "inv_skewed.pdf", "expected": "review", **info,
                     "note": "crooked faint scan -> low confidence -> review queue"})

    with open("manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "expected", "invoice_number",
                                          "total", "note"])
        w.writeheader()
        w.writerows(manifest)
    demo(manifest)


def demo(manifest):
    import hashlib, os
    assert len(manifest) == 15, len(manifest)
    assert sum(r["expected"] == "posted" for r in manifest) == 10
    assert sum(r["expected"] == "duplicate" for r in manifest) == 3
    assert sum(r["expected"] == "rejected" for r in manifest) == 1
    assert sum(r["expected"] == "review" for r in manifest) == 1
    h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    assert h("inv_01.pdf") == h("inv_01_resend_a.pdf") == h("inv_01_resend_b.pdf")
    assert h("inv_02.pdf") != h("scan_from_vendor.pdf")  # must fall to the composite key
    assert h("inv_01.pdf") != h("inv_02.pdf")
    assert all(os.path.getsize(r["filename"]) > 0 for r in manifest)
    print("ok: 15 PDFs (10 posted, 3 duplicate, 1 rejected, 1 review) + manifest.csv")


if __name__ == "__main__":
    main()
