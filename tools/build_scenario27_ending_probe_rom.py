#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
from tools.v137_release_identity import (  # noqa: E402
    JAPANESE_SOURCE_ROM_BYTES,
    JAPANESE_SOURCE_ROM_SHA256,
)


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 27 Ending Probe).md"
)

SCENARIO_NUMBER = 27
SCENARIO_HEADER = 0x1830CC
PLAYER_NAME_TABLE = 0x1830DC
PLAYER_DEPLOYMENT_COUNT = 10
PLAYER_NAME_POINTER_OFFSET = 0x04
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
# target. Cancel those base values. The explicit diagnostic Start-menu round
# trip stages the remaining runtime HP below before the ordinary attack.
PROBE_BERNHARDT_AT_MODIFIER = -12
PROBE_BERNHARDT_DF_MODIFIER = -4
BALANCE_RECORD_TAG_OFFSET = 0x1D

# Even with displayed AT/DF reduced to zero, stock combat can leave the
# Original-profile Bernhardt at HP1 (the retained -03 run did so on every
# replay). This diagnostic-only Start wrapper therefore changes exactly the
# staged Bernhardt root's runtime HP to one when the harness explicitly opens
# the global Start menu, before it returns to the ordinary unit command menu.
# Selection, combat, death, ending, and epilogue handlers remain stock. No
# production release ROM uses this builder.
PROBE_BERNHARDT_HP = 1
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_HP_OFFSET = 0x03
BERNHARDT_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT + BERNHARDT_RECORD_INDEX
BERNHARDT_RUNTIME_HP_ADDRESS = (
    RUNTIME_GROUP_BASE
    + BERNHARDT_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    + RUNTIME_HP_OFFSET
)
EXPECTED_PROBE_CHANGED_BYTE_COUNT = 31
EXPECTED_PROBE_PAYLOAD_CHANGED_BYTE_COUNT = 29


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def require_canonical_source(source: bytes) -> None:
    """Fail closed unless the exact supported Japanese ROM is supplied."""
    if len(source) != JAPANESE_SOURCE_ROM_BYTES:
        raise ValueError(
            "Japanese source ROM length changed: "
            f"{len(source)} != {JAPANESE_SOURCE_ROM_BYTES}"
        )
    digest = hashlib.sha256(source).hexdigest()
    if digest != JAPANESE_SOURCE_ROM_SHA256:
        raise ValueError(
            "Japanese source ROM SHA-256 changed: "
            f"{digest} != {JAPANESE_SOURCE_ROM_SHA256}"
        )


def completion_hp_wrapper_code() -> bytes:
    """Set only staged Bernhardt's runtime HP to one, then run stock Start."""
    code = bytearray(bytes.fromhex("13 FC 00"))
    code.extend(PROBE_BERNHARDT_HP.to_bytes(1, "big"))
    code.extend(BERNHARDT_RUNTIME_HP_ADDRESS.to_bytes(4, "big"))
    # Recreate the displaced LEA and then jump to the untouched Start entry.
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def install_start_wrapper(
    probe: bytearray,
    source: bytes,
    wrapper: bytes,
) -> None:
    expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{label} Start-menu entry operand changed")
    wrapper_end = RUNTIME_WRAPPER + len(wrapper)
    if wrapper_end > len(probe):
        raise ValueError("input ROM is too short for the diagnostic wrapper")
    if probe[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER:wrapper_end] = wrapper


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
    if be32(source, SCENARIO_HEADER + PLAYER_NAME_POINTER_OFFSET) != PLAYER_NAME_TABLE:
        raise ValueError("unexpected Japanese Scenario 27 player-name table")
    if int.from_bytes(source[PLAYER_NAME_TABLE : PLAYER_NAME_TABLE + 2], "big") != (
        PLAYER_DEPLOYMENT_COUNT
    ):
        raise ValueError("unexpected Japanese Scenario 27 player count")
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
    balance_fields = {
        FIELD_OFFSETS["at"],
        FIELD_OFFSETS["df"],
        BALANCE_RECORD_TAG_OFFSET,
        *(
            FIELD_OFFSETS["mercenaries"] + index
            for index in range(6)
        ),
    }
    for index in range(source_layout.record_count):
        fixed = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = fixed + FIXED_RECORD_SIZE
        if allow_balanced_input:
            protected_differences = [
                relative
                for relative in range(FIXED_RECORD_SIZE)
                if relative not in balance_fields
                and probe[fixed + relative] != source[fixed + relative]
            ]
            if protected_differences:
                label = (
                    "Bernhardt protected fields"
                    if index == BERNHARDT_RECORD_INDEX
                    else f"Scenario 27 fixed record {index} protected fields"
                )
                raise ValueError(
                    f"input {label} differ from Japanese source"
                )
        elif probe[fixed:end] != source[fixed:end]:
            label = (
                "Bernhardt record"
                if index == BERNHARDT_RECORD_INDEX
                else f"Scenario 27 fixed record {index}"
            )
            raise ValueError(f"input {label} differs from Japanese source")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    allow_balanced_input: bool = False,
) -> int:
    require_canonical_source(source)
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
    install_start_wrapper(
        probe,
        source,
        completion_hp_wrapper_code(),
    )
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
        "AT modifier -12, DF modifier -4, runtime HP 1, no mercenaries"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
