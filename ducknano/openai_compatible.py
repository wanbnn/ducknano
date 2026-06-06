# -*- coding: utf-8 -*-
from typing import Optional

from ducknano.provider_client import provider_client


def list_models():
    return provider_client.list_models()


def get_model(model_id: str):
    return provider_client.get_model(model_id)


def list_files():
    return provider_client.list_files()


def upload_file(path: str, purpose: str = "assistants"):
    return provider_client.upload_file(path, purpose)


def create_embedding(input_text: str, model: Optional[str] = None):
    return provider_client.embeddings(input_text, model=model)


def transcribe_audio(path: str, model: str = "whisper-1"):
    return provider_client.transcribe_audio(path, model)


def generate_image(prompt: str, model: Optional[str] = None, size: str = "1024x1024"):
    return provider_client.generate_image(prompt, model=model, size=size)
