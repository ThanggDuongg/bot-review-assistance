import os
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.code_review.core import Utils
from src.code_review.core.schemas import RepoInfo


class FileFetcher:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('SC_URL')
        self.max_workers = 5
        self.retry_attempts = 3
        self.retry_delay = 1

    def fetch_files_parallel(self, documents: List, repo_info: RepoInfo) -> Dict[str, str]:
        file_paths = list(set([
            doc.metadata.get('file_path') for doc in documents
            if hasattr(doc, 'metadata') and doc.metadata.get('file_path')
        ]))

        if not file_paths:
            return {}

        file_contents = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._fetch_single_file, file_path, repo_info): file_path
                for file_path in file_paths
            }

            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    content = future.result()
                    if content:
                        file_contents[file_path] = content
                except Exception as e:
                    Utils.debug_print(f"Failed to fetch {file_path}: {str(e)}")

        return file_contents

    def _fetch_single_file(self, file_path: str, repo_info: RepoInfo) -> Optional[str]:
        project = repo_info.get('project')
        repo = repo_info.get('repo')
        branch = repo_info.get('branch')
        token = repo_info.get('token')

        if not project or not repo:
            Utils.debug_print(f"Missing project or repo info for {file_path}")
            return None
        if not token:
            Utils.debug_print(f"Missing bitbucket token for {file_path}")
            return None

        url = f"{self.base_url}/rest/api/latest/projects/{project}/repos/{repo}/raw/{file_path}?at={branch}"
        headers = {"Authorization": f"Bearer {token}"}

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
                time.sleep(self.retry_delay * (2 ** attempt))  # exponential backoff

        return None