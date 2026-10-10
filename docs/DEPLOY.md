# Deploy ChemCompass (free-tier friendly)

ChemCompass is a **static React app** plus a **long-running FastAPI** service with a ~7 MB SQLite corpus. For faster generation in the cloud, use **Gemini** (or OpenAI), not Ollama on small containers.

For a persistent **dev VM** (clone, test, proxies), see [Sprites setup](./SPRITES.md) ([fly.io/sprites](https://fly.io/sprites/)).

## Architecture

| Component | Host | Notes |
|-----------|------|--------|
| UI (`dist/`) | Cloudflare Pages or Netlify | Set `VITE_PYQ_API_URL` at build time |
| API | Fly.io or Render (Docker) | This repo’s [`Dockerfile`](../Dockerfile) |
| LLM | Google Gemini API | `GEMINI_API_KEY` on the API service |

## 1. API (Docker)

### Build locally

```bash
docker build -t chemcompass-api .
docker run --rm -p 8787:8787 \
  -e GEMINI_API_KEY=your-key \
  -e PYQ_LLM_PROVIDER=gemini \
  -e PYQ_CORS_ORIGINS=http://localhost:5173 \
  chemcompass-api
```

Smoke test: `curl http://127.0.0.1:8787/health`

### Fly.io

1. [Install `flyctl`](https://fly.io/docs/hub/quickstart/) and `fly auth login`.
2. From repo root: `fly launch` (pick a unique app name; keep [`fly.toml`](../fly.toml) or adjust `app =`).
3. Set secrets:

   ```bash
   fly secrets set GEMINI_API_KEY=your-key PYQ_CORS_ORIGINS=https://your-app.pages.dev
   ```

4. `fly deploy`
5. API URL: `https://<your-app>.fly.dev`

### Render

1. Connect the GitHub repo in Render → **New Blueprint** → use [`render.yaml`](../render.yaml), or create a **Web Service** with Docker and this Dockerfile.
2. Add environment variables from [`scripts/pyq-llm/.env.production.example`](../scripts/pyq-llm/.env.production.example).
3. **Free tier:** service sleeps when idle; long paper streams may hit timeouts. Fly with `min_machines_running = 1` is often better for streaming.

## 2. Frontend (static)

1. Copy [`.env.production.example`](../.env.production.example) → set `VITE_PYQ_API_URL` to your API URL (no trailing slash).
2. Build: `npm run build`
3. Deploy the `dist/` folder:
   - **Cloudflare Pages:** build command `npm run build`, output `dist`, add env `VITE_PYQ_API_URL` in the dashboard.
   - **Netlify:** same; publish directory `dist`.

The dev server proxy in `vite.config.ts` is not used in production; the browser calls the API directly (CORS must include your Pages URL via `PYQ_CORS_ORIGINS`).

## 3. Environment reference

| Variable | Where | Purpose |
|----------|--------|---------|
| `GEMINI_API_KEY` | API secrets | LLM (recommended in cloud) |
| `PYQ_LLM_PROVIDER` | API | `gemini` |
| `PYQ_CORS_ORIGINS` | API | Comma-separated UI origins |
| `PYQ_CORPUS_DB` | API | Default `/app/data/pyq-corpus/corpus.sqlite` in Docker |
| `PORT` | API | `8787` (Fly/Render may inject) |
| `VITE_PYQ_API_URL` | UI build | Public API base URL |

## 4. Limits

- **70-mark papers** with high AI blend issue many LLM calls; watch Gemini free-tier quotas.
- Do not enable `USE_OLLAMA=1` on 512 MB free containers.
- Oracle Cloud Always Free VM is an alternative if you want self-hosted Ollama (not covered by the Docker path above).
