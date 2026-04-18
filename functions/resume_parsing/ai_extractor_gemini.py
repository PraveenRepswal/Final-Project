"""AI-powered structured data extraction from resume text using Google GenAI SDK (google-genai)."""

import logging
import os
import json
import time
from typing import Optional, Tuple, Union

from google import genai
from google.genai import types

from .ai_extractor import get_extraction_prompt, parse_resume_data_from_response
from functions.common.models import ResumeData

logger = logging.getLogger(__name__)


def _is_retryable_gemini_error(error_msg: str) -> bool:
    """Return True when error appears temporary and should be retried."""
    if not error_msg:
        return False
    lowered = error_msg.lower()
    retryable_markers = [
        " 429",
        " 500",
        " 502",
        " 503",
        " 504",
        "unavailable",
        "resource exhausted",
        "deadline exceeded",
        "timed out",
        "connection reset",
        "temporary",
        "high demand",
    ]
    return any(marker in lowered for marker in retryable_markers)

def extract_resume_data_gemini(
    text: str,
    model: str = "gemini-2.5-flash",
    api_key: str = None,
    return_debug: bool = False,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.5,
) -> Union[Optional[ResumeData], Tuple[Optional[ResumeData], str]]:
    """
    Extract structured resume data using Gemini 2.x via google-genai SDK.
    Uses native JSON mode for reliability.
    
    Returns:
        ResumeData object if return_debug=False
        (ResumeData object, raw_response_str) if return_debug=True
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found.")
            if return_debug:
                return None, "Error: GEMINI_API_KEY not found."
            return None

    client = genai.Client(api_key=api_key)

    # Construct prompt
    base_prompt = get_extraction_prompt(text)

    prompt = f"""
    {base_prompt}

    IMPORTANT: Output RAW JSON only. Do not wrap in markdown code blocks.
    """

    last_error_msg = ""
    attempts = max(1, int(max_retries))

    for attempt in range(1, attempts + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            result_text = response.text or ""

            # Use the shared parser so Gemini and Ollama both benefit from
            # the same JSON extraction + schema normalization behavior.
            try:
                resume_data = parse_resume_data_from_response(text, result_text)
            except Exception as e:
                logger.error(f"Validation error: {e}")
                resume_data = None

            if return_debug:
                return resume_data, result_text
            return resume_data

        except Exception as e:
            last_error_msg = str(e)
            logger.error(f"Gemini Extraction Error (attempt {attempt}/{attempts}): {last_error_msg}")

            # WinError 10013 is Access Denied (Socket)
            if "10013" in last_error_msg:
                hint = "WinError 10013 detected: This usually means your Firewall or Antivirus is blocking Python from accessing the network/internet. Please allow python.exe through your firewall."
                logger.error(hint)
                if return_debug:
                    return None, f"Network Error: {hint}"
                return None

            should_retry = _is_retryable_gemini_error(last_error_msg)
            if attempt < attempts and should_retry:
                delay = initial_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"Transient Gemini error detected. Retrying in {delay:.1f}s (attempt {attempt + 1}/{attempts})."
                )
                time.sleep(delay)
                continue
            break

    if return_debug:
        return None, f"Error: {last_error_msg}"
    return None
