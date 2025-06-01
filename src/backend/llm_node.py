"""
This module handles communication with the LLM server running in Docker.
"""
import requests
import json
import time
from typing import Dict, Any, Optional, List
from .message import Message


class LLMNode:

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def generate_completion(
            self,
            prompt: str,
            max_tokens: int = 500,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None
    ) -> Message:
        start_time = time.time()

        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop_sequences or [],
            "stream": False
        }

        try:
            response = self.session.post(
                f"{self.base_url}/completion",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "").strip()
                tokens_used = result.get("tokens_predicted", 0) + result.get("tokens_evaluated", 0)

                processing_time = time.time() - start_time

                return Message(
                    role="assistant",
                    content=content,
                    tokens_used=tokens_used,
                    processing_time=round(processing_time, 2)
                )
            else:
                error_msg = f"LLM server returned status {response.status_code}: {response.text}"
                print(error_msg)
                return Message(
                    role="assistant",
                    content=f"Error: {error_msg}",
                    processing_time=round(time.time() - start_time, 2)
                )

        except Exception as e:
            error_msg = f"Error communicating with LLM server: {str(e)}"
            print(error_msg)
            return Message(
                role="assistant",
                content=f"Error: {error_msg}",
                processing_time=round(time.time() - start_time, 2)
            )

    def chat_completion(
            self,
            messages: List[Dict[str, str]],
            max_tokens: int = 500,
            temperature: float = 0.7
    ) -> Message:
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append("Assistant:")
        prompt = "\n\n".join(prompt_parts)

        return self.generate_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=["User:", "System:"]
        )