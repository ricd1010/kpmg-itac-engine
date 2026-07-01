"""Compatibility entrypoint for Streamlit Cloud.

Some deployed apps still point at AuditHackathon/src/app.py.  The active TSDA
implementation lives in the repository-level src/app.py, so this wrapper routes
the legacy entrypoint there and makes sure its modules win import resolution.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = REPO_ROOT / "src"
ROOT_APP = ROOT_SRC / "app.py"

sys.path.insert(0, str(ROOT_SRC))
runpy.run_path(str(ROOT_APP), run_name="__main__")
