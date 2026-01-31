# T073: FastAPI + Streamlit 공통 이미지 (multi-stage 빌드)

# ── Stage 1: 빌드 ──
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: 런타임 ──
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /install /usr/local

COPY src/ ./src/
COPY ui/ ./ui/
COPY scripts/ ./scripts/

RUN mkdir -p /app/data/chroma /app/data/manuals /app/static/images

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV API_BASE_URL=http://localhost:8000/api/v1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000 8501

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
