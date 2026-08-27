"""
app.py
------
Streamlit front end for testing the invoice extractor interactively:
upload invoice PDFs or images (or use the bundled sample_invoices/), run
extraction, inspect results in a table, and download the generated Excel
report.

Run with:
    streamlit run src/app.py
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image
import pytesseract

from extractor import InvoiceRecord, parse_fields, process_invoice
from report import write_report

# On Windows, Tesseract's installer doesn't reliably add itself to PATH.
# Point pytesseract at the default install location if it's not already
# resolvable, so OCR works without requiring a PATH edit + shell restart.
_DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if not shutil.which("tesseract") and _DEFAULT_TESSERACT.exists():
    pytesseract.pytesseract.tesseract_cmd = str(_DEFAULT_TESSERACT)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_invoices"

STATUS_EMOJI = {"ok": "🟢", "partial": "🟡", "failed": "🔴"}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}
UPLOAD_TYPES = ["pdf"] + sorted(ext.lstrip(".") for ext in IMAGE_EXTENSIONS)

st.set_page_config(page_title="Invoice Extractor", page_icon="📄", layout="wide")

st.title("📄 Invoice & Receipt Data Extractor")
st.caption("Upload invoice PDFs or photos/scans, run the extractor, and inspect the results.")


def process_file(path: Path) -> InvoiceRecord:
    """Process a PDF via the normal pipeline, or OCR an image file directly."""
    if path.suffix.lower() != ".pdf":
        try:
            text = pytesseract.image_to_string(Image.open(path))
        except Exception as exc:  # noqa: BLE001 - report any failure on the record
            record = InvoiceRecord(file_name=path.name, status="failed")
            record.notes = f"Image OCR error: {exc}"
            return record
        return parse_fields(text, path.name, used_ocr=True)
    return process_invoice(path)


source = st.radio("Invoice source", ["Upload files", "Use sample_invoices/"], horizontal=True)

input_paths: list[Path] = []

if source == "Upload files":
    uploaded = st.file_uploader(
        "Drop invoice PDFs or images here",
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
    )
    if uploaded:
        upload_dir = Path(tempfile.mkdtemp(prefix="invoice_extractor_upload_"))
        for f in uploaded:
            dest = upload_dir / f.name
            dest.write_bytes(f.getvalue())
            input_paths.append(dest)
else:
    if SAMPLE_DIR.exists():
        input_paths = sorted(SAMPLE_DIR.glob("*.pdf"))
        st.info(f"Found {len(input_paths)} sample invoice(s) in `{SAMPLE_DIR}`.")
    else:
        st.warning(f"Sample folder not found: {SAMPLE_DIR}")

run = st.button("Run extraction", type="primary", disabled=not input_paths)

if run:
    records: list[InvoiceRecord] = []
    progress = st.progress(0.0)
    for i, path in enumerate(input_paths):
        with st.spinner(f"Processing {path.name}..."):
            records.append(process_file(path))
        progress.progress((i + 1) / len(input_paths))
    progress.empty()
    st.session_state["records"] = records

records: list[InvoiceRecord] | None = st.session_state.get("records")

if records:
    ok = sum(1 for r in records if r.status == "ok")
    partial = sum(1 for r in records if r.status == "partial")
    failed = sum(1 for r in records if r.status == "failed")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed", len(records))
    c2.metric("OK", ok)
    c3.metric("Partial", partial)
    c4.metric("Failed", failed)

    table_rows = [
        {
            "Status": f"{STATUS_EMOJI.get(r.status, '')} {r.status}",
            "File": r.file_name,
            "Vendor": r.vendor,
            "Invoice #": r.invoice_number,
            "Date": r.invoice_date,
            "Total": r.total_amount,
            "Currency": r.currency,
            "OCR": "Yes" if r.used_ocr else "No",
            "Notes": r.notes,
        }
        for r in records
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    with st.expander("Raw extracted text previews"):
        for r in records:
            st.markdown(f"**{r.file_name}**")
            st.code(r.raw_text_preview or "(no text extracted)")

    with tempfile.TemporaryDirectory() as out_dir:
        out_path = Path(out_dir) / "report.xlsx"
        write_report(records, out_path)
        report_bytes = out_path.read_bytes()

    st.download_button(
        "Download report.xlsx",
        data=report_bytes,
        file_name="report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Choose an invoice source and click **Run extraction** to get started.")
