from code_review_agent.utils.nodes import define_langgraph

def run_pipeline(diff_text: str):
    graph = define_langgraph()
    return graph.invoke({"diff": diff_text})