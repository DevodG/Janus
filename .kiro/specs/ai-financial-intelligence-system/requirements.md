# Requirements Document

## Introduction

This document specifies requirements for MiroOrg v1.1, a general intelligence operating system that orchestrates multiple specialist agents, runs simulations, supports pluggable domain packs, and autonomously improves itself over time. The system merges capabilities from miroorg-basic-v2 (base architecture), impact_ai (first domain pack), MiroFish (simulation lab), and public-apis (API discovery catalog) into a unified, production-ready platform. The architecture follows a five-layer design: Core Platform, Agent Organization, Domain Packs, Simulation Lab, and Autonomous Knowledge Evolution Layer.

## Glossary

- **System**: MiroOrg v1.1 - The general intelligence operating system
- **Core_Platform**: Layer 1 - FastAPI backend, frontend dashboard, config, health, memory, prompts, cases, logs
- **Agent_Organization**: Layer 2 - Multi-agent orchestration framework (Switchboard, Research, Planner, Verifier, Synthesizer)
- **Domain_Packs**: Layer 3 - Pluggable domain intelligence modules (finance/news from impact_ai as first pack)
- **Simulation_Lab**: Layer 4 - MiroFish integration for simulation, digital-world modeling, and scenario analysis
- **Autonomous_Knowledge_Evolution_Layer**: Layer 5 - Self-improving intelligence system that learns from internet knowledge, past cases, prompt evolution, and skill distillation
- **Knowledge_Item**: Compressed structured record of external information with summary, entities, trust score, and freshness score
- **Skill**: Distilled reusable workflow pattern extracted from repeated successful case executions
- **Trust_Score**: Measure of source reliability learned from verification outcomes (0.0 - 1.0)
- **Freshness_Score**: Measure of information recency and relevance (0.0 - 1.0)
- **Prompt_Version**: Versioned prompt with performance metadata (win_rate, status, last_tested)
- **Switchboard**: Routing agent that classifies tasks by family, domain, complexity, and execution mode
- **Research_Agent**: Agent responsible for gathering context, extracting entities, and fetching external information
- **Planner_Agent**: Agent that converts research into practical action plans
- **Verifier_Agent**: Agent that validates credibility, detects rumors/scams, and surfaces uncertainty
- **Synthesizer_Agent**: Agent that produces final comprehensive responses with honest uncertainty
- **Provider_Layer**: Abstraction for AI model providers (OpenRouter, Ollama, future OpenAI)
- **Case**: A stored execution record containing inputs, routing decisions, agent outputs, and results
- **MiroFish**: External simulation service for graph building, environment setup, simulation, report generation, and deep interaction
- **Domain_Pack**: Pluggable module providing domain-specific intelligence (finance is first, others follow)
- **API_Discovery**: Subsystem using public-apis catalog for discovering and classifying free APIs
- **Ticker**: Stock market symbol (e.g., AAPL, TSLA)
- **Entity**: Company, organization, person, or concept mentioned in text
- **Source_Credibility**: Measure of trustworthiness for information sources
- **Analyze_Mode**: Execution mode for summarization, research, and analysis tasks
- **Organization_Mode**: Execution mode using multi-agent collaboration
- **Simulation_Mode**: Execution mode for scenario forecasting and what-if modeling

## Requirements

### Requirement 1: Repository Ownership and Merge Strategy

**User Story:** As a developer, I want clear repository ownership rules, so that I can merge codebases without architectural confusion.

#### Acceptance Criteria

1. THE System SHALL use miroorg-basic-v2 as the primary repo and canonical architecture
2. THE System SHALL treat impact_ai as a source of reusable domain modules, not as an equal structural peer
3. THE System SHALL integrate MiroFish as a separate service through a client adapter
4. THE System SHALL treat public-apis/public-apis as a discovery dataset for future connector expansion, not as a runtime dependency
5. WHEN overlapping logic exists between repos, THE System SHALL choose one canonical implementation and remove dead duplicates
6. THE System SHALL preserve the existing miroorg-basic-v2 folder structure as the base architecture
7. THE System SHALL maintain separate directories for agents, services, routers, prompts, and core configuration
8. THE System SHALL use environment variables for all configuration and API keys

