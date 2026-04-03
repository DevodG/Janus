import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import UserTask
from app.graph import run_case
from app.memory import save_case

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='MiroOrg Basic v2', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return {'status': 'ok', 'version': '1.0.0'}


@app.post('/run')
def run_org(task: UserTask):
    try:
        logger.info(f"Processing user input: {task.user_input[:50]}...")
        result = run_case(task.user_input)
        logger.info(f"Case {result['case_id']} completed successfully")

        payload = {
            'case_id': result['case_id'],
            'user_input': result['user_input'],
            'outputs': [
                result['research'],
                result['planner'],
                result['verifier'],
                result['final'],
            ],
            'final_answer': result['final']['summary'],
        }

        save_case(result['case_id'], payload)
        return payload

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

