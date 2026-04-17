FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
RUN mkdir -p /app/backend/app/data/context /app/backend/app/data/daemon /app/backend/app/data/adaptive /app/backend/app/data/knowledge /app/backend/app/data/memory /app/backend/app/data/simulations

ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV PYTHONPATH=/app

EXPOSE 7860

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
