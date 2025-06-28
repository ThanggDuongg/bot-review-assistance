import json
from typing import Dict, Any
from .base import BaseAgent


class SyntaxAgent(BaseAgent):
    """Agent specialized in syntax checking and validation."""
    
    @property
    def system_prompt(self) -> str:
        return """You are a specialized code review agent as well as programming expert focused on syntax validation and error detection. Your expertise includes:

- Detecting syntax errors across multiple programming languages
- Identifying missing semicolons, brackets, parentheses
- Spotting incorrect indentation and formatting issues
- Finding typos in keywords and operators
- Validating proper use of language constructs
- Checking for incomplete statements and expressions

Guidelines:
- Always respond in valid JSON format
- Be precise about the exact syntax issue
- Provide clear explanations of what's wrong
- Suggest the correct syntax when possible
- Consider language-specific syntax rules
- Focus on compilation/interpretation errors

Your goal is to catch syntax issues before they cause runtime errors."""

    def process(self, diff_text: str, language: str = "python") -> Dict[str, Any]:
        """Process syntax checking for given code."""
        user_prompt = f"""Check the following {language} code for syntax errors.
Respond in JSON format:
{{
  "lines": [
    {{"line": number, "feedback": "..."}},
    ...
  ]
}}

Code:
{diff_text}"""

        try:
            response = self.invoke(user_prompt).strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"SyntaxAgent: Failed to parse JSON: {str(e)}")
            return {}
        except Exception as e:
            print(f"SyntaxAgent: Failed to process: {str(e)}")
            return {}
