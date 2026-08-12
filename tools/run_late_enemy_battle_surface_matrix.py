#!/usr/bin/env python3
"""Verify late-chapter enemy map, status, and natural-combat surfaces.

The preparation matrix proves the fixed records before sortie.  This runner
starts the unmodified release ROM, enters the real battle map, and links one
named hostile commander plus one of its mercenaries to the exact runtime
record, ROM map-sprite payload, VRAM cache, Plane A use, and full status
surface.  Scenario 23 can additionally end the real first turn and retain the
natural side-view battle frames.

Accepted runs must use the exact per-chapter input GST recorded by a passing
continuous-campaign summary.  ``--preflight-only`` exists solely for harness
development; its evidence is explicitly ineligible for release acceptance.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import run_gray_acted_surface_matrix as gray
from tools import run_hard_s1_movement_regression as movement
from tools import run_mounted_lord_combat_regression as mounted
from tools import run_pike_acted_surface_probe as mercenary
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools import run_sequential_campaign_revalidation as campaign
from tools import verify_hard_mode_first_turn as first_turn
from tools.run_blastem_sequence import battle_map_surface_visible
from tools.scenario_data import (
    DEFAULT_REFERENCE_ROM,
    KOREAN_CLASS_NAMES,
    read_scenario,
)
from tools.verify_preparation_surface_evidence import load_gst, plane_tile_hits


DEFAULT_OUTPUT_ROOT = ROOT / "tmp/v137-late-enemy-battle-surfaces"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/v137-late-enemy-battle-runtime"
DEFAULT_DISPLAY = ":1010"
SCENARIOS = (23, 24, 25, 26)
CURSOR_X_ADDRESS = 0xA6DF
CURSOR_Y_ADDRESS = 0xA6E1
RUNTIME_GROUP_COUNT = 40
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_SIDE_OFFSET = 0x20
RUNTIME_LEVEL_OFFSET = 0x2E
TILE_BYTES = 32
STATUS_COMMAND_PANEL = (31, 43, 97, 165)
STATUS_DETAIL_PANEL = (98, 44, 280, 194)
STATUS_BOTTOM_BAR = (0, 208, 320, 233)
ENEMY_UNIT_MESSAGE_PANEL = (80, 150, 255, 190)
DARK_BLUE = (0, 0, 119)


@dataclass(frozen=True)
class LateTarget:
    scenario: int
    fixed_record_index: int
    mercenary_index: int
    reason: str


# Pick named/distinct commanders where possible.  All four records are visible
# from turn 1 in the Japanese layout and are unchanged by the opening event.
TARGETS = {
    23: LateTarget(23, 4, 1, "Laird / Silver Knight and Royal Horse"),
    24: LateTarget(24, 10, 1, "Vampire Lord and Arch Demon"),
    25: LateTarget(25, 1, 1, "Leon / Royal Guard and Royal Horse"),
    26: LateTarget(26, 9, 1, "Egbert / Zervera and Elemental"),
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes | bytearray) -> str:
    return hashlib.sha256(payload).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def resolve_report_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()


def file_model(path: Path) -> dict[str, object]:
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def image_model(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {**file_model(path), "dimensions": dimensions}


def campaign_input_contract(
    summary_path: Path,
    *,
    profile: str,
    scenario: int,
    seed_gst: Path,
    rom_path: Path,
) -> dict[str, object]:
    """Resolve one exact continuous-campaign input without trusting the CLI."""
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    if data.get("status") != "pass":
        raise ValueError("continuous-campaign summary is not passing")
    if not data.get("continuous_save_chain"):
        raise ValueError("summary does not declare a continuous save chain")
    if list(data.get("route_order", ())) != list(campaign.FULL_ROUTE_ORDER):
        raise ValueError("continuous-campaign route order changed")

    profile_rows = [
        row for row in data.get("results", ()) if row.get("profile") == profile
    ]
    if len(profile_rows) != 1:
        raise ValueError(f"expected one campaign profile row for {profile}")
    profile_row = profile_rows[0]
    if profile_row.get("status") != "pass":
        raise ValueError(f"campaign profile {profile} is not passing")
    release = profile_row.get("release_rom", {})
    if release.get("sha256") != sha256_path(rom_path):
        raise ValueError("campaign release-ROM SHA-256 does not match input ROM")

    matches = [
        row
        for row in profile_row.get("results", ())
        if row.get("scenario") == scenario
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one Scenario {scenario} campaign result for {profile}"
        )
    row = matches[0]
    if row.get("status") != "pass":
        raise ValueError(
            f"Scenario {scenario} campaign input row is not passing"
        )
    state = row.get("input_state")
    if not isinstance(state, dict):
        raise ValueError("campaign row lacks input_state")
    recorded_path = resolve_report_path(str(state.get("path", "")))
    if recorded_path != seed_gst.resolve():
        raise ValueError(
            "--seed-gst is not the campaign row's exact input GST: "
            f"{seed_gst} != {recorded_path}"
        )
    actual_hash = sha256_path(seed_gst)
    if state.get("gst_sha256") != actual_hash:
        raise ValueError("campaign input GST SHA-256 does not match summary")
    if state.get("scenario") != scenario:
        raise ValueError(
            f"campaign input state is Scenario {state.get('scenario')}, "
            f"not {scenario}"
        )
    snapshot = campaign.state_snapshot(seed_gst)
    if snapshot["scenario"] != scenario:
        raise ValueError("serialized input GST scenario does not match target")
    if snapshot["gst_sha256"] != actual_hash:
        raise AssertionError("campaign state snapshot changed its GST hash")
    if snapshot["record_sha256"] != state.get("record_sha256"):
        raise ValueError("serialized campaign record SHA-256 does not match summary")
    return {
        "summary": file_model(summary_path),
        "campaign_run_id": data.get("run_id"),
        "profile": profile,
        "route_index": row.get("route_index"),
        "scenario": scenario,
        "input_state": state,
        "exact_path_match": True,
        "exact_gst_sha256_match": True,
        "exact_serialized_record_sha256_match": True,
        "release_rom_sha256_match": True,
        "status": "pass",
    }


def seed_lineage(
    args: argparse.Namespace,
) -> dict[str, object]:
    snapshot = campaign.state_snapshot(args.seed_gst)
    if args.preflight_only:
        return {
            "mode": "harness_preflight_only",
            "final_acceptance_eligible": False,
            "campaign_summary": None,
            "seed_state": snapshot,
            "reason": (
                "explicit preflight bypass; rerun with the exact passing "
                "continuous-campaign input GST"
            ),
        }
    if args.campaign_summary is None:
        raise ValueError(
            "accepted evidence requires --campaign-summary; use "
            "--preflight-only only for harness development"
        )
    contract = campaign_input_contract(
        args.campaign_summary,
        profile=args.profile,
        scenario=args.scenario,
        seed_gst=args.seed_gst,
        rom_path=args.rom,
    )
    return {
        "mode": "continuous_campaign_exact_input",
        "final_acceptance_eligible": True,
        "campaign_summary": contract,
        "seed_state": snapshot,
    }


def cursor_coordinate(path: Path) -> tuple[int, int]:
    ram = mercenary.work_ram(path)
    return ram[CURSOR_X_ADDRESS], ram[CURSOR_Y_ADDRESS]


def runtime_group(path: Path, group_index: int) -> dict[str, object]:
    if not 0 <= group_index < RUNTIME_GROUP_COUNT:
        raise ValueError(f"runtime group index is invalid: {group_index}")
    ram = mercenary.work_ram(path)
    start = RUNTIME_GROUP_BASE + group_index * RUNTIME_GROUP_SIZE
    raw = ram[start:start + RUNTIME_GROUP_SIZE]
    if len(raw) != RUNTIME_GROUP_SIZE:
        raise ValueError("runtime group record is truncated")
    members = []
    for member_index in range(8):
        member_start = member_index * RUNTIME_MEMBER_SIZE
        record = raw[member_start:member_start + RUNTIME_MEMBER_SIZE]
        members.append(
            {
                "member_index": member_index,
                "class_id": record[0],
                "identity_id": record[1],
                "acted_flag": record[2],
                "hp": record[3],
                "x": record[6],
                "y": record[7],
                "record_hex": record.hex().upper(),
            }
        )
    return {
        "group_index": group_index,
        "side_id": raw[RUNTIME_SIDE_OFFSET],
        "level": raw[RUNTIME_LEVEL_OFFSET],
        "record_hex": raw.hex().upper(),
        "members": members,
    }


def source_target_model(
    rom: bytes,
    reference: bytes,
    target: LateTarget,
) -> dict[str, object]:
    model = read_scenario(rom, reference, target.scenario)
    record = model["records"][target.fixed_record_index]
    mercenary_class = record["mercenaries"][target.mercenary_index - 1]
    if record["hidden"]:
        raise ValueError("late surface target unexpectedly became hidden")
    if mercenary_class == 0xFF:
        raise ValueError("late surface target has no selected mercenary")
    return {
        "fixed_record_index": target.fixed_record_index,
        "fixed_record_offset": f"0x{record['offset']:06X}",
        "side_id": record["side_id"],
        "level": record["level"],
        "x": record["x"],
        "y": record["y"],
        "name_id": record["name"]["id"],
        "name_korean": record["name"]["ko"],
        "class_id": record["class_id"],
        "class_korean": record["class"]["ko"],
        "mercenary_index": target.mercenary_index,
        "mercenary_class_id": mercenary_class,
        "mercenary_class_korean": KOREAN_CLASS_NAMES[mercenary_class],
        # Stock fixed formations place member 1 immediately left of the root.
        "mercenary_x": record["x"] - 1,
        "mercenary_y": record["y"],
        "reason": target.reason,
    }


def runtime_target_report(
    group: dict[str, object],
    source: dict[str, object],
) -> dict[str, object]:
    commander = group["members"][0]
    subordinate = group["members"][int(source["mercenary_index"])]
    checks = {
        "commander_name_identity_exact": commander["identity_id"]
        == source["name_id"],
        "commander_class_exact": commander["class_id"] == source["class_id"],
        "commander_side_exact": group["side_id"] == source["side_id"],
        "commander_level_exact": group["level"] == source["level"],
        "commander_coordinate_exact": (
            commander["x"], commander["y"]
        ) == (source["x"], source["y"]),
        "commander_alive_and_visible": (
            commander["hp"] > 0
            and commander["x"] not in (0, 0xFF)
            and commander["y"] not in (0, 0xFF)
        ),
        "mercenary_member_index_exact": subordinate["member_index"]
        == source["mercenary_index"],
        "mercenary_class_exact": subordinate["class_id"]
        == source["mercenary_class_id"],
        "mercenary_coordinate_exact": (
            subordinate["x"], subordinate["y"]
        ) == (source["mercenary_x"], source["mercenary_y"]),
        "mercenary_alive_and_visible": (
            subordinate["hp"] > 0
            and subordinate["x"] not in (0, 0xFF)
            and subordinate["y"] not in (0, 0xFF)
        ),
    }
    return {
        "group_index": group["group_index"],
        "side_id": f"0x{int(group['side_id']):02X}",
        "level": group["level"],
        "record_hex": group["record_hex"],
        "commander": commander,
        "mercenary": subordinate,
        "expected_labels": {
            "name": source["name_korean"],
            "commander_class": source["class_korean"],
            "mercenary_class": source["mercenary_class_korean"],
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def complete_plane_a_occurrences(
    state: object,
    tile_start: int,
) -> tuple[int, list[dict[str, object]]]:
    rows = []
    counts = []
    for tile in range(tile_start, tile_start + 4):
        hits = plane_tile_hits(state, tile)
        count = sum(hit["plane"] == "plane_a" for hit in hits)
        counts.append(count)
        rows.append(
            {
                "tile": f"0x{tile:04X}",
                "plane_a_hits": count,
                "hits": hits,
            }
        )
    return min(counts), rows


def map_sprite_report(
    rom: bytes,
    gst: Path,
    class_id: int,
) -> dict[str, object]:
    state = load_gst(gst)
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2,
    )
    frames = []
    for frame_index, base in enumerate(builder.MAP_SPRITE_FRAME_BASES):
        source = base + sprite_id * builder.MAP_SPRITE_BYTES
        expected = rom[source:source + builder.MAP_SPRITE_BYTES]
        if len(expected) != builder.MAP_SPRITE_BYTES:
            raise ValueError("map sprite ROM payload is truncated")
        matches = []
        for start in range(0, len(state.vram) - len(expected) + 1, TILE_BYTES):
            if state.vram[start:start + len(expected)] != expected:
                continue
            linked, references = complete_plane_a_occurrences(
                state,
                start // TILE_BYTES,
            )
            matches.append(
                {
                    "vram_start": f"0x{start:04X}",
                    "tile_start": f"0x{start // TILE_BYTES:04X}",
                    "complete_plane_a_occurrences": linked,
                    "plane_references": references,
                }
            )
        frames.append(
            {
                "frame": frame_index,
                "rom_source_range": (
                    f"0x{source:06X}.."
                    f"0x{source + builder.MAP_SPRITE_BYTES - 1:06X}"
                ),
                "rom_source_sha256": sha256_bytes(expected),
                "vram_matches": matches,
                "payload_loaded_into_vram": bool(matches),
                "payload_linked_to_plane_a": any(
                    row["complete_plane_a_occurrences"] > 0 for row in matches
                ),
            }
        )
    checks = {
        "both_animation_frames_loaded_from_exact_rom_source": all(
            row["payload_loaded_into_vram"] for row in frames
        ),
        "hovered_map_unit_uses_one_exact_frame_on_plane_a": any(
            row["payload_linked_to_plane_a"] for row in frames
        ),
    }
    return {
        "class_id": f"0x{class_id:02X}",
        "class_korean": KOREAN_CLASS_NAMES[class_id],
        "generic_sprite_table_offset": (
            f"0x{builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2:06X}"
        ),
        "sprite_id": f"0x{sprite_id:04X}",
        "frames": frames,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def rgb_ratio(
    image: Image.Image,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> float:
    pixels = list(image.crop(box).getdata())
    return pixels.count(color) / len(pixels)


def status_surface_report(
    capture: Path,
    *,
    cursor: tuple[int, int],
    expected_coordinate: tuple[int, int],
    expected_name: str,
    expected_class: str,
    group_unchanged: bool,
    role: str,
) -> dict[str, object]:
    if role not in ("commander", "mercenary"):
        raise ValueError(f"unsupported enemy status role: {role}")
    with Image.open(capture) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"unexpected status capture dimensions: {image.size}")
    ratios = {
        "command_panel": rgb_ratio(image, STATUS_COMMAND_PANEL, DARK_BLUE),
        "detail_panel": rgb_ratio(image, STATUS_DETAIL_PANEL, DARK_BLUE),
        "bottom_status_and_exp_bar": rgb_ratio(
            image, STATUS_BOTTOM_BAR, DARK_BLUE
        ),
        "enemy_unit_message": rgb_ratio(
            image, ENEMY_UNIT_MESSAGE_PANEL, DARK_BLUE
        ),
    }
    checks = {
        "cursor_still_selects_exact_runtime_member": cursor
        == expected_coordinate,
        # Hostile units do not expose the allied action-command column.
        "allied_command_panel_absent": ratios["command_panel"] < 0.20,
        "enemy_unit_message_visible": ratios["enemy_unit_message"] >= 0.45,
        "role_specific_detail_surface": (
            ratios["detail_panel"] >= 0.30
            if role == "commander"
            else ratios["detail_panel"] < 0.20
        ),
        "bottom_status_bar_visible": ratios["bottom_status_and_exp_bar"]
        >= 0.30,
        "runtime_group_unchanged_by_status_open": group_unchanged,
    }
    return {
        **image_model(capture),
        "cursor": list(cursor),
        "expected_coordinate": list(expected_coordinate),
        "expected_runtime_labels": {
            "name": expected_name,
            "class": expected_class,
            "name_display_scope": (
                "commander detail"
                if role == "commander"
                else "owning hostile group; mercenary bottom bar is class-only"
            ),
        },
        "role": role,
        "dark_blue_ratios": {
            key: round(value, 6) for key, value in ratios.items()
        },
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def navigate(
    recorder: matrix.RuntimeRecorder,
    before: tuple[int, int],
    after: tuple[int, int],
) -> list[str]:
    keys = mercenary.move_keys(before, after)
    recorder.send(keys, delay=0.18)
    return keys


def verify_unit_surface(
    recorder: matrix.RuntimeRecorder,
    *,
    rom: bytes,
    group_index: int,
    coordinate: tuple[int, int],
    class_id: int,
    expected_name: str,
    expected_class: str,
    label: str,
) -> dict[str, object]:
    before_gst = recorder.save_gst(f"states/{label}_before_navigation.gst")
    before_cursor = cursor_coordinate(before_gst)
    navigation = navigate(recorder, before_cursor, coordinate)
    time.sleep(0.6)
    hover = recorder.capture(f"battle/{label}_hover.png")
    hover_gst = recorder.save_gst(f"states/{label}_hover.gst")
    hover_cursor = cursor_coordinate(hover_gst)
    if hover_cursor != coordinate:
        raise RuntimeError(
            f"{label} cursor navigation failed: {hover_cursor} != {coordinate}"
        )
    hover_group = runtime_group(hover_gst, group_index)
    sprite = map_sprite_report(rom, hover_gst, class_id)

    recorder.send(["c"], delay=1.2)
    detail = recorder.capture(f"battle/{label}_status_detail.png")
    detail_gst = recorder.save_gst(f"states/{label}_status_detail.gst")
    detail_cursor = cursor_coordinate(detail_gst)
    detail_group = runtime_group(detail_gst, group_index)
    status = status_surface_report(
        detail,
        cursor=detail_cursor,
        expected_coordinate=coordinate,
        expected_name=expected_name,
        expected_class=expected_class,
        group_unchanged=detail_group["record_hex"] == hover_group["record_hex"],
        role=label,
    )
    recorder.send(["b"], delay=0.9)
    returned = recorder.capture(f"battle/{label}_returned_map.png")
    if not battle_map_surface_visible(returned):
        raise RuntimeError(f"{label} status did not return to the battle map")
    return {
        "coordinate": list(coordinate),
        "class_id": f"0x{class_id:02X}",
        "class_korean": expected_class,
        "name_korean": expected_name,
        "navigation": navigation,
        "cursor_before": list(before_cursor),
        "cursor_hover": list(hover_cursor),
        "hover": image_model(hover),
        "hover_gst": file_model(hover_gst),
        "map_sprite": sprite,
        "status_detail": status,
        "detail_gst": file_model(detail_gst),
        "returned_map": image_model(returned),
        "status": (
            "pass"
            if sprite["status"] == "pass" and status["status"] == "pass"
            else "fail"
        ),
    }


def natural_combat_report(
    recorder: matrix.RuntimeRecorder,
    *,
    args: argparse.Namespace,
    output: Path,
) -> dict[str, object]:
    if args.scenario != 23:
        raise ValueError("natural side-view capture is scoped to Scenario 23")
    turns = []
    battle_rows: list[dict[str, object]] = []
    attacker_hashes: set[str] = set()
    for turn_attempt in range(1, args.natural_combat_turns + 1):
        selection = first_turn.select_turn_end(
            env=recorder.environment,
            display=args.display,
            opening_checks=args.max_turn_checks,
            delay=args.turn_delay,
        )
        if args.emulator_speed:
            recorder.send([str(args.emulator_speed)], delay=0.5)
        prefix = output / f"battle/natural_turn/turn_{turn_attempt}/detect.png"
        endpoint, confirmations = first_turn.run_detector(
            display=args.display,
            max_checks=args.max_turn_checks,
            delay=args.turn_delay,
            capture_prefix=prefix,
        )
        accepted = (
            output
            / f"battle/natural_turn/turn_{turn_attempt}/side_view.png"
        )
        retained = movement.retained_turn_combat_report(prefix, accepted)
        turn_surfaces = []
        turn_hashes: set[str] = set()
        for row in retained["combat_frames"]:
            capture_path = resolve_report_path(row["capture"]["path"])
            surface = mounted.battle_surface_report(capture_path)
            turn_surfaces.append(surface)
            battle_rows.append(surface)
            digest = str(surface["attacker_crop_sha256"])
            turn_hashes.add(digest)
            attacker_hashes.add(digest)
        turn_checks = {
            "returned_to_next_turn_command": endpoint == "turn_command",
            "combat_episode_observed": retained["combat_episode_count"] >= 1,
            "multiple_side_view_frames_retained": retained[
                "combat_frame_count"
            ] >= 2,
            "side_view_attacker_region_animated": len(turn_hashes) >= 2,
            "all_retained_frames_are_side_view": bool(turn_surfaces)
            and all(row["battle_surface_visible"] for row in turn_surfaces),
        }
        turns.append(
            {
                "turn_attempt": turn_attempt,
                "selection": selection,
                "endpoint": endpoint,
                "detector_confirmations": confirmations,
                "retained": retained,
                "battle_surfaces": turn_surfaces,
                "unique_attacker_crop_sha256": sorted(turn_hashes),
                "checks": turn_checks,
                "motion_status": (
                    "pass"
                    if all(
                        turn_checks[key]
                        for key in (
                            "combat_episode_observed",
                            "multiple_side_view_frames_retained",
                            "side_view_attacker_region_animated",
                            "all_retained_frames_are_side_view",
                        )
                    )
                    else "not_observed"
                ),
            }
        )
        if turns[-1]["motion_status"] == "pass":
            break
        if endpoint != "turn_command":
            break
    accepted_turns = [row for row in turns if row["motion_status"] == "pass"]
    checks = {
        "every_attempt_returned_to_next_turn_command": all(
            row["checks"]["returned_to_next_turn_command"] for row in turns
        ),
        "one_or_more_natural_combat_episodes": any(
            row["retained"]["combat_episode_count"] >= 1 for row in turns
        ),
        "multiple_side_view_frames_retained": len(battle_rows) >= 2,
        "side_view_attacker_region_animated": len(attacker_hashes) >= 2,
        "all_retained_frames_are_side_view": bool(battle_rows) and all(
            row["battle_surface_visible"] for row in battle_rows
        ),
        "one_turn_has_complete_motion_proof": len(accepted_turns) == 1,
    }
    return {
        "scenario": 23,
        "emulator_speed_slot": args.emulator_speed,
        "emulator_speed_percent": first_turn.EMULATOR_SPEED_PERCENT[
            args.emulator_speed
        ],
        "maximum_turns": args.natural_combat_turns,
        "turns_attempted": len(turns),
        "expected_natural_matchup_for_manual_review": (
            "Paladin versus Hawk Knight (stock enemy phase after TURN 2)"
        ),
        "turns": turns,
        "accepted_turn_attempt": (
            accepted_turns[0]["turn_attempt"] if accepted_turns else None
        ),
        "battle_surfaces": battle_rows,
        "unique_attacker_crop_sha256": sorted(attacker_hashes),
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    target = TARGETS[args.scenario]
    output = args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    if output.exists():
        raise FileExistsError(f"late surface output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = (
        f"late-enemy-{args.profile}-s{args.scenario:02d}-{args.run_id}"
    )
    runtime_home = args.runtime_root / runtime_name
    if runtime_home.exists():
        raise FileExistsError(f"late surface runtime already exists: {runtime_home}")
    recorder = matrix.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    rom_hash_before = sha256_path(args.rom)
    seed_hash_before = sha256_path(args.seed_gst)
    lineage = seed_lineage(args)
    rom = args.rom.read_bytes()
    reference = args.reference_rom.read_bytes()
    source = source_target_model(rom, reference, target)
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            args.scenario,
            runtime_name,
            output,
        )
        recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, output)
        command = recorder.capture("battle/turn1_command.png")
        command_gst = recorder.save_gst("states/turn1_command.gst")
        player_count = matrix.player_commander_count(rom, args.scenario)
        group_index = player_count + target.fixed_record_index
        initial_group = runtime_group(command_gst, group_index)
        runtime_target = runtime_target_report(initial_group, source)
        if runtime_target["status"] != "pass":
            raise RuntimeError("late runtime target differs from its fixed record")

        recorder.send(["b"], delay=0.9)
        commander_surface = verify_unit_surface(
            recorder,
            rom=rom,
            group_index=group_index,
            coordinate=(int(source["x"]), int(source["y"])),
            class_id=int(source["class_id"]),
            expected_name=str(source["name_korean"]),
            expected_class=str(source["class_korean"]),
            label="commander",
        )
        mercenary_surface = verify_unit_surface(
            recorder,
            rom=rom,
            group_index=group_index,
            coordinate=(int(source["mercenary_x"]), int(source["mercenary_y"])),
            class_id=int(source["mercenary_class_id"]),
            expected_name=str(source["name_korean"]),
            expected_class=str(source["mercenary_class_korean"]),
            label="mercenary",
        )
        post_surface_gst = recorder.save_gst("states/post_surface_checks.gst")
        post_surface_group = runtime_group(post_surface_gst, group_index)
        natural = None
        if args.capture_natural_combat:
            natural = natural_combat_report(recorder, args=args, output=output)

        final_gst = recorder.save_gst("states/final.gst")
        rom_hash_after = sha256_path(args.rom)
        seed_hash_after = sha256_path(args.seed_gst)
        checks = {
            "scenario_identity_pass": identity.get("status") == "pass",
            "runtime_target_exact": runtime_target["status"] == "pass",
            "runtime_group_unchanged_by_surface_checks": post_surface_group[
                "record_hex"
            ] == initial_group["record_hex"],
            "commander_surface_pass": commander_surface["status"] == "pass",
            "mercenary_surface_pass": mercenary_surface["status"] == "pass",
            "natural_combat_pass_when_requested": (
                natural is None or natural["status"] == "pass"
            ),
            "release_rom_unchanged": rom_hash_after == rom_hash_before,
            "input_seed_gst_unchanged": seed_hash_after == seed_hash_before,
        }
        result = {
            "schema_version": 1,
            "status": "pass" if all(checks.values()) else "fail",
            "release_acceptance_eligible": bool(
                lineage["final_acceptance_eligible"] and all(checks.values())
            ),
            "profile": args.profile,
            "scenario": args.scenario,
            "run_id": args.run_id,
            "rom": {
                "path": relative(args.rom),
                "sha256_before": rom_hash_before,
                "sha256_after": rom_hash_after,
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "seed_gst": {
                "path": relative(args.seed_gst),
                "sha256_before": seed_hash_before,
                "sha256_after": seed_hash_after,
            },
            "seed_lineage": lineage,
            "scenario_identity": identity,
            "source_target": source,
            "runtime_group_index": group_index,
            "player_group_count": player_count,
            "runtime_target": runtime_target,
            "turn1_command": image_model(command),
            "turn1_command_gst": file_model(command_gst),
            "commander_surface": commander_surface,
            "mercenary_surface": mercenary_surface,
            "post_surface_gst": file_model(post_surface_gst),
            "natural_combat": natural,
            "final_gst": file_model(final_gst),
            "checks": checks,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "release_acceptance_eligible": False,
            "profile": args.profile,
            "scenario": args.scenario,
            "run_id": args.run_id,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "rom_sha256": rom_hash_before,
            "seed_gst_sha256": seed_hash_before,
            "seed_lineage": lineage,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("pure", "normal", "hard"), required=True)
    parser.add_argument("--scenario", type=int, choices=SCENARIOS, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, required=True)
    parser.add_argument("--campaign-summary", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--capture-natural-combat", action="store_true")
    parser.add_argument("--reference-rom", type=Path, default=DEFAULT_REFERENCE_ROM)
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
    parser.add_argument("--max-turn-checks", type=int, default=240)
    parser.add_argument("--turn-delay", type=float, default=0.25)
    parser.add_argument("--natural-combat-turns", type=int, default=2)
    parser.add_argument(
        "--emulator-speed",
        type=int,
        choices=tuple(first_turn.EMULATOR_SPEED_PERCENT),
        default=4,
        help=(
            "BlastEm host speed slot after selecting turn end; slot 4 is "
            "400%% and matches the full first-turn validator"
        ),
    )
    return parser


def normalize_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    for name in (
        "rom",
        "seed_gst",
        "reference_rom",
        "xvfb",
        "xvfb_library_path",
        "output_root",
        "runtime_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    if args.campaign_summary is not None:
        args.campaign_summary = args.campaign_summary.resolve()
    if args.preflight_only and args.campaign_summary is not None:
        parser.error("--preflight-only and --campaign-summary are mutually exclusive")
    if not args.preflight_only and args.campaign_summary is None:
        parser.error("accepted runs require --campaign-summary")
    if args.capture_natural_combat and args.scenario != 23:
        parser.error("--capture-natural-combat is supported only for Scenario 23")
    if args.max_turn_checks < 1:
        parser.error("--max-turn-checks must be positive")
    if not 1 <= args.natural_combat_turns <= 4:
        parser.error("--natural-combat-turns must be 1..4")
    if args.turn_delay < 0.1:
        parser.error("--turn-delay must be at least 0.1 seconds")
    if not args.display.startswith(":"):
        parser.error("--display must use :N syntax")
    try:
        display_number = int(args.display[1:])
    except ValueError:
        parser.error("--display must use :N syntax")
    if display_number < parallel.MIN_ISOLATED_DISPLAY_NUMBER:
        parser.error("--display must be a high-numbered isolated Xvfb display")
    for label, path in (
        ("release ROM", args.rom),
        ("seed GST", args.seed_gst),
        ("Japanese reference ROM", args.reference_rom),
        ("Xvfb", args.xvfb),
        ("Xvfb library path", args.xvfb_library_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.campaign_summary is not None and not args.campaign_summary.is_file():
        raise FileNotFoundError(
            f"campaign summary does not exist: {args.campaign_summary}"
        )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    normalize_args(args, parser)
    report = run_probe(args)
    eligibility = (
        "release-eligible" if report["release_acceptance_eligible"] else "preflight-only"
    )
    print(
        f"{report['status']}: {args.profile} Scenario {args.scenario} "
        f"late enemy surfaces ({eligibility})"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
