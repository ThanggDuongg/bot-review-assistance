import re
from typing import List, Tuple, Dict, Any
from langchain.schema import Document


class DiffChunker:
    def __init__(self):
        self.custom_bitbucket_file_pattern = re.compile(r"^## File: '(.+?)'$", re.MULTILINE)
        self.custom_bitbucket_line_pattern = re.compile(r'^([+\-~])\s+(\d+)\s+(.+)$', re.MULTILINE)
    
    def detect_diff_format(self, diff_text: str) -> str:
        if self.custom_bitbucket_file_pattern.search(diff_text):
            return "custom_bitbucket"
        else:
            return "plain"
    
    def extract_file_paths_custom_bitbucket(self, diff_text: str) -> List[Tuple[str, int, int]]:
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
        hunks = []

        if file_block.strip():
            hunks.append((0, len(file_block), {
                "has_line_numbers": True,
                "format": "custom_bitbucket"
            }))
        
        return hunks
    
    def extract_diff_lines_custom_bitbucket(self, hunk_content: str) -> List[int]:
        diff_lines = []
        
        for line in hunk_content.splitlines():
            match = re.match(self.custom_bitbucket_line_pattern, line)
            if match:
                status = match.group(1)  # +, -, ~
                line_number = int(match.group(2))
                
                # Only include added lines (+) in diff_lines
                if status == '+':
                    diff_lines.append(line_number)
        
        return diff_lines
    
    def chunk_diff(self, diff_text: str) -> Tuple[List[Document], List[str]]:
        documents = []
        file_paths = []
        
        diff_format = self.detect_diff_format(diff_text)

        if diff_format == "custom_bitbucket":
            file_info = self.extract_file_paths_custom_bitbucket(diff_text)
        else:
            # For plain format
            file_info = [("unknown_file", 0, len(diff_text))]

        if not file_info:
            file_info = [("unknown_file", 0, len(diff_text))]
        
        for file_path, start_pos, end_pos in file_info:
            file_block = diff_text[start_pos:end_pos]
            
            # Extract hunks
            if diff_format == "custom_bitbucket":
                hunks = self.extract_hunks_custom_bitbucket(file_block)
            else:
                hunks = []
            
            if not hunks:
                documents.append(Document(
                    page_content=file_block.strip(),
                    metadata={
                        "file_path": file_path,
                        "chunk_type": "file_diff",
                        "diff_format": diff_format
                    }
                ))
            else:
                for hunk_idx, (hunk_start, hunk_end, hunk_info) in enumerate(hunks):
                    hunk_content = file_block[hunk_start:hunk_end].strip()
                    
                    if hunk_content:
                        if diff_format == "custom_bitbucket":
                            diff_lines = self.extract_diff_lines_custom_bitbucket(hunk_content)
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
        
        return documents, file_paths