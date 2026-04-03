from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
