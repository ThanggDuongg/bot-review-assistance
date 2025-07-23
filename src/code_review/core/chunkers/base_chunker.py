import abc
import os
from typing import List, Optional
from langchain.schema import Document
from tree_sitter import Language, Parser

class BaseCodeChunker(abc.ABC):
    # Common project setup
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
    EXT = '.dll' if os.name == 'nt' else '.so'

    def __init__(self, language_name: str):
        self.language_name = language_name
        self.language_path = os.path.join(self.BUILD_DIR, f'my-languages{self.EXT}')
        self.language = None
        self._setup_language()

    def _setup_language(self):
        """Setup tree-sitter language"""
        if os.path.exists(self.language_path):
            self.language = Language(self.language_path, self.language_name)

    def get_parser(self) -> Parser:
        """Get configured parser for this language"""
        parser = Parser()
        if self.language:
            parser.set_language(self.language)
        return parser

    def get_code(self, content: str, start_line: int, end_line: int) -> str:
        """Extract code between start and end lines"""
        lines = content.splitlines()
        return '\n'.join(lines[start_line:end_line])

    def extract_node_text(self, node, content: str) -> str:
        """Extract text content from a tree-sitter node using consistent method"""
        if node is None:
            return ""

        try:
            # Use point-based extraction for consistency
            start_row, start_col = node.start_point
            end_row, end_col = node.end_point

            lines = content.split('\n')

            # Handle single line case
            if start_row == end_row:
                if start_row < len(lines):
                    return lines[start_row][start_col:end_col].strip()
                return ""

            # Handle multi-line case
            text_parts = []

            # First line (from start_col to end)
            if start_row < len(lines):
                text_parts.append(lines[start_row][start_col:])

            # Middle lines (complete lines)
            for row in range(start_row + 1, end_row):
                if row < len(lines):
                    text_parts.append(lines[row])

            # Last line (from start to end_col)
            if end_row < len(lines):
                text_parts.append(lines[end_row][:end_col])

            return '\n'.join(text_parts).strip()

        except Exception as e:
            print(f"Error extracting text from node {node.type}: {e}")
            return ""

    def find_child_by_type(self, node, child_type: str):
        """Find first child node with specific type"""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def find_identifier(self, node, content: str) -> Optional[str]:
        """Find identifier name from a node"""
        identifier_node = self.find_child_by_type(node, "identifier")
        if identifier_node:
            return self.extract_node_text(identifier_node, content)
        return None

    def create_document(self, chunk: str, file_path: str, chunk_type: str,
                        name: str, start_line: int, end_line: int,
                        diff_lines: List[int], parent: str = None,
                        **extra_metadata) -> Document:
        """Create a Document with common metadata"""
        metadata = {
            "file_path": file_path,
            "chunk_type": chunk_type,
            "name": name,
            "parent": parent,
            "start_line": start_line + 1,  # Convert to 1-indexed
            "end_line": end_line + 1,  # Convert to 1-indexed
            "diff_lines": [d for d in diff_lines if start_line + 1 <= d <= end_line + 1],
            "language": self.language_name,
            **extra_metadata
        }
        return Document(page_content=chunk, metadata=metadata)

    @abc.abstractmethod
    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
       pass