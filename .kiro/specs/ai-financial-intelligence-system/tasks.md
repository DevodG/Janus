# Implementation Plan: AI Financial Intelligence System (MiroOrg v1.1)

## Overview

This implementation plan transforms MiroOrg into a general intelligence operating system that orchestrates multiple specialist agents, runs simulations, and supports pluggable domain packs. The system merges capabilities from miroorg-basic-v2 (base architecture), impact_ai (first domain pack), MiroFish (simulation lab), and public-apis (API discovery catalog) into a unified, production-ready platform.

The implementation follows 9 phases, each building on the previous while maintaining a runnable system. The focus is on single-user local deployment with production-quality code structure.

## Tasks

### Phase 1: Backend Consolidation and Provider Enhancement

- [x] 1. Strengthen core platform and provider abstraction
  - [x] 1.1 Add OpenAI provider support to model abstraction layer
    - Implement `_call_openai()` function in `backend/app/agents/_model.py`
    - Add OpenAI API key configuration in `backend/app/config.py`
    - Add OpenAI to provider fallback chain
    - _Requirements: 6.2, 6.4_
  
  - [x] 1.2 Enhance provider fallback logging and health checks
    - Add detailed logging for provider selection events in `backend/app/agents/_model.py`
    - Add logging for fallback attempts and failures
    - Implement provider health checks in `backend/app/services/health_service.py`
    - Add provider status to deep health endpoint
    - _Requirements: 6.5, 6.6, 9.4_
  
  - [x] 1.3 Add configuration validation on startup
    - Implement config validation in `backend/app/config.py`
    - Add warnings for missing optional API keys
    - Add errors for missing required configuration
    - Validate provider configuration completeness
    - _Requirements: 1.8, 6.7, 13.5, 13.6_
  
  - [x] 1.4 Update environment configuration files
    - Add OpenAI configuration to `backend/.env.example`
    - Add domain pack feature flags
    - Add simulation trigger keywords configuration
    - Document all environment variables
    - _Requirements: 1.8, 4.6, 13.1, 13.2_

- [x] 2. Checkpoint - Verify provider abstraction
  - Ensure all three providers (OpenRouter, Ollama, OpenAI) work correctly
  - Verify fallback behavior with proper logging
  - Verify health check reports provider status accurately
  - Ask the user if questions arise

### Phase 2: Domain Pack Architecture

- [x] 3. Create domain pack base infrastructure
  - [x] 3.1 Implement domain pack base architecture
    - Create `backend/app/domain_packs/__init__.py`
    - Create `backend/app/domain_packs/base.py` with DomainPack abstract base class
    - Define abstract methods: name, keywords, enhance_research, enhance_verification, get_capabilities
    - _Requirements: 2.3, 2.5, 2.7, 5.6_
  
  - [x] 3.2 Implement domain pack registry
    - Create `backend/app/domain_packs/registry.py` with DomainPackRegistry class
    - Implement register(), get_pack(), detect_domain(), list_packs(), get_capabilities()
    - Create global registry instance
    - _Requirements: 2.5, 5.6_
  
  - [x] 3.3 Create finance domain pack structure
    - Create `backend/app/domain_packs/finance/__init__.py`
    - Create `backend/app/domain_packs/finance/pack.py` with FinanceDomainPack class
    - Implement name, keywords properties for finance domain
    - _Requirements: 5.1, 5.2, 5.7_

- [x] 4. Port impact_ai modules to finance domain pack
  - [x] 4.1 Port market data and news modules
    - Create `backend/app/domain_packs/finance/market_data.py` from impact_ai alpha_vantage_client.py
    - Create `backend/app/domain_packs/finance/news.py` from impact_ai news_api.py
    - Refactor to match service layer pattern
    - _Requirements: 5.2, 5.5_
  
  - [x] 4.2 Port entity and ticker resolution modules
    - Create `backend/app/domain_packs/finance/entity_resolver.py`
    - Create `backend/app/domain_packs/finance/ticker_resolver.py`
    - Implement entity extraction and normalization
    - _Requirements: 5.2, 7.2_
  
  - [x] 4.3 Port credibility and detection modules
    - Create `backend/app/domain_packs/finance/source_checker.py`
    - Create `backend/app/domain_packs/finance/rumor_detector.py`
    - Create `backend/app/domain_packs/finance/scam_detector.py`
    - Implement credibility scoring and detection logic
    - _Requirements: 5.2, 7.8_
  
  - [x] 4.4 Port analysis and prediction modules
    - Create `backend/app/domain_packs/finance/stance_detector.py`
    - Create `backend/app/domain_packs/finance/event_analyzer.py`
    - Create `backend/app/domain_packs/finance/prediction.py`
    - Implement sentiment analysis and prediction logic
    - _Requirements: 5.2_

