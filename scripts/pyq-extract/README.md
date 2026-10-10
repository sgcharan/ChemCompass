# CBSE Chemistry PYQ PDF extractor

Extracts **English-only** questions and **marking-scheme answers** from CBSE Class 12 Chemistry previous-year PDFs (bilingual Hindi/English layout).

## Setup

```powershell
py -m pip install -r requirements.txt
```

Requires Python 3.11+ and [PyMuPDF](https://pymupdf.readthedocs.io/).

## Usage

Single PDF:

```powershell
$env:PYTHONPATH = "."
python -m pyq_extract.cli -i "path\to\paper.pdf" -o "path\to\output"
```

Batch folder (recursive `*.pdf`):

```powershell
python -m pyq_extract.cli -i "C:\...\CBSE\PYQs\Chemistry" -o ".\out"
```

Outputs per paper:

- `{id}.json` — questions, answers, marks, figures, validation flags
- `{id}.md` — human-readable QA export
- `assets/{id}/` — cropped diagram PNGs when text layer is thin
- `reports/summary.csv` — batch status

## Tests

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/ -q
```

Set `PYQ_SAMPLE_PDF` to override the default 2014 Delhi sample path.

## Unified corpus (for LLM / RAG)

Build SQLite + JSONL from all PDFs:

```powershell
$env:PYTHONPATH = "."
python -m pyq_extract.corpus_cli --pdf-dir "C:\path\to\CBSE\PYQs\Chemistry" --corpus-dir "..\..\data\pyq-corpus"
```

Re-ingest existing JSON only:

```powershell
python -m pyq_extract.corpus_cli --raw-dir "..\..\data\pyq-corpus\raw" --corpus-dir "..\..\data\pyq-corpus"
```
