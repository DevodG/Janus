---
title: Janus
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---
# Rebuild trigger Fri Apr 10 15:59:28 IST 2026

## Run Locally

Start the backend and frontend together from the repo root:

```bash
./run-dev.sh
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:7860`

Prerequisites:

- backend virtualenv at `backend/.venv`
- frontend dependencies installed in `frontend/`
- required secrets available in your shell or environment manager

Useful env vars:

```bash
export HUGGINGFACE_API_KEY=...
export TAVILY_API_KEY=...
```

Optional overrides:

```bash
API_PORT=7860 WEB_PORT=3000 NEXT_PUBLIC_API_URL=http://localhost:7860 ./run-dev.sh
```

## Hugging Face Spaces

- Keep backend secrets in the backend Space secrets
- Set `NEXT_PUBLIC_API_URL` in the frontend Space to your backend Space URL
- Backend defaults to port `7860`