### Requirement 2: Five-Layer Architecture

**User Story:** As a system architect, I want a clear five-layer architecture, so that the system can scale across multiple domains, use cases, and autonomously improve over time.

#### Acceptance Criteria

1. THE System SHALL implement Layer 1 (Core Platform) with FastAPI backend, frontend dashboard, config, health, memory, prompts, cases, and logs
2. THE System SHALL implement Layer 2 (Agent Organization) with Switchboard, Research Agent, Planner Agent, Verifier Agent, and Synthesizer Agent
3. THE System SHALL implement Layer 3 (Domain Packs) with finance/news intelligence from impact_ai as the first pack
4. THE System SHALL implement Layer 4 (Simulation Lab) with MiroFish integration for simulation and digital-world modeling
5. THE System SHALL implement Layer 5 (Autonomous Knowledge Evolution Layer) with world knowledge ingestion, experience learning, prompt evolution, skill distillation, and trust management
6. THE System SHALL support future domain packs (policy, cyber, enterprise ops, research, education) without changing Layer 2
7. THE System SHALL support optional future agents (Risk, Market, Simulation, Compliance) in Layer 2
8. THE System SHALL maintain clear separation between layers with well-defined interfaces

### Requirement 3: Product Modes

**User Story:** As a user, I want the system to support different execution modes, so that I can choose the appropriate approach for my task.

#### Acceptance Criteria

1. THE System SHALL support Analyze Mode for summarization, research, market/news analysis, entity/ticker detection, credibility/risk evaluation, and actionable recommendations
2. THE System SHALL support Organization Mode for multi-agent debate, planning, verification, synthesis, and case memory workflows
3. THE System SHALL support Simulation Mode for scenario forecasting, market reaction prediction, stakeholder reaction modeling, policy/narrative/reputation simulation, and post-simulation questioning
4. WHEN Simulation Mode is used, THE System SHALL use MiroFish through adapter endpoints, not through frontend-direct calls
5. THE System SHALL route tasks to the appropriate mode based on Switchboard classification

### Requirement 4: Switchboard Routing and Classification

**User Story:** As a user, I want intelligent task routing, so that my requests are handled by the appropriate execution path.

#### Acceptance Criteria

1. THE Switchboard SHALL classify every task using four dimensions: task_family (normal or simulation), domain_pack (finance, general, policy, custom), complexity (simple, medium, complex), and execution_mode (solo, standard, deep)
2. WHEN complexity is simple, THE Switchboard SHALL route to solo execution mode (minimal path)
3. WHEN complexity is medium, THE Switchboard SHALL route to standard execution mode (normal multi-agent path)
4. WHEN complexity is complex, THE Switchboard SHALL route to deep execution mode (full multi-agent path with optional verifier and optional simulation handoff)
5. WHEN user input contains simulation trigger keywords, THE Switchboard SHALL route to Simulation Mode
6. THE System SHALL make simulation trigger keywords environment-configurable
7. THE Switchboard SHALL detect keywords including: simulate, predict, model reaction, test scenarios, run digital twins, explore "what if" outcomes
8. THE Switchboard SHALL include routing decision in case metadata

### Requirement 5: Domain Engine Integration

**User Story:** As a financial analyst, I want the system to leverage impact_ai's financial intelligence modules, so that I can perform sophisticated market and news analysis.

#### Acceptance Criteria

1. THE System SHALL integrate impact_ai as the first domain pack
2. THE System SHALL inspect and reuse valuable modules including: alpha_vantage_client.py, news_api.py, brain.py, event_analyzer.py, ticker_resolver.py, source_checker.py, rumor_detector.py, scam_detector.py, stance_detector.py, prediction.py, market_data.py, entity_resolver.py
3. THE System SHALL expose domain pack capabilities through the MiroOrg service layer, not as scattered utility scripts
4. THE System SHALL consolidate overlapping external API clients (Alpha Vantage, NewsAPI) with existing external_sources.py
5. WHEN integrating impact_ai modules, THE System SHALL refactor code to match the existing service layer pattern
6. THE System SHALL design the architecture to support additional domain packs later without changing the agent organization layer
7. THE System SHALL treat finance as the first deep pack, not the only pack

