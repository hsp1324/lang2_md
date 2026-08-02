#!/usr/bin/env python3
"""Hire, move, and verify an ordinary mercenary's active/acted sprites."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools.verify_preparation_surface_evidence import (
    expand_gray_source_mask,
    load_gst,
    plane_tile_hits,
)


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/pike_acted_surface_probe"
DEFAULT_DISPLAY = ":171"
SCENARIO = 12
SHERRY_COMMANDER_ID = 4
SHERRY_CLASS_ID = 0x01
PIKE_CLASS_ID = 0x62
MONK_CLASS_ID = 0x6C
HIRED_COUNT = 6
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
GROUP_COUNT = 40
PIKE_GRAY_TILE_START = 0x03B0
PIKE_GRAY_TILE_COUNT = 4
PIKE_GRAY_VRAM_START = PIKE_GRAY_TILE_START * 32
PIKE_GRAY_VRAM_BYTES = PIKE_GRAY_TILE_COUNT * 32
ORDINARY_GRAY_TILE_START = 0x03B0
ORDINARY_GRAY_TILES_PER_CLASS = 4
ORDINARY_ACTIVE_TILE_START = 0x0348
ORDINARY_ACTIVE_TILES_PER_CLASS = 4
SECOND_FRAME_TILE_DELTA = 0x0100
GRAY_SOURCE_MASK_BASE = 0x0510C0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        # Release/user ROMs can intentionally live on the Windows-mounted
        # Desktop.  Keep their absolute path in diagnostic evidence instead
        # of failing after the complete emulator run has finished.
        return str(resolved)


def work_ram(path: Path) -> bytes:
    payload = path.read_bytes()
    ram = payload[0x2478:0x2478 + 0x10000]
    if len(ram) != 0x10000:
        raise ValueError(f"GST is missing work RAM: {path}")
    return ram


def runtime_groups(path: Path) -> list[dict[str, object]]:
    ram = work_ram(path)
    groups = []
    for group_index in range(GROUP_COUNT):
        group_start = RUNTIME_GROUP_BASE + group_index * RUNTIME_GROUP_SIZE
        members = []
        for member_index in range(8):
            start = group_start + member_index * RUNTIME_MEMBER_SIZE
            record = ram[start:start + RUNTIME_MEMBER_SIZE]
            members.append(
                {
                    "member_index": member_index,
                    "class_id": record[0],
                    "commander_id": record[1],
                    "acted_flag": record[2],
                    "hp": record[3],
                    "x": record[6],
                    "y": record[7],
                    "record": record.hex(),
                }
            )
        if members[0]["class_id"] != 0xFF:
            groups.append({"group_index": group_index, "members": members})
    return groups


def commander_group(path: Path, commander_id: int) -> dict[str, object]:
    matches = [
        group
        for group in runtime_groups(path)
        if group["members"][0]["commander_id"] == commander_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one commander {commander_id} runtime group, "
            f"got {len(matches)}"
        )
    return matches[0]


def member_summary(member: dict[str, object]) -> dict[str, object]:
    return {
        **member,
        "class_id": f"0x{member['class_id']:02X}",
    }


def ordinary_gray_tile_start(class_id: int) -> int:
    first = builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS
    last = builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS
    if not first <= class_id <= last:
        raise ValueError(f"class 0x{class_id:02X} is not an ordinary mercenary")
    return ORDINARY_GRAY_TILE_START + (
        class_id - first
    ) * ORDINARY_GRAY_TILES_PER_CLASS


def expected_mercenary_gray(
    rom: bytes,
    class_id: int,
) -> tuple[int, int, bytes]:
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2,
    )
    source = GRAY_SOURCE_MASK_BASE + sprite_id * 0x40
    mask = rom[source:source + 0x40]
    return sprite_id, source, expand_gray_source_mask(mask)


def complete_plane_a_sprite_occurrences(
    references: list[dict[str, object]],
) -> int:
    """Count complete four-tile sprites backed by one cache frame."""
    if len(references) != ORDINARY_ACTIVE_TILES_PER_CLASS:
        raise ValueError("active mercenary frame must reference four tiles")
    return min(
        sum(hit["plane"] == "plane_a" for hit in row["hits"])
        for row in references
    )


def mercenary_active_report(
    rom: bytes,
    gst: Path,
    class_id: int,
) -> dict[str, object]:
    state = load_gst(gst)
    class_index = class_id - builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS
    tile_start = (
        ORDINARY_ACTIVE_TILE_START
        + class_index * ORDINARY_ACTIVE_TILES_PER_CLASS
    )
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2,
    )
    frames = []
    for frame, frame_tile in (
        (0, tile_start),
        (1, tile_start + SECOND_FRAME_TILE_DELTA),
    ):
        source = (
            builder.MAP_SPRITE_FRAME_BASES[frame]
            + sprite_id * builder.MAP_SPRITE_BYTES
        )
        expected = rom[source:source + builder.MAP_SPRITE_BYTES]
        vram_start = frame_tile * 32
        actual = state.vram[
            vram_start:vram_start + builder.MAP_SPRITE_BYTES
        ]
        references = [
            {
                "tile": f"0x{tile:04X}",
                "hits": plane_tile_hits(state, tile),
            }
            for tile in range(
                frame_tile,
                frame_tile + ORDINARY_ACTIVE_TILES_PER_CLASS,
            )
        ]
        complete_occurrences = complete_plane_a_sprite_occurrences(
            references
        )
        frames.append({
            "frame": frame,
            "source": f"0x{source:06X}..0x{source + 0x7F:06X}",
            "tile_range": f"0x{frame_tile:04X}..0x{frame_tile + 3:04X}",
            "vram_range": (
                f"0x{vram_start:04X}.."
                f"0x{vram_start + builder.MAP_SPRITE_BYTES - 1:04X}"
            ),
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "actual_sha256": hashlib.sha256(actual).hexdigest(),
            "matches_rom_source": actual == expected,
            "plane_references": references,
            # A complete 16x16 unit contributes one Plane A reference to
            # each of its four tiles.  Taking the minimum count therefore
            # proves that at least this many on-map units actually point at
            # the verified cache payload; unrelated Window/UI references do
            # not satisfy the check.
            "complete_plane_a_sprite_occurrences": complete_occurrences,
        })
    return {
        "class_id": f"0x{class_id:02X}",
        "class_korean": builder.KOREAN_CLASS_LABELS[class_id],
        "sprite_id": f"0x{sprite_id:04X}",
        "frames": frames,
        "both_frames_match_rom_source": all(
            row["matches_rom_source"] for row in frames
        ),
        "one_animation_frame_visible": any(
            row["complete_plane_a_sprite_occurrences"] > 0
            for row in frames
        ),
        "max_complete_plane_a_sprite_occurrences": max(
            row["complete_plane_a_sprite_occurrences"] for row in frames
        ),
    }


def mercenary_gray_report(
    rom: bytes,
    gst: Path,
    class_id: int,
) -> dict[str, object]:
    state = load_gst(gst)
    tile_start = ordinary_gray_tile_start(class_id)
    vram_start = tile_start * 32
    sprite_id, source, expected = expected_mercenary_gray(rom, class_id)
    actual = state.vram[
        vram_start:vram_start + PIKE_GRAY_VRAM_BYTES
    ]
    references = [
        {
            "tile": f"0x{tile:04X}",
            "hits": plane_tile_hits(state, tile),
        }
        for tile in range(
            tile_start,
            tile_start + PIKE_GRAY_TILE_COUNT,
        )
    ]
    return {
        "class_id": f"0x{class_id:02X}",
        "class_korean": builder.KOREAN_CLASS_LABELS[class_id],
        "sprite_id": f"0x{sprite_id:04X}",
        "source": f"0x{source:06X}..0x{source + 0x3F:06X}",
        "vram": (
            f"0x{vram_start:04X}.."
            f"0x{vram_start + PIKE_GRAY_VRAM_BYTES - 1:04X}"
        ),
        "expected_sha256": hashlib.sha256(expected).hexdigest(),
        "actual_sha256": hashlib.sha256(actual).hexdigest(),
        "matches_stock_silhouette_expansion": actual == expected,
        "plane_references": references,
        "all_four_tiles_visible": all(row["hits"] for row in references),
    }


def ordinary_gray_cache_report(rom: bytes, gst: Path) -> dict[str, object]:
    state = load_gst(gst)
    rows = []
    for index, class_id in enumerate(
        range(
            builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS,
            builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS + 1,
        )
    ):
        sprite_id = builder.be16(
            rom,
            builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2,
        )
        source = GRAY_SOURCE_MASK_BASE + sprite_id * 0x40
        expected = expand_gray_source_mask(rom[source:source + 0x40])
        tile = ORDINARY_GRAY_TILE_START + index * ORDINARY_GRAY_TILES_PER_CLASS
        start = tile * 32
        actual = state.vram[start:start + len(expected)]
        rows.append(
            {
                "class_id": f"0x{class_id:02X}",
                "class_korean": builder.KOREAN_CLASS_LABELS[class_id],
                "sprite_id": f"0x{sprite_id:04X}",
                "tile_range": f"0x{tile:04X}..0x{tile + 3:04X}",
                "vram_range": f"0x{start:04X}..0x{start + 0x7F:04X}",
                "expected_sha256": hashlib.sha256(expected).hexdigest(),
                "actual_sha256": hashlib.sha256(actual).hexdigest(),
                "matches_stock_silhouette_expansion": actual == expected,
            }
        )
    return {
        "class_count": len(rows),
        "tile_range": "0x03B0..0x03EF",
        "vram_range": "0x7600..0x7DFF",
        "all_match_stock_silhouette_expansion": all(
            row["matches_stock_silhouette_expansion"] for row in rows
        ),
        "classes": rows,
    }


def move_keys(before: tuple[int, int], after: tuple[int, int]) -> list[str]:
    x0, y0 = before
    x1, y1 = after
    horizontal = ["right"] * max(0, x1 - x0) + ["left"] * max(0, x0 - x1)
    vertical = ["down"] * max(0, y1 - y0) + ["up"] * max(0, y0 - y1)
    return horizontal + vertical


def occupied_coordinates(groups: list[dict[str, object]]) -> set[tuple[int, int]]:
    return {
        (member["x"], member["y"])
        for group in groups
        for member in group["members"]
        if member["class_id"] != 0xFF and member["hp"] > 0
    }


def movement_candidates(
    groups: list[dict[str, object]],
    group: dict[str, object],
    class_id: int,
) -> list[tuple[dict[str, object], str]]:
    occupied = occupied_coordinates(groups)
    directions = (
        ("down", 0, 1),
        ("right", 1, 0),
        ("left", -1, 0),
        ("up", 0, -1),
    )
    result = []
    for member in group["members"][1:]:
        if member["class_id"] != class_id or member["hp"] <= 0:
            continue
        for direction, dx, dy in directions:
            destination = (member["x"] + dx, member["y"] + dy)
            if destination not in occupied:
                result.append((member, direction))
    return result


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
            str(RUN_SEQUENCE),
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


def launch_and_hire(
    recorder: matrix.RuntimeRecorder,
    args: argparse.Namespace,
    output: Path,
    runtime_name: str,
) -> Path:
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "scenario-select",
            "--rom", str(args.rom),
            "--scenario-number", str(args.scenario),
            "--runtime-name", runtime_name,
            "--manual-slot-gst", str(args.seed_gst),
            "--manual-slot-commander-id", str(args.commander_id),
            "--manual-slot-level", str(args.commander_level),
            "--manual-slot-experience", str(args.commander_experience),
            "--manual-slot-class", f"0x{args.commander_class:02X}",
            "--manual-slot-hire-mask-or", f"0x{args.hire_mask_or:04X}",
            "--initial-delay", "12.0",
            "--virtual-display", args.display,
            "--replace-existing",
            "--send-event",
        ]
    )
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "detect-prep",
            "--rom", str(args.rom),
            "--no-launch",
            "--confirmation-delay", "0.8",
            "--max-confirmations", "80",
            "--capture-prefix", str(output / "briefing/detect.png"),
            "--virtual-display", args.display,
            "--send-event",
        ]
    )
    commander_ids = matrix.player_commander_ids(
        args.rom.read_bytes(), args.scenario
    )
    selection_steps = commander_ids.index(args.commander_id)
    # Depending on the exact frame at which detect-prep returns, the cursor is
    # either still on the root `고용` command or already on commander 1.  One
    # confirm therefore either enters the commander roster or opens commander
    # 1's hire list.  Normalize both states back to commander 1 before moving.
    recorder.send(["c"], delay=1.1)
    normalized = recorder.capture("preparation/commander_normalize.png")
    if matrix.hire_screen_visible(normalized):
        first_commander_id = commander_ids[0]
        first_row = next(
            row
            for row in matrix.manual_slot_roster(args.seed_gst)
            if row["commander_id"] == first_commander_id
        )
        first_mask = int(first_row["hire_mask"], 0)
        if first_commander_id == args.commander_id:
            first_mask |= args.hire_mask_or
        visible_rows = min(
            matrix.HIRE_PAGE_SIZE,
            len(matrix.hire_rows(first_mask)),
        )
        recorder.send(["down"] * visible_rows, delay=0.8)
        recorder.send(["c"], delay=1.0)
        recorder.capture("preparation/commander_after_close.png")
        recorder.send(["c"], delay=1.0)
    if selection_steps:
        recorder.send(["down"] * selection_steps, delay=0.9)
    recorder.capture("preparation/commander_selected.png")
    recorder.send(["c"], delay=1.1)
    opened = recorder.capture("preparation/hire_open.png")
    if not matrix.hire_screen_visible(opened):
        raise RuntimeError("target mercenary hire screen did not open")
    if args.target_page:
        recorder.send(["right"] * args.target_page, delay=0.9)
    if args.target_row:
        recorder.send(["down"] * args.target_row, delay=0.8)
    for count in range(1, args.hired_count + 1):
        recorder.send(["c"], delay=0.7)
        recorder.capture(f"preparation/hired_{count}.png")
    hired_gst = recorder.save_gst("states/after_hire.gst")
    group = commander_group(hired_gst, args.commander_id)
    classes = [
        member["class_id"]
        for member in group["members"][1:1 + args.hired_count]
    ]
    if classes != [args.mercenary_class] * args.hired_count:
        raise RuntimeError(
            "hired member classes do not match target "
            f"0x{args.mercenary_class:02X}: {classes}"
        )
    recorder.send(
        ["down"] * (args.page_row_count - args.target_row),
        delay=0.8,
    )
    recorder.send(["c"], delay=1.1)
    return hired_gst


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"merc-acted-{args.mercenary_class:02x}-{args.run_id}"
    runtime_home = ROOT / "captures/runtime" / runtime_name
    recorder = matrix.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        hired_gst = launch_and_hire(recorder, args, output, runtime_name)
        enter_battle_command(recorder, args.rom, output)
        active_command_capture = recorder.capture(
            "battle/active_command.png"
        )
        active_command_gst = recorder.save_gst(
            "states/active_command.gst"
        )
        # The command window can cover half of a 16x16 mercenary and made the
        # old verifier accept a correct cache payload without proving that an
        # actual unit used all four tiles.  Close it before taking the active
        # sprite evidence so the map linkage is observable.
        recorder.send(["b"], delay=0.8)
        active_capture = recorder.capture("battle/active_map.png")
        active_gst = recorder.save_gst("states/active_map.gst")
        groups_before = runtime_groups(active_gst)
        target_group_before = commander_group(active_gst, args.commander_id)
        active_report = mercenary_active_report(
            args.rom.read_bytes(),
            active_gst,
            args.mercenary_class,
        )
        ordinary_gray_before = ordinary_gray_cache_report(
            args.rom.read_bytes(), active_gst
        )
        candidates = movement_candidates(
            groups_before,
            target_group_before,
            args.mercenary_class,
        )
        if not candidates:
            raise RuntimeError(
                "no deployed target mercenary has an unoccupied adjacent tile"
            )
        mercenary_before, direction = candidates[0]
        commander_before = groups_before[0]["members"][0]

        # The command menu was closed for the active-map linkage proof above.
        # Move the map cursor to the chosen mercenary, then apply Move and
        # Standby.
        navigation = move_keys(
            (commander_before["x"], commander_before["y"]),
            (mercenary_before["x"], mercenary_before["y"]),
        )
        recorder.send(navigation, delay=0.18)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=0.8)
        recorder.send([direction], delay=0.6)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=1.4)
        acted_capture = recorder.capture("battle/mercenary_acted_gray.png")
        acted_gst = recorder.save_gst("states/mercenary_acted_gray.gst")
        target_group_after = commander_group(acted_gst, args.commander_id)
        mercenary_after = target_group_after["members"][
            mercenary_before["member_index"]
        ]
        coordinate_changed = (
            mercenary_before["x"], mercenary_before["y"]
        ) != (mercenary_after["x"], mercenary_after["y"])
        gray_report = mercenary_gray_report(
            args.rom.read_bytes(),
            acted_gst,
            args.mercenary_class,
        )
        ordinary_gray_after = ordinary_gray_cache_report(
            args.rom.read_bytes(), acted_gst
        )
        passed = (
            mercenary_before["class_id"]
            == mercenary_after["class_id"]
            == args.mercenary_class
            and mercenary_before["acted_flag"] == 0
            and mercenary_after["acted_flag"] == 1
            and coordinate_changed
            and active_report["both_frames_match_rom_source"]
            and active_report["one_animation_frame_visible"]
            and gray_report["matches_stock_silhouette_expansion"]
            and gray_report["all_four_tiles_visible"]
            and ordinary_gray_before["all_match_stock_silhouette_expansion"]
            and ordinary_gray_after["all_match_stock_silhouette_expansion"]
        )
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "rom": {
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario": args.scenario,
            "commander_id": args.commander_id,
            "commander_class_id": f"0x{args.commander_class:02X}",
            "hired_class": builder.KOREAN_CLASS_LABELS[args.mercenary_class],
            "hired_class_id": f"0x{args.mercenary_class:02X}",
            "hired_count": args.hired_count,
            "hired_gst": relative(hired_gst),
            "hired_gst_sha256": sha256(hired_gst),
            "active_command_capture": relative(active_command_capture),
            "active_command_capture_sha256": sha256(
                active_command_capture
            ),
            "active_command_gst": relative(active_command_gst),
            "active_command_gst_sha256": sha256(active_command_gst),
            "active_capture": relative(active_capture),
            "active_capture_sha256": sha256(active_capture),
            "active_gst": relative(active_gst),
            "active_gst_sha256": sha256(active_gst),
            "acted_capture": relative(acted_capture),
            "acted_capture_sha256": sha256(acted_capture),
            "acted_gst": relative(acted_gst),
            "acted_gst_sha256": sha256(acted_gst),
            "navigation_from_group_zero": navigation,
            "move_direction": direction,
            "mercenary_before": member_summary(mercenary_before),
            "mercenary_after": member_summary(mercenary_after),
            "coordinate_changed": coordinate_changed,
            "mercenary_active_cache": active_report,
            "mercenary_gray_cache": gray_report,
            "ordinary_gray_cache_before_move": ordinary_gray_before,
            "ordinary_gray_cache_after_move": ordinary_gray_after,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--commander-id", type=int, default=SHERRY_COMMANDER_ID)
    parser.add_argument(
        "--commander-class",
        type=lambda value: int(value, 0),
        default=SHERRY_CLASS_ID,
    )
    parser.add_argument("--commander-level", type=int, default=9)
    parser.add_argument("--commander-experience", type=int, default=15)
    parser.add_argument(
        "--hire-mask-or",
        type=lambda value: int(value, 0),
        default=0x0001,
    )
    parser.add_argument(
        "--mercenary-class",
        type=lambda value: int(value, 0),
        default=PIKE_CLASS_ID,
    )
    parser.add_argument("--scenario", type=int, default=SCENARIO)
    parser.add_argument("--target-page", type=int, default=0)
    parser.add_argument("--target-row", type=int, default=0)
    parser.add_argument("--page-row-count", type=int, default=2)
    parser.add_argument("--hired-count", type=int, default=HIRED_COUNT)
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    for name in (
        "rom", "seed_gst", "xvfb", "xvfb_library_path", "output_root"
    ):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if not 1 <= args.commander_id <= matrix.MANUAL_SLOT_COMMANDER_COUNT:
        parser.error("--commander-id is outside the saved roster")
    if not 1 <= args.scenario <= 27:
        parser.error("--scenario must be 1..27")
    if not 0 <= args.commander_class < len(builder.KOREAN_CLASS_LABELS):
        parser.error("--commander-class is outside the class table")
    if not 0 <= args.commander_level <= 99:
        parser.error("--commander-level must be 0..99")
    if not 0 <= args.commander_experience <= 99:
        parser.error("--commander-experience must be 0..99")
    if not 0 <= args.hire_mask_or <= 0xFFFF:
        parser.error("--hire-mask-or must be 0..0xFFFF")
    try:
        ordinary_gray_tile_start(args.mercenary_class)
    except ValueError as exc:
        parser.error(str(exc))
    if not 0 <= args.target_page <= 5:
        parser.error("--target-page must be 0..5")
    if not 0 <= args.target_row < args.page_row_count <= 3:
        parser.error("target row/page-row count must describe a 1..3 row page")
    if not 1 <= args.hired_count <= HIRED_COUNT:
        parser.error(f"--hired-count must be 1..{HIRED_COUNT}")
    result = run_probe(args)
    print(
        f"{result['status']}: Scenario {args.scenario} commander "
        f"{args.commander_id} hired {args.hired_count} "
        f"{result['hired_class']} mercenaries; acted-gray cache "
        f"{result['mercenary_gray_cache']['actual_sha256']}"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
