from dataclasses import dataclass
from typing import TypedDict, Optional, List, Dict
from langchain.schema import Document

from src.code_review.core.schemas import RepoInfo


@dataclass
class ReviewState(TypedDict):
    diff: str
    repo_info: Optional[RepoInfo]
    diff_chunks: Optional[List[Document]]
    diff_file_paths: Optional[List[str]]
    file_contents: Optional[Dict[str, str]]
    ast_chunks: Optional[List[Document]]
    summary_result: Optional[dict]
    review_result: Optional[dict]
    final_result: Optional[dict]