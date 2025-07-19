from dataclasses import dataclass
from typing import TypedDict

@dataclass
class RepoInfo(TypedDict, total=False):
    project: str
    repo: str
    pr_number: str
    branch: str
    token: str