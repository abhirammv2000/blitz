# Built and run from the backend/ directory:
#   docker build -t blitz-backend .
#   docker run -p 8001:8001 --env-file .env blitz-backend
#
# Chroma and the leads/usage sqlite db write to /data, which the ECS task
# definition mounts as a persistent EFS volume - without that mount this is
# still correct, just not durable across a container restart, the same as
# running the app locally with a fresh chroma_data/ every time.

FROM python:3.11-slim

# Installed from PyPI rather than the astral-sh Docker image so the exact
# build here depends on nothing but this Dockerfile and PyPI, which the rest
# of the project's dependency installs already trust.
RUN pip install --no-cache-dir uv==0.5.11

WORKDIR /app

# Dependencies first so an app code change doesn't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/data/chroma_data \
    SQLITE_PATH=/data/blitz.db

RUN mkdir -p /data

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
