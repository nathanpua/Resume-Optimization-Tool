from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

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
        # HTTP timeout (seconds), adjustable via env
        try:
            self.request_timeout_s = float(os.getenv("GOOGLE_HTTP_TIMEOUT", "15"))
        except ValueError:
            self.request_timeout_s = 15.0
        self.calls_made: int = 0
        self.last_status: str = ""
        self.last_error: str = ""

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def _post(self, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """POST body and return parsed JSON payload or None on error (with timeout)."""
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_s) as resp:
                self.calls_made += 1
                resp_data = resp.read().decode("utf-8", errors="ignore")
                self.last_status = "ok"
                self.last_error = ""
                return json.loads(resp_data)
        except Exception as e:
            self.calls_made += 1
            self.last_status = "error"
            self.last_error = f"{type(e).__name__}: {getattr(e, 'reason', getattr(e, 'code', ''))}"
            return None

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
        payload = self._post(body)
        if payload is None:
            return ""

        # Extract text from first candidate
        try:
            candidates = payload.get("candidates", [])
            parts = candidates[0]["content"]["parts"]
            texts = [p.get("text", "") for p in parts]
            return "\n".join([t for t in texts if t])
        except Exception:
            return ""

    def _call_json(self, prompt: str) -> str:
        """Call the API asking explicitly for JSON, return raw text (expected JSON string).

        Some models wrap JSON in prose or code fences; callers should still be robust in parsing.
        """
        if not self._is_configured():
            return ""
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            },
        }
        payload = self._post(body)
        if payload is None:
            return ""

        try:
            candidates = payload.get("candidates", [])
            parts = candidates[0]["content"]["parts"]
            texts = [p.get("text", "") for p in parts]
            return "\n".join([t for t in texts if t])
        except Exception:
            return ""

    @staticmethod
    def _render_prompt(template: str, **values: str) -> str:
        """Safely substitute known placeholders without touching other braces.

        This avoids str.format() conflicts with JSON braces in the templates.
        """
        rendered = template
        for key, val in values.items():
            rendered = rendered.replace("{" + key + "}", val or "")
        return rendered

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Best-effort: extract a JSON object/array from arbitrary text.

        - Strips common Markdown code fences
        - Finds the first top-level JSON object/array by brace/bracket matching
        """
        if not text:
            return ""
        s = text.strip()
        # Strip triple backticks if present
        if s.startswith("```"):
            s = s.strip('`')
            # Remove possible language hint like json\n
            if s.lower().startswith("json"):
                s = s[4:].lstrip()
        # Find first '{' or '[' and attempt to balance braces/brackets
        start_candidates = [i for i, ch in enumerate(s) if ch in "[{"]
        if not start_candidates:
            return ""
        start = start_candidates[0]
        stack = []
        for i in range(start, len(s)):
            ch = s[i]
            if ch in "[{":
                stack.append(ch)
            elif ch in "]}":
                if not stack:
                    return ""
                open_ch = stack.pop()
                if (open_ch, ch) not in (("[", "]"), ("{", "}")):
                    return ""
                if not stack:
                    # Found a balanced block
                    return s[start : i + 1]
        return ""

    def extract_keywords(self, jd_text: str) -> Dict[str, List[str]]:
        prompt = self._render_prompt(prompts.KEYWORD_EXTRACTION_PROMPT, jd_text=jd_text or "")
        text = self._call_json(prompt) or self._call(prompt)
        # Try parse directly; if fails, try extracting a JSON block
        try:
            data = json.loads(text)
        except Exception:
            json_block = self._extract_json_block(text)
            try:
                data = json.loads(json_block) if json_block else {}
            except Exception:
                data = {}
        # Support both legacy {required, preferred} schema and new category schema
        required: List[str] = []
        preferred: List[str] = []
        verbs: List[str] = []
        domains: List[str] = []

        if isinstance(data, dict):
            legacy_required = data.get("required")
            legacy_preferred = data.get("preferred")
            if isinstance(legacy_required, list) or isinstance(legacy_preferred, list):
                required = list(map(str, legacy_required or []))
                preferred = list(map(str, legacy_preferred or []))
            else:
                core_skills = data.get("core_skills", [])
                technical_skills = data.get("technical_skills", [])
                soft_skills = data.get("soft_skills", [])
                qualifications = data.get("qualifications", [])
                tools_platforms = data.get("tools_platforms", [])
                methodologies = data.get("methodologies", [])

                required = list(map(str, (
                    (core_skills or [])
                    + (technical_skills or [])
                    + (tools_platforms or [])
                    + (methodologies or [])
                    + (qualifications or [])
                )))
                preferred = list(map(str, (soft_skills or [])))

            verbs = list(map(str, data.get("verbs", [])))
            domains = list(map(str, data.get("domains", [])))

        # Deduplicate while preserving order
        def _dedup(items: List[str]) -> List[str]:
            seen = set()
            out: List[str] = []
            for it in items:
                if it not in seen and it.strip():
                    seen.add(it)
                    out.append(it)
            return out

        return {
            "required": _dedup(required),
            "preferred": _dedup(preferred),
            "verbs": _dedup(verbs),
            "domains": _dedup(domains),
        }

    def rewrite_bullets(self, experience_item: Dict[str, Any], target_keywords: List[str], resume_markdown: str | None = None) -> List[str]:
        try:
            exp_json = json.dumps(experience_item)
            kw = ", ".join(target_keywords or [])
        except Exception:
            exp_json = "{}"
            kw = ""
        resume_context_section = ""
        if isinstance(resume_markdown, str) and resume_markdown.strip():
            # Bound the size to avoid excessive prompt length
            snippet = resume_markdown.strip()
            if len(snippet) > 5000:
                snippet = snippet[:5000]
            resume_context_section = f"\n## Candidate Resume (Markdown excerpt)\n\n{snippet}\n"
        prompt = self._render_prompt(
            prompts.BULLET_REWRITE_PROMPT,
            experience_json=exp_json,
            keywords=kw,
            resume_context_section=resume_context_section,
        )
        text = self._call_json(prompt) or self._call(prompt)
        try:
            data = json.loads(text)
        except Exception:
            json_block = self._extract_json_block(text)
            try:
                data = json.loads(json_block) if json_block else {}
            except Exception:
                data = {}
        bullets = []
        if isinstance(data, dict):
            bullets = data.get("bullets", [])
        if bullets:
            return [str(b).strip() for b in bullets if str(b).strip()]
        # Safe fallback to original items
        items = experience_item.get("bullets", []) if isinstance(experience_item, dict) else []
        return [str(it) for it in items]

    def generate_summary(self, role: str, company: str, keywords: List[str]) -> str:
        prompt = self._render_prompt(prompts.SUMMARY_PROMPT, role=role or "", company=company or "", keywords=", ".join(keywords or []))
        text = self._call(prompt)
        return text.strip() if text else ""
