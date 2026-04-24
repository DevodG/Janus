# MiroOrg v1.1 Architecture

## System Overview

MiroOrg v1.1 is a 5-layer AI intelligence system designed for single-user local deployment with autonomous learning capabilities.

## Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Autonomous Knowledge Evolution                    │
│  - Knowledge ingestion from web/news                        │
│  - Experience learning from cases                           │
│  - Prompt evolution via A/B testing                         │
│  - Skill distillation from patterns                         │
│  - Trust & freshness management                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Simulation Lab Integration                        │
│  - MiroFish adapter for scenario modeling                   │
│  - Case-simulation linking                                  │
│  - Simulation result synthesis                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Agent Orchestration                               │
│  - Switchboard (4D routing)                                 │
│  - Research (domain-enhanced)                               │
│  - Verifier (credibility scoring)                           │
│  - Planner (simulation-aware)                               │
│  - Synthesizer (uncertainty quantification)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Domain Intelligence                               │
│  - Pluggable domain packs                                   │
│  - Finance pack (market data, news, analysis)               │
│  - Domain registry & detection                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Core Platform                                     │
│  - Multi-provider LLM (OpenRouter/Ollama/OpenAI)           │
│  - Automatic fallback                                       │
│  - Configuration management                                 │
│  - Data persistence                                         │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Core Platform

### Multi-Provider LLM Abstraction

The system supports three LLM providers with automatic fallback:

1. **OpenRouter** - Recommended for production
   - Access to multiple models
   - Pay-per-use pricing
   - High availability

2. **Ollama** - Local deployment
   - Privacy-focused
   - No API costs
   - Requires local GPU/CPU

3. **OpenAI** - High quality
   - GPT-4 and GPT-3.5
   - Reliable performance
   - Higher cost

**Fallback Chain:**
```
Primary Provider → Fallback Provider → Error
```

### Configuration Management

All configuration via environment variables:
- Provider selection
- API keys
- Feature flags
- Domain pack enablement
- Learning layer settings

### Data Persistence

JSON-based storage for single-user deployment:
- Cases: `backend/app/data/memory/`
- Simulations: `backend/app/data/simulations/`
- Knowledge: `backend/app/data/knowledge/`
- Skills: `backend/app/data/skills/`
- Prompt versions: `backend/app/data/prompt_versions/`

## Layer 2: Domain Intelligence

### Domain Pack System

Domain packs are pluggable modules that enhance agent capabilities:

```python
class DomainPack(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Domain pack name (e.g., 'finance')"""
        pass
    
    @property
    @abstractmethod
    def keywords(self) -> List[str]:
        """Keywords for domain detection"""
        pass
    
    @abstractmethod
    async def enhance_research(self, query: str, context: Dict) -> Dict:
        """Enhance research with domain-specific capabilities"""
        pass
    
    @abstractmethod
    async def enhance_verification(self, claims: List[str], context: Dict) -> Dict:
        """Enhance verification with domain-specific checks"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """List domain-specific capabilities"""
        pass
```

### Finance Domain Pack

Included capabilities:
- **Market Data**: Real-time quotes via Alpha Vantage
- **News**: Financial news via NewsAPI
- **Entity Resolution**: Extract and normalize company names
- **Ticker Resolution**: Map companies to stock tickers
- **Source Checking**: Credibility scoring for financial sources
- **Rumor Detection**: Identify unverified claims
- **Scam Detection**: Flag potential scams
- **Stance Detection**: Analyze sentiment and stance
- **Event Analysis**: Analyze market-moving events
- **Prediction**: Generate market predictions

### Domain Detection

Automatic domain detection based on keywords:
```python
# Finance keywords
["stock", "market", "trading", "investment", "portfolio", 
 "earnings", "dividend", "IPO", "merger", "acquisition"]
```

## Layer 3: Agent Orchestration

### Agent Pipeline

```
User Input
    ↓
Switchboard (4D Routing)
    ↓
Research (Domain-Enhanced)
    ↓
Planner (Simulation-Aware)
    ↓
Verifier (Credibility Scoring)
    ↓
Synthesizer (Final Answer)
    ↓
Case Storage
```

### Switchboard Agent

