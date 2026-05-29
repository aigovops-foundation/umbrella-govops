"""Root conftest: ensure the repo root is on sys.path so `conformance` imports cleanly."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
