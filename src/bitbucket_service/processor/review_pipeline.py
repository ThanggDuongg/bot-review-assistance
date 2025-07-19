from ...code_review import LogicAgent, SummaryAgent, build_review_graph

class ReviewPipeline:
    def __init__(self):
        # self.logic_agent = LogicAgent()
        # self.summary_agent = SummaryAgent()
        self.graph = build_review_graph()

    def run(self, diff_text, repo_info=None):
        initial_state = {
            "diff": diff_text,
            "repo_info": repo_info or {}
        }
        return self.graph.invoke(initial_state)

# Singleton instance
review_pipeline = ReviewPipeline()

def get_review_pipeline():
    return review_pipeline 