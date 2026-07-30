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
    ROOT / "roms/builds/Langrisser II (Scenario 3 Clear Probe).md"
)

SCENARIO_NUMBER = 3
SCENARIO_HEADER = 0x1804F8
DEPLOYMENT_TABLE = 0x180510
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0010 0010")
SOURCE_PLAYER_DEPLOYMENTS = (
    (16, 16),
    (15, 20),
    (20, 19),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
FIRST_ENEMY_RECORD_INDEX = 2
LAST_ENEMY_RECORD_INDEX = 9
PROBE_AT = 90
PROBE_DF = 0
PROBE_COORDINATES = (
    (16, 15),
    (15, 15),
    (17, 15),
    (14, 15),
    (18, 15),
    (14, 16),
    (18, 16),
    (16, 14),
)

EVENT_BLOCK_START = 0x1881AE
EVENT_BLOCK_END = 0x189BA6
PROTAGONIST_DEATH_TRIGGER = 0x188222
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0C 02 01 00 00 18 85 E8"
)
PROTAGONIST_DEATH_HANDLER = 0x1885E8
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 01 02 01 00 18 92 BE 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x1892BE
LIANA_DEATH_TRIGGER = 0x18823A
LIANA_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "10 02 02 00 00 18 86 14"
)
LIANA_DEATH_HANDLER = 0x188614
LIANA_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 02 06 01 00 18 93 3C "
    "13 FF "
    "04 13 00 18 86 32 "
    "02 13 60 01 00 18 93 76 "
    "16 FF 00 18 86 3A "
    "02 0F 54 01 00 18 93 DC "
    "02 01 04 01 00 18 94 88 "
    "15 FF FF FF"
)
LIANA_DEATH_DIRECT_TEXTS = (0x18933C, 0x189376, 0x1893DC, 0x189488)
LIANA_DEATH_PHYSICAL_TEXTS = (
    0x18933C,
    0x189376,
    0x189388,
    0x1893DC,
    0x189402,
    0x189448,
    0x189488,
)
LIANA_DEATH_CONTINUATIONS = {
    0x189376: 0x189388,
    0x1893DC: 0x189402,
    0x189402: 0x189448,
}

START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
LIANA_RUNTIME_GROUP = 3
ZORUM_RUNTIME_GROUP = 5
ANNIHILATION_RUNTIME_GROUPS = tuple(range(ZORUM_RUNTIME_GROUP, 13))
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def runtime_death_wrapper_code(target_groups: tuple[int, ...]) -> bytes:
    allowed = {
        (PROTAGONIST_RUNTIME_GROUP,),
        (LIANA_RUNTIME_GROUP,),
        (LIANA_RUNTIME_GROUP, ZORUM_RUNTIME_GROUP),
    }
    if target_groups not in allowed:
        raise ValueError("unsupported Scenario 3 death target groups")
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


def enemy_annihilation_wrapper_code() -> bytes:
    code = bytearray()
    for group in ANNIHILATION_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
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
    ):
        end = offset + len(expected)
        for source_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected:
                raise ValueError(
                    f"{source_label} Scenario 3 {label} changed"
                )


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 3 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 3 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 3 fixed record count {source_layout.record_count}"
        )
    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(
        expected_deployments
    )
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end]
            != expected_deployments
        ):
            raise ValueError(f"{label} Scenario 3 player deployments changed")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 3 fixed record {index} differs from Japanese source"
            )
    validate_events(probe, source)


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    enemy_annihilation: bool = False,
    liana_death: bool = False,
    liana_death_zorum_defeated: bool = False,
    protagonist_death: bool = False,
) -> int:
    if sum(
        (
            enemy_annihilation,
            liana_death,
            liana_death_zorum_defeated,
            protagonist_death,
        )
    ) > 1:
        raise ValueError("Scenario 3 diagnostic modes are mutually exclusive")
    validate_layout(probe, source)
    if enemy_annihilation:
        install_start_wrapper(
            probe,
            source,
            enemy_annihilation_wrapper_code(),
            label="enemy-annihilation",
        )
        return builder.update_md_checksum(probe)
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code((PROTAGONIST_RUNTIME_GROUP,)),
            label="protagonist-death",
        )
        return builder.update_md_checksum(probe)
    if liana_death:
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code((LIANA_RUNTIME_GROUP,)),
            label="Liana-death",
        )
        return builder.update_md_checksum(probe)
    if liana_death_zorum_defeated:
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code(
                (LIANA_RUNTIME_GROUP, ZORUM_RUNTIME_GROUP)
            ),
            label="Liana-death-after-Zorum",
        )
        return builder.update_md_checksum(probe)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index, (x, y) in enumerate(
        PROBE_COORDINATES, start=FIRST_ENEMY_RECORD_INDEX
    ):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        probe[base + FIELD_OFFSETS["x"]] = x
        probe[base + FIELD_OFFSETS["y"]] = y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 3 ROM with weakened enemies placed "
            "around Elwin for stock completion-dialogue tests"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--enemy-annihilation",
        action="store_true",
        help=(
            "preserve all Scenario 3 records and mark only enemy runtime "
            "groups 5..12 defeated through Start"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve all Scenario 3 records and mark only runtime player "
            "group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--liana-death",
        action="store_true",
        help=(
            "preserve all Scenario 3 records and mark only Liana's runtime "
            "group 3 defeated through Start while Zorum remains alive"
        ),
    )
    mode.add_argument(
        "--liana-death-zorum-defeated",
        action="store_true",
        help=(
            "preserve all Scenario 3 records and mark only Liana and Zorum "
            "runtime groups defeated through Start"
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
        enemy_annihilation=args.enemy_annihilation,
        liana_death=args.liana_death,
        liana_death_zorum_defeated=args.liana_death_zorum_defeated,
        protagonist_death=args.protagonist_death,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.enemy_annihilation:
        print(
            "Scenario 3 enemy-annihilation mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only enemy runtime groups 5..12 defeated, then "
            "returns to the stock Start handler"
        )
    elif args.protagonist_death:
        print(
            "Scenario 3 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.liana_death:
        print(
            "Scenario 3 Liana-death mode: all deployments and fixed records "
            "remain source-identical; Zorum remains alive"
        )
        print(
            "Start marks only Liana runtime group 3 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.liana_death_zorum_defeated:
        print(
            "Scenario 3 alternate Liana-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only Liana group 3 and Zorum group 5 defeated, then "
            "returns to the stock Start handler"
        )
    else:
        print(
            f"Scenario 3 enemies: AT {PROBE_AT}, DF {PROBE_DF}, no "
            "mercenaries, placed around first Elwin deployment"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
