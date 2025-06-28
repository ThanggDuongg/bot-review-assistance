import os
from abc import ABC, abstractmethod
from typing import Optional, Any
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import SystemMessage, HumanMessage

_cached_llm = None

def load_local_llm():
    """Load and cache the local LLM instance."""
    global _cached_llm
    if _cached_llm is not None:
        return _cached_llm

    model_path = "./models/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")

    try:
        _cached_llm = ChatLlamaCpp(
            model_path=model_path,
            n_ctx=4096,  # Context window
            n_threads=2,  # Number of CPU threads
            temperature=0.1,  # Low temperature for consistent code review
            max_tokens=512,  # Max tokens to generate
            verbose=False,  # Disable verbose logging
            stop=["</s>", "\n\n"],  # Stop sequences
        )
        return _cached_llm
    except Exception as e:
        raise RuntimeError(f"Failed to load LLM model: {str(e)}")


class BaseAgent(ABC):
    """Base class for all code review agents."""
    
    def __init__(self, llm: Optional[Any] = None):
        """Initialize the agent with an optional LLM instance."""
        self.llm = llm or load_local_llm()
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt specific to this agent."""
        pass
    
    def invoke(self, user_prompt: str) -> str:
        """Invoke the agent with a user prompt."""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, 'content') else str(response)
    
    @abstractmethod
    def process(self, **kwargs) -> dict:
        """Process the input and return structured output."""
        pass
