#!/usr/bin/env python3
"""Drive Scenario 27 to Bernhardt through stock UI in one live process.

This module is deliberately narrow.  It observes GST files only after normal
controller actions; it never loads one, edits tactical work RAM, or modifies a
unit's runtime HP/coordinates.  The only setup change is a declared manual-save
Elwin class/AT/DF variant applied before the exact release ROM is launched.
Every accepted movement, target, and attack is then produced by the stock UI.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image

from tools import run_blastem_sequence as sequence
from tools import run_hard_s1_movement_regression as movement
from tools import run_legacy_5a_runestone_release_matrix as legacy
from tools import run_preparation_surface_matrix as preparation
from tools import run_scenario21_result_surface as shared
from tools import verify_hard_mode_first_turn as first_turn


SCENARIO_NUMBER = 27
TURN_TWO = 2
ELWIN_GROUP = 0
ELWIN_MEMBER = 0
ELWIN_COMMANDER_ID = 1
ELWIN_SOURCE_CLASS = 0x12
ELWIN_COMBAT_CLASS = 0x22
ELWIN_LEVEL = 8
ELWIN_EXPERIENCE = 18
ELWIN_COMBAT_AT = 99
ELWIN_COMBAT_DF = 99
BERNHARDT_GROUP = 18
BERNHARDT_MEMBER = 0
BERNHARDT_CLASS = 0x4E
BERNHARDT_COMMANDER_ID = 0x0E
FULL_RUNTIME_GROUP_COUNT = legacy.RUNTIME_GROUP_COUNT
TURN_ONE_ROUTE = (
    (18, 3, 0x7C, (15, 4), (13, 4), "bernhardt_soldier"),
    (17, 3, 0x89, (15, 7), (14, 7), "central_upper_left"),
    (17, 4, 0x89, (15, 9), (16, 9), "central_upper_right"),
    (17, 0, 0x5F, (15, 8), (14, 6), "central_upper_commander"),
    (10, 3, 0x89, (15, 11), (14, 11), "central_lower_left"),
    (10, 4, 0x89, (15, 13), (16, 13), "central_lower_right"),
    (10, 0, 0x5D, (15, 12), (14, 10), "central_lower_commander"),
    (
        BERNHARDT_GROUP,
        BERNHARDT_MEMBER,
        BERNHARDT_CLASS,
        (15, 3),
        (15, 9),
        "bernhardt_turn_one",
    ),
)
ELWIN_TURN_ONE_ORIGIN = (15, 16)
ELWIN_TURN_ONE_DESTINATION = (15, 10)
RESIDUAL_PANEL_CROP = (34, 32, 98, 63)
RESIDUAL_PANEL_DARK_BLUE_RATIO = 0.45
MAX_STANDBY_CONFIRMATIONS = 2
RUNTIME_MOVEMENT_OFFSET = 0x44


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def rom_file_identity(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "sha256": sha256_bytes(path.read_bytes()),
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def live_process_checkpoint(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    phase: str,
) -> dict[str, Any]:
    checkpoint = legacy.live_process_identity(
        recorder,
        rom=rom,
        phase=phase,
    )
    checkpoint["rom_file_identity"] = rom_file_identity(rom)
    return checkpoint


def assert_same_exact_process(
    baseline: dict[str, Any],
    checkpoint: dict[str, Any],
) -> None:
    legacy.assert_same_live_process(baseline, checkpoint)
    if checkpoint["rom_file_identity"] != baseline["rom_file_identity"]:
        raise RuntimeError(
            "exact release ROM file identity changed inside one stock route: "
            f"baseline={baseline['rom_file_identity']}, "
            f"checkpoint={checkpoint['rom_file_identity']}"
        )


def manual_slot_args() -> list[str]:
    """Return the pre-launch save-only Elwin combat setup."""
    return [
        "--manual-slot-commander-id",
        str(ELWIN_COMMANDER_ID),
        "--manual-slot-level",
        str(ELWIN_LEVEL),
        "--manual-slot-experience",
        str(ELWIN_EXPERIENCE),
        "--manual-slot-expected-class",
        f"0x{ELWIN_SOURCE_CLASS:02X}",
        "--manual-slot-class",
        f"0x{ELWIN_COMBAT_CLASS:02X}",
        "--manual-slot-at",
        str(ELWIN_COMBAT_AT),
        "--manual-slot-df",
        str(ELWIN_COMBAT_DF),
    ]


def manual_slot_change_report(
    seed_gst: Path,
    live_sram: Path,
) -> dict[str, Any]:
    """Prove that pre-launch setup changes no serialized ending statistic."""
    before = preparation.manual_slot_record_from_gst(seed_gst)
    after = legacy.manual_slot_record(live_sram)
    if len(before) != len(after):
        raise RuntimeError("manual-slot source/live record size changed")
    changed = [
        offset
        for offset, (left, right) in enumerate(zip(before, after, strict=True))
        if left != right
    ]
    commander = (
        sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + (ELWIN_COMMANDER_ID - 1)
        * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    expected_changed = sorted(
        {
            commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET,
            commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET,
            commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET,
        }
    )
    if changed != expected_changed:
        raise RuntimeError(
            "manual-slot setup changed undeclared serialized bytes: "
            f"observed={changed}, expected={expected_changed}"
        )
    before_commander = {
        "class_id": before[
            commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET
        ],
        "level": before[
            commander + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
        ],
        "experience": before[
            commander + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET
        ],
        "at": before[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET],
        "df": before[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET],
    }
    after_commander = {
        "class_id": after[
            commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET
        ],
        "level": after[
            commander + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
        ],
        "experience": after[
            commander + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET
        ],
        "at": after[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET],
        "df": after[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET],
    }
    expected_before = {
        "class_id": ELWIN_SOURCE_CLASS,
        "level": ELWIN_LEVEL,
        "experience": ELWIN_EXPERIENCE,
    }
    expected_after = {
        "class_id": ELWIN_COMBAT_CLASS,
        "level": ELWIN_LEVEL,
        "experience": ELWIN_EXPERIENCE,
        "at": ELWIN_COMBAT_AT,
        "df": ELWIN_COMBAT_DF,
    }
    if any(before_commander[key] != value for key, value in expected_before.items()):
        raise RuntimeError(
            f"exact S27 seed Elwin progress changed: {before_commander}"
        )
    if after_commander != expected_after:
        raise RuntimeError(
            f"live manual-slot Elwin combat setup changed: {after_commander}"
        )
    stats_offsets = {
        commander + 0x12,
        commander + 0x13,
        commander + 0x14,
    }
    if stats_offsets & set(changed):
        raise RuntimeError("manual-slot setup changed Elwin ending statistics")
    return {
        "status": "pass",
        "method": "declared_prelaunch_manual_save_variant",
        "source_seed_gst": str(seed_gst),
        "live_sram": str(live_sram),
        "changed_offsets": changed,
        "changed_offsets_sha256": sha256_bytes(
            b"".join(offset.to_bytes(2, "big") for offset in changed)
        ),
        "before_elwin": before_commander,
        "after_elwin": after_commander,
        "level_experience_unchanged": True,
        "ending_kill_retreat_fields_unchanged": True,
        "runtime_hp_coordinate_fields_written": False,
    }


def live_occupants(
    gst: Path,
    coordinate: tuple[int, int],
) -> list[dict[str, int]]:
    """Return live occupants across the complete 40-group runtime table."""
    return [
        row
        for group in range(FULL_RUNTIME_GROUP_COUNT)
        for member in range(8)
        if (
            (row := legacy.runtime_member(gst, group, member))["class_id"]
            != 0xFF
            and row["hp"] > 0
            and (row["x"], row["y"]) == coordinate
        )
    ]


def residual_command_panel_visible(path: Path) -> bool:
    """Recognize the stock one-row `Command` panel left by the first B press."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        return False
    panel = frame.crop(RESIDUAL_PANEL_CROP)
    pixels = list(panel.getdata())
    ratio = sum(
        1
        for red, green, blue in pixels
        if (
            50 <= blue <= 180
            and red < 45
            and green < 65
            and blue > red * 2
            and blue > green * 1.8
        )
    ) / len(pixels)
    return ratio > RESIDUAL_PANEL_DARK_BLUE_RATIO