### Requirement 6: Provider Abstraction Layer

**User Story:** As a system administrator, I want a unified provider interface, so that I can switch between AI model providers without changing agent code.

#### Acceptance Criteria

1. THE System SHALL create a provider abstraction layer with a single call_model() interface
2. THE System SHALL support OpenRouter as a primary provider
3. THE System SHALL support Ollama as a fallback provider
4. THE System SHALL support future OpenAI provider integration
5. WHEN the primary provider fails, THE System SHALL automatically fall back to the secondary provider according to environment-configured policy
6. THE System SHALL log provider selection and fallback events
7. THE System SHALL expose provider configuration through environment variables
8. THE System SHALL allow per-agent model selection (chat vs reasoner models)
9. THE System SHALL support adaptive execution depth to reduce unnecessary external model usage on trivial tasks

### Requirement 7: Enhanced Agent Intelligence

**User Story:** As a user, I want agents to use domain intelligence capabilities, so that I receive accurate and credible analysis.

#### Acceptance Criteria

1. THE Research_Agent SHALL gather context from prompts, APIs, and domain services
2. THE Research_Agent SHALL extract entities, tickers, and claims from user input
3. THE Research_Agent SHALL fetch external information where allowed
4. THE Research_Agent SHALL return structured facts, assumptions, open questions, and useful signals
5. THE Planner_Agent SHALL convert research into a practical response or action plan
6. THE Planner_Agent SHALL highlight dependencies, risks, and possible next steps
7. THE Verifier_Agent SHALL test credibility of information
8. THE Verifier_Agent SHALL detect rumors, scams, unsupported claims, and contradictions using source_checker, rumor_detector, and scam_detector
9. THE Verifier_Agent SHALL force uncertainty to be made visible
10. THE Synthesizer_Agent SHALL combine outputs into one final answer
11. THE Synthesizer_Agent SHALL state uncertainty honestly
12. THE Synthesizer_Agent SHALL recommend next actions
13. THE Synthesizer_Agent SHALL suggest simulation mode when scenario analysis is more appropriate
14. THE System SHALL preserve existing agent prompt files and update them with domain intelligence instructions
15. THE System SHALL maintain agent modularity and separation of concerns

### Requirement 9: External API Integration and Discovery

**User Story:** As a developer, I want a structured approach to external API integration, so that I can easily add new connectors and discover useful APIs.

#### Acceptance Criteria

1. THE System SHALL support external API integrations through a dedicated services layer
2. THE System SHALL include initial connector support for: market/news connectors from impact_ai, OpenRouter, Ollama, Tavily, Jina Reader, NewsAPI, Alpha Vantage
3. THE System SHALL use public-apis/public-apis as an API discovery source for future connectors
4. THE System SHALL implement an API discovery subsystem that classifies free APIs by category
5. THE API discovery subsystem SHALL score candidate APIs for usefulness
6. THE API discovery subsystem SHALL store metadata such as auth requirements, HTTPS support, and CORS configuration
7. THE API discovery subsystem SHALL support future sandbox testing and promotion into connectors
8. THE System SHALL treat public-apis as a discovery catalog, not as a runtime dependency
9. THE System SHALL use connection pooling for external API clients
10. THE System SHALL implement request timeouts for all external API calls

### Requirement 10: Case Memory System

**User Story:** As a user, I want all interactions stored, so that I can review past analyses and track system behavior.

#### Acceptance Criteria

