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
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
COMPLETION_ELWIN_POSITION = (35, 5)
DARK_PRINCESS_ELWIN_POSITION = (37, 3)
RESIDENT_PROBE_ELWIN_POSITION = SOURCE_PLAYER_DEPLOYMENTS[0]
RESIDENT_COMBAT_ATTACKER_RECORDS = (9, 10)
RESIDENT_COMBAT_ATTACKER_POSITIONS = ((15, 19), (11, 19))
GREAT_DRAGON_POSITION = (35, 4)
DARK_PRINCESS_POSITION = (37, 2)
FIRST_RESIDENT_RECORD_INDEX = 0
LAST_RESIDENT_RECORD_INDEX = 1
FIRST_ENEMY_RECORD_INDEX = 2
LAST_ENEMY_RECORD_INDEX = 10
GREAT_DRAGON_RECORD_INDEX = 5
GREAT_DRAGON_NAME_ID = 0x54
GREAT_DRAGON_CLASS_ID = 0x5E
GREAT_DRAGON_RUNTIME_GROUP = (
    PLAYER_DEPLOYMENT_COUNT + GREAT_DRAGON_RECORD_INDEX
)
COMPLETION_HP = 1
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
RESIDENT_COMBAT_ATTACKER_AT = 99
RESIDENT_COMBAT_ATTACKER_DF = 99
DEFEAT_TRIGGER_POINTER = 0x1A4208
DEFEAT_TRIGGER_LIST = 0x1A4268
DEFEAT_TRIGGER_LIST_END = 0x1A4322
RESIDENT_LOSS_EVENT_ID = 0x22
SAME_BANK_RESIDENT_LOSS_EVENT_ID = RESIDENT_LOSS_EVENT_ID
ALL_LISTED_NAMES_DEFEATED_CONDITION = 0x04
RELOCATED_DEFEAT_TRIGGER_LIST = 0x1BFE00
SAME_BANK_DEFEAT_TRIGGER_LIST = 0x1A4C2E
DISPLACED_DIALOGUE_CHAIN_START = SAME_BANK_DEFEAT_TRIGGER_LIST
DISPLACED_DIALOGUE_CHAIN_END = 0x1A4D0E
DISPLACED_DIALOGUE_POINTER = 0x1A4518
RELOCATED_DIALOGUE_CHAIN = 0x3FEE00
LAST_GROUP_DEATH_TRIGGER = 0x1A4312
LAST_GROUP_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "22 08 3E 52 3F 5E 5F 45 46 00 00 1A 47 3C"
)
INPLACE_RESIDENT_LOSS_HANDLER = PROTAGONIST_DEATH_EVENT + 8
INPLACE_RESIDENT_LOSS_EVENT_ID = RESIDENT_LOSS_EVENT_ID
RESIDENT_LOSS_HANDLER = INPLACE_RESIDENT_LOSS_HANDLER
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_GROUP_COUNT = 20
PROTAGONIST_RUNTIME_GROUP = 0
PROTAGONIST_NAME_ID = 0x01
RESIDENT_NAME_IDS = (0x20, 0x21)
RESIDENT_LOSS_CONDITION_NAMES = (
    *RESIDENT_NAME_IDS,
    RESIDENT_NAME_IDS[-1],
)
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