def close_unit_command_to_bare_map(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
) -> tuple[Path, dict[str, Any]]:
    """Close both the full unit menu and its optional one-row stock panel."""
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 4):
        recorder.send(["b"], delay=0.8)
        capture = recorder.capture(
            f"battle/stock_route/{phase}/close_{attempt:02d}.png"
        )
        full_command = sequence.battle_command_menu_visible(capture)
        short_command = movement.short_battle_command_menu_visible(capture)
        residual = residual_command_panel_visible(capture)
        map_visible = sequence.battle_map_surface_visible(capture)
        row = {
            "attempt": attempt,
            "capture": str(capture),
            "map_visible": map_visible,
            "full_command_visible": full_command,
            "short_command_visible": short_command,
            "residual_command_visible": residual,
        }
        attempts.append(row)
        if map_visible and not full_command and not short_command and not residual:
            gst = recorder.save_gst(
                f"states/stock_route/{phase}/bare_map.gst"
            )
            return gst, {
                "status": "pass",
                "attempts": attempts,
                "bare_map_gst": str(gst),
            }
        if residual:
            continue
        endpoint, confirmations = first_turn.run_detector(
            display=recorder.display,
            max_checks=300,
            delay=0.22,
            capture_prefix=(
                recorder.output
                / f"battle/stock_route/{phase}/queued_{attempt:02d}.png"
            ),
        )
        row["detector_endpoint"] = endpoint
        row["detector_confirmations"] = confirmations
        if endpoint != "turn_command":
            raise RuntimeError(
                f"{phase}: queued event did not return to a unit command"
            )
    raise RuntimeError(f"{phase}: stock bare map did not appear: {attempts}")


