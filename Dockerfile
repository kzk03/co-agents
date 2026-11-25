FROM ghcr.io/astral-sh/uv:0.9.5-python3.11-bookworm-slim
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    PATH=/opt/venv/bin:$PATH \
    HF_HOME=/work/data/hf_home
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /work
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project && chmod -R a+rX /opt/venv
