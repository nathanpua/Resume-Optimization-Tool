# Ensure 'src' is on sys.path so tests can import 'resume_ai'
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
# Also add project root to import top-level modules like 'tools'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
