from typing import List, Dict
import time

from src.code_review.core.schemas import RepoInfo


class MockFileFetcher:
    def __init__(self):
        self.mock_files = {
            'Backend/Controllers/ProductController.cs': '''
        using Microsoft.AspNetCore.Mvc;
        namespace Backend.Controllers {
            public class ProductController : Controller {
                public IActionResult GetProductReviews(int id) {
                    var product = _productRepository.GetById(id);
                    var reviews = new List<Review>();
                    foreach (var reviewId in product.ReviewIds) {
                        reviews.Add(_reviewRepository.GetById(reviewId));
                    }
                    return Ok(reviews);
                }
            }
        }
        '''.strip(),
        }

    def fetch_files_parallel(self, documents: List, repo_info: RepoInfo) -> Dict[str, str]:
        file_contents = {}
        time.sleep(3)  # Simulate delay for testing parallel execution
        for doc in documents:
            file_path = doc.metadata.get('file_path')
            file_contents[file_path] = self._get_mock_content(file_path)
        return file_contents


    def _get_mock_content(self, file_path: str) -> str:
        if file_path in self.mock_files:
            return self.mock_files[file_path]
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        # Generate code mock by extension
        if ext == 'ts':
            return "export function mock() { return 'mock'; }"
        elif ext == 'js':
            return "function mock() { return 'mock'; }"
        elif ext == 'cs':
            return "public class Mock { public string Hello() => \"mock\"; }"
        elif ext == 'html':
            return "<div>Mock HTML</div>"
        elif ext == 'scss':
            return ".mock { color: #999; }"
        else:
            return f"// MOCK: No content for {file_path}" 