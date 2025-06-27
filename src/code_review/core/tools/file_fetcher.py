import os
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.code_review.core import Utils


class FileFetcher:
    def __init__(self, bitbucket_token: Optional[str] = None):
        self.bitbucket_token = bitbucket_token or os.getenv('BITBUCKET_TOKEN')
        self.base_url = "https://api.bitbucket.org/2.0"
        self.max_workers = 5  # Limit concurrent requests
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        
    def fetch_files_parallel(self, documents: List, repo_info: Dict) -> Dict[str, str]:
        file_paths = list(set([
            doc.metadata.get('file_path') for doc in documents
            if hasattr(doc, 'metadata') and doc.metadata.get('file_path')
        ]))
        
        if not file_paths:
            return {}
        
        file_contents = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all fetch tasks
            future_to_path = {
                executor.submit(self._fetch_single_file, file_path, repo_info): file_path
                for file_path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    content = future.result()
                    if content:
                        file_contents[file_path] = content
                except Exception as e:
                    Utils.debug_print(f"Failed to fetch {file_path}: {str(e)}")
        
        return file_contents
    
    def _fetch_single_file(self, file_path: str, repo_info: Dict) -> Optional[str]:
        workspace = repo_info.get('workspace')
        repo = repo_info.get('repo')
        branch = repo_info.get('branch', 'main')
        
        if not workspace or not repo:
            Utils.debug_print(f"Missing workspace or repo info for {file_path}")
            return None
        
        url = f"{self.base_url}/repositories/{workspace}/{repo}/src/{branch}/{file_path}"
        headers = {}
        
        if self.bitbucket_token:
            headers["Authorization"] = f"Bearer {self.bitbucket_token}"
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    Utils.debug_print(f"File not found: {file_path}")
                    return None
                elif response.status_code == 401:
                    Utils.debug_print(f"Unauthorized access to {file_path}")
                    return None
                else:
                    Utils.debug_print(f"HTTP {response.status_code} for {file_path}")
                    
            except requests.RequestException as e:
                Utils.debug_print(f"Request error for {file_path} (attempt {attempt + 1}): {str(e)}")
                
            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        return None