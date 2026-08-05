import os
import sys
from pathlib import Path
import runpy

# Ensure project root, ml, and dashboard directories are in Python path
_PROJECT_ROOT = Path(__file__).resolve().parent
_ML_DIR = _PROJECT_ROOT / "ml"
_DASHBOARD_DIR = _PROJECT_ROOT / "dashboard"

for p in [_PROJECT_ROOT, _ML_DIR, _DASHBOARD_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Delegate execution to full Streamlit application in dashboard/app.py
_APP_PATH = _DASHBOARD_DIR / "app.py"
runpy.run_path(str(_APP_PATH), run_name="__main__")