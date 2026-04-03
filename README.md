# MiroOrg Basic v2

A multi-agent AI organization system built with FastAPI, LangGraph, and Google Gemini.

## Overview

MiroOrg Basic v2 is an intelligent system that processes user requests through a pipeline of specialized AI agents:
- **Switchboard**: Routes and categorizes incoming requests
- **Research**: Gathers relevant information and context
- **Planner**: Creates actionable plans based on research
- **Verifier**: Validates plans and identifies potential issues
- **Synthesizer**: Produces final, comprehensive responses

## Architecture

- **Backend**: FastAPI application with REST endpoints
- **Orchestration**: LangGraph for agent workflow management
- **AI Model**: Google Gemini for agent responses
- **Memory**: JSON-based case persistence
- **Configuration**: Environment variables for API keys

## Quick Start

### Prerequisites

- Python 3.14+
- Google Gemini API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd miroorg-basic-v2
```

2. Set up virtual environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### POST /run
Process a user request through the agent pipeline.

**Request:**
```json
{
  "user_input": "Your request here"
}
```

**Response:**
```json
{
  "case_id": "uuid-string",
  "route": {...},
  "research": {...},
  "planner": {...},
  "verifier": {...},
  "final": {...}
}
```

## Configuration

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your_api_key_here
MODEL_NAME=gemini-1.5-flash
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration and paths
│   ├── main.py            # FastAPI application
│   ├── schemas.py         # Pydantic models
│   ├── memory.py          # Case persistence
│   ├── graph.py           # LangGraph orchestration
│   ├── agents/            # Agent implementations
│   │   ├── __init__.py
│   │   ├── _model.py      # Gemini API wrapper
│   │   ├── switchboard.py
│   │   ├── research.py
│   │   ├── planner.py
│   │   ├── verifier.py
│   │   └── synthesizer.py
│   ├── prompts/           # Agent instruction files
│   │   ├── research.txt
│   │   ├── planner.txt
│   │   ├── verifier.txt
│   │   └── synthesizer.txt
│   └── data/
│       ├── logs/          # Application logs
│       └── memory/        # Saved cases
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── README.md
```

## Development

### Running Tests

```bash
pytest
```

### Adding New Agents

1. Create agent file in `app/agents/`
2. Add prompt file in `app/prompts/`
3. Update `graph.py` to include new node
4. Add to `schemas.py` if needed

### Logging

Logs are written to `app/data/logs/` with rotation. Check logs for debugging agent execution and API errors.

## Deployment

### Docker

```dockerfile
FROM python:3.14-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- Set `GEMINI_API_KEY` securely (environment variables, secrets management)
- Configure logging for your deployment environment
- Add rate limiting and authentication as needed
- Monitor agent performance and API usage

## License

[Add your license here]