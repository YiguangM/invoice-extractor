"""
extractor.py
------------
Core logic for pulling text out of invoice PDFs and parsing structured
fields (vendor, invoice number, date, total) out of that text.

Two extraction paths are supported:
  1. Native text extraction via pdfplumber (fast, works for digitally
     generated PDFs).
  2. OCR fallback via pdf2image + pytesseract (for scanned invoices
     where step 1 yields little or no text).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pdfplumber
from pdf2image import convert_from_path
import pytesseract

# Minimum characters of native text before we consider a page "readable"
# without falling back to OCR.
MIN_NATIVE_TEXT_LEN = 30


@dataclass
class InvoiceRecord:
    """Structured result for a single processed invoice file."""

    file_name: str
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    po_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    subtotal: Optional[str] = None
    tax_amount: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    used_ocr: bool = False
    status: str = "ok"  # "ok" | "partial" | "failed"
    notes: str = ""
    raw_text_preview: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(pdf_path: Path) -> tuple[str, bool]:
    """Return (text, used_ocr) for the given PDF file.

    Tries native text extraction first; if that yields too little text
    (typical of scanned/image-only PDFs), falls back to OCR.
    """
    text_chunks: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception:
        text_chunks = []

    native_text = "\n".join(text_chunks).strip()

    if len(native_text) >= MIN_NATIVE_TEXT_LEN:
        return native_text, False

    # Fallback to OCR for scanned/image-based PDFs.
    ocr_text = _ocr_pdf(pdf_path)
    return ocr_text, True


def _ocr_pdf(pdf_path: Path) -> str:
    """Convert PDF pages to images and run tesseract OCR on each page."""
    try:
        images = convert_from_path(str(pdf_path), dpi=300)
    except Exception:
        return ""

    text_chunks = []
    for image in images:
        text_chunks.append(pytesseract.image_to_string(image))
    return "\n".join(text_chunks).strip()


# ---------------------------------------------------------------------------
# Field parsing
# ---------------------------------------------------------------------------

_DATE_SUBPATTERNS = [
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
    r"\d{4}-\d{2}-\d{2}",
    r"[A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s+\d{4}",  # e.g. January 5, 2026
]

_DATE_PATTERNS = [rf"\b({p})\b" for p in _DATE_SUBPATTERNS]

_DUE_DATE_PATTERNS = [
    rf"\b(?:due\s*date|payment\s*due|due\s*by)\s*[:\-]?\s*({p})" for p in _DATE_SUBPATTERNS
]

_INVOICE_NUM_PATTERNS = [
    r"(?:invoice|inv)\s*(?:#|no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-]{3,20})",
    r"(?:receipt)\s*(?:#|no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-]{3,20})",
]

_PO_NUMBER_PATTERNS = [
    r"\b(?:p\.?\s?o\.?|purchase\s*order)\s*(?:#|no\.?|number)?\s*[:\-]\s*([A-Z0-9][A-Z0-9\-]{2,19})",
]

_MONEY = r"((?:[$€£]|AED|USD|EUR|GBP)?\s?\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)"

_TOTAL_PATTERNS = [
    # \b keeps this from matching "total" inside "Subtotal"
    rf"\b(?:grand\s*total|total\s*due|amount\s*due|total)\s*[:\-]?\s*{_MONEY}",
]

_SUBTOTAL_PATTERNS = [
    rf"\bsub[\s\-]?total\s*[:\-]?\s*{_MONEY}",
]

_TAX_PATTERNS = [
    rf"\b(?:sales\s*tax|vat|gst|tax)\s*(?:\(\d{{1,2}}(?:\.\d+)?%\))?\s*[:\-]?\s*{_MONEY}",
]

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "AED": "AED"}


def _search_first(patterns: list[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _guess_vendor(text: str) -> Optional[str]:
    """Heuristic: vendor name is usually one of the first non-empty lines
    that isn't itself a label like 'Invoice' or 'Date'."""
    skip_words = ("invoice", "receipt", "date", "bill to", "ship to", "total")
    for line in text.splitlines():
        clean = line.strip()
        if not clean or len(clean) < 3:
            continue
        if any(clean.lower().startswith(w) for w in skip_words):
            continue
        return clean[:80]
    return None


def _guess_currency(total_raw: Optional[str], text: str) -> Optional[str]:
    if total_raw:
        for symbol, code in _CURRENCY_SYMBOLS.items():
            if symbol in total_raw:
                return code
    for code in ("USD", "EUR", "GBP", "AED"):
        if code in text:
            return code
    return None


def _normalize_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    formats = ["%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y-%m-%d",
               "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%m/%d/%y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # keep raw string if we can't confidently parse it


def parse_fields(text: str, file_name: str, used_ocr: bool) -> InvoiceRecord:
    """Parse structured fields out of raw extracted text."""
    record = InvoiceRecord(file_name=file_name, used_ocr=used_ocr)
    record.raw_text_preview = text[:300]

    if not text.strip():
        record.status = "failed"
        record.notes = "No text could be extracted (empty or unreadable file)."
        return record

    record.vendor = _guess_vendor(text)
    record.invoice_number = _search_first(_INVOICE_NUM_PATTERNS, text)
    record.po_number = _search_first(_PO_NUMBER_PATTERNS, text)
    raw_date = _search_first(_DATE_PATTERNS, text)
    record.invoice_date = _normalize_date(raw_date)
    record.due_date = _normalize_date(_search_first(_DUE_DATE_PATTERNS, text))
    record.subtotal = _search_first(_SUBTOTAL_PATTERNS, text)
    record.tax_amount = _search_first(_TAX_PATTERNS, text)
    record.total_amount = _search_first(_TOTAL_PATTERNS, text)
    record.currency = _guess_currency(record.total_amount, text)

    missing = [
        name for name, val in [
            ("vendor", record.vendor),
            ("invoice_number", record.invoice_number),
            ("invoice_date", record.invoice_date),
            ("total_amount", record.total_amount),
        ] if not val
    ]
    if missing:
        record.status = "partial"
        record.notes = f"Could not confidently extract: {', '.join(missing)}"

    return record


def process_invoice(pdf_path: Path) -> InvoiceRecord:
    """End-to-end: extract text (with OCR fallback) then parse fields."""
    try:
        text, used_ocr = extract_text(pdf_path)
    except Exception as exc:  # noqa: BLE001 - want to capture and report any failure
        record = InvoiceRecord(file_name=pdf_path.name, status="failed")
        record.notes = f"Extraction error: {exc}"
        return record

    return parse_fields(text, pdf_path.name, used_ocr)
