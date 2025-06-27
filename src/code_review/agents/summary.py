import json
import os
from typing import List, Dict, Any
from langchain.schema import Document
from .base import BaseAgent
from ..core import Utils


class SummaryAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__("summary", llm)
        self.max_group_size = int(os.getenv("SUMMARY_MAX_GROUP_SIZE", "8000"))
        self.size_threshold = int(os.getenv("SUMMARY_SIZE_THRESHOLD", "15000"))
        self.chars_per_token = int(os.getenv("SUMMARY_CHARS_PER_TOKEN", "4"))
    
    @property
    def system_prompt(self) -> str:
        return """
You are a Code Analysis Expert specializing in analyzing pull request changes using DeepSeek Coder's capabilities.

Your expertise:
- Deep understanding of code structure and patterns
- Ability to identify technical implementation details
- Structured analysis of code changes across different layers (frontend/backend)
- Clear categorization of changes by type and impact

Your task is to:
1. Analyze code changes at chunk, file, and project level
2. Identify the technical purpose and implementation details
3. Categorize changes by frontend/backend impact
4. Assess business and technical implications
5. Provide structured JSON output with specific fields

Focus on:
- Technical accuracy and code-specific insights
- Structured categorization rather than narrative flow
- Precise identification of code patterns and dependencies
- Clear separation of concerns (frontend vs backend vs business logic)

Output format: Always return valid JSON with the specified fields.
        """

    def process(self, chunk_docs: List[Document]) -> Dict[str, dict]:
        Utils.debug_print(f"[DEBUG] Processing {len(chunk_docs)} chunk documents...")
        
        if not chunk_docs:
            Utils.debug_print("[DEBUG] No chunks provided")
            return {"summary": self._create_empty_summary()}
        
        # Group chunks by file
        file_contents = self._group_chunks_by_file(chunk_docs)
        
        Utils.debug_print(f"[DEBUG] Grouped into {len(file_contents)} files")
        
        # Analyze based on content size
        pr_summary = self._analyze_files_smart(file_contents)
        
        Utils.debug_print(f"[DEBUG] PR summary: {pr_summary}")
        
        return {"summary": pr_summary}

    @staticmethod
    def _group_chunks_by_file(chunk_docs: List[Document]) -> Dict[str, List[str]]:
        file_contents = {}
        for doc in chunk_docs:
            file_path = doc.metadata.get("file_path", "unknown")
            if file_path not in file_contents:
                file_contents[file_path] = []
            file_contents[file_path].append(doc.page_content)
        return file_contents

    def _analyze_files_smart(self, file_contents: Dict[str, List[str]]) -> dict:
        # Calculate total content size
        total_size = self._calculate_total_size(file_contents)
        estimated_tokens = Utils.estimate_tokens(total_size, self.chars_per_token)
        
        Utils.debug_print(f"[DEBUG] Total content size: {total_size} chars, estimated tokens: {estimated_tokens}")
        
        # Check for mixed languages
        extensions = set(Utils.extract_file_extension(fp).lower() for fp in file_contents.keys())
        has_mixed_languages = len(extensions) > 2
        
        Utils.debug_print(f"[DEBUG] File extensions: {extensions}")
        Utils.debug_print(f"[DEBUG] Has mixed languages: {has_mixed_languages}")
        
        # Strategy based on size AND language diversity
        if total_size > self.size_threshold or has_mixed_languages:
            Utils.debug_print(f"[DEBUG] Using hybrid grouping (size: {total_size > self.size_threshold}, mixed: {has_mixed_languages})")
            return self._analyze_with_hybrid_grouping(file_contents)
        else:
            Utils.debug_print(f"[DEBUG] Content size OK and single language, using single call")
            return self._analyze_single_call(file_contents)

    @staticmethod
    def _calculate_total_size(file_contents: Dict[str, List[str]]) -> int:
        """Calculate total content size in characters."""
        total_size = 0
        for file_path, contents in file_contents.items():
            file_content = "\n".join(contents)
            total_size += Utils.calculate_content_size(file_content)
        return total_size

    def _analyze_single_call(self, file_contents: Dict[str, List[str]]) -> dict:
        # Combined content
        combined_content = self._prepare_combined_content(file_contents)

        user_prompt = self._create_analysis_prompt(combined_content, list(file_contents.keys()))
        try:
            Utils.debug_print(f"[DEBUG] Analyzing {len(file_contents)} files in single call")
            
            result = self.invoke(user_prompt).strip()
            parsed_result = Utils.parse_json_from_response(result)
            
            if parsed_result:
                Utils.debug_print(f"[DEBUG] Successfully analyzed all files in single call")
                return parsed_result
            else:
                Utils.debug_print(f"[DEBUG] Failed to parse JSON for combined analysis")
                return self._create_error_summary("JSON parsing failed")
                
        except Exception as e:
            Utils.debug_print(f"[DEBUG] Failed to analyze files in single call: {e}")
            return self._create_error_summary("Processing failed")

    def _analyze_with_hybrid_grouping(self, file_contents: Dict[str, List[str]]) -> dict:
        # Group by extension
        extension_groups = self._group_by_extension(file_contents)
        
        Utils.debug_print(f"[DEBUG] Created {len(extension_groups)} extension groups")
        
        # Split large extension groups by size
        final_groups = []
        for group in extension_groups:
            group_size = self._calculate_group_size(group)
            
            if group_size > self.max_group_size:
                Utils.debug_print(f"[DEBUG] Splitting large group ({group_size} chars) by size")
                # Split large group by size
                size_groups = self._split_group_by_size(group)
                final_groups.extend(size_groups)
            else:
                final_groups.append(group)
        
        Utils.debug_print(f"[DEBUG] Final groups: {len(final_groups)}")
        
        # Analyze each group
        group_summaries = []
        for i, group in enumerate(final_groups):
            Utils.debug_print(f"[DEBUG] Analyzing group {i+1}/{len(final_groups)}")
            group_summary = self._analyze_single_call(group)
            group_summaries.append(group_summary)
        
        # Combine group summaries
        return self._combine_group_summaries(group_summaries)

    @staticmethod
    def _group_by_extension(file_contents: Dict[str, List[str]]) -> List[Dict[str, List[str]]]:
        extension_groups = {}
        
        for file_path, contents in file_contents.items():
            extension = Utils.extract_file_extension(file_path).lower()
            
            # Group by extension
            if extension not in extension_groups:
                extension_groups[extension] = {}
            extension_groups[extension][file_path] = contents
        
        return list(extension_groups.values())

    @staticmethod
    def _calculate_group_size(group: Dict[str, List[str]]) -> int:
        total_size = 0
        for file_path, contents in group.items():
            file_content = "\n".join(contents)
            total_size += Utils.calculate_content_size(file_content)
        return total_size

    def _split_group_by_size(self, group: Dict[str, List[str]]) -> List[Dict[str, List[str]]]:
        groups = []
        current_group = {}
        current_size = 0
        
        for file_path, contents in group.items():
            file_content = "\n".join(contents)
            file_size = Utils.calculate_content_size(file_content)
            
            # If adding this file would exceed limit, start new group
            if current_size + file_size > self.max_group_size and current_group:
                groups.append(current_group)
                current_group = {}
                current_size = 0
            
            # Add file to current group
            current_group[file_path] = contents
            current_size += file_size
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups

    def _combine_group_summaries(self, group_summaries: List[dict]) -> dict:
        if not group_summaries:
            return self._create_empty_summary()
        
        if len(group_summaries) == 1:
            return group_summaries[0]
        
        summary_list = "\n- ".join([json.dumps(v) for v in group_summaries])
        user_prompt = self._create_combination_prompt(summary_list)

        try:
            Utils.debug_print(f"[DEBUG] Combining {len(group_summaries)} group summaries")
            
            result = self.invoke(user_prompt).strip()
            parsed_result = Utils.parse_json_from_response(result)
            
            if parsed_result:
                Utils.debug_print(f"[DEBUG] Successfully combined group summaries")
                return parsed_result
            else:
                Utils.debug_print(f"[DEBUG] Failed to parse JSON for combined summaries")
                return self._create_error_summary("JSON parsing failed")
                
        except Exception as e:
            Utils.debug_print(f"[DEBUG] Failed to combine group summaries: {e}")
            return self._create_error_summary("Processing failed")

    @staticmethod
    def _prepare_combined_content(file_contents: Dict[str, List[str]]) -> str:
        combined_content = []
        for file_path, contents in file_contents.items():
            file_content = "\n".join(contents)
            combined_content.append(f"File: {file_path}\nContent:\n{file_content}\n")
        return "\n---\n".join(combined_content)

    @staticmethod
    def _create_analysis_prompt(content: str, file_paths: List[str]) -> str:
        extensions = [Utils.extract_file_extension(fp).lower() for fp in file_paths]
        unique_extensions = list(set(extensions))
        
        return f"""
Analyze these specific code changes:

File extensions: {', '.join(unique_extensions)}
Content:
{content}

CRITICAL: You MUST be specific and concrete. DO NOT use generic language.

Provide a detailed analysis as JSON with these fields:
- summary: What specific feature or functionality does this code implement? Be specific about what users can do. (max 100 words)
- technical_details: What specific code changes were made? Include exact methods, classes, patterns used. Focus on concrete implementation details. (max 150 words)

REQUIRED: Use specific language like:
- "User dashboard displays order history with prices and dates"
- "Fixed N+1 query using Include() for user orders"
- "Added authorization check for profile updates"
- "Implemented MediatR pattern for user queries"
- "Display user statistics with total orders and spending"
- "Show loading spinner during data fetching"

FORBIDDEN: Do NOT use generic language like:
- "Significant improvements"
- "Enhanced security measures"
- "Improved user experience"
- "Better functionality"
- "Comprehensive updates"

INSTRUCTIONS:
1. Identify specific user features implemented
2. List exact technical changes made
3. Mention specific patterns and optimizations
4. Focus on concrete implementation details
5. Avoid any generic marketing language

Return only valid JSON based on the actual code content.
        """

    @staticmethod
    def _create_combination_prompt(summary_list: str) -> str:
        return f"""
Combine these group summaries into a comprehensive PR summary:

Group summaries:
- {summary_list}

CRITICAL: You MUST be specific and concrete. DO NOT use generic language.

Provide a comprehensive PR summary as JSON with these fields:
- summary: What specific business functionality does this PR implement? What can users do now that they couldn't before? Be specific about features and user value. (max 150 words)
- technical_details: What specific technical changes were made? Include exact patterns, optimizations, security measures, and implementation details. Focus on concrete changes, not generic concepts. (max 200 words)

REQUIRED: Use specific language like:
- "User dashboard displays order history with prices and dates"
- "Fixed N+1 query using Include() for user orders"
- "Added authorization check for profile updates"
- "Implemented MediatR pattern for user queries"
- "Display user statistics with total orders and spending"
- "Show loading spinner during data fetching"

FORBIDDEN: Do NOT use generic language like:
- "Significant improvements"
- "Enhanced security measures"
- "Improved user experience"
- "Better functionality"
- "Comprehensive updates"

INSTRUCTIONS:
1. Extract specific features from group summaries
2. Focus on concrete technical changes
3. Mention exact patterns and optimizations
4. Describe specific user functionality
5. Avoid any generic marketing language

Return only valid JSON based on the actual group summaries provided.
        """

    @staticmethod
    def _create_empty_summary() -> dict:
        return {
            "summary": "[No changes to analyze]",
            "technical_details": ""
        }

    @staticmethod
    def _create_error_summary(error_message: str) -> dict:
        return {
            "summary": f"[{error_message}]",
            "technical_details": ""
        }
