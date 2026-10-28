# syntax=docker/dockerfile:1.7
FROM python:3.14.10-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install only the application inputs. Generated model/index artifacts are mounted
# read-only at runtime and remain out of the image build context.
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY configs/ ./configs/
COPY apps/ ./apps/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY ui/ ./ui/
COPY data/test-cases/ ./data/test-cases/
COPY data/replays/ ./data/replays/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable \
      --extra api \
      --extra embeddings \
      --extra postgres \
      --extra ui \
      --extra workflow \
    && groupadd --system --gid 10001 sandbox \
    && useradd --system --uid 10001 --gid 10001 --home-dir /home/sandbox \
         --create-home --shell /usr/sbin/nologin sandbox \
    && install -d --owner=10001 --group=10001 /var/lib/eu-ai-act-sandbox

ENV PATH="/app/.venv/bin:${PATH}" \
    HOME=/home/sandbox \
    HF_HOME=/tmp/huggingface \
    TMPDIR=/tmp

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "eu_ai_act_sandbox.api.bootstrap:create_configured_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
