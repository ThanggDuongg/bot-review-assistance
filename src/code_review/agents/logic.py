import json
from typing import List, Dict, Any
from .base import BaseAgent


class LogicAgent(BaseAgent):
    """Agent specialized in logic review and code analysis."""
    
    @property
    def system_prompt(self) -> str:
        return """You are a specialized code review agent as well as programming expert focused on logic analysis and code quality. Your expertise includes:

- Analyzing code logic for correctness and efficiency
- Identifying potential bugs, edge cases, and logical errors
- Detecting code smells and anti-patterns
- Evaluating algorithm complexity and performance issues
- Checking for proper error handling and validation
- Identifying security vulnerabilities and best practices
- Analyzing code flow and control structures
- Give feedback and suggest alternative best practice code

Guidelines:
- Always respond in valid JSON format
- Focus on logical correctness over style
- Identify potential runtime issues
- Consider edge cases and error scenarios
- Evaluate code maintainability and readability
- Suggest improvements for complex logic by provide best practice code

Your goal is to ensure code works correctly and efficiently in all scenarios."""

    def process(self, diff_text: str, context: List[str] = None) -> Dict[str, Any]:
        """Process logic review for given code."""
        context = context or []
        
        user_prompt = f"""Review the following code for logic issues.
Refer to context from similar code when useful.
Return JSON format:
{{
  "lines": [
    {{"line": number, "feedback": "..."}},
    ...
  ]
}}

Code:
{diff_text}

Context:
{context}"""

        try:
            response = self.invoke(user_prompt).strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"LogicAgent: Failed to parse JSON: {str(e)}")
            return {}
        except Exception as e:
            print(f"LogicAgent: Failed to process: {str(e)}")
            return {}
