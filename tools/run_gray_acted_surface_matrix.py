#!/usr/bin/env python3
"""Capture and verify one scenario's real-move gray acted sprite surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_blastem_sequence as sequence  # noqa: E402
from tools.run_pike_acted_surface_probe import (  # noqa: E402
    runtime_groups,
    work_ram,
)
from tools.verify_preparation_surface_evidence import (  # noqa: E402
    GRAY_TILE_START as GRAY_TILE_START,
    GRAY_VRAM_BYTES,
    GRAY_VRAM_START as GRAY_VRAM_START,
    expected_gray_payload as expected_gray_payload,
    expand_gray_source_mask,
    load_gst,
    plane_tile_hits,
    runtime_group_zero as runtime_group_zero,
)
from scripts import build_korean_jp_probe as builder  # noqa: E402
from tools.scenario_data import FIXED_RECORD_SIZE  # noqa: E402


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/gray_acted_surface_matrix"
DEFAULT_DIRECTIONS = ("down", "right", "left", "up")
VALID_DIRECTIONS = frozenset(DEFAULT_DIRECTIONS)
SELECTION_POLICY = "live_stock_command_pointer"
SELECTED_GROUP_INDEX_ADDRESS = 0xA624
SELECTED_MEMBER_INDEX_ADDRESS = 0xA625
SELECTED_GROUP_POINTER_ADDRESS = 0xA628
SELECTED_MEMBER_POINTER_ADDRESS = 0xA62C
CURSOR_X_ADDRESS = 0xA6DF
CURSOR_Y_ADDRESS = 0xA6E1
RUNTIME_GROUP_ABSOLUTE_BASE = 0x00FF0000 + matrix.RUNTIME_GROUP_BASE
REFERENCE_ROM_SHA256 = "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"


def expected_commander_gray_payload(
    rom_data: bytes,
    commander_id: int,
    class_id: int,
) -> tuple[int, int, bytes, str]:
    source_record = builder.commander_sprite_record_offset(
        rom_data, commander_id, class_id
    )
    release_sprite_id = builder.be16(rom_data, source_record + 1)
    original = builder.IN_ROM.read_bytes()
    custom_mapping = builder.custom_map_sprite_gray_source_map(original)
    if release_sprite_id not in custom_mapping:
        start = 0x0510C0 + release_sprite_id * 0x40
        mask = rom_data[start:start + 0x40]
        if len(mask) != 0x40:
            raise ValueError("stock commander gray mask is truncated")
        payload = expand_gray_source_mask(mask)
        return source_record, release_sprite_id, payload, "stock"

    first_custom_id = min(custom_mapping)
    mask_start = (
        builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE
        + (release_sprite_id - first_custom_id)
        * builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
    )
    mask = rom_data[
        mask_start : mask_start + builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
    ]
    if len(mask) != builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES:
        raise ValueError("custom commander gray mask is truncated")
    return mask_start, release_sprite_id, expand_gray_source_mask(mask), "custom"


def runtime_group_by_index(path: Path, group_index: int) -> dict[str, object]:
    matches = [
        group
        for group in runtime_groups(path)
        if group["group_index"] == group_index
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected runtime group {group_index}, got {len(matches)}"
        )
    return matches[0]


def selected_player_commander(
    gst: Path,
    rom_data: bytes,
    scenario: int,
) -> dict[str, object]:
    """Identify the commander whose stock command menu is actually open."""
    ram = work_ram(gst)
    group_index = ram[SELECTED_GROUP_INDEX_ADDRESS]
    member_index = ram[SELECTED_MEMBER_INDEX_ADDRESS]
    group_pointer = int.from_bytes(
        ram[
            SELECTED_GROUP_POINTER_ADDRESS:
            SELECTED_GROUP_POINTER_ADDRESS + 4
        ],
        "big",
    )
    member_pointer = int.from_bytes(
        ram[
            SELECTED_MEMBER_POINTER_ADDRESS:
            SELECTED_MEMBER_POINTER_ADDRESS + 4
        ],
        "big",
    )
    expected_group_pointer = (
        RUNTIME_GROUP_ABSOLUTE_BASE
        + group_index * matrix.RUNTIME_GROUP_SIZE
    )
    expected_member_pointer = (
        expected_group_pointer
        + member_index * matrix.RUNTIME_MEMBER_SIZE
    )
    player_group_count = matrix.player_commander_count(rom_data, scenario)
    if not 0 <= group_index < player_group_count:
        raise RuntimeError(
            "stock command menu did not select a player runtime group: "
            f"{group_index} not in 0..{player_group_count - 1}"
        )
    if member_index != 0:
        raise RuntimeError(
            "stock command menu selected a mercenary instead of a commander: "
            f"group {group_index}, member {member_index}"
        )
    if (
        group_pointer != expected_group_pointer
        or member_pointer != expected_member_pointer
    ):
        raise RuntimeError(
            "stock command selection pointers do not match the selected "
            f"runtime record: group {group_index}, member {member_index}"
        )
    member = runtime_group_by_index(gst, group_index)["members"][0]
    cursor = (ram[CURSOR_X_ADDRESS], ram[CURSOR_Y_ADDRESS])
    coordinate = (member["x"], member["y"])
    if cursor != coordinate:
        raise RuntimeError(
            "stock command cursor does not match the selected commander: "
            f"cursor={cursor}, commander={coordinate}"
        )
    if (
        member["class_id"] == 0xFF
        or member["hp"] <= 0
        or member["acted_flag"] != 0
        or 0xFF in coordinate
    ):
        raise RuntimeError(
            "stock command menu selected a commander that cannot begin a "
            f"move: {member}"
        )
    return {
        "policy": SELECTION_POLICY,
        "player_group_count": player_group_count,
        "group_index": group_index,
        "member_index": member_index,
        "group_pointer": f"0x{group_pointer:08X}",
        "member_pointer": f"0x{member_pointer:08X}",
        "cursor": list(cursor),
        "commander_id": member["commander_id"],
        "class_id": member["class_id"],
        "runtime": member,
    }


def fixed_record_runtime_coverage(
    *,
    scenario_identity: dict[str, object],
    rom_data: bytes,
    scenario: int,
) -> dict[str, object]:
    """Summarize structural fixed/event coverage without inflating UI claims."""
    fixed = scenario_identity.get("fixed_record_layout")
    if not isinstance(fixed, dict):
        raise RuntimeError("scenario identity lacks fixed-record runtime coverage")
    records = fixed.get("records")
    if (
        fixed.get("status") != "pass"
        or fixed.get("mismatch_count") != 0
        or not isinstance(records, list)
    ):
        raise RuntimeError("fixed-record runtime identity did not pass")

    reference_data = matrix.DEFAULT_REFERENCE_ROM.read_bytes()
    reference_sha256 = hashlib.sha256(reference_data).hexdigest()
    if reference_sha256 != REFERENCE_ROM_SHA256:
        raise RuntimeError(
            "Japanese reference ROM identity changed: "
            f"{reference_sha256} != {REFERENCE_ROM_SHA256}"
        )
    model = matrix.read_scenario(rom_data, reference_data, scenario)
    if len(records) != int(model["record_count"]):
        raise RuntimeError("fixed-record runtime coverage count differs from release")
    expected_indexes = list(range(int(model["record_count"])))
    if [row.get("fixed_record_index") for row in records] != expected_indexes:
        raise RuntimeError("fixed-record runtime coverage order differs from release")
    if any(row.get("protected_mismatches") for row in records):
        raise RuntimeError("fixed-record runtime coverage contains a mismatch")

    release_layout = matrix.scenario_layout(rom_data, scenario)
    release_records = rom_data[
        release_layout.records_offset:
        release_layout.records_offset
        + release_layout.record_count * FIXED_RECORD_SIZE
    ]
    reference_layout = matrix.scenario_layout(reference_data, scenario)
    reference_records = reference_data[
        reference_layout.records_offset:
        reference_layout.records_offset
        + reference_layout.record_count * FIXED_RECORD_SIZE
    ]
    side_counts: dict[str, int] = {}
    hidden_or_parked = 0
    visible = 0
    for source_row in model["records"]:
        side = f"0x{int(source_row['side_id']):02X}"
        side_counts[side] = side_counts.get(side, 0) + 1
        if (
            bool(source_row["hidden"])
            or int(source_row["x"]) == 0xFF
            or int(source_row["y"]) == 0xFF
        ):
            hidden_or_parked += 1
        else:
            visible += 1

    checked_fields = [
        "class_id",
        "name_id",
        "side_id",
        "level",
        "x",
        "y",
        "mercenaries",
    ]
    if fixed.get("checked_fields") != checked_fields:
        raise RuntimeError("fixed-record runtime checked-field contract changed")
    return {
        "status": "pass",
        "scenario": scenario,
        "release_record_count": release_layout.record_count,
        "release_records_sha256": hashlib.sha256(release_records).hexdigest(),
        "reference_record_count": reference_layout.record_count,
        "reference_records_sha256": hashlib.sha256(reference_records).hexdigest(),
        "reference_rom": relative(matrix.DEFAULT_REFERENCE_ROM),
        "reference_rom_sha256": reference_sha256,
        "runtime_records_checked": len(records),
        "runtime_checked_fields": checked_fields,
        "side_record_counts": side_counts,
        "preparation_visible_records": visible,
        "hidden_or_parked_event_records": hidden_or_parked,
        "runtime_structural_identity_asserted": True,
        "ui_surface_claims": {
            "selected_allied_real_move_and_gray_sprite": True,
            "all_fixed_and_event_record_identity_fields": True,
            "every_side_bottom_status_opened": False,
            "every_side_detail_popup_opened": False,
            "every_side_combat_animation_opened": False,
        },
        "scope_note": (
            "Every loaded fixed/event record is checked structurally against "
            "the release table. This gray run opens and moves one selected "
            "allied commander only; it does not claim per-side status, detail, "
            "or combat UI coverage."
        ),
    }


def player_runtime_coverage(
    *,
    gst: Path,
    seed_gst: Path,
    rom_data: bytes,
    scenario: int,
    manual_override: dict[str, int] | None,
) -> dict[str, object]:
    """Bind every deployed allied root record to the imported save roster."""
    commander_ids = matrix.player_commander_ids(rom_data, scenario)
    roster = {
        int(row["commander_id"]): row
        for row in matrix.manual_slot_roster(seed_gst)
    }
    if manual_override is not None:
        commander_id = int(manual_override["commander_id"])
        roster[commander_id] = {
            **roster[commander_id],
            "class_id": int(manual_override["class_id"]),
            "level": int(manual_override["level"]),
        }
    gst_data = gst.read_bytes()
    live_groups = {
        int(group["group_index"]): group
        for group in runtime_groups(gst)
    }
    rows = []
    for group_index, commander_id in enumerate(commander_ids):
        expected = roster[commander_id]
        actual = matrix.runtime_fixed_record_layout(gst_data, group_index)
        mismatches = {}
        live_group = live_groups.get(group_index)
        if not isinstance(live_group, dict):
            raise RuntimeError(
                "player runtime group is missing: "
                f"Scenario {scenario} group {group_index}"
            )
        live_root = live_group["members"][0]
        for field, expected_value in (
            ("name_id", commander_id),
            ("class_id", int(expected["class_id"])),
            ("level", int(expected["level"])),
        ):
            if actual[field] != expected_value:
                mismatches[field] = {
                    "expected": expected_value,
                    "actual": actual[field],
                }
        if (
            live_root["commander_id"] != commander_id
            or live_root["class_id"] != int(expected["class_id"])
            or live_root["acted_flag"] != 0
            or live_root["hp"] <= 0
        ):
            mismatches["live_root"] = {
                "expected": {
                    "commander_id": commander_id,
                    "class_id": int(expected["class_id"]),
                    "acted_flag": 0,
                    "hp": "positive",
                },
                "actual": live_root,
            }
        if actual["x"] == 0xFF or actual["y"] == 0xFF:
            mismatches["coordinates"] = {
                "expected": "deployed map coordinate",
                "actual": [actual["x"], actual["y"]],
            }
        row = {
            "runtime_group": group_index,
            "commander_id": commander_id,
            "expected_class_id": int(expected["class_id"]),
            "expected_level": int(expected["level"]),
            "actual": actual,
            "live_root": live_root,
            "mismatches": mismatches,
        }
        rows.append(row)
        if mismatches:
            raise RuntimeError(
                "player runtime identity mismatch: "
                f"Scenario {scenario} group {group_index} {mismatches}"
            )
    return {
        "status": "pass",
        "scenario": scenario,
        "player_runtime_groups_checked": len(rows),
        "commander_ids": commander_ids,
        "commander_class_identities": [
            {
                "commander_id": row["commander_id"],
                "class_id": row["expected_class_id"],
                "level": row["expected_level"],
            }
            for row in rows
        ],
        "all_player_runtime_identities_asserted": True,
        "checked_fields": [
            "commander_id",
            "class_id",
            "level",
            "coordinates",
            "acted_flag",
            "hp",
        ],
        "records": rows,
        "scope_note": (
            "Every deployed allied commander root record is bound to the "
            "imported save. Only the stock-selected commander is moved and "
            "has its acted gray sprite asserted."
        ),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_directions(value: str) -> list[str]:
    directions = [part.strip().lower() for part in value.split(",") if part.strip()]
    if not directions:
        raise argparse.ArgumentTypeError("at least one movement direction is required")
    invalid = [direction for direction in directions if direction not in VALID_DIRECTIONS]
    if invalid:
        raise argparse.ArgumentTypeError(
            "invalid movement direction(s): " + ", ".join(invalid)
        )
    if len(set(directions)) != len(directions):
        raise argparse.ArgumentTypeError("movement directions must not repeat")
    return directions


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "dimensions": dimensions,
    }


def enter_battle_command(
    recorder: matrix.RuntimeRecorder,
    rom: Path,
    output: Path,
) -> None:
    matrix.open_arrangement(recorder, "deploy")
    # Arrangement rows: commander, order, auto, enemy, sortie.
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.4)
    auto = recorder.capture("deployment/after_auto_deploy.png")
    if not matrix.arrangement_menu_visible(auto):
        raise RuntimeError("automatic deployment did not return to arrangement menu")
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_select.png")
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_confirm.png")
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom", str(rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay", "0.8",
            "--max-confirmations", "200",
            "--capture-prefix", str(output / "detect/command.png"),
            "--virtual-display", recorder.display,
            "--send-event",
        ]
    )


def manual_slot_arguments(
    *,
    preserve_seed_roster: bool,
    commander_id: int,
    commander_class: int,
    commander_level: int,
    commander_experience: int,
) -> list[str] | None:
    if preserve_seed_roster:
        return None
    return [
        "--manual-slot-commander-id", str(commander_id),
        "--manual-slot-level", str(commander_level),
        "--manual-slot-experience", str(commander_experience),
        "--manual-slot-class", f"0x{commander_class:02X}",
    ]


def run_direction_attempt(
    *,
    profile: str,
    scenario: int,
    rom: Path,
    seed_gst: Path,
    display: str,
    output: Path,
    runtime_root: Path,
    run_id: str,
    direction: str,
    attempt: int,
    commander_id: int,
    commander_class: int,
    commander_level: int,
    commander_experience: int,
    preserve_seed_roster: bool,
) -> dict[str, object]:
    runtime_name = (
        f"gray-acted-{profile}-s{scenario:02d}-{run_id}-"
        f"a{attempt:02d}-{direction}"
    )
    if len(runtime_name) > 120 or Path(runtime_name).name != runtime_name:
        raise ValueError("gray acted runtime name is unsafe")
    runtime_home = runtime_root / runtime_name
    recorder = matrix.RuntimeRecorder(output, display, runtime_home)
    started = time.monotonic()
    try:
        manual_slot_args = manual_slot_arguments(
            preserve_seed_roster=preserve_seed_roster,
            commander_id=commander_id,
            commander_class=commander_class,
            commander_level=commander_level,
            commander_experience=commander_experience,
        )
        scenario_identity = matrix.launch_to_preparation(
            recorder,
            rom,
            seed_gst,
            scenario,
            runtime_name,
            output,
            manual_slot_args,
        )
        recorder.capture("preparation.png")
        enter_battle_command(recorder, rom, output)
        initial_gst = recorder.save_gst("states/initial_command.gst")
        rom_data = rom.read_bytes()
        fixed_coverage = fixed_record_runtime_coverage(
            scenario_identity=scenario_identity,
            rom_data=rom_data,
            scenario=scenario,
        )
        player_coverage = player_runtime_coverage(
            gst=initial_gst,
            seed_gst=seed_gst,
            rom_data=rom_data,
            scenario=scenario,
            manual_override=(
                None
                if preserve_seed_roster
                else {
                    "commander_id": commander_id,
                    "class_id": commander_class,
                    "level": commander_level,
                }
            ),
        )
        selected = selected_player_commander(
            initial_gst,
            rom_data,
            scenario,
        )
        selected_group = int(selected["group_index"])
        selected_commander_id = int(selected["commander_id"])
        selected_class_id = int(selected["class_id"])
        active = recorder.capture("active_command.png")
        if not sequence.battle_command_menu_visible(active):
            raise RuntimeError(
                "stock command menu disappeared before the selected "
                "commander move"
            )
        active_gst = recorder.save_gst("states/active_command.gst")
        active_selected = selected_player_commander(
            active_gst,
            rom_data,
            scenario,
        )
        if active_selected["group_index"] != selected_group:
            raise RuntimeError("stock command selection changed before Move")
        before = runtime_group_by_index(
            active_gst,
            selected_group,
        )["members"][0]

        # First C chooses Move, the directional key changes the destination,
        # and the two final confirmations apply the preview and end the action.
        # Some late-scenario maps leave the command cursor on the menu for
        # an extra frame after detect-command returns.  Confirm that Move
        # actually opened before sending the direction; otherwise all four
        # directions are silently ignored and produce a false product fail.
        move_opened = False
        for retry in range(4):
            recorder.send(["c"], delay=0.8)
            probe = recorder.capture(f"transitions/move_open_retry_{retry + 1}.png")
            if not sequence.battle_command_menu_visible(probe):
                move_opened = True
                break
        if not move_opened:
            raise RuntimeError("Move command did not open after four confirmations")
        recorder.send([direction], delay=0.6)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=1.4)
        acted = recorder.capture("acted_gray.png")
        acted_gst = recorder.save_gst("states/acted_gray.gst")
        after = runtime_group_by_index(
            acted_gst,
            selected_group,
        )["members"][0]

        state = load_gst(acted_gst)
        source_record, source_sprite_id, expected_gray, source_kind = (
            expected_commander_gray_payload(
                rom_data,
                selected_commander_id,
                selected_class_id,
            )
        )
        matching_gray_ranges = []
        for start in range(0, len(state.vram) - GRAY_VRAM_BYTES + 1, 0x20):
            if state.vram[start:start + GRAY_VRAM_BYTES] != expected_gray:
                continue
            tile_start = start // 0x20
            references = [
                {
                    "tile": f"0x{tile:04X}",
                    "hits": plane_tile_hits(state, tile),
                }
                for tile in range(tile_start, tile_start + 4)
            ]
            matching_gray_ranges.append(
                {
                    "vram_start": f"0x{start:04X}",
                    "tile_start": f"0x{tile_start:04X}",
                    "plane_references": references,
                    "all_four_tiles_referenced": all(
                        row["hits"] for row in references
                    ),
                }
            )
        linked_gray_ranges = [
            row
            for row in matching_gray_ranges
            if row["all_four_tiles_referenced"]
        ]
        coordinate_changed = (before["x"], before["y"]) != (
            after["x"], after["y"]
        )
        passed = (
            before["commander_id"]
            == after["commander_id"]
            == selected_commander_id
            and before["class_id"]
            == after["class_id"]
            == selected_class_id
            and before["acted_flag"] == 0
            and after["acted_flag"] == 1
            and coordinate_changed
            and bool(linked_gray_ranges)
            and fixed_coverage["status"] == "pass"
            and player_coverage["status"] == "pass"
        )
        return {
            "status": "pass" if passed else "fail",
            "direction": direction,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "scenario_identity": scenario_identity,
            "fixed_record_runtime_coverage": fixed_coverage,
            "player_runtime_coverage": player_coverage,
            "seed_policy": (
                "preserve_exact_campaign_roster"
                if preserve_seed_roster
                else "manual_diagnostic_commander_override"
            ),
            "selection_policy": SELECTION_POLICY,
            "selected_commander": selected,
            "requested_manual_slot_commander": (
                None
                if preserve_seed_roster
                else {
                    "commander_id": commander_id,
                    "class_id": f"0x{commander_class:02X}",
                    "level": commander_level,
                    "experience": commander_experience,
                }
            ),
            "active_capture": image_report(active),
            "acted_capture": image_report(acted),
            "active_gst": relative(active_gst),
            "active_gst_sha256": sha256(active_gst),
            "acted_gst": relative(acted_gst),
            "acted_gst_sha256": sha256(acted_gst),
            "runtime_before": before,
            "runtime_after": after,
            "coordinate_changed": coordinate_changed,
            "source_record_offset": f"0x{source_record:06X}",
            "source_silhouette_id": f"0x{source_sprite_id:04X}",
            "source_kind": source_kind,
            "expected_gray_sha256": hashlib.sha256(expected_gray).hexdigest(),
            "matching_gray_ranges": matching_gray_ranges,
            "linked_gray_ranges": linked_gray_ranges,
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
    finally:
        matrix.terminate_blastem_processes(display=display)


def run_matrix(args: argparse.Namespace) -> dict[str, object]:
    output = (
        args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    )
    if output.exists():
        raise FileExistsError(f"gray acted output already exists: {output}")
    output.mkdir(parents=True)
    seed_before = {
        "path": relative(args.seed_gst),
        "sha256": sha256(args.seed_gst),
    }
    started = time.monotonic()
    attempts = []
    accepted = None
    for attempt, direction in enumerate(args.directions, 1):
        attempt_output = output / "attempts" / f"{attempt:02d}_{direction}"
        attempt_output.mkdir(parents=True)
        try:
            row = run_direction_attempt(
                profile=args.profile,
                scenario=args.scenario,
                rom=args.rom,
                seed_gst=args.seed_gst,
                display=args.display,
                output=attempt_output,
                runtime_root=args.runtime_root,
                run_id=args.run_id,
                direction=direction,
                attempt=attempt,
                commander_id=args.commander_id,
                commander_class=args.commander_class,
                commander_level=args.commander_level,
                commander_experience=args.commander_experience,
                preserve_seed_roster=args.preserve_seed_roster,
            )
        except Exception as exc:
            matrix.terminate_blastem_processes(display=args.display)
            row = {
                "status": "error",
                "direction": direction,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        attempts.append(row)
        if row["status"] == "pass":
            accepted = row
            break
    seed_after = {
        "path": relative(args.seed_gst),
        "sha256": sha256(args.seed_gst),
    }
    seed_unchanged = seed_after == seed_before
    result = {
        "schema_version": 1,
        "status": "pass" if accepted is not None and seed_unchanged else "fail",
        "profile": args.profile,
        "scenario": args.scenario,
        "commander_id": args.commander_id,
        "commander_class_id": f"0x{args.commander_class:02X}",
        "selection_policy": SELECTION_POLICY,
        "seed_policy": (
            "preserve_exact_campaign_roster"
            if args.preserve_seed_roster
            else "manual_diagnostic_commander_override"
        ),
        "seed": seed_before,
        "seed_after": seed_after,
        "seed_unchanged": seed_unchanged,
        "selected_commander": (
            accepted["selected_commander"]
            if accepted is not None
            else None
        ),
        "run_id": args.run_id,
        "rom": {
            "path": relative(args.rom),
            "sha256": sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "directions_tried": [row["direction"] for row in attempts],
        "accepted_attempt": accepted,
        "attempts": attempts,
        "acceptance_updated": False,
        "limitations": [
            "This run covers one selected allied commander's real move and gray acted sprite only.",
            "Every fixed/event runtime record is structurally checked, but per-side bottom status, detail, and combat UI are not opened by this runner.",
            "Preparation/shop surfaces and unselected commander silhouettes are separate gates.",
        ],
    }
    (output / "evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(matrix.PROFILE_ROMS), required=True)
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--commander-id", type=int, default=1)
    parser.add_argument(
        "--commander-class", type=lambda value: int(value, 0), default=1
    )
    parser.add_argument("--commander-level", type=int, default=1)
    parser.add_argument("--commander-experience", type=int, default=0)
    parser.add_argument(
        "--preserve-seed-roster",
        action="store_true",
        help=(
            "do not patch a diagnostic commander/class into the imported save; "
            "required when --seed-gst is an exact continuous-campaign input"
        ),
    )
    parser.add_argument(
        "--directions",
        type=parse_directions,
        default=list(DEFAULT_DIRECTIONS),
    )
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if not 1 <= args.commander_id <= matrix.MANUAL_SLOT_COMMANDER_COUNT:
        parser.error("--commander-id is outside the saved roster")
    if not 0 <= args.commander_class < len(builder.KOREAN_CLASS_LABELS):
        parser.error("--commander-class is outside the class table")
    result = run_matrix(args)
    print(
        f"scenario {args.scenario:02d}: {result['status']} "
        f"({','.join(result['directions_tried'])})"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