- [x] 5. Consolidate external API clients
  - [x] 5.1 Merge Alpha Vantage and NewsAPI clients
    - Consolidate Alpha Vantage logic into `backend/app/services/external_sources.py`
    - Consolidate NewsAPI logic into `backend/app/services/external_sources.py`
    - Remove duplicate implementations
    - Add connection pooling and timeouts
    - _Requirements: 5.4, 9.9, 9.10, 15.3, 15.4_
  
  - [x] 5.2 Register finance pack and update configuration
    - Register FinanceDomainPack in global registry
    - Add finance pack configuration to `backend/app/config.py`
    - Add feature flags for domain pack enablement
    - _Requirements: 5.3, 5.6_

- [x] 6. Checkpoint - Verify domain pack infrastructure
  - Ensure finance pack is registered successfully
  - Verify domain detection works for finance keywords
  - Verify external API clients are consolidated
  - Ask the user if questions arise

### Phase 3: Agent Enhancement with Domain Intelligence

- [ ] 7. Enhance Switchboard with domain detection
  - [ ] 7.1 Add domain pack dimension to routing
    - Modify `backend/app/agents/switchboard.py` to add domain_pack to routing decision
    - Implement domain detection using domain registry
    - Update RouteDecision schema in `backend/app/schemas.py`
    - _Requirements: 4.1, 5.6_
  
  - [ ] 7.2 Implement complexity-based routing logic
    - Ensure simple queries (≤5 words) route to solo mode
    - Ensure medium queries (≤25 words) route to standard mode
    - Ensure complex queries (>25 words) route to deep mode
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [ ] 7.3 Implement simulation keyword detection
    - Add simulation trigger keyword detection
    - Load keywords from environment configuration
    - Set task_family="simulation" when keywords detected
    - _Requirements: 4.5, 4.6, 4.7_

- [ ] 8. Enhance Research Agent with domain capabilities
  - [ ] 8.1 Integrate domain pack research enhancement
    - Modify `backend/app/agents/research.py` to detect domain
    - Call domain pack enhance_research() when domain detected
    - Add structured entity extraction output
    - _Requirements: 5.3, 7.1, 7.2, 7.3, 7.4_
  
  - [ ] 8.2 Update research agent prompt
    - Update `backend/app/prompts/research.txt` with domain intelligence instructions
    - Add instructions for entity and ticker extraction
    - Add instructions for structured output
    - _Requirements: 7.14_

- [ ] 9. Enhance Verifier Agent with domain capabilities
  - [ ] 9.1 Integrate domain pack verification enhancement
    - Modify `backend/app/agents/verifier.py` to detect domain
    - Call domain pack enhance_verification() when domain detected
    - Add structured credibility scoring output
    - _Requirements: 5.3, 7.7, 7.8, 7.9_
  
  - [ ] 9.2 Update verifier agent prompt
    - Update `backend/app/prompts/verifier.txt` with domain intelligence instructions
    - Add instructions for rumor and scam detection
    - Add instructions for uncertainty surfacing
    - _Requirements: 7.14_

- [ ] 10. Enhance Planner and Synthesizer Agents
  - [ ] 10.1 Add simulation mode suggestion to Planner
    - Modify `backend/app/agents/planner.py` to detect simulation opportunities
    - Add simulation_suggested field to output
    - Update `backend/app/prompts/planner.txt` with simulation guidance
    - _Requirements: 7.6, 7.14_
  
  - [ ] 10.2 Add uncertainty quantification to Synthesizer
    - Modify `backend/app/agents/synthesizer.py` to quantify uncertainty
    - Add simulation recommendation logic
    - Update `backend/app/prompts/synthesizer.txt` with uncertainty instructions
    - _Requirements: 7.11, 7.12, 7.13, 7.14_

- [ ] 11. Update graph execution with domain context
  - [ ] 11.1 Pass domain pack context through pipeline
    - Modify `backend/app/graph.py` to detect domain early
    - Pass domain context to all agents
    - Ensure domain-enhanced execution flows correctly
    - _Requirements: 2.5, 5.3, 7.15_

- [ ] 12. Checkpoint - Verify agent enhancements
  - Ensure Switchboard detects finance domain correctly
  - Verify Research agent extracts entities and tickers
  - Verify Verifier agent scores credibility
  - Verify agents suggest simulation mode appropriately
  - Ask the user if questions arise

### Phase 4: Simulation Integration Enhancement

