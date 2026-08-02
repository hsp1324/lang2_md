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
    ROOT / "roms/builds/Langrisser II (Scenario 4 Clear Probe).md"
)
DEFAULT_PROGRESSION_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 Progression Probe).md"
)
DEFAULT_MASKED_KNIGHT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 Masked Knight Status Probe).md"
)
DEFAULT_PROTAGONIST_DEATH_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 protagonist Probe).md"
)
DEFAULT_LIANA_DEATH_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 liana Probe).md"
)
DEFAULT_PRIEST_ANNIHILATION_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 priest annihilation Probe).md"
)

SCENARIO_NUMBER = 4
SCENARIO_HEADER = 0x180688
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1806A0
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0007 0026")
SOURCE_PLAYER_DEPLOYMENTS = (
    (7, 38),
    (5, 40),
    (9, 40),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
PROBE_FIRST_PLAYER_X = 7
PROBE_FIRST_PLAYER_Y = 22
MORGAN_RECORD_INDEX = 7
MORGAN_RECORD_OFFSET = 0x1807AC
SOURCE_MORGAN_X = 7
SOURCE_MORGAN_Y = 21
PROBE_MORGAN_AT = 0
PROBE_MORGAN_DF = 0
MASKED_KNIGHT_RECORD_INDEX = 4
MASKED_KNIGHT_RECORD_OFFSET = 0x180740
MASKED_KNIGHT_NAME_ID = 0x0B
MASKED_KNIGHT_CLASS_ID = 0x01
MASKED_KNIGHT_X = 7
MASKED_KNIGHT_Y = 37
FIRST_ENEMY_RECORD_INDEX = 5
LAST_ENEMY_RECORD_INDEX = 10
PROGRESSION_ENEMY_AT = 0
PROGRESSION_ENEMY_DF = 0

EVENT_BLOCK_START = 0x189BA6
EVENT_BLOCK_END = 0x18C056
PROTAGONIST_DEATH_TRIGGER = 0x189C8A
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0F 02 01 00 00 18 9F 52"
)
PROTAGONIST_DEATH_HANDLER = 0x189F52
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 01 02 01 00 18 AD 96 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x18AD96
LIANA_DEATH_TRIGGER = 0x189CA2
LIANA_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "15 02 02 00 00 18 9F 92"
)
LIANA_DEATH_HANDLER = 0x189F92
LIANA_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 02 06 01 00 18 AE 56 "
    "13 FF "
    "02 01 04 01 00 18 AE 6C "
    "15 FF FF FF"
)
LIANA_DEATH_TEXTS = (0x18AE56, 0x18AE6C)
PRIEST_ANNIHILATION_TRIGGER = 0x189CDE
PRIEST_ANNIHILATION_TRIGGER_BYTES = bytes.fromhex(
    "21 04 70 71 1F 00 00 18 A0 8A"
)
PRIEST_ANNIHILATION_HANDLER = 0x18A08A
PRIEST_ANNIHILATION_HANDLER_BYTES = bytes.fromhex(
    "13 FF "
    "02 16 62 01 00 18 B1 1A "
    "0E 16 "
    "02 01 04 01 00 18 B1 94 "
    "15 FF FF FF"
)
PRIEST_ANNIHILATION_DIRECT_TEXTS = (0x18B11A, 0x18B194)
PRIEST_ANNIHILATION_PHYSICAL_TEXTS = (0x18B11A, 0x18B156, 0x18B194)
PRIEST_ANNIHILATION_CONTINUATIONS = {0x18B11A: 0x18B156}

