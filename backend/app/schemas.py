from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Routing decision from Switchboard agent — v2."""
    domain: str = Field(default="general", description="Domain: 'finance', 'general', 'research', 'simulation', 'mixed'")
    complexity: str = Field(default="medium", description="Complexity: 'low', 'medium', 'high', 'very_high'")
    intent: str = Field(default="", description="Short plain-English summary of user intent")
    sub_tasks: List[str] = Field(default_factory=list, description="Decomposed sub-tasks")
    requires_simulation: bool = Field(default=False)
    requires_finance_data: bool = Field(default=False)
    requires_news: bool = Field(default=False)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class RunResponse(BaseModel):
    """Response from the /run endpoint — v2."""
    case_id: str
    user_input: str
    route: Dict[str, Any]
    research: Dict[str, Any] = Field(default_factory=dict)
    planner: Dict[str, Any] = Field(default_factory=dict)
    verifier: Dict[str, Any] = Field(default_factory=dict)
    simulation: Optional[Dict[str, Any]] = None
    finance: Optional[Dict[str, Any]] = None
    final: Dict[str, Any] = Field(default_factory=dict)
    final_answer: str = ""


class UserTask(BaseModel):
    user_input: str


class AgentRunRequest(BaseModel):
    agent: str
    user_input: str
    research_output: Optional[str] = None
    planner_output: Optional[str] = None
    verifier_output: Optional[str] = None


class AgentOutput(BaseModel):
    agent: str
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class CaseMemory(BaseModel):
    case_id: str
    user_input: str
    outputs: List[Dict[str, Any]]
    final_answer: str


class CaseSummary(BaseModel):
    case_id: str
    user_input: str
    saved_at: Optional[str] = None
    final_answer_preview: str


class PromptUpdateRequest(BaseModel):
    content: str


class PromptResponse(BaseModel):
    name: str
    content: str


class MemoryStatsResponse(BaseModel):
    total_cases: int
    latest_case_id: Optional[str] = None
    memory_dir: str
    disk_bytes: int


class ConfigStatusResponse(BaseModel):
    app_version: str
    primary_provider: str
    fallback_provider: str
    openrouter_key_present: bool
    ollama_enabled: bool
    mirofish_enabled: bool
    tavily_enabled: bool
    newsapi_enabled: bool
    alphavantage_enabled: bool
    memory_dir: str
    prompts_dir: str


class AgentInfo(BaseModel):
    name: str
    purpose: str
    prompt_name: Optional[str] = None
    inputs_required: List[str] = Field(default_factory=list)


class DeepHealthResponse(BaseModel):
    status: str
    version: str
    checks: Dict[str, Any]


class SimulationRunRequest(BaseModel):
    title: str
    seed_text: str
    prediction_goal: str
    mode: str = "standard"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationChatRequest(BaseModel):
    message: str


class SimulationStoredRecord(BaseModel):
    simulation_id: str
    status: str
    title: Optional[str] = None
    prediction_goal: Optional[str] = None
    remote_payload: Dict[str, Any] = Field(default_factory=dict)
    disk_bytes: int


# Learning Layer Schemas

class KnowledgeItem(BaseModel):
    """Knowledge item with compressed content."""
    id: Optional[str] = None
    source: str = Field(..., description="Source: 'tavily_search', 'jina_reader', 'newsapi'")
    query: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    summary: str = Field(..., description="Compressed summary (2-4KB)")
    published_at: Optional[str] = None
    ingested_at: str
    saved_at: Optional[str] = None
    last_accessed: Optional[str] = None
    trust_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    freshness_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)


class CaseLearning(BaseModel):
    """Learning metadata extracted from case execution."""
    case_id: str
    route_effectiveness: Dict[str, Any] = Field(default_factory=dict)
    prompt_performance: Dict[str, Any] = Field(default_factory=dict)
    provider_reliability: Dict[str, Any] = Field(default_factory=dict)
    patterns_detected: List[str] = Field(default_factory=list)
    learned_at: str


class PromptVersion(BaseModel):
    """Prompt version with A/B testing metadata."""
    id: str
    prompt_name: str
    version: int
    prompt_text: str
    goal: str
    status: str = Field(..., description="Status: 'testing', 'production', 'archived'")
    created_at: str
    test_count: int = 0
    win_count: int = 0
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    promoted_at: Optional[str] = None
    archived_at: Optional[str] = None


class Skill(BaseModel):
    """Distilled skill from execution patterns."""
    id: str
    name: str
    type: str = Field(..., description="Type: 'domain_expertise', 'preferred_source', 'agent_workflow'")
    description: str
    trigger_patterns: List[str] = Field(default_factory=list)
    recommended_agents: List[str] = Field(default_factory=list)
    preferred_sources: List[str] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)
    frequency: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: str
    usage_count: int = 0
    success_count: int = 0
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SourceTrust(BaseModel):
    """Trust score for a source."""
    source: str
    trust_score: float = Field(..., ge=0.0, le=1.0)
    verification_count: int
    success_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    last_updated: str


class FreshnessScore(BaseModel):
    """Freshness score for a knowledge item."""
    item_id: str
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    age_days: int
    last_updated: str


class LearningStatusResponse(BaseModel):
    """Learning engine status."""
    enabled: bool
    storage: Dict[str, Any]
    last_run: Dict[str, str]


class LearningInsightsResponse(BaseModel):
    """Learning insights."""
    recent_knowledge: List[Dict[str, Any]]
    storage_stats: Dict[str, Any]


class KnowledgeIngestionRequest(BaseModel):
    """Request to ingest knowledge."""
    topics: List[str] = Field(..., description="Topics to ingest knowledge about")


class SkillDistillRequest(BaseModel):
    """Request to distill skills."""
    min_frequency: int = Field(default=3, description="Minimum pattern frequency")


# Sentinel Layer Schemas

class SentinelAlert(BaseModel):
    """Sentinel alert from system health scan."""
    alert_id: str
    layer: int = Field(..., description="Layer: 1-6")
    component: str = Field(..., description="Component name")
    issue_type: str = Field(..., description="Issue type: error, degradation, anomaly")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    raw_evidence: str = Field(..., description="Raw evidence from scan")
    timestamp: str


class SentinelDiagnosis(BaseModel):
    """Sentinel diagnosis of an alert."""
    diagnosis_id: str
    alert_id: str
    root_cause: str
    fix_type: str = Field(..., description="Fix type: config, prompt, logic, dependency, data")
    safe_to_auto_apply: bool
    proposed_fix: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    timestamp: str


class PatchResult(BaseModel):
    """Result of patch application."""
    patch_id: str
    applied: bool
    target_file: str
    change_summary: str
    requires_human_review: bool
    timestamp: str


class CapabilitySnapshot(BaseModel):
    """Capability snapshot with AGI progression index."""
    snapshot_id: str
    timestamp: str
    scores: Dict[str, float] = Field(..., description="Dimension scores: reasoning_depth, source_trust_avg, skill_coverage, prompt_win_rate_avg, stability, self_correction_rate")
    # IMPORTANT COMMENT (must appear in schemas):
    # agi_progression_index is a VANITY METRIC for developer motivation.
    # It is a weighted composite of system health indicators:
    # error rate, confidence scores, trust quality, skill growth, etc.
    # It does NOT measure general intelligence, emergent reasoning, or AGI.
    # The name is aspirational and intentionally optimistic, not scientific.
    agi_progression_index: float = Field(..., ge=0.0, le=1.0)
    delta_from_last: Dict[str, float]


class SentinelCycleReport(BaseModel):
    """Report from a sentinel cycle."""
    cycle_id: str
    started_at: str
    completed_at: str
    alerts_found: int
    diagnoses_made: int
    patches_applied: int
    patches_pending_review: int
    capability_snapshot: CapabilitySnapshot
