import os
import json
import requests

from src.code_review.core import Utils

class APIClient:
    def __init__(self):
        self.api_url = os.getenv("AI_URL")
        self.model_name = os.getenv("API_MODEL", "qwen2.5-coder:32b")
        self.api_key = os.getenv("API_KEY", "")

    def _call_ollama_server(self, system_prompt: str, human_prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model_name,
                    "system": system_prompt,
                    "prompt": human_prompt,
                    "stream": False,
                    "options": {
                        "temperature": float(os.getenv("API_TEMPERATURE", "0")),
                        "top_p": float(os.getenv("API_TOP_P", "1.0")),
                        "top_k": int(os.getenv("API_TOP_K", "50")),
                        "repeat_penalty": float(os.getenv("API_REPEAT_PENALTY", "1.1")),
                        "seed": int(os.getenv("API_SEED", "42"))
                    }
                },
                verify=False,
                timeout=int(os.getenv("API_TIMEOUT", "120"))
            )
            response.raise_for_status()

            json_response = response.json()

            # Ollama response format
            if "response" in json_response:
                return json_response["response"]
            else:
                Utils.debug_print(f"[DEBUG] Unexpected Ollama response structure: {json_response}")
                raise ValueError("Invalid response format from Ollama API")

        except requests.exceptions.RequestException as e:
            Utils.debug_print(f"[DEBUG] Ollama API network error: {e}")
            raise RuntimeError(f"Ollama API network call failed: {str(e)}")
        except json.JSONDecodeError as e:
            Utils.debug_print(f"[DEBUG] Ollama API JSON decode error: {e}")
            raise RuntimeError(f"Failed to parse Ollama API response: {str(e)}")
        except Exception as e:
            Utils.debug_print(f"[DEBUG] Ollama API unexpected error: {e}")
            raise RuntimeError(f"Ollama API call failed: {str(e)}")

    def invoke_api(self, system_prompt: str, user_prompt: str) -> str:
        return self._call_ollama_server(system_prompt, user_prompt)