- [ ] 13. Enhance simulation workflow and case linking
  - [ ] 13.1 Add case linking to simulation router
    - Modify `backend/app/routers/simulation.py` to link case_id
    - Improve error messages for MiroFish failures
    - Add better status reporting
    - _Requirements: 8.1, 8.11, 8.12_
  
  - [ ] 13.2 Enhance simulation store with search and filtering
    - Modify `backend/app/services/simulation_store.py`
    - Add simulation search by title or prediction_goal
    - Add simulation filtering by status
    - _Requirements: 8.10_
  
  - [ ] 13.3 Update case storage for simulation linking
    - Modify `backend/app/services/case_store.py` to add simulation_id field
    - Add case-to-simulation lookup functionality
    - Update CaseRecord schema in `backend/app/schemas.py`
    - _Requirements: 10.8, 14.9_
  
  - [ ] 13.4 Add simulation workflow to graph execution
    - Modify `backend/app/graph.py` to add simulation handoff logic
    - Add simulation result synthesis
    - Ensure simulation results flow into final answer
    - _Requirements: 3.4, 8.13_

- [ ] 14. Checkpoint - Verify simulation integration
  - Ensure simulation requests create linked cases
  - Verify cases with simulations show simulation_id
  - Verify simulation results are synthesized correctly
  - Ask the user if questions arise

### Phase 5: API Discovery Subsystem

- [ ] 15. Create API discovery infrastructure
  - [ ] 15.1 Create API discovery structure
    - Create `backend/app/services/api_discovery/__init__.py`
    - Create `backend/app/services/api_discovery/catalog_loader.py`
    - Create `backend/app/services/api_discovery/classifier.py`
    - Create `backend/app/services/api_discovery/scorer.py`
    - Create `backend/app/services/api_discovery/metadata_store.py`
    - _Requirements: 9.3, 9.4_
  
  - [ ] 15.2 Implement catalog loader
    - Implement load_public_apis_catalog() to fetch from GitHub or local cache
    - Parse API entries with name, description, auth, HTTPS, CORS, category, link
    - _Requirements: 9.3, 9.6_
  
  - [ ] 15.3 Implement API classifier and scorer
    - Implement classify_api() to categorize APIs by domain
    - Implement score_api_usefulness() to prioritize APIs for integration
    - Consider auth simplicity, HTTPS, CORS, category relevance
    - _Requirements: 9.5, 9.6_
  
  - [ ]* 15.4 Add optional discovery endpoints
    - Add `GET /api-discovery/categories` endpoint
    - Add `GET /api-discovery/search?category=X` endpoint
    - Add `GET /api-discovery/top-scored` endpoint
    - _Requirements: 9.4_

- [ ] 16. Checkpoint - Verify API discovery
  - Ensure catalog loads successfully
  - Verify APIs are classified correctly
  - Verify scoring produces reasonable priorities
  - Ask the user if questions arise

### Phase 6: Frontend Enhancement

- [ ] 17. Create layout and navigation infrastructure
  - [ ] 17.1 Create layout components
    - Create `frontend/src/components/layout/Header.tsx` with branding and navigation
    - Create `frontend/src/components/layout/Navigation.tsx` with tab navigation
    - Modify `frontend/src/app/layout.tsx` to use new layout components
    - _Requirements: 12.1, 12.2_
  
  - [ ] 17.2 Create common UI components
    - Create `frontend/src/components/common/Badge.tsx` for status indicators
    - Create `frontend/src/components/common/Card.tsx` for content containers
    - Create `frontend/src/components/common/LoadingSpinner.tsx` for loading states
    - Create `frontend/src/components/common/ErrorMessage.tsx` for error display
    - _Requirements: 12.10, 12.11, 12.15_
  
  - [ ] 17.3 Create API client and type definitions
    - Create `frontend/src/lib/api.ts` with MiroOrgClient class
    - Implement methods for all backend endpoints
    - Create `frontend/src/lib/types.ts` with TypeScript interfaces
    - _Requirements: 11.21_

- [ ] 18. Create Main Dashboard page
  - [ ] 18.1 Implement dashboard with system overview
    - Modify `frontend/src/app/page.tsx` to show quick stats
    - Display recent cases summary
    - Display system health status
    - Add navigation to main features
    - _Requirements: 12.2_

- [ ] 19. Create Analyze page and components
  - [ ] 19.1 Create Analyze page structure
    - Create `frontend/src/app/analyze/page.tsx` with analysis interface
    - Create `frontend/src/components/analyze/TaskInput.tsx` for user input
    - Create `frontend/src/components/analyze/ModeSelector.tsx` for mode selection
    - _Requirements: 12.3, 12.7, 12.8_
  
  - [ ] 19.2 Create result display components
    - Create `frontend/src/components/analyze/ResultViewer.tsx` for final answers
    - Create `frontend/src/components/analyze/AgentOutputPanel.tsx` for agent outputs
    - Display route/debug badges and confidence indicators
    - _Requirements: 12.9, 12.10, 12.11, 12.14_

