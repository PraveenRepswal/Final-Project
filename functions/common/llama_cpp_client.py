"""Utilities for interacting with a llama.cpp OpenAI-compatible server."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Generator, Optional

import requests

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _candidate_base_urls() -> list[str]:
    """Return preferred base URLs for llama.cpp server probing."""
    configured = os.getenv("LLAMA_CPP_BASE_URL", "").strip().rstrip("/")
    if configured:
        return [configured]

    # Common defaults: llama-cpp-python server uses 8000, llama-server often uses 8080.
    return ["http://127.0.0.1:8000", "http://127.0.0.1:8080"]


def _endpoint_candidates(base_url: str) -> list[str]:
    """Return endpoint candidates in preference order."""
    return [
        f"{base_url}/v1/chat/completions",  # OpenAI-compatible chat endpoint
        f"{base_url}/completion",  # Legacy llama.cpp completion endpoint
    ]


def default_model() -> str:
    return _normalize_model_name(os.getenv("LLAMA_CPP_MODEL", "local-model"))


def _normalize_model_name(model_name: str) -> str:
    """Convert path-like model values to the id expected by /v1/chat/completions."""
    if not model_name:
        return "local-model"
    value = model_name.strip().strip('"').strip("'")
    if "\\" in value or "/" in value:
        return os.path.basename(value)
    return value


def _strip_think_tags(text: str) -> str:
    """Remove model-emitted think tags from output content."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("LLAMA_CPP_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def is_llama_cpp_available(timeout: int = 5) -> bool:
    """Best-effort health check for llama.cpp server."""
    candidates: list[str] = []
    for base_url in _candidate_base_urls():
        candidates.extend([f"{base_url}/health", f"{base_url}/v1/models"])

    for url in candidates:
        try:
            response = requests.get(url, headers=_headers(), timeout=timeout)
            if response.status_code < 400:
                return True
        except Exception:
            continue
    return False


def chat_completion(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    json_mode: bool = False,
    json_schema: Optional[dict[str, Any]] = None,
    timeout: int = 120,
    max_retries: int = 3,
) -> str:
    """Call llama.cpp and return generated text."""
    selected_model = _normalize_model_name(model or default_model())

    chat_payload: dict[str, object] = {
        "model": selected_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "reasoning": False,
    }
    if json_mode:
        response_format: dict[str, Any] = {"type": "json_object"}
        if json_schema:
            response_format["schema"] = json_schema
        chat_payload["response_format"] = response_format

    legacy_payload: dict[str, object] = {
        "prompt": prompt,
        "temperature": temperature,
        "n_predict": max_tokens,
        "stream": False,
    }

    attempts = max(1, int(max_retries))
    last_error = ""

    for base_url in _candidate_base_urls():
        for url in _endpoint_candidates(base_url):
            payload = chat_payload if url.endswith("/v1/chat/completions") else legacy_payload
            for attempt in range(1, attempts + 1):
                try:
                    response = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()

                    if "choices" in data:
                        content = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                    else:
                        content = data.get("content", "")
                    return _strip_think_tags(content)
                except Exception as exc:
                    last_error = str(exc)
                    if attempt < attempts:
                        delay = 1.0 * (2 ** (attempt - 1))
                        logger.warning(
                            "llama.cpp request failed for %s (attempt %s/%s): %s. Retrying in %.1fs",
                            url,
                            attempt,
                            attempts,
                            last_error,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    break

    raise ConnectionError(f"llama.cpp request failed: {last_error}")


def stream_chat_completion(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    timeout: int = 120,
) -> Generator[str, None, None]:
    """Stream text from llama.cpp server endpoint."""
    selected_model = _normalize_model_name(model or default_model())

    chat_payload = {
        "model": selected_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    legacy_payload = {
        "prompt": prompt,
        "temperature": temperature,
        "n_predict": max_tokens,
        "stream": True,
    }

    last_error = ""
    for base_url in _candidate_base_urls():
        for url in _endpoint_candidates(base_url):
            payload = chat_payload if url.endswith("/v1/chat/completions") else legacy_payload
            try:
                response = requests.post(url, headers=_headers(), json=payload, stream=True, timeout=timeout)
                response.raise_for_status()

                buffer = ""
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue

                    line = raw_line
                    if line.startswith("data: "):
                        line = line[6:]

                    if line.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(line)
                    except Exception:
                        continue

                    if "choices" in data:
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        chunk = choices[0].get("delta", {}).get("content", "")
                    else:
                        chunk = data.get("content", "")

                    if chunk:
                        buffer += chunk
                        yield _strip_think_tags(buffer)
                return
            except Exception as exc:
                last_error = str(exc)
                continue

    raise ConnectionError(f"llama.cpp stream request failed: {last_error}")
