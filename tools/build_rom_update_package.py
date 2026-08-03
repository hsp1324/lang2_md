#!/usr/bin/env python3
"""Build a save-compatible Langrisser II Korean BPS update package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rom_update import (
    DEFAULT_SAVE_FORMAT,
    MANIFEST_NAME,
    PACKAGE_SCHEMA_VERSION,
    PACKAGE_TYPE,
    bps_apply,
    bps_create,
    md_header_checksum,
    md_sram_descriptor,
    sha256_bytes,
    validate_md_rom,
)


DEFAULT_TARGET = ROOT / "roms/builds/Langrisser II (Korean).md"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class SourceRom:
    release_id: str
    path: Path


def release_record(
    release_id: str,
    payload: bytes,
    save_format: str,
) -> dict[str, object]:
    validate_md_rom(payload, release_id)
    return {
        "release_id": release_id,
        "sha256": sha256_bytes(payload),
        "size": len(payload),
        "md_checksum": f"{md_header_checksum(payload):04X}",
        "sram_descriptor": md_sram_descriptor(payload).hex().upper(),
        "save_format": save_format,
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    if not slug:
        raise ValueError(f"release ID has no safe filename characters: {value}")
    return slug


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.create_system = 3
    return info


def windows_launcher() -> bytes:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set \"ROM=%~1\"\r\n"
        "if not defined ROM set /p \"ROM=업데이트할 한국어판 ROM 경로: \"\r\n"
        "where py >nul 2>nul\r\n"
        "if %ERRORLEVEL% EQU 0 (\r\n"
        "  py -3 apply_update.py apply --package . --rom \"%ROM%\"\r\n"
        ") else (\r\n"
        "  python apply_update.py apply --package . --rom \"%ROM%\"\r\n"
        ")\r\n"
        "set \"RESULT=%ERRORLEVEL%\"\r\n"
        "pause\r\n"
        "exit /b %RESULT%\r\n"
    ).encode("utf-8")


def unix_launcher() -> bytes:
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        "cd \"$(dirname \"$0\")\"\n"
        "rom=${1-}\n"
        "if [ -z \"$rom\" ]; then\n"
        "  printf '업데이트할 한국어판 ROM 경로: '\n"
        "  IFS= read -r rom\n"
        "fi\n"
        "python3 apply_update.py apply --package . --rom \"$rom\"\n"
    ).encode("utf-8")


def windows_save_launcher() -> bytes:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set \"SAVE=%~1\"\r\n"
        "set \"ROM=%~2\"\r\n"
        "if not defined SAVE set /p \"SAVE=기존 SRM 파일 경로: \"\r\n"
        "if not defined ROM set /p \"ROM=새 한국어판 ROM 경로: \"\r\n"
        "where py >nul 2>nul\r\n"
        "if %ERRORLEVEL% EQU 0 (\r\n"
        "  py -3 apply_update.py migrate-save --save \"%SAVE%\" --target-rom \"%ROM%\"\r\n"
        ") else (\r\n"
        "  python apply_update.py migrate-save --save \"%SAVE%\" --target-rom \"%ROM%\"\r\n"
        ")\r\n"
        "set \"RESULT=%ERRORLEVEL%\"\r\n"
        "pause\r\n"
        "exit /b %RESULT%\r\n"
    ).encode("utf-8")


def unix_save_launcher() -> bytes:
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        "cd \"$(dirname \"$0\")\"\n"
        "save=${1-}\n"
        "rom=${2-}\n"
        "if [ -z \"$save\" ]; then\n"
        "  printf '기존 SRM 파일 경로: '\n"
        "  IFS= read -r save\n"
        "fi\n"
        "if [ -z \"$rom\" ]; then\n"
        "  printf '새 한국어판 ROM 경로: '\n"
        "  IFS= read -r rom\n"
        "fi\n"
        "python3 apply_update.py migrate-save --save \"$save\" --target-rom \"$rom\"\n"
    ).encode("utf-8")


def player_readme(target_release: str) -> bytes:
    return f"""랑그릿사 II 한국어판 ROM 업데이트 ({target_release})

중요
1. 에뮬레이터를 완전히 종료합니다.
2. 게임 안에서 저장한 뒤 업데이트합니다.
3. 상태 저장(save state)은 ROM 코드 주소를 포함할 수 있어 호환을 보장하지 않습니다.
4. 이 패치는 SRAM, .srm, .sav, .state 파일을 열거나 수정하지 않습니다.

Windows
- ROM 파일을 apply_update.bat 위로 끌어 놓거나 apply_update.bat를 실행합니다.
- Python 3가 필요합니다.
- 업데이트 전 ROM은 같은 폴더에 .bak로 백업됩니다.
- ROM 경로와 파일명은 그대로 유지되므로 기존 SRAM 저장명이 바뀌지 않습니다.

새 파일명으로 배포된 ROM에서 기존 저장 이어하기
- migrate_save.bat를 실행합니다.
- 기존 .srm 파일과 새 ROM 파일을 차례로 지정합니다.
- 기존 .srm은 그대로 두고 같은 저장 폴더에 새 ROM 이름의 .srm을 만듭니다.
- 다른 저장이 이미 있으면 덮어쓰지 않고 중단합니다.

Linux/macOS
- ./apply_update.sh "/path/to/Langrisser II (Korean).md"
- ./migrate_save.sh "/path/to/old.srm" "/path/to/new.md"

Android/RetroArch
- patches 폴더에서 자신의 이전 버전에 맞는 .bps 파일을 BPS 패처로 적용합니다.
- 패치 결과 ROM을 기존 ROM과 정확히 같은 파일명으로 둡니다.
- 기존 ROM은 먼저 다른 폴더에 백업합니다.
- RetroArch의 저장 디렉터리에 있는 기존 .srm 파일은 그대로 둡니다.

