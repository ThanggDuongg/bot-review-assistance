from ..processor import get_review_pipeline, get_pr_data
from ..cache_store import cache

async def review_task(project, repo, pr_number, token, pipeline=None):
    key = f"{project}_{repo}_{pr_number}"
    if key in cache and cache[key] == "processing":
        return
    cache[key] = "processing"
    repo_info, diff = await get_pr_data(project, repo, pr_number, token)
    if pipeline is None:
        pipeline = get_review_pipeline()
    cache[key] = pipeline.run(diff, repo_info)