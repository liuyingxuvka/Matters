"""Write one path-free identity for the Windows desktop build toolchain."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return ""


def build_receipt() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "matters.desktop-build-toolchain.v1",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "pyinstaller_version": _version("pyinstaller"),
        "pywebview_version": _version("pywebview"),
    }
    if not payload["pyinstaller_version"] or not payload["pywebview_version"]:
        raise RuntimeError("desktop build dependencies are unavailable")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    payload["toolchain_fingerprint"] = "sha256:" + sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "toolchain_fingerprint": payload["toolchain_fingerprint"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
