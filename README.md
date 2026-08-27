# Invoice & Receipt Data Extractor

Automatically pull structured data (vendor, invoice number, date, total) out
of a folder of invoice PDFs — digital **or scanned** — and log it into a
clean, color-coded Excel report. Built to demonstrate the kind of
document-automation / RPA workflow used in real finance and ops teams.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://github.com/<your-username>/invoice-extractor/actions/workflows/tests.yml/badge.svg)

## Why this exists

Manually re-typing invoice totals into a spreadsheet is exactly the kind of
repetitive task RPA is meant to eliminate. This project automates that
end-to-end: point it at a folder of PDFs, get back a formatted Excel report,
no manual data entry.

## What it does

- **Reads native PDF text** with `pdfplumber` for digitally generated invoices
- **Falls back to OCR** (`pytesseract` + `pdf2image`) automatically when a PDF
  has little or no embedded text — i.e. scanned documents
- **Parses key fields** with a set of regex heuristics: vendor name, invoice
  number, date (normalized to `YYYY-MM-DD`), total amount, and currency
- **Flags confidence**: each row is marked `ok`, `partial` (some fields
  missing), or `failed`, so nothing gets silently mis-extracted
- **Writes a styled Excel report** with a color-coded status column and a
  summary sheet (totals processed, OCR usage, success rate)

## Example output

Running the tool on the 4 sample invoices in `sample_invoices/` (including
one simulated scanned receipt) produces:

| File | Vendor | Invoice # | Date | Total | OCR Used | Status |
|---|---|---|---|---|---|---|
| invoice_atlas_supplies.pdf | Atlas Office Supplies LLC | INV-10234 | 2026-03-14 | $1,248.50 | No | ok |
| invoice_northwind_cloud.pdf | Northwind Cloud Services | NW-2026-0091 | 2026-02-01 | $542.00 | No | ok |
| invoice_dubai_print.pdf | Dubai Print & Design Co. | DPD-8871 | 2026-01-05 | AED 3,120.00 | No | ok |
| invoice_scanned_receipt.pdf | Dubai Print & Design Co. | DPD-8871 | 2026-01-05 | AED 3,120.00 | **Yes** | ok |

## Quick start

```bash
git clone https://github.com/<your-username>/invoice-extractor.git
cd invoice-extractor

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

This project also needs two system tools for OCR support:

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — `brew install tesseract` (macOS) / `sudo apt install tesseract-ocr` (Linux) / [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler](https://poppler.freedesktop.org/) (for `pdf2image`) — `brew install poppler` (macOS) / `sudo apt install poppler-utils` (Linux) / [Windows binaries](https://github.com/oschwartz10612/poppler-windows)

### Run it

```bash
python src/main.py --input sample_invoices --output output/report.xlsx --verbose
```

Then open `output/report.xlsx`.

To try it on your own invoices, drop PDFs into any folder and point
`--input` at it:

```bash
python src/main.py -i path/to/my_invoices -o output/report.xlsx
```

### Try it in a browser

A small Streamlit UI is included for interactive testing — upload PDFs or
photos/scans (PNG, JPG, TIFF, BMP, WEBP, GIF — OCR'd directly), or use the
bundled samples, run extraction, inspect results in a table, and download
the generated report:

```bash
streamlit run src/app.py
```

### Run the tests

```bash
pytest tests/ -v
```

## How it works

```
PDF file
   │
   ▼
pdfplumber text extraction ──► enough text? ──Yes──► parse fields
   │                                │
   │ No / too little text          │
   ▼                                │
pdf2image → tesseract OCR ──────────┘
   │
   ▼
regex field parsing (vendor, invoice #, date, total, currency)
   │
   ▼
openpyxl → styled Excel report (Invoices + Summary sheets)
```

## Project structure

```
invoice-extractor/
├── src/
│   ├── extractor.py      # text extraction (native + OCR) and field parsing
│   ├── report.py         # Excel report generation
│   ├── main.py           # CLI entry point
│   └── app.py            # Streamlit UI for interactive testing
├── scripts/
│   └── generate_sample_invoices.py   # regenerates the demo PDFs
├── sample_invoices/       # ready-to-run demo invoices (incl. a scanned one)
├── tests/
│   └── test_extractor.py
├── output/                 # generated reports land here (gitignored)
├── requirements.txt
└── .github/workflows/tests.yml   # CI: runs the test suite on every push
```

## Limitations & possible extensions

The field parser uses regex heuristics tuned to common invoice layouts —
it won't be 100% accurate on every invoice format in the wild, which is why
every row is tagged with a confidence status rather than presented as
ground truth. Natural next steps:

- Swap the regex parser for a small NER/LLM-based extractor for messier layouts
- Add a `--watch` mode to process new files dropped into a folder automatically
- Export to Google Sheets or push rows directly into an accounting system (e.g. QuickBooks, Xero) via API
- Add multi-currency total validation against line items

## License

MIT — see [LICENSE](LICENSE).
