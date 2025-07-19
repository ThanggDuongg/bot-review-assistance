import os
from abc import ABC, abstractmethod
from typing import Optional, Any
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import SystemMessage, HumanMessage
import streamlit as st

from src.code_review.core import Utils

_cached_llms = {}

def get_llm_config(model_path):
    n_gpu_layers = Utils.detect_gpu_vram_and_layers()
    Utils.debug_print(f"Detected GPU layers: {n_gpu_layers}")

    default_threads = int(os.getenv("EMBEDDING_N_THREADS", "8"))
    optimal_threads = Utils.get_optimal_thread_count(default_threads)
    return dict(
        n_ctx=8192,  # Reduced context window for faster processing
        n_threads=optimal_threads,  # Increased threads for better CPU utilization
        n_batch=1024,  # Increased batch size for better throughput
        max_tokens=3072,  # Increased max tokens for comprehensive responses
        n_gpu_layers=n_gpu_layers,  # Dynamically set GPU layers
    )

@st.cache_resource
def load_local_llm(instance_name="default"):
    global _cached_llms
    if instance_name in _cached_llms:
        return _cached_llms[instance_name]
    model_path = os.getenv("MODEL_PATH", "./models/Qwen2.5-Coder-7B-Instruct-Q6_K.gguf")
    Utils.debug_print(f"Loading LLM model instance '{instance_name}' from {model_path}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    config = get_llm_config(model_path)
    try:
        llm_instance = ChatLlamaCpp(
            model_path=model_path,
            n_ctx=config['n_ctx'],
            n_threads=Utils.get_optimal_thread_count(config['n_threads']),
            n_batch=config['n_batch'],
            max_tokens=config['max_tokens'],
            temperature=0.1,
            verbose=False,
            stop=["</s>", "\n\n"],
            f16_kv=True,
            use_mlock=True,
            n_gpu_layers=config['n_gpu_layers'],  # Use detected value
            seed=42,
            repeat_penalty=1.1,
            top_k=40,
            top_p=0.9,
        )
        _cached_llms[instance_name] = llm_instance
        Utils.debug_print(f"Loaded and cached LLM instance '{instance_name}'")
        return llm_instance
    except Exception as e:
        raise RuntimeError(f"Failed to load LLM model instance '{instance_name}': {str(e)}")


class BaseAgent(ABC):
    """Base class for all code review agents."""
    
    def __init__(self, agent_type: str = "default", llm: Optional[Any] = None):
        self.agent_type = agent_type
        self.llm = llm or self._get_llm_instance()
    
    def _get_llm_instance(self):
        Utils.debug_print(f"Using shared LLM instance for agent type: {self.agent_type}")
        return load_local_llm("default")
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt specific to this agent."""
        pass
    
    def invoke(self, user_prompt: str) -> str:
        """Invoke the agent with a user prompt."""
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt)
            ]

            Utils.debug_print(f"[DEBUG] Invoking LLM with {len(user_prompt)} chars...")

            response = self.llm.invoke(messages)
            result = response.content if hasattr(response, 'content') else str(response)

            Utils.debug_print(f"[DEBUG] LLM response length: {len(result)} chars")

            return result
        except Exception as e:
            Utils.debug_print(f"[DEBUG] LLM invoke error: {e}")
            raise
    
    @abstractmethod
    def process(self, **kwargs) -> dict:
        """Process the input and return structured output."""
        pass