def completion_hp_wrapper_code() -> bytes:
    """Lower only the identity-checked source Great Dragon to one HP."""
    record = (
        RUNTIME_GROUP_BASE
        + GREAT_DRAGON_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    code = bytearray(bytes.fromhex("0C 39 00"))
    code.extend(GREAT_DRAGON_NAME_ID.to_bytes(1, "big"))
    code.extend((record + RUNTIME_NAME_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("66 12"))
    code.extend(bytes.fromhex("0C 39 00"))
    code.extend(GREAT_DRAGON_CLASS_ID.to_bytes(1, "big"))
    code.extend(record.to_bytes(4, "big"))
    code.extend(bytes.fromhex("66 08"))
    code.extend(bytes.fromhex("13 FC 00"))
    code.extend(COMPLETION_HP.to_bytes(1, "big"))
    code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


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


def resident_loss_trigger_code(
    source: bytes,
    *,
    event_id: int = RESIDENT_LOSS_EVENT_ID,
    handler_address: int = RESIDENT_LOSS_HANDLER,
) -> bytes:
    source_triggers = source[DEFEAT_TRIGGER_LIST:DEFEAT_TRIGGER_LIST_END]
    if not source_triggers.endswith(b"\xFF\xFF"):
        raise ValueError("Scenario 18 defeat-trigger list terminator changed")
    aggregate_prefix = bytes(
        (
            event_id,
            ALL_LISTED_NAMES_DEFEATED_CONDITION,
            *RESIDENT_LOSS_CONDITION_NAMES,
            0,
        )
    )
    aggregate_trigger = (
        aggregate_prefix + handler_address.to_bytes(4, "big")
    )
    return source_triggers[:-2] + aggregate_trigger + b"\xFF\xFF"


def same_bank_resident_loss_trigger_installed(
    probe: bytes | bytearray,
    source: bytes,
) -> bool:
    if (
        probe[DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4]
        != SAME_BANK_DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
        or probe[
            DISPLACED_DIALOGUE_POINTER : DISPLACED_DIALOGUE_POINTER + 4
        ]
        != RELOCATED_DIALOGUE_CHAIN.to_bytes(4, "big")
    ):
        return False
    code = resident_loss_trigger_code(
        source,
        event_id=SAME_BANK_RESIDENT_LOSS_EVENT_ID,
    )
    if (
        probe[
            SAME_BANK_DEFEAT_TRIGGER_LIST:
            SAME_BANK_DEFEAT_TRIGGER_LIST + len(code)
        ]
        != code
    ):
        raise ValueError("installed Scenario 18 resident-loss trigger changed")
    return True


def install_resident_loss_trigger(probe: bytearray, source: bytes) -> None:
    expected_pointer = DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
    for label, data in (("Japanese", source), ("input", probe)):
        if data[DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4] != expected_pointer:
            raise ValueError(f"{label} Scenario 18 defeat-trigger pointer changed")
    code = resident_loss_trigger_code(source)
    end = RELOCATED_DEFEAT_TRIGGER_LIST + len(code)
    if probe[RELOCATED_DEFEAT_TRIGGER_LIST:end] != b"\xFF" * len(code):
        raise ValueError("input resident-loss trigger region is not empty")
    probe[
        DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4
    ] = RELOCATED_DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
    probe[RELOCATED_DEFEAT_TRIGGER_LIST:end] = code


def install_same_bank_resident_loss_trigger(
    probe: bytearray,
    source: bytes,
) -> None:
    if same_bank_resident_loss_trigger_installed(probe, source):
        return
    expected_list_pointer = DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
    expected_dialogue_pointer = DISPLACED_DIALOGUE_CHAIN_START.to_bytes(
        4, "big"
    )
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4]
            != expected_list_pointer
        ):
            raise ValueError(
                f"{label} Scenario 18 defeat-trigger pointer changed"
            )
        if (
            data[
                DISPLACED_DIALOGUE_POINTER :
                DISPLACED_DIALOGUE_POINTER + 4
            ]
            != expected_dialogue_pointer
        ):
            raise ValueError(
                f"{label} Scenario 18 displaced-dialogue pointer changed"
            )

    displaced_dialogue = bytes(
        probe[DISPLACED_DIALOGUE_CHAIN_START:DISPLACED_DIALOGUE_CHAIN_END]
    )
    relocated_dialogue_end = RELOCATED_DIALOGUE_CHAIN + len(
        displaced_dialogue
    )
    if (
        probe[RELOCATED_DIALOGUE_CHAIN:relocated_dialogue_end]
        != b"\xFF" * len(displaced_dialogue)
    ):
        raise ValueError("input relocated-dialogue region is not empty")

    code = resident_loss_trigger_code(
        source,
        event_id=SAME_BANK_RESIDENT_LOSS_EVENT_ID,
    )
    available = (
        DISPLACED_DIALOGUE_CHAIN_END - DISPLACED_DIALOGUE_CHAIN_START
    )
    if len(code) > available:
        raise ValueError("same-bank resident-loss trigger exceeds dialogue slot")

    probe[RELOCATED_DIALOGUE_CHAIN:relocated_dialogue_end] = (
        displaced_dialogue
    )
    probe[
        DISPLACED_DIALOGUE_POINTER : DISPLACED_DIALOGUE_POINTER + 4
    ] = RELOCATED_DIALOGUE_CHAIN.to_bytes(4, "big")
    probe[
        DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4
    ] = SAME_BANK_DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
    probe[
        SAME_BANK_DEFEAT_TRIGGER_LIST:DISPLACED_DIALOGUE_CHAIN_END
    ] = code + b"\xFF" * (available - len(code))


