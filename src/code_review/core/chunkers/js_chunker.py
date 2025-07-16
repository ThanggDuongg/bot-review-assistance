from typing import List
from langchain.schema import Document
from .base_chunker import BaseCodeChunker
import re

class JSChunker(BaseCodeChunker):
    def __init__(self):
        super().__init__('javascript')
    
    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
        parser = self.get_parser()
        tree = parser.parse(bytes(content, "utf8"))
        root = tree.root_node
        chunks = []
        method_nodes = []
        method_code_map = {}
        method_name_map = {}
        
        def extract_params(node):
            params = []
            param_list = self.find_child_by_type(node, "formal_parameters")
            if param_list:
                for p in param_list.children:
                    if p.type == "identifier":
                        param_text = self.extract_node_text(p, content)
                        params.append(param_text)
            return params
        
        def walk(node, class_stack=None):
            if class_stack is None:
                class_stack = []
            
            if node.type == "class_declaration":
                name = self.find_identifier(node, content)
                class_stack.append(name)
                for child in node.children:
                    walk(child, class_stack)
                class_stack.pop()
                return
            
            if node.type in ("method_definition", "function_declaration"):
                name = None
                for child in node.children:
                    if child.type in ("property_identifier", "identifier"):
                        name = self.extract_node_text(child, content)
                        break
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                chunk = self.get_code(content, start_line, end_line + 1)
                parent = class_stack[-1] if class_stack else None
                method_nodes.append((name, node, chunk, start_line, end_line, parent))
                method_code_map[name] = chunk
                method_name_map[(parent, name)] = chunk
            
            for child in node.children:
                walk(child, class_stack)
        
        walk(root)
        
        # After collecting all methods, analyze method_calls for each method
        for name, node, chunk, start_line, end_line, parent in method_nodes:
            method_calls = set()
            for called_name in re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', chunk):
                if called_name != name and (called_name in method_code_map):
                    method_calls.add(called_name)
            doc = self.create_document(
                chunk=chunk,
                file_path=file_path,
                chunk_type="function",
                name=name,
                start_line=start_line,
                end_line=end_line,
                diff_lines=diff_lines,
                parent=parent,
                parameters=extract_params(node),
                method_calls=list(method_calls)
            )
            chunks.append(doc)
        return chunks 