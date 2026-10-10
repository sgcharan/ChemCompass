import importlib

import pyq_llm.config as cfg


def test_ollama_provider(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "1")
    monkeypatch.setenv("PYQ_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    importlib.reload(cfg)
    assert cfg.active_llm_provider() == "ollama"