def install_inplace_resident_loss_trigger(
    probe: bytearray,
    source: bytes,
) -> None:
    """Diagnostic only: replace the final group trigger without relocating the list."""
    if (
        probe[DEFEAT_TRIGGER_POINTER : DEFEAT_TRIGGER_POINTER + 4]
        != DEFEAT_TRIGGER_LIST.to_bytes(4, "big")
    ):
        raise ValueError(
            "input Scenario 18 defeat-trigger pointer is already relocated"
        )
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[
                LAST_GROUP_DEATH_TRIGGER:
                LAST_GROUP_DEATH_TRIGGER + len(LAST_GROUP_DEATH_TRIGGER_BYTES)
            ]
            != LAST_GROUP_DEATH_TRIGGER_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 18 final group-death trigger changed"
            )
    aggregate_trigger = bytes(
        (
            INPLACE_RESIDENT_LOSS_EVENT_ID,
            ALL_LISTED_NAMES_DEFEATED_CONDITION,
            *RESIDENT_LOSS_CONDITION_NAMES,
            0,
        )
    ) + INPLACE_RESIDENT_LOSS_HANDLER.to_bytes(4, "big")
    replacement = (
        aggregate_trigger
        + b"\xFF\xFF"
        + b"\xFF"
        * (
            len(LAST_GROUP_DEATH_TRIGGER_BYTES)
            - len(aggregate_trigger)
            - 2
        )
    )
    probe[
        LAST_GROUP_DEATH_TRIGGER:
        LAST_GROUP_DEATH_TRIGGER + len(replacement)
    ] = replacement
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[
                INPLACE_RESIDENT_LOSS_HANDLER:
                INPLACE_RESIDENT_LOSS_HANDLER + 2
            ]
            != b"\x13\xFF"
        ):
            raise ValueError(
                f"{label} Scenario 18 protagonist GAME OVER handler changed"
            )


