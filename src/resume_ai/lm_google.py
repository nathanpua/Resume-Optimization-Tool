from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

from . import prompts


class GoogleLMClient:
    """Thin wrapper for Google LLM (Gemini) calls.

    This is a scaffold. It expects GOOGLE_API_KEY in the environment. If not
    present, methods return stubbed outputs to keep the pipeline runnable.
    """

    def __init__(self, model: str = "gemini-1.5-pro-002") -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.model = model

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def extract_keywords(self, jd_text: str) -> Dict[str, List[str]]:
        if not self._is_configured():
            return {"required": [], "preferred": [], "verbs": [], "domains": []}
        # TODO: Implement actual Google Generative Language API call.
        # Return parsed JSON according to the prompt contract.
        raise NotImplementedError("Google LLM integration pending API key setup.")

    def rewrite_bullets(self, experience_item: Dict[str, Any], target_keywords: List[str]) -> List[str]:
        if not self._is_configured():
            return [
                "Delivered feature X improving Y by 20% using A/B testing and automation.",
                "Optimized pipeline reducing costs by 15% with caching and batching.",
                "Led integration with AWS services (Lambda, S3) to scale to 1M+ events/day.",
            ]
        raise NotImplementedError("Google LLM integration pending API key setup.")

    def generate_summary(self, role: str, company: str, keywords: List[str]) -> str:
        if not self._is_configured():
            return (
                f"{role} candidate aligning with {company} needs; experienced in "
                f"{', '.join(keywords[:4])} with measurable impact."
            )
        raise NotImplementedError("Google LLM integration pending API key setup.")