def normalize_full_turn_command(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
) -> tuple[Path, dict[str, Any]]:
    """Promote an optional one-row panel back to the full unit command."""
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 4):
        capture = recorder.capture(
            f"battle/stock_route/{phase}/command_probe_{attempt:02d}.png"
        )
        full_command = sequence.battle_command_menu_visible(capture)
        residual = residual_command_panel_visible(capture)
        attempts.append(
            {
                "attempt": attempt,
                "capture": str(capture),
                "full_command_visible": full_command,
                "residual_command_visible": residual,
            }
        )
        if full_command:
            gst = recorder.save_gst(
                f"states/stock_route/{phase}/full_command.gst"
            )
            legacy.runtime_command_selection(gst)
            return gst, {
                "status": "pass",
                "attempts": attempts,
                "full_command_gst": str(gst),
            }
        if residual:
            recorder.send(["c"], delay=0.8)
            continue
        endpoint, confirmations = first_turn.run_detector(
            display=recorder.display,
            max_checks=300,
            delay=0.22,
            capture_prefix=(
                recorder.output
                / f"battle/stock_route/{phase}/queued_{attempt:02d}.png"
            ),
        )
        attempts[-1]["detector_endpoint"] = endpoint
        attempts[-1]["detector_confirmations"] = confirmations
        if endpoint != "turn_command":
            raise RuntimeError(f"{phase}: did not return to a full command")
    raise RuntimeError(f"{phase}: full stock unit command absent: {attempts}")


def navigate_cursor(
    recorder: preparation.RuntimeRecorder,
    *,
    source: tuple[int, int],
    target: tuple[int, int],
    phase: str,
) -> tuple[dict[str, Any], Path]:
    return legacy.live_cursor_navigation(
        recorder,
        source=source,
        target=target,
        phase=f"stock_route/{phase}",
        delay=0.18,
    )


def open_stock_unit_command(
    recorder: preparation.RuntimeRecorder,
    *,
    group: int,
    member: int,
    class_id: int,
    coordinate: tuple[int, int],
    phase: str,
) -> tuple[dict[str, Any], Path]:
    recorder.send(["c"], delay=0.8)
    capture = recorder.capture(f"battle/stock_route/{phase}/command.png")
    movement.require_command_menu(capture, phase)
    gst = recorder.save_gst(f"states/stock_route/{phase}/command.gst")
    selection = legacy.runtime_command_selection(gst)
    record = selection["selected_runtime_record"]
    observed = (
        selection["selected_group_index"],
        selection["selected_member_index"],
        record["class_id"],
        record["x"],
        record["y"],
    )
    expected = (group, member, class_id, *coordinate)
    if observed != expected:
        raise RuntimeError(f"{phase}: selected runtime record {observed} != {expected}")
    return {
        "status": "pass",
        "capture": str(capture),
        "gst": str(gst),
        "selection": selection,
    }, gst


