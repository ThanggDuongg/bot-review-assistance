from typing import List, Dict, Any, Optional
from .base import BaseAgent
from langchain.schema import Document
from ..core import Utils
from ..core.vector_store import get_relevant_best_practices_for_chunk, format_best_practices_for_prompt
from .language_contexts import get_language_context


class LogicAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__("logic", llm)

    @staticmethod
    def _get_single_best_practice(chunk_content: str) -> Optional[Dict]:
        relevant_bp = get_relevant_best_practices_for_chunk(chunk_content, max_top_n=1)
        
        if relevant_bp and len(relevant_bp) > 0:
            return relevant_bp[0]
        else:
            return None

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
                "total_files_reviewed": 0,
                "total_chunks_reviewed": 0
            }

        file_reviews = []

        # Only review function chunks
        method_chunks = [
            doc for doc in chunked_documents
            if self._should_review_chunk(doc)
        ]

        for chunk in method_chunks:
            chunk_review = self._review_single_chunk(chunk)
            if chunk_review:
                file_reviews.append(chunk_review)

        review_objects = []
        for file_review in file_reviews:
            Utils.debug_print(f"[DEBUG] Test - File review object: {file_review}")
            file_obj = {
                "file_path": file_review.get("file_path"),
                "diff_lines": file_review.get("diff_lines", []),
                "line_feedback": file_review.get("line_feedback", []),
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

    def _review_single_chunk(self, chunk: Document) -> Dict[str, Any]:
        metadata = chunk.metadata
        chunk_type = metadata.get('chunk_type', 'unknown')
        chunk_name = metadata.get('name', 'unknown')
        diff_lines = metadata.get('diff_lines', [])
        file_path = metadata.get('file_path', 'unknown')

        code_type = Utils.detect_code_type(file_path)
        language_context = get_language_context(code_type)

        chunk_content = chunk.page_content
        best_practice = self._get_single_best_practice(chunk_content)
        
        best_practices_section = ""
        if best_practice:
            best_practices_text = format_best_practices_for_prompt([best_practice])
            best_practices_section = f"""
            **RELEVANT BEST PRACTICES** (only include if you find a direct violation; DO NOT force-match otherwise)
            These are best practices that might be relevant. You should ONLY mention them if the chunk of code actually violates them. If there's no clear violation, IGNORE them entirely. Do NOT try to match them if not applicable.
            {best_practices_text}
            """

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
            ]
        }}
        ```

        If NO functional issues found in marked lines:
        ```json
        {{
            "line_feedback": []
        }}
        ```

        **MANDATORY:** 
        - Replace "[ACTUAL_LINE_NUMBER]" with the real line number that has issues
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

                review_obj['line_feedback'] = self._normalize_line_feedback(
                    review_obj.get('line_feedback', []), 
                    file_path
                )

                # Add metadata
                review_obj.update({
                    "file_path": file_path,
                    "chunk_type": chunk_type,
                    "chunk_name": chunk_name,
                    "diff_lines": diff_lines,
                    "start_line": metadata.get('start_line'),
                    "end_line": metadata.get('end_line')
                })
                
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

    @staticmethod
    def _normalize_line_feedback(line_feedback: Any, file_path: str) -> List[Dict]:
        if not line_feedback:
            return []
        
        normalized = []

        items = line_feedback.items() if isinstance(line_feedback, dict) else line_feedback
        
        for item in items:
            if isinstance(item, dict):
                line_num, feedback = list(item.items())[0]
            else:
                line_num, feedback = item, str(item)

            if not isinstance(feedback, dict):
                feedback = {
                    "comment": str(feedback),
                    "suggest_code": "",
                    "explain_suggest_code": "",
                    "matched_best_practices_and_severities": [],
                }
            
            normalized.append({line_num: feedback})
        
        return normalized

    @staticmethod
    def _create_fallback_chunk_review(chunk: Document) -> Dict[str, Any]:
        metadata = chunk.metadata
        return {
            "file_path": metadata.get('file_path', 'unknown'),
            "chunk_type": metadata.get('chunk_type', 'unknown'),
            "chunk_name": metadata.get('name', 'unknown'),
            "line_feedback": [],
            "diff_lines": metadata.get('diff_lines', []),
            "start_line": metadata.get('start_line'),
            "end_line": metadata.get('end_line')
        }