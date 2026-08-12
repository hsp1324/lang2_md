#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.class_change_data import (
    ClassTransition,
    class_change_chain_pointer,
    read_class_change_chain,
    transition_for_class,
)
from tools.class_hire_data import (
    CLASS_COUNT,
    CLASS_RECORD_SIZE,
    CLASS_RECORD_TABLE,
)


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Class Change Probe).md"
)

LEVEL_UP_HANDLER = 0x01480C
END_TURN_LEVEL_UP_ENTRY_OPERAND = 0x00D748
PROBE_WRAPPER = 0x3FF000
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
START_MENU_PROBE_WRAPPER = 0x3FF040
CLASS_CHANGE_RESUME_OPERAND = 0x014D0C
POST_APPLY_WRAPPER = START_MENU_PROBE_WRAPPER
RUNTIME_RECORD_BASE = 0xFFFF603C
RUNTIME_RECORD_SIZE = 0x60
PLAYER_RUNTIME_RECORD_COUNT = 10
ELWIN_CLASS_OFFSET = 0x00
ELWIN_LEVEL_OFFSET = 0x2E
ELWIN_EXPERIENCE_OFFSET = 0x2F
EQUIPPED_ITEM_OFFSET = 0x0B
RUNESTONE_ITEM_ID = 0x1A
ELWIN_FIGHTER_CLASS = 0x01
PROBE_LEVEL = 9
PROBE_EXPERIENCE = 16
CLASS_EXPERIENCE_FACTOR_OFFSET = 0x14


def runtime_record_address(runtime_record_index: int) -> int:
    if not 0 <= runtime_record_index < PLAYER_RUNTIME_RECORD_COUNT:
        raise ValueError("runtime record index must be 0..9")
    return RUNTIME_RECORD_BASE + runtime_record_index * RUNTIME_RECORD_SIZE


def class_change_experience(source: bytes, class_id: int) -> int:
    if not 0 <= class_id < CLASS_COUNT:
        raise ValueError(f"class ID must be 0..{CLASS_COUNT - 1}")
    offset = (
        CLASS_RECORD_TABLE
        + class_id * CLASS_RECORD_SIZE
        + CLASS_EXPERIENCE_FACTOR_OFFSET
    )
    return source[offset] << 3