- [ ] 20. Create Cases page and components
  - [ ] 20.1 Create Cases history interface
    - Create `frontend/src/app/cases/page.tsx` with case list
    - Create `frontend/src/components/cases/CaseList.tsx` for listing cases
    - Create `frontend/src/components/cases/CaseCard.tsx` for case preview
    - _Requirements: 12.4, 12.17_
  
  - [ ] 20.2 Create Case detail view
    - Create `frontend/src/app/cases/[id]/page.tsx` for case details
    - Create `frontend/src/components/cases/CaseDetail.tsx` for full case display
    - Display case_id, routing decision, agent outputs, timestamps
    - _Requirements: 12.17_

- [ ] 21. Create Simulation page and components
  - [ ] 21.1 Create Simulation submission interface
    - Create `frontend/src/app/simulation/page.tsx` with simulation form
    - Create `frontend/src/components/simulation/SimulationForm.tsx` for input
    - Create `frontend/src/components/simulation/SimulationStatus.tsx` for status display
    - _Requirements: 12.6, 12.13_
  
  - [ ] 21.2 Create Simulation detail and chat interface
    - Create `frontend/src/app/simulation/[id]/page.tsx` for simulation details
    - Create `frontend/src/components/simulation/SimulationReport.tsx` for report display
    - Create `frontend/src/components/simulation/SimulationChat.tsx` for post-simulation chat
    - _Requirements: 12.13_

- [ ] 22. Create Prompt Lab and Config pages
  - [ ] 22.1 Create Prompt Lab interface
    - Create `frontend/src/app/prompts/page.tsx` with prompt management
    - Create `frontend/src/components/prompts/PromptList.tsx` for listing prompts
    - Create `frontend/src/components/prompts/PromptEditor.tsx` for editing
    - _Requirements: 12.5_
  
  - [ ] 22.2 Create Config page
    - Create `frontend/src/app/config/page.tsx` with system configuration view
    - Display provider status, feature flags, health checks
    - _Requirements: 12.1_

- [ ] 23. Implement dark theme and styling
  - [ ] 23.1 Update global styles with dark theme
    - Modify `frontend/src/app/globals.css` with dark color palette
    - Implement card-based structure with subtle borders
    - Add animations and transitions
    - Use Inter font family
    - _Requirements: 12.15, 12.16_

- [ ] 24. Checkpoint - Verify frontend functionality
  - Ensure all pages are accessible via navigation
  - Verify Analyze workflow works end-to-end
  - Verify Case history displays correctly
  - Verify Simulation workflow works end-to-end
  - Verify Prompt lab allows editing
  - Verify Config page shows system status
  - Ask the user if questions arise

### Phase 7: Testing and Documentation

- [ ] 25. Write unit tests for core functionality
  - [ ]* 25.1 Write provider abstraction tests
    - Test OpenRouter, Ollama, OpenAI provider calls
    - Test provider fallback behavior
    - Test provider error handling
    - _Requirements: 6.5, 6.6_
  
  - [ ]* 25.2 Write domain pack tests
    - Test domain pack registration
    - Test domain detection
    - Test finance pack capabilities
    - Test entity and ticker extraction
    - _Requirements: 5.6, 7.2_
  
  - [ ]* 25.3 Write agent routing tests
    - Test Switchboard classification logic
    - Test complexity-to-execution-mode mapping
    - Test simulation keyword detection
    - Test domain detection
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 25.4 Write storage tests
    - Test case save and retrieve
    - Test simulation save and retrieve
    - Test directory auto-creation
    - Test memory statistics
    - _Requirements: 10.1, 10.3, 10.12_
  
  - [ ]* 25.5 Write simulation integration tests
    - Test MiroFish client adapter
    - Test simulation workflow
    - Test case-simulation linking
    - Test error handling for disabled MiroFish
    - _Requirements: 8.1, 8.11, 8.12_

