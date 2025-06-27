from langchain_core.tools import tool
import re
import langdetect
from code_review_agent.utils.llm import load_local_llm, invoke_with_system_prompt
from code_review_agent.utils.prompts import SYSTEM_PROMPT
import json

@tool
def scan_structure(diff_text: str) -> list:
    """Scan code diff text to extract class, method, and variable declarations.

    Args:
        diff_text: The code diff text to analyze

    Returns:
        List of dictionaries containing name and line number of detected declarations
    """
    patterns = [
        (r'^\s*(class|record|interface|struct)\s+(\w+)', 2),
        (r'^\s*(def|function)\s+(\w+)', 2),
        (r'\b(?:public|private|protected|internal|static|async|final)?\s*\w+[<>,\s\[\]]*\s+(\w+)\s*\(.*?\)\s*\{?', 1),
        (r'^\s*def\s+(\w+)\s*\(', 1),
        (r'^\s*(?:var|int|float|double|bool|string|char|long|decimal|const|let|final)\s+(\w+)\s*=.*;', 1),
        # TypeScript/JS/Java field/property/assignment
        # (r'^\s*(\w+)\s*=\s*.+;', 1),
    ]
    result = []
    lines = diff_text.splitlines()
    for i, line in enumerate(lines):
        for pattern, group_index in patterns:
            match = re.search(pattern, line)
            if match:
                name = match.group(group_index)
                if name:
                    result.append({"name": name, "line": i + 1})
    return result

@tool
def check_naming(declarations: list = None) -> dict:
    """Check naming conventions for class, method, and variable names.

    Args:
        declarations: List of declarations with name and line number

    Returns:
        Dictionary containing feedback on naming conventions
    """
    if not declarations:
        return {}

    decl_str = "\n".join([f"- {d['name']} (line {d['line']})" for d in declarations])
    print("Check Naming - Detected Language:", langdetect.detect(decl_str))
    print(decl_str)
    if len(decl_str.strip()) < 10 or langdetect.detect(decl_str) != "en":
        return {}

    llm = load_local_llm()
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
        response = invoke_with_system_prompt(llm, SYSTEM_PROMPT, user_prompt).strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse naming check JSON: {str(e)}")
        return {}
    except Exception as e:
        print(f"Failed to check naming conventions: {str(e)}")
        return {}


@tool
def check_syntax(diff_text: str, language: str = "python") -> dict:
    """Check code for syntax errors using LLM analysis.

    Args:
        diff_text: The code text to check for syntax errors
        language: Programming language of the code (default: python)

    Returns:
        Dictionary containing syntax error feedback
    """
    llm = load_local_llm()
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
        response = invoke_with_system_prompt(llm, SYSTEM_PROMPT, user_prompt).strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse syntax check JSON: {str(e)}")
        return {}
    except Exception as e:
        print(f"Failed to check syntax: {str(e)}")
        return {}

@tool
def review_logic(diff_text: str, context: list) -> dict:
    """Review code for logic issues and potential problems.

    Args:
        diff_text: The code text to review for logic issues
        context: List of context information from similar code

    Returns:
        Dictionary containing logic review feedback
    """
    llm = load_local_llm()
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
        response = invoke_with_system_prompt(llm, SYSTEM_PROMPT, user_prompt).strip()
        # Clean response if it has markdown formatting
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse logic review JSON: {str(e)}")
        return {}
    except Exception as e:
        print(f"Failed to review logic: {str(e)}")
        return {}

@tool
def summarize_issues(diff_text: str, feedbacks: list) -> dict:
    """Summarize pull request issues and provide overall evaluation.

    Args:
        diff_text: The pull request diff text
        feedbacks: List of feedback from various review tools

    Returns:
        Dictionary containing summary and details of issues
    """
    llm = load_local_llm()
    extracted_summaries = [f.get("summary") if isinstance(f, dict) else str(f) for f in feedbacks if f]

    user_prompt = f"""Analyze the following pull request diff and summarize:
        1. What the PR is trying to do (its main purpose).
        2. Provide a high-level evaluation: is the implementation clear? any smells?
        3. Then summarize the individual review feedbacks below.
        
        Respond with a natural language paragraph.
        
        [DIFF]
        {diff_text}
        
        [FEEDBACKS]
        {json.dumps(extracted_summaries, indent=2)}"""

    try:
        summary_text = invoke_with_system_prompt(llm, SYSTEM_PROMPT, user_prompt).strip()
        return {
            "summary": summary_text,
            "details": extracted_summaries
        }
    except Exception as e:
        return {
            "summary": f"Failed to summarize issues: {str(e)}",
            "details": extracted_summaries
        }
