"""Orchestrate full PDF extraction."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pymupdf as fitz

from pyq_extract.chemistry import normalize_chemistry_text
from pyq_extract.figures import crop_question_figures
from pyq_extract.filter_en import general_instructions_text
from pyq_extract.lines import lines_from_pages, page_text
from pyq_extract.marking import parse_marking_scheme
from pyq_extract.metadata import parse_metadata, paper_id
from pyq_extract.questions import parse_questions
from pyq_extract.rubric import parse_rubric
from pyq_extract.segment import segment_document
from pyq_extract.validate import validate_paper


def extract_paper(
    pdf_path: Path,
    output_dir: Path | None = None,
    assets_dir: Path | None = None,
    write_markdown: bool = True,
) -> dict[str, Any]:
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    sections = segment_document(doc)
    source = parse_metadata(pdf_path)
    pid = paper_id(pdf_path, source)

    if output_dir is None:
        output_dir = pdf_path.parent / "extracted"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if assets_dir is None:
        assets_dir = output_dir / "assets" / pid
    assets_dir = Path(assets_dir)

    if sections.general_instructions_page_index is not None:
        gi_text = doc[sections.general_instructions_page_index].get_text()
    else:
        gi_text = general_instructions_text(lines_from_pages(doc, sections.question_page_indices))
    rubric = parse_rubric(gi_text)

    q_lines = lines_from_pages(doc, sections.question_page_indices)

    parsed_qs = parse_questions(q_lines, doc)

    ms_lines = lines_from_pages(doc, sections.marking_page_indices)
    marking = parse_marking_scheme(ms_lines)

    questions_out: list[dict[str, Any]] = []
    for pq in parsed_qs:
        marks_entry = marking.get(pq.number)
        answer = ""
        or_answer = None
        answer_marks: list[float] = []
        flags = list(pq.flags)

        if marks_entry:
            answer = normalize_chemistry_text(marks_entry.answer)
            or_answer = (
                normalize_chemistry_text(marks_entry.or_answer)
                if marks_entry.or_answer
                else None
            )
            answer_marks = marks_entry.marks_breakdown
            flags.extend(marks_entry.flags)

        text = normalize_chemistry_text(pq.text)
        text_raw = pq.text
        or_text = normalize_chemistry_text(pq.or_text) if pq.or_text else None

        figures = [
            {"path": f.path, "pageIndex": f.page_index, "note": f.note}
            for f in crop_question_figures(doc, pq, assets_dir, pid)
        ]

        rubric_marks = rubric.marks_for(pq.number)
        questions_out.append(
            {
                "number": pq.number,
                "marks": rubric_marks,
                "text": text,
                "textRaw": text_raw,
                "orText": or_text,
                "figures": figures,
                "answer": answer,
                "orAnswer": or_answer,
                "answerMarks": answer_marks,
                "flags": sorted(set(flags)),
            }
        )

    questions_out.sort(key=lambda q: q["number"])

    report = validate_paper(questions_out, rubric)
    validation_dict = {
        "ok": report.ok,
        "fatal": report.fatal,
        "warnings": report.warnings,
        "questionFlags": report.question_flags,
    }
    for q in questions_out:
        extra = report.question_flags.get(q["number"], [])
        q["flags"] = sorted(set(q.get("flags") or []) | set(extra))

    paper: dict[str, Any] = {
        "id": pid,
        "source": {
            "year": source.year,
            "exam": source.exam,
            "region": source.region,
            "set": source.set,
            "pdfPath": str(pdf_path.resolve()),
        },
        "rubric": rubric.to_dict(),
        "questions": questions_out,
        "validation": validation_dict,
    }

    json_path = output_dir / f"{pid}.json"
    json_path.write_text(json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8")

    if write_markdown:
        from pyq_extract.markdown import paper_to_markdown

        md_path = output_dir / f"{pid}.md"
        md_path.write_text(paper_to_markdown(paper), encoding="utf-8")

    doc.close()
    return paper
