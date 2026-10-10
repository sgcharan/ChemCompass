"""Build unified PYQ corpus from PDF folder or existing JSON extracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyq_extract.corpus import (
    batch_extract_and_ingest,
    export_jsonl,
    load_papers_from_raw,
    write_quality_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build PYQ corpus SQLite + JSONL + quality report.")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        help="Folder of PDFs (recursive). Extracts to --raw-dir if needed.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="Folder of per-paper JSON from pyq_extract (skip PDF extraction).",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        required=True,
        help="Output corpus root (e.g. data/pyq-corpus)",
    )
    parser.add_argument("--reextract", action="store_true", help="Re-run PDF extraction even if JSON exists")
    args = parser.parse_args(argv)

    if not args.pdf_dir and not args.raw_dir:
        print("Provide --pdf-dir or --raw-dir", file=sys.stderr)
        return 1

    corpus_dir = args.corpus_dir
    raw_dir = args.raw_dir or (corpus_dir / "raw")
    db_path = corpus_dir / "corpus.sqlite"
    report_path = corpus_dir / "reports" / "quality.csv"
    jsonl_path = corpus_dir / "corpus.jsonl"

    if args.pdf_dir:
        rows = batch_extract_and_ingest(
            args.pdf_dir,
            raw_dir,
            db_path,
            skip_existing=not args.reextract,
        )
    else:
        rows = load_papers_from_raw(raw_dir, db_path)

    write_quality_report(rows, report_path)
    n = export_jsonl(db_path, jsonl_path)

    manifest = {
        "papers": len(rows),
        "questions_jsonl": n,
        "db": str(db_path),
        "quality_report": str(report_path),
    }
    (corpus_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    total_q = sum(r.get("questions", 0) for r in rows)
    total_u = sum(r.get("usable", 0) for r in rows)
    print(f"Corpus: {len(rows)} papers, {total_q} questions, {total_u} usable ({n} in JSONL)")
    print(f"DB: {db_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
