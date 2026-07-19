"""Run the current Matters ModelMesh and write its immutable snapshot receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard_models.model_mesh import run_mesh


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt",
        default=".flowguard/evidence/model_mesh/MM0_matters_parent_child_mesh.json",
    )
    args = parser.parse_args()
    result = run_mesh()
    path = Path(args.receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"receipt": str(path), **result}, indent=2))
    return 0 if result["status"] == "mesh_green" else 1


if __name__ == "__main__":
    raise SystemExit(main())
