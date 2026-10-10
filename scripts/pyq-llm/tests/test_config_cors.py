import os

from pyq_llm.config import cors_allow_origins


def test_cors_defaults_local():
    os.environ.pop("PYQ_CORS_ORIGINS", None)
    origins = cors_allow_origins()
    assert "http://localhost:5173" in origins


def test_cors_extra_origins():
    os.environ["PYQ_CORS_ORIGINS"] = "https://app.pages.dev, https://foo.com"
    try:
        origins = cors_allow_origins()
        assert "https://app.pages.dev" in origins
        assert "https://foo.com" in origins
    finally:
        os.environ.pop("PYQ_CORS_ORIGINS", None)
