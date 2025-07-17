from typing import List
from langchain.schema import Document
from .base_chunker import BaseCodeChunker
import re

class CSharpCodeChunker(BaseCodeChunker):
    def __init__(self):
        super().__init__('c_sharp')
    
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
            param_list = self.find_child_by_type(node, "parameter_list")
            if param_list:
                for p in param_list.children:
                    if p.type == "parameter":
                        param_text = self.extract_node_text(p, content)
                        params.append(param_text)
            return params
        
        def extract_return_type(node):
            # Look for return type in method declaration
            # In C#, the return type comes before the method name
            for child in node.children:
                if child.type == "predefined_type":
                    return self.extract_node_text(child, content)
                elif child.type == "identifier":
                    # This could be a custom type or generic type
                    return self.extract_node_text(child, content)
                elif child.type == "generic_name":
                    # Handle generic types like IActionResult<T>, List<T>, etc.
                    return self.extract_node_text(child, content)
                elif child.type == "qualified_name":
                    # Handle qualified names like System.Collections.Generic.List<T>
                    return self.extract_node_text(child, content)

            # Alternative approach: find type node more specifically
            # Look for the pattern: [modifiers] return_type method_name(params)
            children = node.children
            for i, child in enumerate(children):
                if child.type == "identifier" and i > 0:
                    # Check if previous node could be return type
                    prev_child = children[i - 1]
                    if prev_child.type in ["predefined_type", "identifier", "generic_name", "qualified_name"]:
                        return self.extract_node_text(prev_child, content)

            return None
        
        def extract_access_modifier(node):
            # Access modifiers appear at the beginning of method declaration
            for child in node.children:
                if child.type in ("public", "private", "protected", "internal"):
                    return child.type
                elif child.type == "modifier":
                    # Some parsers might wrap modifiers in a modifier node
                    modifier_text = self.extract_node_text(child, content).strip()
                    if modifier_text in ("public", "private", "protected", "internal"):
                        return modifier_text

            # Alternative approach: check if any child contains modifier keywords
            for child in node.children:
                child_text = self.extract_node_text(child, content).strip()
                if child_text in ("public", "private", "protected", "internal"):
                    return child_text

            return None

        def extract_method_name(node):
            # Method name is typically an identifier that comes after return type
            # and before parameter list
            children = node.children
            param_list_found = False

            # Find parameter list first
            for child in children:
                if child.type == "parameter_list":
                    param_list_found = True
                    break

            if param_list_found:
                for i, child in enumerate(children):
                    if child.type == "parameter_list" and i > 0:
                        # Check previous nodes for method name
                        for j in range(i - 1, -1, -1):
                            if children[j].type == "identifier":
                                return self.extract_node_text(children[j], content)

            return self.find_identifier(node, content)
        
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
                class_stack.append(name)
                for child in node.children:
                    walk(child, class_stack)
                class_stack.pop()
                return
            
            if node.type == "method_declaration":
                name = extract_method_name(node)
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
            # Find method calls inside this method
            method_calls = set()
            # Simple regex for method calls: name(...)
            for called_name in re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', chunk):
                # Only add if called_name is a method in the same class
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
                return_type=extract_return_type(node),
                access_modifier=extract_access_modifier(node),
                attributes=extract_attributes(node),
                method_calls=list(method_calls)
            )
            chunks.append(doc)
        return chunks 