"""Apply Alembic migrations for the backend database."""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    backend = Path(__file__).resolve().parents[1]
    return subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend)


if __name__ == "__main__":
    raise SystemExit(main())
