import requests
import os
from dacite import from_dict
from src.bitbucket_service.schemas.bitbucket_diff import DiffResponse
from src.bitbucket_service.utils import Utils

url = os.getenv("SC_URL")

def get_pr_diff(project: str, repo: str, pr_number: int, token: str) -> str:
    Utils.debug_print(f"Getting PR diff: project={project}, repo={repo}, pr_number={pr_number}")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{url}/rest/api/latest/projects/{project}/repos/{repo}/pull-requests/{pr_number}/diff",
        headers=headers
    )
    Utils.debug_print(f"Bitbucket response status: {response.status_code}")
    data = response.json()
    diff_response = from_dict(data_class=DiffResponse, data=data)
    result_lines = []
    for diff in diff_response.diffs:
        if diff.destination is None:
            continue
        result_lines.append(f"## File: '{diff.destination.toString}'")
        for hunk in diff.hunks:
            for segment in hunk.segments:
                status = {"ADDED": "+", "REMOVED": "-"}.get(segment.type, "~")
                for line in segment.lines:
                    text = f"{status} {line.destination} {line.line}"
                    result_lines.append(text)
            result_lines.append("...")
        result_lines.append("")
    return "\n".join(result_lines) 