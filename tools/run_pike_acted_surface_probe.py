#!/usr/bin/env python3
"""Hire, move, and verify an actual Pike's acted-gray battle sprite."""

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
GRAY_SOURCE_MASK_BASE = 0x0510C0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


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


def sherry_group(path: Path) -> dict[str, object]:
    matches = [
        group
        for group in runtime_groups(path)
        if group["members"][0]["commander_id"] == SHERRY_COMMANDER_ID
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one Sherry runtime group, got {len(matches)}")
    return matches[0]


def member_summary(member: dict[str, object]) -> dict[str, object]:
    return {
        **member,
        "class_id": f"0x{member['class_id']:02X}",
    }


def expected_pike_gray(rom: bytes) -> tuple[int, int, bytes]:
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + PIKE_CLASS_ID * 2,
    )
    source = GRAY_SOURCE_MASK_BASE + sprite_id * 0x40
    mask = rom[source:source + 0x40]
    return sprite_id, source, expand_gray_source_mask(mask)


def pike_gray_report(rom: bytes, gst: Path) -> dict[str, object]:
    state = load_gst(gst)
    sprite_id, source, expected = expected_pike_gray(rom)
    actual = state.vram[
        PIKE_GRAY_VRAM_START:PIKE_GRAY_VRAM_START + PIKE_GRAY_VRAM_BYTES
    ]
    references = [
        {
            "tile": f"0x{tile:04X}",
            "hits": plane_tile_hits(state, tile),
        }
        for tile in range(
            PIKE_GRAY_TILE_START,
            PIKE_GRAY_TILE_START + PIKE_GRAY_TILE_COUNT,
        )
    ]
    return {
        "class_id": f"0x{PIKE_CLASS_ID:02X}",
        "class_korean": builder.KOREAN_CLASS_LABELS[PIKE_CLASS_ID],
        "sprite_id": f"0x{sprite_id:04X}",
        "source": f"0x{source:06X}..0x{source + 0x3F:06X}",
        "vram": (
            f"0x{PIKE_GRAY_VRAM_START:04X}.."
            f"0x{PIKE_GRAY_VRAM_START + PIKE_GRAY_VRAM_BYTES - 1:04X}"
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
        if member["class_id"] != PIKE_CLASS_ID or member["hp"] <= 0:
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
            "--scenario-number", str(SCENARIO),
            "--runtime-name", runtime_name,
            "--manual-slot-gst", str(args.seed_gst),
            "--manual-slot-commander-id", str(SHERRY_COMMANDER_ID),
            "--manual-slot-level", "9",
            "--manual-slot-experience", "15",
            "--manual-slot-class", f"0x{SHERRY_CLASS_ID:02X}",
            "--manual-slot-hire-mask-or", "0x0001",
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
    commander_ids = matrix.player_commander_ids(args.rom.read_bytes(), SCENARIO)
    selection_steps = commander_ids.index(SHERRY_COMMANDER_ID)
    if selection_steps:
        recorder.send(["down"] * selection_steps, delay=0.9)
    recorder.capture("preparation/sherry_selected.png")
    recorder.send(["c"], delay=1.1)
    opened = recorder.capture("preparation/hire_open.png")
    if not matrix.hire_screen_visible(opened):
        raise RuntimeError("Sherry's Pike hire screen did not open")
    for count in range(1, HIRED_COUNT + 1):
        recorder.send(["c"], delay=0.7)
        recorder.capture(f"preparation/hired_{count}.png")
    hired_gst = recorder.save_gst("states/after_hire.gst")
    group = sherry_group(hired_gst)
    classes = [member["class_id"] for member in group["members"][1:7]]
    if classes != [PIKE_CLASS_ID] * HIRED_COUNT:
        raise RuntimeError(f"hired member classes are not six Pikes: {classes}")
    # Pike, Lizardman, END.
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.1)
    return hired_gst


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"pike-acted-{args.run_id}"
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
        active_capture = recorder.capture("battle/active_command.png")
        active_gst = recorder.save_gst("states/active_command.gst")
        groups_before = runtime_groups(active_gst)
        pike_group_before = sherry_group(active_gst)
        ordinary_gray_before = ordinary_gray_cache_report(
            args.rom.read_bytes(), active_gst
        )
        candidates = movement_candidates(groups_before, pike_group_before)
        if not candidates:
            raise RuntimeError("no deployed Pike has an unoccupied adjacent tile")
        pike_before, direction = candidates[0]
        commander_before = groups_before[0]["members"][0]

        # detect-command leaves the command menu open on group 0. Close it,
        # move the map cursor to the chosen Pike, then apply Move and Standby.
        recorder.send(["b"], delay=0.8)
        navigation = move_keys(
            (commander_before["x"], commander_before["y"]),
            (pike_before["x"], pike_before["y"]),
        )
        recorder.send(navigation, delay=0.18)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=0.8)
        recorder.send([direction], delay=0.6)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=1.4)
        acted_capture = recorder.capture("battle/pike_acted_gray.png")
        acted_gst = recorder.save_gst("states/pike_acted_gray.gst")
        pike_group_after = sherry_group(acted_gst)
        pike_after = pike_group_after["members"][pike_before["member_index"]]
        coordinate_changed = (
            pike_before["x"], pike_before["y"]
        ) != (pike_after["x"], pike_after["y"])
        gray_report = pike_gray_report(args.rom.read_bytes(), acted_gst)
        ordinary_gray_after = ordinary_gray_cache_report(
            args.rom.read_bytes(), acted_gst
        )
        passed = (
            pike_before["class_id"] == pike_after["class_id"] == PIKE_CLASS_ID
            and pike_before["acted_flag"] == 0
            and pike_after["acted_flag"] == 1
            and coordinate_changed
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
            "scenario": SCENARIO,
            "commander": "셰리",
            "hired_class": "파이크",
            "hired_count": HIRED_COUNT,
            "hired_gst": relative(hired_gst),
            "hired_gst_sha256": sha256(hired_gst),
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
            "pike_before": member_summary(pike_before),
            "pike_after": member_summary(pike_after),
            "coordinate_changed": coordinate_changed,
            "pike_gray_cache": gray_report,
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
    result = run_probe(args)
    print(
        f"{result['status']}: Scenario {SCENARIO} Sherry hired "
        f"{HIRED_COUNT} Pikes; acted-gray cache "
        f"{result['pike_gray_cache']['actual_sha256']}"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
