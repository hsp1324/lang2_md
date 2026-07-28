#!/usr/bin/env python3
"""Archive the current ignored ROM before building the next release."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rom_update import (
    md_header_checksum,
    md_sram_descriptor,
    sha256_bytes,
    validate_md_rom,
)


DEFAULT_REGISTRY = ROOT / "localization/rom_update_releases.json"
DEFAULT_ARCHIVE_DIR = ROOT / "roms/releases"


def _release_filename(release_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", release_id).strip("-")
    if not safe:
        raise ValueError("current release ID has no safe filename characters")
    return f"Langrisser II (Korean {safe}).md"


def _current_record(registry: dict[str, object]) -> dict[str, object]:
    current = registry.get("current_release")
    releases = registry.get("releases")
    if not isinstance(current, str) or not isinstance(releases, list):
        raise ValueError("invalid ROM release registry")
    matches = [
        row
        for row in releases
        if isinstance(row, dict) and row.get("release_id") == current
    ]
    if len(matches) != 1:
        raise ValueError(
            f"registry must contain exactly one current release {current!r}"
        )
    return matches[0]


def _verify_registry_record(
    payload: bytes,
    record: dict[str, object],
) -> None:
    validate_md_rom(payload, "current release")
    actual = {
        "size": len(payload),
        "sha256": sha256_bytes(payload),
        "md_checksum": f"{md_header_checksum(payload):04X}",
        "sram_descriptor": md_sram_descriptor(payload).hex().upper(),
    }
    for key, value in actual.items():
        if record.get(key) != value:
            raise ValueError(
                f"current ROM {key} does not match registry: "
                f"{value} != {record.get(key)}"
            )


def archive_current_release(
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    root: Path = ROOT,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
) -> Path:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("invalid ROM release registry")
    record = _current_record(registry)
    release_id = str(record["release_id"])
    source = root / str(record["rom_path"])
    if not source.is_file():
        raise FileNotFoundError(f"current release ROM not found: {source}")
    payload = source.read_bytes()
    _verify_registry_record(payload, record)

    archive_dir.mkdir(parents=True, exist_ok=True)
    output = archive_dir / _release_filename(release_id)
    if output.exists():
        if sha256_bytes(output.read_bytes()) != record["sha256"]:
            raise ValueError(
                f"archive path contains different data: {output}"
            )
        return output

    descriptor, name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=archive_dir,
    )
    temp_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copymode(source, temp_path)
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)
    _verify_registry_record(output.read_bytes(), record)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "새 한국어판을 빌드하기 전에 현재 배포 ROM을 해시 검증하여 "
            "로컬 보관합니다."
        )
    )
    parser.add_argument(
        "--registry", type=Path, default=DEFAULT_REGISTRY
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        output = archive_current_release(
            registry_path=args.registry,
            root=args.root,
            archive_dir=args.archive_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    print(f"보관 완료: {output}")
    print(f"SHA-256: {sha256_bytes(output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
