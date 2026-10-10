# ChemCompass PYQ API (FastAPI + corpus.sqlite). Use Gemini/OpenAI in cloud — not Ollama.
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY scripts/pyq-llm/requirements.txt /app/scripts/pyq-llm/requirements.txt
RUN pip install --no-cache-dir -r /app/scripts/pyq-llm/requirements.txt

COPY scripts/pyq-llm/pyq_llm /app/scripts/pyq-llm/pyq_llm
COPY data/pyq-corpus /app/data/pyq-corpus

ENV PYTHONPATH=/app/scripts/pyq-llm
ENV PYQ_CORPUS_DB=/app/data/pyq-corpus/corpus.sqlite
ENV PORT=8787

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health')" || exit 1

CMD ["sh", "-c", "uvicorn pyq_llm.main:app --host 0.0.0.0 --port ${PORT}"]
