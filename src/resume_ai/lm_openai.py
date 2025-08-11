from __future__ import annotations
import json
import os
import ssl
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from . import prompts

# Use certifi CA bundle when available to avoid SSL certificate issues on some systems
try:  # pragma: no cover - availability depends on runtime env
    import certifi  # type: ignore
except Exception:  # pragma: no cover
    certifi = None  # type: ignore


class OpenAIClient:
    """Minimal REST client for OpenAI Chat Completions.

    - Auth via `OPENAI_API_KEY`
    - Uses `model` passed at init (e.g., `gpt-5`, `gpt-4o-mini`)
    - On any error or missing config, returns safe fallbacks
    """

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        try:
            self.request_timeout_s = float(os.getenv("OPENAI_HTTP_TIMEOUT", "15"))
        except ValueError:
            self.request_timeout_s = 15.0
        self.calls_made: int = 0
        self.last_status: str = ""
        self.last_error: str = ""

        # Build SSL context with certifi CA bundle when available
        try:
            if certifi is not None:
                # Hint the Python SSL layer and also create an explicit context we will pass to urlopen
                os.environ.setdefault("SSL_CERT_FILE", certifi.where())
                self.ssl_context = ssl.create_default_context(cafile=certifi.where())
            else:
                self.ssl_context = ssl.create_default_context()
        except Exception:
            # As a last resort, fall back to default context
            self.ssl_context = ssl.create_default_context()

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def _post(self, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_s, context=self.ssl_context) as resp:
                self.calls_made += 1
                resp_data = resp.read().decode("utf-8", errors="ignore")
                self.last_status = "ok"
                self.last_error = ""
                return json.loads(resp_data)
        except Exception as e:
            self.calls_made += 1
            self.last_status = "error"
            reason_or_code = getattr(e, "reason", getattr(e, "code", ""))
            msg = str(e) or reason_or_code
            self.last_error = f"{type(e).__name__}: {msg}"
            return None

    def _call(self, prompt: str) -> str:
        if not self._is_configured():
            return ""
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        payload = self._post(body)
        if payload is None:
            return ""
        try:
            choices = payload.get("choices", [])
            content = choices[0]["message"]["content"]
            return str(content or "")
        except Exception:
            return ""

    def _call_json(self, prompt: str) -> str:
        if not self._is_configured():
            return ""
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            # Ask for valid JSON object; supported by newer GPT models
            "response_format": {"type": "json_object"},
        }
        payload = self._post(body)
        if payload is None:
            return ""
        try:
            choices = payload.get("choices", [])
            content = choices[0]["message"]["content"]
            return str(content or "")
        except Exception:
            return ""

    @staticmethod
    def _render_prompt(template: str, **values: str) -> str:
        rendered = template
        for key, val in values.items():
            rendered = rendered.replace("{" + key + "}", val or "")
        return rendered

    @staticmethod
    def _extract_json_block(text: str) -> str:
        if not text:
            return ""
        s = text.strip()
        # No special block handling needed here; reuse same logic as Google client
        # to be robust if the model ignores response_format
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
                    return s[start : i + 1]
        return ""

    def extract_keywords(self, jd_text: str) -> Dict[str, List[str]]:
        prompt = self._render_prompt(prompts.KEYWORD_EXTRACTION_PROMPT, jd_text=jd_text or "")
        text = self._call_json(prompt) or self._call(prompt)
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
            # If legacy keys exist, use them directly
            legacy_required = data.get("required")
            legacy_preferred = data.get("preferred")
            if isinstance(legacy_required, list) or isinstance(legacy_preferred, list):
                required = list(map(str, legacy_required or []))
                preferred = list(map(str, legacy_preferred or []))
            else:
                # Map category-based output to expected buckets
                core_skills = data.get("core_skills", [])
                technical_skills = data.get("technical_skills", [])
                soft_skills = data.get("soft_skills", [])
                qualifications = data.get("qualifications", [])
                tools_platforms = data.get("tools_platforms", [])
                methodologies = data.get("methodologies", [])

                # Treat hard/role-specific items as required; soft skills as preferred
                required = list(map(str, (
                    (core_skills or [])
                    + (technical_skills or [])
                    + (tools_platforms or [])
                    + (methodologies or [])
                    + (qualifications or [])
                )))
                preferred = list(map(str, (soft_skills or [])))

            # Optional auxiliary fields
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
        items = experience_item.get("bullets", []) if isinstance(experience_item, dict) else []
        return [str(it) for it in items]

    def generate_summary(self, role: str, company: str, keywords: List[str]) -> str:
        prompt = self._render_prompt(prompts.SUMMARY_PROMPT, role=role or "", company=company or "", keywords=", ".join(keywords or []))
        text = self._call(prompt)
        return text.strip() if text else ""


