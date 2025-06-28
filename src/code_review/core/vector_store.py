from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import re

def chunk_diff(diff_text):
    chunk_size = 512
    chunk_overlap = 128
    pattern = re.compile(r'(def|function|class|public|private|protected)\s+[\w<>,\s\[\]]+\s+[\w_]+\s*\(.*?\)')
    method_starts = [m.start() for m in pattern.finditer(diff_text)] + [len(diff_text)]
    
    if len(method_starts) > 1:
        chunks = [diff_text[method_starts[i]:method_starts[i+1]] for i in range(len(method_starts)-1)]
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        ).create_documents(chunks)
    
    # If no methods found, use standard text chunking
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    ).create_documents([diff_text])


def build_vector_store(documents):
    if not documents:
        return None
        
    embeddings = HuggingFaceEmbeddings(model_name="models/all-MiniLM-L6-v2-Q4_K_M.gguf")
    return FAISS.from_documents(documents, embeddings)


def search_similar_code(vector_store, query, k=3):
    if vector_store is None:
        return []
    
    try:
        return vector_store.similarity_search(query, k=k)
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []
