---
title: Janus
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Janus

**Cognitive Intelligence Interface** — A multi-agent AI system that researches, simulates scenarios, and produces expert-level analysis.

Built for your Mac. Runs on free models. Gets smarter with every query.

## What It Does

Janus takes any question — financial, strategic, technical — and runs it through an orchestrated pipeline of specialist agents that gather data, analyze from multiple perspectives, and produce deep, non-generic answers.

- **Command** — Ask anything. The system routes, researches, and synthesizes.
- **Intel Stream** — Live news feed with deep research on any article.
- **Markets** — Embedded candlestick charts, ticker intelligence, AI signals, and event analysis — all in-app.
- **Simulation Lab** — Native scenario engine: decomposes "what if" questions → runs 4 perspectives (optimist/pessimist/realist/contrarian) → synthesizes outcomes with probabilities, early warning signals, and decision frameworks.
- **Sentinel** — System health, domain expertise tracking, cache performance, and cross-case pattern recognition.

## Architecture

### Agent Pipeline (2-3 model calls, optimized)

```
User Query
    │
    ▼
┌─────────────┐
│ Switchboard │  ← Classifies query type, domain, complexity
└──────┬──────┘
       │
  ┌────┴────┐
  │ Finance │  ← Alpha Vantage data (if market query)
  └────┬────┘
       │
  ┌────┴────┐
  │Research │  ← Tavily web search, News API, knowledge base
  └────┬────┘
       │
┌──────┴───────┐
│ Synthesizer  │  ← Deep analysis with all context
└──────┬───────┘
       │
       ▼
   Final Answer
```

### Native Simulation Engine

Replaces external dependencies. When a query triggers simulation:

1. **Decompose** — Identifies variables, actors, forces, constraints
2. **4 Perspectives** — Optimist, Pessimist, Realist, Contrarian each analyze independently
3. **Synthesize** — Combines into scenarios with probability distributions, impact levels, timelines, and early warning signals

### Intelligent Caching

- **Generic queries** (definitions, simple facts) → cached for 30 days, instant response
- **Specific queries** (analysis, reasoning) → cached for 7 days, learned from
- **Hybrid queries** → cached for 14 days, conditionally learned from

### Adaptive Intelligence

The system builds institutional knowledge over time:
- **Domain Expertise** — Tracks key entities, trusted sources, success rates per domain
- **Cross-Case Patterns** — Finds patterns across all queries that no single query reveals
- **System Personality** — Adapts analytical depth and skepticism based on accumulated experience

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- At least one LLM provider (OpenRouter recommended for free tier)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your API keys

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend: `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

## Environment Variables

### Required (pick one LLM provider)

```env
# OpenRouter (recommended — free tier available)
PRIMARY_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY

# Or Ollama (local)
PRIMARY_PROVIDER=ollama
OLLAMA_ENABLED=true

# Or OpenAI
PRIMARY_PROVIDER=openai
OPENAI_API_KEY=sk-proj-YOUR_KEY
```

### Optional (enhance capabilities)

```env
# Web search (research quality)
TAVILY_API_KEY=tvly-dev-YOUR_KEY

# News (event intelligence)
NEWSAPI_KEY=YOUR_KEY

# Market data (charts, ticker intelligence)
ALPHAVANTAGE_API_KEY=YOUR_KEY
```

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/health/deep` | Detailed health with provider status |
| `GET` | `/config/status` | System configuration |
| `POST` | `/run` | Process query through agent pipeline |
| `GET` | `/cases` | List case history |
| `GET` | `/cases/{id}` | Get case details |

### Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/intelligence/report` | Full adaptive intelligence report |
| `GET` | `/intelligence/domain/{domain}` | Domain-specific expertise |
| `GET` | `/cache/stats` | Cache statistics |
| `POST` | `/cache/cleanup` | Clean expired cache entries |

### Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/simulation/run` | Run native simulation |
| `GET` | `/simulation/list` | List all simulations |
| `GET` | `/simulation/{id}` | Simulation details |
| `GET` | `/simulation/{id}/report` | Simulation report |
| `POST` | `/simulation/{id}/chat` | Chat with simulation |

### Markets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/finance/headlines` | Top business headlines |
| `POST` | `/finance/news/analyze` | Analyze news for a query |
| `GET` | `/finance/ticker/{symbol}` | Full ticker intelligence |
| `GET` | `/finance/search/{query}` | Search tickers |

### Agents & Prompts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/agents` | List all agents |
| `GET` | `/agents/{name}` | Agent details |
| `GET` | `/prompts` | List all prompts |
| `GET` | `/prompts/{name}` | Get prompt |
| `PUT` | `/prompts/{name}` | Update prompt |

### Sentinel

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sentinel/status` | System health status |
| `GET` | `/sentinel/alerts` | Recent alerts |
| `GET` | `/sentinel/capability/current` | Capability snapshot |

## Project Structure

```
backend/
├── app/
│   ├── agents/              # Specialist agents
│   │   ├── _model.py        # Multi-provider LLM (OpenRouter → Ollama fallback)
│   │   ├── switchboard.py   # Query routing & classification
│   │   ├── research.py      # Web search, news, knowledge gathering
│   │   ├── synthesizer.py   # Final answer generation
│   │   ├── mirofish_node.py # Native simulation trigger
│   │   └── finance_node.py  # Market data integration
│   ├── services/            # Core services
│   │   ├── simulation_engine.py    # Native scenario simulation
│   │   ├── adaptive_intelligence.py # Domain expertise & pattern recognition
│   │   ├── cache_manager.py        # Intelligent query caching
│   │   ├── query_classifier.py     # GENERIC/SPECIFIC/HYBRID classification
│   │   └── learning_filter.py      # Decides what to learn from
│   ├── routers/             # API routers
│   │   ├── simulation.py    # Native simulation endpoints
│   │   ├── learning.py      # Learning layer
│   │   ├── sentinel.py      # System monitoring
│   │   └── finance.py       # Market intelligence
│   ├── prompts/             # Agent system prompts
│   ├── graph.py             # LangGraph pipeline
│   ├── main.py              # FastAPI application
│   └── config.py            # Configuration
│
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx         # Main app (Command / Intel / Markets)
│   │   ├── simulation/      # Simulation lab
│   │   ├── sentinel/        # System health & intelligence
│   │   └── cases/           # Case history
│   ├── lib/
│   │   ├── api.ts           # API clients
│   │   └── types.ts         # TypeScript types
│   └── components/          # Shared UI components
```

## Design

- **Dark premium interface** — Glass cards, strong hierarchy, clean typography
- **Embedded charts** — TradingView Lightweight Charts v5, no external redirections
- **Responsive** — Works on any screen size
- **Smooth motion** — Framer Motion for meaningful transitions

## License

MIT
