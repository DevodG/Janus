"""
Workflow Engine — Multi-step intelligence workflows for Janus.

Supports:
- Research workflows (gather → analyze → synthesize)
- Simulation workflows (decompose → simulate → evaluate)
- Monitoring workflows (watch → detect → alert)
- Custom workflows (user-defined step chains)

Each workflow has:
- Steps (ordered, with dependencies)
- State (running, completed, failed)
- Results (per-step and final)
- History (audit trail)
"""

import os
import json
import time
import uuid
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR as BASE_DATA_DIR
except ImportError:
    BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR = Path(BASE_DATA_DIR) / "workflows"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowEngine:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.workflows: Dict[str, Dict] = {}
        self._load_workflows()

    def _load_workflows(self):
        wf_dir = DATA_DIR / "workflows.json"
        if wf_dir.exists():
            try:
                with open(wf_dir) as f:
                    self.workflows = json.load(f)
            except:
                self.workflows = {}

    def _save_workflows(self):
        wf_dir = DATA_DIR / "workflows.json"
        with open(wf_dir, "w") as f:
            json.dump(self.workflows, f, indent=2)

    def create_research_workflow(self, query: str, depth: str = "standard") -> str:
        """Create a research workflow: gather → analyze → synthesize → report."""
        wf_id = f"wf-research-{uuid.uuid4().hex[:8]}"

        steps = [
            {
                "id": "gather",
                "name": "Information Gathering",
                "description": "Search web, news, knowledge base for relevant information",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": [],
            },
            {
                "id": "analyze",
                "name": "Deep Analysis",
                "description": "Analyze gathered information, identify patterns, contradictions, gaps",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["gather"],
            },
            {
                "id": "simulate",
                "name": "Scenario Simulation",
                "description": "Run what-if scenarios based on analysis",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["analyze"],
            },
            {
                "id": "synthesize",
                "name": "Synthesis",
                "description": "Combine analysis and simulation into coherent insights",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["analyze", "simulate"],
            },
            {
                "id": "report",
                "name": "Final Report",
                "description": "Generate structured report with findings, recommendations, caveats",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["synthesize"],
            },
        ]

        workflow = {
            "id": wf_id,
            "type": "research",
            "query": query,
            "depth": depth,
            "status": WorkflowStatus.PENDING.value,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {},
            "metadata": {
                "total_steps": len(steps),
                "completed_steps": 0,
                "failed_steps": 0,
            },
        }

        self.workflows[wf_id] = workflow
        self._save_workflows()
        return wf_id

    def create_simulation_workflow(self, scenario: str) -> str:
        """Create a simulation workflow: decompose → perspectives → synthesize → evaluate."""
        wf_id = f"wf-sim-{uuid.uuid4().hex[:8]}"

        steps = [
            {
                "id": "decompose",
                "name": "Scenario Decomposition",
                "description": "Break down scenario into variables, actors, forces",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": [],
            },
            {
                "id": "perspectives",
                "name": "Multi-Perspective Analysis",
                "description": "Analyze from optimist, pessimist, realist, contrarian perspectives",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["decompose"],
            },
            {
                "id": "synthesize",
                "name": "Outcome Synthesis",
                "description": "Combine perspectives into scenarios with probabilities",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["perspectives"],
            },
            {
                "id": "evaluate",
                "name": "Risk Evaluation",
                "description": "Assess risks, uncertainties, early warning signals",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["synthesize"],
            },
        ]

        workflow = {
            "id": wf_id,
            "type": "simulation",
            "scenario": scenario,
            "status": WorkflowStatus.PENDING.value,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {},
            "metadata": {
                "total_steps": len(steps),
                "completed_steps": 0,
                "failed_steps": 0,
            },
        }

        self.workflows[wf_id] = workflow
        self._save_workflows()
        return wf_id

    def create_monitoring_workflow(
        self, watchlist: List[str], topics: List[str]
    ) -> str:
        """Create a monitoring workflow: watch → detect → alert → report."""
        wf_id = f"wf-monitor-{uuid.uuid4().hex[:8]}"

        steps = [
            {
                "id": "watch",
                "name": "Market Watching",
                "description": f"Monitor {len(watchlist)} tickers and {len(topics)} topics",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": [],
            },
            {
                "id": "detect",
                "name": "Anomaly Detection",
                "description": "Detect unusual movements, breaking news, sentiment shifts",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["watch"],
            },
            {
                "id": "alert",
                "name": "Alert Generation",
                "description": "Generate alerts for significant events",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["detect"],
            },
            {
                "id": "report",
                "name": "Intelligence Report",
                "description": "Compile daily intelligence digest",
                "status": StepStatus.PENDING.value,
                "result": None,
                "depends_on": ["alert"],
            },
        ]

        workflow = {
            "id": wf_id,
            "type": "monitoring",
            "watchlist": watchlist,
            "topics": topics,
            "status": WorkflowStatus.PENDING.value,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {},
            "metadata": {
                "total_steps": len(steps),
                "completed_steps": 0,
                "failed_steps": 0,
            },
        }

        self.workflows[wf_id] = workflow
        self._save_workflows()
        return wf_id

    async def run_workflow(self, wf_id: str) -> Dict:
        """Execute a workflow step by step."""
        workflow = self.workflows.get(wf_id)
        if not workflow:
            return {"error": "Workflow not found"}

        workflow["status"] = WorkflowStatus.RUNNING.value
        workflow["started_at"] = datetime.utcnow().isoformat()
        self._save_workflows()

        for step in workflow["steps"]:
            # Check dependencies
            if not all(
                self.workflows.get(wf_id, {}).get("steps", [{}])[i].get("status")
                == StepStatus.COMPLETED.value
                for dep in step.get("depends_on", [])
                for i, s in enumerate(self.workflows.get(wf_id, {}).get("steps", []))
                if s.get("id") == dep
            ):
                step["status"] = StepStatus.SKIPPED.value
                continue

            step["status"] = StepStatus.RUNNING.value
            self._save_workflows()

            try:
                result = await self._execute_step(step, workflow)
                step["result"] = result
                step["status"] = StepStatus.COMPLETED.value
                workflow["metadata"]["completed_steps"] += 1
            except Exception as e:
                step["result"] = {"error": str(e)}
                step["status"] = StepStatus.FAILED.value
                workflow["metadata"]["failed_steps"] += 1
                workflow["status"] = WorkflowStatus.FAILED.value
                workflow["updated_at"] = datetime.utcnow().isoformat()
                self._save_workflows()
                return workflow

            workflow["updated_at"] = datetime.utcnow().isoformat()
            self._save_workflows()

        workflow["status"] = WorkflowStatus.COMPLETED.value
        workflow["completed_at"] = datetime.utcnow().isoformat()
        self._save_workflows()
        return workflow

    async def _execute_step(self, step: Dict, workflow: Dict) -> Any:
        """Execute a single workflow step."""
        step_id = step["id"]
        wf_type = workflow["type"]
        query = workflow.get("query", workflow.get("scenario", ""))

        if not self.api_key:
            return {"error": "No API key configured"}

        prompts = {
            "research": {
                "gather": f"Gather comprehensive information about: {query}. Search for recent developments, key facts, expert opinions, and data points. Return structured findings.",
                "analyze": f"Analyze the gathered information about: {query}. Identify patterns, contradictions, gaps, and non-obvious connections. Be critical and evidence-based.",
                "simulate": f"Based on the analysis of: {query}, run what-if scenarios. What happens if key variables change? What are the most likely outcomes?",
                "synthesize": f"Synthesize the analysis and simulation results for: {query}. Produce coherent insights with evidence, confidence levels, and actionable recommendations.",
                "report": f"Generate a structured report on: {query}. Include executive summary, key findings, evidence, scenarios, recommendations, caveats, and next steps.",
            },
            "simulation": {
                "decompose": f"Decompose this scenario into its core components: {workflow.get('scenario', '')}. Identify variables, actors, forces, constraints, and uncertainties.",
                "perspectives": f"Analyze this scenario from multiple perspectives (optimist, pessimist, realist, contrarian): {workflow.get('scenario', '')}. What does each perspective see?",
                "synthesize": f"Synthesize the multi-perspective analysis into coherent scenarios with probabilities: {workflow.get('scenario', '')}. What are the most likely outcomes?",
                "evaluate": f"Evaluate the risks and uncertainties for: {workflow.get('scenario', '')}. What are the early warning signals? What could go wrong? What could go right?",
            },
        }

        prompt = prompts.get(wf_type, {}).get(
            step_id, f"Process step '{step_id}' for: {query}"
        )

        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://huggingface.co",
                    "X-Title": "Janus Workflows",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen3.6-plus:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Janus's workflow engine. Execute this step thoroughly and return structured results.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            r.raise_for_status()
            return {
                "content": r.json()["choices"][0]["message"]["content"],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_workflow(self, wf_id: str) -> Optional[Dict]:
        """Get a workflow by ID."""
        return self.workflows.get(wf_id)

    def list_workflows(self, limit: int = 20, wf_type: str = None) -> List[Dict]:
        """List workflows."""
        workflows = list(self.workflows.values())
        if wf_type:
            workflows = [w for w in workflows if w.get("type") == wf_type]
        workflows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return workflows[:limit]

    def get_status(self) -> Dict:
        """Get workflow engine status."""
        total = len(self.workflows)
        by_status = {}
        by_type = {}
        for wf in self.workflows.values():
            status = wf.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            wf_type = wf.get("type", "unknown")
            by_type[wf_type] = by_type.get(wf_type, 0) + 1
        return {"total_workflows": total, "by_status": by_status, "by_type": by_type}


# Global instance
workflow_engine = WorkflowEngine()