1. THE System SHALL persist every case execution to local storage
2. THE System SHALL store case_id, user_input, routing decision, agent outputs, final answer, and timestamps
3. THE System SHALL support retrieving cases by case_id
4. THE System SHALL support listing all cases with optional limit parameter
5. THE System SHALL support deleting cases by case_id
6. THE System SHALL provide memory statistics including total cases and storage size
7. THE System SHALL use JSON format for case storage
8. WHEN a simulation is executed, THE System SHALL link simulation_id to the case record
9. THE System SHALL store cases in backend/app/data/memory directory
10. THE System SHALL store simulations in backend/app/data/simulations directory
11. THE System SHALL store logs in backend/app/data/logs directory
12. THE System SHALL create data directories automatically if they do not exist

### Requirement 8: Simulation Integration

**User Story:** As a user, I want to run simulations and explore what-if scenarios, so that I can predict potential impacts and test hypotheses.

#### Acceptance Criteria

1. THE System SHALL integrate MiroFish as a separate backend service, not merged directly into the MiroOrg codebase
2. THE System SHALL implement a mirofish_client service as an adapter
3. THE System SHALL make MiroFish API paths configurable through environment variables
4. THE System SHALL support MiroFish health check
5. THE System SHALL support simulation submission with title and prediction_goal
6. THE System SHALL support simulation status retrieval by simulation_id
7. THE System SHALL support report retrieval by simulation_id
8. THE System SHALL support post-simulation chat by simulation_id
9. THE System SHALL use MiroFish for graph building, entity relationship extraction, persona generation, simulation, report generation, and deep interaction
10. THE System SHALL store simulation metadata locally in simulations directory
11. WHEN MiroFish is disabled, THE System SHALL return appropriate error messages for simulation requests
12. THE System SHALL handle MiroFish connection failures gracefully with descriptive errors
13. THE frontend SHALL only consume MiroOrg endpoints for simulation, never direct MiroFish calls

### Requirement 11: API Endpoints

**User Story:** As a frontend developer, I want comprehensive REST endpoints, so that I can build a rich user interface.

#### Acceptance Criteria

1. THE System SHALL preserve GET /health endpoint for basic health checks
2. THE System SHALL preserve GET /health/deep endpoint for comprehensive health status
3. THE System SHALL preserve GET /config/status endpoint for configuration visibility
4. THE System SHALL preserve GET /agents endpoint for listing all agents
5. THE System SHALL preserve GET /agents/{agent_name} endpoint for agent details
6. THE System SHALL preserve POST /run endpoint for standard execution
7. THE System SHALL preserve POST /run/debug endpoint for detailed execution traces
8. THE System SHALL preserve POST /run/agent endpoint for single agent execution
9. THE System SHALL preserve GET /cases endpoint for listing cases
10. THE System SHALL preserve GET /cases/{case_id} endpoint for case details
11. THE System SHALL preserve DELETE /cases/{case_id} endpoint for case deletion
12. THE System SHALL preserve GET /memory/stats endpoint for memory statistics
13. THE System SHALL preserve GET /prompts endpoint for listing prompts
14. THE System SHALL preserve GET /prompts/{name} endpoint for prompt retrieval
15. THE System SHALL preserve PUT /prompts/{name} endpoint for prompt updates
16. THE System SHALL preserve GET /simulation/health endpoint for MiroFish health
17. THE System SHALL preserve POST /simulation/run endpoint for simulation submission
18. THE System SHALL preserve GET /simulation/{simulation_id} endpoint for simulation status
19. THE System SHALL preserve GET /simulation/{simulation_id}/report endpoint for simulation reports
20. THE System SHALL preserve POST /simulation/{simulation_id}/chat endpoint for simulation chat
21. THE frontend SHALL only consume MiroOrg endpoints, even for simulation operations

### Requirement 9: Error Handling and Logging

**User Story:** As a developer, I want robust error handling and logging, so that I can diagnose issues and monitor system behavior.

#### Acceptance Criteria

1. THE System SHALL use typed Pydantic schemas for all request and response models
2. THE System SHALL validate all incoming requests against schemas
3. THE System SHALL return structured error responses with appropriate HTTP status codes
4. THE System SHALL log all agent executions with case_id and timestamps
5. THE System SHALL log provider selection and fallback events
6. THE System SHALL log external API calls and failures
7. THE System SHALL log simulation requests and responses
8. WHEN an external service fails, THE System SHALL return descriptive error messages without exposing internal details
9. THE System SHALL write logs to backend/app/data/logs directory with rotation
10. THE System SHALL never expose raw provider exceptions to the frontend

