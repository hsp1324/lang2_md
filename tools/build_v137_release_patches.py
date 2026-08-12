#!/usr/bin/env python3
"""Rebuild and verify the candidate v1.3.7 Japanese-ROM BPS patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_hard_mode_rom import verify_applied_hard_mode  # noqa: E402
from tools.rom_version import get_profile  # noqa: E402
from tools.rom_update import bps_apply, bps_create, sha256_bytes  # noqa: E402
from tools.v137_release_identity import (  # noqa: E402
    RELEASE_ROM_PATHS,
    RELEASE_ROM_SHA256,
)


VERSION = "v1.3.7"
SOURCE_PATH = ROOT / "roms/original/Langrisser II (Japan).md"
SOURCE_SIZE = 2_097_152
SOURCE_SHA256 = (
    "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"
)
PATCH_DIR = ROOT / "patches"
MANIFEST_PATH = PATCH_DIR / "v1.3.7.json"

TARGETS = (
    {
        "id": "pure",
        "label_ko": "원작 디자인판",
        "description_ko": (
            "원작 맵 디자인과 밸런스에 한국어화 및 공통 진행 수정 적용"
        ),
        "rom_path": RELEASE_ROM_PATHS["pure"],
        "output_filename": RELEASE_ROM_PATHS["pure"].name,
        "patch_filename": "original-v1.3.7.bps",
        "size": 4_194_304,
        "sha256": RELEASE_ROM_SHA256["pure"],
    },
    {
        "id": "normal",
        "label_ko": "최신 디자인 일반판",
        "description_ko": "최신 New 클래스 디자인과 한국어화 적용",
        "rom_path": RELEASE_ROM_PATHS["normal"],
        "output_filename": RELEASE_ROM_PATHS["normal"].name,
        "patch_filename": "normal-v1.3.7.bps",
        "size": 4_194_304,
        "sha256": RELEASE_ROM_SHA256["normal"],
    },
    {
        "id": "hard",
        "label_ko": "최신 디자인 하드판",
        "description_ko": (
            "최신 New 클래스 디자인·한국어화 1.3.7·하드 밸런스 1.3.7 적용"
        ),
        "rom_path": RELEASE_ROM_PATHS["hard"],
        "output_filename": RELEASE_ROM_PATHS["hard"].name,
        "patch_filename": "hard-v1.3.7.bps",
        "size": 4_194_304,
        "sha256": RELEASE_ROM_SHA256["hard"],
    },
)


def _verify_version_registry() -> None:
    expected = {
        "pure": {
            "release_id": "ko-original-1.3.7",
            "translation_version": "1.3.7",
            "balance_version": None,
            "base_release": "ko-original-1.3.6",
        },
        "normal": {
            "release_id": "ko-normal-1.3.7",
            "translation_version": "1.3.7",
            "balance_version": None,
            "base_release": "ko-normal-1.3.6",
        },
        "hard": {
            "release_id": "ko-hard-1.3.7",
            "translation_version": "1.3.7",
            "balance_version": "1.3.7",
            "base_release": "ko-hard-1.3.6",
        },
    }
    target_by_id = {str(row["id"]): row for row in TARGETS}
    for profile_name, expected_fields in expected.items():
        profile = get_profile(profile_name)
        for field, expected_value in expected_fields.items():
            if profile[field] != expected_value:
                raise ValueError(
                    f"{profile_name} version registry {field} mismatch: "
                    f"{profile[field]!r} != {expected_value!r}"
                )
        if (
            profile["rom_filename"]
            != target_by_id[profile_name]["output_filename"]
        ):
            raise ValueError(
                f"{profile_name} registry filename does not match v1.3.7 target"
            )


def rebuild_roms() -> None:
    """Rebuild all three exact targets from the Japanese source and registry."""

    _verify_version_registry()
    target_by_id = {str(row["id"]): row for row in TARGETS}
    for profile_name in ("pure", "normal"):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_korean_jp_probe.py"),
                "--rom-profile",
                profile_name,
                "--out",
                str(target_by_id[profile_name]["rom_path"]),
            ],
            cwd=ROOT,
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_hard_mode_rom.py"),
            "--out",
            str(target_by_id["hard"]["rom_path"]),
        ],
        cwd=ROOT,
        check=True,
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
    _verify_version_registry()
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
                "output_sha256": target_spec["sha256"],
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
    generated[MANIFEST_PATH] = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

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
    parser.add_argument(
        "--rebuild-roms",
        action="store_true",
        help="rebuild all three exact ROM targets before creating BPS assets",
    )
    args = parser.parse_args(argv)
    if args.rebuild_roms:
        rebuild_roms()
    manifest = build(check=args.check)
    for record in manifest["targets"]:
        print(
            f"{record['id']}: {record['patch_filename']} "
            f"{record['patch_size']} bytes {record['patch_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
