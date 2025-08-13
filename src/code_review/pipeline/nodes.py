from typing import List, Tuple
from langchain_core.documents import Document
from ..agents import LogicAgent, SummaryAgent
from ..core.schemas import ReviewState, RepoInfo
from ..core.tools import FileFetcher
from ..core.vector_store import chunk_diff
from ..core.utils import Utils

summary_agent = SummaryAgent()
logic_agent = LogicAgent()
file_fetcher = FileFetcher()

def validate_repo_info(repo_info: RepoInfo) -> bool:
    if not repo_info:
        return False
    
    required_fields = ['project', 'repo', 'pr_number', 'branch', 'token']
    for field in required_fields:
        if field not in repo_info or not repo_info[field]:
            Utils.debug_print(f"Pipeline: Missing required field '{field}' in repo_info")
            return False

    return True

def should_fetch_file(document: Document) -> bool:
    # In diff_chunker I just add line + into diff_lines
    diff_lines = document.metadata.get('diff_lines', [])
    return len(diff_lines) > 0

def filter_files_for_fetching(documents: List) -> Tuple[List[Document], List[Document]]:
    files_to_fetch = []
    skipped_files = []

    for doc in documents:
        file_path = doc.metadata.get('file_path', 'unknown')

        if should_fetch_file(doc) and Utils.is_valid_code_file(file_path):
            files_to_fetch.append(doc)
        else:
            skipped_files.append(file_path)

    return files_to_fetch, skipped_files

def chunk_node(state: ReviewState) -> dict:
    try:
        diff_chunks, diff_file_paths = chunk_diff(state["diff"])
        output = {
            "diff_chunks": diff_chunks,
            "diff_file_paths": diff_file_paths
        }
        Utils.debug_print(f"[chunk_node] output: {{'diff_chunks': {len(diff_chunks)}, 'diff_file_paths': {len(diff_file_paths)}}}")
        return output
    except Exception as e:
        Utils.debug_print(f"[chunk_node] Exception: {e}")
        return {
            "diff_chunks": [],
            "diff_file_paths": []
        }

def fetch_files_node(state: ReviewState) -> dict:
    try:
        documents = state.get("diff_chunks", [])
        repo_info = state.get("repo_info", {})
        if not documents:
            Utils.debug_print("[fetch_files_node] No documents, returning empty file_contents")
            return {"file_contents": {}}

        # Filter documents to only fetch files that need content
        files_to_fetch, skipped_files = filter_files_for_fetching(documents)

        if skipped_files:
            Utils.debug_print(f"Pipeline: Skipped files (only removals): {skipped_files}")

        if not files_to_fetch:
            Utils.debug_print("[fetch_files_node] No files need content fetching, returning empty file_contents")
            return {"file_contents": {}}

        if not validate_repo_info(repo_info):
            Utils.debug_print("[fetch_files_node] Invalid repo_info, skipping file fetching")
            return {"file_contents": {}}

        fetcher = file_fetcher
        file_contents = fetcher.fetch_files_parallel(files_to_fetch, repo_info)
        output = {"file_contents": file_contents}
        Utils.debug_print(f"[fetch_files_node] output: {{'file_contents': {len(file_contents)}}}")
        return output
    except Exception as e:
        Utils.debug_print(f"[fetch_files_node] Exception: {e}")
        return {"file_contents": {}}

def summary_branch_node(state: ReviewState) -> dict:
    try:
        documents = state.get("diff_chunks", [])
        if not documents:
            Utils.debug_print("[summary_branch_node] No documents, returning error summary_result")
            return {"summary_result": {"summary": {"error": "No documents to summarize"}}}

        result = summary_agent.process(documents)
        Utils.debug_print("Pipeline: Summary branch completed")
        output = {"summary_result": result}
        return output
    except Exception as e:
        Utils.debug_print(f"[summary_branch_node] Exception: {e}")
        return {"summary_result": {"summary": {"error": f"Summary failed: {str(e)}"}}}

def create_ast_chunks_node(state: ReviewState) -> dict:
    # TODO
    return {}

def review_branch_node(state: ReviewState) -> dict:
    # TODO
    return {}
