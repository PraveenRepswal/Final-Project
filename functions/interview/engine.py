"""Compatibility wrapper for interview manager.

This module re-exports the canonical InterviewManager from
functions.interview.interviewer to avoid duplicate implementations.
"""

from __future__ import annotations

from functions.interview.interviewer import InterviewManager

__all__ = ["InterviewManager"]
