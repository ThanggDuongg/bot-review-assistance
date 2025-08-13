from langgraph.graph import StateGraph, END
from .nodes import (
    chunk_node, 
    fetch_files_node,
    create_ast_chunks_node,
    summary_branch_node, 
    review_branch_node
)
from typing import Optional

from ..core.schemas import ReviewState, RepoInfo


def build_review_graph():
    graph = StateGraph(ReviewState)
    
    # Add nodes
    graph.add_node("chunk_node", chunk_node)
    graph.add_node("fetch_files_node", fetch_files_node)
    graph.add_node("create_ast_chunks_node", create_ast_chunks_node)
    graph.add_node("summary_branch_node", summary_branch_node)
    graph.add_node("review_branch_node", review_branch_node)
    
    # Workflow edges
    graph.set_entry_point("chunk_node")
    graph.add_edge("chunk_node", "summary_branch_node")
    graph.add_edge("chunk_node", "fetch_files_node")
    graph.add_edge("fetch_files_node", "create_ast_chunks_node")
    graph.add_edge("create_ast_chunks_node", "review_branch_node")
    graph.set_finish_point("summary_branch_node")
    graph.set_finish_point("review_branch_node")

    return graph.compile()

# Export the compiled graph for LangGraph CLI
code_review_graph = build_review_graph()

class ReviewPipeline:
    def __init__(self):
        self.graph = build_review_graph()
    
    def run(self, diff_text: str, repo_info: Optional[RepoInfo] = None) -> dict:
        initial_state = {
            "diff": diff_text,
            "repo_info": repo_info or {}
        }
        return self.graph.invoke(initial_state)

    def invoke(self, input_data: dict) -> dict:
        """Invoke method for LangGraph CLI compatibility"""
        diff_text = input_data.get("diff", "")
        repo_info = input_data.get("repo_info", {})
        
        if not diff_text:
            messages = input_data.get("messages", [])
            if messages:
                diff_text = messages[-1].get("content", "")
        
        return self.run(diff_text, repo_info)


def run_pipeline(diff_text: str, repo_info: Optional[RepoInfo] = None) -> dict:
    pipeline = ReviewPipeline()
    return pipeline.run(diff_text, repo_info)
