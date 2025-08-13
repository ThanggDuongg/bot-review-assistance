import os
from abc import ABC, abstractmethod
from typing import Optional, Any
from langchain_core.messages import SystemMessage, HumanMessage
import streamlit as st

from src.code_review.agents import APIClient
from src.code_review.core import Utils

_cached_llms = {}

def get_common_config():
    return dict(
        max_tokens=1024,
        stop=[
            "</s>",
            "<|end|>",
            "<|endoftext|>",
            # Invalid JSON patterns
            "}\n{",  # Multiple JSON objects
            "}}\n",  # Double closing braces
            "},\n  ]",
            "},\n}",
            "Human:",
            "Assistant:",
            "User:",
            "AI:",
            "INSTRUCTIONS:",
            "CRITICAL:",
            "REQUIRED:",
            "FORBIDDEN:",
            "\n\nLooking at",  # Prevents re-analysis
            "\n\nExamining",  # Prevents re-examination
            "\n\nAnalyzing",  # Prevents re-analyzing
        ]
    )

def get_llamacpp_config():
    common = get_common_config()
    n_gpu_layers = Utils.detect_gpu_vram_and_layers()
    Utils.debug_print(f"Detected GPU layers: {n_gpu_layers}")
    
    default_threads = int(os.getenv("EMBEDDING_N_THREADS", "8"))
    optimal_threads = Utils.get_optimal_thread_count(default_threads)

    return {
        **common,
        "n_ctx": 4096,
        "n_threads": optimal_threads,
        "n_batch": 128,
        "n_gpu_layers": n_gpu_layers,
        "f16_kv": False,  # Use 16-bit float -> quickly on CPU
        "use_mlock": True,
        "seed": 42,  # Deterministic
        "repeat_penalty": 1.4,
        "top_k": 15,  # Focused vocabulary
        "top_p": 0.9,  # Less creativity
    }

def get_ollama_config():
    common = get_common_config()
    default_threads = int(os.getenv("EMBEDDING_N_THREADS", "8"))
    optimal_threads = Utils.get_optimal_thread_count(default_threads)
    
    return {
        **common,
        "num_predict": common["max_tokens"],  # Ollama equivalent
        "num_ctx": 4096,
        "num_thread": optimal_threads,
        "temperature": 0.05
    }

def get_azure_openai_config():
    """Config cho Azure OpenAI"""
    common = get_common_config()
    return {
        **common,
        "temperature": 0.05,
        "max_tokens": common["max_tokens"],
        "timeout": None,
        "max_retries": 2
    }

@st.cache_resource
def load_local_llm(instance_name="default"):
    global _cached_llms
    if instance_name in _cached_llms:
        return _cached_llms[instance_name]

    model_path = os.getenv("MODEL_PATH", "./models/main.gguf")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    config = get_llamacpp_config()
    try:
        from langchain_community.chat_models import ChatLlamaCpp

        llm_instance = ChatLlamaCpp(
            model_path=model_path,
            n_ctx=config['n_ctx'],
            n_threads=Utils.get_optimal_thread_count(config['n_threads']),
            n_batch=config['n_batch'],
            max_tokens=config['max_tokens'],
            temperature=0.05,
            verbose=False,
            stop=config['stop'],
            f16_kv=config['f16_kv'],
            use_mlock=config['use_mlock'],
            n_gpu_layers=config['n_gpu_layers'],
            seed=config['seed'],
            repeat_penalty=config['repeat_penalty'],
            top_k=config['top_k'],
            top_p=config['top_p'],
        )
        _cached_llms[instance_name] = llm_instance
        return llm_instance
    except Exception as e:
        raise RuntimeError(f"Failed to load LLM model instance '{instance_name}': {str(e)}")

@st.cache_resource
def load_ollama_llm(instance_name: str = "default"):
    global _cached_llms
    base_url = os.getenv("AI_URL", "")
    model = os.getenv("API_MODEL", "codellama:7b")
    cache_key = f"ollama::{base_url}::{model}::{instance_name}"
    if cache_key in _cached_llms:
        return _cached_llms[cache_key]
    try:
        from langchain_ollama import ChatOllama
        config = get_ollama_config()

        llm_instance = ChatOllama(
            base_url=base_url,
            model=model,
            **config
        )
        _cached_llms[cache_key] = llm_instance
        return llm_instance
    except Exception as e:
        raise RuntimeError(f"Failed to load Ollama LLM instance '{cache_key}': {str(e)}")

@st.cache_resource
def load_azure_openai_llm(instance_name: str = "default"):
    raise RuntimeError(f"Not Supported")

class BaseAgent(ABC):
    """Base class for all code review agents."""
    
    def __init__(self, agent_type: str = "default", llm: Optional[Any] = None):
        self.agent_type = agent_type
        self.use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        self.use_azure_openai = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"
        self.use_api = os.getenv("USE_API_LLM", "false").lower() == "true"

        if self.use_ollama:
            self.api_client = None
            self.llm = llm or load_ollama_llm("default")
            Utils.debug_print(f"[DEBUG] Agent '{self.agent_type}' using Ollama server")
        elif self.use_azure_openai:
            self.api_client = None
            self.llm = llm or load_azure_openai_llm("default")
            Utils.debug_print(f"[DEBUG] Agent '{self.agent_type}' using Azure OpenAI")
        elif self.use_api:
            self.api_client = APIClient()
            self.llm = None
            Utils.debug_print(f"[DEBUG] Agent '{self.agent_type}' using API backend")
        else:
            self.api_client = None
            self.llm = llm or load_local_llm("default")
            Utils.debug_print(f"[DEBUG] Agent '{self.agent_type}' using local GGUF model")
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt specific to this agent."""
        pass
    
    def invoke(self, user_prompt: str) -> str:
        """Invoke the agent with a user prompt."""
        try:
            if self.use_api:
                result = self.api_client.invoke_api(self.system_prompt, user_prompt)
            else:
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_prompt)
                ]
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
