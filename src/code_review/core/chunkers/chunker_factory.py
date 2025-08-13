from .csharp_chunker import CSharpCodeChunker
from .base_chunker import BaseCodeChunker
from typing import Optional
from .diff_chunker import DiffChunker
from ..utils import Utils

# Cache for chunker instances
_context_chunker_cache = {}
_diff_chunker_cache = None

def get_diff_chunker() -> DiffChunker:
    global _diff_chunker_cache
    if _diff_chunker_cache is None:
        _diff_chunker_cache = DiffChunker()
    return _diff_chunker_cache

def get_context_chunker(file_path: str) -> Optional[BaseCodeChunker]:
    if not Utils.is_valid_code_file(file_path):
        return None

    file_type = Utils.detect_code_type(file_path)

    if not file_type or file_type == 'unknown':
        return None

    if file_type in _context_chunker_cache:
        return _context_chunker_cache[file_type]

    chunker = None
    if file_type == 'csharp':
        chunker = CSharpCodeChunker()

    if chunker:
        _context_chunker_cache[file_type] = chunker

    return chunker 