**Four-Dimensional Classification:**

1. **Task Family**
   - `normal`: Standard analysis
   - `simulation`: Scenario modeling

2. **Domain Pack**
   - `finance`: Financial domain
   - `general`: General knowledge
   - `policy`: Policy analysis
   - `custom`: Custom domains

3. **Complexity**
   - `simple`: ≤5 words
   - `medium`: 6-25 words
   - `complex`: >25 words

4. **Execution Mode**
   - `solo`: Synthesizer only (simple queries)
   - `standard`: Research → Synthesizer (medium queries)
   - `deep`: Full pipeline (complex queries)

### Research Agent

**Capabilities:**
- Web search via Tavily
- News search via NewsAPI
- Domain-specific data sources
- Entity extraction
- Source credibility assessment

**Domain Enhancement:**
```python
if domain == "finance":
    # Extract tickers and entities
    # Fetch market data
    # Get financial news
    # Score source credibility
```

### Verifier Agent

**Verification Process:**
1. Extract claims from research
2. Check source reliability
3. Detect rumors and scams
4. Quantify uncertainty
5. Flag high-risk claims

**Domain Enhancement:**
```python
if domain == "finance":
    # Check financial source credibility
    # Detect market manipulation
    # Verify regulatory compliance
```

### Planner Agent

**Planning Process:**
1. Analyze research findings
2. Identify action items
3. Detect simulation opportunities
4. Create structured plan

**Simulation Detection:**
- Keywords: "predict", "what if", "scenario", "impact"
- Uncertainty level: High
- Recommendation: Suggest simulation mode

### Synthesizer Agent

**Synthesis Process:**
1. Combine all agent outputs
2. Quantify uncertainty
3. Generate final answer
4. Add metadata (confidence, sources, etc.)

**Output Structure:**
```json
{
  "summary": "Final answer",
  "confidence": 0.85,
  "uncertainty_factors": [...],
  "sources": [...],
  "simulation_recommended": false
}
```

## Layer 4: Simulation Lab Integration

### MiroFish Adapter

Adapter pattern for simulation integration:

```python
class MiroFishClient:
    async def submit_simulation(self, title, seed_text, prediction_goal):
        """Submit simulation to MiroFish"""
        
    async def get_status(self, simulation_id):
        """Get simulation status"""
        
    async def get_report(self, simulation_id):
        """Get simulation report"""
        
    async def chat(self, simulation_id, message):
        """Chat with simulation"""
```

### Case-Simulation Linking

Cases and simulations are linked:
```json
{
  "case_id": "uuid",
  "simulation_id": "uuid",
  "user_input": "...",
  "route": {...},
  "outputs": {...},
  "final_answer": "..."
}
```

### Simulation Workflow

```
User Input with Simulation Keywords
    ↓
Switchboard (task_family="simulation")
    ↓
Research (gather context)
    ↓
Submit to MiroFish
    ↓
Poll for completion
    ↓
Synthesize results
    ↓
Return to user
```

## Layer 5: Autonomous Knowledge Evolution

### Knowledge Ingestion

**Sources:**
- Web search (Tavily)
- News (NewsAPI)
- URLs (Jina Reader)

**Process:**
1. Fetch content from source
2. Compress to 2-4KB summary using LLM
3. Store with metadata
4. Enforce 200MB storage limit
5. LRU eviction when limit reached

**Scheduling:**
- Every 6 hours (configurable)
- Only when system idle (CPU <50%)
- Only when battery OK (>30%)

### Experience Learning

**Learning from Cases:**
1. Extract metadata from case execution
2. Detect patterns (domain, sources, agents)
3. Track route effectiveness
4. Track prompt performance
5. Track provider reliability

**Pattern Detection:**
- Domain expertise patterns
- Preferred source patterns
- Agent workflow patterns
- Minimum frequency: 3 occurrences

### Prompt Evolution

**A/B Testing Process:**
1. Create prompt variant using LLM
2. Test variant with sample inputs
3. Measure quality metrics
4. Compare win rates
5. Promote if criteria met (>70% win rate, >10 tests)