START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
LIANA_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
PRIEST_RUNTIME_GROUPS = tuple(
    range(PLAYER_DEPLOYMENT_COUNT + 1, PLAYER_DEPLOYMENT_COUNT + 4)
)
MORGAN_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT + MORGAN_RECORD_INDEX
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def runtime_death_wrapper_code(target_groups: tuple[int, ...]) -> bytes:
    allowed = {
        (PROTAGONIST_RUNTIME_GROUP,),
        (LIANA_RUNTIME_GROUP,),
        PRIEST_RUNTIME_GROUPS,
        (MORGAN_RUNTIME_GROUP,),
    }
    if target_groups not in allowed:
        raise ValueError("unsupported Scenario 4 death target groups")
    code = bytearray()
    for group in target_groups:
        target = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (target + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((target + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((target + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def install_start_wrapper(
    probe: bytearray,
    source: bytes,
    wrapper: bytes,
    *,
    label: str,
) -> None:
    expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
    for source_label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{source_label} Start-menu entry operand changed")
    wrapper_end = RUNTIME_WRAPPER + len(wrapper)
    if probe[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError(f"input {label} wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER:wrapper_end] = wrapper


def validate_events(probe: bytes, source: bytes) -> None:
    for label, offset, expected in (
        (
            "protagonist-death trigger",
            PROTAGONIST_DEATH_TRIGGER,
            PROTAGONIST_DEATH_TRIGGER_BYTES,
        ),
        (
            "protagonist-death handler",
            PROTAGONIST_DEATH_HANDLER,
            PROTAGONIST_DEATH_HANDLER_BYTES,
        ),
        (
            "Liana-death trigger",
            LIANA_DEATH_TRIGGER,
            LIANA_DEATH_TRIGGER_BYTES,
        ),
        (
            "Liana-death handler",
            LIANA_DEATH_HANDLER,
            LIANA_DEATH_HANDLER_BYTES,
        ),
        (
            "priest-annihilation trigger",
            PRIEST_ANNIHILATION_TRIGGER,
            PRIEST_ANNIHILATION_TRIGGER_BYTES,
        ),
        (
            "priest-annihilation handler",
            PRIEST_ANNIHILATION_HANDLER,
            PRIEST_ANNIHILATION_HANDLER_BYTES,
        ),
    ):
        end = offset + len(expected)
        for source_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected:
                raise ValueError(f"{source_label} Scenario 4 {label} changed")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 4 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 4 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 4 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 4 deployment table")
    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(
        expected_deployments
    )
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end
            ]
            != expected_deployments
        ):
            raise ValueError(
                f"{label} first player deployment or deployment list changed"
            )

    record_offset = (
        source_layout.records_offset + MORGAN_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != MORGAN_RECORD_OFFSET:
        raise ValueError(f"unexpected Morgan record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Morgan record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_MORGAN_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_MORGAN_Y
    ):
        raise ValueError("unexpected Japanese Scenario 4 Morgan coordinates")

    masked_offset = (
        source_layout.records_offset
        + MASKED_KNIGHT_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if masked_offset != MASKED_KNIGHT_RECORD_OFFSET:
        raise ValueError(
            f"unexpected masked-knight record 0x{masked_offset:06X}"
        )
    masked_end = masked_offset + FIXED_RECORD_SIZE
    if probe[masked_offset:masked_end] != source[masked_offset:masked_end]:
        raise ValueError("input masked-knight record differs from Japanese source")
    if (
        source[masked_offset] != 0x80
        or source[masked_offset + FIELD_OFFSETS["x"]] != 0xFF
        or source[masked_offset + FIELD_OFFSETS["y"]] != 0xFF
        or source[masked_offset + FIELD_OFFSETS["name_id"]]
        != MASKED_KNIGHT_NAME_ID
        or source[masked_offset + FIELD_OFFSETS["class_id"]]
        != MASKED_KNIGHT_CLASS_ID
    ):
        raise ValueError("unexpected Japanese Scenario 4 masked-knight identity")
    validate_events(probe, source)


def validate_all_records(probe: bytes, source: bytes) -> None:
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(layout.record_count):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 4 fixed record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    runtime_clear: bool = False,
) -> int:
    validate_layout(probe, source)
    if runtime_clear:
        validate_all_records(probe, source)
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code((MORGAN_RUNTIME_GROUP,)),
            label="Morgan-clear",
        )
        return builder.update_md_checksum(probe)
    probe[
        FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
    ] = bytes.fromhex(
        f"{PROBE_FIRST_PLAYER_X:04X} {PROBE_FIRST_PLAYER_Y:04X}"
    )
    base = MORGAN_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["at"]] = PROBE_MORGAN_AT
    probe[base + FIELD_OFFSETS["df"]] = PROBE_MORGAN_DF
    mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
    probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def patch_progression_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 4 enemy record {index} differs from Japanese source"
            )
        probe[base + FIELD_OFFSETS["at"]] = PROGRESSION_ENEMY_AT
        probe[base + FIELD_OFFSETS["df"]] = PROGRESSION_ENEMY_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def patch_masked_knight_status_probe(
    probe: bytearray, source: bytes
) -> int:
    validate_layout(probe, source)
    base = MASKED_KNIGHT_RECORD_OFFSET
    probe[base] &= 0x7F
    probe[base + FIELD_OFFSETS["x"]] = MASKED_KNIGHT_X
    probe[base + FIELD_OFFSETS["y"]] = MASKED_KNIGHT_Y
    return builder.update_md_checksum(probe)


def patch_death_probe(
    probe: bytearray,
    source: bytes,
    *,
    liana_death: bool = False,
    priest_annihilation: bool = False,
    protagonist_death: bool = False,
) -> int:
    if sum((liana_death, priest_annihilation, protagonist_death)) != 1:
        raise ValueError("Scenario 4 death modes are mutually exclusive")
    validate_layout(probe, source)
    validate_all_records(probe, source)
    if protagonist_death:
        target_groups = (PROTAGONIST_RUNTIME_GROUP,)
        label = "protagonist-death"
    elif liana_death:
        target_groups = (LIANA_RUNTIME_GROUP,)
        label = "Liana-death"
    else:
        target_groups = PRIEST_RUNTIME_GROUPS
        label = "priest-annihilation"
    install_start_wrapper(
        probe,
        source,
        runtime_death_wrapper_code(target_groups),
        label=label,
    )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 4 ROM with Elwin adjacent to an "
            "unguarded Morgan for stock completion-dialogue tests"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument(
        "--mode",
        choices=(
            "clear",
            "progression",
            "masked-knight-status",
            "protagonist-death",
            "liana-death",
            "priest-annihilation",
        ),
        default="clear",
        help=(
            "clear moves Elwin next to Morgan; progression preserves all "
            "coordinates; masked-knight-status reveals the source hidden "
            "record above the stock Elwin deployment; death modes preserve "
            "all static records and alter only declared runtime groups"
        ),
    )
    parser.add_argument("--output-rom", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    if args.mode == "protagonist-death":
        checksum = patch_death_probe(
            probe,
            source,
            protagonist_death=True,
        )
        output_rom = args.output_rom or DEFAULT_PROTAGONIST_DEATH_OUTPUT_ROM
        print(
            "Scenario 4 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.mode == "liana-death":
        checksum = patch_death_probe(
            probe,
            source,
            liana_death=True,
        )
        output_rom = args.output_rom or DEFAULT_LIANA_DEATH_OUTPUT_ROM
        print(
            "Scenario 4 Liana-death mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            "Start marks only Liana runtime group 3 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.mode == "priest-annihilation":
        checksum = patch_death_probe(
            probe,
            source,
            priest_annihilation=True,
        )
        output_rom = (
            args.output_rom or DEFAULT_PRIEST_ANNIHILATION_OUTPUT_ROM
        )
        print(
            "Scenario 4 priest-annihilation mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only the two Shinkan and one Priest runtime groups "
            "4..6 defeated, then returns to the stock Start handler"
        )
    elif args.mode == "progression":
        checksum = patch_progression_probe(probe, source)
        output_rom = args.output_rom or DEFAULT_PROGRESSION_OUTPUT_ROM
        print(
            "Scenario 4 original coordinates preserved; enemy records "
            f"{FIRST_ENEMY_RECORD_INDEX}..{LAST_ENEMY_RECORD_INDEX}: "
            "AT 0, DF 0, no mercenaries"
        )
    elif args.mode == "masked-knight-status":
        checksum = patch_masked_knight_status_probe(probe, source)
        output_rom = args.output_rom or DEFAULT_MASKED_KNIGHT_OUTPUT_ROM
        print(
            "Scenario 4 source masked knight: hidden flag cleared; "
            f"coordinates ({MASKED_KNIGHT_X},{MASKED_KNIGHT_Y}); "
            "name, class, level, stats, side, and mercenaries preserved"
        )
    else:
        checksum = patch_probe(probe, source)
        output_rom = args.output_rom or DEFAULT_OUTPUT_ROM
        print(
            f"Scenario 4 Elwin: ({PROBE_FIRST_PLAYER_X},{PROBE_FIRST_PLAYER_Y}); "
            f"Morgan: ({SOURCE_MORGAN_X},{SOURCE_MORGAN_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    print(f"checksum: {checksum:04X}")
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