def stock_move_and_standby(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    group: int,
    member: int,
    class_id: int,
    origin: tuple[int, int],
    destination: tuple[int, int],
    phase: str,
) -> tuple[dict[str, Any], Path]:
    """Move one selected unit and require stock occupancy and Standby state."""
    before_navigation = recorder.save_gst(
        f"states/stock_route/{phase}/before_navigation.gst"
    )
    selection = legacy.runtime_selection(before_navigation)
    source = (selection["cursor_x"], selection["cursor_y"])
    origin_navigation, origin_gst = navigate_cursor(
        recorder,
        source=source,
        target=origin,
        phase=f"{phase}/origin",
    )
    origin_occupants = live_occupants(origin_gst, origin)
    if not any(
        (row["group_index"], row["member_index"]) == (group, member)
        for row in origin_occupants
    ):
        raise RuntimeError(f"{phase}: requested origin has no selected unit")
    command, command_gst = open_stock_unit_command(
        recorder,
        group=group,
        member=member,
        class_id=class_id,
        coordinate=origin,
        phase=phase,
    )
    before = legacy.runtime_member(command_gst, group, member)
    destination_before = live_occupants(command_gst, destination)
    if destination_before:
        raise RuntimeError(
            f"{phase}: requested destination occupied: {destination_before}"
        )
    ram = legacy.runtime_ram(command_gst)
    group_start = legacy.RUNTIME_GROUP_BASE + group * legacy.RUNTIME_GROUP_SIZE
    runtime_movement = ram[group_start + RUNTIME_MOVEMENT_OFFSET]
    class_movement = movement.class_record(
        rom.read_bytes(), class_id
    )[movement.CLASS_MOVEMENT_OFFSET]
    distance = abs(origin[0] - destination[0]) + abs(
        origin[1] - destination[1]
    )
    if (
        distance > runtime_movement
        or not 1 <= runtime_movement <= class_movement
    ):
        raise RuntimeError(
            f"{phase}: destination distance {distance} exceeds exact stock "
            f"movement runtime={runtime_movement}/class={class_movement}"
        )
    recorder.send(["c"], delay=0.8)
    overlay = recorder.capture(f"battle/stock_route/{phase}/move_overlay.png")
    overlay_gst = recorder.save_gst(
        f"states/stock_route/{phase}/move_overlay.gst"
    )
    overlay_delta = movement.plane_delta(command_gst, overlay_gst)
    if not overlay_delta["changed_cell_count"]:
        raise RuntimeError(f"{phase}: stock Move overlay changed no plane words")
    destination_navigation, _ = navigate_cursor(
        recorder,
        source=origin,
        target=destination,
        phase=f"{phase}/destination",
    )
    recorder.send(["c"], delay=0.8)
    moved_capture = recorder.capture(
        f"battle/stock_route/{phase}/after_move.png"
    )
    moved_gst = recorder.save_gst(
        f"states/stock_route/{phase}/after_move.gst"
    )
    moved = legacy.runtime_member(moved_gst, group, member)
    if (
        (moved["x"], moved["y"]) != destination
        or moved["defeated_flag"] != 0
        or any(
            moved[field] != before[field]
            for field in ("class_id", "name_id", "side_id", "hp")
        )
    ):
        raise RuntimeError(f"{phase}: stock Move state mismatch: {moved}")
    destination_occupants = live_occupants(moved_gst, destination)
    origin_after = live_occupants(moved_gst, origin)
    if (
        len(destination_occupants) != 1
        or (
            destination_occupants[0]["group_index"],
            destination_occupants[0]["member_index"],
        )
        != (group, member)
        or any(
            (row["group_index"], row["member_index"]) == (group, member)
            for row in origin_after
        )
    ):
        raise RuntimeError(
            f"{phase}: post-Move occupancy mismatch: "
            f"destination={destination_occupants}, origin={origin_after}"
        )
    standby_gst = moved_gst
    standby = moved
    confirmations = []
    for confirmation in range(1, MAX_STANDBY_CONFIRMATIONS + 1):
        if standby["defeated_flag"] == 1:
            break
        recorder.send(["c"], delay=0.8)
        capture = recorder.capture(
            f"battle/stock_route/{phase}/standby_{confirmation:02d}.png"
        )
        standby_gst = recorder.save_gst(
            f"states/stock_route/{phase}/standby_{confirmation:02d}.gst"
        )
        standby = legacy.runtime_member(standby_gst, group, member)
        confirmations.append(
            {
                "confirmation": confirmation,
                "capture": str(capture),
                "gst": str(standby_gst),
                "member": standby,
            }
        )
    if (
        (standby["x"], standby["y"]) != destination
        or standby["defeated_flag"] != 1
    ):
        raise RuntimeError(f"{phase}: stock Standby state mismatch: {standby}")
    return {
        "status": "pass",
        "method": "stock_command_move_overlay_destination_then_standby",
        "group": group,
        "member": member,
        "class_id": f"0x{class_id:02X}",
        "origin": list(origin),
        "destination": list(destination),
        "distance": distance,
        "runtime_movement": runtime_movement,
        "class_movement": class_movement,
        "origin_navigation": origin_navigation,
        "origin_occupants": origin_occupants,
        "command": command,
        "move_overlay_capture": str(overlay),
        "move_overlay_gst": str(overlay_gst),
        "move_overlay_plane_delta": overlay_delta,
        "destination_navigation": destination_navigation,
        "after_move_capture": str(moved_capture),
        "after_move_gst": str(moved_gst),
        "before_member": before,
        "after_move_member": moved,
        "destination_occupants": destination_occupants,
        "origin_occupants_after": origin_after,
        "standby_confirmations": confirmations,
        "after_standby_member": standby,
        "after_standby_gst": str(standby_gst),
    }, standby_gst


