from __future__ import annotations
import json
import os
import ssl
import urllib.request
from typing import Any, Dict, List, Optional

from . import prompts

# Use certifi CA bundle when available to avoid SSL certificate issues on some systems
try:  # pragma: no cover - availability depends on runtime env
    import certifi  # type: ignore
except Exception:  # pragma: no cover
    certifi = None  # type: ignore


class OpenRouterClient:
    """Minimal REST client for OpenRouter (OpenAI-compatible schema).

    - Auth via `OPENROUTER_API_KEY`
    - Optional headers: `OPENROUTER_REFERER`, `OPENROUTER_TITLE`
    - Uses `model` passed at init (e.g., `openrouter/auto`, `anthropic/claude-3.5-sonnet`, `openai/gpt-4o-mini`)
    - On any error or missing config, returns safe fallbacks
    """

    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        # Respect an explicitly provided model; otherwise fall back to env/defaults
        env_primary = os.getenv("OPENROUTER_MODEL", "").strip()
        primary_model = (model or env_primary or "openrouter/auto")
        fallback_model = os.getenv("OPENROUTER_MODEL_FALLBACK", "moonshotai/kimi-k2").strip()
        models_env = os.getenv("OPENROUTER_MODELS", "").strip()

        # Build candidate order:
        # - If a model param is provided, try it first
        # - If OPENROUTER_MODELS is set, extend with that ordered list
        # - Ensure fallback is included at the end
        model_candidates = [primary_model]
        if models_env:
            model_candidates.extend([m.strip() for m in models_env.split(",") if m.strip()])
        if fallback_model and fallback_model not in model_candidates:
            model_candidates.append(fallback_model)

        # Keep existing attribute name for backward compatibility
        self.model = primary_model
        self.model_candidates = model_candidates
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        try:
            self.request_timeout_s = float(os.getenv("OPENROUTER_HTTP_TIMEOUT", "15"))
        except ValueError:
            self.request_timeout_s = 15.0
        self.calls_made: int = 0
        self.last_status: str = ""
        self.last_error: str = ""
        self.last_model_used: str = ""
        self.last_payload_preview: str = ""
        # Token limits (can help avoid very long responses on some models)
        try:
            self.max_tokens_text = int(os.getenv("OPENROUTER_MAX_TOKENS_TEXT", "300"))
        except ValueError:
            self.max_tokens_text = 300
        try:
            self.max_tokens_json = int(os.getenv("OPENROUTER_MAX_TOKENS_JSON", "400"))
        except ValueError:
            self.max_tokens_json = 400

        # Build SSL context with certifi CA bundle when available
        try:
            if certifi is not None:
                os.environ.setdefault("SSL_CERT_FILE", certifi.where())
                self.ssl_context = ssl.create_default_context(cafile=certifi.where())
            else:
                self.ssl_context = ssl.create_default_context()
        except Exception:
            self.ssl_context = ssl.create_default_context()

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def _post(self, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # Optional OpenRouter headers for routing/analytics
        referer = os.getenv("OPENROUTER_REFERER", "")
        title = os.getenv("OPENROUTER_TITLE", "")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title

        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_s, context=self.ssl_context) as resp:
                self.calls_made += 1
                resp_data = resp.read().decode("utf-8", errors="ignore")
                self.last_status = "ok"
                self.last_error = ""
                try:
                    payload = json.loads(resp_data)
                except Exception as je:
                    self.last_status = "error"
                    self.last_error = f"JSONDecodeError: {str(je)[:200]}"
                    return None
                # Keep small preview for diagnostics
                try:
                    self.last_payload_preview = json.dumps(payload, ensure_ascii=False)[:500]
                except Exception:
                    self.last_payload_preview = resp_data[:500]
                return payload
        except Exception as e:
            self.calls_made += 1
            self.last_status = "error"
            reason_or_code = getattr(e, "reason", getattr(e, "code", ""))
            msg = str(e) or reason_or_code
            self.last_error = f"{type(e).__name__}: {msg}"
            return None

    @staticmethod
    def _extract_text_from_payload(payload: Dict[str, Any]) -> str:
        try:
            choices = payload.get("choices", [])
            if not choices:
                return ""
            choice = choices[0] or {}
            message = choice.get("message", {}) or {}
            content = message.get("content")
            # Case 1: direct string content
            if isinstance(content, str):
                return content.strip()
            # Case 2: content as a list of segments
            if isinstance(content, list):
                parts: List[str] = []
                for seg in content:
                    if isinstance(seg, dict):
                        # Common keys used by various providers
                        if "text" in seg and isinstance(seg.get("text"), str):
                            parts.append(seg.get("text", ""))
                        elif "content" in seg and isinstance(seg.get("content"), str):
                            parts.append(seg.get("content", ""))
                joined = "".join(parts).strip()
                if joined:
                    return joined
            # Case 3: tool_calls with empty content; surface the arguments
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                try:
                    first = tool_calls[0] or {}
                    function = first.get("function", {}) or {}
                    args = function.get("arguments")
                    if isinstance(args, str) and args.strip():
                        return args.strip()
                    if isinstance(args, dict):
                        return json.dumps(args, ensure_ascii=False)
                except Exception:
                    pass
            # Case 4: text field at choice-level (some providers)
            if isinstance(choice.get("text"), str):
                return choice.get("text", "").strip()
        except Exception:
            return ""
        return ""

    def _call(self, prompt: str) -> str:
        if not self._is_configured():
            return ""
        last_text: str = ""
        for candidate in self.model_candidates:
            body = {
                "model": candidate,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": self.max_tokens_text,
            }
            payload = self._post(body)
            if payload is None:
                continue
            try:
                self.last_model_used = candidate
                text = self._extract_text_from_payload(payload)
                if text:
                    return text
                last_text = text
            except Exception:
                continue
        return last_text

    def _call_json(self, prompt: str) -> str:
        if not self._is_configured():
            return ""
        last_text: str = ""
        for candidate in self.model_candidates:
            body = {
                "model": candidate,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "max_tokens": self.max_tokens_json,
            }
            payload = self._post(body)
            if payload is None:
                continue
            try:
                self.last_model_used = candidate
                text = self._extract_text_from_payload(payload)
                if text:
                    return text
                last_text = text
            except Exception:
                continue
        return last_text

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
        # Strip triple backticks if present
        if s.startswith("```"):
            s = s.strip('`')
            if s.lower().startswith("json"):
                s = s[4:].lstrip()
        start_candidates = [i for i, ch in enumerate(s) if ch in "[{"]
        if not start_candidates:
            return ""
        start = start_candidates[0]
        stack: List[str] = []
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

    def rewrite_bullets_multi(
        self,
        sections: List[Dict[str, Any]],
        target_keywords: List[str],
        resume_markdown: str | None = None,
    ) -> Dict[int, List[str]]:
        """Rewrite bullets for multiple sections in a single call.

        Returns a mapping of section id -> bullets. On any parsing failure, returns {}.
        """
        try:
            sections_json = json.dumps(sections, ensure_ascii=False)
            kw = ", ".join(target_keywords or [])
        except Exception:
            sections_json = "[]"
            kw = ""

        resume_context_section = ""
        if isinstance(resume_markdown, str) and resume_markdown.strip():
            snippet = resume_markdown.strip()
            if len(snippet) > 5000:
                snippet = snippet[:5000]
            resume_context_section = snippet

        prompt = self._render_prompt(
            prompts.BULLET_REWRITE_MULTI_PROMPT,
            keywords=kw,
            resume_context_section=resume_context_section,
            sections_json=sections_json,
        )
        # Allow larger JSON responses when configured
        original_max = self.max_tokens_json
        try:
            # No-op if env not set; caller may raise this via env to 1200–2000
            self.max_tokens_json = int(os.getenv("OPENROUTER_MAX_TOKENS_JSON", str(self.max_tokens_json)))
        except Exception:
            pass

        text = self._call_json(prompt) or self._call(prompt)
        # Restore previous token cap
        self.max_tokens_json = original_max

        def _parse(text_in: str) -> Dict[int, List[str]]:
            try:
                data = json.loads(text_in)
            except Exception:
                json_block = self._extract_json_block(text_in)
                try:
                    data = json.loads(json_block) if json_block else {}
                except Exception:
                    data = {}
            out: Dict[int, List[str]] = {}
            if isinstance(data, dict):
                arr = data.get("sections")
                if isinstance(arr, list):
                    for it in arr:
                        try:
                            sid = int(it.get("id"))  # type: ignore[arg-type]
                            bl = it.get("bullets", [])
                            if isinstance(bl, list):
                                cleaned = [str(b).strip() for b in bl if str(b).strip()]
                                out[sid] = cleaned
                        except Exception:
                            continue
            return out

        mapping = _parse(text)
        if not mapping:
            self.last_status = self.last_status or "error"
            if not self.last_error:
                self.last_error = "rewrite_bullets_multi: empty or invalid JSON response"
        return mapping
