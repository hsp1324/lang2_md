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
    ROOT / "roms/builds/Langrisser II (Scenario 18 Clear Probe).md"
)

SCENARIO_NUMBER = 18
SCENARIO_HEADER = 0x182070
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x182092
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (9, 12),
    (14, 12),
    (3, 20),
    (3, 23),
    (26, 25),
    (8, 31),
    (22, 30),
    (30, 31),
)
COMPLETION_ELWIN_POSITION = (35, 5)
DARK_PRINCESS_ELWIN_POSITION = (37, 3)
RESIDENT_PROBE_ELWIN_POSITION = SOURCE_PLAYER_DEPLOYMENTS[0]
GREAT_DRAGON_POSITION = (35, 4)
DARK_PRINCESS_POSITION = (37, 2)
FIRST_RESIDENT_RECORD_INDEX = 0
LAST_RESIDENT_RECORD_INDEX = 1
FIRST_ENEMY_RECORD_INDEX = 2
LAST_ENEMY_RECORD_INDEX = 10
GREAT_DRAGON_RECORD_INDEX = 5
LANA_RECORD_INDEX = 6
PROTAGONIST_DEATH_TRIGGER = 0x1A4268
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "06 02 01 00 00 1A 45 BE"
)
FIRST_RESIDENT_DEATH_TRIGGER = 0x1A42A8
FIRST_RESIDENT_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "10 02 20 00 00 1A 46 36"
)
SECOND_RESIDENT_DEATH_TRIGGER = 0x1A42B0
SECOND_RESIDENT_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "11 02 21 00 00 1A 46 48"
)
DARK_PRINCESS_DEATH_TRIGGER = 0x1A42B8
DARK_PRINCESS_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "12 02 0C 00 00 1A 46 68"
)
GREAT_DRAGON_DEATH_TRIGGER = 0x1A42C0
GREAT_DRAGON_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "15 02 54 00 00 1A 46 A2"
)
PROTAGONIST_DEATH_EVENT = 0x1A45BE
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 01 02 01 00 1A 51 42 13 FF"
)
FIRST_RESIDENT_DEATH_EVENT = 0x1A4636
FIRST_RESIDENT_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 20 32 01 00 1A 52 7A 02 0C 5A 01 00 1A 52 8E FF FF"
)
SECOND_RESIDENT_DEATH_EVENT = 0x1A4648
SECOND_RESIDENT_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 21 32 01 00 1A 52 B0 02 0C 5A 01 00 1A 52 D2 FF FF"
)
DARK_PRINCESS_DEATH_EVENT = 0x1A4668
DARK_PRINCESS_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 0C 5B 01 00 1A 53 2E 17 FF"
)
GREAT_DRAGON_DEATH_EVENT = 0x1A46A2
GREAT_DRAGON_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 54 C4 01 00 1A 54 12 13 FF"
)
PROBE_AT = 0
PROBE_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_GROUP_COUNT = 20
PROTAGONIST_RUNTIME_GROUP = 0
PROTAGONIST_NAME_ID = 0x01
RESIDENT_NAME_IDS = (0x20, 0x21)
RUNTIME_NAME_OFFSET = 0x01
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_Y_OFFSET = 0x07


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def mark_runtime_groups_defeated_code(groups: tuple[int, ...]) -> bytes:
    code = bytearray()
    for group in groups:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def protagonist_death_wrapper_code() -> bytes:
    return mark_runtime_groups_defeated_code((PROTAGONIST_RUNTIME_GROUP,))


