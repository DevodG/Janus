FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /frontend

ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps

COPY frontend/ ./

ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build && \
    mkdir -p /frontend-standalone/.next && \
    cp -r .next/standalone/. /frontend-standalone/ && \
    if [ -d public ]; then cp -r public /frontend-standalone/public; fi && \
    cp -r .next/static /frontend-standalone/.next/static

FROM node:20-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /opt/venv/bin/python -m playwright install --with-deps chromium

COPY --from=frontend-builder /frontend-standalone /app/frontend

COPY backend/ ./backend/
RUN ln -sf /app/backend/app /app/app
RUN mkdir -p /app/backend/app/data/context /app/backend/app/data/daemon /app/backend/app/data/adaptive /app/backend/app/data/knowledge /app/backend/app/data/memory /app/backend/app/data/simulations /app/backend/app/data/distilled_models /app/backend/app/data/metrics /app/backend/app/data/kaggle

ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV PYTHONPATH=/app
ENV NEXT_STANDALONE_DIR=/app/frontend
ENV NEXT_INTERNAL_PORT=3000

EXPOSE 7860

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
