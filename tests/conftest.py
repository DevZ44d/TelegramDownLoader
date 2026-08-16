from __future__ import annotations

import os
import sys
from pathlib import Path

# config.py (imported by nearly every module under test) reads these at
# import time and raises if they're missing, so they must exist before
# ANY project module is imported anywhere in the test session.
os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("BOT_TOKEN", "123:test-token")
os.environ.setdefault("DOWNLOAD_DIR", "tests/.tmp_downloads")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
