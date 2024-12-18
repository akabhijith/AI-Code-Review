from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from uuid import uuid4
from app.tasks import analyze_pr_task
from redis import Redis
import os

router = APIRouter()

# Initialize Redis for storing task statuses and results
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Request schema for analyze-pr
class AnalyzePRRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: str = None

# Endpoint to start the PR analysis task
@router.post("/analyze-pr")
def analyze_pr(request: AnalyzePRRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid4())
    redis.set(f"task:{task_id}:status", "pending")
    
    # Launch the Celery task
    background_tasks.add_task(analyze_pr_task, request.repo_url, request.pr_number, request.github_token)
    
    return {"task_id": task_id, "status": "Task submitted"}

# Endpoint to check the status of a task
@router.get("/status/{task_id}")
def get_status(task_id: str):
    status = redis.get(f"task:{task_id}:status")
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": status.decode()}

# Endpoint to get the results of a task
@router.get("/results/{task_id}")
def get_results(task_id: str):
    results = redis.get(f"task:{task_id}:results")
    if not results:
        raise HTTPException(status_code=404, detail="Results not found or task still processing")
    return {"task_id": task_id, "results": results.decode()}
 