# from src.code_review.agents import NamingAgent, SyntaxAgent, LogicAgent, SummaryAgent
from src.code_review.core import CodeChunker
# from src.code_review.pipeline.workflow import run_pipeline

# Sample test data
sample_declarations = [
    {"name": "calculate_total_price", "line": 5},
    {"name": "x", "line": 10},
    {"name": "isValid", "line": 15}
]

sample_code = """
def calculate_total_price(items):
    total = 0
    for item in items:
        total += item.price
    return total

x = 5  # unclear variable name
isValid = True  # should be is_valid in Python
"""

sample_diff = """
diff --git a/example.py b/example.py
index abc123..def456 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,8 @@
 def calculate_total_price(items):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * 1.1  # add 10% tax
     return total
+
+x = 5  # unclear variable name
+isValid = True  # should be is_valid
"""


# def test_naming_agent():
#     print("▶ Testing NamingAgent")
#     agent = NamingAgent()
#     result = agent.process(sample_declarations)
#     print(result)
#     assert isinstance(result, list)
#
#
# def test_syntax_agent():
#     print("▶ Testing SyntaxAgent")
#     agent = SyntaxAgent()
#     result = agent.process(sample_code, "python")
#     print(result)
#     assert isinstance(result, list)
#
#
# def test_logic_agent():
#     print("▶ Testing LogicAgent")
#     agent = LogicAgent()
#     result = agent.process(sample_code, [])
#     print(result)
#     assert isinstance(result, list)
#
#
# def test_summary_agent():
#     print("▶ Testing SummaryAgent")
#     agent = SummaryAgent()
#     chunk_summary = agent.summarize_chunk(sample_code)
#     result = agent.process([chunk_summary], ["a/example.py"])
#     print(result)
#     assert isinstance(result, str)


# def test_pipeline():
#     print("▶ Testing Full Pipeline")
#     result = run_pipeline(sample_diff)
#     print(result)
#     assert isinstance(result, dict)

def test_extract_file_paths_standard_diff():
    diff = """
diff --git a/src/test1.py b/src/test1.py
+++ b/src/test1.py
+print("Hello")
diff --git a/src/test2.py b/src/test2.py
+++ b/src/test2.py
+print("World")
"""
    paths = CodeChunker.extract_file_paths(diff)
    assert "src/test1.py" in paths
    assert "src/test2.py" in paths
    assert len(paths) == 2

def test_extract_file_paths_bitbucket_style():
    diff = """
## File: 'src/a.cs'
+ public class A { }

## File: 'src/b.cs'
+ public class B { }
"""
    paths = CodeChunker.extract_file_paths(diff)
    assert "src/a.cs" in paths or "src/b.cs" in paths  # only works if pattern supports it
    # For this format, extract_file_paths may not always catch it (not ++ b/)

def test_split_diff_by_file_git_format():
    diff = """
diff --git a/src/file1.py b/src/file1.py
+++ b/src/file1.py
+print("file1")

diff --git a/src/file2.py b/src/file2.py
+++ b/src/file2.py
+print("file2")
"""
    result = CodeChunker.split_diff_by_file(diff)
    assert len(result) == 2
    assert result[0][0] == "src/file1.py"
    assert "print" in result[0][1]

def test_split_diff_by_file_bitbucket_format():
    diff = """
## File: 'dir/a.ts'
+function a() {}

## File: 'dir/b.ts'
+function b() {}
"""
    result = CodeChunker.split_diff_by_file(diff)
    assert len(result) == 2
    assert result[0][0] == "dir/a.ts"
    assert "function a" in result[0][1]

def test_chunk_diff_documents():
    diff = """
diff --git a/src/main.py b/src/main.py
+++ b/src/main.py
+print("hello world")
"""
    docs = CodeChunker.chunk_diff(diff)
    assert len(docs) == 1
    assert docs[0]["metadata"]["file_path"] == "src/main.py"
    assert "print" in docs[0]["page_content"]

if __name__ == "__main__":
    test_extract_file_paths_standard_diff()
    test_extract_file_paths_bitbucket_style()
    test_split_diff_by_file_git_format()
    test_split_diff_by_file_bitbucket_format()
    test_chunk_diff_documents()
