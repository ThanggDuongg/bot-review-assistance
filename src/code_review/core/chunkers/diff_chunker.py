import re
from typing import List, Tuple, Dict, Any
from langchain.schema import Document
import os
from ..utils import Utils

# Debug mode flag
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

class DiffChunker:
    def __init__(self):
        # Custom Bitbucket patterns (with line numbers)
        self.custom_bitbucket_file_pattern = re.compile(r"^## File: '(.+?)'$", re.MULTILINE)
        self.custom_bitbucket_line_pattern = re.compile(r'^([+\-~])\s+(\d+)\s+(.+)$', re.MULTILINE)
    
    def detect_diff_format(self, diff_text: str) -> str:
        if self.custom_bitbucket_file_pattern.search(diff_text):
            return "custom_bitbucket"
        else:
            return "plain"
    
    def extract_file_paths_custom_bitbucket(self, diff_text: str) -> List[Tuple[str, int, int]]:
        """Extract file paths for custom Bitbucket format with line numbers"""
        file_info = []
        for match in self.custom_bitbucket_file_pattern.finditer(diff_text):
            file_path = match.group(1)
            start_pos = match.start()
            file_info.append((file_path, start_pos))
        
        # Add end positions
        for i in range(len(file_info)):
            start_pos = file_info[i][1]
            end_pos = file_info[i + 1][1] if i + 1 < len(file_info) else len(diff_text)
            file_info[i] = (file_info[i][0], start_pos, end_pos)
        
        return file_info
    
    @staticmethod
    def extract_hunks_custom_bitbucket(file_block: str) -> List[Tuple[int, int, Dict[str, Any]]]:
        """Extract hunks for custom Bitbucket format (no @@ headers, just line-by-line)"""
        hunks = []
        
        # For custom Bitbucket format, treat entire file block as one hunk
        # since there are no @@ headers to split on
        if file_block.strip():
            hunks.append((0, len(file_block), {
                "has_line_numbers": True,
                "format": "custom_bitbucket"
            }))
        
        return hunks
    
    def extract_diff_lines_custom_bitbucket(self, hunk_content: str, hunk_info: Dict[str, Any]) -> List[int]:
        """Extract diff lines for custom Bitbucket format with line numbers"""
        diff_lines = []
        
        for line in hunk_content.splitlines():
            # Ex: + 15 public class UserService {
            match = re.match(self.custom_bitbucket_line_pattern, line)
            if match:
                status = match.group(1)  # +, -, or ~
                line_number = int(match.group(2))  # Actual file line number
                content = match.group(3)
                
                # Only include added lines (+) in diff_lines
                if status == '+':
                    diff_lines.append(line_number)
        
        return diff_lines
    
    def chunk_diff(self, diff_text: str) -> Tuple[List[Document], List[str]]:
        if DEBUG_MODE:
            Utils.debug_print("[DEBUG] chunk_diff input:\n", diff_text[:1000], "...\n---END---")
        
        documents = []
        file_paths = []
        
        # Detect diff format
        diff_format = self.detect_diff_format(diff_text)
        if DEBUG_MODE:
            Utils.debug_print(f"[DEBUG] Detected diff format: {diff_format}")
        
        # Extract file information
        if diff_format == "custom_bitbucket":
            file_info = self.extract_file_paths_custom_bitbucket(diff_text)
        else:
            # Fallback for plain format
            file_info = [("unknown_file", 0, len(diff_text))]
        
        if DEBUG_MODE:
            Utils.debug_print(f"[DEBUG] Found {len(file_info)} file matches in diff.")
        
        # If no files detected, treat entire diff as one file
        if not file_info:
            file_info = [("unknown_file", 0, len(diff_text))]
        
        # Process each file
        for file_path, start_pos, end_pos in file_info:
            file_block = diff_text[start_pos:end_pos]
            
            # Extract hunks (only custom bitbucket supported)
            if diff_format == "custom_bitbucket":
                hunks = self.extract_hunks_custom_bitbucket(file_block)
            else:
                hunks = []
            
            if not hunks:
                # If no hunks, create one document for entire file
                documents.append(Document(
                    page_content=file_block.strip(),
                    metadata={
                        "file_path": file_path,
                        "chunk_type": "file_diff",
                        "diff_format": diff_format
                    }
                ))
            else:
                # Create document for each hunk
                for hunk_idx, (hunk_start, hunk_end, hunk_info) in enumerate(hunks):
                    hunk_content = file_block[hunk_start:hunk_end].strip()
                    
                    if hunk_content:
                        if diff_format == "custom_bitbucket":
                            diff_lines = self.extract_diff_lines_custom_bitbucket(hunk_content, hunk_info)
                        else:
                            diff_lines = []
                        
                        documents.append(Document(
                            page_content=hunk_content,
                            metadata={
                                "file_path": file_path,
                                "chunk_type": "hunk_diff",
                                "hunk_index": hunk_idx,
                                "diff_format": diff_format,
                                "diff_lines": diff_lines,
                                "has_line_numbers": hunk_info.get("has_line_numbers", False)
                            }
                        ))
            
            file_paths.append(file_path)
        
        Utils.debug_print(f"[DEBUG] chunk_diff: Total file_paths: {file_paths}")
        Utils.debug_print(f"[DEBUG] chunk_diff: Total documents: {len(documents)}")
        
        return documents, file_paths