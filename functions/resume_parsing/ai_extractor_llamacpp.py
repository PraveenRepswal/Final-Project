"""AI-powered structured data extraction from resume text using llama.cpp server."""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

from functions.common.llama_cpp_client import chat_completion
from functions.common.models import ResumeData

from .ai_extractor import get_extraction_prompt, parse_resume_data_from_response

logger = logging.getLogger(__name__)


def extract_resume_data_llama_cpp(
    text: str,
    model: Optional[str] = None,
    return_debug: bool = False,
) -> Union[Optional[ResumeData], Tuple[Optional[ResumeData], str]]:
    """Extract structured resume data via llama.cpp OpenAI-compatible API."""
    prompt = f"""
    {get_extraction_prompt(text)}

    IMPORTANT: Output RAW JSON only. Do not wrap in markdown code blocks.
    """

    try:
        result_text = chat_completion(
            prompt=prompt,
            model=model,
            temperature=0.1,
            max_tokens=4096,
            json_mode=True,
            timeout=180,
            max_retries=3,
        )

        try:
            resume_data = parse_resume_data_from_response(text, result_text)
        except Exception as parse_err:
            logger.error("llama.cpp validation error: %s", parse_err)
            resume_data = None

        if return_debug:
            return resume_data, result_text
        return resume_data
    except Exception as exc:
        logger.error("llama.cpp extraction error: %s", exc)
        if return_debug:
            return None, f"Error: {exc}"
        return None