def resident_annihilation_wrapper_code() -> bytes:
    # Runtime group slots depend on the deployed commander count. Find the
    # residents by their source name IDs instead of assuming fixed slots.
    code = bytearray(bytes.fromhex("2F 00"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(RUNTIME_GROUP_BASE.to_bytes(4, "big"))
    code.extend(bytes.fromhex("70 13"))
    resident_loop = len(code)
    code.extend(bytes.fromhex("0C 28 00 20 00 01"))
    code.extend(bytes.fromhex("67 08"))
    code.extend(bytes.fromhex("0C 28 00 21 00 01"))
    code.extend(bytes.fromhex("66 04"))
    code.extend(bytes.fromhex("42 28 00 03"))
    code.extend(bytes.fromhex("D0 FC 00 60"))
    resident_dbra = len(code)
    code.extend(bytes.fromhex("51 C8"))
    code.extend(
        (resident_loop - (resident_dbra + 2)).to_bytes(
            2, "big", signed=True
        )
    )

    # A reused completion save can leave Elwin off-map. Resolve him by name as
    # well so the diagnostic remains independent of runtime slot ordering.
    code.extend(bytes.fromhex("41 F9"))
    code.extend(RUNTIME_GROUP_BASE.to_bytes(4, "big"))
    code.extend(bytes.fromhex("70 13"))
    protagonist_loop = len(code)
    code.extend(bytes.fromhex("0C 28 00 01 00 01"))
    code.extend(bytes.fromhex("67 0A"))
    code.extend(bytes.fromhex("D0 FC 00 60"))
    protagonist_dbra = len(code)
    code.extend(bytes.fromhex("51 C8"))
    code.extend(
        (protagonist_loop - (protagonist_dbra + 2)).to_bytes(
            2, "big", signed=True
        )
    )
    code.extend(bytes.fromhex("60 0C"))
    x, y = RESIDENT_PROBE_ELWIN_POSITION
    code.extend(bytes.fromhex("11 7C"))
    code.extend(x.to_bytes(2, "big"))
    code.extend(RUNTIME_X_OFFSET.to_bytes(2, "big"))
    code.extend(bytes.fromhex("11 7C"))
    code.extend(y.to_bytes(2, "big"))
    code.extend(RUNTIME_Y_OFFSET.to_bytes(2, "big"))
    code.extend(bytes.fromhex("20 1F"))
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
    if probe[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 18 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 18 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 18 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 18 deployment table")

    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 18 player deployments differ")

    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 18 fixed record {index} differs from Japanese source"
            )
    event_records = (
        (
            "protagonist-death trigger",
            PROTAGONIST_DEATH_TRIGGER,
            PROTAGONIST_DEATH_TRIGGER_BYTES,
        ),
        (
            "first-resident-death trigger",
            FIRST_RESIDENT_DEATH_TRIGGER,
            FIRST_RESIDENT_DEATH_TRIGGER_BYTES,
        ),
        (
            "second-resident-death trigger",
            SECOND_RESIDENT_DEATH_TRIGGER,
            SECOND_RESIDENT_DEATH_TRIGGER_BYTES,
        ),
        (
            "Dark Princess death trigger",
            DARK_PRINCESS_DEATH_TRIGGER,
            DARK_PRINCESS_DEATH_TRIGGER_BYTES,
        ),
        (
            "Great Dragon death trigger",
            GREAT_DRAGON_DEATH_TRIGGER,
            GREAT_DRAGON_DEATH_TRIGGER_BYTES,
        ),
        (
            "protagonist-death event",
            PROTAGONIST_DEATH_EVENT,
            PROTAGONIST_DEATH_EVENT_BYTES,
        ),
        (
            "first-resident-death event",
            FIRST_RESIDENT_DEATH_EVENT,
            FIRST_RESIDENT_DEATH_EVENT_BYTES,
        ),
        (
            "second-resident-death event",
            SECOND_RESIDENT_DEATH_EVENT,
            SECOND_RESIDENT_DEATH_EVENT_BYTES,
        ),
        (
            "Dark Princess death event",
            DARK_PRINCESS_DEATH_EVENT,
            DARK_PRINCESS_DEATH_EVENT_BYTES,
        ),
        (
            "Great Dragon death event",
            GREAT_DRAGON_DEATH_EVENT,
            GREAT_DRAGON_DEATH_EVENT_BYTES,
        ),
    )
    for event_label, event_start, expected in event_records:
        event_end = event_start + len(expected)
        for label, data in (("Japanese", source), ("input", probe)):
            if data[event_start:event_end] != expected:
                raise ValueError(
                    f"{label} Scenario 18 {event_label} changed"
                )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    dark_princess_layout: bool = False,
    protagonist_death: bool = False,
    resident_annihilation: bool = False,
) -> int:
    validate_layout(probe, source)
    modes = (
        completion_layout,
        dark_princess_layout,
        protagonist_death,
        resident_annihilation,
    )
    if sum(modes) > 1:
        raise ValueError("Scenario 18 diagnostic modes conflict")
    if protagonist_death or resident_annihilation:
        wrapper = (
            protagonist_death_wrapper_code()
            if protagonist_death
            else resident_annihilation_wrapper_code()
        )
        install_start_wrapper(probe, source, wrapper)
        return builder.update_md_checksum(probe)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if completion_layout or dark_princess_layout:
        position = (
            COMPLETION_ELWIN_POSITION
            if completion_layout
            else DARK_PRINCESS_ELWIN_POSITION
        )
        elwin = deployment_bytes((position,))
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(elwin)
        ] = elwin
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 18 ROM with weakened monster groups "
            "while preserving both residents, stock deployments, Lana, and "
            "all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "move only Elwin to (35,5), one tile below the source Great "
            "Dragon at (35,4)"
        ),
    )
    parser.add_argument(
        "--dark-princess-layout",
        action="store_true",
        help=(
            "move only Elwin to (37,3), one tile below the source Dark "
            "Princess at (37,2)"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 18 deployment and fixed record, then "
            "mark only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--resident-annihilation",
        action="store_true",
        help=(
            "preserve every Scenario 18 deployment and fixed record, then "
            "find resident name IDs 20/21 and give only those commanders zero "
            "HP through Start"
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
        completion_layout=args.completion_layout,
        dark_princess_layout=args.dark_princess_layout,
        protagonist_death=args.protagonist_death,
        resident_annihilation=args.resident_annihilation,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death: all Scenario 18 deployments and fixed "
            "records preserved"
        )
        print("Start marks only runtime player group 0 defeated")
    elif args.resident_annihilation:
        print(
            "resident-annihilation: all Scenario 18 deployments and fixed "
            "records preserved"
        )
        print(
            "Start scans all runtime groups for resident name IDs 20/21 and "
            "gives only those commanders zero HP so the stock group-death "
            "cleanup handles their commanders and troops"
        )
        print(
            "Elwin retains HP/status and returns from the completion GST "
            "position to the source deployment (9,12)"
        )
    else:
        print("Scenario 18 enemy records 2..10: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (9,12) to (35,5)")
        print("Great Dragon remains at the source position (35,4)")
    elif args.dark_princess_layout:
        print("Dark Princess layout: Elwin moved from (9,12) to (37,3)")
        print("Lana remains at the source position (37,2)")
    elif not args.protagonist_death and not args.resident_annihilation:
        print(
            "both residents, stock deployments, identities, classes, levels, "
            "coordinates, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
