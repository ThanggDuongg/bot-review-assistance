from typing import Optional, Any, Dict
import os

from ..agents import LogicAgent, SummaryAgent
from ..core.schemas import ReviewState
from ..core.tools import FileFetcher, MockFileFetcher
from ..core.vector_store import chunk_diff
from ..core.chunkers.chunker_factory import get_context_chunker
from ..core.utils import Utils

summary_agent = SummaryAgent()
logic_agent = LogicAgent()
file_fetcher = FileFetcher()
mock_file_fetcher = MockFileFetcher()

def validate_repo_info(repo_info: Optional[Dict[str, Any]]) -> bool:
    if not repo_info:
        return False
    
    # Check required fields
    required_fields = ['workspace', 'repo']
    for field in required_fields:
        if field not in repo_info or not repo_info[field]:
            Utils.debug_print(f"Pipeline: Missing required field '{field}' in repo_info")
            return False
    
    # Validate field types
    if not isinstance(repo_info['workspace'], str) or not isinstance(repo_info['repo'], str):
        Utils.debug_print("Pipeline: workspace and repo must be strings")
        return False
    
    # Optional branch validation
    if 'branch' in repo_info and not isinstance(repo_info['branch'], str):
        Utils.debug_print("Pipeline: branch must be a string")
        return False
    
    return True

def chunk_node(state: ReviewState) -> dict:
    Utils.debug_print(f"[chunk_node] input state keys: {list(state.keys())}")
    try:
        Utils.debug_print("Pipeline: Chunking diff content...")
        diff_chunks, diff_file_paths = chunk_diff(state["diff"])
        Utils.debug_print(f"Pipeline: Created {len(diff_chunks)} documents")
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
    Utils.debug_print(f"[fetch_files_node] input state type: {type(state)}")
    Utils.debug_print(f"[fetch_files_node] input state keys: {list(state.keys()) if hasattr(state, 'keys') else state}")
    Utils.debug_print(f"[fetch_files_node] state value: {state}")
    try:
        documents = state.get("diff_chunks", [])
        repo_info = state.get("repo_info", {})
        Utils.debug_print(f"[fetch_files_node] type diff_chunks: {type(documents)}, value: {documents}")
        Utils.debug_print(f"[fetch_files_node] type repo_info: {type(repo_info)}, value: {repo_info}")
        if not documents:
            Utils.debug_print("[fetch_files_node] No documents, returning empty file_contents")
            return {"file_contents": {}}
        env = os.getenv('ENVIRONMENT', 'prod')
        if env != 'dev' and not validate_repo_info(repo_info):
            Utils.debug_print("[fetch_files_node] Invalid repo_info, skipping file fetching")
            return {"file_contents": {}}
        if env == 'dev':
            fetcher = mock_file_fetcher
            Utils.debug_print("Pipeline: Using MockFileFetcher (dev mode)")
        else:
            fetcher = file_fetcher
            Utils.debug_print("Pipeline: Using real FileFetcher")
        Utils.debug_print(f"Pipeline: Fetching {len(documents)} files from {repo_info.get('workspace','?')}/{repo_info.get('repo','?')}...")
        file_contents = fetcher.fetch_files_parallel(documents, repo_info)
        Utils.debug_print(f"Pipeline: Successfully fetched {len(file_contents)} files")
        output = {"file_contents": file_contents}
        Utils.debug_print(f"[fetch_files_node] output: {{'file_contents': {len(file_contents)}}}")
        return output
    except Exception as e:
        Utils.debug_print(f"[fetch_files_node] Exception: {e}")
        return {"file_contents": {}}

