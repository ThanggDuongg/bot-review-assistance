from dataclasses import dataclass
from typing import Optional, TypedDict

@dataclass
class RepoInfo(TypedDict, total=False):
    # Required fields for Bitbucket API
    workspace: str  # Bitbucket workspace name
    repo: str  # Repository name
    branch: str  # Branch name (default: 'develop')

    # Optional fields for enhanced context
    project_key: Optional[str]  # Project key (for enterprise Bitbucket)
    commit_hash: Optional[str]  # Specific commit hash
    pr_id: Optional[str]  # Pull request ID for context

    # Optional authentication
    token: Optional[str]  # Custom token (overrides env var)

    # Optional metadata
    repo_url: Optional[str]  # Full repository URL
    description: Optional[str]  # Repository description