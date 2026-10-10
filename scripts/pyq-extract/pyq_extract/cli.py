"""CLI for batch PYQ extraction."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from pyq_extract.extract import extract_paper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract English CBSE Chemistry PYQs from PDFs.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="PDF file or directory")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output directory")
    parser.add_argument("--no-markdown", action="store_true", help="Skip Markdown export")
    parser.add_argument("--report", type=Path, help="CSV summary path (default: output/reports/summary.csv)")
    args = parser.parse_args(argv)

    pdfs: list[Path] = []
    if args.input.is_file() and args.input.suffix.lower() == ".pdf":
        pdfs = [args.input]
    elif args.input.is_dir():
        pdfs = sorted(args.input.rglob("*.pdf"))
    else:
        print(f"Input not found or not a PDF: {args.input}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.report or (args.output / "reports" / "summary.csv")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int | bool]] = []
    for pdf in pdfs:
        try:
            paper = extract_paper(
                pdf,
                output_dir=args.output,
                write_markdown=not args.no_markdown,
            )
            v = paper.get("validation") or {}
            rows.append(
                {
                    "id": paper["id"],
                    "pdf": str(pdf),
                    "questions": len(paper.get("questions") or []),
                    "ok": v.get("ok", False),
                    "fatal_count": len(v.get("fatal") or []),
                    "warning_count": len(v.get("warnings") or []),
                }
            )
            status = "OK" if v.get("ok") else "FAIL"
            print(f"[{status}] {paper['id']} ({len(paper.get('questions') or [])} questions)")
        except Exception as exc:
            rows.append(
                {
                    "id": pdf.stem,
                    "pdf": str(pdf),
                    "questions": 0,
                    "ok": False,
                    "fatal_count": 1,
                    "warning_count": 0,
                    "error": str(exc),
                }
            )
            print(f"[ERROR] {pdf.name}: {exc}", file=sys.stderr)

    with report_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "pdf", "questions", "ok", "fatal_count", "warning_count", "error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Report: {report_path}")
    return 0 if all(r.get("ok") for r in rows if "error" not in r) else 2


if __name__ == "__main__":
    raise SystemExit(main())
