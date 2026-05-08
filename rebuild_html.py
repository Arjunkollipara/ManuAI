#!/usr/bin/env python3
"""Keep the generated dashboard away from the live frontend.

The FastAPI app now serves the static files in ``frontend/`` directly.
This script is retained for compatibility, but it writes a separate
legacy artifact so it cannot overwrite the active UI again.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
LEGACY_SOURCE = ROOT / "api" / "static" / "index.html.backup"
LEGACY_OUTPUT = ROOT / "api" / "static" / "legacy-generated-dashboard.html"


def main() -> int:
    if not LEGACY_SOURCE.exists():
        raise SystemExit(f"Missing legacy source file: {LEGACY_SOURCE}")

    LEGACY_OUTPUT.write_text(LEGACY_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote legacy dashboard copy to {LEGACY_OUTPUT}")
    print("Live UI is served from /frontend and is no longer overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
