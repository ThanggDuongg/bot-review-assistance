from typing import List, Dict
from .base import BaseAgent
from langchain.schema import Document


class LogicAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__("logic", llm)

    @property
    def system_prompt(self) -> str:
        return """
        You are a Code Analysis Expert. Analyze pull request changes with focus on:
        """

    def process(self, chunk_docs: List[Document]) -> Dict[str, dict]:
        return {}