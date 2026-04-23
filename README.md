---
title: Janus ZeroTrust Sentinel
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_file: app.py
pinned: true
---

# Janus: The Multimodal Intelligence Sentinel

Janus is a self-evolving, multi-agent cognitive system designed for high-fidelity financial intelligence and proactive **ZeroTrust** protection. It doesn't just process data; it **dreams**, **reflects**, and **intercepts** scam journeys before they manifest.

## 🌊 The Janus Cognitive Signal Flow

Every signal entering the Janus cluster undergoes a multi-stage cognitive transformation:

1.  **Smart Routing**: The `SmartRouter` classifies intent (Finance, Security, Research) and determines the optimal agent swarm configuration.
2.  **ZeroTrust Audit**: The `GuardianInterceptor` performs an immediate heuristic and relational scan for deception patterns.
3.  **Parallel Execution**:
    - **Curiosity Node**: Proactively discovers market anomalies and news pulses.
    - **Research Swarm**: Performs deep-web evidence gathering and credibility scoring.
    - **Mirofish Simulation**: Runs predictive scenario modeling (Monte Carlo / Predictive AI).
4.  **The Reflection Loop**:
    - **Dream Engine**: Generates speculative "what-if" scenarios based on current discoveries.
    - **Self-Reflection**: Critical audit of agent outputs to minimize hallucination and bias.
5.  **Synthesis & Verification**: The `Verifier` node merges disparate outputs into a unified, high-confidence brief.
6.  **Adaptive Memory**: Learnings are enrolled in the persistent `ScamGraph` and context engine for future recall.

## 🛡️ ZeroTrust Defensive Architecture

- **Active Interception**: Autonomous signal squashing for confirmed scam trajectories.
- **Multimodal Dissonance Fusion**: Fuses link heuristics with the **MMSA Engine** for YouTube/Video forensic probing.
- **Relational Threat Mapping**: Tracks persistent "Scam Journeys" by linking scattered entities in the `ScamGraph`.
- **Forensic Safety Gateway**: A dedicated portal for deep-probing SMS, Chat logs, and malicious files.

## 📈 Financial & Adaptive Intelligence

- **Autonomous Curiosity**: The system never sleeps; it continuously scans global markets and sentiment shifts.
- **Dream-to-Reality Synthesis**: Uses historical market data and generative dreaming to predict volatility and opportunities.
- **Cross-Case Pattern Analysis**: Identifies systemic patterns (e.g., typosquatting clusters or sector-wide anomalies) across unrelated user cases.
- **Market Watcher**: Real-time integration with AlphaVantage and NewsAPI for live-streaming financial truth.

## 🚀 Deployment (Hugging Face Spaces / Docker)

Janus is a unified Docker service:

1.  **Secrets Configuration**:
    - `HUGGINGFACE_API_KEY`: Core cognitive reasoning.
    - `TAVILY_API_KEY`: Deep-web evidence gathering.
    - `HF_STORE_REPO`: Persistent dataset storage.
2.  **Unified Origin**: FastAPI proxies the Next.js Sentinel Dashboard, serving the entire system from a single origin (Port `7860`).

## 🛠️ Run Locally

```bash
./run-dev.sh
```

### Prerequisites
- **Cognitive**: Python 3.10+ (backend/.venv)
- **Visuals**: Next.js 14+ (frontend/)
- **Sensory**: `easyocr` (OCR), `pymupdf` (PDF), `yt-dlp` (MMSA Video).

---
*Janus adapts. Janus Dreams. Janus Protects.*
