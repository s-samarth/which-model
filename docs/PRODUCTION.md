# Taking Which Model? to Production

The architecture has one deliberate seam: the app talks to any OpenAI-compatible endpoint through two env vars (`OPENAI_BASE_URL`, `MODEL_NAME`, plus `EMBED_MODEL_NAME` for retrieval). Everything below is a different answer to "what sits behind that URL", and switching answers later is a config change plus one eval run.

## The three production shapes

| Shape | Brain runs on | Monthly cost | Ops burden | When |
|---|---|---|---|---|
| A. API-served | A managed endpoint (Fireworks, Azure, Bedrock, OpenRouter) | Pennies to a few dollars at hobby traffic; free with credits | Near zero | Launch now |
| B. Serverless GPU | RunPod Serverless / Modal container running vLLM | Single-digit dollars at low traffic | Low | Bursty traffic, no credits |
| C. Owned GPU box | A rented GPU VM running vLLM or SGLang | ~$220-450 always-on | Real | Steady traffic or strict data control |

Start with A (you have credits), keep C documented for later. Local Ollama remains the dev mode forever.

## Shape A: API-served brain, step by step

### A1. Pick the endpoint and set env

**Fireworks** (simplest, OpenAI-compatible):
```
OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
OPENAI_API_KEY=<fireworks key>
MODEL_NAME=accounts/fireworks/models/<pick a hosted Qwen-class model>
LLM_REASONING_EFFORT=          # empty unless the hosted model supports it
```
Check their model library for the exact id; prefer a 4-9B instruct model to match the evals.

**OpenRouter** (one key, most models):
```
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=<openrouter key>
MODEL_NAME=qwen/qwen3.5-9b
```

**Azure AI Foundry** (your credits): deploy a model from the catalog as a serverless endpoint in the portal (Deployments > Deploy model). The endpoint page shows a URL and key. Serverless endpoints speak the OpenAI chat protocol:
```
OPENAI_BASE_URL=https://<your-endpoint>.services.ai.azure.com/models
OPENAI_API_KEY=<endpoint key>
MODEL_NAME=<deployment name>
```
Note: some Azure endpoint flavors want an `api-version` query or `api-key` header; if the OpenAI SDK call fails, check the endpoint's "consume" tab for the OpenAI-compatible URL form. <!-- Azure surface changes; verify in portal -->

**AWS Bedrock** (your credits): enable a model in the Bedrock console (Model access), then use Bedrock's OpenAI-compatible endpoint for supported models, with an API key created under Bedrock > API keys:
```
OPENAI_BASE_URL=https://bedrock-runtime.<region>.amazonaws.com/openai/v1
OPENAI_API_KEY=<bedrock api key>
MODEL_NAME=<model id from the console>
```
Coverage of the OpenAI-compat layer varies by model; verify in the console docs for your region.

### A2. Embeddings and reasoning flags
Managed endpoints may not host `nomic-embed-text`. Either set `RETRIEVER_BACKEND=bm25` (fine; hybrid is an enhancement) or point embeddings at any host offering an embedding model and set `EMBED_MODEL_NAME` accordingly. Set `LLM_REASONING_EFFORT=` (empty) unless the hosted model documents support for it; the client retries without it on rejection anyway. `LLM_KEEP_ALIVE` is Ollama-only; harmless but pointless elsewhere.

### A3. Validate before exposing
```
uv run pytest && EVAL_MOCK=1 make eval    # fast sanity
make eval                                  # once, against the new endpoint
```
The live gate is the contract that the swapped brain still elicits, grounds, and recommends.

## Hosting the app itself (all shapes need this)

The app is a small FastAPI process; any $5 VPS or container platform works.

### Path 1: VPS + Docker + Caddy (recommended, ~30 minutes)
1. Get a small VPS (Hetzner CX22, DigitalOcean basic, Lightsail; 2GB RAM is plenty).
2. Point your subdomain at it: in your DNS panel add `A` record `which.yourdomain.com -> <server IP>`.
3. On the server: install Docker (`curl -fsSL https://get.docker.com | sh`), clone the repo, write `.env` with the Shape A values.
4. Edit `docker-compose.yml`: for Shape A you do not need the ollama service; run only the app (set the env vars in the compose file or an `env_file`).
5. `docker compose up -d --build`.
6. TLS + reverse proxy with Caddy (automatic HTTPS):
   ```
   sudo apt install caddy
   # /etc/caddy/Caddyfile
   which.yourdomain.com {
       reverse_proxy localhost:8000
   }
   sudo systemctl reload caddy
   ```
7. Done: https://which.yourdomain.com. Updates: `git pull --rebase && docker compose up -d --build`.

### Path 2: Container platforms (no server administration)
Fly.io, Railway, Render, or Azure Container Apps build from the Dockerfile, give you HTTPS and a CNAME target for the subdomain, and restart on crash. Trade-off: in-memory sessions mean one instance only (fine at this scale); the SQLite catalog ships inside the image, so redeploy on data refresh or mount a volume.

### Data freshness in production
Keep the GitHub Actions refresh committing to the repo, and either redeploy daily (container platforms can auto-deploy on push) or run `make refresh-data` in a cron on the VPS. `git pull --rebase` is the sync rule; the workflow commits to main daily.

## Shape C for later: your own GPU endpoint (AWS example, from zero)

1. **Quota**: AWS console > Service Quotas > EC2 > "Running On-Demand G and VT instances" > request 4+ vCPUs (new accounts start at 0; approval takes hours to days).
2. **Launch**: EC2 > Launch instance > AMI: "Deep Learning OSS Nvidia Driver AMI (Ubuntu)" > type `g6.xlarge` (24GB L4, ~$0.80/hr) or `g5.xlarge` (24GB A10G) > 100GB disk > security group allowing port 8001 only from your app server's IP.
3. **Serve**:
   ```
   pip install vllm
   vllm serve Qwen/Qwen3.5-9B --port 8001 --api-key <make one up>
   ```
   (SGLang equivalent: `python -m sglang.launch_server --model-path Qwen/Qwen3.5-9B`.)
4. **Point the app at it**: `OPENAI_BASE_URL=http://<gpu-ip>:8001/v1`, run the eval gate.
5. **Keep it alive**: wrap in systemd (`Restart=always`), CloudWatch alarm on instance health, and remember it bills 24/7; stop it when idle or use marketplace clouds (RunPod/Vast) at a third of the hourly price.

## Monitoring and logging (any shape)
- Uptime: UptimeRobot/BetterStack free tier pinging `/health` every minute with email/Telegram alerts.
- Logs: `docker compose logs` locally; ship JSON logs to Axiom or Grafana Loki free tier when traffic is real. Log per turn: latency, phase, notices, grounding flags.
- Metrics (Shape C): vLLM/SGLang expose Prometheus `/metrics` (TTFT, throughput, queue depth) > Grafana Cloud free tier.
- Guardrails are a prerequisite for any public URL: see GUARDRAILS.md.
