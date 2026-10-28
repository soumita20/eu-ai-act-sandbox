# Local Docker Compose profile

The Local profile runs the authenticated FastAPI service, PostgreSQL with pgvector, and the separate reviewer screen. PostgreSQL migrations and publication of the verified regulatory index run as one-shot services before the API becomes ready. API and reviewer ports bind to loopback only. Demo remains a separate profile: run `uv run streamlit run ui/app.py` from the host for the in-process, synthetic, review-free Demo.

The application image uses Python `3.14.10` on Debian Bookworm and a pinned `uv` release. It installs dependencies from `uv.lock`, runs as an unprivileged user, and does not contain local model weights, regulatory index artifacts, secrets, or the PostgreSQL data volume. The host model directory and the publisher's index file are mounted read-only. Docker Compose waits for the database health check and successful migration and index publication jobs before it starts the API. These ordering conditions use Compose's health and successful-completion dependencies. [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)

## Prerequisites

- Docker Desktop using Linux containers, or Docker Engine with Docker Compose.
- The pinned local model at `models/all-MiniLM-L6-v2`.
- The verified file index at `data/index/phase1-regulatory-index-v3.json`.
- At least 8 GB of memory available to Docker for the API and embedding runtime. Adjust the Compose resource limits if needed.

If the model or index is missing, prepare them using the commands in [the regulatory corpus guide](regulatory-corpus.md). The index publisher and API validate the artifact and model identity; they do not download model files or legal sources at container startup.

## Create local secrets

Copy the template to the ignored `.env.docker` file, then generate distinct keys and a database password. URL-safe random strings avoid escaping issues in the Compose-built PostgreSQL URL. This keeps the container settings separate from any existing host `.env` file.

```powershell
Copy-Item .env.docker.example .env.docker
$apiKey = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$reviewerKey = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$postgresPassword = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$content = Get-Content .env.docker -Raw
$content = $content -replace '(?m)^API_KEY=.*$', "API_KEY=$apiKey"
$content = $content -replace '(?m)^REVIEWER_API_KEY=.*$', "REVIEWER_API_KEY=$reviewerKey"
$content = $content -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$postgresPassword"
Set-Content -Path .env.docker -Value $content -NoNewline -Encoding ascii
```

Keep `.env.docker` private and out of source control. The API and reviewer keys must remain distinct.

## Start the Local profile

```powershell
docker compose --env-file .env.docker up --build -d
docker compose --env-file .env.docker ps
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

The API is at `http://127.0.0.1:8000`. The reviewer screen is at `http://127.0.0.1:8502`; it prompts for the reviewer key and sends it to the API over loopback. The reviewer container shares the API container's network namespace so the reviewer app can use the loopback-only API origin. Compose supports a service container as another service's network namespace. [Compose service networking](https://docs.docker.com/reference/compose-file/services/#network_mode)

The `/health/live` endpoint checks process liveness. `/health/ready` checks PostgreSQL retrieval publication, the configured local model path, and assessment/review tables. API and reviewer ports are not published on external interfaces. PostgreSQL is exposed only on `127.0.0.1:${POSTGRES_PORT}` for local tools.

To stop the stack while retaining the local PostgreSQL data:

```powershell
docker compose --env-file .env.docker down
```

The named `postgres_data` volume contains local assessment and review data. Back it up as appropriate. `docker compose down -v` deletes that database volume and should be used only when intentionally resetting it.

## Use the RTX GPU

CPU is the default for portability. Docker Desktop on Windows can pass NVIDIA GPUs to Linux containers when its WSL 2 backend and NVIDIA GPU paravirtualization prerequisites are configured. [Docker Desktop GPU support on Windows](https://docs.docker.com/desktop/features/gpu/)

When GPU support is available, start the stack with the overlay:

```powershell
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

The overlay reserves one GPU for the API and selects `cuda:0`. Verify that CUDA is available before using the API:

```powershell
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.gpu.yml exec api python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'unavailable')"
```

When the GPU overlay is active, API readiness remains false if the requested CUDA device is unavailable. The host-run Demo can still use its existing automatic CUDA selection independently.

## Operational boundaries

- This profile executes the registered synthetic first-party adapters only. It does not mount the Docker socket or run arbitrary repositories.
- The API is authenticated. Reviewer authorization uses a separate configured identity and key.
- Local database data persists in a Docker named volume. The public Demo remains separate and does not use PostgreSQL or reviewer endpoints.
- The reviewer UI shares the API network namespace so its HTTP reviewer request uses loopback. This is intended for local development only; do not expose the Compose ports outside the host.
- Compose configuration can be validated without a running daemon, but starting containers requires a working Docker Engine.
