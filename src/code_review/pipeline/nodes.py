import langdetect
from typing import TypedDict, Optional, List, Any

from ..agents import NamingAgent, SyntaxAgent, LogicAgent, SummaryAgent
from ..core.tools import scan_structure
from ..core.vector_store import chunk_diff, build_vector_store, search_similar_code

# Initialize agents
naming_agent = NamingAgent()
syntax_agent = SyntaxAgent()
logic_agent = LogicAgent()
summary_agent = SummaryAgent()


class ReviewState(TypedDict):
    """State definition for the review workflow."""
    diff: str
    language: Optional[str]
    chunks: Optional[List[Any]]
    vs: Optional[Any]
    scan: Optional[List[dict]]
    naming: Optional[dict]
    syntax: Optional[dict]
    review: Optional[dict]
    summary: Optional[dict]


def detect_language(state: ReviewState) -> dict:
    """Detect the programming language of the diff."""
    try:
        language = langdetect.detect(state["diff"])
        return {"language": language}
    except Exception:
        return {"language": "python"}


def chunk(state: ReviewState) -> dict:
    """Chunk the diff and build vector store."""
    try:
        docs = chunk_diff(state["diff"])
        vs = build_vector_store(docs)
        return {"chunks": docs, "vs": vs}
    except Exception:
        return {"chunks": [], "vs": None}


def scan(state: ReviewState) -> dict:
    """Scan code structure for declarations."""
    return {"scan": scan_structure.invoke({"diff_text": state["diff"]})}


def naming(state: ReviewState) -> dict:
    """Use NamingAgent to check naming conventions."""
    declarations = state.get("scan", [])
    return {"naming": naming_agent.process(declarations)}


def syntax(state: ReviewState) -> dict:
    """Use SyntaxAgent to check syntax."""
    language = state.get("language", "python")
    return {"syntax": syntax_agent.process(state["diff"], language)}


def review(state: ReviewState) -> dict:
    """Use LogicAgent to review code logic."""
    try:
        context = []
        if state.get("vs") is not None:
            retrieved = search_similar_code(state["vs"], state["diff"])
            context = [d.page_content for d in retrieved]
        return {"review": logic_agent.process(state["diff"], context)}
    except Exception:
        return {"review": logic_agent.process(state["diff"], [])}


def summarize(state: ReviewState) -> dict:
    """Use SummaryAgent to summarize all feedback."""
    feedbacks = [state.get("naming"), state.get("syntax"), state.get("review")]
    return {"summary": summary_agent.process(state["diff"], feedbacks)}
