"""
generate_sample_invoices.py
----------------------------
One-off helper to generate realistic-looking sample invoice PDFs into
sample_invoices/, so the repo works out of the box without needing
real invoice data. Not part of the extraction pipeline itself.

Run:
    python scripts/generate_sample_invoices.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT_DIR = Path(__file__).resolve().parent.parent / "sample_invoices"

INVOICES = [
    dict(
        file="invoice_atlas_supplies.pdf",
        vendor="Atlas Office Supplies LLC",
        invoice_no="INV-10234",
        po_no="PO-55219",
        date="03/14/2026",
        due_date="04/13/2026",
        subtotal="$1,150.00",
        tax="$98.50",
        total="$1,248.50",
        items=[("Standing desks x4", "$980.00"), ("Ergonomic chairs x2", "$268.50")],
    ),
    dict(
        file="invoice_northwind_cloud.pdf",
        vendor="Northwind Cloud Services",
        invoice_no="NW-2026-0091",
        po_no="PO-88012",
        date="2026-02-01",
        due_date="2026-03-03",
        subtotal="$500.00",
        tax="$42.00",
        total="$542.00",
        items=[("Cloud hosting - February", "$420.00"), ("Support plan", "$122.00")],
    ),
    dict(
        file="invoice_dubai_print.pdf",
        vendor="Dubai Print & Design Co.",
        invoice_no="DPD-8871",
        po_no="PO-3390",
        date="January 5, 2026",
        due_date="February 4, 2026",
        subtotal="AED 2,970.00",
        tax="AED 150.00",
        total="AED 3,120.00",
        items=[("Business cards - 2000 units", "AED 620.00"),
               ("Roll-up banners x3", "AED 2,500.00")],
    ),
]


def make_invoice_pdf(path: Path, vendor, invoice_no, po_no, date, due_date,
                      subtotal, tax, total, items):
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, vendor)

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 90, f"Invoice #: {invoice_no}")
    c.drawString(50, height - 108, f"PO Number: {po_no}")
    c.drawString(50, height - 126, f"Date: {date}")
    c.drawString(50, height - 144, f"Due Date: {due_date}")

    c.drawString(50, height - 176, "Bill To:")
    c.drawString(50, height - 192, "Yiguang Ma")
    c.drawString(50, height - 208, "Dubai, UAE")

    y = height - 256
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Description")
    c.drawString(400, y, "Amount")
    c.line(50, y - 5, 500, y - 5)

    c.setFont("Helvetica", 11)
    y -= 25
    for desc, amount in items:
        c.drawString(50, y, desc)
        c.drawString(400, y, amount)
        y -= 20

    y -= 15
    c.line(50, y, 500, y)
    y -= 20
    c.setFont("Helvetica", 11)
    c.drawString(350, y, f"Subtotal: {subtotal}")
    y -= 18
    c.drawString(350, y, f"Tax: {tax}")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, f"Total Due: {total}")

    c.showPage()
    c.save()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for inv in INVOICES:
        make_invoice_pdf(
            OUT_DIR / inv["file"], inv["vendor"], inv["invoice_no"], inv["po_no"],
            inv["date"], inv["due_date"], inv["subtotal"], inv["tax"],
            inv["total"], inv["items"],
        )
        print(f"Created {inv['file']}")


if __name__ == "__main__":
    main()
