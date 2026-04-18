from __future__ import annotations

from functions.common.llama_cpp_client import default_model as llama_cpp_default_model

DEFAULT_OLLAMA_MODEL = "qwen3.5:2b"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
LLAMA_CPP_PROVIDER_ALIASES = {"llama.cpp", "llama_cpp", "llamacpp"}


def normalize_provider(provider: str | None) -> str:
    value = (provider or "ollama").strip().lower()
    if value in LLAMA_CPP_PROVIDER_ALIASES:
        return "llama.cpp"
    return value or "ollama"


def select_model_for_provider(
    provider: str | None,
    requested_model: str | None,
    *,
    prefer_requested: bool = True,
) -> str:
    normalized_provider = normalize_provider(provider)
    selected_model = (requested_model or "").strip()

    if normalized_provider == "gemini":
        if prefer_requested and selected_model and not selected_model.startswith("qwen"):
            return selected_model
        return DEFAULT_GEMINI_MODEL

    if normalized_provider == "llama.cpp":
        if prefer_requested and selected_model and not selected_model.startswith("qwen"):
            return selected_model
        return llama_cpp_default_model()

    return selected_model or DEFAULT_OLLAMA_MODEL