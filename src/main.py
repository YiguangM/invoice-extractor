"""
main.py
-------
CLI entry point for the Invoice/Receipt Data Extractor.

Usage:
    python src/main.py --input sample_invoices --output output/report.xlsx
    python src/main.py -i sample_invoices -o output/report.xlsx -v
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from extractor import process_invoice
from report import write_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured data from invoice/receipt PDFs "
                    "into a single Excel report."
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=Path("sample_invoices"),
        help="Folder containing invoice PDFs (default: sample_invoices)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("output/report.xlsx"),
        help="Path to write the Excel report to (default: output/report.xlsx)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print per-file extraction status as it runs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not args.input.exists():
        print(f"Input folder not found: {args.input}", file=sys.stderr)
        return 1

    pdf_files = sorted(args.input.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {args.input}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for pdf_path in pdf_files:
        record = process_invoice(pdf_path)
        records.append(record)
        if args.verbose:
            ocr_tag = " [OCR]" if record.used_ocr else ""
            print(f"[{record.status.upper():7s}]{ocr_tag} {pdf_path.name} "
                  f"-> vendor={record.vendor!r} total={record.total_amount!r}")

    write_report(records, args.output)

    ok = sum(1 for r in records if r.status == "ok")
    partial = sum(1 for r in records if r.status == "partial")
    failed = sum(1 for r in records if r.status == "failed")
    print(f"\nProcessed {len(records)} file(s): {ok} ok, {partial} partial, "
          f"{failed} failed.")
    print(f"Report written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
