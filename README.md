# MiroOrg v1.1 - AI Financial Intelligence System

A general intelligence operating system that orchestrates multiple specialist agents, runs simulations, and supports pluggable domain packs with autonomous knowledge evolution.

## Overview

MiroOrg v1.1 is a 5-layer AI system that processes user requests through specialized agents, integrates domain-specific intelligence, runs simulations, and continuously improves itself over time:

- **Layer 1: Core Platform** - Multi-provider LLM abstraction (OpenRouter, Ollama, OpenAI) with automatic fallback
- **Layer 2: Domain Intelligence** - Pluggable domain packs (starting with Finance) that enhance agent capabilities
- **Layer 3: Agent Orchestration** - Five specialized agents working in concert
- **Layer 4: Simulation Lab** - Integration with MiroFish for scenario modeling
- **Layer 5: Autonomous Learning** - Self-improvement through knowledge ingestion, prompt evolution, and skill distillation

## Architecture

### Five Specialized Agents

1. **Switchboard** - Routes requests using 4-dimensional classification:
   - Task family (normal/simulation)
   - Domain pack (finance/general/policy/custom)
   - Complexity (simple/medium/complex)
   - Execution mode (solo/standard/deep)

2. **Research** - Gathers information with domain-enhanced capabilities:
   - Web search via Tavily
   - News via NewsAPI
   - Financial data via Alpha Vantage
   - Entity and ticker extraction for finance domain

3. **Verifier** - Validates information with credibility scoring:
   - Source reliability checking
   - Rumor and scam detection
   - Uncertainty quantification

4. **Planner** - Creates actionable plans with simulation awareness:
   - Detects opportunities for scenario modeling
   - Suggests simulation mode when appropriate

5. **Synthesizer** - Produces final answers with confidence metrics:
   - Uncertainty quantification
   - Simulation recommendations
   - Structured output with metadata

### Domain Pack System

Domain packs are pluggable modules that enhance agent capabilities for specific domains:

- **Finance Domain Pack** (included):
  - Market data integration
  - News analysis
  - Entity/ticker resolution
  - Credibility scoring
  - Stance detection
  - Event analysis
  - Prediction capabilities

- **Custom Domain Packs** (extensible):
  - Implement `DomainPack` base class
  - Register in domain registry
  - Agents automatically detect and use capabilities

### Autonomous Learning Layer

The system improves itself over time without local model training:

- **Knowledge Ingestion**: Automatically ingests knowledge from web search, news, and URLs
- **Experience Learning**: Learns from case execution patterns
- **Prompt Evolution**: A/B tests and evolves agent prompts
- **Skill Distillation**: Extracts reusable skills from repeated patterns
- **Trust Management**: Tracks source reliability over time
- **Freshness Management**: Manages knowledge expiration with domain-specific rules
- **Scheduler**: Runs learning tasks with CPU/battery safeguards for laptop deployment

Storage limits: 200MB max for knowledge cache, 2-4KB per summary.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- At least one LLM provider:
  - OpenRouter API key (recommended), or
  - Ollama running locally, or
  - OpenAI API key

### Backend Setup

1. Clone and navigate to backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Run backend:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend:
```bash
cd frontend
npm install
```

2. Configure environment:
```bash
cp .env.local.example .env.local
# Edit if needed (defaults to localhost:8000)
```

3. Run frontend:
```bash
npm run dev
```

Frontend available at `http://localhost:3000`

## Environment Variables

### Required

```env
# Primary LLM Provider (choose one)
PRIMARY_PROVIDER=openrouter  # or ollama, openai
OPENROUTER_API_KEY=your_key_here
# OR
OLLAMA_ENABLED=true
# OR
OPENAI_API_KEY=your_key_here
```

### Optional Services

```env
# Web Search
TAVILY_API_KEY=your_key_here

# News
NEWSAPI_KEY=your_key_here

# Financial Data
ALPHAVANTAGE_API_KEY=your_key_here

# Simulation Lab
MIROFISH_ENABLED=true
MIROFISH_API_BASE=http://127.0.0.1:5001

# Learning Layer
LEARNING_ENABLED=true
KNOWLEDGE_MAX_SIZE_MB=200
LEARNING_TOPICS=finance,markets,technology,policy
```

See `.env.example` for complete configuration options.

## API Endpoints

### Core Endpoints

- `GET /health` - Health check
- `GET /health/deep` - Detailed health with provider status
- `GET /config/status` - System configuration
- `POST /run` - Process user request through agent pipeline
- `GET /cases` - List case history
- `GET /cases/{id}` - Get case details

### Agent Endpoints

- `GET /agents` - List all agents
- `GET /agents/{name}` - Get agent details
- `POST /run/agent` - Run single agent

### Prompt Management

- `GET /prompts` - List all prompts
- `GET /prompts/{name}` - Get prompt content
- `PUT /prompts/{name}` - Update prompt

### Simulation Endpoints

