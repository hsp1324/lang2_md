#!/usr/bin/env python3
"""Install a newer ROM without breaking its emulator SRAM filename link."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from tools import rom_update


SAVE_EXTENSIONS = {".srm", ".sav", ".sram"}
MAX_ROM_SIZE = 64 * 1024 * 1024


class SaveLinkError(ValueError):
    """Raised when a ROM cannot be installed without risking saved data."""


@dataclass(frozen=True)
class RomInfo:
    path: Path
    size: int
    sha256: str
    md_checksum: str
    sram_descriptor: str


@dataclass(frozen=True)
class InstallResult:
    current: RomInfo
    latest: RomInfo
    linked_saves: tuple[Path, ...]
    backup_path: Path | None
    installed_path: Path
    dry_run: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_rom(path: Path) -> RomInfo:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise SaveLinkError(f"ROM을 찾을 수 없습니다: {path}")
    size = path.stat().st_size
    if not 0x200 <= size <= MAX_ROM_SIZE:
        raise SaveLinkError(f"ROM 크기가 올바르지 않습니다: {size}바이트")
    payload = path.read_bytes()
    if payload[0x100:0x104] != b"SEGA":
        raise SaveLinkError(f"메가드라이브 ROM 헤더가 아닙니다: {path.name}")
    try:
        rom_update.validate_md_rom(payload, path.name)
    except rom_update.UpdateError as exc:
        raise SaveLinkError(str(exc)) from exc
    return RomInfo(
        path=path,
        size=size,
        sha256=rom_update.sha256_bytes(payload),
        md_checksum=f"{rom_update.md_header_checksum(payload):04X}",
        sram_descriptor=(
            rom_update.md_sram_descriptor(payload).hex().upper()
        ),
    )


def default_save_roots(
    *,
    home: Path | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[Path, ...]:
    home = (home or Path.home()).expanduser()
    environ = environ or dict(os.environ)
    candidates: list[Path] = []
    explicit = environ.get("RETROARCH_SAVE_DIR")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    candidates.extend(
        [
            home / "RetroArch/saves",
            home / ".config/retroarch/saves",
            home
            / ".var/app/org.libretro.RetroArch/config/retroarch/saves",
            home
            / "snap/retroarch/common/.config/retroarch/saves",
            home / "Documents/RetroArch/saves",
        ]
    )
    for key in ("APPDATA", "LOCALAPPDATA"):
        value = environ.get(key)
        if value:
            candidates.append(Path(value) / "RetroArch/saves")

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            unique.append(resolved)
    return tuple(unique)


def _matches_save(path: Path, rom_stem: str) -> bool:
    return (
        path.is_file()
        and path.suffix.casefold() in SAVE_EXTENSIONS
        and path.stem.casefold() == rom_stem.casefold()
    )


def _walk_matching_saves(root: Path, rom_stem: str) -> list[Path]:
    matches: list[Path] = []
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = [
            name
            for name in names
            if not name.startswith(".") and name != "__pycache__"
        ]
        parent = Path(directory)
        for name in files:
            path = parent / name
            if _matches_save(path, rom_stem):
                matches.append(path.resolve())
    return matches


def find_linked_saves(
    rom_path: Path,
    *,
    save_roots: tuple[Path, ...] = (),
) -> tuple[Path, ...]:
    rom_path = rom_path.expanduser().resolve()
    matches = [
        path.resolve()
        for path in rom_path.parent.iterdir()
        if _matches_save(path, rom_path.stem)
    ]
    roots = list(save_roots) if save_roots else list(default_save_roots())
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir() or root == rom_path.parent:
            continue
        matches.extend(_walk_matching_saves(root, rom_path.stem))
    return tuple(sorted(set(matches), key=lambda path: str(path).casefold()))


def validate_compatible_roms(current: RomInfo, latest: RomInfo) -> None:
    if current.path == latest.path:
        raise SaveLinkError("현재 ROM과 최신 ROM은 서로 다른 파일이어야 합니다")
    if current.sha256 == latest.sha256:
        raise SaveLinkError("현재 ROM과 최신 ROM의 내용이 이미 같습니다")
    if current.size != latest.size:
        raise SaveLinkError(
            "ROM 크기가 달라 저장 호환 업데이트로 설치할 수 없습니다: "
            f"{current.size} != {latest.size}"
        )
    if current.sram_descriptor != latest.sram_descriptor:
        raise SaveLinkError(
            "SRAM 주소 형식이 달라 자동 연결할 수 없습니다: "
            f"{current.sram_descriptor} != {latest.sram_descriptor}"
        )


def _next_backup_path(path: Path, latest_sha256: str) -> Path:
    stem = f"{path.name}.before-{latest_sha256[:8]}.bak"
    candidate = path.with_name(stem)
    sequence = 2
    while candidate.exists():
        candidate = path.with_name(f"{stem}.{sequence}")
        sequence += 1
    return candidate


def _write_temp(path: Path, payload: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{path.name}.save-link-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def install_latest_rom(
    current_path: Path,
    latest_path: Path,
    *,
    save_roots: tuple[Path, ...] = (),
    dry_run: bool = False,
) -> InstallResult:
    current = inspect_rom(current_path)
    latest = inspect_rom(latest_path)
    validate_compatible_roms(current, latest)
    linked_saves = find_linked_saves(
        current.path,
        save_roots=save_roots,
    )
    save_hashes = {
        path: _sha256_file(path)
        for path in linked_saves
    }
    if dry_run:
        return InstallResult(
            current=current,
            latest=latest,
            linked_saves=linked_saves,
            backup_path=None,
            installed_path=current.path,
            dry_run=True,
        )

    source_payload = current.path.read_bytes()
    latest_payload = latest.path.read_bytes()
    if rom_update.sha256_bytes(source_payload) != current.sha256:
        raise SaveLinkError("검사 중 현재 ROM이 변경되어 설치를 중단했습니다")
    if rom_update.sha256_bytes(latest_payload) != latest.sha256:
        raise SaveLinkError("검사 중 최신 ROM이 변경되어 설치를 중단했습니다")

    backup_path = _next_backup_path(current.path, latest.sha256)
    temporary = _write_temp(current.path, latest_payload)
    replaced = False
    try:
        shutil.copy2(current.path, backup_path)
        if _sha256_file(backup_path) != current.sha256:
            backup_path.unlink(missing_ok=True)
            raise SaveLinkError("기존 ROM 백업 검증에 실패했습니다")
        os.replace(temporary, current.path)
        replaced = True
        installed = inspect_rom(current.path)
        if installed.sha256 != latest.sha256:
            raise SaveLinkError("설치된 ROM의 SHA-256 검증에 실패했습니다")
        after_save_hashes = {
            path: _sha256_file(path)
            for path in linked_saves
        }
        if after_save_hashes != save_hashes:
            raise SaveLinkError("설치 중 저장 파일이 변경되었습니다")
    except BaseException:
        if replaced and backup_path.is_file():
            rollback = _write_temp(current.path, backup_path.read_bytes())
            try:
                os.replace(rollback, current.path)
            finally:
                rollback.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)

    return InstallResult(
        current=current,
        latest=latest,
        linked_saves=linked_saves,
        backup_path=backup_path,
        installed_path=current.path,
        dry_run=False,
    )


def result_document(result: InstallResult) -> dict[str, object]:
    return {
        "status": "verified" if result.dry_run else "installed",
        "current_rom": str(result.current.path),
        "installed_path": str(result.installed_path),
        "old_sha256": result.current.sha256,
        "new_sha256": result.latest.sha256,
        "sram_descriptor": result.latest.sram_descriptor,
        "linked_saves": [str(path) for path in result.linked_saves],
        "backup_path": (
            str(result.backup_path)
            if result.backup_path is not None
            else None
        ),
    }


def _paths(values: list[Path]) -> tuple[Path, ...]:
    return tuple(path.expanduser() for path in values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "최신 ROM을 기존 ROM 이름으로 설치해 RetroArch SRAM 연결을 "
            "유지합니다"
        )
    )
    parser.add_argument("current_rom", type=Path)
    parser.add_argument("latest_rom", type=Path)
    parser.add_argument(
        "--save-dir",
        type=Path,
        action="append",
        default=[],
        help="RetroArch 저장 폴더. 반복 지정 가능",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="검사 후 기존 ROM을 백업하고 최신 ROM으로 교체",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = install_latest_rom(
            args.current_rom,
            args.latest_rom,
            save_roots=_paths(args.save_dir),
            dry_run=not args.install,
        )
    except (OSError, SaveLinkError) as exc:
        raise SystemExit(f"오류: {exc}") from exc
    document = result_document(result)
    if args.json:
        print(json.dumps(document, ensure_ascii=False, indent=2))
    else:
        print(
            "검사 완료" if result.dry_run else "설치 완료",
            f"\nROM: {result.installed_path}",
            f"\n연결 저장 파일: {len(result.linked_saves)}개",
        )
        for path in result.linked_saves:
            print(f"  - {path}")
        if result.backup_path is not None:
            print(f"백업: {result.backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