def stage_resident_combat_loss(probe: bytearray, source: bytes) -> None:
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(
        FIRST_RESIDENT_RECORD_INDEX,
        LAST_RESIDENT_RECORD_INDEX + 1,
    ):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["df"]] = 0
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    for index, (x, y) in zip(
        RESIDENT_COMBAT_ATTACKER_RECORDS,
        RESIDENT_COMBAT_ATTACKER_POSITIONS,
    ):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = RESIDENT_COMBAT_ATTACKER_AT
        probe[base + FIELD_OFFSETS["df"]] = RESIDENT_COMBAT_ATTACKER_DF
        probe[base + FIELD_OFFSETS["x"]] = x
        probe[base + FIELD_OFFSETS["y"]] = y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6


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
    resident_combat_loss: bool = False,
    resident_combat_loss_fix: bool = False,
    resident_combat_loss_same_bank_fix: bool = False,
    resident_combat_loss_inplace_fix: bool = False,
) -> int:
    validate_layout(probe, source)
    modes = (
        completion_layout,
        dark_princess_layout,
        protagonist_death,
        resident_annihilation,
        resident_combat_loss,
        resident_combat_loss_fix,
        resident_combat_loss_same_bank_fix,
        resident_combat_loss_inplace_fix,
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
    if (
        resident_combat_loss
        or resident_combat_loss_fix
        or resident_combat_loss_same_bank_fix
        or resident_combat_loss_inplace_fix
    ):
        stage_resident_combat_loss(probe, source)
        if resident_combat_loss_fix:
            install_resident_loss_trigger(probe, source)
        elif resident_combat_loss_same_bank_fix:
            install_same_bank_resident_loss_trigger(probe, source)
        elif resident_combat_loss_inplace_fix:
            install_inplace_resident_loss_trigger(probe, source)
        return builder.update_md_checksum(probe)
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
    if completion_layout:
        install_start_wrapper(
            probe,
            source,
            completion_hp_wrapper_code(),
        )
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
    parser.add_argument(
        "--resident-combat-loss",
        action="store_true",
        help=(
            "remove resident and two attacker mercenaries, lower resident DF, "
            "and stage two source enemy commanders for natural resident-loss "
            "battles"
        ),
    )
    parser.add_argument(
        "--resident-combat-loss-fix",
        action="store_true",
        help=(
            "stage the same natural resident-loss battles and add the missing "
            "source aggregate-loss trigger as a second event ID 22 condition"
        ),
    )
    parser.add_argument(
        "--resident-combat-loss-inplace-fix",
        action="store_true",
        help=(
            "diagnostically replace Scenario 18's final group-death record "
            "with the missing resident-loss condition while keeping the "
            "event list at its original address"
        ),
    )
    parser.add_argument(
        "--resident-combat-loss-same-bank-fix",
        action="store_true",
        help=(
            "stage the natural resident-loss battles, relocate one Korean "
            "dialogue chain to expansion ROM, and place the complete source "
            "trigger list plus resident-loss condition in its freed 0x1A-bank "
            "slot"
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
        resident_combat_loss=args.resident_combat_loss,
        resident_combat_loss_fix=args.resident_combat_loss_fix,
        resident_combat_loss_same_bank_fix=(
            args.resident_combat_loss_same_bank_fix
        ),
        resident_combat_loss_inplace_fix=(
            args.resident_combat_loss_inplace_fix
        ),
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
    elif (
        args.resident_combat_loss
        or args.resident_combat_loss_fix
        or args.resident_combat_loss_same_bank_fix
        or args.resident_combat_loss_inplace_fix
    ):
        print(
            "resident-combat-loss: resident identities/classes/events are "
            "preserved with no mercenaries and DF 0"
        )
        print(
            "source enemy records 9 and 10 retain identity/class/events, "
            "gain AT/DF 99 with no mercenaries, and start beside the residents"
        )
        if args.resident_combat_loss_fix:
            print(
                "missing resident aggregate-loss condition is installed as "
                "a second event ID 22 record in the relocated Scenario 18 "
                "defeat-trigger list"
            )
        elif args.resident_combat_loss_same_bank_fix:
            print(
                "missing resident aggregate-loss condition is installed "
                "beside the complete source list in a freed Scenario 18 "
                "dialogue slot within the original 0x1A event bank"
            )
        elif args.resident_combat_loss_inplace_fix:
            print(
                "missing resident aggregate-loss condition temporarily "
                "reuses event ID 22 and replaces the final group-death record "
                "at the original list address"
            )
    else:
        print("Scenario 18 enemy records 2..10: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (9,12) to (35,5)")
        print("Great Dragon remains at the source position (35,4)")
    elif args.dark_princess_layout:
        print("Dark Princess layout: Elwin moved from (9,12) to (37,3)")
        print("Lana remains at the source position (37,2)")
    elif (
        not args.protagonist_death
        and not args.resident_annihilation
        and not args.resident_combat_loss
        and not args.resident_combat_loss_fix
        and not args.resident_combat_loss_same_bank_fix
        and not args.resident_combat_loss_inplace_fix
    ):
        print(
            "both residents, stock deployments, identities, classes, levels, "
            "coordinates, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
