import os
from pathlib import Path
from typing import Dict


def load_dotenv(path: str | None = None) -> Dict[str, str]:
    """Minimal .env loader: KEY=VALUE per line, '#' comments allowed."""
    env_path = Path(path) if path else Path.cwd() / ".env"
    if not env_path.exists():
        return {}
    loaded: Dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            if key not in os.environ:
                os.environ[key] = val
            loaded[key] = val
    return loaded
