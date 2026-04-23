---
title: Janus ZeroTrust Sentinel
emoji: 🛡️
colorFrom: indigo
colorTo: slate
sdk: docker
app_file: app.py
pinned: true
---

# Janus: The ZeroTrust Scam Journey Guardian

Janus is a proactive, multimodal intelligence sentinel designed to detect, intercept, and neutralize the entire lifecycle of a scam journey. Unlike standard phishing filters, Janus utilizes a **Multimodal Dissonance Engine** and a **Scam Journey Graph** to link disparate signals—SMS, URLs, Voice, and Documents—into a persistent relational threat map.

## 🛡️ The ZeroTrust Defensive Architecture

Janus operates on a **ZeroTrust Execution Mode**, assuming every incoming signal is potentially part of a sophisticated deception campaign until proven otherwise.

- **Active Interception**: The `GuardianInterceptor` audits the real-time signal stream, autonomously squashing high-risk trajectories before they can interact with the user.
- **Dissonance Fusion**: Fuses Link Intelligence (LinkBrain) with the **MMSA Engine** to analyze the dissonance between audio-visual content and metadata signatures.
- **Relational Threat Mapping**: The `ScamGraph` links entities (Phone numbers, UPI IDs, URL patterns) into a complex relational graph to identify persistent scammer clusters.
- **Forensic Intake Hub**: A dedicated Safety Gateway for manual ingestion and high-diligence analysis of suspicious SMS, Chat logs, and Files.

## 🧠 Core Sensory Hubs

- **Optical Forensics**: OCR-driven extraction of scam intent from screenshots and document trails.
- **Document Guardian**: Native PDF forensic analysis to detect fraudulent bank statements, KYC phishing, and malicious attachments.
- **Link Dissonance**: Deep-probing of URLs for typosquatting, domain age anomalies, and media-layer deception.
- **MMSA Engine**: High-fidelity audio-visual analysis for YouTube and video-based financial scams.

## 🚀 Deployment (Hugging Face Spaces / Docker)

Janus is optimized for **Hugging Face Docker Spaces** as a unified service:

1.  **Secrets Configuration**:
    - `HUGGINGFACE_API_KEY`: Required for core cognitive reasoning.
    - `TAVILY_API_KEY`: Required for deep web research and threat verification.
    - `HF_STORE_REPO`: (Optional) Persistent dataset repo for long-term memory.
2.  **Architecture**:
    - **FastAPI** serves the Janus Gateway on port `7860`.
    - **Next.js** serves the Sentinel Dashboard internally on port `3000`.
    - Automated proxying ensures one seamless origin for the API and UI.

## 🛠️ Run Locally

Initialize the Janus cognitive cluster from the repository root:

```bash
./run-dev.sh
```

### Prerequisites
- **Backend**: Python 3.10+ virtualenv at `backend/.venv`
- **Frontend**: Node.js dependencies installed in `frontend/`
- **Sensory**: `easyocr` and `pymupdf` are required for full forensic capabilities.

### Environment variables
```bash
export HUGGINGFACE_API_KEY=...
export TAVILY_API_KEY=...
export JANUS_DATA_DIR=./data
```

---
*Janus adapts. Janus Intercepts. Janus Protects.*
