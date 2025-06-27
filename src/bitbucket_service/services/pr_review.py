from src.bitbucket_service.processor import get_review_pipeline
from src.bitbucket_service.processor.bitbucket_api import get_pr_diff
from src.bitbucket_service.routes.pr import cache

def review_task(project, repo, pr_number, token, pipeline=None):
    key = f"{project}_{repo}_{pr_number}"
    if key in cache and cache[key] == "processing":
        return
    cache[key] = "processing"
    diff = get_pr_diff(project, repo, pr_number, token)
    if pipeline is None:
        pipeline = get_review_pipeline()
    cache[key] = pipeline.run(diff) 