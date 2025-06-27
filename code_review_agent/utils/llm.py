import os
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import SystemMessage, HumanMessage

_cached_llm = None

def load_local_llm():
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
            # Use chat format for better system prompt support
            chat_format="chatml"  # Generic chat format that works well with most models
        )
        return _cached_llm
    except Exception as e:
        raise RuntimeError(f"Failed to load LLM model: {str(e)}")

def invoke_with_system_prompt(llm, system_prompt: str, user_prompt: str) -> str:
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = llm.invoke(messages)
    return response.content if hasattr(response, 'content') else str(response)