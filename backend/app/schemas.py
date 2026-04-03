from typing import List, Dict, Any
from pydantic import BaseModel, Field


class UserTask(BaseModel):
    user_input: str


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
