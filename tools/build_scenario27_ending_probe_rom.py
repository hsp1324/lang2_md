#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 27 Ending Probe).md"
)

SCENARIO_NUMBER = 27
SCENARIO_HEADER = 0x1830CC
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1830F2
ELWIN_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
ELWIN_DEPLOYMENT = bytes.fromhex("000F 0010")
BERNHARDT_RECORD_INDEX = 8
BERNHARDT_RECORD_OFFSET = 0x18323E

# The probe puts Bernhardt directly above the first automatic Elwin position.
PROBE_BERNHARDT_X = 15
PROBE_BERNHARDT_Y = 15
# Scenario stat bytes are signed modifiers applied after class base stats.
# Emperor contributes AT 12 / DF 4, so zero bytes still leave a much stronger
# target. Cancel those base values. Combat variance can still leave an AT/DF 0
# commander at one HP, so runtime verification retries from a pre-attack state.
PROBE_BERNHARDT_AT_MODIFIER = -12
PROBE_BERNHARDT_DF_MODIFIER = -4
BALANCE_RECORD_TAG_OFFSET = 0x1D


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(
    probe: bytes,
    source: bytes,
    *,
    allow_balanced_input: bool = False,
) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 27 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 27 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 27 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 27 deployment table")
    if probe[ELWIN_DEPLOYMENT_OFFSET : ELWIN_DEPLOYMENT_OFFSET + 4] != ELWIN_DEPLOYMENT:
        raise ValueError("input ROM first Elwin deployment is not (15,16)")
    if source[ELWIN_DEPLOYMENT_OFFSET : ELWIN_DEPLOYMENT_OFFSET + 4] != ELWIN_DEPLOYMENT:
        raise ValueError("Japanese source first Elwin deployment is not (15,16)")

    record_offset = (
        source_layout.records_offset + BERNHARDT_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != BERNHARDT_RECORD_OFFSET:
        raise ValueError(f"unexpected Bernhardt record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if allow_balanced_input:
        diagnostic_fields = {
            FIELD_OFFSETS["at"],
            FIELD_OFFSETS["df"],
            BALANCE_RECORD_TAG_OFFSET,
            *(
                FIELD_OFFSETS["mercenaries"] + index
                for index in range(6)
            ),
        }
        protected_differences = [
            offset
            for offset in range(FIXED_RECORD_SIZE)
            if offset not in diagnostic_fields
            and probe[record_offset + offset] != source[record_offset + offset]
        ]
        if protected_differences:
            raise ValueError(
                "input Bernhardt protected fields differ from Japanese source"
            )
    elif probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Bernhardt record differs from Japanese source")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    allow_balanced_input: bool = False,
) -> int:
    validate_layout(
        probe,
        source,
        allow_balanced_input=allow_balanced_input,
    )
    base = BERNHARDT_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["at"]] = PROBE_BERNHARDT_AT_MODIFIER & 0xFF
    probe[base + FIELD_OFFSETS["df"]] = PROBE_BERNHARDT_DF_MODIFIER & 0xFF
    probe[base + FIELD_OFFSETS["x"]] = PROBE_BERNHARDT_X
    probe[base + FIELD_OFFSETS["y"]] = PROBE_BERNHARDT_Y
    mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
    probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 27 ROM with an adjacent, unguarded "
            "Bernhardt for stock ending and epilogue playback tests"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--allow-balanced-input",
        action="store_true",
        help=(
            "allow input Bernhardt AT/DF and mercenary balance differences; "
            "the hard-mode record tag is preserved, while identity, class, "
            "level, flags, and coordinates must still match the Japanese source"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(
        probe,
        source,
        allow_balanced_input=args.allow_balanced_input,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(
        f"Scenario 27 Bernhardt: ({PROBE_BERNHARDT_X},{PROBE_BERNHARDT_Y}), "
        "AT modifier -12, DF modifier -4, no mercenaries"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
