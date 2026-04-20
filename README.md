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

## Hosted Deployment

This repo is now set up to run as a single Docker service:

- FastAPI serves the API on port `7860`
- a bundled Next.js standalone server runs internally on port `3000`
- FastAPI proxies the frontend, so the public app and API share one origin

For a Hugging Face Docker Space:

- add `HUGGINGFACE_API_KEY` in Space Secrets
- add `TAVILY_API_KEY` in Space Secrets if you want web search
- optionally add `HF_STORE_REPO=username/private-dataset-repo` if you want memory/cases to survive restarts
- do not create a separate frontend Space for this repo
- do not set `NEXT_PUBLIC_API_URL` unless you intentionally want the UI to call some external API host

Important:

- free Hugging Face Spaces can sleep when idle, so they are not truly 24/7
- for always-on uptime, use upgraded HF hardware or another always-on host

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
export JANUS_DATA_DIR=./data
```

Optional overrides:

```bash
API_PORT=7860 WEB_PORT=3000 NEXT_PUBLIC_API_URL=http://localhost:7860 ./run-dev.sh
```

## Hugging Face Spaces

- this repo should be deployed as one Docker Space
- backend defaults to public port `7860`
- the frontend is bundled into the same container and served through the backend