검증만 하기
python3 apply_update.py apply --package . --rom "ROM경로" --dry-run

지원하지 않는 ROM, 이미 수정된 ROM, 손상된 패치는 쓰기 전에 거부됩니다.
""".encode("utf-8")


def build_package(
    *,
    target_path: Path,
    target_release: str,
    sources: list[SourceRom],
    output_path: Path,
    save_format: str = DEFAULT_SAVE_FORMAT,
    release_notes: str = "",
    force: bool = False,
) -> dict[str, object]:
    if not sources:
        raise ValueError("at least one source ROM is required")
    if output_path.exists() and not force:
        raise FileExistsError(
            f"output package already exists: {output_path}"
        )

    target = target_path.read_bytes()
    target_record = release_record(
        target_release, target, save_format
    )
    target_slug = _slug(target_release)
    source_hashes: set[str] = set()
    patch_names: set[str] = set()
    patch_payloads: dict[str, bytes] = {}
    patch_records: list[dict[str, object]] = []

    for source_spec in sources:
        source = source_spec.path.read_bytes()
        source_record = release_record(
            source_spec.release_id, source, save_format
        )
        if source_record["sha256"] == target_record["sha256"]:
            raise ValueError(
                f"{source_spec.release_id} is identical to the target"
            )
        if source_record["sha256"] in source_hashes:
            raise ValueError(
                "multiple source releases have the same SHA-256"
            )
        if source_record["size"] != target_record["size"]:
            raise ValueError(
                f"{source_spec.release_id} ROM size differs from target"
            )
        if (
            source_record["sram_descriptor"]
            != target_record["sram_descriptor"]
        ):
            raise ValueError(
                f"{source_spec.release_id} SRAM layout differs from target"
            )

        source_slug = _slug(source_spec.release_id)
        patch_name = (
            f"patches/{source_slug}-to-{target_slug}.bps"
        )
        if patch_name in patch_names:
            raise ValueError(
                f"source release IDs collide as filenames: {patch_name}"
            )
        metadata = json.dumps(
            {
                "game": "Langrisser II",
                "edition": "Korean",
                "source_release": source_spec.release_id,
                "target_release": target_release,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        patch = bps_create(source, target, metadata)
        if bps_apply(patch, source) != target:
            raise AssertionError(
                f"BPS round trip failed for {source_spec.release_id}"
            )
        patch_record = dict(source_record)
        patch_record.update(
            {
                "patch_file": patch_name,
                "patch_sha256": sha256_bytes(patch),
                "patch_size": len(patch),
                "format": "BPS1",
            }
        )
        patch_records.append(patch_record)
        patch_payloads[patch_name] = patch
        patch_names.add(patch_name)
        source_hashes.add(str(source_record["sha256"]))

    patch_records.sort(key=lambda row: str(row["release_id"]))
    manifest: dict[str, object] = {
        "package_type": PACKAGE_TYPE,
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "game": "Langrisser II",
        "edition": "Korean",
        "target": target_record,
        "patches": patch_records,
        "compatibility": {
            "in_game_sram": "compatible",
            "save_states": "not_guaranteed",
            "rom_filename_must_be_preserved": True,
            "rom_backup_required": True,
        },
    }
    manifest_bytes = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    files: dict[str, tuple[bytes, int]] = {
        MANIFEST_NAME: (manifest_bytes, 0o644),
        "apply_update.py": (
            (Path(__file__).with_name("rom_update.py")).read_bytes(),
            0o755,
        ),
        "apply_update.bat": (windows_launcher(), 0o644),
        "apply_update.sh": (unix_launcher(), 0o755),
        "migrate_save.bat": (windows_save_launcher(), 0o644),
        "migrate_save.sh": (unix_save_launcher(), 0o755),
        "README_KO.txt": (player_readme(target_release), 0o644),
    }
    if release_notes:
        files["RELEASE_NOTES_KO.txt"] = (
            release_notes.encode("utf-8"),
            0o644,
        )
    for name, payload in patch_payloads.items():
        files[name] = (payload, 0o644)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(files):
            payload, mode = files[name]
            archive.writestr(_zip_info(name, mode), payload)
    return manifest


def parse_source(value: str) -> SourceRom:
    release_id, separator, path = value.partition("=")
    if not separator or not release_id or not path:
        raise argparse.ArgumentTypeError(
            "source must be RELEASE_ID=ROM_PATH"
        )
    return SourceRom(release_id, Path(path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "이전 한국어판 ROM에서 새 한국어판 ROM으로 갱신하는 "
            "세이브 호환 BPS 패키지를 만듭니다."
        )
    )
    parser.add_argument(
        "--target-rom", type=Path, default=DEFAULT_TARGET
    )
    parser.add_argument("--target-release", required=True)
    parser.add_argument(
        "--source",
        action="append",
        type=parse_source,
        required=True,
        help="RELEASE_ID=ROM_PATH (여러 번 지정 가능)",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--save-format", default=DEFAULT_SAVE_FORMAT
    )
    parser.add_argument(
        "--release-notes",
        type=Path,
        help="UTF-8 한국어 릴리스 노트",
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    notes = (
        args.release_notes.read_text(encoding="utf-8")
        if args.release_notes
        else ""
    )
    manifest = build_package(
        target_path=args.target_rom,
        target_release=args.target_release,
        sources=args.source,
        output_path=args.output,
        save_format=args.save_format,
        release_notes=notes,
        force=args.force,
    )
    target = manifest["target"]
    print(f"package: {args.output}")
    print(f"target release: {target['release_id']}")
    print(f"target SHA-256: {target['sha256']}")
    print(f"source patches: {len(manifest['patches'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
