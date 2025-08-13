from langchain_community.embeddings import LlamaCppEmbeddings
import streamlit as st
import numpy as np
import json
import os
from typing import List, Dict

from .utils import Utils
from src.code_review.core.chunkers import get_diff_chunker

# Cache for embedding model
_cached_embeddings = None

def chunk_diff(diff_text: str):
    return get_diff_chunker().chunk_diff(diff_text)

@st.cache_resource
def load_embedding_model():
    global _cached_embeddings
    if _cached_embeddings is not None:
        return _cached_embeddings

    embedding_model_path = os.getenv("EMBEDDING_MODEL_PATH", "./models/embedding.gguf")
    try:
        # Get optimal thread count based on CPU cores
        default_threads = int(os.getenv("EMBEDDING_N_THREADS", "8"))
        optimal_threads = Utils.get_optimal_thread_count(default_threads)
        
        _cached_embeddings = LlamaCppEmbeddings(
            model_path=embedding_model_path,
            n_ctx=int(os.getenv("EMBEDDING_N_CTX", "256")),  # Context window for embeddings
            n_threads=optimal_threads,  # Optimized thread count based on CPU cores
            n_batch=int(os.getenv("EMBEDDING_N_BATCH", "256")),  # Batch size for throughput
            n_gpu_layers=0,  # Number of model layers to offload to GPU (set > 0 if using GPU)
            n_parts=-1,  # Number of model parts to split into (default -1 means auto)
            seed=42,  # Random seed for reproducibility (use -1 for random behavior)
            f16_kv=True,  # Use 16-bit key/value cache if supported (saves memory)
            logits_all=False,  # Whether to return logits for all tokens (not needed for embedding)
            vocab_only=False,  # Load only vocabulary without weights (False = load full model)
            use_mlock=True,  # Lock the model in RAM to prevent swapping
            device=None,  # Device override (None = auto-select, can set 'cpu' or 'cuda')
            verbose=False,  # Disable verbose logs
        )
        Utils.debug_print(f"Loaded embedding model: {embedding_model_path}")
        return _cached_embeddings
    except Exception as e:
        Utils.debug_print(f"Failed to load GGUF embedding model: {e}")
        return None

def search_best_practices_by_embedding(query_embedding, top_n=3, best_practices_path=None):
    if best_practices_path is None:
        candidates = [
            os.path.join('data', 'best_practices.json'),
            os.path.join(os.path.dirname(__file__), '../../../data/best_practices.json'),
        ]
        for path in candidates:
            if os.path.exists(path):
                best_practices_path = path
                break
        else:
            raise FileNotFoundError("Could not find best_practices.json")

    with open(best_practices_path, 'r', encoding='utf-8') as f:
        best_practices = json.load(f)

    query_vec = np.array(query_embedding, dtype=np.float32)
    results = []
    for bp in best_practices:
        bp_embedding = np.array(bp.get('embedding', []), dtype=np.float32)
        if bp_embedding.shape != query_vec.shape or bp_embedding.size == 0:
            continue
        # Cosine similarity
        sim = np.dot(query_vec, bp_embedding) / (np.linalg.norm(query_vec) * np.linalg.norm(bp_embedding) + 1e-8)
        results.append({
            **{k: v for k, v in bp.items() if k != 'embedding'},
            'similarity': float(sim)
        })
    # Sort by similarity descending
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_n]

def embed_text(text: str) -> List[float]:
    embeddings = load_embedding_model()
    if embeddings is None:
        return []
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        Utils.debug_print(f"Failed to embed text: {e}")
        return []

def get_relevant_best_practices_for_chunk(chunk_content: str, max_top_n: int = 3) -> List[Dict]:
    if not chunk_content.strip():
        Utils.debug_print("get_relevant_best_practices_for_chunk: Empty chunk content")
        return []
    
    # Embed chunk content
    chunk_embedding = embed_text(chunk_content)
    if not chunk_embedding:
        Utils.debug_print("get_relevant_best_practices_for_chunk: Failed to embed chunk content")
        return []

    candidates = search_best_practices_by_embedding(chunk_embedding, top_n=max_top_n + 2)

    if not candidates:
        Utils.debug_print("get_relevant_best_practices_for_chunk: No candidates found")
        return []

    highest_similarity = candidates[0]['similarity']

    if highest_similarity < 0.3:
        # Low relevance: return only top 1 if similarity is reasonable
        if highest_similarity >= 0.1:
            return candidates[:1]
        else:
            return []  # Too low relevance, don't inject anything
    
    elif highest_similarity >= 0.6:
        # High relevance: return up to max_top_n
        return candidates[:max_top_n]
    
    else:
        # Medium relevance (0.3-0.6): return up to 2
        return candidates[:2]

def format_best_practices_for_prompt(best_practices: List[Dict]) -> str:
    if not best_practices:
        return "No specific best practices identified for this code section. Focus on general code quality, performance, and security issues."
    
    lines = ["RELEVANT BEST PRACTICES FOR THIS CODE SECTION:"]
    for idx, bp in enumerate(best_practices, 1):
        lines.append(f"{idx}. [{bp.get('id', 'unknown')}] {bp.get('title', 'Unknown')} (Severity: {bp.get('severity', 'Medium')})")
        if bp.get('description'):
            lines.append(f"   - {bp.get('description')}")
        if bp.get('example_violation'):
            lines.append(f"   - Example violation: {bp.get('example_violation')}")
        lines.append("")  # Empty line for readability
    
    return "\n".join(lines)
