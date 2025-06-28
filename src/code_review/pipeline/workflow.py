from langgraph.graph import StateGraph
from .nodes import (
    ReviewState, detect_language, chunk, scan, 
    naming, syntax, review, summarize
)


class ReviewPipeline:
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self):
        graph = StateGraph(ReviewState)
        
        # Add nodes
        graph.add_node("detect_language_node", detect_language)
        graph.add_node("chunk_node", chunk)
        graph.add_node("scan_node", scan)
        graph.add_node("naming_node", naming)
        graph.add_node("syntax_node", syntax)
        graph.add_node("review_node", review)
        graph.add_node("summarize_node", summarize)
        
        # Define workflow edges
        graph.set_entry_point("detect_language_node")
        graph.add_edge("detect_language_node", "chunk_node")
        graph.add_edge("chunk_node", "scan_node")
        graph.add_edge("scan_node", "naming_node")
        graph.add_edge("naming_node", "syntax_node")
        graph.add_edge("syntax_node", "review_node")
        graph.add_edge("review_node", "summarize_node")
        graph.set_finish_point("summarize_node")
        
        return graph.compile()
    
    def run(self, diff_text: str) -> dict:
        """Run the complete review pipeline on a diff.
        
        Args:
            diff_text: The code diff to review
            
        Returns:
            Dictionary containing all review results
        """
        return self.graph.invoke({"diff": diff_text})


def run_pipeline(diff_text: str) -> dict:
    """Run the code review pipeline on a diff.
    
    Args:
        diff_text: The code diff to review
        
    Returns:
        Dictionary containing all review results
    """
    pipeline = ReviewPipeline()
    return pipeline.run(diff_text)
