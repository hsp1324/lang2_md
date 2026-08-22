#!/usr/bin/env python3
"""Rebuild and verify the v1.4.1 Japanese-ROM BPS patches."""

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
from tools.rom_update import bps_apply, bps_create, sha256_bytes  # noqa: E402
from tools.rom_version import get_profile  # noqa: E402
from tools.v138_release_identity import JAPANESE_SOURCE_ROM_SHA256  # noqa: E402


VERSION = "v1.4.1"
SOURCE_PATH = ROOT / "roms/original/Langrisser II (Japan).md"
SOURCE_SIZE = 2_097_152
PATCH_DIR = ROOT / "patches"
MANIFEST_PATH = PATCH_DIR / f"{VERSION}.json"

TARGET_LABELS = {
    "pure": "원작 한국어판",
    "normal": "최신 디자인 일반판",
    "hard": "최신 디자인 하드판",
}
TARGET_DESCRIPTIONS = {
    "pure": "원작 디자인·밸런스·합류 클래스에 한국어화만 적용",
    "normal": (
        "최신 New 클래스 디자인과 한국어화, 키스·레스터·제시카의 "
        "1단 LV10 선택 합류 적용(지급 경험치는 원작과 동일)"
    ),
    "hard": (
        "최신 New 클래스 디자인·한국어화·하드 밸런스 및 "
        "전 상점 룬스톤·메사이어소드 적용"
    ),
}


def target_specs() -> tuple[dict[str, object], ...]:
    records = []
    for profile_name in ("pure", "normal", "hard"):
        profile = get_profile(profile_name)
        records.append(
            {
                "id": profile_name,
                "label_ko": TARGET_LABELS[profile_name],
                "description_ko": TARGET_DESCRIPTIONS[profile_name],
                "rom_path": ROOT / "roms/builds" / profile["rom_filename"],
                "output_filename": profile["rom_filename"],
                "patch_filename": (
                    f"{profile_name if profile_name != 'pure' else 'original'}"
                    f"-{VERSION}.bps"
                ),
            }
        )
    return tuple(records)


TARGETS = target_specs()


def _verify_version_registry() -> None:
    expected = {
        "pure": ("ko-original-1.4.1", "1.4.1", None, "ko-original-1.4.0"),
        "normal": ("ko-normal-1.4.1", "1.4.1", None, "ko-normal-1.4.0"),
        "hard": ("ko-hard-1.4.1", "1.4.1", "1.4.1", "ko-hard-1.4.0"),
    }
    for profile_name, expected_values in expected.items():
        profile = get_profile(profile_name)
        actual = (
            profile["release_id"],
            profile["translation_version"],
            profile["balance_version"],
            profile["base_release"],
        )
        if actual != expected_values:
            raise ValueError(
                f"{profile_name} version registry mismatch: "
                f"{actual!r} != {expected_values!r}"
            )


def _verified_payload(path: Path, size: int, label: str) -> bytes:
    payload = path.read_bytes()
    if len(payload) != size:
        raise ValueError(f"{label} size mismatch: {len(payload)} != {size}")
    return payload


def rebuild_roms() -> None:
    _verify_version_registry()
    specs = {str(spec["id"]): spec for spec in target_specs()}
    for profile_name in ("pure", "normal"):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_korean_jp_probe.py"),
                "--rom-profile",
                profile_name,
                "--out",
                str(specs[profile_name]["rom_path"]),
            ],
            cwd=ROOT,
            check=True,
        )
    # Keep the canonical development normal ROM in sync with the versioned
    # Normal target; hard-mode verification and shared UI tests read it.
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_korean_jp_probe.py"),
            "--rom-profile",
            "normal",
            "--out",
            str(ROOT / "roms/builds/Langrisser II (Korean).md"),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_hard_mode_rom.py"),
            "--out",
            str(specs["hard"]["rom_path"]),
        ],
        cwd=ROOT,
        check=True,
    )


def build(*, check: bool = False) -> dict[str, object]:
    _verify_version_registry()
    source = _verified_payload(SOURCE_PATH, SOURCE_SIZE, "Japanese source")
    if sha256_bytes(source) != JAPANESE_SOURCE_ROM_SHA256:
        raise ValueError("Japanese source SHA-256 mismatch")
    records: list[dict[str, object]] = []
    generated: dict[Path, bytes] = {}
    for target_spec in target_specs():
        target_id = str(target_spec["id"])
        target = _verified_payload(
            Path(target_spec["rom_path"]), 4_194_304, str(target_spec["label_ko"])
        )
        if target_id == "hard":
            verify_applied_hard_mode(target)
        metadata = json.dumps(
            {
                "game": "Langrisser II",
                "source": "Japan",
                "target": target_id,
                "version": VERSION,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        patch = bps_create(source, target, metadata)
        if bps_apply(patch, source) != target:
            raise AssertionError(f"{target_id} BPS round trip failed")
        patch_path = PATCH_DIR / str(target_spec["patch_filename"])
        generated[patch_path] = patch
        records.append(
            {
                "id": target_id,
                "label_ko": target_spec["label_ko"],
                "description_ko": target_spec["description_ko"],
                "output_filename": target_spec["output_filename"],
                "output_size": len(target),
                "output_sha256": sha256_bytes(target),
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
            "sha256": JAPANESE_SOURCE_ROM_SHA256,
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
    parser.add_argument("--rebuild-roms", action="store_true")
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
