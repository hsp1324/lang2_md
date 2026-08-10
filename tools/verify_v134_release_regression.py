#!/usr/bin/env python3
"""Verify the reviewed v1.3.4 ROM, patch, screenshot, and GST evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "localization/v134_release_regression.json"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_SIZE = 0x10000
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_GROUP_COUNT = 40


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file(row: dict[str, object]) -> None:
    path = ROOT / str(row["path"])
    if not path.is_file():
        raise ValueError(f"missing v1.3.4 evidence: {path}")
    actual = sha256(path)
    expected = str(row["sha256"])
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual} != {expected}")


def commander_runtime(path: Path, commander_id: int) -> dict[str, int]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET : GST_WORK_RAM_OFFSET + WORK_RAM_SIZE]
    if len(ram) != WORK_RAM_SIZE:
        raise ValueError(f"GST is missing work RAM: {path}")
    matches = []
    for group in range(RUNTIME_GROUP_COUNT):
        start = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        record = ram[start : start + RUNTIME_GROUP_SIZE]
        if record[1] == commander_id:
            matches.append(
                {
                    "class_id": record[0],
                    "level": record[0x2E],
                    "experience": record[0x2F],
                    "x": record[0x06],
                    "y": record[0x07],
                    "mp": record[0x39],
                    "at": record[0x3A],
                    "df": record[0x3B],
                }
            )
    if len(matches) != 1:
        raise ValueError(
            f"expected one runtime group for commander {commander_id}, "
            f"found {len(matches)} in {path}"
        )
    return matches[0]


def verify_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["release"] != "v1.3.4" or manifest["status"] != "reviewed_pass":
        raise ValueError("v1.3.4 manifest is not a reviewed passing release")
    if manifest["method"]["physical_desktop_used"]:
        raise ValueError("runtime evidence was not captured on an isolated display")

    file_count = 0
    state_count = 0
    for row in (*manifest["release_roms"], *manifest["patches"]):
        verify_file(row)
        file_count += 1
    for case in manifest["join_class_choice"]:
        commander_id = int(case["commander_id"])
        for state in case["states"]:
            verify_file(state)
            actual = commander_runtime(ROOT / state["path"], commander_id)
            if actual != state["runtime"]:
                raise ValueError(
                    f"{case['character']} {state['phase']} runtime mismatch: "
                    f"{actual} != {state['runtime']}"
                )
            file_count += 1
            state_count += 1
        for capture in case["captures"]:
            verify_file(capture)
            file_count += 1
    for surface in manifest["carried_release_surfaces"]:
        for key in ("capture", "gst"):
            verify_file(surface[key])
            file_count += 1
    return {
        "status": "pass",
        "release": manifest["release"],
        "verified_files": file_count,
        "verified_runtime_states": state_count,
        "join_cases": len(manifest["join_class_choice"]),
        "carried_surfaces": len(manifest["carried_release_surfaces"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(json.dumps(verify_manifest(args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
