from dataclasses import dataclass
from typing import TypedDict, Optional, List, Dict
from langchain.schema import Document

from src.code_review.core.schemas import RepoInfo


@dataclass
class ReviewState(TypedDict):
    diff: str
    repo_info: Optional[RepoInfo]
    # Diff-based chunks
    diff_chunks: Optional[List[Document]]
    diff_file_paths: Optional[List[str]]
    # File contents for AST chunking
    file_contents: Optional[Dict[str, str]]
    # AST chunks for review
    ast_chunks: Optional[List[Document]]
    # Results
    summary_result: Optional[dict]
    review_result: Optional[dict]
    final_result: Optional[dict]