#!/usr/bin/env python3
# ruff: noqa: E402
"""Bounded fresh-boot Scenario 1 tactical automation prototype.

This probe intentionally does much less than a campaign revalidation.  It
starts the exact supplied ROM with an empty isolated HOME, enters a genuinely
new Scenario 1, and drives only stock controller UI.  It moves Elwin toward
Bald, commits Standby, ends the turn, lets the stock enemy AI run, and proves
that Turn 2 is playable.  GST files are created only as read-only evidence;
they are never supplied to BlastEm or edited.

The result is a feasibility gate for a future tactical player, not evidence
that Scenario 1 (or the full campaign) was cleared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import run_gray_acted_surface_matrix as gray
from tools import run_hard_s1_movement_regression as movement
from tools import run_legacy_5a_runestone_release_matrix as legacy
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as parallel
from tools import verify_hard_mode_first_turn as first_turn
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


DEFAULT_ROM = RELEASE_ROM_PATHS["pure"]
DEFAULT_EXPECTED_ROM_SHA256 = RELEASE_ROM_SHA256["pure"]
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/s1-natural-ui-prototype"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/s1-natural-ui-prototype-runtime"
DEFAULT_DISPLAY = ":985"

SCENARIO = 1
ELWIN_GROUP = 0
ELWIN_MEMBER = 0
ELWIN_COMMANDER_ID = 1
ELWIN_CLASS_ID = 0x01
BALD_GROUP = 10
BALD_MEMBER = 0
BALD_NAME_ID = 0x12
BALD_CLASS_ID = 0x2E
HOSTILE_GROUPS = tuple(range(10, 14))

# These are forbidden launch mechanisms, not forbidden substrings in prose.
# The fresh emulator command is validated token-by-token before it is run.
FORBIDDEN_LAUNCH_TOKENS = frozenset({
    "-s",
    "--manual-slot-gst",
    "--manual-slot-srm",
    "--manual-slot-copy-from",
})

TURN2_STABLE_FRAME_COUNT = 2
DIALOGUE_STABLE_CHANGE_RATIO = 0.005
DIALOGUE_PAGE_CHANGE_RATIO = 0.02
DIALOGUE_CONFIRM_RETRY_FRAMES = 3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def file_report(path: Path) -> dict[str, object]:
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def validate_run_id(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value) is None:
        raise argparse.ArgumentTypeError("run ID contains unsafe characters")
    return value


def validate_sha256(value: str) -> str:
    normalized = value.lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise argparse.ArgumentTypeError("expected one SHA-256 digest")
    return normalized


def require_isolated_display(display: str) -> None:
    match = re.fullmatch(r":(\d+)(?:\.\d+)?", display)
    if match is None or int(match.group(1)) < 100:
        raise ValueError(
            "fresh Scenario 1 prototype requires a high-numbered isolated "
            f"Xvfb display, got {display!r}"
        )


def fresh_launch_command(
    *,
    rom: Path,
    runtime_name: str,
    runtime_root: Path,
    display: str,
    initial_delay: float,
) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "tools/run_blastem_sequence.py"),
        "scenario",
        "--rom",
        str(rom),
        "--runtime-name",
        runtime_name,
        "--runtime-root",
        str(runtime_root),
        "--initial-delay",
        str(initial_delay),
        "--virtual-display",
        display,
        "--replace-existing",
        "--send-event",
    ]
    validate_fresh_launch_command(command)
    return command


def validate_fresh_launch_command(command: Iterable[str]) -> None:
    argv = list(command)
    forbidden = sorted(FORBIDDEN_LAUNCH_TOKENS.intersection(argv))
    if forbidden:
        raise ValueError(f"fresh launch contains forbidden input: {forbidden}")
    if "scenario" not in argv or "--replace-existing" not in argv:
        raise ValueError("fresh launch must use the new-game Scenario 1 route")


def manhattan(first: tuple[int, int], second: tuple[int, int]) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def choose_advance_destination(
    *,
    reachable: Iterable[Iterable[int]],
    origin: tuple[int, int],
    occupied: set[tuple[int, int]],
    objective: tuple[int, int],
    hostiles: set[tuple[int, int]],
    require_safe_standby: bool,
) -> tuple[int, int]:
    """Pick a live-overlay cell that makes strict progress toward Bald."""
    return advance_destination_candidates(
        reachable=reachable,
        origin=origin,
        occupied=occupied,
        objective=objective,
        hostiles=hostiles,
        require_safe_standby=require_safe_standby,
    )[0]


def advance_destination_candidates(
    *,
    reachable: Iterable[Iterable[int]],
    origin: tuple[int, int],
    occupied: set[tuple[int, int]],
    objective: tuple[int, int],
    hostiles: set[tuple[int, int]],
    require_safe_standby: bool,
) -> list[tuple[int, int]]:
    """Order logical candidates; live orange-cursor checks choose the winner."""
    candidates = {
        (int(row[0]), int(row[1]))
        for row in reachable
        if len(tuple(row)) == 2
    }
    candidates.discard(origin)
    candidates.difference_update(occupied)
    if require_safe_standby:
        candidates = {
            coordinate
            for coordinate in candidates
            if all(manhattan(coordinate, hostile) > 1 for hostile in hostiles)
        }
    origin_distance = manhattan(origin, objective)
    candidates = {
        coordinate
        for coordinate in candidates
        if manhattan(coordinate, objective) < origin_distance
    }
    if not candidates:
        raise RuntimeError(
            "live Move overlay has no unoccupied safe cell that advances "
            f"from {origin} toward Bald at {objective}"
        )
    return sorted(
        candidates,
        key=lambda coordinate: (
            manhattan(coordinate, objective),
            min(
                (manhattan(coordinate, hostile) for hostile in hostiles),
                default=0xFFFF,
            ),
            coordinate,
        ),
    )


def live_member(
    gst: Path,
    group_index: int,
    member_index: int,
) -> dict[str, int]:
    member = movement.runtime_group(gst, group_index)["members"][member_index]
    return {
        "group_index": group_index,
        "member_index": member_index,
        "class_id": int(member["class_id"]),
        "name_id": int(member["name_id"]),
        "acted_flag": int(member["acted_flag"]),
        "hp": int(member["hp"]),
        "x": int(member["x"]),
        "y": int(member["y"]),
    }


def live_units(
    gst: Path,
    groups: Iterable[int],
) -> list[dict[str, int]]:
    rows = []
    for group_index in groups:
        group = movement.runtime_group(gst, group_index)
        for member in group["members"]:
            row = {
                "group_index": group_index,
                "member_index": int(member["member_index"]),
                "class_id": int(member["class_id"]),
                "name_id": int(member["name_id"]),
                "acted_flag": int(member["acted_flag"]),
                "hp": int(member["hp"]),
                "x": int(member["x"]),
                "y": int(member["y"]),
            }
            if (
                row["class_id"] != 0xFF
                and row["hp"] > 0
                and 0 <= row["x"] < 64
                and 0 <= row["y"] < 64
            ):
                rows.append(row)
    return rows


def unit_delta(
    before: Iterable[dict[str, int]],
    after: Iterable[dict[str, int]],
) -> list[dict[str, object]]:
    before_by_key = {
        (row["group_index"], row["member_index"]): row for row in before
    }
    after_by_key = {
        (row["group_index"], row["member_index"]): row for row in after
    }
    rows = []
    for key in sorted(before_by_key.keys() | after_by_key.keys()):
        left = before_by_key.get(key)
        right = after_by_key.get(key)
        if left != right:
            rows.append({
                "group_index": key[0],
                "member_index": key[1],
                "before": left,
                "after": right,
            })
    return rows


def fingerprint_change_ratio(left: bytes, right: bytes) -> float:
    """Return the normalized bit change between two dialogue text masks."""
    if len(left) != len(right) or not left:
        raise ValueError("dialogue fingerprints must have equal non-zero size")
    return sum(a != b for a, b in zip(left, right)) / len(left)


class DialoguePageTracker:
    """Fail-closed dialogue stability and page-advance state machine."""

    def __init__(
        self,
        *,
        stable_frames: int = TURN2_STABLE_FRAME_COUNT,
        stable_change_ratio: float = DIALOGUE_STABLE_CHANGE_RATIO,
        page_change_ratio: float = DIALOGUE_PAGE_CHANGE_RATIO,
        retry_frames: int = DIALOGUE_CONFIRM_RETRY_FRAMES,
    ) -> None:
        if stable_frames < 2:
            raise ValueError("dialogue stability needs at least two frames")
        if not 0 <= stable_change_ratio < page_change_ratio <= 1:
            raise ValueError("dialogue change thresholds are inconsistent")
        if retry_frames < 1:
            raise ValueError("dialogue confirmation retry needs one frame")
        self.stable_frames = stable_frames
        self.stable_change_ratio = stable_change_ratio
        self.page_change_ratio = page_change_ratio
        self.retry_frames = retry_frames
        self.candidate: bytes | None = None
        self.stable_count = 0
        self.confirmed: bytes | None = None
        self.waiting_for_advance = False
        self.unchanged_after_confirmation = 0
        self.page_advance_count = 0

    def observe_dialogue(self, fingerprint: bytes) -> str:
        if not fingerprint:
            raise ValueError("dialogue fingerprint cannot be empty")
        if self.waiting_for_advance:
            if self.confirmed is None:
                raise RuntimeError("dialogue tracker lost confirmed page")
            change = fingerprint_change_ratio(self.confirmed, fingerprint)
            if change >= self.page_change_ratio:
                self.waiting_for_advance = False
                self.unchanged_after_confirmation = 0
                self.page_advance_count += 1
                self.candidate = fingerprint
                self.stable_count = 1
                return "page_advanced_by_text_change"
            self.unchanged_after_confirmation += 1
            if self.unchanged_after_confirmation >= self.retry_frames:
                self.unchanged_after_confirmation = 0
                return "retry_confirmation"
            return "waiting_for_page_advance"

        if self.candidate is None:
            self.candidate = fingerprint
            self.stable_count = 1
            return "waiting_for_stability"
        change = fingerprint_change_ratio(self.candidate, fingerprint)
        if change <= self.stable_change_ratio:
            self.stable_count += 1
        else:
            self.candidate = fingerprint
            self.stable_count = 1
        if self.stable_count < self.stable_frames:
            return "waiting_for_stability"
        self.confirmed = fingerprint
        self.waiting_for_advance = True
        self.unchanged_after_confirmation = 0
        self.stable_count = 0
        return "confirm_stable_page"

    def observe_non_dialogue(self) -> str:
        action = "no_dialogue"
        if self.waiting_for_advance:
            self.page_advance_count += 1
            action = "page_advanced_by_dialogue_disappearance"
        self.candidate = None
        self.stable_count = 0
        self.confirmed = None
        self.waiting_for_advance = False
        self.unchanged_after_confirmation = 0
        return action


class StableSurfaceTracker:
    """Count consecutive classified frames without relying on pixel identity."""

    def __init__(self, required: int = TURN2_STABLE_FRAME_COUNT) -> None:
        if required < 2:
            raise ValueError("surface stability needs at least two frames")
        self.required = required
        self.label: str | None = None
        self.count = 0

    def observe(self, label: str) -> bool:
        if label == self.label:
            self.count += 1
        else:
            self.label = label
            self.count = 1
        return self.count >= self.required

    def reset(self) -> None:
        self.label = None
        self.count = 0


def classify_turn2_frame(path: Path) -> str:
    if sequence.game_over_visible(path):
        return "game_over"
    if sequence.title_screen_visible(path):
        return "title_screen"
    if sequence.battle_command_menu_visible(path):
        return "turn_command"
    if sequence.battle_dialogue_visible(path):
        return "dialogue"
    if sequence.battle_map_surface_visible(path):
        return "battle_map"
    return "transient"


def detect_turn2_command(
    recorder: preparation.RuntimeRecorder,
    *,
    max_checks: int,
    delay: float,
) -> dict[str, object]:
    """Advance complete dialogue pages and require a stable command surface."""
    dialogue = DialoguePageTracker()
    surfaces = StableSurfaceTracker()
    events: list[dict[str, object]] = []
    dialogue_confirmations = 0
    dialogue_confirmation_retries = 0
    map_confirmations = 0
    for step in range(max_checks + 1):
        frame = recorder.capture(f"turn2/detect_{step:03d}.png")
        classification = classify_turn2_frame(frame)
        event: dict[str, object] = {
            "screen_check": step,
            "classification": classification,
            "capture": file_report(frame),
        }
        sent_key = False
        if classification in {"game_over", "title_screen"}:
            dialogue_action = dialogue.observe_non_dialogue()
            if dialogue_action != "no_dialogue":
                event["dialogue_action"] = dialogue_action
            events.append(event)
            return {
                "endpoint": classification,
                "screen_checks": step + 1,
                "dialogue_confirmations": dialogue_confirmations,
                "dialogue_confirmation_retries": (
                    dialogue_confirmation_retries
                ),
                "dialogue_page_advances": dialogue.page_advance_count,
                "map_confirmations": map_confirmations,
                "stable_command_frames": 0,
                "events": events,
            }
        if classification == "dialogue":
            surfaces.reset()
            fingerprint = sequence.dialogue_text_fingerprint(frame)
            dialogue_action = dialogue.observe_dialogue(fingerprint)
            event["dialogue_action"] = dialogue_action
            event["dialogue_fingerprint_sha256"] = hashlib.sha256(
                fingerprint
            ).hexdigest()
            if dialogue_action in {
                "confirm_stable_page",
                "retry_confirmation",
            }:
                recorder.send(["c"], delay=delay)
                sent_key = True
                dialogue_confirmations += 1
                if dialogue_action == "retry_confirmation":
                    dialogue_confirmation_retries += 1
        else:
            dialogue_action = dialogue.observe_non_dialogue()
            if dialogue_action != "no_dialogue":
                event["dialogue_action"] = dialogue_action
            stable = surfaces.observe(classification)
            event["consecutive_surface_frames"] = surfaces.count
            if classification == "turn_command" and stable:
                events.append(event)
                return {
                    "endpoint": "turn_command",
                    "screen_checks": step + 1,
                    "dialogue_confirmations": dialogue_confirmations,
                    "dialogue_confirmation_retries": (
                        dialogue_confirmation_retries
                    ),
                    "dialogue_page_advances": dialogue.page_advance_count,
                    "map_confirmations": map_confirmations,
                    "stable_command_frames": surfaces.count,
                    "events": events,
                }
            if classification == "battle_map" and stable:
                # Enemy movement ignores C.  Once the player map is idle, the
                # same stock input dismisses TURN and opens a commander menu.
                recorder.send(["c"], delay=delay)
                sent_key = True
                map_confirmations += 1
                surfaces.reset()
        events.append(event)
        if not sent_key and step < max_checks:
            time.sleep(delay)
    raise RuntimeError(
        "Turn 2 command was not detected after stable dialogue/page tracking: "
        f"checks={max_checks + 1}, dialogue_confirms={dialogue_confirmations}, "
        f"page_advances={dialogue.page_advance_count}, "
        f"map_confirms={map_confirmations}"
    )


def require_exact_rom(
    rom: Path,
    expected: str,
    phase: str,
    checkpoints: list[dict[str, str]],
) -> None:
    actual = sha256(rom)
    checkpoints.append({"phase": phase, "sha256": actual})
    if actual != expected:
        raise RuntimeError(
            f"{phase}: exact ROM changed: expected {expected}, got {actual}"
        )


def launch_fresh_s1_to_command(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    runtime_name: str,
    runtime_root: Path,
    output: Path,
    initial_delay: float,
    max_confirmations: int,
) -> dict[str, object]:
    command = fresh_launch_command(
        rom=rom,
        runtime_name=runtime_name,
        runtime_root=runtime_root,
        display=recorder.display,
        initial_delay=initial_delay,
    )
    recorder.run_command(command)
    recorder.run_command([
        sys.executable,
        str(ROOT / "tools/run_blastem_sequence.py"),
        "detect-prep",
        "--rom",
        str(rom),
        "--no-launch",
        "--confirmation-delay",
        "0.8",
        "--max-confirmations",
        str(max_confirmations),
        "--capture-prefix",
        str(output / "briefing/detect.png"),
        "--virtual-display",
        recorder.display,
        "--send-event",
    ])
    preparation_capture = recorder.capture("preparation/fresh.png")
    preparation_gst = recorder.save_gst("states/preparation.gst")
    gray.enter_battle_command(recorder, rom, output)
    command_capture = recorder.capture("battle/turn1/command.png")
    movement.require_command_menu(command_capture, "fresh Turn 1 Elwin")
    command_gst = recorder.save_gst("states/turn1/command.gst")
    movement.selected_runtime_pointer_report(
        command_gst,
        expected_group_index=ELWIN_GROUP,
        expected_member_index=ELWIN_MEMBER,
    )
    if movement.turn_counter(command_gst) != 1:
        raise RuntimeError("fresh Scenario 1 did not reach Turn 1")
    return {
        "launcher_argv": command,
        "preparation_capture": file_report(preparation_capture),
        "preparation_gst": file_report(preparation_gst),
        "command_capture": file_report(command_capture),
        "command_gst": file_report(command_gst),
    }


def move_elwin_toward_bald_and_standby(
    recorder: preparation.RuntimeRecorder,
    *,
    command_gst: Path,
) -> dict[str, object]:
    elwin_before = live_member(command_gst, ELWIN_GROUP, ELWIN_MEMBER)
    bald_before = live_member(command_gst, BALD_GROUP, BALD_MEMBER)
    if (
        elwin_before["name_id"] != ELWIN_COMMANDER_ID
        or elwin_before["class_id"] != ELWIN_CLASS_ID
        or elwin_before["acted_flag"] != 0
    ):
        raise RuntimeError(f"fresh Elwin identity differs: {elwin_before}")
    if (
        bald_before["name_id"] != BALD_NAME_ID
        or bald_before["class_id"] != BALD_CLASS_ID
        or bald_before["hp"] <= 0
    ):
        raise RuntimeError(f"fresh Bald objective identity differs: {bald_before}")

    origin = (elwin_before["x"], elwin_before["y"])
    objective = (bald_before["x"], bald_before["y"])
    recorder.send(["c"], delay=0.8)
    overlay_capture = recorder.capture("battle/turn1/move_overlay.png")
    overlay_gst = recorder.save_gst("states/turn1/move_overlay.gst")
    delta = movement.plane_delta(command_gst, overlay_gst)
    reach = movement.reach_coordinate_report(
        delta,
        origin,
        movement=int(movement.runtime_group(command_gst, ELWIN_GROUP)[
            "movement_plus_0x44"
        ]),
        overlay_capture=overlay_capture,
        overlay_gst=overlay_gst,
    )
    movement.movement_palette_blocks(delta)
    movement.selection_frame_cell_top_left(overlay_capture)

    occupied = movement.occupied_runtime_coordinates(command_gst)
    occupied.discard(origin)
    hostile_units = live_units(command_gst, HOSTILE_GROUPS)
    hostile_coordinates = {(row["x"], row["y"]) for row in hostile_units}
    candidates = advance_destination_candidates(
        reachable=reach["coordinates"],
        origin=origin,
        occupied=occupied,
        objective=objective,
        hostiles=hostile_coordinates,
        require_safe_standby=True,
    )
    cursor = origin
    destination = None
    destination_capture = None
    navigation: list[str] | None = None
    destination_attempts = []
    for attempt, candidate in enumerate(candidates, 1):
        navigation = movement.navigate(
            recorder, cursor, candidate, delay=0.45
        )
        cursor = candidate
        candidate_capture = recorder.capture(
            f"battle/turn1/destination_attempt_{attempt:02d}.png"
        )
        try:
            screen_cell = movement.selection_frame_cell_top_left(
                candidate_capture
            )
            valid = True
        except ValueError:
            screen_cell = None
            valid = False
        destination_attempts.append({
            "candidate": list(candidate),
            "navigation": navigation,
            "capture": file_report(candidate_capture),
            "stock_valid_orange_cursor": valid,
            "screen_cell_top_left": (
                list(screen_cell) if screen_cell is not None else None
            ),
        })
        if valid:
            destination = candidate
            destination_capture = candidate_capture
            break
    if destination is None or destination_capture is None or navigation is None:
        recorder.send(["b"], delay=0.8)
        raise RuntimeError(
            "every logical progress candidate showed the stock red-X cursor"
        )
    destination_gst = recorder.save_gst("states/turn1/destination.gst")

    recorder.send(["c"], delay=0.9)
    post_move_capture = recorder.capture("battle/turn1/post_move_menu.png")
    post_move_gst = recorder.save_gst("states/turn1/post_move_menu.gst")
    elwin_moved = live_member(post_move_gst, ELWIN_GROUP, ELWIN_MEMBER)
    if (
        (elwin_moved["x"], elwin_moved["y"]) != destination
        or elwin_moved["acted_flag"] != 0
    ):
        raise RuntimeError(f"stock Elwin Move did not commit: {elwin_moved}")

    # The candidate is deliberately non-adjacent to every hostile.  Stock
    # post-Move UI therefore begins on Standby; one C commits the action.
    recorder.send(["c"], delay=1.2)
    standby_capture = recorder.capture("battle/turn1/after_standby.png")
    standby_gst = recorder.save_gst("states/turn1/after_standby.gst")
    elwin_standby = live_member(standby_gst, ELWIN_GROUP, ELWIN_MEMBER)
    if (
        (elwin_standby["x"], elwin_standby["y"]) != destination
        or elwin_standby["acted_flag"] != 1
    ):
        raise RuntimeError(f"stock Elwin Standby did not commit: {elwin_standby}")
    before_distance = manhattan(origin, objective)
    after_distance = manhattan(destination, objective)
    if after_distance >= before_distance:
        raise RuntimeError("Elwin Move did not advance toward Bald")
    return {
        "method": "stock_move_overlay_then_standby",
        "elwin_before": elwin_before,
        "bald_before": bald_before,
        "origin": list(origin),
        "objective": list(objective),
        "distance_before": before_distance,
        "destination": list(destination),
        "distance_after": after_distance,
        "distance_reduced_by": before_distance - after_distance,
        "navigation": navigation,
        "destination_attempts": destination_attempts,
        "reachable_coordinate_count": len(reach["coordinates"]),
        "hostile_coordinates": [list(row) for row in sorted(hostile_coordinates)],
        "overlay_capture": file_report(overlay_capture),
        "overlay_gst": file_report(overlay_gst),
        "destination_capture": file_report(destination_capture),
        "destination_gst": file_report(destination_gst),
        "post_move_capture": file_report(post_move_capture),
        "post_move_gst": file_report(post_move_gst),
        "standby_capture": file_report(standby_capture),
        "standby_gst": file_report(standby_gst),
        "elwin_after_standby": elwin_standby,
    }


def advance_enemy_ai_to_turn2(
    recorder: preparation.RuntimeRecorder,
    *,
    standby_gst: Path,
    output: Path,
    max_confirmations: int,
    confirmation_delay: float,
    emulator_speed_key: str | None,
) -> dict[str, object]:
    hostiles_before = live_units(standby_gst, HOSTILE_GROUPS)
    turn_end = first_turn.select_turn_end(
        env=recorder.environment,
        display=recorder.display,
        opening_checks=max_confirmations,
        delay=confirmation_delay,
    )
    if emulator_speed_key:
        recorder.send([emulator_speed_key], delay=0.25)
    detection = detect_turn2_command(
        recorder,
        max_checks=max_confirmations,
        delay=confirmation_delay,
    )
    endpoint = str(detection["endpoint"])
    if endpoint != "turn_command":
        raise RuntimeError(f"Scenario 1 stopped before Turn 2: {endpoint}")
    turn2_capture = recorder.capture("battle/turn2/command.png")
    movement.require_command_menu(turn2_capture, "fresh Turn 2")
    turn2_gst = recorder.save_gst("states/turn2/command.gst")
    if movement.turn_counter(turn2_gst) != 2:
        raise RuntimeError(
            f"Turn 2 counter differs: {movement.turn_counter(turn2_gst)}"
        )
    elwin = live_member(turn2_gst, ELWIN_GROUP, ELWIN_MEMBER)
    if elwin["acted_flag"] != 0:
        raise RuntimeError(f"Elwin acted flag did not reset on Turn 2: {elwin}")
    hostiles_after = live_units(turn2_gst, HOSTILE_GROUPS)
    hostile_delta = unit_delta(hostiles_before, hostiles_after)
    combat = movement.retained_turn_combat_report(
        output / "turn2/detect.png",
        output / "battle/turn1_to_turn2_side_view.png",
    )
    if not hostile_delta and combat["combat_episode_count"] == 0:
        raise RuntimeError("enemy phase produced neither movement nor combat")
    bald = live_member(turn2_gst, BALD_GROUP, BALD_MEMBER)
    return {
        "turn_end": turn_end,
        "detector_endpoint": endpoint,
        "detector": detection,
        "turn2_capture": file_report(turn2_capture),
        "turn2_gst": file_report(turn2_gst),
        "turn2_elwin": elwin,
        "turn2_bald": bald,
        "hostile_unit_delta_count": len(hostile_delta),
        "hostile_unit_deltas": hostile_delta,
        "combat": combat,
    }


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    require_isolated_display(args.display)
    if args.max_confirmations < 1 or args.max_confirmations > 500:
        raise ValueError("max confirmations must be 1..500")
    if not 0.1 <= args.confirmation_delay <= 3.0:
        raise ValueError("confirmation delay must be 0.1..3.0 seconds")
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    runtime_name = f"s1-natural-{args.run_id}"
    runtime_home = args.runtime_root / runtime_name
    if runtime_home.exists():
        raise FileExistsError(
            f"fresh runtime HOME already exists: {runtime_home}"
        )
    args.output.mkdir(parents=True)
    checkpoints: list[dict[str, str]] = []
    require_exact_rom(args.rom, args.expected_rom_sha256, "before", checkpoints)
    recorder = preparation.RuntimeRecorder(
        args.output,
        args.display,
        runtime_home,
    )
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        launch = launch_fresh_s1_to_command(
            recorder,
            rom=args.rom,
            runtime_name=runtime_name,
            runtime_root=args.runtime_root,
            output=args.output,
            initial_delay=args.initial_delay,
            max_confirmations=args.max_confirmations,
        )
        require_exact_rom(
            args.rom, args.expected_rom_sha256, "turn1_command", checkpoints
        )
        process_before = legacy.live_process_identity(
            recorder, rom=args.rom, phase="turn1_command"
        )
        command_gst = args.output / "states/turn1/command.gst"
        tactical_action = move_elwin_toward_bald_and_standby(
            recorder,
            command_gst=command_gst,
        )
        require_exact_rom(
            args.rom, args.expected_rom_sha256, "after_standby", checkpoints
        )
        process_after_action = legacy.live_process_identity(
            recorder, rom=args.rom, phase="after_standby"
        )
        legacy.assert_same_live_process(process_before, process_after_action)
        turn2 = advance_enemy_ai_to_turn2(
            recorder,
            standby_gst=args.output / "states/turn1/after_standby.gst",
            output=args.output,
            max_confirmations=args.max_confirmations,
            confirmation_delay=args.confirmation_delay,
            emulator_speed_key=args.emulator_speed_key,
        )
        require_exact_rom(
            args.rom, args.expected_rom_sha256, "turn2", checkpoints
        )
        process_turn2 = legacy.live_process_identity(
            recorder, rom=args.rom, phase="turn2"
        )
        legacy.assert_same_live_process(process_before, process_turn2)

        destination = tuple(int(v) for v in tactical_action["destination"])
        bald_turn2 = turn2["turn2_bald"]
        bald_turn2_coordinate = (int(bald_turn2["x"]), int(bald_turn2["y"]))
        checks = {
            "empty_runtime_home_at_start": True,
            "new_game_launcher_has_no_state_or_sram_input": not any(
                token in FORBIDDEN_LAUNCH_TOKENS
                for token in launch["launcher_argv"]
            ),
            "same_exact_rom_every_checkpoint": all(
                row["sha256"] == args.expected_rom_sha256
                for row in checkpoints
            ),
            "one_live_process_no_savestate_restore": (
                process_before["pid"]
                == process_after_action["pid"]
                == process_turn2["pid"]
                and not any(
                    row["argv_has_savestate_restore_option"]
                    for row in (
                        process_before,
                        process_after_action,
                        process_turn2,
                    )
                )
            ),
            "elwin_moved_through_stock_overlay": (
                tuple(tactical_action["origin"]) != destination
                and tactical_action["distance_reduced_by"] > 0
            ),
            "elwin_committed_stock_standby": (
                tactical_action["elwin_after_standby"]["acted_flag"] == 1
            ),
            "enemy_ai_phase_observed": (
                turn2["hostile_unit_delta_count"] > 0
                or turn2["combat"]["combat_episode_count"] > 0
            ),
            "turn2_playable_and_elwin_reset": (
                turn2["detector_endpoint"] == "turn_command"
                and turn2["turn2_elwin"]["acted_flag"] == 0
            ),
            "bald_objective_still_live_and_trackable": (
                bald_turn2["name_id"] == BALD_NAME_ID
                and bald_turn2["class_id"] == BALD_CLASS_ID
                and bald_turn2["hp"] > 0
            ),
        }
        passed = all(checks.values())
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "classification": "bounded_mechanics_prototype_not_full_clear",
            "scope": (
                "fresh Scenario 1 actual UI: Elwin Move, Standby, stock enemy "
                "AI phase, and playable Turn 2"
            ),
            "explicit_non_claims": {
                "scenario_1_victory_proven": False,
                "bald_defeated": False,
                "full_campaign_autoplay_proven": False,
                "gst_used_as_input": False,
                "rom_or_runtime_ram_modified": False,
                "stock_cheat_used": False,
            },
            "feasibility": {
                "bounded_tactical_controller": (
                    "feasible" if passed else "not_yet_feasible"
                ),
                "victory_condition": "defeat Bald before his escape",
                "victory_controller_next_requirement": (
                    "repeat live-overlay path planning, add adjacent Attack "
                    "target selection and post-combat/result detection"
                ),
                "distance_to_live_bald_at_turn2": manhattan(
                    destination, bald_turn2_coordinate
                ),
                "assessment": (
                    "The real UI primitives and enemy-turn loop are proven, "
                    "but one safe turn is insufficient to claim a natural "
                    "clear. A fail-closed Attack/result loop remains required."
                ),
            },
            "rom": {
                **file_report(args.rom),
                "expected_sha256": args.expected_rom_sha256,
                "hash_checkpoints": checkpoints,
            },
            "runtime": {
                "display": args.display,
                "runtime_home": relative(runtime_home),
                "runtime_home_existed_before_launch": False,
                "process_checkpoints": [
                    process_before,
                    process_after_action,
                    process_turn2,
                ],
            },
            "fresh_launch": launch,
            "tactical_action": tactical_action,
            "turn2": turn2,
            "checks": checks,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "actions": recorder.actions,
        }
        evidence = args.output / "evidence.json"
        evidence.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        sequence.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument(
        "--expected-rom-sha256",
        type=validate_sha256,
        default=DEFAULT_EXPECTED_ROM_SHA256,
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
    parser.add_argument("--run-id", type=validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=6.0)
    parser.add_argument("--max-confirmations", type=int, default=220)
    parser.add_argument("--confirmation-delay", type=float, default=0.5)
    parser.add_argument(
        "--emulator-speed-key",
        choices=("", "1", "2", "3", "4"),
        default="4",
        help="optional BlastEm host speed slot used only during enemy AI",
    )
    args = parser.parse_args()
    require_isolated_display(args.display)
    for name in (
        "rom",
        "xvfb",
        "xvfb_library_path",
        "output_root",
        "runtime_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (
        ("ROM", args.rom),
        ("Xvfb", args.xvfb),
        ("Xvfb library path", args.xvfb_library_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    args.output = args.output_root / args.run_id
    result = run_probe(args)
    print(
        f"{result['status']}: fresh S1 Move/Standby/enemy AI/Turn 2 "
        f"({result['classification']})"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
