from urllib.parse import unquote_plus
from fastapi import APIRouter, Depends, BackgroundTasks

from ..processor import ReviewPipeline, get_review_pipeline
from ..services import review_task
from ..cache_store import cache

pr_router = APIRouter(prefix="/pr")

@pr_router.get("/review")
async def review(project, repo, pr_number, token, background_tasks: BackgroundTasks, pipeline: ReviewPipeline = Depends(get_review_pipeline)):
    token = unquote_plus(token)
    background_tasks.add_task(
        review_task,
        project,
        repo,
        pr_number,
        token,
        pipeline
    )

@pr_router.get("/result")
async def result(project, repo, pr_number):
    key = f"{project}_{repo}_{pr_number}"
    if key not in cache:
        return None

    if cache[key] == "processing":
        return 'processing'

    return cache[key]
