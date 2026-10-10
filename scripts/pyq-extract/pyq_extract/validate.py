"""Validation and QA flags for extracted papers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pyq_extract.rubric import Rubric

DEVANAGARI = re.compile(r"[\u0900-\u097F]")


@dataclass
class ValidationReport:
    fatal: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    question_flags: dict[int, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.fatal


def validate_paper(
    questions: list[dict],
    rubric: Rubric,
    expected_count: int = 30,
) -> ValidationReport:
    report = ValidationReport()

    if len(questions) != expected_count:
        report.fatal.append(f"expected {expected_count} questions, got {len(questions)}")

    numbers = [q["number"] for q in questions]
    if sorted(numbers) != list(range(1, expected_count + 1)):
        report.warnings.append(f"question numbers not 1..{expected_count}: {sorted(numbers)}")

    for q in questions:
        flags: list[str] = []
        num = q["number"]
        text = q.get("text") or ""
        answer = q.get("answer") or ""

        if not text.strip():
            flags.append("empty_question_text")
        if DEVANAGARI.search(text):
            flags.append("devanagari_in_question")
        if DEVANAGARI.search(answer):
            flags.append("devanagari_in_answer")
        if not answer.strip():
            flags.append("missing_answer")

        rubric_marks = rubric.marks_for(num)
        if rubric_marks is not None:
            q["marks"] = rubric_marks
            scheme_total = sum(q.get("answerMarks") or [])
            if scheme_total and abs(scheme_total - rubric_marks) > 0.51:
                flags.append("marks_mismatch")

        if flags:
            report.question_flags[num] = flags
            for f in flags:
                if f == "empty_question_text":
                    report.fatal.append(f"Q{num}: empty English text")
                elif f == "missing_answer":
                    report.warnings.append(f"Q{num}: missing answer")

    return report
