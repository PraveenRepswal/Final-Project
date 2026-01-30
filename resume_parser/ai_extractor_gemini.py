"""AI-powered structured data extraction from resume text using Google GenAI SDK (google-genai)."""

import logging
import os
import json
from typing import Optional, Tuple, Union

from google import genai
from google.genai import types

from .ai_extractor import get_extraction_prompt, parse_resume_data_from_response
from .models import ResumeData

logger = logging.getLogger(__name__)

def extract_resume_data_gemini(
    text: str,
    model: str = "gemini-2.5-flash",
    api_key: str = None,
    return_debug: bool = False
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

    try:
        client = genai.Client(api_key=api_key)
        
        # Construct prompt
        base_prompt = get_extraction_prompt(text)
        
        prompt = f"""
        {base_prompt}
        
        IMPORTANT: Output RAW JSON only. Do not wrap in markdown code blocks.
        """
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        
        result_text = response.text
        resume_data = None

        # Parse JSON directly since we requested JSON mode
        try:
            data_dict = json.loads(result_text)
            resume_data = ResumeData(**data_dict)
        except json.JSONDecodeError:
            logger.warning("Gemini JSON mode failed to produce valid JSON, trying fallback parser.")
            resume_data = parse_resume_data_from_response(result_text)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            resume_data = parse_resume_data_from_response(result_text)

        if return_debug:
            return resume_data, result_text
        return resume_data

    except Exception as e:
        logger.error(f"Gemini Extraction Error: {e}")
        if return_debug:
            return None, f"Error: {str(e)}"
        return None