**Versioning:**
```json
{
  "id": "uuid",
  "prompt_name": "research",
  "version": 2,
  "status": "testing",
  "test_count": 15,
  "win_count": 12,
  "win_rate": 0.80
}
```

### Skill Distillation

**Skill Creation:**
1. Detect patterns in successful cases
2. Distill into reusable skills
3. Test skills with validation cases
4. Track usage and success rate

**Skill Structure:**
```json
{
  "id": "domain_expertise_finance",
  "type": "domain_expertise",
  "trigger_patterns": ["stock", "market"],
  "recommended_agents": ["research", "verifier"],
  "preferred_sources": ["bloomberg", "reuters"],
  "success_rate": 0.85
}
```

### Trust Management

**Source Trust Scoring:**
- Initial score: 0.5 (neutral)
- Updated based on verification outcomes
- Exponential moving average
- Minimum verifications: 3

**Trust Categories:**
- Trusted: score ≥0.7, verifications ≥3
- Untrusted: score ≤0.3, verifications ≥3
- Unknown: verifications <3

### Freshness Management

**Domain-Specific Expiration:**
- Finance: 7-day half-life
- General: 30-day half-life
- Exponential decay: `freshness = 2^(-age_days / half_life_days)`

**Refresh Recommendations:**
- Freshness <0.3: Stale
- Prioritize by staleness
- Automatic refresh during scheduled ingestion

### Learning Scheduler

**Safeguards:**
- CPU usage check: <50%
- Battery level check: >30%
- System idle detection
- Error handling with backoff

**Scheduled Tasks:**
- Knowledge ingestion: Every 6 hours
- Expired cleanup: Daily
- Pattern detection: Daily
- Skill distillation: Weekly
- Prompt optimization: Weekly

## Data Flow

### Normal Request Flow

```
1. User submits request
2. Switchboard classifies (4D)
3. Domain pack detected
4. Research gathers info (domain-enhanced)
5. Planner creates plan
6. Verifier validates (domain-enhanced)
7. Synthesizer produces answer
8. Case saved
9. Learning extracts metadata
```

### Simulation Request Flow

```
1. User submits request with simulation keywords
2. Switchboard detects simulation
3. Research gathers context
4. Submit to MiroFish
5. Poll for completion
6. Synthesize results
7. Case and simulation saved
8. Learning extracts metadata
```

### Learning Flow

```
1. Scheduler checks system conditions
2. If idle and battery OK:
   a. Ingest knowledge from sources
   b. Compress to 2-4KB summaries
   c. Store with metadata
   d. Enforce storage limits
3. Detect patterns in recent cases
4. Distill skills from patterns
5. Optimize prompts via A/B testing
6. Update trust scores
7. Calculate freshness scores
```

## Deployment Considerations

### Single-User Local (Recommended)

**Optimizations:**
- JSON storage (no database)
- Learning scheduler with safeguards
- 200MB knowledge cache limit
- CPU/battery awareness
- Automatic LRU eviction

**Hardware Requirements:**
- 8GB RAM minimum
- 256GB storage minimum
- M2 Air or equivalent

### Multi-User Production

**Required Changes:**
- PostgreSQL for storage
- Redis for caching
- Authentication/authorization
- Rate limiting
- Request queuing
- Monitoring/alerting
- Horizontal scaling

## Security

### API Key Management

- All keys in environment variables
- Never committed to source control
- Validated on startup

### Error Handling

- Sanitized error messages
- No internal details leaked
- Comprehensive logging

### Input Validation

- Pydantic schemas for all inputs
- Type checking
- Length limits
- Sanitization

## Performance

### Response Times

- Simple queries: <5s
- Medium queries: <15s
- Complex queries: <30s
- Simulations: 60-120s

### Optimization Strategies

- Connection pooling for external APIs
- Request timeouts (30s)
- Caching for market quotes (5min TTL)
- Rate limiting for external APIs
- Async/await throughout

## Monitoring

### Health Checks

- `/health` - Basic health
- `/health/deep` - Detailed health with provider status

### Metrics

- Case execution time
- Provider success/failure rates
- Domain pack usage
- Learning task completion
- Storage usage

### Logging

- Structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Rotation and retention
- Provider fallback events
- Learning task events