def create_ast_chunks_node(state: ReviewState) -> dict:
    Utils.debug_print(f"[create_ast_chunks_node] input state type: {type(state)}")
    Utils.debug_print(f"[create_ast_chunks_node] input state keys: {list(state.keys()) if hasattr(state, 'keys') else state}")
    Utils.debug_print(f"[create_ast_chunks_node] state value: {state}")
    try:
        documents = state.get("diff_chunks", [])
        file_contents = state.get("file_contents", {})
        Utils.debug_print(f"[create_ast_chunks_node] type diff_chunks: {type(documents)}, value: {documents}")
        Utils.debug_print(f"[create_ast_chunks_node] type file_contents: {type(file_contents)}, value: {file_contents}")
        if not documents:
            Utils.debug_print("[create_ast_chunks_node] No documents, returning empty ast_chunks")
            return {"ast_chunks": []}
        Utils.debug_print("Pipeline: Creating AST chunks...")
        chunked_documents = []
        for doc in documents:
            file_path = doc.metadata.get('file_path')
            file_content = file_contents.get(file_path)
            if not file_content:
                Utils.debug_print(f"Pipeline: No content available for {file_path}")
                continue
            chunker = get_context_chunker(file_path)
            if not chunker:
                Utils.debug_print(f"Pipeline: No chunker available for {file_path}")
                continue
            try:
                chunks = chunker.chunk_code(file_content, file_path, doc.metadata.get('diff_lines', []))
                chunked_documents.extend(chunks)
                Utils.debug_print(f"Pipeline: Created {len(chunks)} chunks for {file_path}")
            except Exception as e:
                Utils.debug_print(f"Pipeline: Error chunking {file_path}: {str(e)}")
                continue
        Utils.debug_print(f"Pipeline: Created {len(chunked_documents)} total AST chunks")
        output = {"ast_chunks": chunked_documents}
        Utils.debug_print(f"[create_ast_chunks_node] output: {{'ast_chunks': {len(chunked_documents)}}}")
        return output
    except Exception as e:
        Utils.debug_print(f"[create_ast_chunks_node] Exception: {e}")
        return {"ast_chunks": []}

def summary_branch_node(state: ReviewState) -> dict:
    Utils.debug_print(f"[summary_branch_node] input state keys: {list(state.keys())}")
    try:
        Utils.debug_print("Pipeline: Processing summary branch...")
        documents = state.get("diff_chunks", [])
        if not documents:
            Utils.debug_print("[summary_branch_node] No documents, returning error summary_result")
            return {"summary_result": {"summary": {"error": "No documents to summarize"}}}
        result = summary_agent.process(documents)
        Utils.debug_print("Pipeline: Summary branch completed")
        output = {"summary_result": result}
        Utils.debug_print(f"[summary_branch_node] output: {output}")
        return output
    except Exception as e:
        Utils.debug_print(f"[summary_branch_node] Exception: {e}")
        return {"summary_result": {"summary": {"error": f"Summary failed: {str(e)}"}}}

def review_branch_node(state: ReviewState) -> dict:
    Utils.debug_print(f"[review_branch_node] input state keys: {list(state.keys())}")
    try:
        Utils.debug_print("Pipeline: Processing review branch...")
        chunked_documents = state.get("ast_chunks", [])
        file_contents = state.get("file_contents", {})
        if not chunked_documents:
            Utils.debug_print("[review_branch_node] No ast_chunks, returning empty review_result")
            return {"review_result": {
                "file_reviews": [],
                "total_files_reviewed": 0,
                "total_chunks_reviewed": 0,
                "error": "No chunks to review"
            }}
        result = logic_agent.process(chunked_documents, file_contents)
        review_result = result
        Utils.debug_print("Pipeline: Review branch completed")
        output = {"review_result": review_result}
        Utils.debug_print(f"[review_branch_node] output: {output}")
        return output
    except Exception as e:
        Utils.debug_print(f"[review_branch_node] Exception: {e}")
        return {"review_result": {
            "file_reviews": [],
            "total_files_reviewed": 0,
            "total_chunks_reviewed": 0,
            "error": f"Review failed: {str(e)}"
        }}

def combine_results_node(state: ReviewState) -> dict:
    """Flatten summary and review results into a single flat dict."""
    return {
        **state.get("summary_result", {}).get("summary", {}),
        **state.get("review_result", {})
    }
