import re
from typing import List, Tuple, Dict, Any
from langchain.schema import Document
import os
from ..utils import Utils

# Debug mode flag
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

class DiffChunker:
    def __init__(self):
        # Git diff patterns
        self.git_file_pattern = re.compile(r"^diff --git a/(.*?) b/", re.MULTILINE)
        self.git_hunk_pattern = re.compile(r'^@@\s+-(\d+),?(\d+)?\s+\+(\d+),?(\d+)?\s+@@', re.MULTILINE)
        
        # Bitbucket diff patterns  
        self.bitbucket_file_pattern = re.compile(r"^### File: '(.+?)'$", re.MULTILINE)
        self.bitbucket_hunk_pattern = re.compile(r'^@@.*$', re.MULTILINE)
        
        # Custom Bitbucket patterns (with line numbers)
        self.custom_bitbucket_file_pattern = re.compile(r"^## File: '(.+?)'$", re.MULTILINE)
        self.custom_bitbucket_line_pattern = re.compile(r'^([+\-~])\s+(\d+)\s+(.+)$', re.MULTILINE)
        
        # Generic hunk pattern for any @@ line
        self.generic_hunk_pattern = re.compile(r'^@@.*$', re.MULTILINE)
        
        # Generic file separation patterns
        self.generic_file_separators = [
            re.compile(r"^### File: '(.+?)'$", re.MULTILINE),
            re.compile(r"^--- (.+?)$", re.MULTILINE),
            re.compile(r"^\+\+\+ (.+?)$", re.MULTILINE),
        ]
    
    def detect_diff_format(self, diff_text: str) -> str:
        if self.git_file_pattern.search(diff_text):
            return "git"
        elif self.custom_bitbucket_file_pattern.search(diff_text):
            return "custom_bitbucket"
        elif self.bitbucket_file_pattern.search(diff_text):
            return "bitbucket"
        else:
            # Check if there are any @@ hunks at all
            if self.generic_hunk_pattern.search(diff_text):
                return "generic"
            else:
                return "plain"
    
    def extract_file_paths_git(self, diff_text: str) -> List[Tuple[str, int, int]]:
        file_info = []
        for match in self.git_file_pattern.finditer(diff_text):
            file_path = match.group(1)
            start_pos = match.start()
            file_info.append((file_path, start_pos))
        
        # Add end positions
        for i in range(len(file_info)):
            start_pos = file_info[i][1]
            end_pos = file_info[i + 1][1] if i + 1 < len(file_info) else len(diff_text)
            file_info[i] = (file_info[i][0], start_pos, end_pos)
        
        return file_info
    
    def extract_file_paths_bitbucket(self, diff_text: str) -> List[Tuple[str, int, int]]:
        file_info = []
        for match in self.bitbucket_file_pattern.finditer(diff_text):
            file_path = match.group(1)
            start_pos = match.start()
            file_info.append((file_path, start_pos))
        
        # Add end positions
        for i in range(len(file_info)):
            start_pos = file_info[i][1]
            end_pos = file_info[i + 1][1] if i + 1 < len(file_info) else len(diff_text)
            file_info[i] = (file_info[i][0], start_pos, end_pos)
        
        return file_info
    
    def extract_file_paths_generic(self, diff_text: str) -> List[Tuple[str, int, int]]:
        """Extract file paths using multiple generic patterns"""
        file_info = []
        
        # Try different file separator patterns
        for pattern in self.generic_file_separators:
            matches = list(pattern.finditer(diff_text))
            if matches:
                for match in matches:
                    file_path = match.group(1)
                    start_pos = match.start()
                    
                    # Avoid duplicates
                    if not any(fp == file_path for fp, _, _ in file_info):
                        file_info.append((file_path, start_pos))
                break
        
        # If no file separators found, treat entire diff as one file
        if not file_info:
            file_info = [("unknown_file", 0)]
        
        # Add end positions
        for i in range(len(file_info)):
            start_pos = file_info[i][1]
            end_pos = file_info[i + 1][1] if i + 1 < len(file_info) else len(diff_text)
            file_info[i] = (file_info[i][0], start_pos, end_pos)
        
        return file_info
    
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
    
    def extract_hunks_git(self, file_block: str) -> List[Tuple[int, int, Dict[str, Any]]]:
        hunks = []
        for match in self.git_hunk_pattern.finditer(file_block):
            hunk_start = match.end()
            # Find the next hunk or end of the file
            next_match = self.git_hunk_pattern.search(file_block, hunk_start)
            hunk_end = next_match.start() if next_match else len(file_block)
            
            # Parse line numbers from hunk header
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1
            
            hunks.append((hunk_start, hunk_end, {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "has_line_numbers": True
            }))
        
        return hunks
    
    def extract_hunks_generic(self, file_block: str) -> List[Tuple[int, int, Dict[str, Any]]]:
        """Extract hunks using generic @@ pattern"""
        hunks = []
        for match in self.generic_hunk_pattern.finditer(file_block):
            hunk_start = match.end()
            # Find next hunk or end of file
            next_match = self.generic_hunk_pattern.search(file_block, hunk_start)
            hunk_end = next_match.start() if next_match else len(file_block)
            
            # Try to parse line numbers from hunk header if possible
            hunk_header = match.group(0)
            line_info = self.parse_hunk_header(hunk_header)
            
            hunks.append((hunk_start, hunk_end, line_info))
        
        return hunks
    
    def parse_hunk_header(self, hunk_header: str) -> Dict[str, Any]:
        """Parse hunk header to extract line number information"""
        # Try to match git-style hunk header
        git_match = re.match(self.git_hunk_pattern, hunk_header)
        if git_match:
            old_start = int(git_match.group(1))
            old_count = int(git_match.group(2)) if git_match.group(2) else 1
            new_start = int(git_match.group(3))
            new_count = int(git_match.group(4)) if git_match.group(4) else 1
            return {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "has_line_numbers": True
            }
        
        # If can't parse, return generic info
        return {"has_line_numbers": False}
    
    def extract_hunks_bitbucket(self, file_block: str) -> List[Tuple[int, int, Dict[str, Any]]]:
        hunks = []
        for match in self.bitbucket_hunk_pattern.finditer(file_block):
            hunk_start = match.end()
            # Find next hunk or end of file
            next_match = self.bitbucket_hunk_pattern.search(file_block, hunk_start)
            hunk_end = next_match.start() if next_match else len(file_block)
            
            # Try to parse line numbers from hunk header
            hunk_header = match.group(0)
            line_info = self.parse_hunk_header(hunk_header)
            
            hunks.append((hunk_start, hunk_end, line_info))
        
        return hunks
    
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
    
    @staticmethod
    def extract_diff_lines_git(hunk_content: str, hunk_info: Dict[str, Any]) -> List[int]:
        diff_lines = []
        if not hunk_info.get("has_line_numbers"):
            return diff_lines
        
        new_start = hunk_info["new_start"]
        new_line_num = new_start
        
        for line in hunk_content.splitlines():
            if line.startswith('@@'):
                break
            if line.startswith('+') and not line.startswith('+++'):
                diff_lines.append(new_line_num)
                new_line_num += 1
            elif line.startswith('-') and not line.startswith('---'):
                continue
            else:
                new_line_num += 1
        
        return diff_lines
    
    @staticmethod
    def extract_diff_lines_generic(hunk_content: str, hunk_info: Dict[str, Any]) -> List[int]:
        """Extract diff lines for generic format"""
        diff_lines = []
        
        if hunk_info.get("has_line_numbers"):
            # Use git-style extraction if we have line numbers
            return DiffChunker.extract_diff_lines_git(hunk_content, hunk_info)
        
        # Otherwise, use approximate line numbers
        for i, line in enumerate(hunk_content.splitlines()):
            if line.startswith('@@'):
                continue
            if line.startswith('+') and not line.startswith('+++'):
                diff_lines.append(i + 1)  # Approximate line number
        
        return diff_lines

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
        
        # Extract file information based on format
        if diff_format == "git":
            file_info = self.extract_file_paths_git(diff_text)
        elif diff_format == "bitbucket":
            file_info = self.extract_file_paths_bitbucket(diff_text)
        elif diff_format == "generic":
            file_info = self.extract_file_paths_generic(diff_text)
        elif diff_format == "custom_bitbucket":
            file_info = self.extract_file_paths_custom_bitbucket(diff_text)
        else:  # plain format
            file_info = [("unknown_file", 0, len(diff_text))]
        
        if DEBUG_MODE:
            Utils.debug_print(f"[DEBUG] Found {len(file_info)} file matches in diff.")
        
        # If no files detected, treat entire diff as one file
        if not file_info:
            file_info = [("unknown_file", 0, len(diff_text))]
        
        # Process each file
        for file_path, start_pos, end_pos in file_info:
            file_block = diff_text[start_pos:end_pos]
            
            # Extract hunks based on format
            if diff_format == "git":
                hunks = self.extract_hunks_git(file_block)
            elif diff_format == "bitbucket":
                hunks = self.extract_hunks_bitbucket(file_block)
            elif diff_format == "generic":
                hunks = self.extract_hunks_generic(file_block)
            elif diff_format == "custom_bitbucket":
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
                        # Extract diff lines based on format
                        if diff_format == "git":
                            diff_lines = self.extract_diff_lines_git(hunk_content, hunk_info)
                        elif diff_format == "custom_bitbucket":
                            diff_lines = self.extract_diff_lines_custom_bitbucket(hunk_content, hunk_info)
                        else:
                            diff_lines = self.extract_diff_lines_generic(hunk_content, hunk_info)
                        
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