def toggle_all_factions(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    enable: bool,
    phase: str,
) -> tuple[dict[str, Any], Path]:
    before = recorder.save_gst(
        f"states/stock_route/{phase}/before_empty_navigation.gst"
    )
    selection = legacy.runtime_selection(before)
    source = (selection["cursor_x"], selection["cursor_y"])
    navigation, empty_gst = navigate_cursor(
        recorder,
        source=source,
        target=legacy.LIVE_CHEAT_EMPTY_CELL,
        phase=f"{phase}/empty",
    )
    occupants = live_occupants(empty_gst, legacy.LIVE_CHEAT_EMPTY_CELL)
    if occupants:
        raise RuntimeError(f"{phase}: all-factions cell occupied: {occupants}")
    if enable:
        accepted_gst, runtime, attempts = movement.activate_all_factions(
            recorder
        )
    else:
        accepted_gst, runtime, attempts = movement.deactivate_all_factions(
            recorder
        )
    expected = 1 if enable else 0
    if runtime["active_flag"] != expected:
        raise RuntimeError(f"{phase}: all-factions flag {runtime}")
    return {
        "status": "pass",
        "stock_input_sequence": movement.all_factions_static_report(
            rom.read_bytes()
        ),
        "enable": enable,
        "empty_cell": list(legacy.LIVE_CHEAT_EMPTY_CELL),
        "empty_cell_occupants": occupants,
        "navigation": navigation,
        "runtime": runtime,
        "attempts": attempts,
        "accepted_gst": str(accepted_gst),
    }, accepted_gst


def require_exact_unit(
    gst: Path,
    *,
    group: int,
    member: int,
    class_id: int,
    name_id: int,
) -> dict[str, int]:
    row = legacy.runtime_member(gst, group, member)
    if row["class_id"] != class_id or row["name_id"] != name_id or row["hp"] <= 0:
        raise RuntimeError(
            f"runtime unit identity changed for group/member {group}/{member}: {row}"
        )
    return row


