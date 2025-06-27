from typing import List
from langchain.schema import Document
from .typescript_chunker import TypeScriptCodeChunker

class AngularCodeChunker(TypeScriptCodeChunker):
    def __init__(self):
        super().__init__()
        # Override language for Angular
        self.language_name = 'angular'
        self._setup_language()
    
    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
        parser = self.get_parser()
        tree = parser.parse(bytes(content, "utf8"))
        root = tree.root_node
        chunks = []
        
        def extract_decorators(node):
            decos = []
            for child in node.children:
                if child.type == "decorator":
                    decos.append(self.extract_node_text(child, content))
            return decos
        
        def get_angular_type(decorators):
            for deco in decorators:
                if "@Component" in deco:
                    return "component"
                if "@Injectable" in deco:
                    return "service"
            return None
        
        def walk(node, class_stack=None):
            if class_stack is None:
                class_stack = []
            
            if node.type == "class_declaration":
                name = self.find_identifier(node, content)
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                chunk = self.get_code(content, start_line, end_line + 1)
                decorators = extract_decorators(node)
                angular_type = get_angular_type(decorators)
                
                if angular_type:
                    chunks.append(self.create_document(
                        chunk=chunk,
                        file_path=file_path,
                        chunk_type=angular_type,
                        name=name,
                        start_line=start_line,
                        end_line=end_line,
                        diff_lines=diff_lines,
                        parent=class_stack[-1] if class_stack else None,
                        decorators=decorators
                    ))
                
                class_stack.append(name)
                for child in node.children:
                    walk(child, class_stack)
                class_stack.pop()
                return
            
            # fallback: dùng logic TypeScript cho các node còn lại
            if node.type in ("method_definition", "function_declaration"):
                # Gọi lại logic TypeScriptCodeChunker (super) cho function/method
                # Sử dụng lại extract_params, extract_return_type, extract_access_modifier từ TypeScriptCodeChunker
                name = None
                for child in node.children:
                    if child.type in ("property_identifier", "identifier"):
                        name = self.extract_node_text(child, content)
                        break
                
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                chunk = self.get_code(content, start_line, end_line + 1)
                
                # Use parent class methods if available
                params = self.extract_params(node, content) if hasattr(self, 'extract_params') else []
                return_type = self.extract_return_type(node, content) if hasattr(self, 'extract_return_type') else None
                access_modifier = self.extract_access_modifier(node, content) if hasattr(self, 'extract_access_modifier') else None
                decorators = extract_decorators(node)
                
                chunks.append(self.create_document(
                    chunk=chunk,
                    file_path=file_path,
                    chunk_type="function",
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    diff_lines=diff_lines,
                    parent=class_stack[-1] if class_stack else None,
                    parameters=params,
                    return_type=return_type,
                    access_modifier=access_modifier,
                    decorators=decorators
                ))
            
            for child in node.children:
                walk(child, class_stack)
        
        walk(root)
        return chunks 