def wrapper_code(
    runtime_record_index: int = 0,
    expected_class: int = ELWIN_FIGHTER_CLASS,
    forced_commander_id: int | None = None,
    probe_level: int = PROBE_LEVEL,
    probe_experience: int = PROBE_EXPERIENCE,
    equipped_item: int | None = None,
) -> bytes:
    if not 0 <= expected_class <= 0xFF:
        raise ValueError("expected class ID must fit one byte")
    if forced_commander_id is not None and not 1 <= forced_commander_id <= 10:
        raise ValueError("forced commander ID must be 1..10")
    if not 1 <= probe_level <= 9:
        raise ValueError("probe level must be 1..9")
    if not 0 <= probe_experience <= 0xFF:
        raise ValueError("probe experience must fit one byte")
    if equipped_item is not None and not 0 <= equipped_item <= 0xFF:
        raise ValueError("equipped item ID must fit one byte")
    record = runtime_record_address(runtime_record_index)
    code = bytearray()
    if forced_commander_id is None:
        code.extend(bytes.fromhex("0C 39"))
        code.extend(expected_class.to_bytes(2, "big"))
        code.extend(record.to_bytes(4, "big"))
        skip_state_writes = 0x12 + (8 if equipped_item is not None else 0)
        code.extend(bytes.fromhex("66 00"))
        code.extend(skip_state_writes.to_bytes(2, "big"))
    else:
        for value, field_offset in (
            (expected_class, ELWIN_CLASS_OFFSET),
            (forced_commander_id, 0x01),
        ):
            code.extend(bytes.fromhex("13 FC"))
            code.extend(value.to_bytes(2, "big"))
            code.extend((record + field_offset).to_bytes(4, "big"))
    for value, field_offset in (
        (probe_level, ELWIN_LEVEL_OFFSET),
        (probe_experience, ELWIN_EXPERIENCE_OFFSET),
    ):
        code.extend(bytes.fromhex("13 FC"))
        code.extend(value.to_bytes(2, "big"))
        code.extend((record + field_offset).to_bytes(4, "big"))
    if equipped_item is not None:
        code.extend(bytes.fromhex("13 FC"))
        code.extend(equipped_item.to_bytes(2, "big"))
        code.extend((record + EQUIPPED_ITEM_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9 00 01 48 0C"))
    return bytes(code)


def join_marker_clear_instruction(commander_id: int) -> bytes:
    """Return the diagnostic CLR.B used before the stock level-up handler."""
    try:
        row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
    except KeyError as exc:
        raise ValueError(
            f"commander {commander_id} has no join class-choice marker"
        ) from exc
    marker_address = int(row["active_marker_address"])
    return bytes.fromhex("42 39") + marker_address.to_bytes(4, "big")


def start_menu_wrapper_code(
    commander_id: int = 1,
    candidates: tuple[int, ...] = (4, 5, 10),
    runtime_record_index: int = 0,
) -> bytes:
    if not 1 <= commander_id <= 10:
        raise ValueError("commander ID must be 1..10")
    if not 1 <= len(candidates) <= 3:
        raise ValueError("class-change probe needs 1..3 candidates")
    if any(not 0 <= candidate <= 0xFFFF for candidate in candidates):
        raise ValueError("candidate class ID must fit one word")

    # Reproduce the eight-word candidate array built by the stock level-up
    # routine: commander ID, up to three classes, then FFFF sentinels.
    values = [commander_id, *candidates]
    values.extend([0xFFFF] * (8 - len(values)))
    code = bytearray(bytes.fromhex("41 F9 FF FF AA 00"))
    for value in values:
        code.extend(bytes.fromhex("30 FC"))
        code.extend(value.to_bytes(2, "big"))
    runtime_record = runtime_record_address(runtime_record_index)
    code.extend(bytes.fromhex("43 F9"))
    code.extend(runtime_record.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9 00 02 BB 48"))
    return bytes(code)


def post_apply_wrapper_code(
    runtime_record_index: int,
    restore_commander_id: int,
) -> bytes:
    if not 1 <= restore_commander_id <= 10:
        raise ValueError("restore commander ID must be 1..10")
    record = runtime_record_address(runtime_record_index)
    code = bytearray(bytes.fromhex("13 FC"))
    code.extend(restore_commander_id.to_bytes(2, "big"))
    code.extend((record + 0x01).to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9 00 01 48 0C"))
    return bytes(code)


def selected_transition(
    source: bytes, commander_id: int, current_class: int | None
) -> ClassTransition:
    if current_class is None:
        return read_class_change_chain(source, commander_id)[0]
    return transition_for_class(source, commander_id, current_class)


def prefer_transition_candidate(
    probe: bytearray,
    source: bytes,
    commander_id: int,
    transition: ClassTransition,
    preferred_candidate: int | None,
) -> ClassTransition:
    if preferred_candidate is None:
        return transition
    if preferred_candidate not in transition.candidates:
        candidates = "/".join(f"0x{value:02X}" for value in transition.candidates)
        raise ValueError(
            f"preferred class 0x{preferred_candidate:02X} is not a source "
            f"candidate ({candidates})"
        )
    reordered = (
        preferred_candidate,
        *(value for value in transition.candidates if value != preferred_candidate),
    )
    if reordered == transition.candidates:
        return transition

    chain = read_class_change_chain(source, commander_id)
    transition_index = next(
        index
        for index, source_transition in enumerate(chain)
        if source_transition.current_class == transition.current_class
    )
    candidate_offset = (
        class_change_chain_pointer(source, commander_id)
        + transition_index * 8
        + 2
    )
    expected = b"".join(
        value.to_bytes(2, "big") for value in transition.candidates
    )
    if probe[candidate_offset : candidate_offset + len(expected)] != expected:
        raise ValueError("input class-change candidate record changed")
    replacement = b"".join(value.to_bytes(2, "big") for value in reordered)
    probe[candidate_offset : candidate_offset + len(replacement)] = replacement
    return ClassTransition(transition.current_class, reordered)


def patch_probe(
    probe: bytearray,
    source: bytes,
    commander_id: int = 1,
    current_class: int | None = None,
    runtime_record_index: int = 0,
    enable_start_menu_probe: bool = True,
    force_runtime_context: bool = False,
    restore_commander_id: int = 1,
    preferred_candidate: int | None = None,
    runestone_restart: bool = False,
    preserve_production_resume: bool = False,
    clear_join_marker: bool = False,
) -> int:
    if force_runtime_context and enable_start_menu_probe:
        raise ValueError(
            "forced runtime context requires the end-turn-only probe"
        )
    if runestone_restart and current_class is None:
        raise ValueError("Runestone restart requires a current class")
    if preserve_production_resume and not force_runtime_context:
        raise ValueError(
            "preserving the production resume requires a forced runtime context"
        )
    if clear_join_marker and not (force_runtime_context and runestone_restart):
        raise ValueError(
            "clearing the join marker requires a forced Rune Stone context"
        )
    transition = prefer_transition_candidate(
        probe,
        source,
        commander_id,
        (
            read_class_change_chain(source, commander_id)[0]
            if runestone_restart
            else selected_transition(source, commander_id, current_class)
        ),
        preferred_candidate,
    )
    trigger_class = (
        int(current_class) if runestone_restart else transition.current_class
    )
    expected = LEVEL_UP_HANDLER.to_bytes(4, "big")
    offset = END_TURN_LEVEL_UP_ENTRY_OPERAND
    if source[offset : offset + 4] != expected:
        raise ValueError("Japanese end-turn level-up operand changed")
    if probe[offset : offset + 4] != expected:
        raise ValueError("input end-turn level-up operand changed")

    code = wrapper_code(
        runtime_record_index=runtime_record_index,
        expected_class=trigger_class,
        forced_commander_id=commander_id if force_runtime_context else None,
        probe_experience=class_change_experience(
            source,
            trigger_class,
        ),
        equipped_item=RUNESTONE_ITEM_ID if runestone_restart else None,
    )
    if clear_join_marker:
        code = join_marker_clear_instruction(commander_id) + code
    wrapper_end = PROBE_WRAPPER + len(code)
    if probe[PROBE_WRAPPER:wrapper_end] != b"\xFF" * len(code):
        raise ValueError("input probe wrapper region is not empty")

    probe[offset : offset + 4] = PROBE_WRAPPER.to_bytes(4, "big")
    probe[PROBE_WRAPPER:wrapper_end] = code

    if force_runtime_context:
        resume_expected = LEVEL_UP_HANDLER.to_bytes(4, "big")
        resume_offset = CLASS_CHANGE_RESUME_OPERAND
        declared_join_wrapper = (
            builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER.to_bytes(4, "big")
        )
        source_resume = source[resume_offset : resume_offset + 4]
        if source_resume not in (resume_expected, declared_join_wrapper):
            raise ValueError("source class-change resume operand changed")
        production_resume = probe[resume_offset : resume_offset + 4]
        if production_resume not in (resume_expected, declared_join_wrapper):
            raise ValueError("input class-change resume operand changed")
        if not preserve_production_resume:
            post_code = post_apply_wrapper_code(
                runtime_record_index,
                restore_commander_id,
            )
            post_end = POST_APPLY_WRAPPER + len(post_code)
            if probe[POST_APPLY_WRAPPER:post_end] != b"\xFF" * len(post_code):
                raise ValueError("input post-apply wrapper region is not empty")
            probe[resume_offset : resume_offset + 4] = POST_APPLY_WRAPPER.to_bytes(
                4, "big"
            )
            probe[POST_APPLY_WRAPPER:post_end] = post_code
    elif enable_start_menu_probe:
        start_expected = START_MENU_ENTRY.to_bytes(4, "big")
        start_offset = START_MENU_ENTRY_OPERAND
        if source[start_offset : start_offset + 4] != start_expected:
            raise ValueError("Japanese Start-menu entry operand changed")
        if probe[start_offset : start_offset + 4] != start_expected:
            raise ValueError("input Start-menu entry operand changed")
        start_code = start_menu_wrapper_code(
            commander_id,
            transition.candidates,
            runtime_record_index=runtime_record_index,
        )
        start_wrapper_end = START_MENU_PROBE_WRAPPER + len(start_code)
        if (
            probe[START_MENU_PROBE_WRAPPER:start_wrapper_end]
            != b"\xFF" * len(start_code)
        ):
            raise ValueError("input Start-menu probe wrapper region is not empty")
        probe[start_offset : start_offset + 4] = START_MENU_PROBE_WRAPPER.to_bytes(
            4, "big"
        )
        probe[START_MENU_PROBE_WRAPPER:start_wrapper_end] = start_code
    return builder.update_md_checksum(probe)


def patch_level_up_only_probe(
    probe: bytearray,
    source: bytes,
    current_class: int,
    runtime_record_index: int,
    probe_level: int = 1,
    start_menu_trigger: bool = False,
) -> int:
    if not 0 <= current_class < CLASS_COUNT:
        raise ValueError(f"class ID must be 0..{CLASS_COUNT - 1}")

    if start_menu_trigger:
        expected = START_MENU_ENTRY.to_bytes(4, "big")
        offset = START_MENU_ENTRY_OPERAND
        label = "Start-menu entry"
    else:
        expected = LEVEL_UP_HANDLER.to_bytes(4, "big")
        offset = END_TURN_LEVEL_UP_ENTRY_OPERAND
        label = "end-turn level-up"
    if source[offset : offset + 4] != expected:
        raise ValueError(f"Japanese {label} operand changed")
    if probe[offset : offset + 4] != expected:
        raise ValueError(f"input {label} operand changed")

    code = wrapper_code(
        runtime_record_index=runtime_record_index,
        expected_class=current_class,
        probe_level=probe_level,
        probe_experience=class_change_experience(source, current_class),
    )
    wrapper_end = PROBE_WRAPPER + len(code)
    if probe[PROBE_WRAPPER:wrapper_end] != b"\xFF" * len(code):
        raise ValueError("input probe wrapper region is not empty")

    probe[offset : offset + 4] = PROBE_WRAPPER.to_bytes(4, "big")
    probe[PROBE_WRAPPER:wrapper_end] = code
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that gives one selected active "
            "commander exactly enough progress to trigger the stock class-change "
            "handler at the next end-turn level-up pass. Pressing Start on a "
            "command-ready map also opens the same UI with that commander's "
            "source-derived candidates."
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--commander-id", type=int, default=1)
    parser.add_argument(
        "--runtime-record-index",
        type=int,
        default=0,
        help=(
            "active player runtime record index (0..9); independent of the "
            "source class-chain commander ID"
        ),
    )
    parser.add_argument(
        "--end-turn-only",
        action="store_true",
        help="preserve the normal Start menu and install only the end-turn trigger",
    )
    parser.add_argument(
        "--level-up-only",
        action="store_true",
        help=(
            "preserve the normal Start menu and perform one stock level-up "
            "without requiring a class-change transition"
        ),
    )
    parser.add_argument(
        "--start-level-up",
        action="store_true",
        help=(
            "with --level-up-only, trigger the guarded stock level-up from "
            "Start instead of waiting through the enemy phase; useful for "
            "an already equipped Rune Stone application probe"
        ),
    )
    parser.add_argument(
        "--probe-level",
        type=int,
        default=1,
        help="current level used by --level-up-only before the stock level-up",
    )
    parser.add_argument(
        "--force-runtime-context",
        action="store_true",
        help=(
            "diagnostic only: set the selected runtime record's current class "
            "and commander ID before entering the stock end-turn handler"
        ),
    )
    parser.add_argument(
        "--restore-commander-id",
        type=int,
        default=1,
        help=(
            "commander ID restored after the forced class-change callback; "
            "Scenario 1 runtime record 0 is Elwin (1)"
        ),
    )
    parser.add_argument(
        "--current-class",
        type=lambda value: int(value, 0),
        help="source class ID; defaults to the commander's initial class",
    )
    parser.add_argument(
        "--preferred-candidate",
        type=lambda value: int(value, 0),
        help=(
            "diagnostic only: retain the source candidate set but move this "
            "candidate to the first row so held confirm input selects it"
        ),
    )
    parser.add_argument(
        "--runestone-restart",
        action="store_true",
        help=(
            "diagnostic only: equip a Rune Stone on the current class and "
            "verify that the stock LV10 handler restarts at the first row"
        ),
    )
    parser.add_argument(
        "--preserve-production-resume",
        action="store_true",
        help=(
            "diagnostic contract: leave the production class-change resume "
            "operand and EXP wrapper byte-identical"
        ),
    )
    parser.add_argument(
        "--clear-join-marker",
        action="store_true",
        help=(
            "diagnostic contract: clear this commander's release join marker "
            "immediately before entering the stock level-up handler"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    if args.level_up_only:
        if args.current_class is None:
            raise ValueError("--level-up-only requires --current-class")
        if args.force_runtime_context:
            raise ValueError("--level-up-only does not force commander identity")
        if args.preferred_candidate is not None:
            raise ValueError(
                "--preferred-candidate requires a class-change transition"
            )
        checksum = patch_level_up_only_probe(
            probe,
            source,
            current_class=args.current_class,
            runtime_record_index=args.runtime_record_index,
            probe_level=args.probe_level,
            start_menu_trigger=args.start_level_up,
        )
        args.output_rom.parent.mkdir(parents=True, exist_ok=True)
        args.output_rom.write_bytes(probe)
        print(
            ("Start" if args.start_level_up else "end-turn level-up handler")
            + " redirected through runtime record "
            f"{args.runtime_record_index} class 0x{args.current_class:02X} "
            f"LV{args.probe_level}/EXP"
            f"{class_change_experience(source, args.current_class)} probe"
        )
        print("normal Start menu and source ability-learning path preserved")
        print(f"checksum: {checksum:04X}")
        print(args.output_rom)
        return 0
    if args.start_level_up:
        raise ValueError("--start-level-up requires --level-up-only")
    if args.probe_level != 1:
        raise ValueError("--probe-level is only valid with --level-up-only")

    if args.runestone_restart and args.current_class is None:
        raise ValueError("--runestone-restart requires --current-class")
    transition = (
        read_class_change_chain(source, args.commander_id)[0]
        if args.runestone_restart
        else selected_transition(source, args.commander_id, args.current_class)
    )
    checksum = patch_probe(
        probe,
        source,
        commander_id=args.commander_id,
        current_class=transition.current_class,
        runtime_record_index=args.runtime_record_index,
        enable_start_menu_probe=not args.end_turn_only,
        force_runtime_context=args.force_runtime_context,
        restore_commander_id=args.restore_commander_id,
        preferred_candidate=args.preferred_candidate,
        runestone_restart=args.runestone_restart,
        preserve_production_resume=args.preserve_production_resume,
        clear_join_marker=args.clear_join_marker,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    trigger_class = int(
        args.current_class if args.runestone_restart else transition.current_class
    )
    print(
        "end-turn level-up handler redirected through runtime record "
        f"{args.runtime_record_index} class 0x{trigger_class:02X} "
        f"LV{PROBE_LEVEL}/EXP"
        f"{class_change_experience(source, trigger_class)} probe"
    )
    if args.runestone_restart:
        print("real Rune Stone item 0x1A equipped for stock restart handling")
    if args.clear_join_marker:
        print("release join marker cleared immediately before stock level-up")
    candidates = "/".join(f"0x{value:02X}" for value in transition.candidates)
    if args.preferred_candidate is not None:
        print(
            "diagnostic candidate order prefers "
            f"0x{args.preferred_candidate:02X}; source membership preserved"
        )
    if args.end_turn_only:
        print("normal Start menu preserved for end-turn application verification")
        if args.force_runtime_context:
            print(
                "runtime context forced to commander "
                f"{args.commander_id} before the stock handler"
            )
    else:
        print(
            f"Start opens commander {args.commander_id} class "
            f"0x{transition.current_class:02X} candidates {candidates} using "
            f"runtime record {args.runtime_record_index}"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