### Requirement 12: Frontend Enhancement

**User Story:** As a user, I want a polished dashboard interface, so that I can interact with the system professionally.

#### Acceptance Criteria

1. THE System SHALL evolve the frontend from a demo page into a product dashboard
2. THE System SHALL provide a Main Dashboard page
3. THE System SHALL provide an Analyze tab for analysis tasks
4. THE System SHALL provide a Cases/History tab for reviewing past executions
5. THE System SHALL provide a Prompt Lab tab for prompt management
6. THE System SHALL provide a Simulation tab for scenario modeling
7. THE System SHALL provide an input task box
8. THE System SHALL provide a mode selector for Analyze vs Simulation
9. THE System SHALL provide a case output viewer
10. THE System SHALL display route/debug badges
11. THE System SHALL display agent output panels
12. THE System SHALL display market context panel
13. THE System SHALL display simulation status panel
14. THE System SHALL display confidence badges
15. THE System SHALL use a premium dark UI with card-based structure
16. THE System SHALL include subtle animations and transitions
17. THE System SHALL allow users to view case details including case_id and stored metadata
18. THE System MAY reuse impact_ai UI ideas and data panels, but SHALL consolidate into the miroorg-basic-v2 app shell

### Requirement 13: Configuration and Deployment

**User Story:** As a system administrator, I want clear configuration and setup instructions, so that I can deploy the system reliably.

#### Acceptance Criteria

1. THE System SHALL provide a .env.example file with all required environment variables
2. THE System SHALL document all environment variables in README.md
3. THE System SHALL include setup instructions for local development
4. THE System SHALL include instructions for running backend and frontend separately
5. THE System SHALL specify Python version requirements (3.10+)
6. THE System SHALL specify Node.js version requirements for frontend
7. THE System SHALL include a requirements.txt with all Python dependencies
8. THE System SHALL include a package.json with all Node.js dependencies
9. THE System SHALL document API endpoint usage with examples
10. THE System SHALL document the four-layer architecture in README.md
11. THE System SHALL document agent roles and responsibilities
12. THE System SHALL document simulation integration setup
13. THE System SHALL document domain pack integration approach
14. THE System SHALL keep the backend runnable locally at every phase

### Requirement 14: Data Persistence and Storage

**User Story:** As a user, I want my data stored locally, so that I can access historical analyses offline.

#### Acceptance Criteria

1. THE System SHALL store cases in backend/app/data/memory directory
2. THE System SHALL store simulations in backend/app/data/simulations directory
3. THE System SHALL store logs in backend/app/data/logs directory
4. THE System SHALL use JSON format for case and simulation storage
5. THE System SHALL create data directories automatically if they do not exist
6. THE System SHALL include data directories in .gitignore to prevent committing user data
7. THE System SHALL support exporting cases as JSON files
8. WHEN storage operations fail, THE System SHALL log errors and return appropriate HTTP status codes
9. EACH case SHALL store: case_id, input, route, agent outputs, final answer, timestamps, optional simulation_id
10. EACH simulation SHALL store: simulation_id, remote payload, local metadata, status, report snapshot

### Requirement 13: Security and Secrets Management

**User Story:** As a security-conscious developer, I want proper secrets management, so that API keys are never exposed.

#### Acceptance Criteria

1. THE System SHALL load all API keys from environment variables
2. THE System SHALL never commit .env files to version control
3. THE System SHALL include .env in .gitignore
4. THE System SHALL provide .env.example with placeholder values
5. THE System SHALL validate required API keys on startup
6. WHEN required API keys are missing, THE System SHALL log warnings and disable affected features
7. THE System SHALL never expose API keys in API responses
8. THE System SHALL never log API keys in plain text
9. THE System SHALL use HTTPS for all external API calls
10. THE System SHALL sanitize error messages to prevent information leakage

### Requirement 14: Testing and Quality Assurance