- [ ] 26. Write property-based tests
  - [ ]* 26.1 Write Property 1: Configuration Environment Isolation
    - **Property 1: Configuration Environment Isolation**
    - **Validates: Requirements 1.8, 6.7**
    - Test that all configuration values come from environment variables
    - Generate random config keys and verify no hardcoded values
  
  - [ ]* 26.2 Write Property 2: Switchboard Four-Dimensional Classification
    - **Property 2: Switchboard Four-Dimensional Classification**
    - **Validates: Requirements 4.1**
    - Test that routing decisions contain all four dimensions
    - Generate random user inputs and verify structure
  
  - [ ]* 26.3 Write Property 3: Complexity-to-Execution-Mode Mapping
    - **Property 3: Complexity-to-Execution-Mode Mapping**
    - **Validates: Requirements 4.2, 4.3, 4.4**
    - Test that complexity maps correctly to execution mode
    - Generate inputs of varying lengths and verify mapping
  
  - [ ]* 26.4 Write Property 4: Simulation Keyword Triggering
    - **Property 4: Simulation Keyword Triggering**
    - **Validates: Requirements 4.5, 4.6**
    - Test that simulation keywords trigger correct classification
    - Generate inputs with/without keywords and verify task_family
  
  - [ ]* 26.5 Write Property 5: Provider Fallback Behavior
    - **Property 5: Provider Fallback Behavior**
    - **Validates: Requirements 6.5**
    - Test that provider fallback works correctly
    - Mock primary provider failures and verify fallback
  
  - [ ]* 26.6 Write Property 6: Case Persistence Round Trip
    - **Property 6: Case Persistence Round Trip**
    - **Validates: Requirements 10.1, 10.3**
    - Test that saved cases can be retrieved correctly
    - Generate random case data and verify round trip
  
  - [ ]* 26.7 Write Property 7: Case Record Structure Completeness
    - **Property 7: Case Record Structure Completeness**
    - **Validates: Requirements 10.2, 10.7, 10.8**
    - Test that case records contain all required fields
    - Generate random cases and verify structure
  
  - [ ]* 26.8 Write Property 8: Data Directory Organization
    - **Property 8: Data Directory Organization**
    - **Validates: Requirements 10.9, 10.10, 10.11**
    - Test that data is stored in correct directories
    - Generate random data and verify file locations
  
  - [ ]* 26.9 Write Property 9: Directory Auto-Creation
    - **Property 9: Directory Auto-Creation**
    - **Validates: Requirements 10.12**
    - Test that missing directories are created automatically
    - Remove directories and verify auto-creation
  
  - [ ]* 26.10 Write Property 10: MiroFish Adapter Isolation
    - **Property 10: MiroFish Adapter Isolation**
    - **Validates: Requirements 1.3, 3.4**
    - Test that all MiroFish calls go through adapter
    - Scan codebase for direct MiroFish URLs
  
  - [ ]* 26.11 Write Property 11: Comprehensive Logging
    - **Property 11: Comprehensive Logging**
    - **Validates: Requirements 6.6, 9.4, 9.6, 9.7**
    - Test that all operations create log entries
    - Generate random operations and verify logging
  
  - [ ]* 26.12 Write Property 12: Schema Validation
    - **Property 12: Schema Validation**
    - **Validates: Requirements 9.1, 9.2**
    - Test that invalid requests return 422 errors
    - Generate invalid request bodies and verify errors
  
  - [ ]* 26.13 Write Property 13: External API Client Patterns
    - **Property 13: External API Client Patterns**
    - **Validates: Requirements 9.1, 9.9, 9.10**
    - Test that external API clients use consistent patterns
    - Verify connection pooling, timeouts, error handling
  
  - [ ]* 26.14 Write Property 14: Error Response Sanitization
    - **Property 14: Error Response Sanitization**
    - **Validates: Requirements 9.3, 9.8, 9.10**
    - Test that error responses don't leak internals
    - Generate various errors and verify sanitization
  
  - [ ]* 26.15 Write Property 15: Domain Pack Extensibility
    - **Property 15: Domain Pack Extensibility**
    - **Validates: Requirements 2.5, 2.7**
    - Test that new domain packs don't require agent changes
    - Create mock domain pack and verify integration

- [ ] 27. Write integration tests
  - [ ]* 27.1 Write end-to-end case execution test
    - Test complete workflow from user input to final answer
    - Verify all agents execute correctly
    - Verify case is saved with correct structure
    - _Requirements: 3.2_
  
  - [ ]* 27.2 Write simulation workflow test
    - Test complete simulation workflow
    - Verify submission, status, report, chat
    - Verify case-simulation linking
    - _Requirements: 3.3, 8.1_
  
  - [ ]* 27.3 Write provider fallback integration test
    - Test fallback in real execution context
    - Verify system continues working with fallback provider
    - _Requirements: 6.5_
  
  - [ ]* 27.4 Write domain pack enhancement test
    - Test domain-enhanced research and verification
    - Verify finance pack capabilities are used
    - _Requirements: 5.3, 7.1, 7.7_

