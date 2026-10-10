"""Assemble a full practice paper from PYQ corpus + LLM (blend by ai_level)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyq_llm.chem_format import format_chemistry_display, format_question_layout
from pyq_llm.corpus_spread import rebalance_counts_for_corpus
from pyq_llm.generate_mcq import StemMode, generate_mcq
from pyq_llm.generate_subjective import generate_subjective
from pyq_llm.mark_spread import cbse_spread_for_total, format_spread, marks_from_counts
from pyq_llm.paper_blend import PaperSlot, build_slot_list, plan_slot_modes
from pyq_llm.pyq_ref import attribution_dict, pyq_id_to_label, primary_stem
from pyq_llm.retrieve import list_mcq_seed_pool, retrieve, sample_for_slot
from pyq_llm.subjective_quality import is_good_subjective_text

ProgressCallback = Callable[[int, int, str], None]
STEM_MIX: StemMode = "mix"


def _subjective_item_from_hit(hit, kind: str, slot_marks: int) -> dict[str, Any]:
    ref = attribution_dict(hit)
    ch = hit.chapter or "Solutions"
    stem = format_question_layout(primary_stem(hit))
    return {
        "id": hit.id,
        "source": "pyq",
        "chapter": ch,
        "kind": kind,
        "marks": slot_marks,
        "text": format_question_layout(hit.text),
        "answer": format_chemistry_display(hit.answer),
        "pyqReference": {
            "id": ref["basedOnPyqId"],
            "label": ref["basedOnLabel"],
            "stem": stem,
            "markingAnswer": format_chemistry_display(ref.get("basedOnMarkingAnswer") or ""),
            "generationStyle": "strict",
        },
    }


def _subjective_item_from_llm(data: dict[str, Any], kind: str, slot_marks: int) -> dict[str, Any]:
    ref_id = data.get("basedOnPyqId") or (data.get("sourcePyqIds") or [""])[0]
    ch = data.get("chapter") or "Solutions"
    stem = data.get("basedOnStem") or data.get("text", "")
    return {
        "id": f"pyq-llm-subj-{ref_id}-{slot_marks}",
        "source": "pyq",
        "chapter": ch,
        "kind": kind,
        "marks": slot_marks,
        "text": data["text"],
        "answer": data.get("answer", ""),
        "pyqReference": {
            "id": ref_id,
            "label": data.get("basedOnLabel") or pyq_id_to_label(ref_id),
            "stem": stem,
            "markingAnswer": data.get("basedOnMarkingAnswer"),
            "generationStyle": data.get("stemMode") or "creative",
        },
    }


def _mcq_item(data: dict[str, Any]) -> dict[str, Any]:
    ch = data.get("chapter") or "Solutions"
    ref_id = data.get("basedOnPyqId") or (data.get("sourcePyqIds") or [""])[0]
    return {
        "id": data.get("id") or ref_id,
        "source": "pyq",
        "chapter": ch,
        "kind": "mcq",
        "marks": 1,
        "text": data["text"],
        "options": data["options"],
        "answer": data["answer"],
        "pyqReference": {
            "id": ref_id,
            "label": data.get("basedOnLabel") or pyq_id_to_label(ref_id),
            "stem": data.get("basedOnStem") or data["text"],
            "markingAnswer": data.get("basedOnMarkingAnswer"),
            "generationStyle": data.get("stemMode") or "strict",
        },
    }


async def _fill_corpus_subjective(
    db_path: Path,
    slot: PaperSlot,
    used: set[str],
    chapters: list[str] | None,
) -> dict[str, Any] | None:
    hits = sample_for_slot(
        db_path,
        slot_marks=slot.mark_value,
        count=1,
        chapters=chapters,
        exclude_ids=used,
    )
    for h in hits:
        if not is_good_subjective_text(h.text, marks=slot.mark_value):
            continue
        used.add(h.id)
        return _subjective_item_from_hit(h, slot.kind, slot.mark_value)
    return None


async def _llm_mcq(
    db_path: Path,
    slot: PaperSlot,
    used: set[str],
    chapters: list[str] | None,
    seed_pool: list,
    item_index: int,
) -> dict[str, Any] | None:
    pool = seed_pool or list_mcq_seed_pool(db_path, chapters=chapters, exclude_ids=used, limit=40)
    if not pool:
        hits = retrieve(db_path, chapter=None, marks=1, limit=10, exclude_ids=used)
        pool = hits
    for attempt in range(min(len(pool) or 1, 12)):
        if not pool:
            break
        focus = pool[(item_index + attempt) % len(pool)]
        try:
            data = await generate_mcq(
                [focus],
                chapter=focus.chapter,
                stem_mode=STEM_MIX,
                item_index=item_index,
            )
            for sid in data.get("sourcePyqIds") or []:
                used.add(sid)
            return _mcq_item(data)
        except ValueError:
            continue
    return None


async def _llm_subjective(
    db_path: Path,
    slot: PaperSlot,
    used: set[str],
    chapters: list[str] | None,
    item_index: int,
) -> dict[str, Any] | None:
    hits = retrieve(
        db_path,
        chapter=chapters[0] if chapters and len(chapters) == 1 else None,
        query="chemistry",
        marks=slot.mark_value,
        limit=15,
        exclude_ids=used,
    )
    if chapters and len(chapters) > 1:
        hits = [h for h in hits if h.chapter in chapters]
    if not hits:
        hits = sample_for_slot(
            db_path,
            slot_marks=slot.mark_value,
            count=3,
            chapters=chapters,
            exclude_ids=used,
        )
    if not hits:
        hits = list_mcq_seed_pool(db_path, chapters=chapters, exclude_ids=used, limit=5)
    if not hits:
        return None
    focus = hits[item_index % len(hits)]
    try:
        data = await generate_subjective(
            [focus],
            slot_marks=slot.mark_value,
            chapter=focus.chapter,
            stem_mode=STEM_MIX,
            item_index=item_index,
        )
        for sid in data.get("sourcePyqIds") or []:
            used.add(sid)
        return _subjective_item_from_llm(data, slot.kind, slot.mark_value)
    except ValueError:
        return None


async def _fill_slot(
    db_path: Path,
    slot: PaperSlot,
    used: set[str],
    chapters: list[str] | None,
    seed_pool: list,
    item_index: int,
    *,
    allow_corpus: bool,
    allow_llm: bool,
) -> dict[str, Any] | None:
    if allow_corpus and slot.mode == "corpus" and slot.mark_value > 1:
        item = await _fill_corpus_subjective(db_path, slot, used, chapters)
        if item:
            return item
    if allow_llm:
        if slot.mark_value == 1:
            return await _llm_mcq(db_path, slot, used, chapters, seed_pool, item_index)
        return await _llm_subjective(db_path, slot, used, chapters, item_index)
    return None


async def generate_pyq_paper(
    db_path: Path,
    *,
    target_marks: int,
    chapters: list[str] | None,
    ai_level: int = 0,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    planned = cbse_spread_for_total(target_marks)
    counts, plan_notes = rebalance_counts_for_corpus(db_path, planned, chapters)
    spread_label = format_spread(counts)
    target = marks_from_counts(counts)
    used: set[str] = set()
    warnings: list[str] = list(plan_notes)

    slots = plan_slot_modes(build_slot_list(counts), ai_level)
    step_total = len(slots)
    step = 0

    def progress(message: str) -> None:
        nonlocal step
        step += 1
        if on_progress:
            on_progress(step, step_total, message)

    seed_pool = list_mcq_seed_pool(
        db_path,
        chapters=chapters,
        exclude_ids=used,
        limit=max(40, counts.one * 6),
    )

    filled: dict[int, dict[str, Any]] = {}

    for idx, slot in enumerate(slots):
        q = await _fill_slot(
            db_path,
            slot,
            used,
            chapters,
            seed_pool,
            idx,
            allow_corpus=True,
            allow_llm=slot.mode == "llm",
        )
        if not q:
            q = await _fill_slot(
                db_path,
                slot,
                used,
                chapters,
                seed_pool,
                idx,
                allow_corpus=False,
                allow_llm=True,
            )
        if q:
            filled[idx] = q
            progress(f"{slot.section_label}: question {slot.index_in_section + 1}")
        else:
            progress(f"{slot.section_label}: could not fill")
            warnings.append(
                f"Could not fill {slot.section_label} slot {slot.index_in_section + 1}"
            )

    # Assemble sections in slot order
    n = 1
    sections: list[dict[str, Any]] = []
    last_key = None
    current_section: dict[str, Any] | None = None

    for idx, slot in enumerate(slots):
        if idx not in filled:
            continue
        if slot.section_key != last_key:
            if current_section and current_section.get("items"):
                sections.append(current_section)
            current_section = {
                "title": slot.title,
                "instruction": slot.instruction,
                "items": [],
            }
            last_key = slot.section_key
        current_section["items"].append(
            {
                "number": n,
                "marks": slot.mark_value,
                "questions": [filled[idx]],
            }
        )
        n += 1

    if current_section and current_section.get("items"):
        sections.append(current_section)

    max_marks = sum(item["marks"] for sec in sections for item in sec["items"])
    blend_note = (
        f"AI blend: {ai_level}% (0 = corpus first, 100 = all AI-generated from PYQ topics)."
    )

    return {
        "title": "ChemCompass PYQ Practice Paper",
        "subtitle": "CBSE Class XII · Chemistry (043) · Previous Year Papers",
        "time": "3 hours" if target >= 60 else "2 hours" if target >= 30 else "1 hour",
        "maxMarks": max_marks,
        "targetMarks": target,
        "sectionSpread": spread_label,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "seed": 0,
        "sections": sections,
        "warnings": warnings,
        "generalInstructions": [
            f"This paper targets {target} marks ({spread_label}) using your local PYQ corpus.",
            blend_note,
            "Use of log tables and calculators is not allowed.",
            *(
                [f"Note: {max_marks} marks filled — corpus or LLM limits prevented a full {target}-mark paper."]
                if max_marks < target
                else []
            ),
            *[f"⚠ {w}" for w in warnings[:8]],
        ],
    }
