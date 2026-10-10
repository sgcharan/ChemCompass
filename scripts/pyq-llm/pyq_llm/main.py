from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pyq_llm.answer_quality import filter_quality_hits
from pyq_llm.config import CORPUS_DB, LLM_CONFIGURED, active_llm_provider, cors_allow_origins
from pyq_llm.generate_mcq import StemMode, generate_mcq
from pyq_llm.corpus_spread import max_feasible_targets, rebalance_counts_for_corpus
from pyq_llm.mark_spread import cbse_spread_for_total, format_spread, marks_from_counts
from pyq_llm.paper_pyq import generate_pyq_paper
from pyq_llm.retrieve import retrieve

app = FastAPI(title="ChemCompass PYQ MCQ API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    chapter: str | None = None
    count: int = Field(default=5, ge=1, le=20)
    marks: int | None = 1
    query: str | None = None
    difficulty: str = "board"
    stem_mode: str = Field(
        default="strict",
        description="strict: same PYQ stem + new options; creative: new stem + options; mix: alternate",
    )


class PaperGenerateRequest(BaseModel):
    chapters: list[str] | None = None
    target_marks: int = Field(default=70, ge=5, le=70)
    ai_level: int = Field(default=0, ge=0, le=100)


class McqResponse(BaseModel):
    id: str
    chapter: str | None
    text: str
    options: list[str]
    answer: str
    explanation: str | None = None
    sourcePyqIds: list[str] = []
    mode: str = "llm"
    basedOnPyqId: str | None = None
    basedOnLabel: str | None = None
    basedOnStem: str | None = None
    basedOnMarkingAnswer: str | None = None
    stemMode: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "api_version": 2,
        "paper_api": True,
        "corpus_db": str(CORPUS_DB),
        "corpus_exists": CORPUS_DB.is_file(),
        "llm_configured": LLM_CONFIGURED,
        "llm_provider": active_llm_provider(),
    }


@app.get("/api/chapters")
def list_chapters() -> list[str]:
    if not CORPUS_DB.is_file():
        return []
    import sqlite3

    conn = sqlite3.connect(CORPUS_DB)
    cur = conn.execute(
        "SELECT DISTINCT chapter FROM questions WHERE usable = 1 AND chapter IS NOT NULL ORDER BY chapter"
    )
    out = [r[0] for r in cur if r[0]]
    conn.close()
    return out


def _parse_chapters_param(chapters: str | None) -> list[str] | None:
    if not chapters or not chapters.strip():
        return None
    parts = [p.strip() for p in chapters.split(",") if p.strip()]
    return parts if parts else None


@app.get("/api/paper/capacity")
def paper_capacity(chapters: str | None = None) -> dict[str, object]:
    ch = _parse_chapters_param(chapters)
    if not CORPUS_DB.is_file():
        return {"maxMarks": 0, "allowedTargets": [], "corpusNotes": ["Corpus not found."]}
    max_m, allowed = max_feasible_targets(CORPUS_DB, ch)
    notes: list[str] = []
    if max_m < 70:
        notes.append(f"Up to {max_m} marks for selected chapters (corpus limit).")
    if not allowed:
        notes.append("No full paper fill possible — add chapters or rebuild corpus.")
    return {
        "maxMarks": max_m,
        "allowedTargets": allowed,
        "corpusNotes": notes,
    }


@app.get("/api/paper/spread")
def paper_spread(target_marks: int = 70, chapters: str | None = None) -> dict[str, object]:
    ch = _parse_chapters_param(chapters)
    planned = cbse_spread_for_total(target_marks)
    notes: list[str] = []
    c = planned
    if CORPUS_DB.is_file():
        c, notes = rebalance_counts_for_corpus(CORPUS_DB, planned, ch)
        _, allowed = max_feasible_targets(CORPUS_DB, ch)
    else:
        allowed = []
    return {
        "targetMarks": marks_from_counts(c),
        "spread": format_spread(c),
        "plannedSpread": format_spread(planned),
        "corpusNotes": notes,
        "allowedTargets": allowed,
        "counts": {
            "oneMark": c.one,
            "twoMark": c.vsa,
            "threeMark": c.sa,
            "fourMark": c.case,
            "fiveMark": c.la,
        },
    }


