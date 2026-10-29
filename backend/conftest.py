import os
import sys

# Ensure the backend directory (which contains the 'app' package) is in sys.path for test imports.
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
