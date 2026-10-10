# Fly.io Sprites (ChemCompass dev VM)

[Sprites](https://fly.io/sprites/) are persistent Linux environments for agents: full disk, checkpoints, sleep/wake, optional HTTPS on port **8080** (use `sprite proxy` for Vite **5173** and PYQ API **8787**).

This is separate from [`fly.toml`](../fly.toml) **Machines** deploy of the production API.

## One-time setup

1. Install CLI (Windows): `iwr https://sprites.dev/install.ps1 -useb | iex`
2. Add a card on your Fly org (Sprites requires it; [$30 trial credit](https://fly.io/sprites/) on first org).
3. `sprite login`
4. From repo root:

   ```powershell
   .\scripts\create-chemcompass-sprite.ps1
   ```

   Or manually:

   ```bash
   sprite create chemcompass
   sprite use chemcompass
   sprite info
   ```

Cursor MCP (optional): `sprites` → `https://sprites.dev/mcp` in [`.cursor/mcp.json`](../.cursor/mcp.json).

## Daily use

| Goal | Command |
|------|---------|
| Shell | `sprite console` |
| Run one-off | `sprite exec -- npm test` |
| Vite on laptop | `sprite exec --dir /home/sprite/ChemCompass -- npm run dev` then `sprite proxy 5173:5173` |
| PYQ API | `sprite exec --dir /home/sprite/ChemCompass/scripts/pyq-llm -- bash -lc 'export PYTHONPATH=.; uvicorn pyq_llm.main:app --host 0.0.0.0 --port 8787'` then `sprite proxy 8787:8787` |
| Snapshot | `sprite checkpoint create --comment "before upgrade"` |
| Roll back | `sprite checkpoint list` → `sprite restore vN` |

## Corpus

`corpus.sqlite` is not in git. After bootstrap, copy from your machine:

```powershell
sprite file upload data/pyq-corpus/corpus.sqlite /home/sprite/ChemCompass/data/pyq-corpus/corpus.sqlite
```

(Or run your corpus build script on the Sprite.)

## Secrets

Prefer [Connectors](https://docs.fly.io/sprites/concepts/connectors.md) for Gemini/GitHub instead of pasting keys into the Sprite. For local dev you can use `sprite exec --env GEMINI_API_KEY=...` sparingly.

## References

- [Agent-ready guide](https://fly.io/sprites/agent-ready.md)
- [CLI commands](https://docs.fly.io/sprites/cli/commands.md)
- [API](https://sprites.dev/api)
