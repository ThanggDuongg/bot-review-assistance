import json
from typing import List, Dict, Any
from .base import BaseAgent


class SummaryAgent(BaseAgent):
    """Agent specialized in summarizing review results."""
    
    @property
    def system_prompt(self) -> str:
        return """You are a specialized code review agent as well as programming expert focused on synthesizing and summarizing review feedback. Your expertise includes:

- Analyzing pull request changes and understanding their purpose
- Synthesizing feedback from multiple review agents
- Identifying the most critical issues and priorities
- Providing clear, actionable summaries
- Evaluating overall code quality and implementation approach
- Communicating technical feedback in accessible language

Guidelines:
- Provide natural language summaries, not JSON
- Start with the main purpose of the PR
- Highlight critical issues first, then minor ones
- Be constructive and solution-oriented
- Consider the bigger picture and architectural implications
- Balance technical accuracy with readability

Your goal is to provide developers with clear, prioritized feedback they can act on."""

    def process(self, diff_text: str, feedbacks: List[Any]) -> Dict[str, Any]:
        """Process and summarize all review feedback."""
        extracted_summaries = [f.get("summary") if isinstance(f, dict) else str(f) for f in feedbacks if f]

        user_prompt = f"""Analyze the following pull request diff and summarize:
1. What the PR is trying to do (its main purpose).
2. Provide a high-level evaluation: is the implementation clear? any smells?
3. Then summarize the individual review feedbacks below.

Respond with a natural language paragraph.

[DIFF]
{diff_text}

[FEEDBACKS]
{json.dumps(extracted_summaries, indent=2)}"""

        try:
            summary_text = self.invoke(user_prompt).strip()
            return {
                "summary": summary_text,
                "details": extracted_summaries
            }
        except Exception as e:
            return {
                "summary": f"Failed to summarize issues: {str(e)}",
                "details": extracted_summaries
            }
