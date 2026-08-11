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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 31 Clear Probe).md"
SCENARIO_NUMBER = 31
SCENARIO_HEADER = 0x18376C
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x183792
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (14, 61),
    (16, 61),
    (5, 56),
    (5, 46),
    (25, 46),
    (25, 36),
    (25, 26),
    (5, 26),
    (5, 16),
    (25, 16),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
COMPACT_PLAYER_DEPLOYMENTS = (
    (14, 56),
    (16, 56),
    (12, 56),
    (18, 56),
    (15, 58),
    *SOURCE_PLAYER_DEPLOYMENTS[5:],
)
FIRST_COMBAT_RECORD_INDEX = 0
LAST_COMBAT_RECORD_INDEX = 9
COMPACT_COMBAT_POSITIONS = {
    0: (13, 55),
    1: (14, 55),
    2: (15, 55),
    3: (16, 55),
    4: (17, 55),
    5: (13, 56),
    6: (15, 56),
    7: (17, 56),
    8: (14, 57),
    9: (16, 57),
}
COMPLETION_SOURCE_RECORD_INDEX = 9
COMPLETION_TARGET_RECORD_INDEX = 0
COMPLETION_RECORD_COUNT = 1
COMPLETION_ACTIVE_POSITION = (14, 60)
COMPLETION_AT = 0xF4
# Keep the one-enemy completion probe five points below the old 0xFC defense.
# At 0xFA the current Normal profile consistently left Bernhardt at HP2 while
# Hard reached HP0; 0xF8 still left Normal at HP1 in eight ordinary attacks.
# The displayed DF floors at 5 even at 0xF7, so the completion Start wrapper
# sets only this diagnostic enemy's runtime HP to 1 before an ordinary attack.
# Larger negative-looking bytes wrap the stock unsigned battle arithmetic and
# can instead turn the hit into zero damage. This is diagnostic ROM data only;
# production Scenario 31 keeps the stock layout and now corrects only record
# 8's duplicate Demon Lord name ID so its existing death event can run.
COMPLETION_DF = 0xF7
COMPLETION_HP = 1
BRANCH_TARGET_INDICES = tuple(range(0, 9))
ALL_FIXED_RECORD_INDICES = tuple(
    range(FIRST_COMBAT_RECORD_INDEX, LAST_COMBAT_RECORD_INDEX + 1)
)
BRANCH_EVENT_SPECS = {
    0: (0x0F, 0x1B83E6, 0x1B8648, 0x1B8A12),
    1: (0x15, 0x1B83EE, 0x1B8688, 0x1B8AAC),
    2: (0x67, 0x1B83F6, 0x1B86BC, 0x1B8B2C),
    3: (0x0D, 0x1B83FE, 0x1B86C6, 0x1B8B36),
    4: (0x11, 0x1B8406, 0x1B86F6, 0x1B8B8A),
    5: (0x14, 0x1B840E, 0x1B8700, 0x1B8BB0),
    6: (0x65, 0x1B8416, 0x1B872C, 0x1B8BD4),
    7: (0x10, 0x1B841E, 0x1B8736, 0x1B8BE2),
    8: (0x66, 0x1B8426, 0x1B8782, 0x1B8C86),
}
BRANCH_EVENT_IDS = {
    0: 0x11,
    1: 0x12,
    2: 0x13,
    3: 0x14,
    4: 0x16,
    5: 0x17,
    6: 0x18,
    7: 0x19,
    8: 0x1A,
}
BRANCH_HANDLER_SPEAKERS = {
    0: (0x0F, 0x55),
    1: (0x15, 0x58),
    2: (0x67, 0xC3),
    3: (0x0D, 0x51),
    4: (0x11, 0xC7),
    5: (0x14, 0x4E),
    6: (0x65, 0xC3),
    7: (0x10, 0x5E),
    8: (0x66, 0xC3),
}
PLAYER_BRANCH_EVENT_SPECS = {
    # runtime group: (event ID, name ID, trigger, handler, text, portrait)
    1: (0x09, 0x05, 0x1B83A6, 0x1B85F8, 0x1B895A, 0x12),
    2: (0x0A, 0x04, 0x1B83AE, 0x1B8602, 0x1B897C, 0x0E),
    3: (0x0B, 0x08, 0x1B83B6, 0x1B860C, 0x1B898A, 0x26),
    4: (0x0C, 0x07, 0x1B83BE, 0x1B8616, 0x1B8996, 0x22),
    5: (0x0D, 0x09, 0x1B83C6, 0x1B8620, 0x1B89B0, 0x1E),
    7: (0x10, 0x0A, 0x1B83DE, 0x1B863E, 0x1B8A06, 0x1A),
    8: (0x0E, 0x02, 0x1B83CE, 0x1B862A, 0x1B89CE, 0x06),
    9: (0x0F, 0x03, 0x1B83D6, 0x1B8634, 0x1B89E2, 0x0A),
}
PLAYER_BRANCH_TARGETS = tuple(PLAYER_BRANCH_EVENT_SPECS)
VARGAS_RECORD_INDEX = 0
LEON_RECORD_INDEX = 3
LAIRD_RECORD_INDEX = 4
EGBERT_RECORD_INDEX = 5
BOZEL_RECORD_INDEX = 7
BERNHARDT_RECORD_INDEX = 9
PROBE_AT = 0
PROBE_DF = 0
PROTAGONIST_DEATH_TRIGGER = 0x1B839E
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "08 02 01 00 00 1B 85 EA"
)
PROTAGONIST_DEATH_EVENT = 0x1B85EA
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 01 02 01 00 1B 89 3E 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x1B893E
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
BRANCH_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
FIRST_FIXED_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
RUNTIME_HP_OFFSET = 0x03
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_NAME_OFFSET = 0x01
RUNTIME_DF_OFFSET = 0x3B
PROTAGONIST_RUNTIME_GROUP = 0
PROTECTED_PROTAGONIST_DF = 0xFF


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def branch_death_wrapper_code(
    target_index: int,
    *,
    protect_protagonist: bool = False,
    repair_legacy_name: bool = True,
) -> bytes:
    if target_index not in BRANCH_TARGET_INDICES:
        raise ValueError(
            f"branch target must be one of {BRANCH_TARGET_INDICES}"
        )
    target_group = FIRST_FIXED_RUNTIME_GROUP + target_index
    trigger_name_id = BRANCH_EVENT_SPECS[target_index][0]
    runtime_name_id = (
        trigger_name_id
        if target_index == 8 and repair_legacy_name
        else None
    )
    return runtime_death_wrapper_code(
        target_group,
        runtime_name_id=runtime_name_id,
        protect_protagonist=protect_protagonist,
    )


