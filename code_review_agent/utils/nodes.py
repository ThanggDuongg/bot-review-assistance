import langdetect
from langgraph.graph import StateGraph
from typing import TypedDict, Optional, List, Any
from code_review_agent.utils.tools import scan_structure, check_naming, check_syntax, review_logic, summarize_issues
from code_review_agent.utils.vector_utils import chunk_diff, build_vector_store, search_similar_code

def detect_language(state):
    try:
        language = langdetect.detect(state["diff"])
        return {"language": language}
    except Exception as e:
        return {"language": "python"}

def chunk(state):
    try:
        docs = chunk_diff(state["diff"])
        vs = build_vector_store(docs)
        return {"chunks": docs, "vs": vs}
    except Exception as e:
        return {"chunks": [], "vs": None}

def scan(state):
    return {"scan": scan_structure.invoke({"diff_text": state["diff"]})}

def naming(state):
    return {"naming": check_naming.invoke({"declarations": state.get("scan")})}

def syntax(state):
    return {"syntax": check_syntax.invoke({"diff_text": state["diff"], "language": state.get("language", "python")})}

def review(state):
    try:
        if state.get("vs") is None:
            return {"review": review_logic.invoke({"diff_text": state["diff"], "context": []})}
        retrieved = search_similar_code(state["vs"], state["diff"])
        return {"review": review_logic.invoke({"diff_text": state["diff"], "context": [d.page_content for d in retrieved]})}
    except Exception as e:
        return {"review": review_logic.invoke({"diff_text": state["diff"], "context": []})}

def summarize(state):
    return {"summary": summarize_issues.invoke({"diff_text": state["diff"], "feedbacks": [state.get("naming"), state.get("syntax"), state.get("review")]})}


def define_langgraph():
    class ReviewState(TypedDict):
        diff: str
        language: Optional[str]
        chunks: Optional[List[Any]]
        vs: Optional[Any]
        scan: Optional[List[dict]]
        naming: Optional[dict]
        syntax: Optional[dict]
        review: Optional[dict]
        summary: Optional[dict]

    graph = StateGraph(ReviewState)

    graph.add_node("detect_language_node", detect_language)
    graph.add_node("chunk_node", chunk)
    graph.add_node("scan_node", scan)
    graph.add_node("naming_node", naming)
    graph.add_node("syntax_node", syntax)
    graph.add_node("review_node", review)
    graph.add_node("summarize_node", summarize)

    graph.set_entry_point("detect_language_node")
    graph.add_edge("detect_language_node", "chunk_node")
    graph.add_edge("chunk_node", "scan_node")
    graph.add_edge("scan_node", "naming_node")
    graph.add_edge("naming_node", "syntax_node")
    graph.add_edge("syntax_node", "review_node")
    graph.add_edge("review_node", "summarize_node")
    graph.set_finish_point("summarize_node")

    return graph.compile()