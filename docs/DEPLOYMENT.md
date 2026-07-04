# Deployment

## Local on macOS (the default path)

```bash
brew install ollama          # or download from ollama.com
ollama serve                 # or: brew services start ollama
ollama pull qwen3.5:4b
ollama pull nomic-embed-text # optional: hybrid retrieval; BM25-only without it
uv sync
make dev                     # http://127.0.0.1:8000
```

No `.env` needed for defaults (Ollama on localhost, qwen3.5:4b). To customize, `cp .env.example .env` and edit. Note: a fanless MacBook Air throttles under sustained load; the first replies are the fastest.

## Linux GPU box with vLLM

The app only speaks the OpenAI-compatible protocol, so vLLM is a drop-in:

```bash
pip install vllm
vllm serve Qwen/Qwen3.5-4B --port 8001
```

Then in `.env`:

```
OPENAI_BASE_URL=http://<gpu-box>:8001/v1
MODEL_NAME=Qwen/Qwen3.5-4B
OPENAI_API_KEY=none
```

Run `make eval` after any backend change; it is the regression gate.

## Docker

`Dockerfile` and `docker-compose.yml` ship in the repo (app + Ollama):

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen3.5:4b   # first run only
open http://localhost:8000
```

Model weights persist in the `ollama-models` volume. For NVIDIA GPUs, uncomment the device reservation block in the compose file.

## Simple VPS hosting

For a small always-on instance (the 4B model runs fine on an 8GB CPU VPS, slowly):

1. Provision Ubuntu 24.04 with at least 8GB RAM. Install Docker.
2. Clone the repo, `docker compose up -d`, pull the model as above.
3. Put a reverse proxy with TLS in front, e.g. Caddy:
   ```
   yourdomain.example {
       reverse_proxy localhost:8000
   }
   ```
4. Sessions are in-memory: one app container, no horizontal scaling without implementing a shared `SessionStore`.
5. Set a cron refresh on the box (below) or let the GitHub Actions workflow commit fresh data and redeploy.

If CPU generation is too slow, point `OPENAI_BASE_URL` at any hosted OpenAI-compatible endpoint instead of the local Ollama container; that is a `.env` change only.

## Data refresh scheduling

The app reads only the local `data/models.db`; freshness comes from running the ingestion on a schedule.

### GitHub Actions (recommended)

`.github/workflows/refresh-data.yml` runs daily at 03:00 UTC, executes `python -m ingestion.refresh`, and commits the updated `data/models.db` plus source snapshots back to the repo. Trigger manually from the Actions tab with workflow_dispatch. Deployments that pull from the repo pick up fresh data on their next deploy.

### Local cron (macOS/Linux)

```bash
crontab -e
# daily at 03:00, log to a file
0 3 * * * cd /path/to/which-model && /usr/local/bin/uv run python -m ingestion.refresh >> ~/.local/state/whichmodel-refresh.log 2>&1
```

On macOS, prefer a launchd job if the machine sleeps at night (launchd runs missed jobs on wake):

```bash
cat > ~/Library/LaunchAgents/com.whichmodel.refresh.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.whichmodel.refresh</string>
  <key>WorkingDirectory</key><string>/path/to/which-model</string>
  <key>ProgramArguments</key>
  <array><string>/usr/local/bin/uv</string><string>run</string>
  <string>python</string><string>-m</string><string>ingestion.refresh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>3</integer></dict>
</dict></plist>
EOF
launchctl load ~/Library/LaunchAgents/com.whichmodel.refresh.plist
```

A partial refresh (one source down) logs a warning and keeps the rest; the UI footer always shows the true data age.
