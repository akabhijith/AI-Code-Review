from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.routers.api import analyze_pr_task, router as api_router

app = FastAPI()

# Include the API routes
app.include_router(api_router, prefix="/api")

class PRRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: Optional[str] = None

@app.post("/api/analyze-pr")
def submit_analysis(request: PRRequest):
    task = analyze_pr_task.apply_async(args=[request.repo_url, request.pr_number, request.github_token])
    return {"task_id": task.id, "status": "Task submitted"}