def player_branch_death_wrapper_code(target_group: int) -> bytes:
    if target_group not in PLAYER_BRANCH_TARGETS:
        raise ValueError(
            f"player branch target must be one of {PLAYER_BRANCH_TARGETS}"
        )
    return runtime_death_wrapper_code(target_group)


def completion_hp_wrapper_code() -> bytes:
    """Set only the one-enemy completion target to HP1, then run Start."""
    target_group = FIRST_FIXED_RUNTIME_GROUP + COMPLETION_TARGET_RECORD_INDEX
    target_hp = (
        RUNTIME_GROUP_BASE
        + target_group * RUNTIME_GROUP_SIZE
        + RUNTIME_HP_OFFSET
    )
    code = bytearray(bytes.fromhex("13 FC 00"))
    code.extend(COMPLETION_HP.to_bytes(1, "big"))
    code.extend(target_hp.to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def runtime_death_wrapper_code(
    target_group: int,
    *,
    runtime_name_id: int | None = None,
    protect_protagonist: bool = False,
) -> bytes:
    if not 0 <= target_group < PLAYER_DEPLOYMENT_COUNT + len(
        ALL_FIXED_RECORD_INDICES
    ):
        raise ValueError("runtime death target group is outside Scenario 31")
    target = RUNTIME_GROUP_BASE + target_group * RUNTIME_GROUP_SIZE
    code = bytearray()
    if protect_protagonist:
        protagonist = (
            RUNTIME_GROUP_BASE
            + PROTAGONIST_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
        )
        code.extend(bytes.fromhex("13 FC 00"))
        code.extend(PROTECTED_PROTAGONIST_DF.to_bytes(1, "big"))
        code.extend((protagonist + RUNTIME_DF_OFFSET).to_bytes(4, "big"))
    if runtime_name_id is not None:
        code.extend(bytes.fromhex("13 FC 00"))
        code.extend(runtime_name_id.to_bytes(1, "big"))
        code.extend((target + RUNTIME_NAME_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend(
        (target + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
    )
    code.extend(bytes.fromhex("13 FC 00 00"))
    code.extend((target + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
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
    wrapper_end = BRANCH_HP_WRAPPER + len(wrapper)
    if probe[BRANCH_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input branch wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = BRANCH_HP_WRAPPER.to_bytes(4, "big")
    probe[BRANCH_HP_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 31 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 31 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 31 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 31 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 31 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        expected = bytearray(source[base:end])
        # A reviewed Hard input is allowed to differ in the same combat fields
        # this diagnostic itself owns.  Identity, class, level, coordinates,
        # side, visibility, and every other byte remain source-locked.
        expected[FIELD_OFFSETS["at"]] = probe[base + FIELD_OFFSETS["at"]]
        expected[FIELD_OFFSETS["df"]] = probe[base + FIELD_OFFSETS["df"]]
        # Standard Hard stores its runtime soldier-correction lookup tag in
        # the source-unused byte immediately before the mercenary list.
        expected[0x1D] = probe[base + 0x1D]
        mercenaries = FIELD_OFFSETS["mercenaries"]
        expected[mercenaries : mercenaries + 6] = probe[
            base + mercenaries : base + mercenaries + 6
        ]
        # v1.3.5 corrects the source's duplicate ID 0x65 to the stock event's
        # otherwise-unreachable ID 0x66.  Accept legacy production as well so
        # historical probe tests remain reproducible, but reject every other
        # fixed-record difference.
        if (
            index == 8
            and probe[base + FIELD_OFFSETS["name_id"]]
            == builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID
        ):
            expected[FIELD_OFFSETS["name_id"]] = (
                builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID
            )
        if probe[base:end] != expected:
            raise ValueError(
                f"input Scenario 31 fixed record {index} differs from the "
                "reviewed production layout"
            )
    for label, offset, expected_bytes in (
        (
            "protagonist-death trigger",
            PROTAGONIST_DEATH_TRIGGER,
            PROTAGONIST_DEATH_TRIGGER_BYTES,
        ),
        (
            "protagonist-death event",
            PROTAGONIST_DEATH_EVENT,
            PROTAGONIST_DEATH_EVENT_BYTES,
        ),
    ):
        end = offset + len(expected_bytes)
        for rom_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected_bytes:
                raise ValueError(
                    f"{rom_label} Scenario 31 {label} changed"
                )
    for target_index, (
        trigger_name_id,
        trigger_offset,
        handler_offset,
        text_offset,
    ) in BRANCH_EVENT_SPECS.items():
        trigger = bytes(
            (
                BRANCH_EVENT_IDS[target_index],
                0x02,
                trigger_name_id,
                0x00,
                0x00,
            )
        ) + handler_offset.to_bytes(3, "big")
        speaker_id, portrait_id = BRANCH_HANDLER_SPEAKERS[target_index]
        handler_prefix = bytes((0x02, speaker_id, portrait_id, 0x01, 0x00))
        handler_prefix += text_offset.to_bytes(3, "big")
        for rom_label, data in (("Japanese", source), ("input", probe)):
            if data[trigger_offset : trigger_offset + len(trigger)] != trigger:
                raise ValueError(
                    f"{rom_label} Scenario 31 branch {target_index} "
                    "trigger changed"
                )
            if (
                data[handler_offset : handler_offset + len(handler_prefix)]
                != handler_prefix
            ):
                raise ValueError(
                    f"{rom_label} Scenario 31 branch {target_index} "
                    "handler changed"
                )
    for target_group, (
        event_id,
        name_id,
        trigger_offset,
        handler_offset,
        text_offset,
        portrait_id,
    ) in PLAYER_BRANCH_EVENT_SPECS.items():
        trigger = bytes((event_id, 0x02, name_id, 0x00, 0x00))
        trigger += handler_offset.to_bytes(3, "big")
        handler_prefix = bytes((0x02, name_id, portrait_id, 0x01, 0x00))
        handler_prefix += text_offset.to_bytes(3, "big")
        for rom_label, data in (("Japanese", source), ("input", probe)):
            if data[trigger_offset : trigger_offset + len(trigger)] != trigger:
                raise ValueError(
                    f"{rom_label} Scenario 31 player branch group "
                    f"{target_group} trigger changed"
                )
            if (
                data[handler_offset : handler_offset + len(handler_prefix)]
                != handler_prefix
            ):
                raise ValueError(
                    f"{rom_label} Scenario 31 player branch group "
                    f"{target_group} handler changed"
                )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    compact_layout: bool = False,
    completion_layout: bool = False,
    branch_target: int | None = None,
    player_branch_target: int | None = None,
    protect_protagonist: bool = False,
) -> int:
    diagnostic_modes = (
        compact_layout,
        completion_layout,
        branch_target is not None,
        player_branch_target is not None,
    )
    if sum(bool(mode) for mode in diagnostic_modes) > 1:
        raise ValueError("Scenario 31 diagnostic modes are mutually exclusive")
    if protect_protagonist and branch_target is None:
        raise ValueError("protagonist protection requires a branch target")
    if (
        branch_target is not None
        and branch_target not in BRANCH_TARGET_INDICES
    ):
        raise ValueError(
            f"branch target must be one of {BRANCH_TARGET_INDICES}"
        )
    if (
        player_branch_target is not None
        and player_branch_target not in PLAYER_BRANCH_TARGETS
    ):
        raise ValueError(
            f"player branch target must be one of {PLAYER_BRANCH_TARGETS}"
        )
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    if branch_target is not None:
        layout = scenario_layout(source, SCENARIO_NUMBER)
        target_name = (
            layout.records_offset
            + branch_target * FIXED_RECORD_SIZE
            + FIELD_OFFSETS["name_id"]
        )
        repair_legacy_name = not (
            branch_target == 8
            and probe[target_name]
            == builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID
        )
        install_start_wrapper(
            probe,
            source,
            branch_death_wrapper_code(
                branch_target,
                protect_protagonist=protect_protagonist,
                repair_legacy_name=repair_legacy_name,
            ),
        )
        return builder.update_md_checksum(probe)
    if player_branch_target is not None:
        install_start_wrapper(
            probe,
            source,
            player_branch_death_wrapper_code(player_branch_target),
        )
        return builder.update_md_checksum(probe)
    for index in range(FIRST_COMBAT_RECORD_INDEX, LAST_COMBAT_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    if compact_layout:
        positions = deployment_bytes(COMPACT_PLAYER_DEPLOYMENTS)
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(positions)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = positions
        for index, (x, y) in COMPACT_COMBAT_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["x"]] = x
            probe[base + FIELD_OFFSETS["y"]] = y
    elif completion_layout:
        source_record = (
            layout.records_offset
            + COMPLETION_SOURCE_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        active = (
            layout.records_offset
            + COMPLETION_TARGET_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        probe[active : active + FIXED_RECORD_SIZE] = source[
            source_record : source_record + FIXED_RECORD_SIZE
        ]
        probe[active + FIELD_OFFSETS["at"]] = COMPLETION_AT
        probe[active + FIELD_OFFSETS["df"]] = COMPLETION_DF
        mercenaries = active + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
        probe[active + FIELD_OFFSETS["x"]] = COMPLETION_ACTIVE_POSITION[0]
        probe[active + FIELD_OFFSETS["y"]] = COMPLETION_ACTIVE_POSITION[1]
        probe[layout.record_list_offset : layout.record_list_offset + 2] = (
            COMPLETION_RECORD_COUNT.to_bytes(2, "big")
        )
        install_start_wrapper(
            probe,
            source,
            completion_hp_wrapper_code(),
        )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 31 ROM with weakened enemy/special "
            "combat groups while preserving stock deployments, commander "
            "identities, classes, and event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    layout_group = parser.add_mutually_exclusive_group()
    layout_group.add_argument(
        "--compact-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: move the first five player "
            "deployments and all ten combat records into the source-verified "
            "lower hall; use the default probe for stock-coordinate evidence"
        ),
    )
    layout_group.add_argument(
        "--player-branch-target",
        type=int,
        choices=PLAYER_BRANCH_TARGETS,
        help=(
            "diagnostic player-death route only: preserve all fixed data and "
            "mark runtime player GROUP defeated when Start is opened"
        ),
    )
    layout_group.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: move Bernhardt directly above "
            "stock Elwin and temporarily reduce the fixed combat list to "
            "that single source-copied record; "
            "use this derivative only to test the stock victory handler"
        ),
    )
    layout_group.add_argument(
        "--branch-target",
        type=int,
        choices=BRANCH_TARGET_INDICES,
        help=(
            "diagnostic branch route only: preserve all fixed data and mark "
            "only INDEX defeated when Start is opened; INDEX 8 additionally "
            "uses the stock event's otherwise-unrepresented runtime name ID 66"
        ),
    )
    parser.add_argument(
        "--protect-protagonist",
        action="store_true",
        help=(
            "branch diagnostics only: set runtime player group 0 DF to FF "
            "when Start opens so long enemy phases cannot obscure a delayed "
            "target branch"
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
        compact_layout=args.compact_layout,
        completion_layout=args.completion_layout,
        branch_target=args.branch_target,
        player_branch_target=args.player_branch_target,
        protect_protagonist=args.protect_protagonist,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.completion_layout:
        print("Scenario 31 Bernhardt: AT -12, DF -4, no mercenaries")
        print("diagnostic single-record adjacent Bernhardt layout applied")
        print("Bernhardt's source record and all scenario handlers preserved")
    elif args.compact_layout:
        print("Scenario 31 combat records 0..9: AT 0, DF 0, no mercenaries")
        print("diagnostic five-player and combat layout moved to the lower hall")
        print("side IDs, commander identities, classes, and all handlers preserved")
    elif args.branch_target is not None:
        print(
            f"Scenario 31 runtime branch group {args.branch_target}: "
            "runtime defeat diagnostic"
        )
        print(
            "all deployments and fixed records remain production-identical; "
            "v1.3.5 record 8 keeps event ID 66"
        )
        if args.branch_target == 8:
            layout = scenario_layout(source, SCENARIO_NUMBER)
            name_offset = (
                layout.records_offset
                + 8 * FIXED_RECORD_SIZE
                + FIELD_OFFSETS["name_id"]
            )
            if probe[name_offset] == builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID:
                print(
                    "production fixed record already uses ID 66; the runtime "
                    "wrapper does not write the name"
                )
            else:
                print(
                    "legacy runtime group 18 name changes from duplicate "
                    "source ID 65 to branch ID 66"
                )
        if args.protect_protagonist:
            print("runtime player group 0 receives diagnostic DF FF protection")
        else:
            print("all non-target runtime groups remain completely unchanged")
    elif args.player_branch_target is not None:
        print(
            f"Scenario 31 runtime player group {args.player_branch_target}: "
            "runtime defeat diagnostic"
        )
        print(
            "all deployments and fixed records remain production-identical; "
            "v1.3.5 record 8 keeps event ID 66"
        )
        print("all non-target runtime groups remain completely unchanged")
    else:
        print("Scenario 31 combat records 0..9: AT 0, DF 0, no mercenaries")
        print("stock player and combat coordinates preserved")
        print("side IDs, commander identities, classes, and all handlers preserved")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