- [ ] 28. Create comprehensive documentation
  - [ ] 28.1 Update main README
    - Update `README.md` with architecture overview
    - Document four-layer architecture
    - Document agent roles and responsibilities
    - Add setup instructions for local development
    - Add environment variable reference
    - _Requirements: 13.2, 13.3, 13.4, 13.10, 13.11, 13.12_
  
  - [ ] 28.2 Create architecture documentation
    - Create `ARCHITECTURE.md` with detailed architecture description
    - Document component interactions
    - Document data flow
    - _Requirements: 13.10_
  
  - [ ] 28.3 Create domain pack documentation
    - Create `DOMAIN_PACKS.md` with domain pack integration guide
    - Document how to create new domain packs
    - Document finance pack capabilities
    - _Requirements: 13.13_
  
  - [ ] 28.4 Create testing documentation
    - Create `TESTING.md` with testing strategy and guidelines
    - Document unit test patterns
    - Document property-based test patterns
    - Document integration test patterns
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [ ] 28.5 Create deployment documentation
    - Create `DEPLOYMENT.md` with deployment instructions
    - Document environment setup
    - Document dependency installation
    - Document running backend and frontend
    - _Requirements: 13.4, 13.5, 13.6, 13.7, 13.8_

- [ ] 29. Checkpoint - Verify testing and documentation
  - Ensure all tests pass
  - Verify coverage meets goals (70%+ overall)
  - Verify documentation is complete and accurate
  - Verify setup instructions work for new developers
  - Ask the user if questions arise

### Phase 8: Cleanup and Optimization

- [ ] 30. Remove dead code and optimize performance
  - [ ] 30.1 Clean up codebase
    - Remove unused imports across all files
    - Remove commented code
    - Remove duplicate implementations
    - _Requirements: 1.5_
  
  - [ ] 30.2 Optimize external API performance
    - Add caching for market quotes with 5 minute TTL
    - Verify connection pooling is implemented
    - Verify request timeouts are configured
    - Add rate limiting for external APIs
    - _Requirements: 15.3, 15.4, 15.5, 15.6_
  
  - [ ] 30.3 Polish error messages and logging
    - Review all error messages for clarity and consistency
    - Review log levels for appropriateness
    - Add missing log entries for key operations
    - _Requirements: 9.3, 9.8_
  
  - [ ] 30.4 Security review
    - Verify no API keys in source code
    - Verify error messages don't leak internals
    - Verify input validation is comprehensive
    - Verify all external API calls use HTTPS
    - _Requirements: 13.1, 13.2, 13.3, 13.7, 13.8, 13.9_
  
  - [ ]* 30.5 Performance testing
    - Test response times for simple queries (target: <5s)
    - Test response times for complex queries (target: <30s)
    - Identify and address bottlenecks
    - _Requirements: 15.1, 15.2_

- [ ] 31. Final checkpoint - System verification
  - Ensure no dead code remains
  - Verify performance meets requirements
  - Verify error messages are clear and consistent
  - Verify logging is comprehensive
  - Verify security review passes
  - Ask the user if questions arise

### Phase 9: Autonomous Knowledge Evolution Layer

- [ ] 32. Create learning subsystem infrastructure
  - [ ] 32.1 Create learning service structure
    - Create `backend/app/services/learning/__init__.py`
    - Create `backend/app/services/learning/knowledge_ingestor.py`
    - Create `backend/app/services/learning/knowledge_store.py`
    - Create `backend/app/services/learning/learning_engine.py`
    - _Requirements: 17.1, 17.2, 17.3_
  
  - [ ] 32.2 Create additional learning services
    - Create `backend/app/services/learning/prompt_optimizer.py`
    - Create `backend/app/services/learning/skill_distiller.py`
    - Create `backend/app/services/learning/trust_manager.py`
    - Create `backend/app/services/learning/freshness_manager.py`
    - Create `backend/app/services/learning/scheduler.py`
    - _Requirements: 17.1, 17.17, 17.23, 17.28, 17.40_
  
  - [ ] 32.3 Create data directories
    - Create `backend/app/data/knowledge/` directory
    - Create `backend/app/data/skills/` directory
    - Create `backend/app/data/prompt_versions/` directory
    - Create `backend/app/data/learning/` directory
    - _Requirements: 17.33, 17.34, 17.35, 17.36_

