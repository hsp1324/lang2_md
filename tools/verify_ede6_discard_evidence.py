#!/usr/bin/env python3
"""Recompute the current frozen-ROM EDE6 discard evidence contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_discard_prompt_probe_rom as discard_probe
from tools import run_blastem_sequence as sequence
from tools.v137_release_identity import (
    JAPANESE_SOURCE_ROM_SHA256,
    RELEASE_ROM_PATHS,
    RELEASE_ROM_SHA256,
)


DEFAULT_EVIDENCE = ROOT / "captures/run/ede6_discard_evidence.json"
EXPECTED_SCOPE = "current_frozen_pure_discard_prompt_diagnostic"
EXPECTED_PROBE_SHA256 = (
    "8a56f5bee65ed1431ae0627a5f363dc7e100f744887b0190e36a5b5dfb987b08"
)
EXPECTED_PROBE_CHECKSUM = "EDE6"
EXPECTED_CHANGED_BYTE_COUNT = 288
EXPECTED_CHANGED_PAYLOAD_BYTE_COUNT = 286
EXPECTED_DECLARED_RANGES = (
    (0x00018E, 0x000190),
    (0x0261F2, 0x0261F6),
    (0x0276AC, 0x0276B2),
    (0x027B32, 0x027B36),
    (0x0A1D32, 0x0A1D7C),
    (0x3F0000, 0x3F001C),
    (0x3F0020, 0x3F0052),
    (0x3F0060, 0x3F007A),
    (0x3F0080, 0x3F009A),
    (0x3F00A0, 0x3F00C6),
    (0x3F00D0, 0x3F011E),
)
EXPECTED_CAPTURE_KEYS = (
    "page_1",
    "page_9",
    "confirm_return",
    "confirm_return_after_three_seconds",
)
EXPECTED_GST_SHA256 = (
    "0ccaf35b92751f6adf4fdd1c66dc5a9b1c5762b168536afeadd74b357482033a"
)
EXPECTED_MARKERS = {
    0xAEF0: 0x1111,
    0xAEF2: 0x2222,
    0xAEF4: 0x3333,
    0xAEF6: 0x2000,
    0xAEF8: 0x4444,
    0xAEFA: 0x5555,
}


def sha256_bytes(payload: bytes | bytearray) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_project_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("evidence path must be a non-empty string")
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    return path


def report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def parse_hex(value: object) -> int:
    if not isinstance(value, str):
        raise ValueError("hex value must be a string")
    return int(value, 16)


def build_report(evidence_path: Path = DEFAULT_EVIDENCE) -> dict[str, object]:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def verify(name: str, operation) -> None:
        try:
            result = operation()
            checks[name] = bool(result)
            if not result:
                errors.append(name)
        except Exception as exc:  # Fail closed while retaining every result.
            checks[name] = False
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "fail",
            "evidence": str(evidence_path),
            "checks": {"evidence_json_loaded": False},
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    checks["evidence_json_loaded"] = True

    release = evidence.get("release_rom", {})
    reference = evidence.get("japanese_reference_rom", {})
    diagnostic = evidence.get("diagnostic_probe", {})
    runtime = evidence.get("runtime", {})
    capture_rows = evidence.get("captures", {})
    gst_row = evidence.get("post_return_gst", {})
    claims = evidence.get("claims", {})

    pure_rom = RELEASE_ROM_PATHS["pure"]
    reference_rom = ROOT / "roms/original/Langrisser II (Japan).md"
    release_bytes = pure_rom.read_bytes()
    reference_bytes = reference_rom.read_bytes()
    release_hash = sha256_bytes(release_bytes)
    reference_hash = sha256_bytes(reference_bytes)

    verify(
        "scope_and_status_locked",
        lambda: evidence.get("schema_version") == 1
        and evidence.get("status") == "pass"
        and evidence.get("scope") == EXPECTED_SCOPE,
    )
    verify(
        "release_path_and_hash_are_central_frozen_pure",
        lambda: resolve_project_path(release.get("path")) == pure_rom.resolve()
        and release_hash == RELEASE_ROM_SHA256["pure"]
        and release.get("sha256") == release_hash
        and release.get("bytes") == len(release_bytes)
        and release.get("md_checksum")
        == release_bytes[0x18E:0x190].hex().upper(),
    )
    verify(
        "japanese_reference_hash_is_locked",
        lambda: resolve_project_path(reference.get("path"))
        == reference_rom.resolve()
        and reference_hash == JAPANESE_SOURCE_ROM_SHA256
        and reference.get("sha256") == reference_hash,
    )

    rebuilt_probe = bytearray(release_bytes)
    rebuilt_checksum = discard_probe.patch_probe(rebuilt_probe, reference_bytes)
    changed_offsets = tuple(
        offset
        for offset, (before, after) in enumerate(
            zip(release_bytes, rebuilt_probe, strict=True)
        )
        if before != after
    )
    payload_offsets = tuple(
        offset for offset in changed_offsets if offset not in (0x18E, 0x18F)
    )
    declared_ranges = tuple(
        (parse_hex(row.get("start")), parse_hex(row.get("end_exclusive")))
        for row in diagnostic.get("declared_mutation_scope", [])
    )
    declared_offsets = {
        offset
        for start, end in declared_ranges
        for offset in range(start, end)
    }
    verify(
        "diagnostic_builder_and_identity_locked",
        lambda: diagnostic.get("builder")
        == "tools/build_discard_prompt_probe_rom.py"
        and sha256_bytes(rebuilt_probe) == EXPECTED_PROBE_SHA256
        and diagnostic.get("sha256") == EXPECTED_PROBE_SHA256
        and f"{rebuilt_checksum:04X}" == EXPECTED_PROBE_CHECKSUM
        and diagnostic.get("md_checksum") == EXPECTED_PROBE_CHECKSUM
        and diagnostic.get("bytes") == len(rebuilt_probe)
        and diagnostic.get("release_promoted") is False,
    )
    verify(
        "declared_mutation_ranges_are_exact",
        lambda: declared_ranges == EXPECTED_DECLARED_RANGES,
    )
    verify(
        "exact_changed_byte_set_is_inside_declared_ranges",
        lambda: set(changed_offsets) <= declared_offsets
        and len(changed_offsets) == EXPECTED_CHANGED_BYTE_COUNT
        and len(payload_offsets) == EXPECTED_CHANGED_PAYLOAD_BYTE_COUNT
        and diagnostic.get("changed_byte_count_including_checksum")
        == len(changed_offsets)
        and diagnostic.get("changed_payload_byte_count")
        == len(payload_offsets),
    )

    capture_payloads: dict[str, bytes] = {}
    capture_hashes: dict[str, str] = {}

    def verify_capture_set() -> bool:
        if tuple(capture_rows) != EXPECTED_CAPTURE_KEYS:
            return False
        for key in EXPECTED_CAPTURE_KEYS:
            row = capture_rows[key]
            path = resolve_project_path(row.get("path"))
            payload = path.read_bytes()
            digest = sha256_bytes(payload)
            if row.get("sha256") != digest:
                return False
            with Image.open(path) as image:
                if image.size != (320, 240) or image.format != "PNG":
                    return False
            capture_payloads[key] = payload
            capture_hashes[key] = digest
        return True

    verify("all_four_png_paths_hashes_and_dimensions_match", verify_capture_set)
    verify(
        "page_1_and_page_9_are_distinct",
        lambda: capture_payloads.get("page_1")
        != capture_payloads.get("page_9")
        and capture_hashes.get("page_1") != capture_hashes.get("page_9"),
    )
    verify(
        "confirm_return_frames_are_pixel_exact",
        lambda: capture_payloads.get("confirm_return")
        == capture_payloads.get("confirm_return_after_three_seconds")
        and capture_hashes.get("confirm_return")
        == capture_hashes.get("confirm_return_after_three_seconds")
        and capture_rows.get("confirm_return_after_three_seconds", {}).get(
            "pixel_exact_with_initial_return"
        )
        is True,
    )

    gst_path = resolve_project_path(gst_row.get("path"))
    gst = gst_path.read_bytes()
    ram = gst[
        sequence.GST_WORK_RAM_FILE_OFFSET:
        sequence.GST_WORK_RAM_FILE_OFFSET + 0x10000
    ]
    verify(
        "post_return_gst_path_hash_and_size_match",
        lambda: len(gst) == gst_row.get("bytes") == 140408
        and sha256_bytes(gst) == gst_row.get("sha256") == EXPECTED_GST_SHA256
        and len(ram) == 0x10000,
    )
    verify(
        "gst_inventory_is_exactly_40_unequipped_daggers",
        lambda: ram[0xC7F2:0xC842] == bytes((0x01, 0xFF)) * 40
        and gst_row.get("inventory", {}).get("occupied_slot_count") == 40,
    )
    verify(
        "gst_callback_stack_and_input_latch_are_stable",
        lambda: int.from_bytes(ram[0x8004:0x8008], "big") == 0x000249F8
        and int.from_bytes(ram[0x8000:0x8004], "big") == 0xFFFF80FC
        and ram[0x8179] == 0,
    )
    verify(
        "gst_diagnostic_markers_are_complete",
        lambda: all(
            int.from_bytes(ram[address:address + 2], "big") == expected
            for address, expected in EXPECTED_MARKERS.items()
        ),
    )
    verify(
        "gst_stock_pop_snapshot_is_exact",
        lambda: int.from_bytes(ram[0xAEE0:0xAEE4], "big") == 0x00017D38
        and int.from_bytes(ram[0xAEE4:0xAEE8], "big") == 0xFFFF80FC,
    )
    verify(
        "runtime_is_fresh_isolated_xvfb_capture",
        lambda: runtime.get("virtual_display") == ":951"
        and runtime.get("software_renderer") is True
        and runtime.get("direct_x11_input_and_capture") is True
        and runtime.get("seed_policy")
        == "fresh isolated runtime; no historical GST or SRAM was loaded",
    )
    verify(
        "claims_are_diagnostic_and_fail_closed",
        lambda: all(
            claims.get(key) is True
            for key in (
                "heading_page_cursor_and_arrows_visible",
                "page_1_to_page_9_traversal",
                "confirmation_returned_to_stock_idle_shop",
                "return_frame_stable_for_three_seconds",
                "inventory_has_40_occupied_slots_after_confirmation",
            )
        )
        and claims.get("natural_event_award_ownership") is False
        and claims.get("classification")
        == "current exact-ROM renderer/capacity diagnostic",
    )

    return {
        "schema_version": 1,
        "status": "pass" if all(checks.values()) else "fail",
        "scope": EXPECTED_SCOPE,
        "evidence": report_path(evidence_path),
        "release_sha256": release_hash,
        "rebuilt_probe_sha256": sha256_bytes(rebuilt_probe),
        "changed_byte_count": len(changed_offsets),
        "changed_payload_byte_count": len(payload_offsets),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "checks": checks,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    report = build_report(args.evidence.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
