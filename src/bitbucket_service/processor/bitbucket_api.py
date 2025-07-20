import os
import urllib.parse
import asyncio
import aiohttp
from dacite import from_dict

from ..schemas import PullRequestInfo, DiffResponse
from ..utils import Utils
from typing import Tuple, Dict

from ...code_review.core.schemas import RepoInfo

uri = os.getenv("SC_URL")

async def get_pr_data(project: str, repo: str, pr_number: int, token: str) -> Tuple[RepoInfo, str]:
    encoded_token = urllib.parse.quote_plus(token)
    headers = {
        "Authorization": f"Bearer {encoded_token}",
        "Accept": "application/json"
    }

    info_url = f"{uri}/rest/api/latest/projects/{project}/repos/{repo}/pull-requests/{pr_number}"
    diff_url = f"{uri}/rest/api/latest/projects/{project}/repos/{repo}/pull-requests/{pr_number}/diff"

    Utils.debug_print(
        f"Fetching PR data parallel: project={project}, repo={repo}, pr_number={pr_number}")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        info_task = _fetch_pr_info(session, info_url, headers)
        diff_task = _fetch_pr_diff(session, diff_url, headers)

        try:
            pr_info, diff_text = await asyncio.gather(info_task, diff_task)
            repo_info = RepoInfo(
                project=project,
                repo=repo,
                pr_number=pr_number,
                branch=pr_info.source_branch,
                token=encoded_token
            )

            return repo_info, diff_text
        except Exception as e:
            Utils.debug_print(f"Error in parallel fetch: {e}")
            raise

async def _fetch_pr_info(session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> PullRequestInfo:
    async with session.get(url, headers=headers) as response:
        Utils.debug_print(f"PR Info response status: {response.status}")

        if response.status != 200:
            error_text = await response.text()
            Utils.debug_print(f"PR Info error: {error_text}")
            raise Exception(f"Failed to fetch PR info: {response.status}")

        data = await response.json()

        # Extract branch and repo info
        from_ref = data['fromRef']
        to_ref = data['toRef']

        pr_info = PullRequestInfo(
            source_branch=from_ref['displayId'],
            target_branch=to_ref['displayId'],
            title=data['title'],
            description=data.get('description', ''),
            author=data['author']['user']['displayName'],
            state=data['state'],
            source_repo=from_ref['repository']['name'],
            target_repo=to_ref['repository']['name']
        )

        Utils.debug_print(f"PR Info: {pr_info.source_branch} -> {pr_info.target_branch}")
        return pr_info

async def _fetch_pr_diff(session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> str:
    params = {
        'contextLines': 0,
        'whitespace': 'ignore-all',
        'withComments': 'false'
    }

    async with session.get(url, params=params, headers=headers) as response:
        Utils.debug_print(f"PR Diff response status: {response.status}")

        if response.status != 200:
            error_text = await response.text()
            Utils.debug_print(f"PR Diff error: {error_text}")
            raise Exception(f"Failed to fetch PR diff: {response.status}")

        data = await response.json()

        # Process diff data
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