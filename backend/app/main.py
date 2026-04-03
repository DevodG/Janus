import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import UserTask, AgentRunRequest, PromptUpdateRequest
from app.graph import run_case
from app.memory import save_case
from app.config import (
    LLM_PROVIDER,
    MEMORY_DIR,
    PROMPTS_DIR,
    DEEPSEEK_API_KEY,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_REASONER_MODEL,
)
from app.services.case_store import list_cases, get_case, delete_case, memory_stats
from app.services.prompt_store import list_prompts, get_prompt, update_prompt
from app.services.health_service import deep_health
from app.services.agent_registry import list_agents, get_agent, run_single_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MiroOrg Basic v2", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/health/deep")
def health_deep():
    return deep_health()


@app.get("/config/status")
def config_status():
    return {
        "llm_provider": LLM_PROVIDER,
        "memory_dir": str(MEMORY_DIR),
        "prompts_dir": str(PROMPTS_DIR),
        "deepseek_key_present": bool(DEEPSEEK_API_KEY),
        "deepseek_chat_model": DEEPSEEK_CHAT_MODEL,
        "deepseek_reasoner_model": DEEPSEEK_REASONER_MODEL,
    }


@app.get("/agents")
def agents():
    return list_agents()


@app.get("/agents/{agent_name}")
def agent_detail(agent_name: str):
    agent = get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.post("/run")
def run_org(task: UserTask):
    try:
        logger.info(f"Processing user input: {task.user_input[:80]}")
        result = run_case(task.user_input)

        payload = {
            "case_id": result["case_id"],
            "user_input": result["user_input"],
            "outputs": [
                result["research"],
                result["planner"],
                result["verifier"],
                result["final"],
            ],
            "final_answer": result["final"]["summary"],
        }

        save_case(result["case_id"], payload)
        return payload

    except Exception as e:
        logger.exception("Error processing /run")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/run/debug")
def run_org_debug(task: UserTask):
    try:
        logger.info(f"Processing debug input: {task.user_input[:80]}")
        result = run_case(task.user_input)

        payload = {
            "case_id": result["case_id"],
            "user_input": result["user_input"],
            "route": result["route"],
            "research": result["research"],
            "planner": result["planner"],
            "verifier": result["verifier"],
            "final": result["final"],
        }

        save_case(result["case_id"], payload)
        return payload

    except Exception as e:
        logger.exception("Error processing /run/debug")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/run/agent")
def run_one_agent(request: AgentRunRequest):
    try:
        result = run_single_agent(
            agent=request.agent,
            user_input=request.user_input,
            research_output=request.research_output,
            planner_output=request.planner_output,
            verifier_output=request.verifier_output,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error processing /run/agent")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/cases")
def cases(limit: int | None = Query(default=None, ge=1, le=200)):
    return list_cases(limit=limit)


@app.get("/cases/{case_id}")
def case_detail(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.get("/cases/{case_id}/raw")
def case_raw(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.delete("/cases/{case_id}")
def case_delete(case_id: str):
    deleted = delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"deleted": True, "case_id": case_id}


@app.get("/memory/stats")
def memory_stats_endpoint():
    return memory_stats()


@app.get("/prompts")
def prompts():
    return list_prompts()


@app.get("/prompts/{name}")
def prompt_detail(name: str):
    try:
        prompt = get_prompt(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.put("/prompts/{name}")
def prompt_update(name: str, payload: PromptUpdateRequest):
    try:
        return update_prompt(name, payload.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