def drive_to_bernhardt_target(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    seed_gst: Path,
    initial_command_gst: Path,
) -> dict[str, Any]:
    """Reach the stock Attack target in one exact-ROM BlastEm process."""
    movement.require_isolated_display(recorder.display)
    initial_process = live_process_checkpoint(
        recorder, rom=rom, phase="initial_turn_one_command"
    )
    initial_elwin = require_exact_unit(
        initial_command_gst,
        group=ELWIN_GROUP,
        member=ELWIN_MEMBER,
        class_id=ELWIN_COMBAT_CLASS,
        name_id=ELWIN_COMMANDER_ID,
    )
    initial_bernhardt = require_exact_unit(
        initial_command_gst,
        group=BERNHARDT_GROUP,
        member=BERNHARDT_MEMBER,
        class_id=BERNHARDT_CLASS,
        name_id=BERNHARDT_COMMANDER_ID,
    )
    if (initial_elwin["x"], initial_elwin["y"]) != ELWIN_TURN_ONE_ORIGIN:
        raise RuntimeError(f"Scenario 27 Elwin origin changed: {initial_elwin}")
    if (initial_bernhardt["x"], initial_bernhardt["y"]) != (15, 3):
        raise RuntimeError(
            f"Scenario 27 Bernhardt origin changed: {initial_bernhardt}"
        )
    live_sram = legacy.find_runtime_sram(recorder.runtime_home)
    save_setup = manual_slot_change_report(seed_gst, live_sram)
    bare_map, initial_close = close_unit_command_to_bare_map(
        recorder, phase="turn_one_initial"
    )
    cheat_on, active_gst = toggle_all_factions(
        recorder,
        rom=rom,
        enable=True,
        phase="turn_one_enable_all_factions",
    )
    turn_one_moves = []
    for group, member, class_id, origin, destination, label in TURN_ONE_ROUTE:
        report, _ = stock_move_and_standby(
            recorder,
            rom=rom,
            group=group,
            member=member,
            class_id=class_id,
            origin=origin,
            destination=destination,
            phase=f"turn_one/{label}",
        )
        turn_one_moves.append(report)
    cheat_off, _ = toggle_all_factions(
        recorder,
        rom=rom,
        enable=False,
        phase="turn_one_disable_all_factions",
    )
    elwin_move, turn_one_ready = stock_move_and_standby(
        recorder,
        rom=rom,
        group=ELWIN_GROUP,
        member=ELWIN_MEMBER,
        class_id=ELWIN_COMBAT_CLASS,
        origin=ELWIN_TURN_ONE_ORIGIN,
        destination=ELWIN_TURN_ONE_DESTINATION,
        phase="turn_one/elwin",
    )
    turn_one_process = live_process_checkpoint(
        recorder, rom=rom, phase="turn_one_ready"
    )
    assert_same_exact_process(initial_process, turn_one_process)
    turn_end = first_turn.select_turn_end(
        env=recorder.environment,
        display=recorder.display,
        opening_checks=500,
        delay=0.25,
    )
    endpoint, confirmations = first_turn.run_detector(
        display=recorder.display,
        max_checks=700,
        delay=0.22,
        capture_prefix=(
            recorder.output / "battle/stock_route/turn_two/detect.png"
        ),
    )
    if endpoint != "turn_command":
        raise RuntimeError(f"Scenario 27 Turn 2 endpoint changed: {endpoint}")
    turn_two_capture = recorder.capture(
        "battle/stock_route/turn_two/initial_command.png"
    )
    turn_two_gst = recorder.save_gst(
        "states/stock_route/turn_two/initial_command.gst"
    )
    turn = legacy.runtime_ram(turn_two_gst)[movement.TURN_COUNTER_OFFSET]
    turn_two_elwin = require_exact_unit(
        turn_two_gst,
        group=ELWIN_GROUP,
        member=ELWIN_MEMBER,
        class_id=ELWIN_COMBAT_CLASS,
        name_id=ELWIN_COMMANDER_ID,
    )
    turn_two_bernhardt = require_exact_unit(
        turn_two_gst,
        group=BERNHARDT_GROUP,
        member=BERNHARDT_MEMBER,
        class_id=BERNHARDT_CLASS,
        name_id=BERNHARDT_COMMANDER_ID,
    )
    if turn != TURN_TWO:
        raise RuntimeError(f"Scenario 27 did not reach Turn 2: {turn}")
    if (turn_two_elwin["x"], turn_two_elwin["y"]) != ELWIN_TURN_ONE_DESTINATION:
        raise RuntimeError(f"Turn 2 Elwin position changed: {turn_two_elwin}")
    if turn_two_elwin["hp"] >= initial_elwin["hp"]:
        raise RuntimeError(
            "enemy phase did not prove contact with moved Elwin: "
            f"before={initial_elwin}, after={turn_two_elwin}"
        )
    if (turn_two_bernhardt["x"], turn_two_bernhardt["y"]) == (15, 9):
        raise RuntimeError(
            "enemy AI did not consume Bernhardt's Turn-1 stock occupancy"
        )
    _, normalize = normalize_full_turn_command(
        recorder, phase="turn_two_initial"
    )
    _, turn_two_close = close_unit_command_to_bare_map(
        recorder, phase="turn_two_initial"
    )
    cheat_on_two, active_two_gst = toggle_all_factions(
        recorder,
        rom=rom,
        enable=True,
        phase="turn_two_enable_all_factions",
    )
    turn_two_bernhardt = require_exact_unit(
        active_two_gst,
        group=BERNHARDT_GROUP,
        member=BERNHARDT_MEMBER,
        class_id=BERNHARDT_CLASS,
        name_id=BERNHARDT_COMMANDER_ID,
    )
    turn_two_elwin = require_exact_unit(
        active_two_gst,
        group=ELWIN_GROUP,
        member=ELWIN_MEMBER,
        class_id=ELWIN_COMBAT_CLASS,
        name_id=ELWIN_COMMANDER_ID,
    )
    target_coordinate = (turn_two_elwin["x"], turn_two_elwin["y"] - 1)
    bernhardt_move, _ = stock_move_and_standby(
        recorder,
        rom=rom,
        group=BERNHARDT_GROUP,
        member=BERNHARDT_MEMBER,
        class_id=BERNHARDT_CLASS,
        origin=(turn_two_bernhardt["x"], turn_two_bernhardt["y"]),
        destination=target_coordinate,
        phase="turn_two/bernhardt",
    )
    cheat_off_two, deactivated_two_gst = toggle_all_factions(
        recorder,
        rom=rom,
        enable=False,
        phase="turn_two_disable_all_factions",
    )
    selection = legacy.runtime_selection(deactivated_two_gst)
    cursor = (selection["cursor_x"], selection["cursor_y"])
    elwin_navigation, _ = navigate_cursor(
        recorder,
        source=cursor,
        target=(turn_two_elwin["x"], turn_two_elwin["y"]),
        phase="turn_two/elwin/origin",
    )
    elwin_command, elwin_command_gst = open_stock_unit_command(
        recorder,
        group=ELWIN_GROUP,
        member=ELWIN_MEMBER,
        class_id=ELWIN_COMBAT_CLASS,
        coordinate=(turn_two_elwin["x"], turn_two_elwin["y"]),
        phase="turn_two/elwin",
    )
    recorder.send(["down"], delay=0.45)
    attack_row = recorder.capture(
        "battle/stock_route/turn_two/elwin/attack_row.png"
    )
    attack_row_gst = recorder.save_gst(
        "states/stock_route/turn_two/elwin/attack_row.gst"
    )
    if legacy.runtime_command_selection(attack_row_gst) != legacy.runtime_command_selection(
        elwin_command_gst
    ):
        raise RuntimeError("Attack row navigation changed the selected unit")
    recorder.send(["c"], delay=0.65)
    attack_overlay = recorder.capture(
        "battle/stock_route/turn_two/elwin/attack_overlay.png"
    )
    attack_overlay_gst = recorder.save_gst(
        "states/stock_route/turn_two/elwin/attack_overlay.gst"
    )
    overlay_selection = legacy.runtime_selection(attack_overlay_gst)
    if (overlay_selection["cursor_x"], overlay_selection["cursor_y"]) != (
        turn_two_elwin["x"],
        turn_two_elwin["y"],
    ):
        raise RuntimeError(
            f"stock Attack overlay cursor changed: {overlay_selection}"
        )
    target_navigation, _ = navigate_cursor(
        recorder,
        source=(turn_two_elwin["x"], turn_two_elwin["y"]),
        target=target_coordinate,
        phase="turn_two/elwin/bernhardt_target",
    )
    target_capture = recorder.capture(
        "battle/stock_route/turn_two/elwin/bernhardt_target.png"
    )
    target_gst = recorder.save_gst(
        "states/stock_route/turn_two/elwin/bernhardt_target.gst"
    )
    target_selection = legacy.runtime_selection(target_gst)
    target_bernhardt = require_exact_unit(
        target_gst,
        group=BERNHARDT_GROUP,
        member=BERNHARDT_MEMBER,
        class_id=BERNHARDT_CLASS,
        name_id=BERNHARDT_COMMANDER_ID,
    )
    if (target_selection["cursor_x"], target_selection["cursor_y"]) != target_coordinate:
        raise RuntimeError(f"Bernhardt target cursor changed: {target_selection}")
    if (target_bernhardt["x"], target_bernhardt["y"]) != target_coordinate:
        raise RuntimeError(f"Bernhardt target occupancy changed: {target_bernhardt}")
    pre_attack_process = live_process_checkpoint(
        recorder, rom=rom, phase="bernhardt_target_selected"
    )
    assert_same_exact_process(initial_process, pre_attack_process)
    return {
        "status": "pass",
        "method": "same_process_stock_move_turn_end_move_attack_target",
        "external_runtime_state_load_count": 0,
        "tactical_runtime_bytes_written": False,
        "runtime_hp_coordinate_setup_used": False,
        "initial_process": initial_process,
        "pre_attack_process": pre_attack_process,
        "manual_save_setup": save_setup,
        "initial_elwin": initial_elwin,
        "initial_bernhardt": initial_bernhardt,
        "initial_bare_map": str(bare_map),
        "initial_close": initial_close,
        "turn_one_cheat_on": cheat_on,
        "turn_one_moves": turn_one_moves,
        "turn_one_cheat_off": cheat_off,
        "elwin_turn_one_move": elwin_move,
        "turn_one_ready_gst": str(turn_one_ready),
        "turn_end": turn_end,
        "turn_two_detector_confirmations": confirmations,
        "turn_two_capture": str(turn_two_capture),
        "turn_two_gst": str(turn_two_gst),
        "turn_two_elwin": turn_two_elwin,
        "turn_two_bernhardt_after_ai": turn_two_bernhardt,
        "turn_two_command_normalization": normalize,
        "turn_two_close": turn_two_close,
        "turn_two_cheat_on": cheat_on_two,
        "bernhardt_turn_two_move": bernhardt_move,
        "turn_two_cheat_off": cheat_off_two,
        "elwin_navigation": elwin_navigation,
        "elwin_command": elwin_command,
        "attack_row_capture": str(attack_row),
        "attack_row_gst": str(attack_row_gst),
        "attack_overlay_capture": str(attack_overlay),
        "attack_overlay_gst": str(attack_overlay_gst),
        "bernhardt_target_navigation": target_navigation,
        "bernhardt_target_capture": str(target_capture),
        "bernhardt_target_gst": str(target_gst),
        "bernhardt_target_runtime": target_bernhardt,
        "target_coordinate": list(target_coordinate),
    }


