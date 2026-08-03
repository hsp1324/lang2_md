#!/usr/bin/env python3
"""Apply a verified BPS ROM update without touching emulator save files.

This module is intentionally self-contained. Release packages copy it as
``apply_update.py`` so players only need Python and the package itself.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import sys
import tempfile
from typing import BinaryIO
import zipfile
import zlib


PACKAGE_TYPE = "langrisser2-korean-rom-update"
PACKAGE_SCHEMA_VERSION = 1
DEFAULT_SAVE_FORMAT = "lang2-ko-sram-v1"
MANIFEST_NAME = "update.json"
BPS_MAGIC = b"BPS1"
BPS_FOOTER_SIZE = 12
MAX_PATCHED_ROM_SIZE = 64 * 1024 * 1024
MAX_PACKAGE_MEMBER_SIZE = 128 * 1024 * 1024
MAX_SAVE_FILE_SIZE = 8 * 1024 * 1024
SUPPORTED_SAVE_SUFFIXES = frozenset({".srm", ".sram", ".sav"})
MD_HEADER_CHECKSUM_OFFSET = 0x18E
MD_CHECKSUM_DATA_OFFSET = 0x200
MD_SRAM_DESCRIPTOR_START = 0x1B0
MD_SRAM_DESCRIPTOR_END = 0x1BC


class UpdateError(ValueError):
    """Raised when an update cannot be verified or safely applied."""


@dataclass(frozen=True)
class UpdateInspection:
    status: str
    source_release: str | None
    target_release: str
    rom_sha256: str
    patch_record: dict[str, object] | None


@dataclass(frozen=True)
class UpdateResult:
    status: str
    source_release: str | None
    target_release: str
    rom_path: Path
    backup_path: Path | None
    old_sha256: str
    new_sha256: str
    dry_run: bool


@dataclass(frozen=True)
class SaveMigrationResult:
    status: str
    source_path: Path
    destination_path: Path
    backup_path: Path | None
    save_sha256: str
    dry_run: bool


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def md_checksum(payload: bytes) -> int:
    if len(payload) < MD_CHECKSUM_DATA_OFFSET:
        raise UpdateError("Mega Drive ROM header is truncated")
    checksum = 0
    for offset in range(MD_CHECKSUM_DATA_OFFSET, len(payload), 2):
        word = payload[offset] << 8
        if offset + 1 < len(payload):
            word |= payload[offset + 1]
        checksum = (checksum + word) & 0xFFFF
    return checksum


def md_header_checksum(payload: bytes) -> int:
    if len(payload) < MD_HEADER_CHECKSUM_OFFSET + 2:
        raise UpdateError("Mega Drive ROM header is truncated")
    return int.from_bytes(
        payload[
            MD_HEADER_CHECKSUM_OFFSET : MD_HEADER_CHECKSUM_OFFSET + 2
        ],
        "big",
    )


def md_sram_descriptor(payload: bytes) -> bytes:
    if len(payload) < MD_SRAM_DESCRIPTOR_END:
        raise UpdateError("Mega Drive ROM SRAM header is truncated")
    return payload[MD_SRAM_DESCRIPTOR_START:MD_SRAM_DESCRIPTOR_END]


def validate_md_rom(payload: bytes, label: str) -> None:
    actual = md_checksum(payload)
    header = md_header_checksum(payload)
    if actual != header:
        raise UpdateError(
            f"{label} ROM checksum mismatch: "
            f"header {header:04X}, calculated {actual:04X}"
        )


def _encode_bps_number(value: int) -> bytes:
    if value < 0:
        raise ValueError("BPS numbers cannot be negative")
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value == 0:
            encoded.append(byte | 0x80)
            return bytes(encoded)
        encoded.append(byte)
        value -= 1


def _decode_bps_number(
    payload: bytes,
    offset: int,
    limit: int,
) -> tuple[int, int]:
    value = 0
    shift = 1
    while True:
        if offset >= limit:
            raise UpdateError("truncated BPS variable-length number")
        byte = payload[offset]
        offset += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, offset
        shift <<= 7
        value += shift
        if shift > (1 << 63):
            raise UpdateError("BPS variable-length number is too large")


def _matching_run(source: bytes, target: bytes, offset: int) -> int:
    end = offset
    limit = min(len(source), len(target))
    while end < limit and source[end] == target[end]:
        end += 1
    return end - offset


def bps_create(
    source: bytes,
    target: bytes,
    metadata: bytes = b"",
) -> bytes:
    """Create a valid BPS1 patch using SourceRead and TargetRead actions."""

    body = bytearray(BPS_MAGIC)
    body.extend(_encode_bps_number(len(source)))
    body.extend(_encode_bps_number(len(target)))
    body.extend(_encode_bps_number(len(metadata)))
    body.extend(metadata)

    offset = 0
    minimum_source_run = 4
    while offset < len(target):
        run = _matching_run(source, target, offset)
        if run:
            body.extend(_encode_bps_number(((run - 1) << 2) | 0))
            offset += run
            continue

        literal_start = offset
        offset += 1
        while offset < len(target):
            run = _matching_run(source, target, offset)
            if run >= minimum_source_run:
                break
            offset += max(run, 1)
        literal = target[literal_start:offset]
        body.extend(
            _encode_bps_number(((len(literal) - 1) << 2) | 1)
        )
        body.extend(literal)

    body.extend(struct.pack("<I", zlib.crc32(source) & 0xFFFFFFFF))
    body.extend(struct.pack("<I", zlib.crc32(target) & 0xFFFFFFFF))
    body.extend(struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF))
    return bytes(body)


def _decode_signed_bps_number(value: int) -> int:
    magnitude = value >> 1
    return -magnitude if value & 1 else magnitude


def bps_apply(
    patch: bytes,
    source: bytes,
    *,
    max_target_size: int = MAX_PATCHED_ROM_SIZE,
) -> bytes:
    """Apply a BPS1 patch and validate all three BPS CRC32 fields."""

    if len(patch) < len(BPS_MAGIC) + BPS_FOOTER_SIZE:
        raise UpdateError("BPS patch is truncated")
    if patch[:4] != BPS_MAGIC:
        raise UpdateError("patch is not BPS1")

    footer_start = len(patch) - BPS_FOOTER_SIZE
    expected_source_crc, expected_target_crc, expected_patch_crc = (
        struct.unpack("<III", patch[footer_start:])
    )
    actual_patch_crc = zlib.crc32(patch[:-4]) & 0xFFFFFFFF
    if actual_patch_crc != expected_patch_crc:
        raise UpdateError(
            "BPS patch checksum mismatch: "
            f"{actual_patch_crc:08X} != {expected_patch_crc:08X}"
        )
    actual_source_crc = zlib.crc32(source) & 0xFFFFFFFF
    if actual_source_crc != expected_source_crc:
        raise UpdateError(
            "BPS source checksum mismatch: "
            f"{actual_source_crc:08X} != {expected_source_crc:08X}"
        )

    offset = len(BPS_MAGIC)
    source_size, offset = _decode_bps_number(
        patch, offset, footer_start
    )
    target_size, offset = _decode_bps_number(
        patch, offset, footer_start
    )
    metadata_size, offset = _decode_bps_number(
        patch, offset, footer_start
    )
    if source_size != len(source):
        raise UpdateError(
            f"BPS source size mismatch: {len(source)} != {source_size}"
        )
    if target_size > max_target_size:
        raise UpdateError(
            f"BPS target is too large: {target_size} > {max_target_size}"
        )
    if offset + metadata_size > footer_start:
        raise UpdateError("BPS metadata is truncated")
    offset += metadata_size

    target = bytearray()
    source_relative = 0
    target_relative = 0
    while len(target) < target_size:
        command, offset = _decode_bps_number(
            patch, offset, footer_start
        )
        action = command & 3
        length = (command >> 2) + 1
        if len(target) + length > target_size:
            raise UpdateError("BPS command exceeds target size")

        if action == 0:
            start = len(target)
            end = start + length
            if end > len(source):
                raise UpdateError("BPS SourceRead exceeds source size")
            target.extend(source[start:end])
        elif action == 1:
            end = offset + length
            if end > footer_start:
                raise UpdateError("BPS TargetRead data is truncated")
            target.extend(patch[offset:end])
            offset = end
        elif action == 2:
            relative, offset = _decode_bps_number(
                patch, offset, footer_start
            )
            source_relative += _decode_signed_bps_number(relative)
            end = source_relative + length
            if source_relative < 0 or end > len(source):
                raise UpdateError("BPS SourceCopy exceeds source size")
            target.extend(source[source_relative:end])
            source_relative = end
        else:
            relative, offset = _decode_bps_number(
                patch, offset, footer_start
            )
            target_relative += _decode_signed_bps_number(relative)
            if target_relative < 0:
                raise UpdateError("BPS TargetCopy has a negative offset")
            for _ in range(length):
                if target_relative >= len(target):
                    raise UpdateError(
                        "BPS TargetCopy reads beyond generated data"
                    )
                target.append(target[target_relative])
                target_relative += 1

    if offset != footer_start:
        raise UpdateError("BPS patch has trailing command data")
    actual_target_crc = zlib.crc32(target) & 0xFFFFFFFF
    if actual_target_crc != expected_target_crc:
        raise UpdateError(
            "BPS target checksum mismatch: "
            f"{actual_target_crc:08X} != {expected_target_crc:08X}"
        )
    return bytes(target)


def _safe_member_name(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
    ):
        raise UpdateError(f"unsafe package member path: {name!r}")
    return path.as_posix()


class UpdatePackage:
    def __init__(self, path: Path):
        self.path = path
        self._zip: zipfile.ZipFile | None = None

    def __enter__(self) -> "UpdatePackage":
        if self.path.is_dir():
            return self
        if not self.path.is_file():
            raise UpdateError(f"update package not found: {self.path}")
        try:
            self._zip = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile as exc:
            raise UpdateError(
                f"invalid update package ZIP: {self.path}"
            ) from exc
        names = self._zip.namelist()
        if len(names) != len(set(names)):
            raise UpdateError("update package has duplicate members")
        for name in names:
            _safe_member_name(name)
        return self

    def __exit__(self, *args: object) -> None:
        if self._zip is not None:
            self._zip.close()

    def read(self, name: str) -> bytes:
        name = _safe_member_name(name)
        if self._zip is not None:
            try:
                info = self._zip.getinfo(name)
            except KeyError as exc:
                raise UpdateError(
                    f"update package member not found: {name}"
                ) from exc
            if info.file_size > MAX_PACKAGE_MEMBER_SIZE:
                raise UpdateError(
                    f"update package member is too large: {name}"
                )
            return self._zip.read(info)

        base = self.path.resolve()
        member = base.joinpath(*PurePosixPath(name).parts)
        try:
            member.resolve().relative_to(base)
        except ValueError as exc:
            raise UpdateError(
                f"unsafe update package member: {name}"
            ) from exc
        if not member.is_file():
            raise UpdateError(
                f"update package member not found: {name}"
            )
        if member.stat().st_size > MAX_PACKAGE_MEMBER_SIZE:
            raise UpdateError(
                f"update package member is too large: {name}"
            )
        return member.read_bytes()


def _require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise UpdateError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise UpdateError(f"{label} must be an array")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise UpdateError(f"{label} must be a non-empty string")
    return value


def _require_hex(value: object, length: int, label: str) -> str:
    text = _require_string(value, label)
    if len(text) != length:
        raise UpdateError(f"{label} is invalid")
    try:
        int(text, 16)
    except ValueError as exc:
        raise UpdateError(f"{label} is invalid") from exc
    return text


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise UpdateError(f"{label} must be a non-negative integer")
    return value


def load_manifest(package: UpdatePackage) -> dict[str, object]:
    try:
        manifest = json.loads(
            package.read(MANIFEST_NAME).decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("update.json is not valid UTF-8 JSON") from exc
    manifest = _require_dict(manifest, "manifest")
    if manifest.get("package_type") != PACKAGE_TYPE:
        raise UpdateError("unsupported update package type")
    if manifest.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise UpdateError(
            f"unsupported update package schema: "
            f"{manifest.get('schema_version')!r}"
        )
    target = _require_dict(manifest.get("target"), "target")
    _validate_release_record(target, "target")
    patches = _require_list(manifest.get("patches"), "patches")
    if not patches:
        raise UpdateError("update package has no source patches")
    seen_hashes: set[str] = set()
    for index, value in enumerate(patches):
        record = _require_dict(value, f"patches[{index}]")
        _validate_release_record(record, f"patches[{index}]")
        patch_file = _require_string(
            record.get("patch_file"), f"patches[{index}].patch_file"
        )
        _safe_member_name(patch_file)
        patch_sha = _require_hex(
            record.get("patch_sha256"),
            64,
            f"patches[{index}].patch_sha256",
        )
        _require_int(
            record.get("patch_size"),
            f"patches[{index}].patch_size",
        )
        if record.get("format") != "BPS1":
            raise UpdateError(
                f"patches[{index}].format must be BPS1"
            )
        source_hash = str(record["sha256"])
        if source_hash in seen_hashes:
            raise UpdateError(
                f"duplicate source SHA-256 in update package: {source_hash}"
            )
        seen_hashes.add(source_hash)
    return manifest


def _validate_release_record(
    record: dict[str, object],
    label: str,
) -> None:
    _require_string(record.get("release_id"), f"{label}.release_id")
    _require_hex(record.get("sha256"), 64, f"{label}.sha256")
    _require_int(record.get("size"), f"{label}.size")
    _require_hex(
        record.get("md_checksum"), 4, f"{label}.md_checksum"
    )
    _require_hex(
        record.get("sram_descriptor"),
        (MD_SRAM_DESCRIPTOR_END - MD_SRAM_DESCRIPTOR_START) * 2,
        f"{label}.sram_descriptor",
    )
    _require_string(
        record.get("save_format"), f"{label}.save_format"
    )


def _verify_release_identity(
    payload: bytes,
    record: dict[str, object],
    label: str,
) -> None:
    expected_size = int(record["size"])
    if len(payload) != expected_size:
        raise UpdateError(
            f"{label} size mismatch: {len(payload)} != {expected_size}"
        )
    digest = sha256_bytes(payload)
    if digest != record["sha256"]:
        raise UpdateError(
            f"{label} SHA-256 mismatch: {digest} != {record['sha256']}"
        )
    validate_md_rom(payload, label)
    checksum = f"{md_header_checksum(payload):04X}"
    if checksum != str(record["md_checksum"]).upper():
        raise UpdateError(
            f"{label} header checksum mismatch: "
            f"{checksum} != {record['md_checksum']}"
        )
    descriptor = md_sram_descriptor(payload).hex().upper()
    if descriptor != str(record["sram_descriptor"]).upper():
        raise UpdateError(
            f"{label} SRAM descriptor mismatch: "
            f"{descriptor} != {record['sram_descriptor']}"
        )


def inspect_update(
    package_path: Path,
    rom_path: Path,
) -> UpdateInspection:
    if not rom_path.is_file():
        raise UpdateError(f"ROM not found: {rom_path}")
    rom = rom_path.read_bytes()
    rom_hash = sha256_bytes(rom)
    with UpdatePackage(package_path) as package:
        manifest = load_manifest(package)
    target = _require_dict(manifest["target"], "target")
    target_release = str(target["release_id"])
    if (
        rom_hash == target["sha256"]
        and len(rom) == target["size"]
    ):
        _verify_release_identity(rom, target, "current")
        return UpdateInspection(
            status="already_current",
            source_release=None,
            target_release=target_release,
            rom_sha256=rom_hash,
            patch_record=None,
        )

    patches = [
        _require_dict(value, "patch")
        for value in _require_list(manifest["patches"], "patches")
    ]
    patch_record = next(
        (
            record
            for record in patches
            if record["sha256"] == rom_hash
            and record["size"] == len(rom)
        ),
        None,
    )
    if patch_record is None:
        return UpdateInspection(
            status="unsupported_source",
            source_release=None,
            target_release=target_release,
            rom_sha256=rom_hash,
            patch_record=None,
        )
    _verify_release_identity(rom, patch_record, "source")
    if patch_record["save_format"] != target["save_format"]:
        raise UpdateError(
            "update package changes the save format and cannot be "
            "applied without a migration"
        )
    if patch_record["sram_descriptor"] != target["sram_descriptor"]:
        raise UpdateError(
            "update package changes the SRAM layout and is not "
            "save-compatible"
        )
    return UpdateInspection(
        status="supported_source",
        source_release=str(patch_record["release_id"]),
        target_release=target_release,
        rom_sha256=rom_hash,
        patch_record=patch_record,
    )


def _next_backup_path(rom_path: Path, target_release: str) -> Path:
    safe_release = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in target_release
    )
    candidate = rom_path.with_name(
        f"{rom_path.name}.before-{safe_release}.bak"
    )
    sequence = 2
    while candidate.exists():
        candidate = rom_path.with_name(
            f"{rom_path.name}.before-{safe_release}.{sequence}.bak"
        )
        sequence += 1
    return candidate


def _next_save_backup_path(save_path: Path) -> Path:
    candidate = save_path.with_name(
        f"{save_path.name}.before-save-migration.bak"
    )
    sequence = 2
    while candidate.exists():
        candidate = save_path.with_name(
            f"{save_path.name}.before-save-migration.{sequence}.bak"
        )
        sequence += 1
    return candidate


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_verified_temp(
    rom_path: Path,
    target: bytes,
) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{rom_path.name}.update-",
        suffix=".tmp",
        dir=rom_path.parent,
    )
    temp_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(target)
            handle.flush()
            os.fsync(handle.fileno())
        mode = stat.S_IMODE(rom_path.stat().st_mode)
        os.chmod(temp_path, mode)
        return temp_path
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _write_save_temp(destination_path: Path, payload: bytes, mode: int) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.migration-",
        suffix=".tmp",
        dir=destination_path.parent,
    )
    temp_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        if sha256_bytes(temp_path.read_bytes()) != sha256_bytes(payload):
            raise UpdateError("temporary save copy verification failed")
        return temp_path
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _restore_from_backup(backup_path: Path, rom_path: Path) -> None:
    rollback_path = _write_verified_temp(
        rom_path, backup_path.read_bytes()
    )
    try:
        os.replace(rollback_path, rom_path)
        _fsync_directory(rom_path.parent)
    finally:
        rollback_path.unlink(missing_ok=True)


def apply_update(
    package_path: Path,
    rom_path: Path,
    *,
    dry_run: bool = False,
) -> UpdateResult:
    rom_path = rom_path.resolve()
    package_path = package_path.resolve()
    inspection = inspect_update(package_path, rom_path)
    if inspection.status == "already_current":
        return UpdateResult(
            status="already_current",
            source_release=None,
            target_release=inspection.target_release,
            rom_path=rom_path,
            backup_path=None,
            old_sha256=inspection.rom_sha256,
            new_sha256=inspection.rom_sha256,
            dry_run=dry_run,
        )
    if inspection.status != "supported_source":
        raise UpdateError(
            "unsupported or modified ROM: "
            f"SHA-256 {inspection.rom_sha256}"
        )
    assert inspection.patch_record is not None

    source = rom_path.read_bytes()
    if sha256_bytes(source) != inspection.rom_sha256:
        raise UpdateError("ROM changed while the update was being prepared")

    with UpdatePackage(package_path) as package:
        manifest = load_manifest(package)
        target_record = _require_dict(manifest["target"], "target")
        patch_name = str(inspection.patch_record["patch_file"])
        patch = package.read(patch_name)
    patch_hash = sha256_bytes(patch)
    if patch_hash != inspection.patch_record["patch_sha256"]:
        raise UpdateError(
            f"patch SHA-256 mismatch: {patch_hash} != "
            f"{inspection.patch_record['patch_sha256']}"
        )
    if len(patch) != inspection.patch_record["patch_size"]:
        raise UpdateError(
            f"patch size mismatch: {len(patch)} != "
            f"{inspection.patch_record['patch_size']}"
        )

    target = bps_apply(patch, source)
    _verify_release_identity(target, target_record, "target")
    if md_sram_descriptor(source) != md_sram_descriptor(target):
        raise UpdateError(
            "patched ROM changes the SRAM descriptor; update aborted"
        )
    if len(source) != len(target):
        raise UpdateError(
            "patched ROM changes the ROM size; update aborted"
        )
    if dry_run:
        return UpdateResult(
            status="verified",
            source_release=inspection.source_release,
            target_release=inspection.target_release,
            rom_path=rom_path,
            backup_path=None,
            old_sha256=inspection.rom_sha256,
            new_sha256=sha256_bytes(target),
            dry_run=True,
        )

    temp_path = _write_verified_temp(rom_path, target)
    backup_path = _next_backup_path(
        rom_path, inspection.target_release
    )
    replaced = False
    try:
        if sha256_bytes(rom_path.read_bytes()) != inspection.rom_sha256:
            raise UpdateError(
                "ROM changed before the atomic replacement; update aborted"
            )
        shutil.copy2(rom_path, backup_path)
        _fsync_file(backup_path)
        if sha256_bytes(backup_path.read_bytes()) != inspection.rom_sha256:
            backup_path.unlink(missing_ok=True)
            raise UpdateError(
                "ROM backup verification failed; update aborted"
            )
        _fsync_directory(rom_path.parent)
        os.replace(temp_path, rom_path)
        replaced = True
        _fsync_directory(rom_path.parent)
        installed = rom_path.read_bytes()
        _verify_release_identity(installed, target_record, "installed")
    except BaseException:
        if replaced:
            try:
                _restore_from_backup(backup_path, rom_path)
            except BaseException as rollback_error:
                raise UpdateError(
                    "update verification failed and automatic rollback "
                    f"also failed; restore {backup_path} manually"
                ) from rollback_error
        raise
    finally:
        temp_path.unlink(missing_ok=True)

    return UpdateResult(
        status="updated",
        source_release=inspection.source_release,
        target_release=inspection.target_release,
        rom_path=rom_path,
        backup_path=backup_path,
        old_sha256=inspection.rom_sha256,
        new_sha256=sha256_bytes(target),
        dry_run=False,
    )


def migrate_save(
    save_path: Path,
    target_rom_path: Path,
    *,
    destination_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> SaveMigrationResult:
    """Copy an in-game save to the basename used by a new ROM.

    The source save is never renamed or modified. Existing destination saves
    are rejected unless they are byte-identical or ``force`` is requested.
    Emulator save states are intentionally unsupported.
    """

    save_path = save_path.resolve()
    target_rom_path = target_rom_path.resolve()
    if not save_path.is_file():
        raise UpdateError(f"save file not found: {save_path}")
    suffix = save_path.suffix.lower()
    if suffix not in SUPPORTED_SAVE_SUFFIXES:
        raise UpdateError(
            "only in-game SRAM saves are supported "
            f"({', '.join(sorted(SUPPORTED_SAVE_SUFFIXES))}); "
            "save states cannot be migrated"
        )
    size = save_path.stat().st_size
    if size <= 0:
        raise UpdateError("save file is empty")
    if size > MAX_SAVE_FILE_SIZE:
        raise UpdateError(
            f"save file is too large: {size} bytes "
            f"(maximum {MAX_SAVE_FILE_SIZE})"
        )
    if not target_rom_path.is_file():
        raise UpdateError(f"target ROM not found: {target_rom_path}")
    validate_md_rom(target_rom_path.read_bytes(), "target")

    if destination_dir is None:
        destination_dir = save_path.parent
    else:
        destination_dir = destination_dir.resolve()
    if not destination_dir.is_dir():
        raise UpdateError(
            f"save destination directory not found: {destination_dir}"
        )
    destination_path = destination_dir / (
        f"{target_rom_path.stem}{suffix}"
    )
    payload = save_path.read_bytes()
    source_hash = sha256_bytes(payload)

    if destination_path.resolve() == save_path:
        return SaveMigrationResult(
            status="already_named",
            source_path=save_path,
            destination_path=destination_path,
            backup_path=None,
            save_sha256=source_hash,
            dry_run=dry_run,
        )

    destination_exists = destination_path.exists()
    if destination_exists:
        if not destination_path.is_file():
            raise UpdateError(
                f"save destination is not a file: {destination_path}"
            )
        destination_hash = sha256_bytes(destination_path.read_bytes())
        if destination_hash == source_hash:
            return SaveMigrationResult(
                status="already_copied",
                source_path=save_path,
                destination_path=destination_path,
                backup_path=None,
                save_sha256=source_hash,
                dry_run=dry_run,
            )
        if not force:
            raise UpdateError(
                "a different save already exists for the target ROM; "
                "use --force only after checking which save to keep: "
                f"{destination_path}"
            )

    planned_status = "would_replace" if destination_exists else "would_copy"
    if dry_run:
        return SaveMigrationResult(
            status=planned_status,
            source_path=save_path,
            destination_path=destination_path,
            backup_path=None,
            save_sha256=source_hash,
            dry_run=True,
        )

    source_mode = stat.S_IMODE(save_path.stat().st_mode)
    temp_path = _write_save_temp(destination_path, payload, source_mode)
    backup_path: Path | None = None
    installed = False
    try:
        if sha256_bytes(save_path.read_bytes()) != source_hash:
            raise UpdateError(
                "source save changed while migration was being prepared"
            )
        if destination_exists:
            backup_path = _next_save_backup_path(destination_path)
            shutil.copy2(destination_path, backup_path)
            _fsync_file(backup_path)
            if (
                sha256_bytes(backup_path.read_bytes())
                != sha256_bytes(destination_path.read_bytes())
            ):
                backup_path.unlink(missing_ok=True)
                backup_path = None
                raise UpdateError(
                    "existing save backup verification failed; "
                    "migration aborted"
                )
        os.replace(temp_path, destination_path)
        installed = True
        _fsync_directory(destination_path.parent)
        if sha256_bytes(destination_path.read_bytes()) != source_hash:
            raise UpdateError("migrated save verification failed")
    except BaseException:
        if installed:
            if backup_path is not None:
                restore_path = _write_save_temp(
                    destination_path,
                    backup_path.read_bytes(),
                    stat.S_IMODE(backup_path.stat().st_mode),
                )
                try:
                    os.replace(restore_path, destination_path)
                    _fsync_directory(destination_path.parent)
                finally:
                    restore_path.unlink(missing_ok=True)
            else:
                destination_path.unlink(missing_ok=True)
                _fsync_directory(destination_path.parent)
        raise
    finally:
        temp_path.unlink(missing_ok=True)

    return SaveMigrationResult(
        status="replaced" if destination_exists else "copied",
        source_path=save_path,
        destination_path=destination_path,
        backup_path=backup_path,
        save_sha256=source_hash,
        dry_run=False,
    )


def _default_package_path() -> Path:
    return Path(__file__).resolve().parent


def _print_inspection(inspection: UpdateInspection) -> None:
    print(f"대상 버전: {inspection.target_release}")
    print(f"ROM SHA-256: {inspection.rom_sha256}")
    if inspection.status == "already_current":
        print("상태: 이미 최신 버전입니다")
    elif inspection.status == "supported_source":
        print(f"현재 버전: {inspection.source_release}")
        print("상태: 안전하게 업데이트할 수 있습니다")
    else:
        print("상태: 지원하지 않거나 수정된 ROM입니다")


def _confirm_apply(inspection: UpdateInspection) -> bool:
    print(
        f"{inspection.source_release} -> "
        f"{inspection.target_release} 업데이트"
    )
    print("ROM 파일명은 유지되고 기존 ROM은 .bak 파일로 백업됩니다")
    print("SRAM/세이브 파일은 열거나 수정하지 않습니다")
    answer = input("계속하시겠습니까? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "저장 파일을 건드리지 않고 랑그릿사 II 한국어판 ROM을 "
            "검증·업데이트합니다."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "apply"):
        child = subparsers.add_parser(command)
        child.add_argument("--rom", type=Path, required=True)
        child.add_argument(
            "--package",
            type=Path,
            default=_default_package_path(),
        )
        if command == "apply":
            child.add_argument("--dry-run", action="store_true")
            child.add_argument(
                "--yes",
                action="store_true",
                help="확인 질문 없이 적용합니다",
            )
    migration = subparsers.add_parser(
        "migrate-save",
        help="기존 게임 내 저장을 새 ROM 파일명으로 안전하게 복사합니다",
    )
    migration.add_argument("--save", type=Path, required=True)
    migration.add_argument("--target-rom", type=Path, required=True)
    migration.add_argument("--destination-dir", type=Path)
    migration.add_argument("--dry-run", action="store_true")
    migration.add_argument(
        "--force",
        action="store_true",
        help="다른 대상 저장을 백업한 뒤 교체합니다",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "migrate-save":
        try:
            result = migrate_save(
                args.save,
                args.target_rom,
                destination_dir=args.destination_dir,
                dry_run=args.dry_run,
                force=args.force,
            )
        except (OSError, UpdateError) as exc:
            print(f"오류: {exc}", file=sys.stderr)
            return 2
        if result.status in {"would_copy", "would_replace"}:
            print("검증 완료: 실제 세이브 파일은 변경하지 않았습니다")
            print(f"생성 예정: {result.destination_path}")
        elif result.status == "already_named":
            print("세이브 파일명이 이미 새 ROM과 일치합니다")
        elif result.status == "already_copied":
            print("같은 세이브가 이미 새 ROM 이름으로 존재합니다")
        else:
            print(f"세이브 연결 완료: {result.destination_path}")
            print(f"기존 세이브 보존: {result.source_path}")
            if result.backup_path is not None:
                print(f"교체 전 대상 세이브 백업: {result.backup_path}")
        print(f"세이브 SHA-256: {result.save_sha256}")
        print("상태 저장이 아닌 게임 안의 불러오기를 사용하세요")
        return 0
    try:
        inspection = inspect_update(args.package, args.rom)
        if args.command == "inspect":
            _print_inspection(inspection)
            return 0 if inspection.status != "unsupported_source" else 2
        if inspection.status == "already_current":
            _print_inspection(inspection)
            return 0
        if inspection.status == "unsupported_source":
            _print_inspection(inspection)
            return 2
        if not args.dry_run and not args.yes and not _confirm_apply(
            inspection
        ):
            print("취소했습니다")
            return 1
        result = apply_update(
            args.package,
            args.rom,
            dry_run=args.dry_run,
        )
    except (OSError, UpdateError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2

    if result.status == "verified":
        print("검증 완료: 실제 파일은 변경하지 않았습니다")
    elif result.status == "updated":
        print(f"업데이트 완료: {result.rom_path}")
        print(f"이전 ROM 백업: {result.backup_path}")
        print("ROM 파일명이 유지되어 기존 SRAM 저장을 계속 사용합니다")
        print(
            "에뮬레이터 상태 저장은 호환을 보장하지 않습니다. "
            "게임 내 저장을 불러오세요"
        )
    else:
        print("이미 최신 버전입니다")
    print(f"새 SHA-256: {result.new_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
