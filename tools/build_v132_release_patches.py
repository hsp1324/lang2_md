#!/usr/bin/env python3
"""Build and verify the public v1.3.4 Japanese-ROM BPS patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rom_update import bps_apply, bps_create, sha256_bytes
from tools.build_hard_mode_rom import verify_applied_hard_mode


VERSION = "v1.3.4"
SOURCE_PATH = ROOT / "roms/original/Langrisser II (Japan).md"
SOURCE_SIZE = 2_097_152
SOURCE_SHA256 = (
    "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"
)
PATCH_DIR = ROOT / "patches"
MANIFEST_PATH = PATCH_DIR / "v1.3.4.json"

TARGETS = (
    {
        "id": "pure",
        "label_ko": "원작 디자인판",
        "description_ko": (
            "원작 맵 디자인과 밸런스에 한국어화 및 공통 진행 수정 적용"
        ),
        "rom_path": ROOT
        / "roms/builds/Langrisser II (Korean Original v1.3.4).md",
        "output_filename": "Langrisser II (Korean Original v1.3.4).md",
        "patch_filename": "original-v1.3.4.bps",
        "size": 4_194_304,
        "sha256": (
            "96ebbdd3970ae21f78067f83d077062657fd7757b7dc45c6f6257b150e19682d"
        ),
    },
    {
        "id": "normal",
        "label_ko": "최신 디자인 일반판",
        "description_ko": "최신 New 클래스 디자인과 한국어화 적용",
        "rom_path": ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.4).md",
        "output_filename": "Langrisser II (Korean Normal v1.3.4).md",
        "patch_filename": "normal-v1.3.4.bps",
        "size": 4_194_304,
        "sha256": (
            "65d7458a3e4aa993c107ff15cda9152b206cf96c0a7ac3e32dfcf6365f4d99a4"
        ),
    },
    {
        "id": "hard",
        "label_ko": "최신 디자인 하드판",
        "description_ko": "최신 New 클래스 디자인·한국어화·하드 밸런스 적용",
        "rom_path": ROOT
        / "roms/builds/Langrisser II (Korean Hard v1.3.4).md",
        "output_filename": "Langrisser II (Korean Hard v1.3.4).md",
        "patch_filename": "hard-v1.3.4.bps",
        "size": 4_194_304,
        "sha256": (
            "5dc9b5502210b2eb86ea16eff3bd8d047fa4b952f817a3366c4cbd6dd3b49dcf"
        ),
    },
)


def _verified_payload(path: Path, size: int, digest: str, label: str) -> bytes:
    payload = path.read_bytes()
    if len(payload) != size:
        raise ValueError(f"{label} size mismatch: {len(payload)} != {size}")
    actual = sha256_bytes(payload)
    if actual != digest:
        raise ValueError(f"{label} SHA-256 mismatch: {actual} != {digest}")
    return payload


def build(*, check: bool = False) -> dict[str, object]:
    source = _verified_payload(
        SOURCE_PATH, SOURCE_SIZE, SOURCE_SHA256, "Japanese source"
    )
    records: list[dict[str, object]] = []
    generated: dict[Path, bytes] = {}

    for target_spec in TARGETS:
        target = _verified_payload(
            Path(target_spec["rom_path"]),
            int(target_spec["size"]),
            str(target_spec["sha256"]),
            str(target_spec["label_ko"]),
        )
        if target_spec["id"] == "hard":
            verify_applied_hard_mode(target)
        target_hash = str(target_spec["sha256"])
        metadata = json.dumps(
            {
                "game": "Langrisser II",
                "source": "Japan",
                "target": target_spec["id"],
                "version": VERSION,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        patch = bps_create(source, target, metadata)
        if bps_apply(patch, source) != target:
            raise AssertionError(f"{target_spec['id']} BPS round trip failed")
        patch_path = PATCH_DIR / str(target_spec["patch_filename"])
        generated[patch_path] = patch
        records.append(
            {
                "id": target_spec["id"],
                "label_ko": target_spec["label_ko"],
                "description_ko": target_spec["description_ko"],
                "output_filename": target_spec["output_filename"],
                "output_size": len(target),
                "output_sha256": target_hash,
                "patch_filename": target_spec["patch_filename"],
                "patch_size": len(patch),
                "patch_sha256": sha256_bytes(patch),
            }
        )

    manifest: dict[str, object] = {
        "schema_version": 1,
        "game": "Langrisser II",
        "release": VERSION,
        "source": {
            "label": "Langrisser II (Japan)",
            "size": SOURCE_SIZE,
            "sha256": SOURCE_SHA256,
            "headered_size": SOURCE_SIZE + 512,
        },
        "targets": records,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    generated[MANIFEST_PATH] = manifest_bytes

    if check:
        for path, expected in generated.items():
            if not path.is_file():
                raise ValueError(f"release patch asset is missing: {path}")
            if path.read_bytes() != expected:
                raise ValueError(f"release patch asset is stale: {path}")
    else:
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
        for path, payload in generated.items():
            path.write_bytes(payload)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    manifest = build(check=args.check)
    for record in manifest["targets"]:
        print(
            f"{record['id']}: {record['patch_filename']} "
            f"{record['patch_size']} bytes {record['patch_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