- [ ] 33. Implement knowledge ingestion and storage
  - [ ] 33.1 Implement knowledge ingestion
    - Implement ingest_from_search() using Tavily API
    - Implement ingest_from_url() using Jina Reader
    - Implement ingest_from_news() using NewsAPI
    - Implement compress_content() for summarization (2-4KB limit)
    - _Requirements: 17.8, 17.9, 17.10, 17.11_
  
  - [ ] 33.2 Implement knowledge store
    - Implement save_knowledge() with JSON storage
    - Implement get_knowledge() and search_knowledge()
    - Implement delete_expired_knowledge() with auto-cleanup
    - Implement storage limit enforcement (200MB max)
    - Implement LRU eviction when limit reached
    - _Requirements: 17.4, 17.5, 17.33, 17.38_
  
  - [ ] 33.3 Add knowledge schemas
    - Add KnowledgeItem schema to `backend/app/schemas.py`
    - Add validation for summary length (2-4KB)
    - Add trust_score and freshness_score fields
    - _Requirements: 17.9_

- [ ] 34. Implement experience learning
  - [ ] 34.1 Implement case learning
    - Implement learn_from_case() to extract metadata
    - Implement detect_patterns() for repeated patterns
    - Implement get_route_effectiveness() for routing insights
    - Implement get_prompt_performance() for prompt insights
    - _Requirements: 17.13, 17.14, 17.15, 17.16_
  
  - [ ] 34.2 Add case learning schemas
    - Add CaseLearning schema to `backend/app/schemas.py`
    - Add fields for route_effectiveness, prompt_performance, provider_reliability
    - _Requirements: 17.13_
  
  - [ ] 34.3 Hook learning into case save flow
    - Modify `backend/app/services/case_store.py` to call learn_from_case()
    - Store case learning metadata separately
    - _Requirements: 17.44_

- [ ] 35. Implement prompt evolution
  - [ ] 35.1 Implement prompt versioning
    - Implement create_prompt_variant() using provider API
    - Implement test_prompt_variant() with quality metrics
    - Implement compare_prompts() for A/B testing
    - Implement promote_prompt() with validation
    - Implement archive_prompt() for old versions
    - _Requirements: 17.17, 17.18, 17.19, 17.20, 17.21, 17.22_
  
  - [ ] 35.2 Add prompt version schemas
    - Add PromptVersion schema to `backend/app/schemas.py`
    - Add fields for version, status, win_rate, test_count
    - _Requirements: 17.17_
  
  - [ ] 35.3 Integrate with prompt management
    - Hook prompt versions into prompt loading
    - Store prompt history in prompt_versions directory
    - _Requirements: 17.47_

- [ ] 36. Implement skill distillation
  - [ ] 36.1 Implement skill detection and creation
    - Implement detect_skill_candidates() from patterns
    - Implement distill_skill() to create skill records
    - Implement test_skill() for validation
    - Implement apply_skill() for skill usage
    - _Requirements: 17.23, 17.24, 17.25, 17.26, 17.27_
  
  - [ ] 36.2 Add skill schemas
    - Add Skill schema to `backend/app/schemas.py`
    - Add fields for trigger_patterns, recommended_agents, preferred_sources
    - _Requirements: 17.24_
  
  - [ ] 36.3 Integrate skills with agents
    - Hook skill application into agent execution
    - Store skills in skills directory
    - _Requirements: 17.45_

- [ ] 37. Implement trust and freshness management
  - [ ] 37.1 Implement trust management
    - Implement get_trust_score() and update_trust()
    - Implement list_trusted_sources() and list_untrusted_sources()
    - Track verification outcomes
    - _Requirements: 17.28, 17.29, 17.30, 17.31, 17.32_
  
  - [ ] 37.2 Implement freshness management
    - Implement calculate_freshness() with domain-specific rules
    - Implement update_freshness() and get_stale_items()
    - Implement recommend_refresh() for stale items
    - _Requirements: 17.28, 17.29, 17.30, 17.31_
  
  - [ ] 37.3 Add trust and freshness schemas
    - Add SourceTrust schema to `backend/app/schemas.py`
    - Add FreshnessScore schema to `backend/app/schemas.py`
    - _Requirements: 17.28_
  
  - [ ] 37.4 Integrate with source selection
    - Hook trust scores into research agent source selection
    - Hook freshness scores into knowledge retrieval
    - _Requirements: 17.46_

- [ ] 38. Implement learning scheduler
  - [ ] 38.1 Implement scheduler with safeguards
    - Implement schedule_task() with interval configuration
    - Implement is_system_idle() to check CPU usage
    - Implement is_battery_ok() to check battery level
    - Implement run_once() for manual triggers
    - _Requirements: 17.40, 17.41, 17.42, 17.43_
  
  - [ ] 38.2 Add scheduled tasks
    - Schedule knowledge ingestion (every 6 hours)
    - Schedule expired knowledge cleanup (daily)
    - Schedule pattern detection (daily)
    - Schedule skill distillation (weekly)
    - Schedule prompt optimization (weekly)
    - _Requirements: 17.6, 17.7, 17.40_
  
  - [ ] 38.3 Add scheduler configuration
    - Add LEARNING_ENABLED flag to config
    - Add KNOWLEDGE_MAX_SIZE_MB (default 200)
    - Add LEARNING_SCHEDULE_INTERVAL
    - Add LEARNING_BATCH_SIZE
    - Add domain-specific expiration rules
    - _Requirements: 17.4, 17.5, 17.6, 17.7, 17.12_

