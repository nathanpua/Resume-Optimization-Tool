from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List

from . import prompts


class GoogleLMClient:
    """REST client for Google Generative Language API (Gemini).

    Uses API key auth via `GOOGLE_API_KEY`. Targets `gemini-2.0-flash`.
    On any error, returns safe fallbacks to keep pipeline running.
    """

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def _call(self, prompt: str) -> str:
        if not self._is_configured():
            return ""
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read().decode("utf-8", errors="ignore")
                payload = json.loads(resp_data)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return ""

        # Extract text from first candidate
        try:
            candidates = payload.get("candidates", [])
            parts = candidates[0]["content"]["parts"]
            texts = [p.get("text", "") for p in parts]
            return "\n".join([t for t in texts if t])
        except Exception:
            return ""

    def extract_keywords(self, jd_text: str) -> Dict[str, List[str]]:
        prompt = prompts.KEYWORD_EXTRACTION_PROMPT.format(jd_text=jd_text or "")
        text = self._call(prompt)
        try:
            data = json.loads(text)
            return {
                "required": list(map(str, data.get("required", []))),
                "preferred": list(map(str, data.get("preferred", []))),
                "verbs": list(map(str, data.get("verbs", []))),
                "domains": list(map(str, data.get("domains", []))),
            }
        except Exception:
            return {"required": [], "preferred": [], "verbs": [], "domains": []}

    def rewrite_bullets(self, experience_item: Dict[str, Any], target_keywords: List[str]) -> List[str]:
        try:
            exp_json = json.dumps(experience_item)
            kw = ", ".join(target_keywords or [])
        except Exception:
            exp_json = "{}"
            kw = ""
        prompt = prompts.BULLET_REWRITE_PROMPT.format(experience_json=exp_json, keywords=kw)
        text = self._call(prompt)
        try:
            data = json.loads(text)
            bullets = data.get("bullets", [])
            return [str(b).strip() for b in bullets if str(b).strip()]
        except Exception:
            # Safe fallback
            items = experience_item.get("bullets", []) if isinstance(experience_item, dict) else []
            return [str(it) for it in items]

    def generate_summary(self, role: str, company: str, keywords: List[str]) -> str:
        prompt = prompts.SUMMARY_PROMPT.format(role=role or "", company=company or "", keywords=", ".join(keywords or []))
        text = self._call(prompt)
        return text.strip() if text else ""
