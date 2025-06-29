"""
Common wrapper around the OpenAI Python client so we can swap
between GPT-4o-mini (cloud) and an Ollama-served Llama model
without changing the rest of the code-base.

Usage
-----
>>> from summarizer.backends import choose_backend
>>> llm = choose_backend("gpt4o")          # cloud
>>> llm.chat([{"role": "user", "content": "Hello"}])
"""

from __future__ import annotations

import os
from typing import List, Dict, Literal, TypedDict

from openai import OpenAI

# --------------------------- type helpers ---------------------------


class Message(TypedDict):
    role: Literal["user", "system", "assistant"]
    content: str


# ------------------------------ classes -----------------------------


class BaseBackend:
    """Minimal interface every backend must implement."""

    def chat(self, messages: List[Message], **kwargs) -> str:  # noqa: D401
        """Send a list of messages and return the assistant’s reply."""
        raise NotImplementedError


class GPT4oBackend(BaseBackend):
    """Cloud – GPT-4o-mini via the default OpenAI endpoint."""

    def __init__(self) -> None:
        self.client = OpenAI()  # reads OPENAI_API_KEY from env

    def chat(self, messages: List[Message], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=kwargs.get("temperature", 0.2),
        )
        return response.choices[0].message.content.strip()


class OllamaBackend(BaseBackend):
    """Local – any Llama model served by Ollama’s OpenAI-compatible proxy."""

    def __init__(self, model: str = "llama3.2") -> None:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        # The API-key value is ignored by Ollama but required by the OpenAI client.
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self.model = model

    def chat(self, messages: List[Message], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.2),
        )
        return response.choices[0].message.content.strip()


# --------------------------- factory helper -------------------------


def choose_backend(
    engine: Literal["gpt4o", "llama"],
    model: str | None = None,
) -> BaseBackend:
    """Return an instantiated backend based on the `--backend` CLI flag."""
    if engine == "gpt4o":
        return GPT4oBackend()
    if engine == "llama":
        return OllamaBackend(model or "llama3.2")
    raise ValueError(f"Unknown backend: {engine!r}")
