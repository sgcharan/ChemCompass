"""Markdown export for human QA."""

from __future__ import annotations


def paper_to_markdown(paper: dict) -> str:
    lines: list[str] = []
    src = paper.get("source") or {}
    lines.append(f"# {paper.get('id', 'paper')}")
    lines.append("")
    lines.append(f"- Year: {src.get('year')}")
    lines.append(f"- Region: {src.get('region')}")
    lines.append(f"- Set: {src.get('set')}")
    lines.append("")

    for q in paper.get("questions") or []:
        marks = q.get("marks", "?")
        lines.append(f"## Q{q['number']} ({marks} mark{'s' if marks != 1 else ''})")
        lines.append("")
        lines.append(q.get("text") or "")
        lines.append("")
        if q.get("orText"):
            lines.append("**OR**")
            lines.append("")
            lines.append(q["orText"])
            lines.append("")
        if q.get("figures"):
            for fig in q["figures"]:
                lines.append(f"![figure]({fig.get('path')})")
            lines.append("")
        lines.append("### Answer")
        lines.append("")
        lines.append(q.get("answer") or "")
        if q.get("orAnswer"):
            lines.append("")
            lines.append("**OR (answer)**")
            lines.append("")
            lines.append(q["orAnswer"])
        if q.get("answerMarks"):
            lines.append("")
            lines.append(f"*Marks breakdown:* {q['answerMarks']}")
        lines.append("")
        if q.get("flags"):
            lines.append(f"*Flags: {', '.join(q['flags'])}*")
            lines.append("")

    if paper.get("validation"):
        v = paper["validation"]
        lines.append("---")
        lines.append("## Validation")
        for item in v.get("fatal") or []:
            lines.append(f"- **FATAL:** {item}")
        for item in v.get("warnings") or []:
            lines.append(f"- WARNING: {item}")

    return "\n".join(lines)
