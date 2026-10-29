# Stage 1: build the React app into static files
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API that also serves the built frontend
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

# Hugging Face Spaces run as user 1000; Lambda runs as its own user, so /app must stay readable by everyone.
RUN useradd -m -u 1000 user && mkdir /app && chown user /app
USER user
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

# Precompile Python files: on Lambda's read-only disk, Python could not cache them and would recompile on every start.
ENV UV_COMPILE_BYTECODE=1
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=user backend backend
RUN python -m compileall -q backend
COPY --chown=user data data
COPY --chown=user --from=frontend /frontend/dist frontend/dist

# On AWS Lambda, this extension turns Lambda events into HTTP requests to uvicorn. Elsewhere it does nothing.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=7860 AWS_LWA_READINESS_CHECK_PATH=/api/health AWS_LWA_PASS_THROUGH_PATH=/api/warmup

EXPOSE 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
