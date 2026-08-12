#!/usr/bin/env python3
# ruff: noqa: E402
"""Play a fresh exact-ROM Scenario 1 to Bald defeat through stock UI only.

The emulator starts with an empty isolated HOME.  This runner hires and
deploys mercenaries through preparation menus, then issues ordinary Move,
Attack, Standby, and End Turn controller input.  GST snapshots are copied
only after the emulator creates them and are used solely to observe cursor,
unit, HP, acted, turn, and save state.  They are never edited or supplied as
emulator input.

Passing requires an ordinary attack to leave exact Bald defeated, followed by
the stock battle-result surface and a save menu whose read-only state records
Scenario 2.  Any escape, GAME OVER, ambiguous cursor, unverified damage, ROM
hash change, process replacement, or missing result/save surface fails closed.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys
import time
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import run_hard_s1_movement_regression as movement
from tools import run_legacy_5a_runestone_release_matrix as legacy
from tools import run_mounted_lord_combat_regression as mounted
from tools import run_pike_acted_surface_probe as mercenary
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as parallel
from tools import run_s1_natural_ui_prototype as prototype
from tools import run_scenario14_15_result_surface as result_surface
from tools import verify_hard_mode_first_turn as first_turn
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


DEFAULT_ROM = RELEASE_ROM_PATHS["pure"]
DEFAULT_EXPECTED_ROM_SHA256 = RELEASE_ROM_SHA256["pure"]
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/s1-natural-ui-victory"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/s1-natural-ui-victory-runtime"
DEFAULT_DISPLAY = ":986"

SCENARIO = 1
EXPECTED_SAVE_SCENARIO = 2
ELWIN_COMMANDER_ID = 1
LIANA_COMMANDER_ID = 5
ELWIN_CLASS_ID = 0x01
LIANA_CLASS_ID = 0x03
SOLDIER_CLASS_ID = 0x64
GUARDMAN_CLASS_ID = 0x6D
HIRED_PER_COMMANDER = 6
BALD_GROUP = 10
BALD_MEMBER = 0
BALD_NAME_ID = 0x12
BALD_CLASS_ID = 0x2E
PLAYER_SIDE = 1
HOSTILE_SIDE = 4
MAX_RUNTIME_GROUPS = 40
MAX_MEMBERS = 8

ROUTE_HISTORY_LIMIT = 6

FORBIDDEN_RUNTIME_INPUT_TOKENS = prototype.FORBIDDEN_LAUNCH_TOKENS | {
    "--seed-gst",
    "--reuse-runtime-state",
}


def validate_fresh_victory_launch(command: Iterable[str]) -> None:
    argv = list(command)
    forbidden = sorted(FORBIDDEN_RUNTIME_INPUT_TOKENS.intersection(argv))
    if forbidden:
        raise ValueError(f"natural victory launch contains state input: {forbidden}")
    prototype.validate_fresh_launch_command(argv)


def fresh_victory_launch_command(
    *,
    rom: Path,
    runtime_name: str,
    runtime_root: Path,
    display: str,
    initial_delay: float,
) -> list[str]:
    command = prototype.fresh_launch_command(
        rom=rom,
        runtime_name=runtime_name,
        runtime_root=runtime_root,
        display=display,
        initial_delay=initial_delay,
    )
    validate_fresh_victory_launch(command)
    return command


def runtime_unit(gst: Path, group_index: int, member_index: int) -> dict[str, int]:
    group = movement.runtime_group(gst, group_index)
    member = group["members"][member_index]
    flag = int(member["acted_flag"])
    return {
        "group_index": group_index,
        "member_index": member_index,
        "side_id": int(group["side_id"]),
        "class_id": int(member["class_id"]),
        "name_id": int(member["name_id"]),
        "raw_action_flag": flag,
        "acted": flag & 1,
        "defeated": 1 if flag & 0x80 else 0,
        "hp": int(member["hp"]),
        "x": int(member["x"]),
        "y": int(member["y"]),
    }


def unit_alive(row: dict[str, int]) -> bool:
    return (
        row["class_id"] != 0xFF
        and row["hp"] > 0
        and not row["defeated"]
        and 0 <= row["x"] < 64
        and 0 <= row["y"] < 64
    )


def units_for_side(gst: Path, side_id: int) -> list[dict[str, int]]:
    rows = []
    for group_index in range(MAX_RUNTIME_GROUPS):
        group = movement.runtime_group(gst, group_index)
        if int(group["side_id"]) != side_id:
            continue
        for member_index in range(MAX_MEMBERS):
            row = runtime_unit(gst, group_index, member_index)
            if unit_alive(row):
                rows.append(row)
    return rows


def exact_bald(gst: Path, *, require_live: bool) -> dict[str, int]:
    bald = runtime_unit(gst, BALD_GROUP, BALD_MEMBER)
    if bald["name_id"] != BALD_NAME_ID or bald["class_id"] != BALD_CLASS_ID:
        raise RuntimeError(f"Scenario 1 Bald identity changed: {bald}")
    if require_live and not unit_alive(bald):
        raise RuntimeError(f"Bald is no longer a live trackable objective: {bald}")
    return bald


def hostile_priority(row: dict[str, int]) -> tuple[int, int, int, int]:
    return (
        0 if (row["group_index"], row["member_index"]) == (BALD_GROUP, 0) else 1,
        0 if row["group_index"] == BALD_GROUP else 1,
        0 if row["member_index"] == 0 else 1,
        row["hp"],
    )


def adjacent(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return prototype.manhattan(first, second) == 1


def adjacent_hostile(
    origin: tuple[int, int],
    hostiles: Iterable[dict[str, int]],
) -> dict[str, int] | None:
    candidates = [
        row for row in hostiles if adjacent(origin, (row["x"], row["y"]))
    ]
    return min(candidates, key=hostile_priority) if candidates else None


class ReachabilityRouteMap:
    """Learn live Move-overlay connectivity and reject tactical cycles."""

    def __init__(self, limit: int = ROUTE_HISTORY_LIMIT) -> None:
        if limit < 2:
            raise ValueError("route history limit must be at least 2")
        self.limit = limit
        self.graph: dict[tuple[int, int], set[tuple[int, int]]] = {}
        self.explored_origins: set[tuple[int, int]] = set()
        self.visits: Counter[tuple[int, int]] = Counter()
        self.unit_coordinates: dict[tuple[int, int], deque[tuple[int, int]]] = {}
        self.turn_formations: deque[tuple[tuple[int, int, int, int], ...]] = deque(
            maxlen=limit
        )

    @staticmethod
    def key(row: dict[str, int]) -> tuple[int, int]:
        return row["group_index"], row["member_index"]

    def recent_for(self, row: dict[str, int]) -> tuple[tuple[int, int], ...]:
        key = self.key(row)
        history = self.unit_coordinates.get(key)
        return tuple(history) if history is not None else ()

    def observe_unit(self, row: dict[str, int]) -> None:
        key = self.key(row)
        coordinate = (row["x"], row["y"])
        history = self.unit_coordinates.setdefault(key, deque(maxlen=self.limit))
        if not history or history[-1] != coordinate:
            history.append(coordinate)
            self.visits[coordinate] += 1

    def learn_overlay(
        self,
        origin: tuple[int, int],
        reachable: Iterable[Iterable[int]],
    ) -> set[tuple[int, int]]:
        coordinates = {
            (int(row[0]), int(row[1]))
            for row in reachable
            if len(tuple(row)) == 2
        }
        if not coordinates:
            raise RuntimeError(f"live Move overlay is empty at {origin}")
        # The stock palette overlay can omit the occupied origin tile even
        # though the exact command selection and runtime record still prove
        # where the unit starts. Add only that graph node; destinations remain
        # restricted to the raw overlay set and then to the orange-cursor gate.
        self.explored_origins.add(origin)
        self.graph.setdefault(origin, set())
        for coordinate in coordinates:
            self.graph.setdefault(coordinate, set()).add(origin)
            self.graph[origin].add(coordinate)
        return coordinates

    @staticmethod
    def nearest_hostile_distance(
        coordinate: tuple[int, int],
        hostiles: Iterable[dict[str, int]],
    ) -> int:
        rows = list(hostiles)
        if not rows:
            raise RuntimeError("no live hostile remains while Bald is live")
        return min(
            prototype.manhattan(coordinate, (row["x"], row["y"]))
            for row in rows
        )

    def known_steps_to_attack(
        self,
        coordinate: tuple[int, int],
        hostiles: Iterable[dict[str, int]],
    ) -> int | None:
        targets = {
            node
            for node in self.graph
            if adjacent_hostile(node, hostiles) is not None
        }
        if not targets or coordinate not in self.graph:
            return None
        queue = deque([(coordinate, 0)])
        seen = {coordinate}
        while queue:
            node, steps = queue.popleft()
            if node in targets:
                return steps
            for following in self.graph[node]:
                if following not in seen:
                    seen.add(following)
                    queue.append((following, steps + 1))
        return None

    def progress_kind(
        self,
        *,
        origin: tuple[int, int],
        candidate: tuple[int, int],
        hostiles: Iterable[dict[str, int]],
        recent: set[tuple[int, int]],
    ) -> str | None:
        hostile_rows = list(hostiles)
        if candidate in recent:
            return None
        if adjacent_hostile(candidate, hostile_rows) is not None:
            return "attack_frontier"
        origin_steps = self.known_steps_to_attack(origin, hostile_rows)
        candidate_steps = self.known_steps_to_attack(candidate, hostile_rows)
        if candidate_steps is not None and (
            origin_steps is None or candidate_steps < origin_steps
        ):
            return "known_graph_shorter"
        if candidate not in self.explored_origins:
            return "unexplored_overlay_frontier"
        return None

    def progress_report(
        self,
        coordinate: tuple[int, int],
        hostiles: Iterable[dict[str, int]],
    ) -> dict[str, object]:
        hostile_rows = list(hostiles)
        return {
            "coordinate": list(coordinate),
            "overlay_origin_explored": coordinate in self.explored_origins,
            "known_steps_to_attack": self.known_steps_to_attack(
                coordinate, hostile_rows
            ),
            "nearest_hostile_manhattan": self.nearest_hostile_distance(
                coordinate, hostile_rows
            ),
            "visit_count": self.visits[coordinate],
            "known_graph_node_count": len(self.graph),
            "explored_overlay_origin_count": len(self.explored_origins),
        }

    def begin_turn(self, rows: Iterable[dict[str, int]], turn: int) -> None:
        live = list(rows)
        formation = tuple(sorted(
            (row["group_index"], row["member_index"], row["x"], row["y"])
            for row in live
        ))
        if formation in self.turn_formations:
            raise RuntimeError(
                f"Turn {turn}: recent player formation cycle detected"
            )
        self.turn_formations.append(formation)
        for row in live:
            self.observe_unit(row)


def tactical_destination_candidates(
    *,
    reachable: Iterable[Iterable[int]],
    origin: tuple[int, int],
    occupied: set[tuple[int, int]],
    hostiles: Iterable[dict[str, int]],
    bald: tuple[int, int],
    route: ReachabilityRouteMap | None = None,
    recent_coordinates: Iterable[tuple[int, int]] = (),
) -> list[tuple[tuple[int, int], dict[str, int] | None]]:
    hostile_rows = list(hostiles)
    if route is not None:
        coordinates = route.learn_overlay(origin, reachable)
    else:
        coordinates = {
            (int(row[0]), int(row[1]))
            for row in reachable
            if len(tuple(row)) == 2
        }
    coordinates.discard(origin)
    coordinates.difference_update(occupied)
    if not coordinates:
        raise RuntimeError("Move overlay has no unoccupied non-origin cell")
    recent = set(recent_coordinates)
    planned = []
    rejected_recent = []
    rejected_no_progress = []
    progress_kinds: dict[tuple[int, int], str] = {}
    for coordinate in coordinates:
        target = adjacent_hostile(coordinate, hostile_rows)
        if coordinate in recent:
            rejected_recent.append(coordinate)
            continue
        if route is not None:
            progress = route.progress_kind(
                origin=origin,
                candidate=coordinate,
                hostiles=hostile_rows,
                recent=recent,
            )
            if progress is None:
                rejected_no_progress.append(coordinate)
                continue
            progress_kinds[coordinate] = progress
        planned.append((coordinate, target))
    if not planned:
        raise RuntimeError(
            "Move overlay has no cycle-safe graph-progress cell: "
            f"origin={origin}, "
            f"recent={sorted(rejected_recent)}, "
            f"no_progress={sorted(rejected_no_progress)}"
        )

    def key(
        row: tuple[tuple[int, int], dict[str, int] | None],
    ) -> tuple[object, ...]:
        coordinate, target = row
        target_key: tuple[int, int, int, int] = (
            hostile_priority(target) if target is not None else (2, 2, 2, 0xFF)
        )
        known_steps = (
            route.known_steps_to_attack(coordinate, hostile_rows)
            if route is not None
            else None
        )
        progress_rank = {
            "attack_frontier": 0,
            "known_graph_shorter": 1,
            "unexplored_overlay_frontier": 2,
        }.get(progress_kinds.get(coordinate, ""), 3)
        return (
            0 if target is not None else 1,
            target_key,
            progress_rank,
            known_steps if known_steps is not None else 0xFFFF,
            route.visits[coordinate] if route is not None else 0,
            (
                route.nearest_hostile_distance(coordinate, hostile_rows)
                if route is not None
                else prototype.manhattan(coordinate, bald)
            ),
            coordinate,
        )

    return sorted(planned, key=key)


def action_order(
    gst: Path,
    bald: dict[str, int],
    route: ReachabilityRouteMap | None = None,
) -> list[dict[str, int]]:
    hostiles = units_for_side(gst, HOSTILE_SIDE)
    units = [row for row in units_for_side(gst, PLAYER_SIDE) if not row["acted"]]

    def key(row: dict[str, int]) -> tuple[object, ...]:
        coordinate = (row["x"], row["y"])
        known = (
            route.known_steps_to_attack(coordinate, hostiles)
            if route is not None
            else None
        )
        return (
            0 if known is not None else 1,
            known if known is not None else 0xFFFF,
            min(
                prototype.manhattan(
                    coordinate, (hostile["x"], hostile["y"])
                )
                for hostile in hostiles
            ),
            0 if row["member_index"] else 1,
            row["group_index"],
            row["member_index"],
        )

    return sorted(
        units,
        key=key,
    )


def launch_fresh_preparation_and_hire(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    runtime_name: str,
    runtime_root: Path,
    output: Path,
    initial_delay: float,
    max_confirmations: int,
) -> dict[str, object]:
    command = fresh_victory_launch_command(
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
    fresh_capture = recorder.capture("preparation/fresh.png")
    fresh_gst = recorder.save_gst("states/preparation/fresh.gst")
    roster = preparation.manual_slot_roster(fresh_gst)
    expected = [
        (ELWIN_COMMANDER_ID, ELWIN_CLASS_ID, SOLDIER_CLASS_ID),
        (LIANA_COMMANDER_ID, LIANA_CLASS_ID, GUARDMAN_CLASS_ID),
    ]
    commander_ids = preparation.player_commander_ids(rom.read_bytes(), SCENARIO)
    if commander_ids != [row[0] for row in expected]:
        raise RuntimeError(f"fresh Scenario 1 commander order changed: {commander_ids}")

    hired_rows = []
    for position, (commander_id, class_id, mercenary_class) in enumerate(expected):
        definition = roster[commander_id - 1]
        offered = definition["hire_rows"]
        if (
            definition["class_id"] != class_id
            or len(offered) != 1
            or int(offered[0]["class_id"]) != mercenary_class
        ):
            raise RuntimeError(
                f"fresh commander {commander_id} hire definition changed: {definition}"
            )
        # END returns all the way to the root preparation action list, not to
        # the commander roster.  Re-observe row 0 for every commander, enter
        # the roster, then navigate from its deterministic first row.
        preparation.ensure_action_row(
            recorder, f"fresh_hire_commander_{commander_id:02d}", 0
        )
        recorder.send(["c"], delay=1.0)
        commander_surface = recorder.capture(
            f"preparation/hire/commander_{commander_id:02d}.png"
        )
        if preparation.hire_screen_visible(commander_surface):
            raise RuntimeError(
                f"commander {commander_id}: root Hire skipped commander roster"
            )
        if position:
            recorder.send(["down"] * position, delay=0.8)
        recorder.send(["c"], delay=1.0)
        opened = recorder.capture(
            f"preparation/hire/commander_{commander_id:02d}_open.png"
        )
        if not preparation.hire_screen_visible(opened):
            raise RuntimeError(f"commander {commander_id} hire screen did not open")
        hire_captures = []
        for count in range(1, HIRED_PER_COMMANDER + 1):
            recorder.send(["c"], delay=0.65)
            hire_captures.append(prototype.file_report(recorder.capture(
                f"preparation/hire/commander_{commander_id:02d}_{count}.png"
            )))
        hired_gst = recorder.save_gst(
            f"states/preparation/commander_{commander_id:02d}_hired.gst"
        )
        group = mercenary.commander_group(hired_gst, commander_id)
        classes = [
            int(row["class_id"])
            for row in group["members"][1:1 + HIRED_PER_COMMANDER]
        ]
        if classes != [mercenary_class] * HIRED_PER_COMMANDER:
            raise RuntimeError(
                f"commander {commander_id} hired classes changed: {classes}"
            )
        recorder.send(["down"], delay=0.7)
        recorder.send(["c"], delay=1.0)
        closed = recorder.capture(
            f"preparation/hire/commander_{commander_id:02d}_closed.png"
        )
        hired_rows.append({
            "commander_id": commander_id,
            "commander_class_id": class_id,
            "mercenary_class_id": mercenary_class,
            "count": HIRED_PER_COMMANDER,
            "captures": hire_captures,
            "gst": prototype.file_report(hired_gst),
            "closed": prototype.file_report(closed),
        })

    mercenary.enter_battle_command(recorder, rom, output)
    command_capture = recorder.capture("battle/turn_01/opening_command.png")
    movement.require_command_menu(command_capture, "fresh hired Scenario 1")
    command_gst = recorder.save_gst("states/turn_01/opening_command.gst")
    if movement.turn_counter(command_gst) != 1:
        raise RuntimeError("fresh hired Scenario 1 did not enter Turn 1")
    for commander_id, _, mercenary_class in expected:
        group = mercenary.commander_group(command_gst, commander_id)
        classes = [
            int(row["class_id"])
            for row in group["members"][1:1 + HIRED_PER_COMMANDER]
        ]
        if classes != [mercenary_class] * HIRED_PER_COMMANDER:
            raise RuntimeError(
                f"commander {commander_id} deployment lost hired units: {classes}"
            )
    return {
        "launcher_argv": command,
        "fresh_capture": prototype.file_report(fresh_capture),
        "fresh_gst": prototype.file_report(fresh_gst),
        "hired": hired_rows,
        "opening_command": prototype.file_report(command_capture),
        "opening_gst": prototype.file_report(command_gst),
    }


def navigate_cursor(
    recorder: preparation.RuntimeRecorder,
    *,
    source: tuple[int, int],
    target: tuple[int, int],
    phase: str,
    delay: float = 0.18,
) -> tuple[dict[str, object], Path]:
    keys = legacy.exact_cursor_navigation(source, target)
    recorder.send(keys, delay=delay, batched=True)
    capture = recorder.capture(f"battle/{phase}/cursor.png")
    gst = recorder.save_gst(f"states/{phase}/cursor.gst")
    selection = legacy.runtime_selection(gst)
    observed = (selection["cursor_x"], selection["cursor_y"])
    if observed != target:
        raise RuntimeError(f"{phase}: cursor {observed} != {target}")
    return ({
        "source": list(source),
        "target": list(target),
        "keys": keys,
        "capture": prototype.file_report(capture),
        "gst": prototype.file_report(gst),
        "selection": selection,
    }, gst)


def open_exact_unit_command(
    recorder: preparation.RuntimeRecorder,
    *,
    unit: dict[str, int],
    phase: str,
) -> tuple[dict[str, object], Path]:
    recorder.send(["c"], delay=0.75)
    capture = recorder.capture(f"battle/{phase}/command.png")
    if not legacy.stock_unit_command_menu_visible(capture):
        raise RuntimeError(f"{phase}: unit command menu is absent")
    gst = recorder.save_gst(f"states/{phase}/command.gst")
    selected = legacy.runtime_command_selection(gst)
    observed = selected["selected_runtime_record"]
    fields = ("group_index", "member_index", "class_id", "name_id", "hp", "x", "y")
    if any(int(observed[field]) != int(unit[field]) for field in fields):
        raise RuntimeError(
            f"{phase}: selected unit changed: expected={unit}, observed={observed}"
        )
    row = legacy.command_cursor_row(capture)
    if row != 0:
        raise RuntimeError(f"{phase}: unit command did not begin on Move: row={row}")
    return ({
        "capture": prototype.file_report(capture),
        "gst": prototype.file_report(gst),
        "selection": selected,
        "command_cursor_row": row,
    }, gst)


def verify_attack_target(
    gst: Path,
    target: dict[str, int],
) -> dict[str, int]:
    selection = legacy.runtime_selection(gst)
    cursor = (selection["cursor_x"], selection["cursor_y"])
    expected = (target["x"], target["y"])
    if cursor != expected:
        raise RuntimeError(f"attack cursor {cursor} != target {expected}")
    observed = runtime_unit(gst, target["group_index"], target["member_index"])
    fields = ("class_id", "name_id", "side_id", "hp", "x", "y")
    if any(observed[field] != target[field] for field in fields) or not unit_alive(observed):
        raise RuntimeError(f"attack target changed before confirmation: {observed}")
    return observed


def wait_for_attack_resolution(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
    actor: dict[str, int],
    target: dict[str, int],
    max_frames: int,
    interval: float,
) -> dict[str, object]:
    samples = []
    combat_frames = 0
    noncombat_after_combat = 0
    resolved_gst: Path | None = None
    endpoint = "unknown"
    for frame in range(max_frames):
        capture = recorder.capture(f"battle/{phase}/resolution_{frame:03d}.png")
        combat = mounted.battle_surface_report(capture)
        surface = result_surface.classify_surface(capture)
        classification = (
            "combat"
            if combat["battle_surface_visible"]
            else (
                surface
                if surface != "other"
                else prototype.classify_turn2_frame(capture)
            )
        )
        samples.append({
            "frame": frame,
            "classification": classification,
            "capture": prototype.file_report(capture),
        })
        if classification == "combat":
            combat_frames += 1
            noncombat_after_combat = 0
        elif combat_frames:
            noncombat_after_combat += 1
            if classification in {
                "battle_map", "dialogue", "turn_command", "battle_result"
            } and noncombat_after_combat >= 2:
                endpoint = classification
                resolved_gst = recorder.save_gst(
                    f"states/{phase}/attack_resolved.gst"
                )
                break
        if classification in {"game_over", "title_screen", "save_menu"}:
            raise RuntimeError(f"{phase}: invalid post-attack endpoint {classification}")
        time.sleep(interval)
    if combat_frames < 2 or resolved_gst is None:
        raise RuntimeError(
            f"{phase}: ordinary combat was not retained and resolved: "
            f"combat_frames={combat_frames}, endpoint={endpoint}"
        )
    actor_after = runtime_unit(
        resolved_gst, actor["group_index"], actor["member_index"]
    )
    target_after = runtime_unit(
        resolved_gst, target["group_index"], target["member_index"]
    )
    if not actor_after["acted"]:
        raise RuntimeError(f"{phase}: attacker did not become acted: {actor_after}")
    if target_after["hp"] >= target["hp"]:
        raise RuntimeError(
            f"{phase}: exact target HP did not decrease: {target} -> {target_after}"
        )
    defeated_consistent = (
        target_after["hp"] > 0 and not target_after["defeated"]
    ) or (
        target_after["hp"] == 0 and target_after["defeated"]
    )
    if not defeated_consistent:
        raise RuntimeError(f"{phase}: target defeat fields disagree: {target_after}")
    return {
        "endpoint": endpoint,
        "combat_frame_count": combat_frames,
        "samples": samples,
        "resolved_gst": prototype.file_report(resolved_gst),
        "actor_after": actor_after,
        "target_after": target_after,
    }


def execute_attack(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
    actor: dict[str, int],
    target: dict[str, int],
    selection_gst: Path,
    max_frames: int,
    interval: float,
) -> dict[str, object]:
    selection = legacy.runtime_selection(selection_gst)
    cursor = (selection["cursor_x"], selection["cursor_y"])
    target_coordinate = (target["x"], target["y"])
    navigation = None
    target_gst = selection_gst
    if cursor != target_coordinate:
        navigation, target_gst = navigate_cursor(
            recorder,
            source=cursor,
            target=target_coordinate,
            phase=f"{phase}/target",
            delay=0.25,
        )
    target_before = verify_attack_target(target_gst, target)
    target_capture = recorder.capture(f"battle/{phase}/target_verified.png")
    try:
        orange_cell = movement.selection_frame_cell_top_left(target_capture)
    except ValueError as exc:
        raise RuntimeError(f"{phase}: attack target lacks orange cursor") from exc
    recorder.send(["c"], delay=0.12)
    resolution = wait_for_attack_resolution(
        recorder,
        phase=phase,
        actor=actor,
        target=target_before,
        max_frames=max_frames,
        interval=interval,
    )
    return {
        "target": target_before,
        "navigation": navigation,
        "target_capture": prototype.file_report(target_capture),
        "orange_cursor_cell": list(orange_cell),
        "resolution": resolution,
    }


def cancel_move_and_standby_at_origin(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
    unit: dict[str, int],
    cursor: tuple[int, int],
    attempts: list[dict[str, object]],
) -> dict[str, object]:
    """Use the stock command menu when no tinted cell accepts a stop."""
    recorder.send(["b"], delay=0.75)
    bare_map = recorder.capture(f"battle/{phase}/move_cancel_bare_map.png")
    bare_map_gst = recorder.save_gst(f"states/{phase}/move_cancel_bare_map.gst")
    bare_selection = legacy.runtime_selection(bare_map_gst)
    bare_unit = runtime_unit(
        bare_map_gst, unit["group_index"], unit["member_index"]
    )
    immutable_fields = ("class_id", "name_id", "hp", "x", "y", "acted")
    if (
        legacy.stock_unit_command_menu_visible(bare_map)
        or (bare_selection["cursor_x"], bare_selection["cursor_y"])
        != (unit["x"], unit["y"])
        or any(bare_unit[field] != unit[field] for field in immutable_fields)
    ):
        raise RuntimeError(
            f"{phase}: B did not return to exact-unit bare map: "
            f"selection={bare_selection}, unit={bare_unit}"
        )
    # Run 08 proved a second B leaves the same bare-map state. Re-open the
    # exact unit with C, then choose Standby from the ordinary command menu.
    recorder.send(["c"], delay=0.75)
    cancelled = recorder.capture(f"battle/{phase}/command_reopened.png")
    if not legacy.stock_unit_command_menu_visible(cancelled):
        raise RuntimeError(f"{phase}: C at exact origin did not reopen command")
    cancelled_gst = recorder.save_gst(f"states/{phase}/command_reopened.gst")
    selected = legacy.runtime_command_selection(cancelled_gst)
    observed = selected["selected_runtime_record"]
    fields = ("group_index", "member_index", "class_id", "name_id", "hp", "x", "y")
    if any(int(observed[field]) != int(unit[field]) for field in fields):
        raise RuntimeError(
            f"{phase}: Move cancel returned to another unit: {observed}"
        )
    row = legacy.command_cursor_row(cancelled)
    if row != 0:
        raise RuntimeError(f"{phase}: cancelled Move cursor row {row} != Move row 0")
    # Stock full player command: Move, Attack, Magic, Item, Equip, Standby.
    recorder.send(["up"], delay=0.55)
    standby_row_capture = recorder.capture(f"battle/{phase}/standby_row.png")
    standby_row = legacy.command_cursor_row(standby_row_capture)
    if standby_row != 5:
        raise RuntimeError(
            f"{phase}: command wrap did not select Standby row 5: {standby_row}"
        )
    recorder.send(["c"], delay=0.9)
    standby = recorder.capture(f"battle/{phase}/origin_standby.png")
    standby_gst = recorder.save_gst(f"states/{phase}/origin_standby.gst")
    acted = runtime_unit(standby_gst, unit["group_index"], unit["member_index"])
    if (
        (acted["x"], acted["y"]) != (unit["x"], unit["y"])
        or not acted["acted"]
        or acted["hp"] != unit["hp"]
        or acted["class_id"] != unit["class_id"]
    ):
        raise RuntimeError(f"{phase}: origin Standby did not commit: {acted}")
    return {
        "kind": "cancel_move_then_origin_standby",
        "unit_before": unit,
        "destination_attempts": attempts,
        "last_move_cursor": list(cursor),
        "move_cancel_bare_map": prototype.file_report(bare_map),
        "move_cancel_bare_map_gst": prototype.file_report(bare_map_gst),
        "bare_map_selection": bare_selection,
        "bare_map_unit": bare_unit,
        "move_cancelled": prototype.file_report(cancelled),
        "move_cancelled_gst": prototype.file_report(cancelled_gst),
        "cancelled_selection": selected,
        "standby_row": standby_row,
        "standby_row_capture": prototype.file_report(standby_row_capture),
        "standby": prototype.file_report(standby),
        "unit_after": acted,
        "destination": [unit["x"], unit["y"]],
        "route_before": None,
        "route_after": None,
        "stock_ui_only": True,
        "reason": "every raw-overlay graph-progress destination lacked orange cursor",
    }


def act_one_unit(
    recorder: preparation.RuntimeRecorder,
    *,
    source_cursor: tuple[int, int],
    unit: dict[str, int],
    turn: int,
    ordinal: int,
    route: ReachabilityRouteMap,
    max_combat_frames: int,
    combat_interval: float,
) -> dict[str, object]:
    phase = f"turn_{turn:02d}/action_{ordinal:02d}_g{unit['group_index']}_m{unit['member_index']}"
    navigation, selected_gst = navigate_cursor(
        recorder,
        source=source_cursor,
        target=(unit["x"], unit["y"]),
        phase=f"{phase}/select",
    )
    selected_unit = runtime_unit(selected_gst, unit["group_index"], unit["member_index"])
    if selected_unit != unit:
        raise RuntimeError(f"{phase}: unit changed before command: {selected_unit}")
    command, command_gst = open_exact_unit_command(
        recorder, unit=unit, phase=phase
    )
    bald = exact_bald(command_gst, require_live=True)
    bald_coordinate = (bald["x"], bald["y"])
    hostiles = units_for_side(command_gst, HOSTILE_SIDE)
    recent_coordinates = route.recent_for(unit)
    route_before = {
        **route.progress_report((unit["x"], unit["y"]), hostiles),
        "recent_coordinates": [list(row) for row in recent_coordinates],
    }
    immediate = adjacent_hostile((unit["x"], unit["y"]), hostiles)
    if immediate is not None:
        recorder.send(["down"], delay=0.55)
        attack_row = recorder.capture(f"battle/{phase}/attack_row.png")
        if legacy.command_cursor_row(attack_row) != 1:
            raise RuntimeError(f"{phase}: direct Attack row was not selected")
        recorder.send(["c"], delay=0.7)
        attack_selection = recorder.save_gst(
            f"states/{phase}/direct_attack_selection.gst"
        )
        attack = execute_attack(
            recorder,
            phase=f"{phase}/direct_attack",
            actor=unit,
            target=immediate,
            selection_gst=attack_selection,
            max_frames=max_combat_frames,
            interval=combat_interval,
        )
        return {
            "kind": "direct_attack",
            "unit_before": unit,
            "route_before": route_before,
            "route_after": route_before,
            "selection_navigation": navigation,
            "command": command,
            "attack_row": prototype.file_report(attack_row),
            "attack": attack,
        }

    recorder.send(["c"], delay=0.75)
    overlay = recorder.capture(f"battle/{phase}/move_overlay.png")
    overlay_gst = recorder.save_gst(f"states/{phase}/move_overlay.gst")
    reach = movement.reach_coordinate_report(
        movement.plane_delta(command_gst, overlay_gst),
        (unit["x"], unit["y"]),
        movement=int(movement.runtime_group(command_gst, unit["group_index"])[
            "movement_plus_0x44"
        ]),
        overlay_capture=overlay,
        overlay_gst=overlay_gst,
    )
    raw_overlay_coordinates = {
        (int(x), int(y)) for x, y in reach["coordinates"]
    }
    overlay_origin_evidence = {
        "coordinate": [unit["x"], unit["y"]],
        "provenance": "exact_selected_runtime_record_from_command_gst",
        "raw_move_overlay_tinted": (unit["x"], unit["y"])
        in raw_overlay_coordinates,
        "graph_origin_node_only": True,
        "eligible_as_destination_without_raw_overlay_and_orange": False,
    }
    occupied = movement.occupied_runtime_coordinates(command_gst)
    occupied.discard((unit["x"], unit["y"]))
    candidates = tactical_destination_candidates(
        reachable=reach["coordinates"],
        origin=(unit["x"], unit["y"]),
        occupied=occupied,
        hostiles=hostiles,
        bald=bald_coordinate,
        route=route,
        recent_coordinates=recent_coordinates,
    )
    cursor = (unit["x"], unit["y"])
    attempts = []
    accepted: tuple[int, int] | None = None
    accepted_target: dict[str, int] | None = None
    destination_gst: Path | None = None
    for attempt, (candidate, target) in enumerate(candidates, 1):
        candidate_navigation, candidate_gst = navigate_cursor(
            recorder,
            source=cursor,
            target=candidate,
            phase=f"{phase}/destination_{attempt:02d}",
            delay=0.22,
        )
        cursor = candidate
        candidate_capture = Path(candidate_navigation["capture"]["path"])
        if not candidate_capture.is_absolute():
            candidate_capture = ROOT / candidate_capture
        try:
            cell = movement.selection_frame_cell_top_left(candidate_capture)
            valid = True
        except ValueError:
            cell = None
            valid = False
        attempts.append({
            "candidate": list(candidate),
            "target": target,
            "navigation": candidate_navigation,
            "orange_cursor": valid,
            "screen_cell": list(cell) if cell is not None else None,
        })
        if valid:
            accepted = candidate
            accepted_target = target
            destination_gst = candidate_gst
            break
    if accepted is None or destination_gst is None:
        fallback = cancel_move_and_standby_at_origin(
            recorder,
            phase=phase,
            unit=unit,
            cursor=cursor,
            attempts=attempts,
        )
        fallback.update({
            "selection_navigation": navigation,
            "command": command,
            "overlay": prototype.file_report(overlay),
            "overlay_origin_evidence": overlay_origin_evidence,
            "reach": reach,
            "route_before": route_before,
            "route_after": {
                **route_before,
                "progress_kind": "stock_origin_standby_no_valid_move",
            },
        })
        return fallback
    recorder.send(["c"], delay=0.8)
    post_move = recorder.capture(f"battle/{phase}/post_move.png")
    post_move_gst = recorder.save_gst(f"states/{phase}/post_move.gst")
    moved = runtime_unit(post_move_gst, unit["group_index"], unit["member_index"])
    if (
        (moved["x"], moved["y"]) != accepted
        or moved["acted"]
        or moved["hp"] != unit["hp"]
        or moved["class_id"] != unit["class_id"]
    ):
        raise RuntimeError(f"{phase}: Move did not commit exactly: {moved}")
    progress_kind = route.progress_kind(
        origin=(unit["x"], unit["y"]),
        candidate=accepted,
        hostiles=hostiles,
        recent=set(recent_coordinates),
    )
    if progress_kind is None:
        raise RuntimeError(
            f"{phase}: accepted orange overlay destination lost graph progress"
        )
    route_after = {
        **route.progress_report(accepted, hostiles),
        "progress_kind": progress_kind,
        "live_move_overlay_coordinate": accepted in {
            (int(x), int(y)) for x, y in reach["coordinates"]
        },
        "stock_orange_cursor_retained": True,
    }
    if accepted_target is not None:
        attack = execute_attack(
            recorder,
            phase=f"{phase}/move_attack",
            actor=moved,
            target=accepted_target,
            selection_gst=post_move_gst,
            max_frames=max_combat_frames,
            interval=combat_interval,
        )
        return {
            "kind": "move_then_attack",
            "unit_before": unit,
            "route_before": route_before,
            "route_after": route_after,
            "selection_navigation": navigation,
            "command": command,
            "overlay": prototype.file_report(overlay),
            "overlay_origin_evidence": overlay_origin_evidence,
            "reach": reach,
            "destination_attempts": attempts,
            "destination": list(accepted),
            "post_move": prototype.file_report(post_move),
            "attack": attack,
        }
    recorder.send(["c"], delay=0.9)
    standby = recorder.capture(f"battle/{phase}/standby.png")
    standby_gst = recorder.save_gst(f"states/{phase}/standby.gst")
    acted = runtime_unit(standby_gst, unit["group_index"], unit["member_index"])
    if (acted["x"], acted["y"]) != accepted or not acted["acted"]:
        raise RuntimeError(f"{phase}: Standby did not commit: {acted}")
    return {
        "kind": "move_then_standby",
        "unit_before": unit,
        "route_before": route_before,
        "route_after": route_after,
        "selection_navigation": navigation,
        "command": command,
        "overlay": prototype.file_report(overlay),
        "overlay_origin_evidence": overlay_origin_evidence,
        "reach": reach,
        "destination_attempts": attempts,
        "destination": list(accepted),
        "post_move": prototype.file_report(post_move),
        "standby": prototype.file_report(standby),
        "unit_after": acted,
    }


def runtime_surface_classification(path: Path) -> str:
    surface = result_surface.classify_surface(path)
    if surface != "other":
        return surface
    combat = mounted.battle_surface_report(path)
    if combat["battle_surface_visible"]:
        return "combat"
    return prototype.classify_turn2_frame(path)


def detect_runtime_endpoint(
    recorder: preparation.RuntimeRecorder,
    *,
    phase: str,
    max_checks: int,
    delay: float,
    stop_on_stable_battle_map: bool = False,
) -> dict[str, object]:
    dialogue = prototype.DialoguePageTracker()
    surfaces = prototype.StableSurfaceTracker()
    events = []
    confirmations = 0
    map_confirms = 0
    for step in range(max_checks + 1):
        capture = recorder.capture(f"{phase}/detect_{step:03d}.png")
        classification = runtime_surface_classification(capture)
        event: dict[str, object] = {
            "step": step,
            "classification": classification,
            "capture": prototype.file_report(capture),
        }
        sent = False
        if classification in {"game_over", "title_screen"}:
            raise RuntimeError(f"{phase}: terminal failure {classification}")
        if classification in {"battle_result", "save_menu"}:
            stable = surfaces.observe(classification)
            event["stable_frames"] = surfaces.count
            events.append(event)
            if stable:
                return {
                    "endpoint": classification,
                    "events": events,
                    "dialogue_confirmations": confirmations,
                    "map_confirmations": map_confirms,
                }
        elif classification == "dialogue":
            surfaces.reset()
            action = dialogue.observe_dialogue(
                sequence.dialogue_text_fingerprint(capture)
            )
            event["dialogue_action"] = action
            if action in {"confirm_stable_page", "retry_confirmation"}:
                recorder.send(["c"], delay=delay)
                confirmations += 1
                sent = True
            events.append(event)
        elif classification == "combat":
            surfaces.reset()
            events.append(event)
        else:
            action = dialogue.observe_non_dialogue()
            if action != "no_dialogue":
                event["dialogue_action"] = action
            stable = surfaces.observe(classification)
            event["stable_frames"] = surfaces.count
            if classification == "turn_command" and stable:
                events.append(event)
                return {
                    "endpoint": "turn_command",
                    "events": events,
                    "dialogue_confirmations": confirmations,
                    "map_confirmations": map_confirms,
                }
            if classification == "battle_map" and stable:
                if stop_on_stable_battle_map:
                    events.append(event)
                    return {
                        "endpoint": "battle_map",
                        "events": events,
                        "dialogue_confirmations": confirmations,
                        "map_confirmations": map_confirms,
                    }
                recorder.send(["c"], delay=delay)
                map_confirms += 1
                surfaces.reset()
                sent = True
            events.append(event)
        if not sent and step < max_checks:
            time.sleep(delay)
    raise RuntimeError(f"{phase}: no stable runtime endpoint after {max_checks + 1} checks")


def turn_action_summary(actions: Iterable[dict[str, object]]) -> dict[str, object]:
    rows = list(actions)
    changes = []
    attack_count = 0
    for action in rows:
        unit = action["unit_before"]
        assert isinstance(unit, dict)
        origin = (int(unit["x"]), int(unit["y"]))
        destination_raw = action.get("destination")
        destination = (
            tuple(int(value) for value in destination_raw)
            if destination_raw is not None
            else origin
        )
        if "attack" in action:
            attack_count += 1
        if destination != origin:
            changes.append({
                "group_index": int(unit["group_index"]),
                "member_index": int(unit["member_index"]),
                "from": list(origin),
                "to": list(destination),
                "progress_kind": action["route_after"]["progress_kind"],
                "nearest_hostile_before": action["route_before"][
                    "nearest_hostile_manhattan"
                ],
                "nearest_hostile_after": action["route_after"][
                    "nearest_hostile_manhattan"
                ],
                "known_steps_before": action["route_before"][
                    "known_steps_to_attack"
                ],
                "known_steps_after": action["route_after"][
                    "known_steps_to_attack"
                ],
            })
    return {
        "action_count": len(rows),
        "movement_count": len(changes),
        "attack_count": attack_count,
        "standby_count": sum(
            action.get("kind") == "move_then_standby" for action in rows
        ),
        "coordinate_changes": changes,
    }


def finish_result_and_save(
    recorder: preparation.RuntimeRecorder,
    *,
    initial_endpoint: dict[str, object] | None,
    max_checks: int,
    delay: float,
) -> dict[str, object]:
    result_detection = initial_endpoint
    if result_detection is None or result_detection["endpoint"] != "battle_result":
        result_detection = detect_runtime_endpoint(
            recorder,
            phase="aftermath",
            max_checks=max_checks,
            delay=delay,
        )
    if result_detection["endpoint"] != "battle_result":
        raise RuntimeError(
            f"Bald defeat did not reach battle result: {result_detection['endpoint']}"
        )
    result_capture = recorder.capture("aftermath/battle_result_accepted.png")
    if result_surface.classify_surface(result_capture) != "battle_result":
        raise RuntimeError("accepted battle result was not retained")
    result_gst = recorder.save_gst("states/aftermath/battle_result.gst")
    recorder.send(["c"], delay=0.7)
    save_detection = detect_runtime_endpoint(
        recorder,
        phase="save",
        max_checks=max_checks,
        delay=delay,
    )
    if save_detection["endpoint"] != "save_menu":
        raise RuntimeError(f"battle result did not reach save menu: {save_detection['endpoint']}")
    save_capture = recorder.capture("save/save_menu_accepted.png")
    if result_surface.classify_surface(save_capture) != "save_menu":
        raise RuntimeError("accepted save menu was not retained")
    save_gst = recorder.save_gst("states/save/save_menu.gst")
    saved_scenario = preparation.manual_slot_scenario_from_gst(save_gst)
    if saved_scenario != EXPECTED_SAVE_SCENARIO:
        raise RuntimeError(
            f"Scenario 1 save transition is {saved_scenario}, expected 2"
        )
    return {
        "battle_result_detection": result_detection,
        "battle_result_capture": prototype.file_report(result_capture),
        "battle_result_gst": prototype.file_report(result_gst),
        "save_detection": save_detection,
        "save_capture": prototype.file_report(save_capture),
        "save_gst": prototype.file_report(save_gst),
        "saved_scenario": saved_scenario,
    }


def run_victory(args: argparse.Namespace) -> dict[str, object]:
    prototype.require_isolated_display(args.display)
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    runtime_name = f"s1-natural-victory-{args.run_id}"
    runtime_home = args.runtime_root / runtime_name
    if runtime_home.exists():
        raise FileExistsError(f"fresh runtime HOME already exists: {runtime_home}")
    args.output.mkdir(parents=True)
    checkpoints: list[dict[str, str]] = []
    prototype.require_exact_rom(
        args.rom, args.expected_rom_sha256, "before", checkpoints
    )
    recorder = preparation.RuntimeRecorder(args.output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(args.xvfb, args.xvfb_library_path, args.display)
    started = time.monotonic()
    process_initial = None
    try:
        fresh = launch_fresh_preparation_and_hire(
            recorder,
            rom=args.rom,
            runtime_name=runtime_name,
            runtime_root=args.runtime_root,
            output=args.output,
            initial_delay=args.initial_delay,
            max_confirmations=args.max_checks,
        )
        prototype.require_exact_rom(
            args.rom, args.expected_rom_sha256, "turn_1", checkpoints
        )
        process_initial = legacy.live_process_identity(
            recorder, rom=args.rom, phase="turn_1"
        )
        current_gst = args.output / "states/turn_01/opening_command.gst"
        opening_bald = exact_bald(current_gst, require_live=True)
        turns = []
        route = ReachabilityRouteMap()
        victory_gst: Path | None = None
        initial_result_endpoint = None
        for turn in range(1, args.max_turns + 1):
            observed_turn = movement.turn_counter(current_gst)
            if observed_turn != turn:
                raise RuntimeError(f"turn counter {observed_turn} != planned {turn}")
            bald_before = exact_bald(current_gst, require_live=True)
            route.begin_turn(units_for_side(current_gst, PLAYER_SIDE), turn)
            selection = legacy.runtime_selection(current_gst)
            recorder.send(["b"], delay=0.6)
            map_capture = recorder.capture(f"battle/turn_{turn:02d}/map_start.png")
            if not sequence.battle_map_surface_visible(map_capture):
                raise RuntimeError(f"Turn {turn}: command did not close to battle map")
            cursor = (selection["cursor_x"], selection["cursor_y"])
            turn_actions = []
            for ordinal in range(1, 1 + MAX_RUNTIME_GROUPS * MAX_MEMBERS):
                action_snapshot = recorder.save_gst(
                    f"states/turn_{turn:02d}/before_action_{ordinal:02d}.gst"
                )
                bald_now = exact_bald(action_snapshot, require_live=False)
                if bald_now["hp"] == 0 and bald_now["defeated"]:
                    victory_gst = action_snapshot
                    break
                if not unit_alive(bald_now):
                    raise RuntimeError(f"Turn {turn}: Bald escaped instead of defeat: {bald_now}")
                ordered = action_order(action_snapshot, bald_now, route)
                if not ordered:
                    current_gst = action_snapshot
                    break
                unit = ordered[0]
                selection = legacy.runtime_selection(action_snapshot)
                cursor = (selection["cursor_x"], selection["cursor_y"])
                action = act_one_unit(
                    recorder,
                    source_cursor=cursor,
                    unit=unit,
                    turn=turn,
                    ordinal=ordinal,
                    route=route,
                    max_combat_frames=args.max_combat_frames,
                    combat_interval=args.combat_interval,
                )
                turn_actions.append(action)
                resolution = action.get("attack", {}).get("resolution")
                if resolution is not None:
                    resolved = Path(str(resolution["resolved_gst"]["path"]))
                    if not resolved.is_absolute():
                        resolved = ROOT / resolved
                    current_gst = resolved
                    target_after = resolution["target_after"]
                    actor_after = resolution["actor_after"]
                    route.observe_unit(actor_after)
                    if (
                        target_after["group_index"], target_after["member_index"]
                    ) == (BALD_GROUP, BALD_MEMBER) and (
                        target_after["hp"] == 0 and target_after["defeated"]
                    ):
                        victory_gst = resolved
                        if resolution["endpoint"] == "battle_result":
                            initial_result_endpoint = {
                                "endpoint": "battle_result",
                                "events": resolution["samples"],
                            }
                        break
                    if resolution["endpoint"] == "dialogue":
                        settlement = detect_runtime_endpoint(
                            recorder,
                            phase=(
                                f"battle/turn_{turn:02d}/"
                                f"post_attack_{ordinal:02d}"
                            ),
                            max_checks=args.max_checks,
                            delay=args.surface_delay,
                            stop_on_stable_battle_map=True,
                        )
                        action["post_attack_settlement"] = settlement
                        if settlement["endpoint"] != "battle_map":
                            raise RuntimeError(
                                f"Turn {turn} action {ordinal}: non-Bald attack "
                                f"settled at {settlement['endpoint']}"
                            )
                else:
                    route.observe_unit(action["unit_after"])
                    current_gst = args.output / (
                        f"states/turn_{turn:02d}/"
                        f"action_{ordinal:02d}_g{unit['group_index']}_m{unit['member_index']}/"
                        "standby.gst"
                    )
            turns.append({
                "turn": turn,
                "bald_before": bald_before,
                "actions": turn_actions,
                "summary": turn_action_summary(turn_actions),
            })
            if victory_gst is not None:
                break
            turn_end = first_turn.select_turn_end(
                env=recorder.environment,
                display=recorder.display,
                opening_checks=args.max_checks,
                delay=args.surface_delay,
            )
            if args.emulator_speed_key:
                recorder.send([args.emulator_speed_key], delay=0.2)
            endpoint = detect_runtime_endpoint(
                recorder,
                phase=f"enemy_phase/turn_{turn:02d}",
                max_checks=args.max_checks,
                delay=args.surface_delay,
            )
            turns[-1]["turn_end"] = turn_end
            turns[-1]["enemy_phase"] = endpoint
            if endpoint["endpoint"] == "battle_result":
                post_enemy_gst = recorder.save_gst(
                    f"states/enemy_phase/turn_{turn:02d}_result.gst"
                )
                bald_after = exact_bald(post_enemy_gst, require_live=False)
                if bald_after["hp"] != 0 or not bald_after["defeated"]:
                    raise RuntimeError("battle result appeared without exact Bald defeat")
                victory_gst = post_enemy_gst
                initial_result_endpoint = endpoint
                break
            if endpoint["endpoint"] != "turn_command":
                raise RuntimeError(f"Turn {turn}: enemy phase ended at {endpoint['endpoint']}")
            if args.emulator_speed_key:
                # Host speed 4 is useful only while stock AI owns the turn.
                # At that speed one held directional edge can repeat across
                # several emulated frames and overshoot the observed cursor.
                # Return to normal speed before any player navigation.
                recorder.send(["1"], delay=0.25)
            current_gst = recorder.save_gst(
                f"states/turn_{turn + 1:02d}/opening_command.gst"
            )
            if movement.turn_counter(current_gst) != turn + 1:
                raise RuntimeError("stable command surface did not advance one turn")
            bald_after = exact_bald(current_gst, require_live=False)
            if not unit_alive(bald_after):
                raise RuntimeError(f"Bald escaped before player victory: {bald_after}")
            prototype.require_exact_rom(
                args.rom,
                args.expected_rom_sha256,
                f"turn_{turn + 1}",
                checkpoints,
            )
        if victory_gst is None:
            raise RuntimeError(f"Bald was not defeated within {args.max_turns} turns")
        defeated_bald = exact_bald(victory_gst, require_live=False)
        if defeated_bald["hp"] != 0 or not defeated_bald["defeated"]:
            raise RuntimeError(f"victory state lacks exact Bald defeat: {defeated_bald}")
        finish = finish_result_and_save(
            recorder,
            initial_endpoint=initial_result_endpoint,
            max_checks=args.max_checks,
            delay=args.surface_delay,
        )
        prototype.require_exact_rom(
            args.rom, args.expected_rom_sha256, "save_menu", checkpoints
        )
        process_final = legacy.live_process_identity(
            recorder, rom=args.rom, phase="save_menu"
        )
        legacy.assert_same_live_process(process_initial, process_final)
        checks = {
            "fresh_empty_runtime_home": True,
            "no_external_state_or_sram_input": not any(
                token in FORBIDDEN_RUNTIME_INPUT_TOKENS
                for token in fresh["launcher_argv"]
            ),
            "same_exact_rom_all_checkpoints": all(
                row["sha256"] == args.expected_rom_sha256 for row in checkpoints
            ),
            "same_live_process_no_restore": (
                process_initial["pid"] == process_final["pid"]
                and not process_initial["argv_has_savestate_restore_option"]
                and not process_final["argv_has_savestate_restore_option"]
            ),
            "actual_ui_hire_and_deployment": len(fresh["hired"]) == 2,
            "actual_ui_move_attack_standby_turn_loop": bool(turns),
            "exact_bald_defeated": (
                defeated_bald["hp"] == 0 and defeated_bald["defeated"] == 1
            ),
            "stock_battle_result_retained": (
                finish["battle_result_capture"]["path"] is not None
            ),
            "stock_save_menu_records_scenario_2": (
                finish["saved_scenario"] == EXPECTED_SAVE_SCENARIO
            ),
        }
        passed = all(checks.values())
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "classification": "fresh_natural_s1_actual_victory",
            "scope": (
                "exact frozen Original ROM, empty runtime, actual preparation "
                "and tactical UI through Bald defeat, result, and Scenario 2 save"
            ),
            "contract": {
                "gst_role": "read_only_observation_only",
                "gst_used_as_emulator_input": False,
                "direct_ram_write": False,
                "rom_patch_or_write": False,
                "stock_cheat_used": False,
                "external_sram_used": False,
            },
            "rom": {
                **prototype.file_report(args.rom),
                "expected_sha256": args.expected_rom_sha256,
                "hash_checkpoints": checkpoints,
            },
            "runtime": {
                "display": args.display,
                "runtime_home": prototype.relative(runtime_home),
                "process_initial": process_initial,
                "process_final": process_final,
            },
            "fresh_preparation": fresh,
            "opening_bald": opening_bald,
            "turns": turns,
            "tactical_summary": {
                "turn_count": len(turns),
                "action_count": sum(
                    int(row["summary"]["action_count"]) for row in turns
                ),
                "attack_count": sum(
                    int(row["summary"]["attack_count"]) for row in turns
                ),
                "movement_count": sum(
                    int(row["summary"]["movement_count"]) for row in turns
                ),
            },
            "defeated_bald": defeated_bald,
            "result_and_save": finish,
            "checks": checks,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "actions": recorder.actions,
        }
        (args.output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "diagnostic_failed_attempt",
            "eligible_as_acceptance_evidence": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "rom": prototype.file_report(args.rom),
            "expected_rom_sha256": args.expected_rom_sha256,
            "hash_checkpoints": checkpoints,
            "runtime_home": prototype.relative(runtime_home),
            "display": args.display,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "actions": recorder.actions,
        }
        try:
            failure_gst = recorder.save_gst("states/failure.gst")
            failure["failure_gst"] = prototype.file_report(failure_gst)
        except Exception:
            failure["failure_gst"] = None
        (args.output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        sequence.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument(
        "--expected-rom-sha256",
        type=prototype.validate_sha256,
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
    parser.add_argument("--run-id", type=prototype.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=6.0)
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument("--max-checks", type=int, default=500)
    parser.add_argument("--max-combat-frames", type=int, default=180)
    parser.add_argument("--combat-interval", type=float, default=0.12)
    parser.add_argument("--surface-delay", type=float, default=0.35)
    parser.add_argument(
        "--emulator-speed-key", choices=("", "1", "2", "3", "4"), default="4"
    )
    args = parser.parse_args()
    prototype.require_isolated_display(args.display)
    for name in ("rom", "xvfb", "xvfb_library_path", "output_root", "runtime_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (
        ("ROM", args.rom),
        ("Xvfb", args.xvfb),
        ("Xvfb library path", args.xvfb_library_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if not 1 <= args.max_turns <= 30:
        parser.error("--max-turns must be 1..30")
    if not 20 <= args.max_checks <= 2000:
        parser.error("--max-checks must be 20..2000")
    if not 10 <= args.max_combat_frames <= 1000:
        parser.error("--max-combat-frames must be 10..1000")
    if not 0.05 <= args.combat_interval <= 1.0:
        parser.error("--combat-interval must be 0.05..1.0")
    if not 0.1 <= args.surface_delay <= 2.0:
        parser.error("--surface-delay must be 0.1..2.0")
    args.output = args.output_root / args.run_id
    result = run_victory(args)
    print(
        f"{result['status']}: exact fresh Scenario 1 natural Bald defeat, "
        "result, and Scenario 2 save"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
