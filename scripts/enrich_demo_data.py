#!/usr/bin/env python3
"""
Wrapper to execute backend/scripts/enrich_demo_data.py from repository root.
"""
import os
import sys
from pathlib import Path

backend_script = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "enrich_demo_data.py"

if not backend_script.exists():
    print(f"Error: Could not locate {backend_script}")
    sys.exit(1)

# Find python interpreter with backend dependencies
root_dir = Path(__file__).resolve().parent.parent
venv_python = root_dir / "backend" / "venv" / "bin" / "python"
dot_venv_python = root_dir / "backend" / ".venv" / "bin" / "python"

if venv_python.exists():
    py_exec = str(venv_python)
elif dot_venv_python.exists():
    py_exec = str(dot_venv_python)
else:
    py_exec = sys.executable

# Forward execution to backend/scripts/enrich_demo_data.py
import subprocess
sys.exit(subprocess.call([py_exec, str(backend_script)] + sys.argv[1:]))