def confirm_target_and_advance_battle(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    baseline_process: dict[str, Any],
    max_frames: int,
    battle_delay: float,
) -> tuple[dict[str, Any], Path]:
    """Confirm the selected target and require an ordinary stock defeat."""
    recorder.send(["c"], delay=0.25)
    frames: list[dict[str, Any]] = []
    post_battle = None
    bernhardt = None
    stop_frame = None
    for frame in range(1, max_frames + 1):
        battle = recorder.capture(
            f"battle/stock_route/ordinary_combat/advance_{frame:03d}.png"
        )
        frames.append(shared.image_report(battle))
        # Confirm stock confrontation pages one at a time.  Inspect the live
        # runtime record after each edge, and stop before any post-defeat key.
        recorder.send(["c"], delay=battle_delay)
        checkpoint = recorder.save_gst(
            f"states/stock_route/ordinary_combat/frame_{frame:03d}.gst"
        )
        member = legacy.runtime_member(
            checkpoint, BERNHARDT_GROUP, BERNHARDT_MEMBER
        )
        bernhardt = {
            "class_id": member["class_id"],
            "name_id": member["name_id"],
            "defeated_flag": member["defeated_flag"],
            "defeated": bool(member["defeated_flag"] & 0x80),
            "hp": member["hp"],
            "x": member["x"],
            "y": member["y"],
        }
        if bernhardt["hp"] == 0:
            post_battle = checkpoint
            stop_frame = frame
            break
    if post_battle is None or bernhardt is None or stop_frame is None:
        raise RuntimeError(
            f"ordinary stock Attack did not defeat Bernhardt in {max_frames} frames"
        )
    if bernhardt["hp"] != 0 or not bernhardt["defeated"]:
        raise RuntimeError(
            f"ordinary stock Attack did not defeat Bernhardt: {bernhardt}"
        )
    post_process = live_process_checkpoint(
        recorder, rom=rom, phase="post_bernhardt_defeat"
    )
    assert_same_exact_process(baseline_process, post_process)
    elwin = legacy.runtime_member(post_battle, ELWIN_GROUP, ELWIN_MEMBER)
    if elwin["hp"] <= 0 or elwin["defeated_flag"] & 0x80:
        raise RuntimeError(f"ordinary stock combat defeated Elwin: {elwin}")
    return {
        "status": "pass",
        "method": "selected_stock_attack_and_ordinary_combat",
        "battle_frames": frames,
        "stop_frame": stop_frame,
        "post_battle_gst": str(post_battle),
        "bernhardt": bernhardt,
        "elwin": elwin,
        "post_battle_process": post_process,
        "same_process": True,
    }, post_battle


def same_process_checkpoint(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    baseline_process: dict[str, Any],
    phase: str,
) -> dict[str, Any]:
    checkpoint = live_process_checkpoint(
        recorder,
        rom=rom,
        phase=phase,
    )
    assert_same_exact_process(baseline_process, checkpoint)
    return checkpoint
