#!/usr/bin/env python3
"""Build the source-triggered Scenario 22 hidden-Bernhardt diagnostic.

The derivative changes only Elwin's Scenario 22 deployment so one ordinary
move crosses into the stock F1 rectangle.  The hidden Bernhardt fixed record,
the event table, and both phases of the stock reveal chain remain
byte-identical to the input release ROM.  Scenario 25 needs no derivative:
its hidden Dragon Lord is placed by the stock opening event itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder  # noqa: E402
from tools.scenario_data import (  # noqa: E402
    FIELD_OFFSETS,
    FIXED_RECORD_SIZE,
    scenario_layout,
)


DEFAULT_INPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Original v1.3.7).md"
)
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = ROOT / "tmp/v137-s22-hidden-bernhardt-spawn-probe.md"

SCENARIO_NUMBER = 22
SCENARIO_HEADER = 0x182770
DEPLOYMENT_TABLE_POINTER_OFFSET = SCENARIO_HEADER + 0x08
DEPLOYMENT_TABLE = 0x182792
FIRST_PLAYER_DEPLOYMENT = DEPLOYMENT_TABLE + 0x02
SOURCE_ELWIN_DEPLOYMENT = bytes.fromhex("00 05 00 27")
PROBE_ELWIN_DEPLOYMENT = bytes.fromhex("00 06 00 11")  # (6,17)

BERNHARDT_RECORD_INDEX = 3
BERNHARDT_NAME_ID = 0x0E
BERNHARDT_CLASS_ID = 0x4E
BERNHARDT_SIDE_ID = 0x04
BERNHARDT_SOURCE_COORDINATE = (0xFF, 0xFF)
BERNHARDT_REVEAL_COORDINATE = (5, 15)

SPATIAL_TRIGGER = 0x1AAA22
SPATIAL_TRIGGER_BYTES = bytes.fromhex(
    "0F F1 00 00 07 0F 1B 18 00 1A AC 44"
)
SPATIAL_TRIGGER_BOUNDS = (7, 15, 27, 24)
SPATIAL_HANDLER_ENTRY = 0x1AAC44
SPATIAL_HANDLER_ENTRY_BYTES = bytes.fromhex(
    "02 01 03 01 00 1A BC 1A 17 FF 00 1A AE 78"
)
SPATIAL_PHASE_HANDLER_ENTRY = 0x1AAE78
SPATIAL_PHASE_HANDLER_PREFIX_BYTES = bytes.fromhex(
    "02 10 5D 01 00 1A C3 34 23 05 23 00 "
    "02 0A 19 01 00 1A C3 50"
)
REVEAL_TRIGGER = 0x1AAA50
REVEAL_TRIGGER_BYTES = bytes.fromhex(
    "01 04 00 00 00 1A AB 20"
)
REVEAL_DISPATCH_ENTRY = 0x1AAB20
REVEAL_DISPATCH_ENTRY_BYTES = bytes.fromhex(
    "04 14 00 1A AB 2C 17 FF 00 1A AE AE"
)
REVEAL_HANDLER_ENTRY = 0x1AAEAE
REVEAL_HANDLER_PREFIX_BYTES = bytes.fromhex(
    "02 14 4D 01 00 1A C4 34 "
    "0C 04 0D FF "
    "0D 0E 05 0F "
    "02 0E 4A 01 00 1A C4 CA"
)
REVEAL_COMMAND = 0x1AAEBA
REVEAL_COMMAND_BYTES = bytes.fromhex("0D 0E 05 0F")

# Scenario 25's equivalent stock opening-event contract is source-locked here
# so the runtime runner can prove it did not substitute a synthetic spawn.
SCENARIO25_OPENING_EVENT_POINTER = 0x1B03EA
SCENARIO25_OPENING_EVENT = 0x1B053A
SCENARIO25_OPENING_EVENT_POINTER_BYTES = SCENARIO25_OPENING_EVENT.to_bytes(
    4, "big"
)
SCENARIO25_REVEAL_CONTEXT = 0x1B05B4
SCENARIO25_REVEAL_CONTEXT_BYTES = bytes.fromhex(
    "02 0D 50 01 00 1B 0C A6 "
    "0D 31 10 0B "
    "02 31 A1 01 00 1B 0D 12"
)
SCENARIO25_REVEAL_COMMAND = 0x1B05BC
SCENARIO25_REVEAL_COMMAND_BYTES = bytes.fromhex("0D 31 10 0B")


def sha256_bytes(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def _require_span(
    label: str,
    data: bytes | bytearray,
    offset: int,
    expected: bytes,
) -> None:
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise ValueError(
            f"{label} changed at 0x{offset:06X}: "
            f"expected {expected.hex(' ')}, got {actual.hex(' ')}"
        )


def _validate_target_record(
    label: str,
    data: bytes | bytearray,
    scenario: int,
    record_index: int,
    *,
    name_id: int,
    class_id: int,
    side_id: int,
) -> bytes:
    layout = scenario_layout(data, scenario)
    base = layout.records_offset + record_index * FIXED_RECORD_SIZE
    record = bytes(data[base : base + FIXED_RECORD_SIZE])
    expected_fields = {
        "hidden": bool(record[0] & 0x80),
        "side_id": record[0x08],
        "x": record[FIELD_OFFSETS["x"]],
        "y": record[FIELD_OFFSETS["y"]],
        "name_id": record[FIELD_OFFSETS["name_id"]],
        "class_id": record[FIELD_OFFSETS["class_id"]],
    }
    if expected_fields != {
        "hidden": True,
        "side_id": side_id,
        "x": 0xFF,
        "y": 0xFF,
        "name_id": name_id,
        "class_id": class_id,
    }:
        raise ValueError(
            f"{label} Scenario {scenario} hidden target identity changed: "
            f"{expected_fields}"
        )
    return record


def validate_stock_contract(
    candidate: bytes | bytearray,
    source: bytes,
) -> dict[str, object]:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    input_layout = scenario_layout(candidate, SCENARIO_NUMBER)
    if source_layout != input_layout:
        raise ValueError("Scenario 22 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 22 header 0x{source_layout.header_offset:06X}"
        )
    if be32(source, DEPLOYMENT_TABLE_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 22 deployment table")
    if be32(candidate, DEPLOYMENT_TABLE_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("input Scenario 22 deployment table changed")
    for label, data in (("Japanese", source), ("input", candidate)):
        _require_span(
            f"{label} Scenario 22 Elwin deployment",
            data,
            FIRST_PLAYER_DEPLOYMENT,
            SOURCE_ELWIN_DEPLOYMENT,
        )
        _require_span(
            f"{label} Scenario 22 F1 spatial trigger",
            data,
            SPATIAL_TRIGGER,
            SPATIAL_TRIGGER_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 spatial handler entry",
            data,
            SPATIAL_HANDLER_ENTRY,
            SPATIAL_HANDLER_ENTRY_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 F1 phase handler prefix",
            data,
            SPATIAL_PHASE_HANDLER_ENTRY,
            SPATIAL_PHASE_HANDLER_PREFIX_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 reveal trigger",
            data,
            REVEAL_TRIGGER,
            REVEAL_TRIGGER_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 reveal dispatch entry",
            data,
            REVEAL_DISPATCH_ENTRY,
            REVEAL_DISPATCH_ENTRY_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 Bernhardt reveal command",
            data,
            REVEAL_COMMAND,
            REVEAL_COMMAND_BYTES,
        )
        _require_span(
            f"{label} Scenario 22 reveal handler prefix",
            data,
            REVEAL_HANDLER_ENTRY,
            REVEAL_HANDLER_PREFIX_BYTES,
        )
        _require_span(
            f"{label} Scenario 25 opening-event pointer",
            data,
            SCENARIO25_OPENING_EVENT_POINTER,
            SCENARIO25_OPENING_EVENT_POINTER_BYTES,
        )
        _require_span(
            f"{label} Scenario 25 Dragon Lord reveal context",
            data,
            SCENARIO25_REVEAL_CONTEXT,
            SCENARIO25_REVEAL_CONTEXT_BYTES,
        )

    source_target = _validate_target_record(
        "Japanese",
        source,
        SCENARIO_NUMBER,
        BERNHARDT_RECORD_INDEX,
        name_id=BERNHARDT_NAME_ID,
        class_id=BERNHARDT_CLASS_ID,
        side_id=BERNHARDT_SIDE_ID,
    )
    input_target = _validate_target_record(
        "input",
        candidate,
        SCENARIO_NUMBER,
        BERNHARDT_RECORD_INDEX,
        name_id=BERNHARDT_NAME_ID,
        class_id=BERNHARDT_CLASS_ID,
        side_id=BERNHARDT_SIDE_ID,
    )
    protected_offsets = (0x00, 0x08, 0x18, 0x19, 0x1A, 0x1B)
    if any(input_target[offset] != source_target[offset] for offset in protected_offsets):
        raise ValueError("input Scenario 22 Bernhardt structural fields differ")
    return {
        "scenario": SCENARIO_NUMBER,
        "event_id": 0x0F,
        "condition_opcode": "0xF1",
        "trigger_offset": f"0x{SPATIAL_TRIGGER:06X}",
        "trigger_bytes": SPATIAL_TRIGGER_BYTES.hex(" ").upper(),
        "bounds": {
            "x_min": SPATIAL_TRIGGER_BOUNDS[0],
            "y_min": SPATIAL_TRIGGER_BOUNDS[1],
            "x_max": SPATIAL_TRIGGER_BOUNDS[2],
            "y_max": SPATIAL_TRIGGER_BOUNDS[3],
        },
        "handler_entry": f"0x{SPATIAL_HANDLER_ENTRY:06X}",
        "spatial_phase_handler_entry": (
            f"0x{SPATIAL_PHASE_HANDLER_ENTRY:06X}"
        ),
        "spatial_phase_boundary": (
            "the F1 phase returns map control before the subsequent stock "
            "reveal event; runtime proof must use ordinary End Turn"
        ),
        "reveal_trigger_offset": f"0x{REVEAL_TRIGGER:06X}",
        "reveal_dispatch_entry": f"0x{REVEAL_DISPATCH_ENTRY:06X}",
        "reveal_handler_entry": f"0x{REVEAL_HANDLER_ENTRY:06X}",
        "reveal_command_offset": f"0x{REVEAL_COMMAND:06X}",
        "reveal_command": "0D 0E 05 0F",
        "target_fixed_record_index": BERNHARDT_RECORD_INDEX,
        "target_name_id": BERNHARDT_NAME_ID,
        "target_class_id": BERNHARDT_CLASS_ID,
        "target_side_id": BERNHARDT_SIDE_ID,
        "target_source_coordinate": list(BERNHARDT_SOURCE_COORDINATE),
        "target_reveal_coordinate": list(BERNHARDT_REVEAL_COORDINATE),
    }


def build_probe(candidate: bytes, source: bytes) -> tuple[bytes, dict[str, object]]:
    contract = validate_stock_contract(candidate, source)
    probe = bytearray(candidate)
    before_target = _validate_target_record(
        "input",
        probe,
        SCENARIO_NUMBER,
        BERNHARDT_RECORD_INDEX,
        name_id=BERNHARDT_NAME_ID,
        class_id=BERNHARDT_CLASS_ID,
        side_id=BERNHARDT_SIDE_ID,
    )
    probe[
        FIRST_PLAYER_DEPLOYMENT : FIRST_PLAYER_DEPLOYMENT + 4
    ] = PROBE_ELWIN_DEPLOYMENT
    checksum = builder.update_md_checksum(probe)
    after_target = _validate_target_record(
        "output",
        probe,
        SCENARIO_NUMBER,
        BERNHARDT_RECORD_INDEX,
        name_id=BERNHARDT_NAME_ID,
        class_id=BERNHARDT_CLASS_ID,
        side_id=BERNHARDT_SIDE_ID,
    )
    if after_target != before_target:
        raise AssertionError("probe changed the hidden Bernhardt fixed record")
    for offset, expected in (
        (SPATIAL_TRIGGER, SPATIAL_TRIGGER_BYTES),
        (SPATIAL_HANDLER_ENTRY, SPATIAL_HANDLER_ENTRY_BYTES),
        (SPATIAL_PHASE_HANDLER_ENTRY, SPATIAL_PHASE_HANDLER_PREFIX_BYTES),
        (REVEAL_TRIGGER, REVEAL_TRIGGER_BYTES),
        (REVEAL_DISPATCH_ENTRY, REVEAL_DISPATCH_ENTRY_BYTES),
        (REVEAL_HANDLER_ENTRY, REVEAL_HANDLER_PREFIX_BYTES),
        (REVEAL_COMMAND, REVEAL_COMMAND_BYTES),
    ):
        _require_span("output stock reveal contract", probe, offset, expected)
    changed_offsets = [
        index
        for index, (before, after) in enumerate(zip(candidate, probe))
        if before != after
    ]
    allowed = set(range(FIRST_PLAYER_DEPLOYMENT, FIRST_PLAYER_DEPLOYMENT + 4))
    allowed.update(range(0x18E, 0x190))
    if not set(changed_offsets) <= allowed:
        unexpected = sorted(set(changed_offsets) - allowed)
        raise AssertionError(f"probe changed unexpected offsets: {unexpected}")
    manifest = {
        "schema_version": 1,
        "kind": "scenario22_stock_spatial_hidden_spawn_probe",
        "input_sha256": sha256_bytes(candidate),
        "source_sha256": sha256_bytes(source),
        "output_sha256": sha256_bytes(probe),
        "output_md_checksum": f"{checksum:04X}",
        "source_contract": contract,
        "diagnostic_change": {
            "offset": f"0x{FIRST_PLAYER_DEPLOYMENT:06X}",
            "before": SOURCE_ELWIN_DEPLOYMENT.hex(" ").upper(),
            "after": PROBE_ELWIN_DEPLOYMENT.hex(" ").upper(),
            "description": "Elwin deployment (5,39) -> (6,17)",
            "inside_stock_trigger_bounds": False,
        },
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "allowed_changed_ranges": [
            {
                "start": f"0x{FIRST_PLAYER_DEPLOYMENT:06X}",
                "end": f"0x{FIRST_PLAYER_DEPLOYMENT + 4:06X}",
                "owner": "Scenario 22 first player deployment",
            },
            {
                "start": "0x00018E",
                "end": "0x000190",
                "owner": "Mega Drive checksum",
            },
        ],
        "target_fixed_record_unchanged": True,
        "stock_trigger_and_handlers_unchanged": True,
        "product_rom_modified": False,
    }
    return bytes(probe), manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = args.input_rom.read_bytes()
    source = args.source_rom.read_bytes()
    probe, manifest = build_probe(candidate, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    manifest_path = args.manifest or args.output_rom.with_suffix(
        args.output_rom.suffix + ".json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output_rom)
    print(manifest_path)
    print(manifest["output_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
