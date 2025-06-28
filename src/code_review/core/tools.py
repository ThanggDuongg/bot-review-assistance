from langchain_core.tools import tool
import re


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
