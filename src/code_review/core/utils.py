import json
from typing import Optional, Any, List
import os
import multiprocessing
import subprocess
import re

class Utils:
    # Debug mode flag
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @staticmethod
    def debug_print(*args, **kwargs):
        if Utils.DEBUG_MODE:
            print(*args, **kwargs)
    
    @staticmethod
    def parse_json_from_response(response: str) -> Optional[dict]:
        response = response.strip()
        # Remove code block markers
        if response.startswith('```json'):
            response = response[len('```json'):].strip()
        if response.startswith('```'):
            response = response[len('```'):].strip()
        if response.endswith('```'):
            response = response[:-3].strip()

        # Fix common JSON issues before parsing
        response = Utils.fix_json_formatting(response)

        try:
            return json.loads(response)
        except Exception as e:
            print(response)
            print(f"[DEBUG] JSON parse error: {e}")
            return None

    @staticmethod
    def fix_json_formatting(json_str: str) -> str:
        # Fix trailing commas in arrays
        json_str = re.sub(r',(\s*])', r'\1', json_str)

        # Fix trailing commas in objects
        json_str = re.sub(r',(\s*})', r'\1', json_str)

        # Fix missing quotes around keys (if needed)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)

        # Fix single quotes to double quotes
        json_str = json_str.replace("'", '"')

        # Remove any trailing commas at the end
        json_str = re.sub(r',(\s*)$', r'\1', json_str)

        return json_str
    
    @staticmethod
    def extract_file_extension(file_path: str) -> str:
        return file_path.split('.')[-1] if '.' in file_path else ""
    
    @staticmethod
    def is_valid_code_file(file_path: str) -> bool:
        code_extensions = {
            'js', 'ts', 'jsx', 'tsx', 'cs'
        }
        return Utils.extract_file_extension(file_path).lower() in code_extensions
    
    @staticmethod
    def get_file_language_category(file_path: str) -> str:
        extension = Utils.extract_file_extension(file_path).lower()
        
        if extension in {'js', 'ts', 'jsx', 'tsx', 'html', 'css', 'scss'}:
            return "frontend"
        elif extension in {'cs'}:
            return "backend"
        elif extension in {'json', 'yml', 'yaml', 'xml', 'toml', 'ini'}:
            return "config"
        else:
            return "other"
    
    @staticmethod
    def calculate_content_size(content: str) -> int:
        return len(content)
    
    @staticmethod
    def estimate_tokens(content: Any, chars_per_token: int = 4) -> int:
        if isinstance(content, str):
            return len(content) // chars_per_token
        elif isinstance(content, int):
            return content // chars_per_token
        else:
            raise ValueError(f"Content must be string or int, got {type(content)}") 

    @staticmethod
    def detect_code_type(file_path: str) -> str:
        ext = Utils.extract_file_extension(file_path).lower()
        if ext == 'cs':
            return 'csharp'
        if ext in {'tsx', 'jsx'}:
            return 'react'
        if ext == 'js':
            return 'javascript'
        if ext == 'ts':
            if any(file_path.endswith(suffix) for suffix in [
                '.component.ts', '.service.ts', '.module.ts', 
                '.directive.ts', '.pipe.ts', '.guard.ts'
            ]):
                return 'angular'
            return 'typescript'
        return 'unknown' 

    @staticmethod
    def ensure_markdown_codeblock(code, lang='csharp'):
        if not code:
            return ''
        code = code.strip()
        if code.startswith('```'):
            return code
        return f'```{lang}\n{code}\n```'
    
    @staticmethod
    def get_optimal_thread_count(default_threads: int = 8) -> int:
        cpu_count = multiprocessing.cpu_count()
        # Use min of default_threads and cpu_count, but at least 2
        optimal_threads = max(2, min(default_threads, cpu_count))
        Utils.debug_print(f"CPU cores: {cpu_count}, using threads: {optimal_threads}")
        return optimal_threads

    @staticmethod
    def detect_gpu_vram_and_layers() -> int:
        # Try NVIDIA (nvidia-smi)
        try:
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=memory.total',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, check=True)
            vram_list = result.stdout.strip().split('\n')
            if vram_list and vram_list[0].isdigit():
                vram_mb = int(vram_list[0])
                vram_gb = vram_mb // 1024
                Utils.debug_print(f"Detected NVIDIA GPU VRAM: {vram_mb} MB ({vram_gb} GB)")
                if vram_gb >= 12:
                    return 40
                elif vram_gb >= 8:
                    return 20
                elif vram_gb >= 4:
                    return 10
                elif vram_gb >= 2: #TODO: [Test] Remove this condition
                    return 2
                else:
                    return 0
        except Exception as e:
            Utils.debug_print(f"No NVIDIA GPU detected or nvidia-smi not available: {e}")
        # Try AMD (rocm-smi)
        try:
            result = subprocess.run([
                'rocm-smi',
                '--showid',
                '--showproductname',
                '--showmeminfo', 'vram',
                '--json'
            ], capture_output=True, text=True, check=True)
            import json as _json
            data = _json.loads(result.stdout)
            # Try to get VRAM from the first GPU
            for gpu in data.get('card', []):
                vram_str = gpu.get('VRAM Total Memory (B)', None)
                if vram_str:
                    vram_gb = int(vram_str) // (1024 ** 3)
                    Utils.debug_print(f"Detected AMD GPU VRAM: {vram_str} bytes ({vram_gb} GB)")
                    if vram_gb >= 12:
                        return 40
                    elif vram_gb >= 8:
                        return 20
                    elif vram_gb >= 4:
                        return 10
                    else:
                        return 0
        except Exception as e:
            Utils.debug_print(f"No AMD GPU detected or rocm-smi not available: {e}")
        # Try Intel/OpenCL (clinfo)
        try:
            result = subprocess.run([
                'clinfo'
            ], capture_output=True, text=True, check=True)
            # Parse clinfo output for Global memory size
            lines = result.stdout.split('\n')
            vram_bytes = 0
            for line in lines:
                if 'Global memory size' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        mem_str = parts[1].strip().split(' ')[0].replace(',', '')
                        try:
                            vram_bytes = int(mem_str)
                        except Exception:
                            continue
                        break
            if vram_bytes > 0:
                vram_gb = vram_bytes // (1024 ** 3)
                Utils.debug_print(f"Detected Intel/OpenCL GPU VRAM: {vram_bytes} bytes ({vram_gb} GB)")
                if vram_gb >= 12:
                    return 40
                elif vram_gb >= 8:
                    return 20
                elif vram_gb >= 4:
                    return 10
                else:
                    return 0
        except Exception as e:
            Utils.debug_print(f"No Intel/OpenCL GPU detected or clinfo not available: {e}")
        return 0

    @staticmethod
    def count_total_lines(chunks) -> int:
        return sum(len(chunk.page_content.split('\n')) for chunk in chunks)