- `POST /simulation/run` - Submit simulation request
- `GET /simulation/{id}` - Get simulation status
- `GET /simulation/{id}/report` - Get simulation report
- `POST /simulation/{id}/chat` - Chat with simulation

### Learning Endpoints

- `GET /learning/status` - Learning engine status
- `POST /learning/run-once` - Manually trigger learning task
- `GET /learning/insights` - Learning insights
- `GET /learning/knowledge` - List knowledge items
- `GET /learning/knowledge/search` - Search knowledge
- `POST /learning/knowledge/ingest` - Ingest knowledge
- `GET /learning/skills` - List distilled skills
- `POST /learning/skills/distill` - Distill new skills
- `GET /learning/sources/trust` - Get trusted sources
- `GET /learning/sources/freshness` - Get stale items
- `GET /learning/prompts/versions/{name}` - Get prompt versions
- `POST /learning/prompts/optimize/{name}` - Optimize prompt
- `POST /learning/prompts/promote/{name}/{version}` - Promote prompt

## Project Structure

```
backend/
├── app/
│   ├── agents/              # Five specialized agents
│   │   ├── _model.py        # Multi-provider LLM abstraction
│   │   ├── switchboard.py   # 4D routing
│   │   ├── research.py      # Domain-enhanced research
│   │   ├── verifier.py      # Credibility scoring
│   │   ├── planner.py       # Simulation-aware planning
│   │   └── synthesizer.py   # Final answer generation
│   ├── domain_packs/        # Pluggable domain intelligence
│   │   ├── base.py          # DomainPack base class
│   │   ├── registry.py      # Domain pack registry
│   │   └── finance/         # Finance domain pack
│   ├── services/            # Core services
│   │   ├── learning/        # Autonomous learning layer
│   │   │   ├── knowledge_ingestor.py
│   │   │   ├── knowledge_store.py
│   │   │   ├── learning_engine.py
│   │   │   ├── prompt_optimizer.py
│   │   │   ├── skill_distiller.py
│   │   │   ├── trust_manager.py
│   │   │   └── scheduler.py
│   │   ├── api_discovery/   # API discovery subsystem
│   │   ├── case_store.py    # Case persistence
│   │   ├── simulation_store.py
│   │   └── external_sources.py
│   ├── routers/             # API routers
│   │   ├── simulation.py
│   │   └── learning.py
│   ├── prompts/             # Agent prompts
│   ├── data/                # Data storage
│   │   ├── memory/          # Case records
│   │   ├── simulations/     # Simulation records
│   │   ├── knowledge/       # Knowledge cache
│   │   ├── skills/          # Distilled skills
│   │   ├── prompt_versions/ # Prompt versions
│   │   └── learning/        # Learning metadata
│   ├── config.py            # Configuration
│   ├── main.py              # FastAPI app
│   ├── schemas.py           # Pydantic models
│   └── graph.py             # Agent orchestration

frontend/
├── src/
│   ├── app/                 # Next.js pages
│   │   ├── page.tsx         # Dashboard
│   │   ├── analyze/         # Analysis interface
│   │   ├── cases/           # Case history
│   │   ├── simulation/      # Simulation interface
│   │   ├── prompts/         # Prompt lab
│   │   └── config/          # System config
│   ├── components/          # React components
│   │   ├── layout/
│   │   ├── common/
│   │   ├── analyze/
│   │   ├── cases/
│   │   ├── simulation/
│   │   └── prompts/
│   └── lib/
│       ├── api.ts           # API client
│       └── types.ts         # TypeScript types
```

## Development

### Adding a New Domain Pack

1. Create domain pack directory: `backend/app/domain_packs/your_domain/`
2. Implement `DomainPack` base class in `pack.py`
3. Add domain-specific modules (data sources, analyzers, etc.)
4. Register in `backend/app/domain_packs/init_packs.py`
5. Agents will automatically detect and use capabilities

### Customizing Agent Prompts

1. Navigate to `backend/app/prompts/`
2. Edit prompt files (research.txt, planner.txt, etc.)
3. Changes take effect immediately (no restart needed)
4. Use Prompt Lab UI for live editing

### Running with Different Providers

**OpenRouter (recommended for production):**
```env
PRIMARY_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
```

**Ollama (local, privacy-focused):**
```env
PRIMARY_PROVIDER=ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434/api
```

**OpenAI (high quality):**
```env
PRIMARY_PROVIDER=openai
OPENAI_API_KEY=your_key
```

## Deployment

### Single-User Local Deployment (Recommended)

This system is optimized for single-user local deployment on laptops (tested on 8GB/256GB M2 Air):

- Learning scheduler respects CPU usage (<50%) and battery level (>30%)
- Knowledge cache limited to 200MB with LRU eviction
- All data stored locally in `backend/app/data/`
- No cloud dependencies required

### Production Deployment

For multi-user production deployment:

1. Add authentication and authorization
2. Use PostgreSQL instead of JSON storage
3. Add rate limiting and request queuing
4. Deploy with Docker/Kubernetes
5. Use managed LLM services
6. Add monitoring and alerting

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
