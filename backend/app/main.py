from fastapi import FastAPI

app = FastAPI(title="MiroOrg Basic v2")

@app.get("/health")
def health():
    return {"status": "ok"}
