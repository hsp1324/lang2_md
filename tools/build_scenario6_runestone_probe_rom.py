#!/usr/bin/env python3
"""Build a minimal Scenario 6 Rune Stone live-play probe.

The current release expands the hidden-item trigger from the occupied well
cell (5,4) through the reachable right approach at (7,4). This diagnostic
changes only Elwin's Scenario 6 deployment to (6,4), allowing one ordinary
rightward move to exercise the production trigger in BlastEm without altering
any event or NPC record. Generated probes belong under ``tmp`` and are not
release artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.rom_update import bps_apply
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT = (
    ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.6).md"
)
DEFAULT_SOURCE = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_PATCH = ROOT / "patches/normal-v1.3.6.bps"
DEFAULT_OUTPUT = ROOT / "tmp/scenario6-runestone-v1.3.6-probe.md"
NORMAL_V136_SHA256 = (
    "b74359800a697eea5e85d7942ac712b74360bbd8b43ff2082b88d009e94a370a"
)
SCENARIO_NUMBER = 6
DEPLOYMENT_POINTER_OFFSET = 0x08
FIRST_PLAYER_DEPLOYMENT = 0x1809D2
SOURCE_FIRST_PLAYER_COORDINATE = bytes.fromhex("00 04 00 1A")
PROBE_FIRST_PLAYER_COORDINATE = bytes.fromhex("00 06 00 04")
RUNESTONE_HANDLER = 0x18D8D8
RUNESTONE_HANDLER_BYTES = bytes.fromhex(
    "0A020018D8EE13FF0200FF000018E1C8031A0B0002FFFFFF"
)
SOURCE_LOCKED_NPC_RECORDS = range(4)


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def load_normal_release(
    input_path: Path,
    patch_path: Path,
    source_rom: bytes,
) -> tuple[bytes, str]:
    """Load the versioned build, or reproduce it from the tracked v1.3.6 BPS."""

    if input_path.is_file():
        data = input_path.read_bytes()
        origin = str(input_path)
    else:
        data = bps_apply(patch_path.read_bytes(), source_rom)
        origin = f"{patch_path} applied to the Japanese source"
    digest = hashlib.sha256(data).hexdigest()
    if digest != NORMAL_V136_SHA256:
        raise ValueError(
            "Normal v1.3.6 ROM identity changed: "
            f"{digest} != {NORMAL_V136_SHA256}"
        )
    return data, origin


def load_hash_locked_candidate(
    input_path: Path,
    expected_sha256: str,
) -> tuple[bytes, str]:
    if not input_path.is_file():
        raise FileNotFoundError(f"candidate ROM does not exist: {input_path}")
    if len(expected_sha256) != 64 or any(
        char not in "0123456789abcdefABCDEF" for char in expected_sha256
    ):
        raise ValueError("expected candidate SHA-256 must contain 64 hex digits")
    data = input_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256.lower():
        raise ValueError(
            f"candidate ROM identity changed: {digest} != "
            f"{expected_sha256.lower()}"
        )
    return data, str(input_path)


def build_probe(input_rom: bytes, source_rom: bytes) -> bytearray:
    source_layout = scenario_layout(source_rom, SCENARIO_NUMBER)
    input_layout = scenario_layout(input_rom, SCENARIO_NUMBER)
    if source_layout != input_layout:
        raise ValueError("Scenario 6 layout differs from Japanese source")
    deployment_table = be32(
        source_rom,
        source_layout.header_offset + DEPLOYMENT_POINTER_OFFSET,
    )
    if deployment_table + 2 != FIRST_PLAYER_DEPLOYMENT:
        raise ValueError(
            "unexpected Scenario 6 deployment table "
            f"0x{deployment_table:06X}"
        )
    end = FIRST_PLAYER_DEPLOYMENT + len(SOURCE_FIRST_PLAYER_COORDINATE)
    for label, data in (
        ("Japanese source", source_rom),
        ("production input", input_rom),
    ):
        if data[FIRST_PLAYER_DEPLOYMENT:end] != SOURCE_FIRST_PLAYER_COORDINATE:
            raise ValueError(f"{label} Scenario 6 Elwin deployment changed")
    trigger = builder.SCENARIO6_RUNESTONE_TRIGGER
    trigger_end = trigger + len(
        builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
    )
    if (
        source_rom[trigger:trigger_end]
        != builder.SCENARIO6_RUNESTONE_TRIGGER_SOURCE
    ):
        raise ValueError("Japanese Scenario 6 Rune Stone trigger changed")
    if (
        input_rom[trigger:trigger_end]
        != builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
    ):
        raise ValueError("input ROM does not contain the current Rune Stone trigger")
    handler_end = RUNESTONE_HANDLER + len(RUNESTONE_HANDLER_BYTES)
    for label, data in (
        ("Japanese source", source_rom),
        ("production input", input_rom),
    ):
        if data[RUNESTONE_HANDLER:handler_end] != RUNESTONE_HANDLER_BYTES:
            raise ValueError(f"{label} Scenario 6 Rune Stone handler changed")
    for index in SOURCE_LOCKED_NPC_RECORDS:
        source_record = (
            source_layout.records_offset
            + index * FIXED_RECORD_SIZE
        )
        input_record = (
            input_layout.records_offset
            + index * FIXED_RECORD_SIZE
        )
        if (
            input_rom[input_record : input_record + FIXED_RECORD_SIZE]
            != source_rom[source_record : source_record + FIXED_RECORD_SIZE]
        ):
            raise ValueError(
                f"production input Scenario 6 NPC record {index} changed"
            )

    probe = bytearray(input_rom)
    probe[FIRST_PLAYER_DEPLOYMENT:end] = PROBE_FIRST_PLAYER_COORDINATE
    builder.update_md_checksum(probe)
    return probe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--patch",
        type=Path,
        default=DEFAULT_PATCH,
        help="Normal v1.3.6 BPS fallback when --input is absent",
    )
    parser.add_argument(
        "--expected-input-sha256",
        help=(
            "hash-lock an explicit current candidate instead of requiring "
            "the default Normal v1.3.6 identity"
        ),
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.source.read_bytes()
    if args.expected_input_sha256:
        input_rom, input_origin = load_hash_locked_candidate(
            args.input,
            args.expected_input_sha256,
        )
    else:
        input_rom, input_origin = load_normal_release(
            args.input,
            args.patch,
            source,
        )
    probe = build_probe(input_rom, source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(probe)
    print(f"input: {input_origin}")
    print(f"wrote {args.out}")
    print("only Scenario 6 Elwin deployment changed: (4,26) -> (6,4)")
    print(f"checksum: {int.from_bytes(probe[0x18E:0x190], 'big'):04X}")


if __name__ == "__main__":
    main()
