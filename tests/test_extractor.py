"""
Unit tests for field-parsing logic in extractor.py.
Run with: pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extractor import parse_fields, _normalize_date  # noqa: E402


SAMPLE_TEXT_USD = """Atlas Office Supplies LLC
Invoice #: INV-10234
Date: 03/14/2026

Bill To:
Yiguang Ma

Description               Amount
Standing desks x4         $980.00
Ergonomic chairs x2       $268.50

Total Due: $1,248.50
"""

SAMPLE_TEXT_AED = """Dubai Print & Design Co.
Invoice #: DPD-8871
Date: January 5, 2026

Total Due: AED 3,120.00
"""

SAMPLE_TEXT_FULL = """Atlas Office Supplies LLC
Invoice #: INV-10234
PO Number: PO-55219
Date: 03/14/2026
Due Date: 04/13/2026

Bill To:
Yiguang Ma

Description               Amount
Standing desks x4         $980.00
Ergonomic chairs x2       $268.50

Subtotal: $1,150.00
Tax: $98.50
Total Due: $1,248.50
"""


def test_parses_vendor_and_invoice_number():
    record = parse_fields(SAMPLE_TEXT_USD, "test.pdf", used_ocr=False)
    assert record.vendor == "Atlas Office Supplies LLC"
    assert record.invoice_number == "INV-10234"


def test_parses_and_normalizes_date():
    record = parse_fields(SAMPLE_TEXT_USD, "test.pdf", used_ocr=False)
    assert record.invoice_date == "2026-03-14"


def test_parses_total_amount_with_dollar_sign():
    record = parse_fields(SAMPLE_TEXT_USD, "test.pdf", used_ocr=False)
    assert record.total_amount == "$1,248.50"
    assert record.currency == "USD"
    assert record.status == "ok"


def test_parses_total_amount_with_currency_code():
    record = parse_fields(SAMPLE_TEXT_AED, "test.pdf", used_ocr=False)
    assert record.total_amount == "AED 3,120.00"
    assert record.currency == "AED"
    assert record.status == "ok"


def test_empty_text_marks_failed():
    record = parse_fields("", "blank.pdf", used_ocr=False)
    assert record.status == "failed"


def test_partial_extraction_when_fields_missing():
    text = "Some Vendor Name\nNo other structured data here."
    record = parse_fields(text, "messy.pdf", used_ocr=False)
    assert record.status == "partial"
    assert record.vendor == "Some Vendor Name"
    assert record.total_amount is None


def test_normalize_date_various_formats():
    assert _normalize_date("03/14/2026") == "2026-03-14"
    assert _normalize_date("2026-03-14") == "2026-03-14"
    assert _normalize_date("January 5, 2026") == "2026-01-05"
    assert _normalize_date(None) is None


def test_parses_po_number():
    record = parse_fields(SAMPLE_TEXT_FULL, "test.pdf", used_ocr=False)
    assert record.po_number == "PO-55219"


def test_parses_due_date():
    record = parse_fields(SAMPLE_TEXT_FULL, "test.pdf", used_ocr=False)
    assert record.due_date == "2026-04-13"


def test_parses_subtotal_and_tax():
    record = parse_fields(SAMPLE_TEXT_FULL, "test.pdf", used_ocr=False)
    assert record.subtotal == "$1,150.00"
    assert record.tax_amount == "$98.50"


def test_missing_optional_fields_do_not_affect_status():
    record = parse_fields(SAMPLE_TEXT_USD, "test.pdf", used_ocr=False)
    assert record.status == "ok"
    assert record.po_number is None
    assert record.due_date is None
    assert record.subtotal is None
    assert record.tax_amount is None


def test_po_number_not_falsely_matched_in_ordinary_text():
    text = "Some Vendor Corp\nThank you for your continued support and cooperation."
    record = parse_fields(text, "messy.pdf", used_ocr=False)
    assert record.po_number is None
