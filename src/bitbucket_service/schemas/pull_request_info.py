from dataclasses import dataclass

@dataclass
class PullRequestInfo:
    source_branch: str
    target_branch: str
    title: str
    description: str
    author: str
    state: str
    source_repo: str
    target_repo: str