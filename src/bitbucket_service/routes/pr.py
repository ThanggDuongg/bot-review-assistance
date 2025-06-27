from cachetools import TTLCache
from fastapi import APIRouter, Depends, BackgroundTasks

from src.bitbucket_service.processor import ReviewPipeline, get_review_pipeline
from src.bitbucket_service.services.pr_review import review_task

pr_router = APIRouter(prefix="/pr")
cache = TTLCache(maxsize=1000, ttl=86400)

@pr_router.get("/review")
async def review(project, repo, pr_number, token, background_tasks: BackgroundTasks, pipeline: ReviewPipeline = Depends(get_review_pipeline)):
    background_tasks.add_task(review_task, project, repo, pr_number, token, pipeline)

@pr_router.get("/result")
async def result(project, repo, pr_number):
    key = f"{project}_{repo}_{pr_number}"
    if key not in cache:
        return None

    if cache[key] == "processing":
        return 'processing'

    return cache[key]
