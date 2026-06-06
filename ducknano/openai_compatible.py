# -*- coding: utf-8 -*-
import os
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from ducknano.config import PROVIDER_CONFIG, provider_endpoint, provider_headers


def json_headers() -> dict:
    return provider_headers()


def auth_headers() -> dict:
    headers = provider_headers().copy()
    headers.pop("Content-Type", None)
    return headers


def request_json(method: str, path: str, **kwargs) -> Dict[str, Any]:
    response = requests.request(
        method,
        provider_endpoint(path),
        headers=json_headers(),
        timeout=kwargs.pop("timeout", 60),
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def list_models() -> Dict[str, Any]:
    return request_json("GET", "/models")


def get_model(model_id: str) -> Dict[str, Any]:
    return request_json("GET", f"/models/{quote(model_id, safe='')}")


def list_files() -> Dict[str, Any]:
    return request_json("GET", "/files")


def upload_file(path: str, purpose: str = "assistants") -> Dict[str, Any]:
    with open(path, "rb") as f:
        response = requests.post(
            provider_endpoint("/files"),
            headers=auth_headers(),
            data={"purpose": purpose},
            files={"file": (os.path.basename(path), f)},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def create_embedding(input_text: str, model: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "model": model or PROVIDER_CONFIG.get("embedding_model") or PROVIDER_CONFIG.get("model") or "any",
        "input": input_text,
    }
    return request_json("POST", "/embeddings", json=payload, timeout=120)


def transcribe_audio(path: str, model: str = "whisper-1") -> Dict[str, Any]:
    with open(path, "rb") as f:
        response = requests.post(
            provider_endpoint("/audio/transcriptions"),
            headers=auth_headers(),
            data={"model": model},
            files={"file": (os.path.basename(path), f)},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def generate_image(prompt: str, model: Optional[str] = None, size: str = "1024x1024") -> Dict[str, Any]:
    payload = {
        "model": model or "gpt-image-1",
        "prompt": prompt,
        "size": size,
    }
    return request_json("POST", "/images/generations", json=payload, timeout=180)
