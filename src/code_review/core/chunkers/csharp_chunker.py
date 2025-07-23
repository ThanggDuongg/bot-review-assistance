from typing import List, Optional, Set
from langchain.schema import Document
from .base_chunker import BaseCodeChunker


class CSharpCodeChunker(BaseCodeChunker):
    def __init__(self):
        super().__init__('c_sharp')

    def chunk_code(self, content: str, file_path: str, diff_lines: List[int]) -> List[Document]:
        parser = self.get_parser()

        # Handle potential BOM in C# files
        if content.startswith('\ufeff'):
            content = content[1:]

        try:
            tree = parser.parse(bytes(content, "utf8"))
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")
            return []

        root = tree.root_node
        chunks = []

        def extract_method_name(method_node):
            """Extract method name from method declaration"""
            # Look for identifier node right before parameter_list
            children = list(method_node.children)

            for i, child in enumerate(children):
                if child.type == "parameter_list" and i > 0:
                    # Check previous node - it should be the method name
                    potential_name_node = children[i - 1]
                    if potential_name_node.type == "identifier":
                        return self.extract_node_text(potential_name_node, content)

            # Fallback: search for any identifier before parameter_list
            for child in children:
                if child.type == "identifier":
                    return self.extract_node_text(child, content)

            return "UnknownMethod"

        def extract_return_type(method_node):
            """Extract return type from method declaration"""
            children = list(method_node.children)

            # Find method name position first
            method_name_index = None
            for i, child in enumerate(children):
                if child.type == "parameter_list" and i > 0:
                    if children[i - 1].type == "identifier":
                        method_name_index = i - 1
                        break

            if method_name_index is None or method_name_index <= 0:
                return "void"

            # Return type should be before method name, skip modifiers
            for i in range(method_name_index - 1, -1, -1):
                child = children[i]
                if child.type in ["predefined_type", "identifier", "generic_name",
                                  "qualified_name", "array_type", "nullable_type"]:
                    return self.extract_node_text(child, content)

            return "void"

        def extract_parameters(method_node):
            """Extract parameters from method declaration"""
            params = []

            # Find parameter_list
            param_list_node = self.find_child_by_type(method_node, "parameter_list")
            if not param_list_node:
                return params

            # Extract each parameter
            for child in param_list_node.children:
                if child.type == "parameter":
                    param_text = self.extract_node_text(child, content)
                    if param_text and param_text not in ["(", ")", ","]:
                        params.append(param_text.strip())

            return params

        def extract_access_modifier(method_node):
            """Extract access modifier from method declaration"""
            for child in method_node.children:
                if child.type == "modifier":
                    modifier_text = self.extract_node_text(child, content)
                    if modifier_text in ["public", "private", "protected", "internal"]:
                        return modifier_text
            return "private"  # Default in C#

        def extract_attributes(method_node):
            """Extract attributes from method declaration"""
            attributes = []

            # Look for attribute_list nodes that come before the method
            parent_node = method_node.parent
            if not parent_node:
                return attributes

            # Find this method's position in parent's children
            method_index = -1
            for i, child in enumerate(parent_node.children):
                if child == method_node:
                    method_index = i
                    break

            if method_index == -1:
                return attributes

            # Look backwards from method position for attribute_list nodes
            for i in range(method_index - 1, -1, -1):
                child = parent_node.children[i]

                if child.type == "attribute_list":
                    # Extract attributes from this attribute_list
                    for attr_child in child.children:
                        if attr_child.type == "attribute":
                            attr_text = self.extract_node_text(attr_child, content)
                            if attr_text and attr_text not in ["[", "]", ","]:
                                attributes.append(attr_text.strip())
                elif child.type not in ["comment", "modifier"]:
                    # Stop if we hit something that's not an attribute, comment, or modifier
                    break

            # Reverse to maintain original order
            attributes.reverse()
            return attributes

        def extract_method_calls(method_node):
            """Extract method calls from within the method body with better classification"""
            method_calls = []

            # Known system/framework namespaces and types to ignore
            SYSTEM_TYPES = {
                'string', 'String', 'int', 'Int32', 'double', 'Double', 'bool', 'Boolean',
                'DateTime', 'TimeSpan', 'Guid', 'object', 'Object', 'typeof', 'nameof',
                'Console', 'Debug', 'Trace', 'Math', 'Convert', 'Environment',
                'System', 'Microsoft', 'Newtonsoft'
            }

            SYSTEM_STATIC_METHODS = {
                'string.IsNullOrEmpty', 'string.IsNullOrWhiteSpace', 'string.Join',
                'string.Format', 'string.Concat', 'Path.Combine', 'File.ReadAllText',
                'Directory.Exists', 'Console.WriteLine', 'Debug.WriteLine',
                'Math.Max', 'Math.Min', 'Convert.ToInt32', 'DateTime.Now'
            }

            def is_system_call(full_call_text):
                """Check if this is a system/framework call that shouldn't be used as context"""
                # Check for direct system type calls
                for sys_type in SYSTEM_TYPES:
                    if full_call_text.startswith(f"{sys_type}.") or full_call_text == sys_type:
                        return True

                # Check for known static method patterns
                for static_method in SYSTEM_STATIC_METHODS:
                    if full_call_text.startswith(static_method):
                        return True

                # Check for generic type patterns like typeof(T).GetProperties()
                if 'typeof(' in full_call_text:
                    return True

                # Check for property/field access on system types
                if any(full_call_text.startswith(f"{sys}.") for sys in ['this.', 'base.']):
                    return False  # These might be internal

                return False

            def classify_method_call(call_text, method_name):
                """Classify the method call to determine if it's worth including as context"""
                full_call = call_text.split('(')[0] if '(' in call_text else call_text

                # Remove whitespace and get clean call
                full_call = full_call.strip()

                if is_system_call(full_call):
                    return {
                        "name": method_name,
                        "full_call": full_call,
                        "call_type": "system",
                        "is_context_worthy": False,
                        "reason": "System/Framework method"
                    }

                # Check for property access (likely not a method we have context for)
                if not call_text.endswith(')') and '(' not in call_text:
                    return {
                        "name": method_name,
                        "full_call": full_call,
                        "call_type": "property",
                        "is_context_worthy": False,
                        "reason": "Property access, not method call"
                    }

                # Check for extension methods or fluent API calls
                if '.' in full_call:
                    parts = full_call.split('.')
                    receiver = '.'.join(parts[:-1])

                    # If receiver looks like a variable (lowercase start), might be internal
                    if receiver and receiver[0].islower() and not is_system_call(receiver):
                        return {
                            "name": method_name,
                            "full_call": full_call,
                            "receiver": receiver,
                            "call_type": "instance_method",
                            "is_context_worthy": True,
                            "reason": "Instance method call on local variable"
                        }

                    # If receiver is 'this' or class name, definitely internal
                    if receiver in ['this'] or receiver[0].isupper():
                        return {
                            "name": method_name,
                            "full_call": full_call,
                            "receiver": receiver,
                            "call_type": "internal_method",
                            "is_context_worthy": True,
                            "reason": "Internal class method"
                        }
                else:
                    # Direct method call without receiver - likely internal
                    return {
                        "name": method_name,
                        "full_call": full_call,
                        "call_type": "direct_method",
                        "is_context_worthy": True,
                        "reason": "Direct method call, likely internal"
                    }

                return {
                    "name": method_name,
                    "full_call": full_call,
                    "call_type": "unknown",
                    "is_context_worthy": False,
                    "reason": "Unable to classify"
                }

            def collect_invocations(node):
                """Recursively collect invocation_expression nodes with better analysis"""
                if node.type == "invocation_expression":
                    # Extract the full method call text
                    call_text = self.extract_node_text(node, content)
                    if not call_text:
                        return

                    # Extract method name more accurately
                    method_name = ""

                    # Try to find member access (obj.Method())
                    member_access = self.find_child_by_type(node, "member_access_expression")
                    if member_access:
                        # Get the rightmost identifier (method name)
                        identifiers = []
                        for child in member_access.children:
                            if child.type == "identifier":
                                identifiers.append(self.extract_node_text(child, content))
                        if identifiers:
                            method_name = identifiers[-1]  # Last identifier is method name
                    else:
                        # Simple method call (Method())
                        identifier = self.find_child_by_type(node, "identifier")
                        if identifier:
                            method_name = self.extract_node_text(identifier, content)

                    if method_name:
                        call_info = classify_method_call(call_text, method_name)
                        method_calls.append(call_info)

                # Continue recursively through children
                for child in node.children:
                    collect_invocations(child)

            # Find the method body and collect invocations
            method_body = self.find_child_by_type(method_node, "block")
            if method_body:
                collect_invocations(method_body)

            return method_calls

        def walk_ast(node, class_stack=None):
            """Walk the AST and collect method information"""
            if class_stack is None:
                class_stack = []

            # Handle class declarations
            if node.type == "class_declaration":
                class_name = self.find_identifier(node, content)
                if class_name:
                    class_stack.append(class_name)

                    # Process children
                    for child in node.children:
                        walk_ast(child, class_stack)

                    class_stack.pop()
                return

            # Handle method declarations
            if node.type == "method_declaration":
                name = extract_method_name(node)
                start_line = node.start_point[0]

                # Find method body to get correct end position
                method_body = self.find_child_by_type(node, "block")
                if method_body:
                    end_line = method_body.end_point[0]
                else:
                    end_line = node.end_point[0]

                # Extract the method chunk
                chunk = self.get_code(content, start_line, end_line + 1)
                parent = class_stack[-1] if class_stack else None

                # Extract additional metadata
                params = extract_parameters(node)
                return_type = extract_return_type(node)
                access_modifier = extract_access_modifier(node)
                attributes = extract_attributes(node)
                method_calls = extract_method_calls(node)

                # Create document
                doc = self.create_document(
                    chunk=chunk,
                    file_path=file_path,
                    chunk_type="function",
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    diff_lines=diff_lines,
                    parent=parent,
                    parameters=params,
                    return_type=return_type,
                    access_modifier=access_modifier,
                    attributes=attributes,
                    method_calls=method_calls
                )
                chunks.append(doc)
                return

            # Continue walking for other nodes
            for child in node.children:
                walk_ast(child, class_stack)

        # Execute the analysis
        walk_ast(root)
        return chunks