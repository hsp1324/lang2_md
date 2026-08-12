#!/usr/bin/env python3
"""Capture the stock Scenario 22/25 hidden-commander spawn paths.

Scenario 22 uses a coordinate-only diagnostic ROM produced by
``build_late_hidden_spawn_probe_rom``.  Scenario 25 runs the release ROM
unchanged and samples every paused opening-event page, because its Dragon Lord
is visible during the opening sequence rather than at the eventual command
checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_late_hidden_spawn_probe_rom as probe_builder  # noqa: E402
from tools import run_blastem_sequence as sequence  # noqa: E402
from tools import run_gray_acted_surface_matrix as gray  # noqa: E402
from tools import run_pike_acted_surface_probe as map_probe  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_preparation_surface_parallel as parallel  # noqa: E402
from tools import verify_hard_mode_first_turn as first_turn  # noqa: E402
from tools.scenario_data import (  # noqa: E402
    FIELD_OFFSETS,
    FIXED_RECORD_SIZE,
    scenario_layout,
)
from tools.v137_release_identity import RELEASE_ROM_SHA256  # noqa: E402


DEFAULT_OUTPUT_ROOT = ROOT / "tmp/v137-late-hidden-spawn-supplement"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/v137-late-hidden-spawn-runtime"
DEFAULT_DISPLAY = ":1010"
DEFAULT_MAX_OPENING_CONFIRMATIONS = 200
CURSOR_X_ADDRESS = 0xA6DF
CURSOR_Y_ADDRESS = 0xA6E1
RUNTIME_GROUP_SCAN_COUNT = 40

EXPECTED_RELEASE_SHA256 = RELEASE_ROM_SHA256

TARGETS = {
    22: {
        "label": "Bernhardt / Emperor",
        "name_korean": "베른하르트",
        "class_korean": "엠퍼러",
        "fixed_record_index": 3,
        "name_id": 0x0E,
        "class_id": 0x4E,
        "side_id": 0x04,
        "source_coordinate": (0xFF, 0xFF),
        "reveal_coordinate": (5, 15),
        "event": {
            "event_id": "0x0F",
            "condition": "F1 spatial range",
            "trigger_offset": "0x1AAA22",
            "trigger_bounds": {"x": [7, 27], "y": [15, 24]},
            "handler_entry": "0x1AAC44",
            "spatial_phase_handler_entry": "0x1AAE78",
            "phase_boundary": "ordinary End Turn after F1 dialogue",
            "reveal_trigger_offset": "0x1AAA50",
            "reveal_dispatch_entry": "0x1AAB20",
            "reveal_handler_entry": "0x1AAEAE",
            "reveal_command_offset": "0x1AAEBA",
            "reveal_command": "0D 0E 05 0F",
        },
        "uses_diagnostic_rom": True,
        # The fresh Scenario 1 lineage intentionally carries no late-game
        # grinding.  Scenario 22's long stock enemy phase can therefore defeat
        # Elwin before control returns.  The acceptance point is the exact
        # source placement itself, sampled from runtime RAM while the event is
        # paused, rather than a later player-controlled hover.
        "require_command_hover": False,
    },
    25: {
        "label": "Imperial Commander / Dragon Lord",
        "name_korean": "제국지휘관",
        "class_korean": "드래곤로드",
        "fixed_record_index": 11,
        "name_id": 0x31,
        "class_id": 0x4B,
        "side_id": 0x04,
        "source_coordinate": (0xFF, 0xFF),
        "reveal_coordinate": (16, 11),
        "event": {
            "event_id": "opening event",
            "condition": "unconditional stock opening-event sequence",
            "opening_event_pointer_offset": "0x1B03EA",
            "opening_event_entry": "0x1B053E",
            "reveal_command_offset": "0x1B05BC",
            "reveal_command": "0D 31 10 0B",
        },
        "uses_diagnostic_rom": False,
        "require_command_hover": False,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def fixed_target(rom: bytes, scenario: int) -> dict[str, object]:
    target = TARGETS[scenario]
    layout = scenario_layout(rom, scenario)
    record_index = int(target["fixed_record_index"])
    base = layout.records_offset + record_index * FIXED_RECORD_SIZE
    record = rom[base : base + FIXED_RECORD_SIZE]
    return {
        "scenario": scenario,
        "fixed_record_index": record_index,
        "offset": f"0x{base:06X}",
        "record_sha256": hashlib.sha256(record).hexdigest(),
        "record_hex": record.hex(),
        "hidden": bool(record[0] & 0x80),
        "side_id": record[0x08],
        "level": record[FIELD_OFFSETS["level"]],
        "at_modifier": record[FIELD_OFFSETS["at"]],
        "df_modifier": record[FIELD_OFFSETS["df"]],
        "x": record[FIELD_OFFSETS["x"]],
        "y": record[FIELD_OFFSETS["y"]],
        "name_id": record[FIELD_OFFSETS["name_id"]],
        "class_id": record[FIELD_OFFSETS["class_id"]],
        "mercenaries": list(
            record[
                FIELD_OFFSETS["mercenaries"] :
                FIELD_OFFSETS["mercenaries"] + 6
            ]
        ),
    }


def validate_fixed_target(rom: bytes, scenario: int) -> dict[str, object]:
    target = TARGETS[scenario]
    record = fixed_target(rom, scenario)
    required = {
        "hidden": True,
        "side_id": int(target["side_id"]),
        "x": int(target["source_coordinate"][0]),
        "y": int(target["source_coordinate"][1]),
        "name_id": int(target["name_id"]),
        "class_id": int(target["class_id"]),
    }
    actual = {key: record[key] for key in required}
    if actual != required:
        raise ValueError(
            f"Scenario {scenario} hidden fixed target changed: "
            f"expected {required}, got {actual}"
        )
    return record


def work_ram(gst: Path) -> bytes:
    payload = gst.read_bytes()
    start = sequence.GST_WORK_RAM_FILE_OFFSET
    ram = payload[start : start + 0x10000]
    if len(ram) != 0x10000:
        raise ValueError(f"GST is missing work RAM: {gst}")
    return ram


def runtime_target(
    gst: Path,
    *,
    group_index: int,
) -> dict[str, object]:
    ram = work_ram(gst)
    base = matrix.RUNTIME_GROUP_BASE + group_index * matrix.RUNTIME_GROUP_SIZE
    group = ram[base : base + matrix.RUNTIME_GROUP_SIZE]
    if len(group) != matrix.RUNTIME_GROUP_SIZE:
        raise ValueError(f"GST is missing runtime group {group_index}: {gst}")
    members = []
    for member_index in range(7):
        start = member_index * matrix.RUNTIME_MEMBER_SIZE
        record = group[start : start + matrix.RUNTIME_MEMBER_SIZE]
        members.append(
            {
                "member_index": member_index,
                "class_id": record[0],
                "identity_id": record[1],
                "flags": record[2],
                "hp": record[3],
                "x": record[6],
                "y": record[7],
                "record_hex": record.hex(),
            }
        )
    commander = members[0]
    return {
        **commander,
        "group_index": group_index,
        "side_id": group[matrix.RUNTIME_SIDE_OFFSET],
        "level": group[matrix.RUNTIME_LEVEL_OFFSET],
        "members": members,
        "group_sha256": hashlib.sha256(group).hexdigest(),
        "group_hex": group.hex(),
    }


def runtime_spawn_target(
    gst: Path,
    *,
    scenario: int,
    template_group_index: int,
) -> dict[str, object]:
    """Resolve an event-spawned target, including stock runtime clones.

    Most placement commands update the fixed-record runtime slot in place.
    Scenario 25 instead keeps its hidden record as a template and materializes
    the Dragon Lord in an earlier free runtime group.  Prefer an exact live
    placement, then any live matching identity, and finally the untouched
    template so pre-event hidden-state checks remain deterministic.
    """
    matching = []
    target = TARGETS[scenario]
    for group_index in range(RUNTIME_GROUP_SCAN_COUNT):
        state = runtime_target(gst, group_index=group_index)
        if (
            int(state["class_id"]) == int(target["class_id"])
            and int(state["identity_id"]) == int(target["name_id"])
            and int(state["side_id"]) == int(target["side_id"])
        ):
            matching.append(state)
    exact = [state for state in matching if target_is_visible_alive(state, scenario)]
    if exact:
        return exact[0]
    live = [state for state in matching if target_has_live_identity(state, scenario)]
    if live:
        return live[0]
    return runtime_target(gst, group_index=template_group_index)


def target_is_hidden(state: dict[str, object]) -> bool:
    return (int(state["x"]), int(state["y"])) == (0xFF, 0xFF)


def target_is_visible_alive(
    state: dict[str, object],
    scenario: int,
) -> bool:
    return (
        target_has_live_identity(state, scenario)
        and (int(state["x"]), int(state["y"]))
        == tuple(TARGETS[scenario]["reveal_coordinate"])
    )


def target_has_live_identity(
    state: dict[str, object],
    scenario: int,
) -> bool:
    target = TARGETS[scenario]
    return (
        int(state["class_id"]) == int(target["class_id"])
        and int(state["identity_id"]) == int(target["name_id"])
        and int(state["side_id"]) == int(target["side_id"])
        and not (int(state["flags"]) & 0x80)
        and int(state["hp"]) > 0
        and (int(state["x"]), int(state["y"])) != (0xFF, 0xFF)
    )


def cursor_coordinate(gst: Path) -> tuple[int, int]:
    ram = work_ram(gst)
    return ram[CURSOR_X_ADDRESS], ram[CURSOR_Y_ADDRESS]


def image_record(path: Path) -> dict[str, object]:
    from PIL import Image

    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "dimensions": dimensions,
    }


def canonical_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def prepare_battle(
    recorder: matrix.RuntimeRecorder,
    output: Path,
) -> None:
    matrix.open_arrangement(recorder, "hidden_spawn")
    # Arrangement rows: commander, order, auto, enemy, sortie.
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.4)
    auto = recorder.capture("deployment/after_auto_deploy.png")
    if not matrix.arrangement_menu_visible(auto):
        raise RuntimeError("automatic deployment did not return to arrangement")
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_select.png")
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_confirm.png")


def detect_s22_initial_command(
    recorder: matrix.RuntimeRecorder,
    output: Path,
    *,
    run_rom: Path,
    group_index: int,
) -> dict[str, object]:
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom",
            str(run_rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay",
            "0.8",
            "--max-confirmations",
            "100",
            "--capture-prefix",
            str(output / "detect/initial_command.png"),
            "--virtual-display",
            recorder.display,
            "--send-event",
        ]
    )
    capture = recorder.capture("battle/initial_command.png")
    gst = recorder.save_gst("states/initial_command.gst")
    state = runtime_spawn_target(
        gst,
        scenario=22,
        template_group_index=group_index,
    )
    if not sequence.battle_command_menu_visible(capture):
        raise RuntimeError("Scenario 22 initial battle command was not visible")
    return {
        "first_visible": None,
        "command": {
            "frame": None,
            "capture": image_record(capture),
            "gst": relative(gst),
            "gst_sha256": sha256(gst),
            "target": state,
        },
        "observations": [
            {
                "frame": None,
                "capture": relative(capture),
                "capture_sha256": sha256(capture),
                "gst": relative(gst),
                "gst_sha256": sha256(gst),
                "target": state,
                "target_visible_alive": target_is_visible_alive(state, 22),
                "battle_command_visible": True,
                "detector": "screen-guided detect-command",
            }
        ],
    }


def step_opening_until_command(
    recorder: matrix.RuntimeRecorder,
    output: Path,
    *,
    scenario: int,
    group_index: int,
    max_confirmations: int,
) -> dict[str, object]:
    first_visible: dict[str, object] | None = None
    command: dict[str, object] | None = None
    observations = []
    for frame in range(max_confirmations + 1):
        frame_path = recorder.capture(f"opening/frame_{frame:03d}.png")
        gst_path = recorder.save_gst(f"states/opening_frame_{frame:03d}.gst")
        template_state = runtime_target(gst_path, group_index=group_index)
        state = runtime_spawn_target(
            gst_path,
            scenario=scenario,
            template_group_index=group_index,
        )
        visible_alive = target_is_visible_alive(state, scenario)
        command_visible = sequence.battle_command_menu_visible(frame_path)
        observations.append(
            {
                "frame": frame,
                "capture": relative(frame_path),
                "capture_sha256": sha256(frame_path),
                "gst": relative(gst_path),
                "gst_sha256": sha256(gst_path),
                "target": state,
                "target_template": template_state,
                "target_visible_alive": visible_alive,
                "battle_command_visible": command_visible,
            }
        )
        if visible_alive and first_visible is None:
            visible_capture = output / "spawn/first_visible.png"
            visible_gst = output / "states/first_visible.gst"
            canonical_copy(frame_path, visible_capture)
            canonical_copy(gst_path, visible_gst)
            first_visible = {
                "frame": frame,
                "capture": image_record(visible_capture),
                "gst": relative(visible_gst),
                "gst_sha256": sha256(visible_gst),
                "target": state,
            }
        if command_visible:
            command_capture = output / "battle/command_open.png"
            command_gst = output / "states/command_open.gst"
            canonical_copy(frame_path, command_capture)
            canonical_copy(gst_path, command_gst)
            command = {
                "frame": frame,
                "capture": image_record(command_capture),
                "gst": relative(command_gst),
                "gst_sha256": sha256(command_gst),
                "target": state,
            }
            break
        recorder.send(["c"], delay=0.8)
    if command is None:
        raise RuntimeError(
            f"Scenario {scenario} did not reach a battle command in "
            f"{max_confirmations} confirmations"
        )
    return {
        "first_visible": first_visible,
        "command": command,
        "observations": observations,
    }


def perform_s22_trigger_action(
    recorder: matrix.RuntimeRecorder,
    output: Path,
    run_rom: Path,
) -> dict[str, object]:
    """Complete one ordinary Elwin move while inside the stock F1 bounds."""
    initial_command = recorder.capture("trigger_action/initial_command.png")
    initial_gst = recorder.save_gst("states/trigger_action_initial_command.gst")
    initial_cursor = cursor_coordinate(initial_gst)
    recorder.send(["b", "b", "b"], delay=0.45)
    map_before = recorder.capture("trigger_action/map_before_elwin_select.png")
    map_before_gst = recorder.save_gst("states/trigger_action_map_before.gst")
    cursor_before = cursor_coordinate(map_before_gst)
    elwin_before = runtime_target(map_before_gst, group_index=0)
    elwin_coordinate = (int(elwin_before["x"]), int(elwin_before["y"]))
    candidate_offsets = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
    selection_attempts = []
    current_cursor = cursor_before
    before = None
    before_gst = None
    selected = None
    navigation_to_elwin = []
    for attempt, (dx, dy) in enumerate(candidate_offsets, 1):
        candidate = (elwin_coordinate[0] + dx, elwin_coordinate[1] + dy)
        navigation = map_probe.move_keys(current_cursor, candidate)
        navigation_to_elwin.extend(navigation)
        recorder.send(navigation, delay=0.12)
        time.sleep(0.5)
        recorder.send(["c"], delay=0.8)
        attempt_capture = recorder.capture(
            f"trigger_action/elwin_select_attempt_{attempt:02d}.png"
        )
        attempt_gst = recorder.save_gst(
            f"states/trigger_action_elwin_select_attempt_{attempt:02d}.gst"
        )
        attempt_cursor = cursor_coordinate(attempt_gst)
        command_visible = sequence.battle_command_menu_visible(attempt_capture)
        attempt_selected = None
        if command_visible:
            try:
                attempt_selected = gray.selected_player_commander(
                    attempt_gst,
                    run_rom.read_bytes(),
                    22,
                )
            except (RuntimeError, ValueError):
                attempt_selected = None
        selection_attempts.append(
            {
                "attempt": attempt,
                "candidate_cursor": list(candidate),
                "navigation": navigation,
                "capture": image_record(attempt_capture),
                "gst": relative(attempt_gst),
                "cursor": list(attempt_cursor),
                "command_visible": command_visible,
                "selected": attempt_selected,
            }
        )
        if (
            attempt_selected is not None
            and int(attempt_selected["group_index"]) == 0
        ):
            before = attempt_capture
            before_gst = attempt_gst
            selected = attempt_selected
            break
        recorder.send(["b", "b", "b"], delay=0.45)
        recentered = recorder.save_gst(
            f"states/trigger_action_after_failed_select_{attempt:02d}.gst"
        )
        current_cursor = cursor_coordinate(recentered)
    if before is None or before_gst is None or selected is None:
        raise RuntimeError("Scenario 22 staged Elwin command menu did not open")
    selected_cursor = cursor_coordinate(before_gst)
    # Elwin is staged immediately outside the stock rectangle at (6,17), away
    # from every source formation. Moving right crosses into (7,17), proving
    # the F1 enter-range condition rather than merely ending inside the area.
    recorder.send(["c"], delay=0.8)
    recorder.send(["right"], delay=0.6)
    recorder.send(["c"], delay=0.8)
    recorder.send(["c"], delay=1.2)
    after = recorder.capture("trigger_action/after_move_confirm.png")
    after_gst = recorder.save_gst("states/trigger_action_after_move.gst")
    cursor_after = cursor_coordinate(after_gst)
    elwin_after = runtime_target(after_gst, group_index=0)
    action_coordinate = (int(elwin_after["x"]), int(elwin_after["y"]))
    return {
        "initial_command_capture": image_record(initial_command),
        "initial_command_gst": relative(initial_gst),
        "initial_cursor": list(initial_cursor),
        "map_before_capture": image_record(map_before),
        "map_before_gst": relative(map_before_gst),
        "capture_before": image_record(before),
        "gst_before": relative(before_gst),
        "gst_before_sha256": sha256(before_gst),
        "cursor_before": list(cursor_before),
        "navigation_to_elwin": navigation_to_elwin,
        "selection_attempts": selection_attempts,
        "selected_cursor": list(selected_cursor),
        "selected_commander": selected,
        "elwin_before": elwin_before,
        "keys": ["c", "right", "c", "c"],
        "capture_after": image_record(after),
        "gst_after": relative(after_gst),
        "gst_after_sha256": sha256(after_gst),
        "cursor_after": list(cursor_after),
        "elwin_after": elwin_after,
        "action_coordinate": list(action_coordinate),
        "action_applied": (
            action_coordinate != elwin_coordinate
            and int(elwin_after["flags"]) != int(elwin_before["flags"])
        ),
        "action_remains_inside_stock_bounds": (
            7 <= action_coordinate[0] <= 27
            and 15 <= action_coordinate[1] <= 24
        ),
    }


def step_spatial_phase_and_turn_until_spawn(
    recorder: matrix.RuntimeRecorder,
    output: Path,
    *,
    scenario: int,
    group_index: int,
    max_confirmations: int,
) -> dict[str, object]:
    """Finish the F1 phase, end the turn, then observe the stock reveal.

    The handler reached directly by the F1 condition ends at opcode ``18 FF``.
    Bernhardt's ``0D 0E 05 0F`` placement belongs to the following stock event
    entry, so repeatedly confirming on the returned player map merely opens an
    ordinary unit panel.  Probe for a real Start menu to prove map control has
    returned, choose the untouched End Turn row, and only then sample the next
    event phase.
    """
    first_visible: dict[str, object] | None = None
    spatial_observations = []
    start_menu: dict[str, object] | None = None
    for frame in range(max_confirmations + 1):
        frame_path = recorder.capture(f"spatial_phase/frame_{frame:03d}.png")
        gst_path = recorder.save_gst(
            f"states/spatial_phase_frame_{frame:03d}.gst"
        )
        template_state = runtime_target(gst_path, group_index=group_index)
        state = runtime_spawn_target(
            gst_path,
            scenario=scenario,
            template_group_index=group_index,
        )
        visible_alive = target_is_visible_alive(state, scenario)
        command_visible = sequence.battle_command_menu_visible(frame_path)
        dialogue_visible = sequence.battle_dialogue_visible(frame_path)
        map_visible = sequence.battle_map_surface_visible(frame_path)
        spatial_observations.append(
            {
                "frame": frame,
                "capture": relative(frame_path),
                "capture_sha256": sha256(frame_path),
                "gst": relative(gst_path),
                "gst_sha256": sha256(gst_path),
                "target": state,
                "target_template": template_state,
                "target_visible_alive": visible_alive,
                "battle_command_visible": command_visible,
                "battle_dialogue_visible": dialogue_visible,
                "battle_map_surface_visible": map_visible,
            }
        )
        if visible_alive and first_visible is None:
            visible_capture = output / "spawn/first_visible.png"
            visible_gst = output / "states/first_visible.gst"
            canonical_copy(frame_path, visible_capture)
            canonical_copy(gst_path, visible_gst)
            first_visible = {
                "frame": frame,
                "capture": image_record(visible_capture),
                "gst": relative(visible_gst),
                "gst_sha256": sha256(visible_gst),
                "target": state,
            }
        if map_visible and not dialogue_visible and not command_visible:
            recorder.send(["start"], delay=0.9)
            menu_capture = recorder.capture(
                f"spatial_phase/start_probe_{frame:03d}.png"
            )
            if first_turn.start_menu_visible(menu_capture):
                menu_gst = recorder.save_gst("states/spatial_phase_start_menu.gst")
                start_menu = {
                    "frame": frame,
                    "capture": image_record(menu_capture),
                    "gst": relative(menu_gst),
                    "gst_sha256": sha256(menu_gst),
                    "target": runtime_spawn_target(
                        menu_gst,
                        scenario=scenario,
                        template_group_index=group_index,
                    ),
                }
                break
            # Start is ignored while a camera/event transition owns control.
            # B safely normalizes any incidental selection before the next
            # source-event confirmation.
            recorder.send(["b"], delay=0.45)
        recorder.send(["c"], delay=0.8)
    if start_menu is None:
        raise RuntimeError(
            "Scenario 22 F1 event did not return to a controllable battle map"
        )

    recorder.send(["down", "down", "down", "down"], delay=0.45)
    recorder.send(["c"], delay=1.4)
    end_turn_capture = recorder.capture("turn_transition/after_end_turn.png")
    end_turn_gst = recorder.save_gst("states/after_end_turn.gst")
    transition_observations = []
    for frame in range(max_confirmations + 1):
        frame_path = recorder.capture(
            f"turn_transition/frame_{frame:03d}.png"
        )
        gst_path = recorder.save_gst(
            f"states/turn_transition_frame_{frame:03d}.gst"
        )
        template_state = runtime_target(gst_path, group_index=group_index)
        state = runtime_spawn_target(
            gst_path,
            scenario=scenario,
            template_group_index=group_index,
        )
        visible_alive = target_is_visible_alive(state, scenario)
        command_visible = sequence.battle_command_menu_visible(frame_path)
        dialogue_visible = sequence.battle_dialogue_visible(frame_path)
        map_visible = sequence.battle_map_surface_visible(frame_path)
        transition_observations.append(
            {
                "frame": frame,
                "capture": relative(frame_path),
                "capture_sha256": sha256(frame_path),
                "gst": relative(gst_path),
                "gst_sha256": sha256(gst_path),
                "target": state,
                "target_template": template_state,
                "target_visible_alive": visible_alive,
                "battle_command_visible": command_visible,
                "battle_dialogue_visible": dialogue_visible,
                "battle_map_surface_visible": map_visible,
            }
        )
        if visible_alive and first_visible is None:
            visible_capture = output / "spawn/first_visible.png"
            visible_gst = output / "states/first_visible.gst"
            canonical_copy(frame_path, visible_capture)
            canonical_copy(gst_path, visible_gst)
            first_visible = {
                "frame": frame,
                "capture": image_record(visible_capture),
                "gst": relative(visible_gst),
                "gst_sha256": sha256(visible_gst),
                "target": state,
            }
            # Stop at the first exact placement.  Continuing through the long
            # source enemy phase would test the deliberately under-levelled
            # Scenario 1 seed rather than the hidden-spawn contract, and can
            # legitimately end in GAME OVER before player control returns.
            break
        recorder.send(["c"], delay=0.8)
    if first_visible is None:
        raise RuntimeError(
            "Scenario 22 Bernhardt did not appear after the stock F1 phase "
            "and ordinary End Turn"
        )
    return {
        "first_visible": first_visible,
        "acceptance_checkpoint": first_visible,
        "spatial_phase_observations": spatial_observations,
        "spatial_phase_start_menu": start_menu,
        "end_turn": {
            "keys": ["down", "down", "down", "down", "c"],
            "normal_start_menu_path": True,
            "capture": image_record(end_turn_capture),
            "gst": relative(end_turn_gst),
            "gst_sha256": sha256(end_turn_gst),
        },
        "turn_transition_observations": transition_observations,
    }


def hover_target_if_present(
    recorder: matrix.RuntimeRecorder,
    output: Path,
    *,
    scenario: int,
    group_index: int,
    command: dict[str, object],
) -> dict[str, object]:
    state = command["target"]
    if not target_has_live_identity(state, scenario):
        return {
            "applicable": False,
            "reason": (
                "stock target is opening-event transient and is hidden again "
                "before the player command checkpoint"
            ),
            "target_at_command": state,
        }
    if bool(command.get("command_menu_open", True)):
        recorder.send(["b"], delay=0.8)
    before = recorder.capture("battle/before_target_hover.png")
    before_gst = recorder.save_gst("states/before_target_hover.gst")
    cursor_before = cursor_coordinate(before_gst)
    destination = (int(state["x"]), int(state["y"]))
    navigation = map_probe.move_keys(cursor_before, destination)
    recorder.send(navigation, delay=0.18)
    time.sleep(0.8)
    hover = recorder.capture("battle/target_hover.png")
    hover_gst = recorder.save_gst("states/target_hover.gst")
    cursor_after = cursor_coordinate(hover_gst)
    target_after = runtime_target(
        hover_gst,
        group_index=int(state["group_index"]),
    )
    return {
        "applicable": True,
        "before_capture": image_record(before),
        "before_gst": relative(before_gst),
        "cursor_before": list(cursor_before),
        "navigation": navigation,
        "hover_capture": image_record(hover),
        "hover_gst": relative(hover_gst),
        "hover_gst_sha256": sha256(hover_gst),
        "cursor_after": list(cursor_after),
        "target_coordinate": list(destination),
        "cursor_matches_target": cursor_after == destination,
        "target_after_hover": target_after,
        "target_unchanged_by_hover": target_after["group_hex"] == state["group_hex"],
    }


def run_scenario(
    recorder: matrix.RuntimeRecorder,
    args: argparse.Namespace,
    output: Path,
    *,
    scenario: int,
    run_rom: Path,
) -> dict[str, object]:
    target = TARGETS[scenario]
    rom_data = run_rom.read_bytes()
    fixed = validate_fixed_target(rom_data, scenario)
    group_index = (
        matrix.player_commander_count(rom_data, scenario)
        + int(target["fixed_record_index"])
    )
    runtime_name = recorder.runtime_home.name
    expected_runtime_name = (
        f"late-hidden-{args.profile}-s{scenario:02d}-{args.run_id}"
    )
    if runtime_name != expected_runtime_name:
        raise ValueError(
            "runtime home does not match the isolated BlastEm runtime name: "
            f"{runtime_name} != {expected_runtime_name}"
        )
    identity = matrix.launch_to_preparation(
        recorder,
        run_rom,
        args.seed_gst,
        scenario,
        runtime_name,
        output,
    )
    preparation = recorder.capture("preparation.png")
    before_gst = recorder.save_gst("states/before_sortie.gst")
    before = runtime_target(before_gst, group_index=group_index)
    if not target_is_hidden(before):
        raise RuntimeError(
            f"Scenario {scenario} target is not hidden before sortie: {before}"
        )
    prepare_battle(recorder, output)
    if scenario == 22:
        opening = detect_s22_initial_command(
            recorder,
            output,
            run_rom=run_rom,
            group_index=group_index,
        )
    else:
        opening = step_opening_until_command(
            recorder,
            output,
            scenario=scenario,
            group_index=group_index,
            max_confirmations=args.max_opening_confirmations,
        )
    trigger_action = None
    post_action = None
    first_visible = opening["first_visible"]
    hover_checkpoint = opening["command"]
    if scenario == 22 and first_visible is None:
        trigger_action = perform_s22_trigger_action(recorder, output, run_rom)
        if not trigger_action["action_applied"]:
            raise RuntimeError("Scenario 22 staged Elwin move was not applied")
        if not trigger_action["action_remains_inside_stock_bounds"]:
            raise RuntimeError(
                "Scenario 22 trigger action left the stock F1 bounds"
            )
        post_action = step_spatial_phase_and_turn_until_spawn(
            recorder,
            output,
            scenario=scenario,
            group_index=group_index,
            max_confirmations=args.max_opening_confirmations,
        )
        first_visible = post_action["first_visible"]
        hover_checkpoint = post_action["acceptance_checkpoint"]
    if first_visible is None:
        raise RuntimeError(
            f"Scenario {scenario} hidden target never became visible/alive"
        )
    if bool(target["require_command_hover"]):
        hover = hover_target_if_present(
            recorder,
            output,
            scenario=scenario,
            group_index=group_index,
            command=hover_checkpoint,
        )
    else:
        hover = {
            "applicable": False,
            "reason": (
                "acceptance is the paused stock-event placement; this "
                "transient path does not require a later command hover"
            ),
            "target_at_acceptance": first_visible["target"],
        }
    first_visible_target = first_visible["target"]
    checks = {
        "target_fixed_record_has_stock_hidden_identity": (
            fixed["hidden"]
            and fixed["side_id"] == int(target["side_id"])
            and fixed["name_id"] == int(target["name_id"])
            and fixed["class_id"] == int(target["class_id"])
            and (fixed["x"], fixed["y"])
            == tuple(target["source_coordinate"])
        ),
        "target_is_hidden_before_sortie": target_is_hidden(before),
        "target_name_exact_after_stock_event": (
            int(first_visible_target["identity_id"]) == int(target["name_id"])
        ),
        "target_class_exact_after_stock_event": (
            int(first_visible_target["class_id"]) == int(target["class_id"])
        ),
        "target_side_exact_after_stock_event": (
            int(first_visible_target["side_id"]) == int(target["side_id"])
        ),
        "target_coordinate_exact_after_stock_event": (
            (int(first_visible_target["x"]), int(first_visible_target["y"]))
            == tuple(target["reveal_coordinate"])
        ),
        "target_alive_after_stock_event": (
            int(first_visible_target["hp"]) > 0
            and not (int(first_visible_target["flags"]) & 0x80)
        ),
        "target_level_matches_fixed_record": (
            int(first_visible_target["level"]) == int(fixed["level"])
        ),
        "opening_reaches_valid_battle_command": opening["command"] is not None,
        "scenario22_spatial_action_applied_or_not_applicable": (
            scenario != 22
            or (
                trigger_action is not None
                and bool(trigger_action["action_applied"])
                and bool(trigger_action["action_remains_inside_stock_bounds"])
            )
        ),
        "scenario22_phase_returned_map_control_or_not_applicable": (
            scenario != 22
            or (
                post_action is not None
                and post_action["spatial_phase_start_menu"] is not None
            )
        ),
        "scenario22_ordinary_end_turn_used_or_not_applicable": (
            scenario != 22
            or (
                post_action is not None
                and bool(post_action["end_turn"]["normal_start_menu_path"])
                and post_action["end_turn"]["keys"]
                == ["down", "down", "down", "down", "c"]
            )
        ),
        "required_command_hover_completed": (
            not bool(target["require_command_hover"])
            or (
                bool(hover.get("applicable"))
                and bool(hover.get("cursor_matches_target"))
                and bool(hover.get("target_unchanged_by_hover"))
            )
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "scenario": scenario,
        "target_contract": target,
        "fixed_template_runtime_group_index": group_index,
        "spawn_runtime_group_index": int(first_visible_target["group_index"]),
        "rom": {
            "path": relative(run_rom),
            "sha256": sha256(run_rom),
            "md_checksum": matrix.md_checksum(run_rom),
        },
        "scenario_identity": identity,
        "fixed_target": fixed,
        "preparation": image_record(preparation),
        "before_sortie_gst": relative(before_gst),
        "before_sortie_gst_sha256": sha256(before_gst),
        "before_sortie_target": before,
        "first_visible": first_visible,
        "command": opening["command"],
        "trigger_action": trigger_action,
        "post_action": post_action,
        "hover": hover,
        "opening_observations": opening["observations"],
        "checks": checks,
    }


def run_profile(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    release_hash_before = sha256(args.rom)
    seed_hash_before = sha256(args.seed_gst)
    source_hash_before = sha256(args.source_rom)
    if release_hash_before != EXPECTED_RELEASE_SHA256[args.profile]:
        raise ValueError(
            f"{args.profile} release ROM hash is not the frozen v1.3.7 "
            f"candidate: {release_hash_before}"
        )
    candidate = args.rom.read_bytes()
    source = args.source_rom.read_bytes()
    # This validates both stock reveal-command contracts before any emulator
    # process starts.
    probe, manifest = probe_builder.build_probe(candidate, source)
    s22_rom = output / "diagnostic/scenario22_spatial_trigger_probe.md"
    s22_manifest = output / "diagnostic/scenario22_spatial_trigger_probe.json"
    s22_rom.parent.mkdir(parents=True, exist_ok=True)
    s22_rom.write_bytes(probe)
    s22_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    scenario_reports = []
    try:
        for scenario, run_rom in ((22, s22_rom), (25, args.rom)):
            scenario_output = output / f"s{scenario:02d}"
            scenario_output.mkdir(parents=True, exist_ok=True)
            runtime_name = (
                f"late-hidden-{args.profile}-s{scenario:02d}-{args.run_id}"
            )
            runtime_home = (
                args.runtime_root
                / args.profile
                / args.run_id
                / runtime_name
            )
            recorder = matrix.RuntimeRecorder(
                scenario_output,
                args.display,
                runtime_home,
            )
            try:
                report = run_scenario(
                    recorder,
                    args,
                    scenario_output,
                    scenario=scenario,
                    run_rom=run_rom,
                )
                report["captures"] = recorder.captures
                report["actions"] = recorder.actions
                (scenario_output / "evidence.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                scenario_reports.append(report)
            finally:
                matrix.terminate_blastem_processes(display=args.display)
        release_hash_after = sha256(args.rom)
        seed_hash_after = sha256(args.seed_gst)
        source_hash_after = sha256(args.source_rom)
        checks = {
            "scenario22_pass": scenario_reports[0]["status"] == "pass",
            "scenario25_pass": scenario_reports[1]["status"] == "pass",
            "release_rom_unchanged": release_hash_before == release_hash_after,
            "seed_gst_unchanged": seed_hash_before == seed_hash_after,
            "japanese_source_rom_unchanged": source_hash_before == source_hash_after,
            "scenario22_derivative_target_record_unchanged": bool(
                manifest["target_fixed_record_unchanged"]
            ),
            "scenario22_stock_trigger_handlers_unchanged": bool(
                manifest["stock_trigger_and_handlers_unchanged"]
            ),
            "scenario25_runs_unmodified_release_rom": (
                scenario_reports[1]["rom"]["sha256"] == release_hash_before
            ),
        }
        result = {
            "schema_version": 1,
            "status": "pass" if all(checks.values()) else "fail",
            "profile": args.profile,
            "run_id": args.run_id,
            "display": args.display,
            "virtual_display_is_isolated": parallel.display_number(args.display)
            >= parallel.MIN_ISOLATED_DISPLAY_NUMBER,
            "release_rom": {
                "path": relative(args.rom),
                "sha256_before": release_hash_before,
                "sha256_after": release_hash_after,
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "seed_gst": {
                "path": relative(args.seed_gst),
                "sha256_before": seed_hash_before,
                "sha256_after": seed_hash_after,
            },
            "japanese_source_rom": {
                "path": relative(args.source_rom),
                "sha256_before": source_hash_before,
                "sha256_after": source_hash_after,
            },
            "scenario22_diagnostic": {
                "rom": relative(s22_rom),
                "manifest": relative(s22_manifest),
                **manifest,
            },
            "scenarios": scenario_reports,
            "checks": checks,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "acceptance_updated": False,
            "evidence_scope": (
                "supplemental preflight; the final gate must rerun from its "
                "own fresh per-profile lineage"
            ),
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=tuple(EXPECTED_RELEASE_SHA256),
        required=True,
    )
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, required=True)
    parser.add_argument(
        "--source-rom",
        type=Path,
        default=probe_builder.DEFAULT_SOURCE_ROM,
    )
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument(
        "--max-opening-confirmations",
        type=int,
        default=DEFAULT_MAX_OPENING_CONFIRMATIONS,
    )
    args = parser.parse_args()
    for name in (
        "rom",
        "seed_gst",
        "source_rom",
        "xvfb",
        "xvfb_library_path",
        "output_root",
        "runtime_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    parallel.display_number(args.display)
    if not 1 <= args.max_opening_confirmations <= 300:
        parser.error("--max-opening-confirmations must be 1..300")
    for label, path in (
        ("release ROM", args.rom),
        ("seed GST", args.seed_gst),
        ("Japanese source ROM", args.source_rom),
        ("Xvfb", args.xvfb),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    return args


def main() -> int:
    args = parse_args()
    result = run_profile(args)
    print(
        f"{result['status']}: {args.profile} Scenario 22 Bernhardt and "
        "Scenario 25 Dragon Lord stock hidden-spawn paths"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
