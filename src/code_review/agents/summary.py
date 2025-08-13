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
        You are a Code Analysis Expert. Analyze pull request changes with focus on:

        1. Technical accuracy and specific implementation details
        2. Clear categorization of code patterns and dependencies  
        3. Structured JSON output with concrete, specific language

        Always avoid generic terms. Use precise technical language describing exact changes and user-facing functionality.
            """

    def process(self, chunk_docs: List[Document]) -> Dict[str, dict]:
        if not chunk_docs:
            Utils.debug_print("[DEBUG] No chunks provided")
            return {"summary": self._create_empty_summary()}
        
        file_contents = self._group_chunks_by_file(chunk_docs)

        total_size = self._calculate_total_size(file_contents)
        if total_size > self.size_threshold:
            Utils.debug_print(f"[DEBUG] Content size exceeds threshold, using hybrid grouping")
            return {"summary": self._analyze_with_hybrid_grouping(file_contents)}
        else:
            Utils.debug_print(f"[DEBUG] Content size OK, using single call")
            return {"summary": self._analyze_single_call(file_contents)}

    @staticmethod
    def _group_chunks_by_file(chunk_docs: List[Document]) -> Dict[str, List[str]]:
        file_contents = {}
        for doc in chunk_docs:
            file_path = doc.metadata.get("file_path", "unknown")
            if file_path not in file_contents:
                file_contents[file_path] = []
            file_contents[file_path].append(doc.page_content)
        return file_contents

    @staticmethod
    def _calculate_total_size(file_contents: Dict[str, List[str]]) -> int:
        total_size = 0
        for file_path, contents in file_contents.items():
            file_content = "\n".join(contents)
            total_size += Utils.calculate_content_size(file_content)
        return total_size

    def _analyze_single_call(self, file_contents: Dict[str, List[str]]) -> dict:
        combined_content = self._prepare_combined_content(file_contents)

        user_prompt = self._create_analysis_prompt(combined_content, list(file_contents.keys()))
        try:
            result = self.invoke(user_prompt).strip()
            parsed_result = Utils.parse_json_from_response(result)
            
            return parsed_result or self._create_error_summary("JSON parsing failed")
                
        except Exception as e:
            Utils.debug_print(f"[DEBUG] Failed to analyze files in single call: {e}")
            return self._create_error_summary("Processing failed")

    def _analyze_with_hybrid_grouping(self, file_contents: Dict[str, List[str]]) -> dict:
        extension_groups = self._group_by_extension(file_contents)

        group_summaries = []
        for group in extension_groups:
            group_summary = self._analyze_single_call(group)
            group_summaries.append(group_summary)

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

    def _combine_group_summaries(self, group_summaries: List[dict]) -> dict:
        if not group_summaries:
            return self._create_empty_summary()
        
        if len(group_summaries) == 1:
            return group_summaries[0]
        
        summary_list = "\n- ".join([json.dumps(v) for v in group_summaries])
        user_prompt = self._create_combination_prompt(summary_list)

        try:
            result = self.invoke(user_prompt).strip()
            parsed_result = Utils.parse_json_from_response(result)
            
            return parsed_result or self._create_error_summary("JSON parsing failed")
                
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
        Analyze this code change ({', '.join(unique_extensions)} files):

        {content}

        Create a concise analysis in JSON format:
        {{
            "summary": "Brief description of what users can now do (max 100 words)",
            "technical_details": "Specific technical changes made (max 150 words)"
        }}

        Requirements:
        - Use specific technical terms, not generic words like "improvements"
        - Each field must be a single paragraph (no bullet points)
        - Stay within word limits strictly
        - Focus on concrete functionality and implementation details

        Good examples:
        - summary: "Users can now view transport allowances and special skill premiums in Mauritius compensation letters with historical data comparison"
        - technical_details: "Added GeneratePremiumsAndAllowancesSection method in CompensationLetterGenerator class with country-specific logic for Mauritius. Extended GenerateCompensationLetterInput with four new nullable double properties for current and previous year transport allowances and special skill premiums. Added corresponding translation keys in en.json localization file"

        Return only valid JSON with no additional text or explanations.
        """

    @staticmethod
    def _create_combination_prompt(summary_list: str) -> str:
        return f"""
        Combine these summaries into one comprehensive PR summary:

        {summary_list}

        Create a concise analysis in JSON format:
        {{
            "summary": "Brief description of what users can now do (max 100 words)",
            "technical_details": "Specific technical changes made (max 150 words)"
        }}

        BE SPECIFIC. Examples:
        - "Dashboard shows real-time order status with WebSocket updates"
        - "Implemented CQRS with MediatR for user management"
        - "Added Redis caching for product catalog queries"

        AVOID: "significant improvements", "enhanced security", "better UX"

        Be concrete: "User can view order history" not "improved experience"
        Continuous text only, no bullets.
        Return only valid JSON with continuous text fields.
        """

    @staticmethod
    def _create_empty_summary() -> dict:
        return {
            "summary": "",
            "technical_details": ""
        }

    @staticmethod
    def _create_error_summary(error_message: str) -> dict:
        return {
            "summary": f"[{error_message}]",
            "technical_details": ""
        }
