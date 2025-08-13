from typing import List, Optional, Set
from langchain.schema import Document
from .base_chunker import BaseCodeChunker


class CSharpCodeChunker(BaseCodeChunker):
    def __init__(self):
        super().__init__('c_sharp')

    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
        # TODO
        pass