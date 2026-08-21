#!/usr/bin/env python3
"""Cross-platform GUI and CLI patcher for Langrisser II Korean v1.3.9."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePath
import struct
import sys
import tempfile
from typing import Callable
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rom_update import (
    UpdateError,
    bps_apply,
    migrate_save,
    sha256_bytes,
    validate_md_rom,
)


APP_TITLE = "랑그릿사 II 한국어 패처 v1.3.9"
MANIFEST_FILENAME = "v1.3.9.json"
PATCHER_RELEASE = "v1.3.9"
ROM_SUFFIXES = frozenset({".md", ".bin", ".gen", ".smd", ".zip"})


@dataclass(frozen=True)
class SourceRom:
    payload: bytes
    display_name: str
    output_dir: Path


@dataclass(frozen=True)
class PatchResult:
    target_id: str
    output_path: Path
    status: str
    sha256: str
    backup_path: Path | None


def _asset_dir() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root is not None:
        return Path(frozen_root) / "patches"
    return ROOT / "patches"


def load_release_manifest() -> dict[str, object]:
    path = _asset_dir() / MANIFEST_FILENAME
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f"패처 manifest를 읽을 수 없습니다: {path}") from exc
    if manifest.get("schema_version") != 1:
        raise UpdateError("지원하지 않는 패처 manifest입니다")
    if manifest.get("release") != PATCHER_RELEASE:
        raise UpdateError("패처 버전과 manifest 버전이 다릅니다")
    source = manifest.get("source")
    targets = manifest.get("targets")
    if not isinstance(source, dict) or not isinstance(targets, list):
        raise UpdateError("패처 manifest 구조가 잘못되었습니다")
    if len(targets) != 3:
        raise UpdateError(
            "원작 디자인판·최신 디자인 일반판·하드판 정보가 완전하지 않습니다"
        )
    target_ids = {
        value.get("id") for value in targets if isinstance(value, dict)
    }
    if target_ids != {"pure", "normal", "hard"}:
        raise UpdateError("패처 대상 ID가 완전하지 않습니다")
    return manifest


def _normalize_source(payload: bytes, source: dict[str, object]) -> bytes:
    expected_size = int(source["size"])
    expected_hash = str(source["sha256"])
    if len(payload) == expected_size and sha256_bytes(payload) == expected_hash:
        return payload
    if len(payload) == expected_size + 512:
        headerless = payload[512:]
        if sha256_bytes(headerless) == expected_hash:
            return headerless
    raise UpdateError(
        "지원하는 일본판 ROM이 아닙니다. "
        f"필요 SHA-256: {expected_hash}"
    )


def read_source_rom(path: Path) -> SourceRom:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise UpdateError(f"원본 파일을 찾을 수 없습니다: {path}")
    manifest = load_release_manifest()
    source = manifest["source"]
    assert isinstance(source, dict)

    if path.suffix.lower() != ".zip":
        payload = _normalize_source(path.read_bytes(), source)
        return SourceRom(payload, path.name, path.parent)

    try:
        with zipfile.ZipFile(path) as archive:
            candidates = [
                info
                for info in archive.infolist()
                if not info.is_dir()
                and info.file_size
                in {int(source["size"]), int(source["headered_size"])}
            ]
            for info in candidates:
                try:
                    payload = _normalize_source(archive.read(info), source)
                except UpdateError:
                    continue
                return SourceRom(
                    payload,
                    f"{path.name} / {info.filename}",
                    path.parent,
                )
    except (OSError, zipfile.BadZipFile) as exc:
        raise UpdateError(f"ZIP 파일을 읽을 수 없습니다: {path}") from exc
    raise UpdateError("ZIP 안에서 지원하는 일본판 ROM을 찾지 못했습니다")


def discover_source_rom(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in ROM_SUFFIXES:
            continue
        try:
            read_source_rom(path)
        except (OSError, UpdateError):
            continue
        return path
    return None


def _safe_asset_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise UpdateError(f"manifest의 {label} 값이 잘못되었습니다")
    path = PurePath(value)
    if path.name != value or value in {".", ".."}:
        raise UpdateError(f"manifest의 {label} 경로가 안전하지 않습니다")
    return value


def _inspect_bps_asset(patch: bytes) -> dict[str, int]:
    """Validate the packaged BPS container without needing copyrighted ROM data."""
    footer_size = 12
    if len(patch) < 4 + footer_size or patch[:4] != b"BPS1":
        raise UpdateError("내장 패치가 올바른 BPS1 파일이 아닙니다")
    footer_start = len(patch) - footer_size
    source_crc32, target_crc32, expected_patch_crc32 = struct.unpack(
        "<III", patch[footer_start:]
    )
    actual_patch_crc32 = zlib.crc32(patch[:-4]) & 0xFFFFFFFF
    if actual_patch_crc32 != expected_patch_crc32:
        raise UpdateError("내장 BPS 패치 체크섬이 다릅니다")

    def decode(offset: int) -> tuple[int, int]:
        value = 0
        shift = 1
        while True:
            if offset >= footer_start:
                raise UpdateError("내장 BPS 헤더가 잘렸습니다")
            byte = patch[offset]
            offset += 1
            value += (byte & 0x7F) * shift
            if byte & 0x80:
                return value, offset
            shift <<= 7
            value += shift
            if shift > (1 << 63):
                raise UpdateError("내장 BPS 헤더 값이 너무 큽니다")

    source_size, offset = decode(4)
    target_size, offset = decode(offset)
    metadata_size, offset = decode(offset)
    if offset + metadata_size > footer_start:
        raise UpdateError("내장 BPS 메타데이터가 잘렸습니다")
    return {
        "source_size": source_size,
        "target_size": target_size,
        "source_crc32": source_crc32,
        "target_crc32": target_crc32,
        "patch_crc32": expected_patch_crc32,
    }


def verify_embedded_assets(
    source_payload: bytes | None = None,
) -> dict[str, object]:
    """Hash every embedded patch and optionally apply all three end to end."""
    manifest = load_release_manifest()
    source = manifest["source"]
    targets = manifest["targets"]
    assert isinstance(source, dict)
    assert isinstance(targets, list)
    normalized_source = (
        _normalize_source(source_payload, source)
        if source_payload is not None
        else None
    )
    seen_patch_names: set[str] = set()
    seen_output_names: set[str] = set()
    records: list[dict[str, object]] = []
    for value in targets:
        if not isinstance(value, dict):
            raise UpdateError("패치 대상 manifest가 잘못되었습니다")
        patch_name = _safe_asset_name(value.get("patch_filename"), "패치")
        output_name = _safe_asset_name(value.get("output_filename"), "출력")
        if patch_name in seen_patch_names or output_name in seen_output_names:
            raise UpdateError("패처 manifest에 중복 파일명이 있습니다")
        seen_patch_names.add(patch_name)
        seen_output_names.add(output_name)
        try:
            patch = (_asset_dir() / patch_name).read_bytes()
        except OSError as exc:
            raise UpdateError(f"내장 패치를 읽을 수 없습니다: {patch_name}") from exc
        if len(patch) != int(value["patch_size"]):
            raise UpdateError(f"내장 패치 크기가 다릅니다: {patch_name}")
        if sha256_bytes(patch) != str(value["patch_sha256"]):
            raise UpdateError(f"내장 패치 해시가 다릅니다: {patch_name}")
        bps = _inspect_bps_asset(patch)
        if bps["source_size"] != int(source["size"]):
            raise UpdateError(f"내장 패치 원본 크기가 다릅니다: {patch_name}")
        if bps["target_size"] != int(value["output_size"]):
            raise UpdateError(f"내장 패치 결과 크기가 다릅니다: {patch_name}")
        applied = False
        if normalized_source is not None:
            target = bps_apply(patch, normalized_source)
            if len(target) != int(value["output_size"]):
                raise UpdateError(f"{value['label_ko']} 결과 크기가 다릅니다")
            if sha256_bytes(target) != str(value["output_sha256"]):
                raise UpdateError(f"{value['label_ko']} 결과 해시가 다릅니다")
            validate_md_rom(target, str(value["label_ko"]))
            applied = True
        records.append(
            {
                "id": str(value["id"]),
                "patch_filename": patch_name,
                "patch_sha256": str(value["patch_sha256"]),
                "output_filename": output_name,
                "output_sha256": str(value["output_sha256"]),
                "bps_container_verified": True,
                "application_verified": applied,
            }
        )
    return {
        "release": PATCHER_RELEASE,
        "asset_directory": str(_asset_dir()),
        "embedded_manifest_verified": True,
        "all_patches_hashed": True,
        "all_patches_applied": normalized_source is not None,
        "targets": records,
    }


def _next_backup_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.name}.before-{PATCHER_RELEASE}.bak")
    sequence = 2
    while candidate.exists():
        candidate = path.with_name(
            f"{path.name}.before-{PATCHER_RELEASE}.{sequence}.bak"
        )
        sequence += 1
    return candidate


def _stage_payload(path: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.patch-", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if sha256_bytes(temp_path.read_bytes()) != sha256_bytes(payload):
            raise UpdateError("임시 ROM 검증에 실패했습니다")
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _atomic_write(path: Path, payload: bytes) -> None:
    temp_path = _stage_payload(path, payload)
    try:
        os.replace(temp_path, path)
        if sha256_bytes(path.read_bytes()) != sha256_bytes(payload):
            raise UpdateError("생성된 ROM 검증에 실패했습니다")
    finally:
        temp_path.unlink(missing_ok=True)


def _same_existing_file(first: Path, second: Path) -> bool:
    try:
        return os.path.samefile(first, second)
    except (FileNotFoundError, OSError):
        return first.resolve() == second.resolve()


def apply_release(
    source_path: Path,
    *,
    output_dir: Path | None = None,
    confirm_overwrite: Callable[[Path], bool] | None = None,
) -> list[PatchResult]:
    source_file = source_path.expanduser().resolve()
    source_rom = read_source_rom(source_file)
    if output_dir is None:
        output_dir = source_rom.output_dir
    output_dir = output_dir.expanduser().resolve()
    if not output_dir.is_dir():
        raise UpdateError(f"출력 폴더를 찾을 수 없습니다: {output_dir}")
    manifest = load_release_manifest()
    targets = manifest["targets"]
    assert isinstance(targets, list)

    prepared: list[tuple[dict[str, object], Path, bytes, str]] = []
    for value in targets:
        if not isinstance(value, dict):
            raise UpdateError("패치 대상 manifest가 잘못되었습니다")
        patch_name = _safe_asset_name(value.get("patch_filename"), "패치")
        output_name = _safe_asset_name(value.get("output_filename"), "출력")
        patch_path = _asset_dir() / patch_name
        patch = patch_path.read_bytes()
        patch_hash = sha256_bytes(patch)
        if len(patch) != int(value["patch_size"]):
            raise UpdateError(f"내장 패치 크기가 다릅니다: {patch_name}")
        if patch_hash != value["patch_sha256"]:
            raise UpdateError(f"내장 패치 해시가 다릅니다: {patch_name}")
        target = bps_apply(patch, source_rom.payload)
        expected_hash = str(value["output_sha256"])
        if len(target) != int(value["output_size"]):
            raise UpdateError(f"{value['label_ko']} 결과 크기가 다릅니다")
        if sha256_bytes(target) != expected_hash:
            raise UpdateError(f"{value['label_ko']} 결과 해시가 다릅니다")
        validate_md_rom(target, str(value["label_ko"]))
        output_path = output_dir / output_name
        prepared.append((value, output_path, target, expected_hash))

    output_paths = [output_path for _, output_path, _, _ in prepared]
    if len(output_paths) != len(set(output_paths)):
        raise UpdateError("패처 manifest의 결과 파일명이 중복되었습니다")
    for output_path in output_paths:
        if _same_existing_file(source_file, output_path):
            raise UpdateError(
                "원본 ROM과 결과 ROM 경로가 같습니다. "
                "원본을 보존할 다른 결과 폴더를 선택하세요: "
                f"{output_path}"
            )

    decisions: dict[Path, str] = {}
    original_hashes: dict[Path, str] = {}
    for _, output_path, _, expected_hash in prepared:
        if not output_path.exists():
            decisions[output_path] = "create"
            continue
        if not output_path.is_file():
            raise UpdateError(f"출력 경로가 파일이 아닙니다: {output_path}")
        existing_hash = sha256_bytes(output_path.read_bytes())
        original_hashes[output_path] = existing_hash
        if existing_hash == expected_hash:
            decisions[output_path] = "current"
            continue
        if confirm_overwrite is None or not confirm_overwrite(output_path):
            raise UpdateError(
                "다른 내용의 결과 ROM이 이미 있습니다: " f"{output_path}"
            )
        decisions[output_path] = "replace"

    mutable = [
        row for row in prepared if decisions[row[1]] in {"create", "replace"}
    ]
    staged: dict[Path, Path] = {}
    backup_paths: dict[Path, Path] = {}
    committed: list[tuple[Path, str]] = []
    try:
        # No visible result changes occur until all three target payloads have
        # been written to verified sibling staging files.
        for _, output_path, target, _ in mutable:
            staged[output_path] = _stage_payload(output_path, target)

        for _, output_path, _, expected_hash in mutable:
            decision = decisions[output_path]
            if decision == "replace":
                backup_path = _next_backup_path(output_path)
                backup_paths[output_path] = backup_path
                os.replace(output_path, backup_path)
            os.replace(staged[output_path], output_path)
            committed.append((output_path, decision))
            if sha256_bytes(output_path.read_bytes()) != expected_hash:
                raise UpdateError(f"생성된 ROM 검증에 실패했습니다: {output_path}")
    except Exception as exc:
        rollback_errors: list[str] = []
        committed_paths = {path for path, _ in committed}
        for output_path, decision in reversed(committed):
            try:
                if decision == "replace":
                    backup_path = backup_paths[output_path]
                    if not backup_path.is_file():
                        raise OSError(f"rollback backup is missing: {backup_path}")
                    os.replace(backup_path, output_path)
                    if (
                        sha256_bytes(output_path.read_bytes())
                        != original_hashes[output_path]
                    ):
                        raise OSError(f"rollback hash mismatch: {output_path}")
                else:
                    output_path.unlink(missing_ok=True)
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        # A replacement may fail after its original was renamed but before
        # its staged target was committed; restore that in-flight file too.
        for output_path, backup_path in backup_paths.items():
            if output_path in committed_paths or not backup_path.exists():
                continue
            try:
                os.replace(backup_path, output_path)
                if (
                    sha256_bytes(output_path.read_bytes())
                    != original_hashes[output_path]
                ):
                    raise OSError(f"rollback hash mismatch: {output_path}")
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        if rollback_errors:
            raise UpdateError(
                "결과 ROM 생성 실패 후 되돌리기도 실패했습니다: "
                + "; ".join(rollback_errors)
            ) from exc
        raise UpdateError(
            f"세 결과 ROM 생성을 취소하고 모두 되돌렸습니다: {exc}"
        ) from exc
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)

    results: list[PatchResult] = []
    for value, output_path, _, expected_hash in prepared:
        decision = decisions[output_path]
        results.append(
            PatchResult(
                target_id=str(value["id"]),
                output_path=output_path,
                status=(
                    "already_current"
                    if decision == "current"
                    else "replaced" if decision == "replace" else "created"
                ),
                sha256=expected_hash,
                backup_path=backup_paths.get(output_path),
            )
        )
    return results


def _application_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix.lower() == ".app":
                    return parent.parent
        return executable.parent
    return Path.cwd()


def run_gui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(APP_TITLE)
    root.resizable(False, False)
    root.columnconfigure(1, weight=1)

    rom_var = tk.StringVar()
    output_var = tk.StringVar(value=str(_application_dir()))
    save_var = tk.StringVar()
    save_target_var = tk.StringVar(value="hard")
    status_var = tk.StringVar(
        value="일본판 ROM 또는 ZIP을 선택한 뒤 패치 시작을 누르세요."
    )

    discovered = discover_source_rom(_application_dir())
    if discovered is not None:
        rom_var.set(str(discovered))
        output_var.set(str(discovered.parent))
        status_var.set(f"지원 원본 자동 발견: {discovered.name}")

    def choose_rom() -> None:
        value = filedialog.askopenfilename(
            title="랑그릿사 II 일본판 ROM 또는 ZIP 선택",
            filetypes=[
                ("ROM 또는 ZIP", "*.md *.bin *.gen *.smd *.zip"),
                ("모든 파일", "*.*"),
            ],
        )
        if value:
            rom_var.set(value)
            output_var.set(str(Path(value).parent))

    def choose_output() -> None:
        value = filedialog.askdirectory(title="결과 ROM 저장 폴더 선택")
        if value:
            output_var.set(value)

    def choose_save() -> None:
        value = filedialog.askopenfilename(
            title="기존 게임 내 저장 선택",
            filetypes=[("게임 내 저장", "*.srm *.sram *.sav")],
        )
        if value:
            save_var.set(value)

    def confirm_overwrite(path: Path) -> bool:
        return messagebox.askyesno(
            "기존 결과 백업 후 교체",
            f"다른 내용의 파일이 이미 있습니다.\n\n{path}\n\n"
            "기존 파일을 .bak으로 백업하고 교체할까요?",
            parent=root,
        )

    def patch_now() -> None:
        try:
            status_var.set("패치와 결과 해시를 검증하고 있습니다…")
            root.update_idletasks()
            results = apply_release(
                Path(rom_var.get()),
                output_dir=Path(output_var.get()),
                confirm_overwrite=confirm_overwrite,
            )
            save_message = ""
            if save_var.get().strip():
                selected = next(
                    result
                    for result in results
                    if result.target_id == save_target_var.get()
                )
                try:
                    save_result = migrate_save(
                        Path(save_var.get()), selected.output_path
                    )
                except UpdateError as exc:
                    if "different save already exists" not in str(exc):
                        raise
                    if not messagebox.askyesno(
                        "기존 대상 세이브 백업 후 교체",
                        "새 ROM 이름에 다른 세이브가 이미 있습니다. "
                        "그 파일을 백업하고 선택한 세이브로 교체할까요?",
                        parent=root,
                    ):
                        raise
                    save_result = migrate_save(
                        Path(save_var.get()), selected.output_path, force=True
                    )
                save_message = f"\n\n세이브 연결: {save_result.destination_path}"
            lines = [
                f"{result.output_path.name}\nSHA-256: {result.sha256}"
                for result in results
            ]
            status_var.set("완료: 세 가지 한국어판 ROM을 생성하고 검증했습니다.")
            messagebox.showinfo(
                "패치 완료",
                "\n\n".join(lines)
                + save_message
                + "\n\n상태 저장 대신 게임 안의 불러오기를 사용하세요.",
                parent=root,
            )
        except (OSError, UpdateError, StopIteration, zipfile.BadZipFile) as exc:
            status_var.set("실패: 파일과 안내된 SHA-256을 확인하세요.")
            messagebox.showerror("패치 실패", str(exc), parent=root)

    padding = {"padx": 8, "pady": 6}
    ttk.Label(root, text="일본판 ROM/ZIP").grid(row=0, column=0, sticky="w", **padding)
    ttk.Entry(root, textvariable=rom_var, width=64).grid(row=0, column=1, **padding)
    ttk.Button(root, text="찾기", command=choose_rom).grid(row=0, column=2, **padding)
    ttk.Label(root, text="결과 폴더").grid(row=1, column=0, sticky="w", **padding)
    ttk.Entry(root, textvariable=output_var, width=64).grid(row=1, column=1, **padding)
    ttk.Button(root, text="찾기", command=choose_output).grid(row=1, column=2, **padding)
    ttk.Label(root, text="기존 세이브(선택)").grid(
        row=2, column=0, sticky="w", **padding
    )
    ttk.Entry(root, textvariable=save_var, width=64).grid(row=2, column=1, **padding)
    ttk.Button(root, text="찾기", command=choose_save).grid(row=2, column=2, **padding)
    save_frame = ttk.Frame(root)
    save_frame.grid(row=3, column=1, sticky="w", **padding)
    ttk.Label(save_frame, text="세이브 연결 대상:").pack(side="left")
    ttk.Radiobutton(
        save_frame, text="원작 디자인판", variable=save_target_var, value="pure"
    ).pack(side="left", padx=8)
    ttk.Radiobutton(
        save_frame, text="하드판", variable=save_target_var, value="hard"
    ).pack(side="left", padx=8)
    ttk.Radiobutton(
        save_frame, text="최신 디자인 일반판", variable=save_target_var, value="normal"
    ).pack(side="left")
    ttk.Label(root, textvariable=status_var, wraplength=620).grid(
        row=4, column=0, columnspan=3, sticky="w", **padding
    )
    ttk.Button(root, text="패치 시작", command=patch_now).grid(
        row=5, column=0, columnspan=3, pady=(8, 14)
    )
    root.mainloop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--rom", type=Path)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help=(
            "내장 manifest와 세 BPS 파일의 크기·해시·BPS 체크섬을 검사합니다; "
            "--rom을 함께 주면 실제 적용 결과 해시까지 검사합니다"
        ),
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--save", type=Path)
    parser.add_argument(
        "--save-target", choices=("pure", "normal", "hard"), default="hard"
    )
    parser.add_argument(
        "--yes", action="store_true", help="다른 결과 ROM 교체를 허용합니다"
    )
    return parser


def configure_cli_streams() -> None:
    """Use UTF-8 for redirected Windows/PyInstaller console output.

    A frozen console executable can inherit a legacy ANSI encoding such as
    cp1252 when stdout is redirected by PowerShell or GitHub Actions.  The
    patcher intentionally prints Korean status and error messages, so leaving
    that encoding in place can make a successful self-test crash while merely
    reporting its result.  Reconfiguring is harmless for modern terminals and
    the ``getattr`` guards preserve test doubles and GUI-only launches.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            # Closed/replaced streams are outside the patcher's control.  The
            # normal print path below will retain the host's behavior.
            pass


