"""Export the FastAPI OpenAPI schema to a JSON file.

Used by the OpenAPI contract pipeline (CI + local `make openapi`):

    uv run python scripts/export_openapi.py [--out PATH]

Default output: ../frontend/openapi-snapshot.json (relative to backend/), which is
git-ignored — the snapshot is a build artifact, not a source of truth. The single
source of truth is `app.openapi()` in FastAPI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Anchor paths relative to this script so the default --out is stable
# regardless of the caller's working directory.
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DEFAULT_OUT = _REPO_ROOT / "frontend" / "openapi-snapshot.json"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"Output path for the OpenAPI JSON (default: {_DEFAULT_OUT}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # Ensure the backend root is on sys.path so `from app.main import app`
    # works when this script is invoked from the repo root in CI (where the
    # working directory is not necessarily backend/).
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))

    # Importing inside main keeps argparse fast and lets --help work without
    # paying the FastAPI import cost.
    from app.main import app

    schema = app.openapi()

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    paths = len(schema.get("paths", {}))
    schemas = len(schema.get("components", {}).get("schemas", {}))
    print(f"Wrote OpenAPI schema to {out_path} (paths={paths}, schemas={schemas})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
