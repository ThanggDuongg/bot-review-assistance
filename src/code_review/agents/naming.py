import json
import langdetect
from typing import List, Dict, Any
from .base import BaseAgent


class NamingAgent(BaseAgent):
    """Agent specialized in checking naming conventions."""
    
    @property
    def system_prompt(self) -> str:
        return """You are a specialized code review agent as well as programming expert focused on naming conventions and code clarity. Your expertise includes:

- Evaluating variable, function, class, and method names for clarity and meaning
- Checking adherence to language-specific naming conventions (camelCase, snake_case, PascalCase)
- Identifying unclear abbreviations, single-letter variables, and misleading names
- Suggesting meaningful alternatives for poor names
- Ensuring boolean variables use appropriate prefixes (is_, has_, can_, should_)

Guidelines:
- Always respond in valid JSON format
- Be specific about what makes a name good or bad
- Suggest concrete improvements
- Consider the context and purpose of the code
- Focus on readability and maintainability

Your goal is to help developers write self-documenting code through better naming."""

    def process(self, declarations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process naming conventions for given declarations."""
        if not declarations:
            return {}

        decl_str = "\n".join([f"- {d['name']} (line {d['line']})" for d in declarations])
        
        print("Naming Agent: ", langdetect.detect(decl_str))
        try:
            if len(decl_str.strip()) < 10 or langdetect.detect(decl_str) != "en":
                return {}
        except:
            return {}

        user_prompt = f"""Review the following class, method, and variable names for proper naming conventions.
Check for clarity, spelling, meaningful verbs (e.g., is_*/has_* for booleans), and consistency.
Respond in JSON:
{{
    "lines": [
        {{"line": number, "feedback": "..."}},
        ...
    ]
}}

Names to review:
{decl_str}"""

        try:
            response = self.invoke(user_prompt).strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"NamingAgent: Failed to parse JSON: {str(e)}")
            return {}
        except Exception as e:
            print(f"NamingAgent: Failed to process: {str(e)}")
            return {}
