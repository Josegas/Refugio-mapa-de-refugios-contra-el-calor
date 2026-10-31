"""Shared pytest setup: lets the tests `import build` and find the data folders."""
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE))  # so `import build` / `import cities` work from any folder

ROOT = PIPELINE.parent
WEB_DATA = ROOT / "web" / "data"   # generated outputs (committed to git)
RAW = ROOT / "data" / "raw"        # raw downloads (NOT in git; only on a machine that ran fetch.py)
