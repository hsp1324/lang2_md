#!/usr/bin/env python3
"""Recheck the Cross/Necklace shop rows on an isolated candidate ROM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


CAPTURE_TOOL = ROOT / "tools/capture_item_shop_inventory.py"
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/shop_necklace_probe"
ITEM_IDS = (27, 28)
ITEM_LABELS = {27: "크로스", 28: "넥클리스"}
ACCEPTED = {
    27: ROOT / "captures/run/shop_overflow_necklace/corrected_id27.png",
    28: ROOT / "captures/run/shop_overflow_necklace/corrected_id28.png",
}
ACCEPTED_SHA256 = {
    27: "a2d886f9b9519513966b7ef7f4c0a93391cae54c48a4796fe02b11bd1119bb87",
    28: "ddfe81f821aabb7200b2045b1ce3e978e67fad1b702403a0e9875d73168dbfea",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_path(prefix: Path, item_id: int) -> Path:
    return Path(f"{prefix}_id{item_id:02d}.png")


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    prefix = output / "item"
    probe_rom = output / "shop-probe.md"
    runtime_name = f"shop-necklace-{args.run_id}"
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        command = [
            sys.executable,
            str(CAPTURE_TOOL),
            "--input-rom", str(args.rom),
            "--source-rom", str(SOURCE_ROM),
            "--output-rom", str(probe_rom),
            "--runtime-name", runtime_name,
            "--capture-prefix", str(prefix),
            "--start-item", str(ITEM_IDS[0]),
            "--end-item", str(ITEM_IDS[-1]),
            "--initial-delay", "20.0",
            "--movement-delay", "0.45",
            "--virtual-display", args.display,
            "--overwrite",
        ]
        environment = os.environ.copy()
        environment["BLASTEM_VIRTUAL_DISPLAY"] = args.display
        capture_attempts = []
        completed = None
        for capture_attempt in range(1, 3):
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            capture_attempts.append({
                "attempt": capture_attempt,
                "returncode": completed.returncode,
                "log": completed.stdout,
            })
            if completed.returncode == 0:
                break
            matrix.terminate_blastem_processes(display=args.display)
        if completed is None:
            raise AssertionError("shop capture retry loop did not run")
        rows = []
        for item_id in ITEM_IDS:
            actual = capture_path(prefix, item_id)
            accepted = ACCEPTED[item_id]
            actual_sha256 = sha256(actual) if actual.is_file() else None
            accepted_file_sha256 = (
                sha256(accepted) if accepted.is_file() else None
            )
            if (
                accepted_file_sha256 is not None
                and accepted_file_sha256 != ACCEPTED_SHA256[item_id]
            ):
                raise ValueError(f"accepted shop capture changed: {accepted}")
            rows.append({
                "item_id": item_id,
                "label": ITEM_LABELS[item_id],
                "capture": str(actual.relative_to(ROOT)),
                "capture_sha256": actual_sha256,
                "accepted_capture": str(accepted.relative_to(ROOT)),
                "accepted_capture_present": accepted.is_file(),
                "accepted_sha256": ACCEPTED_SHA256[item_id],
                "pixel_exact": actual_sha256 == ACCEPTED_SHA256[item_id],
            })
        passed = completed.returncode == 0 and all(
            row["pixel_exact"] for row in rows
        )
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "rom": {
                "path": str(args.rom.relative_to(ROOT)),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
                "release_rom_modified": False,
            },
            "items": rows,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "capture_returncode": completed.returncode,
            "capture_log": completed.stdout,
            "capture_attempts": capture_attempts,
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--display", default=":260")
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    args.output_root = args.output_root.resolve()
    if not args.rom.is_file():
        raise FileNotFoundError(f"ROM does not exist: {args.rom}")
    result = run_probe(args)
    print(
        f"{result['status']}: "
        + ", ".join(row["label"] for row in result["items"])
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
