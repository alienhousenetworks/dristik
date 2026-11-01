import os
import sys

# Ensure the backend directory (which contains the 'app' package) is in sys.path for test imports.
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure backend root is also in sys.path
cwd = os.path.abspath(os.path.dirname(__file__))
if cwd not in sys.path:
    sys.path.insert(0, cwd)

# Pre-import compatibility modules to register sys.modules shims
import app.connectors   # noqa: F401 # Registers app.external_authority.* shims
import app.domain       # noqa: F401 # Registers app.scoring.* and app.evidence.* shims
import app.persistence  # noqa: F401 # Registers app.persistence.* shims
import app.db.session   # noqa: F401 # Registers DatabaseConnectionError on app.core.exceptions

