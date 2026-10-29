"""Check that the seven pillars and the specialist pool still load."""
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agents.runtime.registry import SPECIALIST_AGENTS_V3, specialist_count
from app.domain.pillar import PillarId
from app.pillars.registry import PILLAR_REGISTRY, list_pillars


def main() -> int:
    missing = [pillar.value for pillar in PillarId if pillar not in PILLAR_REGISTRY]
    if missing or len(list_pillars()) != 7:
        print("pillar registry is incomplete:", missing)
        return 1
    if specialist_count() != len(SPECIALIST_AGENTS_V3) or specialist_count() < 1:
        print("specialist registry is empty")
        return 1
    print(f"pillars={len(list_pillars())} specialists={specialist_count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