@app.post("/api/paper/generate")
async def api_paper_generate(req: PaperGenerateRequest) -> dict[str, object]:
    if not CORPUS_DB.is_file():
        raise HTTPException(status_code=503, detail="Corpus not found.")
    if not LLM_CONFIGURED:
        raise HTTPException(status_code=503, detail="LLM required for Section A MCQs.")
    ch = req.chapters if req.chapters else None
    return await generate_pyq_paper(
        Path(CORPUS_DB),
        target_marks=req.target_marks,
        chapters=ch,
        ai_level=req.ai_level,
    )


@app.post("/api/paper/generate-stream")
async def api_paper_generate_stream(req: PaperGenerateRequest) -> StreamingResponse:
    if not CORPUS_DB.is_file():
        raise HTTPException(status_code=503, detail="Corpus not found.")
    if not LLM_CONFIGURED:
        raise HTTPException(status_code=503, detail="LLM required for Section A MCQs.")
    ch = req.chapters if req.chapters else None
    db = Path(CORPUS_DB)
    progress_q: asyncio.Queue[dict[str, object]] = asyncio.Queue()

    def on_progress(step: int, total: int, message: str) -> None:
        progress_q.put_nowait(
            {"type": "progress", "step": step, "total": total, "message": message}
        )

    async def event_stream():
        async def worker() -> None:
            try:
                paper = await generate_pyq_paper(
                    db,
                    target_marks=req.target_marks,
                    chapters=ch,
                    ai_level=req.ai_level,
                    on_progress=on_progress,
                )
                await progress_q.put({"type": "complete", "paper": paper})
            except Exception as exc:
                await progress_q.put({"type": "error", "detail": str(exc)})

        task = asyncio.create_task(worker())
        while True:
            item = await progress_q.get()
            yield json.dumps(item) + "\n"
            if item.get("type") in ("complete", "error"):
                break
        await task

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/mcq/generate", response_model=list[McqResponse])
async def api_generate(req: GenerateRequest) -> list[McqResponse]:
    if not CORPUS_DB.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Corpus not found at {CORPUS_DB}. Run corpus_cli first.",
        )

    if not LLM_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail=(
                "No LLM configured. Use Ollama (USE_OLLAMA=1), LM Studio, GEMINI_API_KEY, or "
                "OPENAI_API_KEY — see scripts/pyq-llm/README.md"
            ),
        )

    stem_mode: StemMode = (
        req.stem_mode if req.stem_mode in ("strict", "creative", "mix") else "strict"
    )

    results: list[McqResponse] = []
    used_sources: set[str] = set()
    errors: list[str] = []

    for i in range(req.count):
        hits = retrieve(
            Path(CORPUS_DB),
            chapter=req.chapter,
            query=req.query or req.chapter,
            marks=req.marks,
            limit=30,
            exclude_ids=used_sources,
        )
        if not hits:
            hits = retrieve(
                Path(CORPUS_DB),
                chapter=None,
                query=req.query or req.chapter,
                marks=req.marks,
                limit=30,
                exclude_ids=used_sources,
            )
        hits = filter_quality_hits(hits)
        if not hits:
            errors.append(f"no quality PYQ hits for item {i + 1}")
            continue

        focus = [hits[i % len(hits)]] + [h for j, h in enumerate(hits) if j != i % len(hits)][:4]
        try:
            data = await generate_mcq(
                focus,
                chapter=req.chapter,
                difficulty=req.difficulty,
                stem_mode=stem_mode,
                item_index=i,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue

        for sid in data.get("sourcePyqIds") or []:
            used_sources.add(sid)

        ch = data.get("chapter") or req.chapter
        results.append(
            McqResponse(
                id=f"pyq-gen-{i+1}-{abs(hash(data.get('text',''))) % 10_000_000}",
                chapter=ch,
                text=data["text"],
                options=data["options"],
                answer=data["answer"],
                explanation=data.get("explanation"),
                sourcePyqIds=data.get("sourcePyqIds") or [],
                mode=data.get("mode", "llm"),
                basedOnPyqId=data.get("basedOnPyqId"),
                basedOnLabel=data.get("basedOnLabel"),
                basedOnStem=data.get("basedOnStem"),
                basedOnMarkingAnswer=data.get("basedOnMarkingAnswer"),
                stemMode=data.get("stemMode"),
            )
        )

    if not results and errors:
        raise HTTPException(status_code=422, detail="; ".join(errors[:3]))
    return results


def run() -> None:
    import uvicorn

    from pyq_llm.config import API_PORT

    host = os.environ.get("PYQ_BIND_HOST", "127.0.0.1")
    uvicorn.run("pyq_llm.main:app", host=host, port=API_PORT, reload=False)


if __name__ == "__main__":
    run()