**User Story:** As a developer, I want the codebase to be testable, so that I can ensure reliability and catch regressions.

#### Acceptance Criteria

1. THE System SHALL maintain modular service layer for unit testing
2. THE System SHALL use dependency injection for external services
3. THE System SHALL provide mock implementations for external APIs in tests
4. THE System SHALL validate all Pydantic schemas with test cases
5. THE System SHALL test provider fallback behavior
6. THE System SHALL test agent routing logic
7. THE System SHALL test case storage and retrieval
8. THE System SHALL test simulation integration error handling
9. THE System SHALL maintain code coverage above 70% for critical paths
10. THE System SHALL run linting and type checking in CI/CD pipeline

### Requirement 15: Performance and Scalability

**User Story:** As a user, I want fast response times, so that I can analyze information efficiently.

#### Acceptance Criteria

1. WHEN processing simple queries, THE System SHALL respond within 5 seconds
2. WHEN processing complex queries, THE System SHALL respond within 30 seconds
3. THE System SHALL use connection pooling for external API clients
4. THE System SHALL implement request timeouts for all external API calls
5. THE System SHALL cache market quotes for 5 minutes to reduce API calls
6. THE System SHALL limit concurrent external API requests to prevent rate limiting
7. THE System SHALL use async/await patterns for I/O-bound operations
8. THE System SHALL implement pagination for case listing endpoints
9. WHEN memory usage exceeds 1GB, THE System SHALL log warnings
10. THE System SHALL support horizontal scaling by making state storage pluggable

### Requirement 16: Implementation Priorities

**User Story:** As a project manager, I want clear implementation priorities, so that the team can deliver value incrementally.

#### Acceptance Criteria

1. THE System SHALL implement in this order: backend consolidation, provider abstraction, impact_ai domain integration, simulation adapter, frontend enhancement, testing and cleanup
2. THE System SHALL keep the backend runnable locally at every phase
3. THE System SHALL NOT prioritize enterprise auth, Kubernetes, large-scale distributed infra, full cloud deployment, or advanced multi-user features in this phase
4. THE System SHALL focus on single-user local deployment with production-quality code structure
5. THE System SHALL use miroorg-basic-v2 as the base repo for all implementation work
6. THE System SHALL port valuable impact_ai modules into the service/domain layer
7. THE System SHALL integrate MiroFish through a clean adapter and router, never direct frontend calls
8. THE System SHALL add API discovery scaffolding using public-apis as a catalog source
9. THE System SHALL remove dead duplicates during consolidation

### Requirement 17: Autonomous Knowledge Evolution Layer

**User Story:** As a user, I want the system to improve itself over time by learning from internet knowledge, past cases, and successful patterns, so that it becomes smarter without requiring manual intervention or stressing my laptop.

#### Acceptance Criteria

1. THE System SHALL implement an Autonomous Knowledge Evolution Layer as Layer 5 in the architecture
2. THE System SHALL NOT train foundation models locally or store large raw datasets
3. THE System SHALL store only compressed summaries, extracted facts, source metadata, trust scores, and skill records
4. THE System SHALL respect strict storage limits: max 200MB for knowledge cache, 2-4KB per article summary
5. THE System SHALL auto-delete stale knowledge after configurable expiration period
6. THE System SHALL run learning tasks only when system is idle and laptop is not stressed
7. THE System SHALL stop learning tasks if battery is low or system resources are constrained

#### World Knowledge Ingestion

8. THE System SHALL continuously ingest high-signal information from Tavily, Jina Reader, NewsAPI, Alpha Vantage, and discovered APIs
9. THE System SHALL compress external information into structured summaries with: title, summary, entities, source_url, source_type, trust_score, freshness_score, domain_pack, timestamps
10. THE System SHALL NOT save raw webpage archives or full-page content
11. THE System SHALL extract and store only: summaries, entities, claims, source metadata, freshness indicators, trust scores
12. THE System SHALL respect API rate limits and avoid excessive external requests

#### Experience Learning

