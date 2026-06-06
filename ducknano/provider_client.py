# -*- coding: utf-8 -*-
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from ducknano.config import PROVIDER_CONFIG, provider_endpoint, provider_headers


class ProviderError(RuntimeError):
    pass


class ProviderClient:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or PROVIDER_CONFIG

    def endpoint(self, path: str, base_url: str = "") -> str:
        if base_url:
            return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        return provider_endpoint(path)

    def json_headers(self, api_key: str = "") -> dict:
        if api_key:
            return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        return provider_headers()

    def auth_headers(self, api_key: str = "") -> dict:
        headers = self.json_headers(api_key=api_key).copy()
        headers.pop("Content-Type", None)
        return headers

    def request_json(self, method: str, path: str, *, base_url: str = "", api_key: str = "", timeout: int = 60, **kwargs) -> Dict[str, Any]:
        response = requests.request(
            method,
            self.endpoint(path, base_url=base_url),
            headers=self.json_headers(api_key=api_key),
            timeout=timeout,
            **kwargs,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ProviderError(f"{response.status_code} {response.text[:500]}") from e
        return response.json()

    def list_models(self, *, base_url: str = "", api_key: str = "") -> Dict[str, Any]:
        return self.request_json("GET", "/models", base_url=base_url, api_key=api_key, timeout=20)

    def model_ids(self, *, base_url: str = "", api_key: str = "") -> List[str]:
        data = self.list_models(base_url=base_url, api_key=api_key).get("data", [])
        model_ids = [
            str(item["id"])
            for item in data
            if isinstance(item, dict) and item.get("id")
        ]
        return sorted(set(model_ids), key=str.lower)

    def get_model(self, model_id: str) -> Dict[str, Any]:
        return self.request_json("GET", f"/models/{quote(model_id, safe='')}", timeout=20)

    def chat_completions(self, payload: dict, *, stream: bool = True, timeout: int = 1240, retries: int = 2):
        last_error = None
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    self.endpoint("/chat/completions"),
                    headers=self.json_headers(),
                    json=payload,
                    timeout=timeout,
                    stream=stream,
                )
                if response.status_code >= 500 and attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return response
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ) as e:
                last_error = e
                if attempt >= retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise ProviderError(f"chat/completions connection failed after {retries + 1} attempts: {last_error}")

    def embeddings(self, input_text: str, model: Optional[str] = None, *, timeout: int = 120) -> Dict[str, Any]:
        payload = {
            "model": model or self.config.get("embedding_model") or self.config.get("model") or "any",
            "input": input_text,
        }
        return self.request_json("POST", "/embeddings", json=payload, timeout=timeout)

    def post_embeddings_payload(self, payload: dict, *, timeout: int = 60) -> Dict[str, Any]:
        return self.request_json("POST", "/embeddings", json=payload, timeout=timeout)

    def list_files(self) -> Dict[str, Any]:
        return self.request_json("GET", "/files", timeout=60)

    def upload_file(self, path: str, purpose: str = "assistants") -> Dict[str, Any]:
        with open(path, "rb") as f:
            response = requests.post(
                self.endpoint("/files"),
                headers=self.auth_headers(),
                data={"purpose": purpose},
                files={"file": (os.path.basename(path), f)},
                timeout=120,
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ProviderError(f"{response.status_code} {response.text[:500]}") from e
        return response.json()

    def transcribe_audio(self, path: str, model: str = "whisper-1") -> Dict[str, Any]:
        with open(path, "rb") as f:
            response = requests.post(
                self.endpoint("/audio/transcriptions"),
                headers=self.auth_headers(),
                data={"model": model},
                files={"file": (os.path.basename(path), f)},
                timeout=120,
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ProviderError(f"{response.status_code} {response.text[:500]}") from e
        return response.json()

    def generate_image(self, prompt: str, model: Optional[str] = None, size: str = "1024x1024") -> Dict[str, Any]:
        payload = {
            "model": model or "gpt-image-1",
            "prompt": prompt,
            "size": size,
        }
        return self.request_json("POST", "/images/generations", json=payload, timeout=180)

    def native_embedding_url(self) -> str:
        return self.endpoint("/embedding").replace("/v1/embedding", "/embedding")

    def native_embedding(self, content: str, *, timeout: int = 60):
        response = requests.post(
            self.native_embedding_url(),
            headers=self.json_headers(),
            json={"content": content},
            timeout=timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ProviderError(f"{response.status_code} {response.text[:500]}") from e
        return response.json()


provider_client = ProviderClient()