def main(argv: list[str] | None = None) -> int:
    configure_cli_streams()
    args = build_parser().parse_args(argv)
    if args.self_test:
        try:
            source_payload = (
                read_source_rom(args.rom).payload
                if args.rom is not None
                else None
            )
            report = verify_embedded_assets(source_payload)
            for target in report["targets"]:
                assert isinstance(target, dict)
                mode = (
                    "BPS 적용·결과 해시 확인"
                    if target["application_verified"]
                    else "내장 크기·해시·BPS 체크섬 확인"
                )
                print(f"{target['id']}: {mode}")
            print(f"self-test 통과: {report['release']}")
        except (OSError, UpdateError, zipfile.BadZipFile) as exc:
            print(f"self-test 오류: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.rom is None:
        return run_gui()
    try:
        results = apply_release(
            args.rom,
            output_dir=args.output_dir,
            confirm_overwrite=(lambda _: args.yes),
        )
        for result in results:
            print(f"{result.target_id}: {result.output_path}")
            print(f"SHA-256: {result.sha256}")
        if args.save is not None:
            selected = next(
                result
                for result in results
                if result.target_id == args.save_target
            )
            save_result = migrate_save(
                args.save, selected.output_path, force=args.yes
            )
            print(f"세이브 연결: {save_result.destination_path}")
    except (OSError, UpdateError, StopIteration) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
