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
        You are PR-Reviewer, an expert code reviewer focused on finding ACTIONABLE issues.

        PRIORITY TARGETS (in order):
        1. Runtime bugs & crashes (null references, index out of bounds, unhandled exceptions)
        2. Security vulnerabilities (SQL injection, XSS, authorization bypass, sensitive data exposure) 
        3. Performance bottlenecks (N+1 queries, infinite loops, memory leaks, inefficient algorithms)
        4. Logic errors that cause incorrect behavior (wrong conditions, calculation errors)
        5. Critical violations of language-specific best practices that impact functionality
        6. Poor naming that significantly impacts code understanding

        STRICT FILTERING RULES:
        - ONLY flag lines with concrete, actionable problems that need immediate attention
        - NO generic suggestions, style preferences, or minor improvements  
        - NO comments on working code unless there's a clear functional issue
        - Focus ONLY on changed lines (marked with ">>>")
        - If no real issues exist in changed lines, return empty line_feedback: []

        QUALITY STANDARDS:
        - Each issue must include specific reason and suggested fix
        - Prioritize issues by business impact and severity
        - Be concise but thorough in explanations
        - Only reference best practices that are directly applicable to the specific issue found

        Response: Valid JSON only, no markdown wrappers.
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

        # Build comprehensive method lookup for context
        method_lookup = self._build_method_lookup(chunked_documents)

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
                context_methods = self._get_context_methods(chunk, method_lookup)
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
    def _build_method_lookup(chunked_documents: List[Document]) -> Dict:
        """Build a comprehensive lookup for methods with multiple indexing strategies"""
        method_lookup = {
            'by_class_method': {},  # (class, method) -> Document
            'by_method_name': {},  # method_name -> [Document, ...]
            'by_file_method': {},  # (file, method) -> Document
            'overloaded_methods': {}  # method_name -> [(class, params, Document), ...]
        }

        for doc in chunked_documents:
            if doc.metadata.get("chunk_type") == "function":
                parent_class = doc.metadata.get("parent")
                method_name = doc.metadata.get("name")
                file_path = doc.metadata.get("file_path")
                parameters = doc.metadata.get("parameters", [])

                # Index by (class, method)
                if parent_class and method_name:
                    key = (parent_class, method_name)
                    method_lookup['by_class_method'][key] = doc

                # Index by method name (for fuzzy matching)
                if method_name:
                    if method_name not in method_lookup['by_method_name']:
                        method_lookup['by_method_name'][method_name] = []
                    method_lookup['by_method_name'][method_name].append(doc)

                # Index by (file, method) for file-scoped lookup
                if file_path and method_name:
                    key = (file_path, method_name)
                    method_lookup['by_file_method'][key] = doc

                # Index overloaded methods
                if method_name:
                    if method_name not in method_lookup['overloaded_methods']:
                        method_lookup['overloaded_methods'][method_name] = []
                    method_lookup['overloaded_methods'][method_name].append(
                        (parent_class, parameters, doc)
                    )

        return method_lookup

    @staticmethod
    def _get_context_methods(chunk: Document, method_lookup: Dict) -> List[str]:
        context_methods = []
        current_file = chunk.metadata.get("file_path")
        current_class = chunk.metadata.get("parent")
        method_calls = chunk.metadata.get("method_calls", [])

        Utils.debug_print(f"Getting context for {chunk.metadata.get('name')} in {current_class}")
        Utils.debug_print(f"Method calls found: {len(method_calls)}")

        for call_info in method_calls:
            if not isinstance(call_info, dict):
                continue

            # Skip calls that are not context-worthy
            if not call_info.get("is_context_worthy", False):
                Utils.debug_print(f"Skipping {call_info.get('name')}: {call_info.get('reason')}")
                continue

            method_name = call_info.get("name")
            call_type = call_info.get("call_type", "unknown")

            Utils.debug_print(f"Looking for context method: {method_name} (type: {call_type})")

            found_method = None

            # Strategy 1: Exact match by class and method
            if current_class and call_type in ["internal_method", "direct_method"]:
                key = (current_class, method_name)
                found_method = method_lookup['by_class_method'].get(key)
                if found_method:
                    Utils.debug_print(f"Found exact match: {current_class}.{method_name}")

            # Strategy 2: Look in same file
            if not found_method and current_file:
                key = (current_file, method_name)
                found_method = method_lookup['by_file_method'].get(key)
                if found_method:
                    Utils.debug_print(f"Found file-scoped match: {method_name} in {current_file}")

            # Strategy 3: Fuzzy match by method name (same class preferred)
            if not found_method:
                candidates = method_lookup['by_method_name'].get(method_name, [])
                if candidates:
                    # Prefer methods from same class
                    same_class_candidates = [
                        doc for doc in candidates
                        if doc.metadata.get("parent") == current_class
                    ]
                    if same_class_candidates:
                        found_method = same_class_candidates[0]
                        Utils.debug_print(f"Found same-class fuzzy match: {method_name}")
                    elif len(candidates) == 1:
                        # Only one candidate, probably safe to use
                        found_method = candidates[0]
                        Utils.debug_print(f"Found single fuzzy match: {method_name}")
                    # If multiple candidates from different classes, skip to avoid confusion

            # Add to context if found and not the same as current chunk
            if found_method and found_method != chunk:
                context_content = found_method.page_content
                if context_content not in context_methods:
                    context_methods.append(context_content)
                    Utils.debug_print(f"Added to context: {method_name}")
                else:
                    Utils.debug_print(f"Already in context: {method_name}")
            elif not found_method:
                Utils.debug_print(f"No context found for: {method_name}")

        Utils.debug_print(f"Total context methods found: {len(context_methods)}")
        return context_methods

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

        # Get relevant best practices for this chunk
        chunk_content = chunk.page_content
        relevant_bp = self._get_cached_best_practices(chunk_content)
        Utils.debug_print(relevant_bp)

        best_practices_section = ""
        if relevant_bp and len(relevant_bp) > 0:
            best_practices_text = format_best_practices_for_prompt(relevant_bp)
            best_practices_section = f"""
        **RELEVANT BEST PRACTICES** (only include if you find a direct violation; DO NOT force-match otherwise)
        These are best practices that might be relevant. You should ONLY mention them if the chunk of code actually violates them. If there's no clear violation, IGNORE them entirely. Do NOT try to match them if not applicable.
        {best_practices_text}
        """

        # Build context methods section
        context_methods_text = ""
        if context_methods:
            context_methods_text = "\n\n# Related Methods (for understanding only - DO NOT review these):\n"
            for i, method in enumerate(context_methods, 1):
                # Truncate very long methods to avoid token overflow
                method_display = method[:500] + "..." if len(method) > 500 else method
                context_methods_text += f"\n## Context Method {i}:\n```{code_type}\n{method_display}\n```\n"
            context_methods_text += "\n" + "=" * 60 + "\n"

        format_chunk = self._format_chunk_with_highlighted_lines(chunk)

        user_prompt = f"""
        Analyze this {code_type.upper()} code for actual functional problems in the changed lines only.

        {best_practices_section}

        ***Find ONLY in changed lines (marked with ">>>"):***
        • Bugs, performance issues, security flaws  
        • Poor naming (use meaningful names, booleans start with is/has/can)
        • Violations of: {language_context}

        **CODE TO ANALYZE:**
        Lines marked with ">>>" need review: {sorted(diff_lines)}
        Read the entire code below for context, but ONLY analyze issues in lines marked with ">>>":

        {format_chunk}
        {context_methods_text}

        **REQUIRED JSON OUTPUT FORMAT:**
        You MUST return valid JSON in exactly this structure:

        If functional issues are found in marked lines:
        ```json
        {{
            "line_feedback": [
                {{
                    "[ACTUAL_LINE_NUMBER]": {{
                        "comment": "Specific functional problem explanation",
                        "suggest_code": "Concrete fix code",
                        "explain_suggest_code": "Why this fix solves the problem",
                        "matched_best_practices_and_severities": ["BP_CODE - Severity"]
                    }}
                }}
            ],
            "key_issues_to_review": ["Critical issues requiring immediate attention"],
            "security_concerns": "Specific security issues found",
            "relevant_tests": ["Unit test code for edge cases"]
        }}
        ```

        If NO functional issues found in marked lines:
        ```json
        {{
            "line_feedback": [],
            "key_issues_to_review": [],
            "security_concerns": "No security concerns identified", 
            "relevant_tests": []
        }}
        ```

        **MANDATORY:** 
        - Replace "[ACTUAL_LINE_NUMBER]" with the real line number that has issues\
        - Response must be valid JSON format
        - If no issues found, return empty arrays/appropriate empty values
        """

        try:
            Utils.debug_print(f"REVIEWING LINES: {sorted(diff_lines)}")

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
                review_obj.setdefault('relevant_tests', [])

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
                review_obj["file_path"] = file_path
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
        """Obsolete"""
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
        """Obsolete"""
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
        """Obsolete"""
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
            "file_path": metadata.get('file_path', 'unknown'),
            "chunk_type": metadata.get('chunk_type', 'unknown'),
            "chunk_name": metadata.get('name', 'unknown'),
            "line_feedback": [],
            "key_issues_to_review": ["Review failed - unable to process chunk"],
            "security_concerns": "Unable to analyze security concerns",
            "relevant_tests": [],
            "diff_lines": metadata.get('diff_lines', []),
            "start_line": metadata.get('start_line'),
            "end_line": metadata.get('end_line')
        }