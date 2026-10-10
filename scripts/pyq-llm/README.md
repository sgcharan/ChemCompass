# PYQ RAG MCQ API



Retrieves similar CBSE Class 12 Chemistry PYQs from `data/pyq-corpus/corpus.sqlite` and generates four-option MCQs with NCERT-style distractors.



## Setup



```powershell

cd scripts\pyq-llm

py -m pip install -r requirements.txt

copy .env.example .env

```



Build corpus first (from repo root):



```powershell

$env:PYTHONPATH = "scripts\pyq-extract"

py -m pyq_extract.corpus_cli --pdf-dir "C:\...\CBSE\PYQs\Chemistry" --corpus-dir "data\pyq-corpus"

```



## Choose how to run the LLM



### Option 1 — Local model with Ollama (no cloud, no Colab)



Best if you have **8 GB+ RAM** (16 GB+ nicer for 7B models).



1. Install [Ollama](https://ollama.com/download) for Windows.

2. Download a model (one time, stored on disk):



   ```powershell

   ollama pull llama3.2

   ```



   Other options good for instruction + JSON: `qwen2.5:7b`, `mistral`, `gemma2:9b` (needs more RAM).



3. In `scripts/pyq-llm/.env`:



   ```env

   USE_OLLAMA=1

   OLLAMA_MODEL=llama3.2

   PYQ_LLM_PROVIDER=ollama

   ```



4. Keep Ollama running (tray app), then start the API:



   ```powershell

   $env:PYTHONPATH = "scripts\pyq-llm"

   py -m pyq_llm.main

   ```



   Health check should show `"llm_provider": "ollama"`.



Chemistry quality depends on model size; **7B+ instruct models** work better than tiny models.



### Option 2 — LM Studio (local GUI)



1. Install [LM Studio](https://lmstudio.ai/), download a model, start the **Local Server** (OpenAI-compatible, usually port 1234).

2. In `.env`:



   ```env

   PYQ_LLM_PROVIDER=local

   OPENAI_BASE_URL=http://127.0.0.1:1234/v1

   PYQ_LLM_MODEL=name-shown-in-lm-studio

   OPENAI_API_KEY=not-needed

   ```



### Option 3 — Gemini (free cloud API)



[Google AI Studio](https://aistudio.google.com/apikey) → `GEMINI_API_KEY=...`



### Option 4 — OpenAI (paid cloud)



[platform.openai.com/api-keys](https://platform.openai.com/api-keys) → `OPENAI_API_KEY=...`



### Google Colab



Still useful for batch jobs without installing Ollama: [`notebooks/colab/05_mcq_with_gemini_colab.ipynb`](../../notebooks/colab/05_mcq_with_gemini_colab.ipynb)



## Run API



```powershell

$env:PYTHONPATH = "scripts\pyq-llm"

py -m pyq_llm.main

```



`POST http://127.0.0.1:8787/api/mcq/generate`:



```json

{"chapter": "Solutions", "count": 5, "marks": 1}

```



## Comparison



| Method | Internet | Cost | Privacy |

|--------|----------|------|---------|

| Ollama / LM Studio | Offline after download | Free | All local |

| Gemini | Yes | Free tier | Data sent to Google |

| OpenAI | Yes | Paid | Data sent to OpenAI |

| Colab + Gemini | Yes | Free tier | Runs in Google VM |

## Cloud deployment (free tier)

See [docs/DEPLOY.md](../../docs/DEPLOY.md) for Docker, Fly.io, Render, Cloudflare Pages, Gemini env vars, and CORS (`PYQ_CORS_ORIGINS`).