13. THE System SHALL learn from every case execution by tracking: route effectiveness, prompt performance, provider reliability, source usefulness, answer corrections, repeated patterns
14. THE System SHALL store case learning metadata without duplicating full case records
15. THE System SHALL identify patterns across multiple cases to inform future routing and agent decisions
16. THE System SHALL update trust scores for sources based on verification outcomes

#### Prompt Evolution

17. THE System SHALL version all agent prompts with metadata: version, last_tested, win_rate, status (active/experimental/archived)
18. THE System SHALL test improved prompt variants on sampled tasks
19. THE System SHALL compare prompt outcomes using quality metrics
20. THE System SHALL promote better-performing prompts to active status
21. THE System SHALL archive underperforming prompt versions
22. THE System SHALL NOT allow uncontrolled autonomous prompt changes without validation

#### Skill Distillation

23. WHEN the system solves similar problems repeatedly, THE System SHALL distill patterns into reusable skills
24. EACH skill SHALL contain: name, trigger_patterns, recommended_agents, preferred_sources, prompt_overrides
25. THE System SHALL store skills as structured records in backend/app/data/skills directory
26. THE System SHALL make distilled skills available to agents for future similar tasks
27. THE System SHALL support skill types including: financial_rumor_review, policy_reaction_analysis, earnings_impact_brief, simulation_prep_pack

#### Trust and Freshness Management

28. THE System SHALL maintain trust scores for all external sources (APIs, news outlets, websites)
29. THE System SHALL track freshness scores to identify stale information
30. THE System SHALL recommend source refresh when freshness degrades
31. THE System SHALL learn which sources are reliable vs noisy over time
32. THE System SHALL expire knowledge items based on domain-specific freshness rules

#### Storage and Resource Management

33. THE System SHALL store knowledge in backend/app/data/knowledge directory
34. THE System SHALL store skills in backend/app/data/skills directory
35. THE System SHALL store prompt versions in backend/app/data/prompt_versions directory
36. THE System SHALL store learning metadata in backend/app/data/learning directory
37. THE System SHALL compress old cases to save space
38. THE System SHALL enforce hard storage limits and auto-cleanup policies
39. THE System SHALL use external provider APIs for heavy reasoning, not local computation

#### Learning Scheduler

40. THE System SHALL implement a lightweight scheduler with safeguards: one background job at a time, small batch sizes, stop on errors, respect rate limits
41. THE System SHALL schedule learning tasks during idle periods
42. THE System SHALL NOT interfere with user-initiated operations
43. THE System SHALL provide manual trigger option for immediate learning runs

#### Integration with Existing Layers

44. THE System SHALL integrate learning insights with normal MiroOrg case executions
45. THE System SHALL integrate learning insights with domain pack intelligence
46. THE System SHALL learn from MiroFish simulation results and outcomes
47. THE System SHALL integrate with prompt management system
48. THE System SHALL integrate with provider abstraction layer

#### API Endpoints

49. THE System SHALL provide GET /learning/status endpoint for learning system status
50. THE System SHALL provide POST /learning/run-once endpoint for manual learning trigger
51. THE System SHALL provide GET /learning/insights endpoint for learning statistics
52. THE System SHALL provide GET /knowledge endpoint for listing knowledge items
53. THE System SHALL provide GET /knowledge/{item_id} endpoint for knowledge details
54. THE System SHALL provide GET /knowledge/search endpoint for knowledge search
55. THE System SHALL provide GET /skills endpoint for listing distilled skills
56. THE System SHALL provide GET /skills/{skill_name} endpoint for skill details
57. THE System SHALL provide POST /skills/distill endpoint for manual skill distillation
58. THE System SHALL provide GET /sources/trust endpoint for source trust scores
59. THE System SHALL provide GET /sources/freshness endpoint for source freshness scores
60. THE System SHALL provide GET /prompts/versions/{name} endpoint for prompt version history
61. THE System SHALL provide POST /prompts/optimize/{name} endpoint for prompt optimization
62. THE System SHALL provide POST /prompts/promote/{name}/{version} endpoint for promoting prompt versions