- [ ] 39. Add learning API endpoints
  - [ ] 39.1 Add learning status endpoints
    - Add GET /learning/status endpoint
    - Add POST /learning/run-once endpoint
    - Add GET /learning/insights endpoint
    - _Requirements: 17.49, 17.50, 17.51_
  
  - [ ] 39.2 Add knowledge endpoints
    - Add GET /knowledge endpoint for listing
    - Add GET /knowledge/{item_id} endpoint for details
    - Add GET /knowledge/search endpoint with query parameter
    - _Requirements: 17.52, 17.53, 17.54_
  
  - [ ] 39.3 Add skill endpoints
    - Add GET /skills endpoint for listing
    - Add GET /skills/{skill_name} endpoint for details
    - Add POST /skills/distill endpoint for manual distillation
    - _Requirements: 17.55, 17.56, 17.57_
  
  - [ ] 39.4 Add trust and freshness endpoints
    - Add GET /sources/trust endpoint
    - Add GET /sources/freshness endpoint
    - _Requirements: 17.58, 17.59_
  
  - [ ] 39.5 Add prompt evolution endpoints
    - Add GET /prompts/versions/{name} endpoint
    - Add POST /prompts/optimize/{name} endpoint
    - Add POST /prompts/promote/{name}/{version} endpoint
    - _Requirements: 17.60, 17.61, 17.62_

- [ ] 40. Integrate learning layer with existing system
  - [ ] 40.1 Integrate with case execution
    - Hook learn_from_case() into case save flow
    - Store case learning metadata
    - _Requirements: 17.44_
  
  - [ ] 40.2 Integrate with research agent
    - Hook knowledge search into research agent
    - Use trust scores for source selection
    - _Requirements: 17.45, 17.46_
  
  - [ ] 40.3 Integrate with simulation
    - Learn from simulation outcomes
    - Store simulation insights
    - _Requirements: 17.46_
  
  - [ ] 40.4 Integrate with prompt management
    - Hook prompt versions into prompt loading
    - Track prompt performance
    - _Requirements: 17.47_

- [ ] 41. Test and verify learning layer
  - [ ]* 41.1 Test knowledge ingestion
    - Test ingest_from_search() with Tavily
    - Test ingest_from_url() with Jina Reader
    - Test compress_content() produces 2-4KB summaries
    - Test storage limit enforcement (200MB)
    - _Requirements: 17.4, 17.8, 17.9, 17.10_
  
  - [ ]* 41.2 Test experience learning
    - Test learn_from_case() extracts metadata
    - Test detect_patterns() finds repeated patterns
    - Test trust score updates
    - _Requirements: 17.13, 17.14, 17.15, 17.16_
  
  - [ ]* 41.3 Test prompt evolution
    - Test create_prompt_variant() generates improvements
    - Test test_prompt_variant() measures quality
    - Test promote_prompt() validates before promotion
    - _Requirements: 17.17, 17.18, 17.19, 17.20_
  
  - [ ]* 41.4 Test skill distillation
    - Test detect_skill_candidates() finds patterns
    - Test distill_skill() creates valid skills
    - Test apply_skill() improves execution
    - _Requirements: 17.23, 17.24, 17.25, 17.26_
  
  - [ ]* 41.5 Test scheduler safeguards
    - Test is_system_idle() respects CPU limits
    - Test is_battery_ok() respects battery level
    - Test scheduler stops on errors
    - Test scheduler respects rate limits
    - _Requirements: 17.6, 17.7, 17.40, 17.41, 17.42_

- [ ] 42. Final checkpoint - Learning layer verification
  - Ensure learning subsystem runs without stressing laptop
  - Verify knowledge cache stays under 200MB
  - Verify scheduler respects battery and CPU constraints
  - Verify trust scores improve source selection
  - Verify prompt evolution produces better prompts
  - Verify skills are distilled from repeated patterns
  - Verify learning endpoints return useful insights
  - Verify system improves over time
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and user feedback
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- The system remains runnable after each phase
- Focus is on single-user local deployment with production-quality code structure
- No enterprise features (auth, Kubernetes, cloud deployment) in this phase
