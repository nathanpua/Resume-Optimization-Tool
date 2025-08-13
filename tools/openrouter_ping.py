from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional


def load_env_if_available() -> None:
    try:
        # Prefer the project helper if available
        from src.resume_ai.env import load_dotenv  # type: ignore

        load_dotenv()
        return
    except Exception:
        pass
    # Fallback to python-dotenv if installed; otherwise ignore silently
    try:
        from dotenv import load_dotenv as dotenv_load  # type: ignore

        dotenv_load()
    except Exception:
        pass


def run_ping(prompt: str, as_json: bool, model: Optional[str]) -> int:
    try:
        from src.resume_ai.lm_openrouter import OpenRouterClient  # type: ignore
    except Exception as e:
        print(f"Failed to import OpenRouterClient: {e}", file=sys.stderr)
        return 2

    client = OpenRouterClient(model=model or "openrouter/auto")

    if not client._is_configured():
        print("OPENROUTER_API_KEY is not set. Please export it or add it to your .env.", file=sys.stderr)
        return 3

    text = client._call_json(prompt) if as_json else client._call(prompt)
    diag = {
        "model_primary": client.model,
        "model_candidates": getattr(client, "model_candidates", [client.model]),
        "calls_made": client.calls_made,
        "last_status": client.last_status,
        "last_error": client.last_error,
    }

    if as_json:
        # Try to pretty-print JSON, otherwise print raw text
        try:
            parsed = json.loads(text or "")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            print(text or "")
    else:
        print(text or "")

    print("\n--- diagnostics ---")
    print(json.dumps(diag, indent=2, ensure_ascii=False))
    return 0 if (text or "").strip() else 4


def main() -> int:
    parser = argparse.ArgumentParser(description="Ping OpenRouter via OpenRouterClient")
    parser.add_argument("--prompt", default="Say 'pong' and nothing else.", help="Prompt text to send")
    parser.add_argument("--json", action="store_true", help="Request JSON response mode")
    parser.add_argument("--model", default=None, help="Primary model id (overrides OPENROUTER_MODEL)")
    parser.add_argument("--fallback", default=None, help="Fallback model id (sets OPENROUTER_MODEL_FALLBACK)")
    parser.add_argument("--models", default=None, help="Comma-separated list of models to try in order (sets OPENROUTER_MODELS)")
    parser.add_argument("--timeout", default=None, help="HTTP timeout seconds (sets OPENROUTER_HTTP_TIMEOUT)")

    args = parser.parse_args()

    load_env_if_available()

    # Allow overriding via CLI by setting env vars for this process
    if args.model:
        os.environ["OPENROUTER_MODEL"] = args.model
    if args.fallback:
        os.environ["OPENROUTER_MODEL_FALLBACK"] = args.fallback
    if args.models:
        os.environ["OPENROUTER_MODELS"] = args.models
    if args.timeout:
        os.environ["OPENROUTER_HTTP_TIMEOUT"] = args.timeout

    return run_ping(prompt=args.prompt, as_json=bool(args.json), model=args.model)


if __name__ == "__main__":
    raise SystemExit(main())


