from typing import List, Dict, Any
from .base import BaseAgent
from langchain.schema import Document
from ..core import Utils
from ..core.vector_store import get_relevant_best_practices_for_chunk, format_best_practices_for_prompt
from .language_contexts import get_language_context
import hashlib
import os
from collections import OrderedDict


class LogicAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__("logic", llm)
        self.bp_cache = OrderedDict()  # LRU Cache for best practices
        self.max_cache_size = int(os.getenv("LOGIC_AGENT_BP_CACHE_SIZE", "100"))
    
    def _get_cached_best_practices(self, chunk_content: str, max_top_n: int = 1) -> list:
        content_hash = hashlib.md5(chunk_content.encode()).hexdigest()
        cache_key = f"{content_hash}_{max_top_n}"
        if cache_key in self.bp_cache:
            Utils.debug_print(f"Using cached best practices for chunk")
            self.bp_cache.move_to_end(cache_key)
            return self.bp_cache[cache_key]
        relevant_bp = get_relevant_best_practices_for_chunk(chunk_content, max_top_n)
        self.bp_cache[cache_key] = relevant_bp
        if len(self.bp_cache) > self.max_cache_size:
            self.bp_cache.popitem(last=False)  # Pop oldest
        return relevant_bp

    @property
    def system_prompt(self) -> str:
        return """
        You are PR-Reviewer, an expert code reviewer. Find REAL issues only:
        - Runtime bugs and crashes
        - Performance problems (N+1 queries, inefficient algorithms) 
        - Security vulnerabilities
        - Critical best practice violations
        - Poor naming (non-descriptive variables/methods)

        STRICT: Only flag lines with actual problems. No generic suggestions or code descriptions.

        Response format: Valid JSON only.
        """

    def process(self, chunked_documents: List[Document],
                file_contents: Dict[str, str] = None) -> Dict[str, Any]:
        if not chunked_documents:
            return {
                "line_feedback": {},
                "key_issues_to_review": [],
                "security_concerns": [],
                "relevant_tests": [],
                "overall_quality": "No files to review",
                "total_files_reviewed": 0,
                "total_chunks_reviewed": 0
            }

        # Build method lookup for context
        method_lookup = {}
        for doc in chunked_documents:
            if doc.metadata.get("chunk_type") == "function":
                key = (doc.metadata.get("parent"), doc.metadata.get("name"))
                method_lookup[key] = doc

        file_reviews = []
        reviewed_hashes = {}
        # Only review function chunks
        method_chunks = [
            doc for doc in chunked_documents
            if self._should_review_chunk(doc)
        ]
        for chunk in method_chunks:
            # Deduplicate by content hash
            content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
            if content_hash in reviewed_hashes:
                chunk_review = reviewed_hashes[content_hash]
            else:
                # Build context methods
                context_methods = []
                parent = chunk.metadata.get("parent")
                method_calls = chunk.metadata.get("method_calls", [])
                for called_name in method_calls:
                    context_key = (parent, called_name)
                    if context_key in method_lookup and method_lookup[context_key] != chunk:
                        context_methods.append(method_lookup[context_key].page_content)
                context_methods = [m for m in context_methods if m != chunk.page_content]
                chunk_review = self._review_single_chunk_with_context(chunk, context_methods)
                reviewed_hashes[content_hash] = chunk_review
            if chunk_review:
                file_reviews.append(chunk_review)

        review_objects = []
        for file_review in file_reviews:
            Utils.debug_print(f"[DEBUG] Test - File review object: {file_review}")
            file_obj = {
                "file_path": file_review.get("file_path"),
                "diff_lines": file_review.get("diff_lines", []),
                "line_feedback": file_review.get("line_feedback", []),
                "key_issues_to_review": file_review.get("key_issues_to_review", []),
                "security_concerns": file_review.get("security_concerns", []),
                "relevant_tests": file_review.get("relevant_tests", []),
            }
            review_objects.append(file_obj)
        Utils.debug_print(f"[DEBUG] Final review_objects: {review_objects}")
        return {
            "file_reviews": review_objects,
            "total_files_reviewed": len(file_reviews),
            "total_chunks_reviewed": len(method_chunks)
        }

    @staticmethod
    def _should_review_chunk(chunk: Document) -> bool:
        metadata = chunk.metadata

        if metadata.get("chunk_type") != "function":
            return False

        diff_lines = metadata.get("diff_lines", [])
        if not diff_lines or len(diff_lines) == 0:
            Utils.debug_print(f"Skipping chunk {metadata.get('name', 'unknown')} - no diff lines")
            return False

        Utils.debug_print(f"Will review chunk {metadata.get('name', 'unknown')} - has {len(diff_lines)} diff lines")
        return True

    def _review_single_chunk_with_context(self, chunk: Document, context_methods: List[str]) -> Dict[str, Any]:
        metadata = chunk.metadata
        chunk_type = metadata.get('chunk_type', 'unknown')
        chunk_name = metadata.get('name', 'unknown')
        diff_lines = metadata.get('diff_lines', [])
        file_path = metadata.get('file_path', 'unknown')

        code_type = Utils.detect_code_type(file_path)
        language_context = get_language_context(code_type)

        # TODO: Will be remove
        # context_info = self._prepare_chunk_context(chunk, file_contents)

        # Get relevant best practices for this chunk
        chunk_content = chunk.page_content
        relevant_bp = self._get_cached_best_practices(chunk_content)
        Utils.debug_print(relevant_bp)
        best_practices_text = format_best_practices_for_prompt(relevant_bp)

        # Build context methods section
        context_methods_text = ""
        if context_methods:
            context_methods_text = "\n\n# Context methods (for reference only, do not review these):\n"
            for i, method in enumerate(context_methods, 1):
                context_methods_text += f"\n## Context Method {i}:\n```{code_type}\n{method}\n```\n"
            context_methods_text += "\n" + "=" * 60 + "\n"

        format_chunk = self._format_chunk_with_highlighted_lines(chunk);
        # TODO: Create NamingAgent to check code convention
        user_prompt = f"""
Review this {code_type.upper()} code for real issues:

{best_practices_text}

**IMPORTANT: ONLY review lines marked with ">>>" (lines {sorted(diff_lines)}). Ignore other lines.**

{format_chunk}
{context_methods_text}

Find ONLY in changed lines (marked with ">>>"):
• Bugs, performance issues, security flaws  
• Poor naming (use meaningful names, booleans start with is/has/can)
• Violations of: {language_context}

**Rules:**
- ONLY comment on lines marked with ">>>" 
- If changed lines have NO issues, return empty line_feedback: []
- Don't review context lines (without ">>>")\

Provide unit test for this method.

Return JSON format:
{{
    "line_feedback": [
        {{
            "LINE_NUMBER": {{
                "comment": "Issue description",
                "suggest_code": "Fix code", 
                "explain_suggest_code": "Why fix is needed",
                "matched_best_practices_and_severities": ["BP_CODE - Severity"]
            }}
        }}
    ],
    "key_issues_to_review": ["Critical issues summary"],
    "security_concerns": "Security issues found or 'No security concerns identified'",
    "relevant_tests": ["Unit test code"]
}}

**Important:** Replace LINE_NUMBER with actual line numbers that have issues.
"""

        try:
            Utils.debug_print(f"REVIEWING LINES: {sorted(diff_lines)}")
            Utils.debug_print(f"USER PROMPT SENT TO LLM:\n{user_prompt[:1000]}...\n[TRUNCATED]" if len(
                user_prompt) > 1000 else f"USER PROMPT SENT TO LLM:\n{user_prompt}")

            response = self.invoke(user_prompt).strip()
            Utils.debug_print(f"RAW LLM RESPONSE: {response}")

            parsed_result = Utils.parse_json_from_response(response)
            Utils.debug_print(f"[DEBUG] parsed_result after parse: {parsed_result}")

            if parsed_result and 'line_feedback' in parsed_result:
                review_obj = parsed_result
                # Validate that feedback is provided for correct lines
                lf = review_obj.get('line_feedback', [])
                if isinstance(lf, dict):
                    feedback_lines = set(lf.keys())
                elif isinstance(lf, list):
                    feedback_lines = set()
                    for fb in lf:
                        if isinstance(fb, dict):
                            feedback_lines.update(fb.keys())
                        else:
                            Utils.debug_print(f"Warning: Unexpected feedback format: {fb}")
                else:
                    feedback_lines = set()
                expected_lines = set(str(line) for line in diff_lines)

                Utils.debug_print(f"Expected lines: {expected_lines}")
                Utils.debug_print(f"Feedback lines: {feedback_lines}")

                missing_lines = expected_lines - feedback_lines
                if missing_lines:
                    Utils.debug_print(f"INFO: No issues found for lines: {missing_lines}")

                # Ensure all required fields are present with reasonable defaults
                review_obj.setdefault('key_issues_to_review', [])
                review_obj.setdefault('security_concerns', "No security concerns identified")
                review_obj.setdefault('relevant_tests', []) # Changed from "Add unit tests for edge cases and error handling" to []

                # Ensure key_issues_to_review is a list
                if not isinstance(review_obj.get('key_issues_to_review'), list):
                    if review_obj.get('key_issues_to_review'):
                        review_obj['key_issues_to_review'] = [str(review_obj['key_issues_to_review'])]
                    else:
                        review_obj['key_issues_to_review'] = []

                # Normalize line_feedback structure to handle both old and new formats
                lf = review_obj.get('line_feedback', [])
                if isinstance(lf, dict):
                    # Convert dict format to list format for consistency
                    normalized_lf = []
                    for line_num, feedback in lf.items():
                        if isinstance(feedback, dict):
                            # New format with nested structure
                            # Ensure suggest_code is properly formatted
                            if 'suggest_code' in feedback and feedback['suggest_code']:
                                feedback['suggest_code'] = Utils.ensure_markdown_codeblock(
                                    feedback['suggest_code'], 
                                    Utils.detect_code_type(file_path)
                                )
                            normalized_lf.append({line_num: feedback})
                        else:
                            # Old format with string feedback - convert to new format
                            normalized_lf.append({line_num: {
                                "comment": str(feedback),
                                "suggest_code": "",
                                "explain_suggest_code": "",
                                "matched_best_practices_and_severities": []
                            }})
                    review_obj['line_feedback'] = normalized_lf
                elif isinstance(lf, list):
                    # Already in list format, but ensure each item is properly structured
                    normalized_lf = []
                    for fb in lf:
                        if isinstance(fb, dict):
                            for line_num, feedback in fb.items():
                                if isinstance(feedback, dict):
                                    # Already in new format
                                    # Ensure suggest_code is properly formatted
                                    if 'suggest_code' in feedback and feedback['suggest_code']:
                                        feedback['suggest_code'] = Utils.ensure_markdown_codeblock(
                                            feedback['suggest_code'], 
                                            Utils.detect_code_type(file_path)
                                        )
                                    normalized_lf.append({line_num: feedback})
                                else:
                                    # Convert string to new format
                                    normalized_lf.append({line_num: {
                                        "comment": str(feedback),
                                        "suggest_code": "",
                                        "explain_suggest_code": "",
                                        "matched_best_practices_and_severities": []
                                    }})
                    review_obj['line_feedback'] = normalized_lf

                # Ensure relevant_tests is properly formatted
                if 'relevant_tests' in review_obj and review_obj['relevant_tests']:
                    # Ensure each item in relevant_tests is a string (code snippet)
                    review_obj['relevant_tests'] = [Utils.ensure_markdown_codeblock(
                        item, 
                        Utils.detect_code_type(file_path)
                    ) for item in review_obj['relevant_tests']]

                # Add metadata
                review_obj["chunk_type"] = chunk_type
                review_obj["chunk_name"] = chunk_name
                review_obj["diff_lines"] = diff_lines
                review_obj["start_line"] = metadata.get('start_line')
                review_obj["end_line"] = metadata.get('end_line')
                return review_obj
            else:
                Utils.debug_print(f"LogicAgent: Failed to parse JSON for chunk {chunk_name}")
                return self._create_fallback_chunk_review(chunk)

        except Exception as e:
            Utils.debug_print(f"LogicAgent: Failed to process chunk {chunk_name}: {str(e)}")
            return self._create_fallback_chunk_review(chunk)

    @staticmethod
    def _format_chunk_with_highlighted_lines(chunk: Document) -> str:
        metadata = chunk.metadata
        diff_lines = metadata.get('diff_lines', [])
        start_line = metadata.get('start_line', 1)

        lines = chunk.page_content.split('\n')
        formatted_lines = []

        for i, line in enumerate(lines):
            current_line_number = start_line + i
            prefix = ">>> " if current_line_number in diff_lines else "    "
            formatted_lines.append(f"{prefix}{current_line_number:4d}: {line}")

        return "\n".join(formatted_lines)

    def _prepare_chunk_context(self, chunk: Document, file_contents: Dict[str, str] = None) -> str:
        """Obsolete"""
        metadata = chunk.metadata
        context_parts = []

        # Basic metadata
        if metadata.get('parent'):
            context_parts.append(f"Parent class: {metadata['parent']}")
        if metadata.get('parameters'):
            context_parts.append(f"Parameters: {', '.join(metadata['parameters'])}")
        if metadata.get('return_type'):
            context_parts.append(f"Return type: {metadata['return_type']}")
        if metadata.get('access_modifier'):
            context_parts.append(f"Access: {metadata['access_modifier']}")

        file_path = metadata.get('file_path')
        diff_lines = metadata.get('diff_lines', [])
        if file_contents and file_path in file_contents:
            context_lines = self._get_smart_context_lines(
                file_contents[file_path], diff_lines
            )
            if context_lines:
                context_parts.append("Context:\n" + "\n".join(context_lines))

        return "\n".join(context_parts) if context_parts else "No context available"

    @staticmethod
    def _get_smart_context_lines(file_content: str, diff_lines: List[int], context_size: int = 1) -> List[str]:
        if not diff_lines:
            return []
        lines = file_content.split('\n')
        min_line = max(1, min(diff_lines) - context_size)
        max_line = min(len(lines), max(diff_lines) + context_size)
        context_lines = []
        for i in range(min_line, max_line + 1):
            prefix = ">>> " if i in diff_lines else "    "
            context_lines.append(f"{prefix}{i:4d}: {lines[i-1]}")
        return context_lines

    @staticmethod
    def _group_chunks_for_review(chunks_by_file: Dict[str, List[Document]], max_lines: int = 300) -> Dict[str, List[List[Document]]]:
        grouped = {}
        for file_path, chunks in chunks_by_file.items():
            total_lines = Utils.count_total_lines(chunks)
            if total_lines <= max_lines:
                grouped[file_path] = [chunks]  # group all chunks in file
            else:
                grouped[file_path] = [[chunk] for chunk in chunks]  # each chunk is a group
        return grouped

    @staticmethod
    def _aggregate_line_feedback(chunk_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        line_feedback = []
        for review in chunk_reviews:
            chunk_line_feedback = review.get('line_feedback', [])
            if isinstance(chunk_line_feedback, dict):
                for k, v in chunk_line_feedback.items():
                    line_feedback.append({k: v})
            elif isinstance(chunk_line_feedback, list):
                line_feedback.extend(chunk_line_feedback)
        return line_feedback

    @staticmethod
    def _create_fallback_chunk_review(chunk: Document) -> Dict[str, Any]:
        metadata = chunk.metadata
        return {
            "chunk_type": metadata.get('chunk_type', 'unknown'),
            "chunk_name": metadata.get('name', 'unknown'),
            "line_feedback": [],
            "key_issues_to_review": ["Review failed - unable to process chunk"],
            "security_concerns": "Unable to analyze security concerns",
            "relevant_tests": "Unable to provide test recommendations",
            "diff_lines": metadata.get('diff_lines', []),
            "start_line": metadata.get('start_line'),
            "end_line": metadata.get('end_line')
        }