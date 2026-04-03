from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Routing decision from Switchboard agent."""
    task_family: str = Field(..., description="Task family: 'normal' or 'simulation'")
    domain_pack: str = Field(..., description="Domain pack: 'finance', 'general', 'policy', 'custom'")
    complexity: str = Field(..., description="Complexity: 'simple', 'medium', 'complex'")
    execution_mode: str = Field(..., description="Execution mode: 'solo', 'standard', 'deep'")
    risk_level: str = Field(default="low", description="Risk level: 'low', 'medium', 'high'")


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


class ConfigStatusResponse(BaseModel):
    model_name: str
    memory_dir: str
    prompts_dir: str
    gemini_key_present: bool


class AgentInfo(BaseModel):
    name: str
    purpose: str
    prompt_name: Optional[str] = None
    inputs_required: List[str] = Field(default_factory=list)


class DeepHealthResponse(BaseModel):
    status: str
    version: str
    checks: Dict[str, Any]
