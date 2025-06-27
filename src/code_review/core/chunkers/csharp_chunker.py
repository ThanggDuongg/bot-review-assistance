from typing import List
from langchain.schema import Document
from .base_chunker import BaseCodeChunker

class CSharpCodeChunker(BaseCodeChunker):
    def __init__(self):
        super().__init__('c_sharp')
    
    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
        parser = self.get_parser()
        tree = parser.parse(bytes(content, "utf8"))
        root = tree.root_node
        chunks = []
        
        def extract_params(node):
            params = []
            param_list = self.find_child_by_type(node, "parameter_list")
            if param_list:
                for p in param_list.children:
                    if p.type == "parameter":
                        param_text = self.extract_node_text(p, content)
                        params.append(param_text)
            return params
        
        def extract_return_type(node):
            type_node = self.find_child_by_type(node, "type")
            if type_node:
                return self.extract_node_text(type_node, content)
            return None
        
        def extract_access_modifier(node):
            for child in node.children:
                if child.type in ("public", "private", "protected", "internal"):
                    return child.type
            return None
        
        def extract_attributes(node):
            attrs = []
            for child in node.children:
                if child.type == "attribute_list":
                    attrs.append(self.extract_node_text(child, content))
            return attrs
        
        def walk(node, class_stack=None):
            if class_stack is None:
                class_stack = []
            
            if node.type == "class_declaration":
                name = self.find_identifier(node, content)
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                chunk = self.get_code(content, start_line, end_line + 1)
                attributes = extract_attributes(node)
                
                chunks.append(self.create_document(
                    chunk=chunk,
                    file_path=file_path,
                    chunk_type="class",
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    diff_lines=diff_lines,
                    parent=class_stack[-1] if class_stack else None,
                    attributes=attributes
                ))
                
                class_stack.append(name)
                for child in node.children:
                    walk(child, class_stack)
                class_stack.pop()
                return
            
            if node.type == "method_declaration":
                name = self.find_identifier(node, content)
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                chunk = self.get_code(content, start_line, end_line + 1)
                
                chunks.append(self.create_document(
                    chunk=chunk,
                    file_path=file_path,
                    chunk_type="function",
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    diff_lines=diff_lines,
                    parent=class_stack[-1] if class_stack else None,
                    parameters=extract_params(node),
                    return_type=extract_return_type(node),
                    access_modifier=extract_access_modifier(node),
                    attributes=extract_attributes(node)
                ))
            
            for child in node.children:
                walk(child, class_stack)
        
        walk(root)
        return chunks 