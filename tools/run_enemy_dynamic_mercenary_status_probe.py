#!/usr/bin/env python3
"""Verify an enemy dynamic-cache mercenary before and after status hover."""

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
from tools import run_pike_acted_surface_probe as mercenary_probe
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools.verify_preparation_surface_evidence import load_gst, plane_tile_hits


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/enemy_dynamic_mercenary_status_probe"
DEFAULT_DISPLAY = ":530"
DYNAMIC_CACHE_TABLE = 0xA88E
DYNAMIC_CACHE_COUNT = 10
DYNAMIC_CACHE_ROW_BYTES = 4
FIXED_CACHE_TABLE = 0xA84E
FIXED_CACHE_COUNT = 16
FRAME_TILE_DELTA = 0x0100
TILE_BYTES = 32


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def cache_row(gst: Path, class_id: int) -> dict[str, object]:
    ram = mercenary_probe.work_ram(gst)
    matches = []
    for owner, table, count in (
        ("fixed", FIXED_CACHE_TABLE, FIXED_CACHE_COUNT),
        ("dynamic", DYNAMIC_CACHE_TABLE, DYNAMIC_CACHE_COUNT),
    ):
        for index in range(count):
            offset = table + index * DYNAMIC_CACHE_ROW_BYTES
            cached_class = int.from_bytes(ram[offset:offset + 2], "big")
            tile = int.from_bytes(ram[offset + 2:offset + 4], "big")
            if cached_class == class_id:
                matches.append({
                    "owner": owner,
                    "index": index,
                    "class_id": cached_class,
                    "tile": tile,
                })
    if not matches:
        fallback_index = class_id - builder.ENEMY_ADVANCED_MERCENARY_FIRST_CLASS
        if 0 <= fallback_index < len(
            builder.ENEMY_ADVANCED_MERCENARY_FALLBACK_CLASSES
        ):
            fallback_class = builder.ENEMY_ADVANCED_MERCENARY_FALLBACK_CLASSES[
                fallback_index
            ]
            for index in range(FIXED_CACHE_COUNT):
                offset = FIXED_CACHE_TABLE + index * DYNAMIC_CACHE_ROW_BYTES
                cached_class = int.from_bytes(ram[offset:offset + 2], "big")
                if cached_class == fallback_class:
                    matches.append({
                        "owner": "fallback",
                        "index": index,
                        "class_id": class_id,
                        "source_class_id": fallback_class,
                        "tile": int.from_bytes(
                            ram[offset + 2:offset + 4], "big"
                        ),
                    })
                    break
    if len(matches) != 1:
        raise ValueError(
            f"expected one cache row for class 0x{class_id:02X}, "
            f"got {matches}"
        )
    return matches[0]


def cache_report(rom: bytes, gst: Path, class_id: int) -> dict[str, object]:
    state = load_gst(gst)
    row = cache_row(gst, class_id)
    source_class_id = int(row.get("source_class_id", class_id))
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + source_class_id * 2,
    )
    frames = []
    for frame, tile in ((0, row["tile"]), (1, row["tile"] + FRAME_TILE_DELTA)):
        source = (
            builder.MAP_SPRITE_FRAME_BASES[frame]
            + sprite_id * builder.MAP_SPRITE_BYTES
        )
        expected = rom[source:source + builder.MAP_SPRITE_BYTES]
        vram_start = tile * TILE_BYTES
        actual = state.vram[vram_start:vram_start + builder.MAP_SPRITE_BYTES]
        frames.append({
            "frame": frame,
            "tile_range": f"0x{tile:04X}..0x{tile + 3:04X}",
            "vram_range": (
                f"0x{vram_start:04X}.."
                f"0x{vram_start + builder.MAP_SPRITE_BYTES - 1:04X}"
            ),
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "actual_sha256": hashlib.sha256(actual).hexdigest(),
            "matches_rom_source": actual == expected,
            "plane_references": [
                {
                    "tile": f"0x{current:04X}",
                    "hits": plane_tile_hits(state, current),
                }
                for current in range(tile, tile + 4)
            ],
        })
    return {
        "class_id": f"0x{class_id:02X}",
        "class_korean": builder.KOREAN_CLASS_LABELS[class_id],
        "rendered_class_id": f"0x{source_class_id:02X}",
        "rendered_class_korean": builder.KOREAN_CLASS_LABELS[source_class_id],
        "sprite_id": f"0x{sprite_id:04X}",
        "cache_owner": row["owner"],
        "cache_index": row["index"],
        "base_tile": f"0x{row['tile']:04X}",
        "frames": frames,
        "both_frames_match_rom_source": all(
            frame["matches_rom_source"] for frame in frames
        ),
    }


def member_summary(member: dict[str, object]) -> dict[str, object]:
    return {
        **member,
        "class_id": f"0x{int(member['class_id']):02X}",
    }


def launch_to_battle(
    recorder: matrix.RuntimeRecorder,
    args: argparse.Namespace,
    output: Path,
    runtime_name: str,
) -> None:
    recorder.run_command([
        sys.executable,
        str(RUN_SEQUENCE),
        "scenario-select",
        "--rom", str(args.rom),
        "--scenario-number", str(args.scenario),
        "--runtime-name", runtime_name,
        "--manual-slot-gst", str(args.seed_gst),
        "--initial-delay", "12.0",
        "--virtual-display", args.display,
        "--replace-existing",
        "--send-event",
    ])
    recorder.run_command([
        sys.executable,
        str(RUN_SEQUENCE),
        "detect-prep",
        "--rom", str(args.rom),
        "--no-launch",
        "--confirmation-delay", "0.8",
        "--max-confirmations", "100",
        "--capture-prefix", str(output / "briefing/detect.png"),
        "--virtual-display", args.display,
        "--send-event",
    ])
    mercenary_probe.enter_battle_command(recorder, args.rom, output)


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"enemy-dynamic-status-{args.run_id}"
    runtime_home = ROOT / "captures/runtime" / runtime_name
    recorder = matrix.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        launch_to_battle(recorder, args, output, runtime_name)
        command_capture = recorder.capture("battle/command_open.png")
        command_gst = recorder.save_gst("states/command_open.gst")
        recorder.send(["b"], delay=0.8)
        before_capture = recorder.capture("battle/before_hover.png")
        before_gst = recorder.save_gst("states/before_hover.gst")
        groups = mercenary_probe.runtime_groups(before_gst)
        target_matches = [
            member
            for group in groups
            for member in group["members"][1:]
            if member["class_id"] == args.class_id
            and member["hp"] > 0
            and (member["x"], member["y"]) != (0, 0)
        ]
        if not target_matches:
            raise RuntimeError(
                f"Scenario {args.scenario} has no visible enemy subordinate "
                f"class 0x{args.class_id:02X}"
            )
        target = target_matches[0]
        cursor = groups[0]["members"][0]
        navigation = mercenary_probe.move_keys(
            (int(cursor["x"]), int(cursor["y"])),
            (int(target["x"]), int(target["y"])),
        )
        before_cache = cache_report(args.rom.read_bytes(), before_gst, args.class_id)
        recorder.send(navigation, delay=0.18)
        time.sleep(0.8)
        hover_capture = recorder.capture("battle/target_hover.png")
        hover_gst = recorder.save_gst("states/target_hover.gst")
        hover_cache = cache_report(args.rom.read_bytes(), hover_gst, args.class_id)
        passed = (
            before_cache["both_frames_match_rom_source"]
            and hover_cache["both_frames_match_rom_source"]
            and before_cache["base_tile"] == hover_cache["base_tile"]
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
            "target": member_summary(target),
            "navigation": navigation,
            "command_capture": relative(command_capture),
            "command_gst": relative(command_gst),
            "before_capture": relative(before_capture),
            "before_gst": relative(before_gst),
            "hover_capture": relative(hover_capture),
            "hover_gst": relative(hover_gst),
            "before_cache": before_cache,
            "hover_cache": hover_cache,
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
    parser.add_argument("--scenario", type=int, default=13)
    parser.add_argument("--class-id", type=lambda value: int(value, 0), default=0x73)
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
    for name in ("rom", "seed_gst", "xvfb", "xvfb_library_path", "output_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if not 1 <= args.scenario <= 27:
        parser.error("--scenario must be 1..27")
    if not 0 <= args.class_id < len(builder.KOREAN_CLASS_LABELS):
        parser.error("--class-id is outside the class table")
    result = run_probe(args)
    print(
        f"{result['status']}: Scenario {args.scenario} "
        f"{builder.KOREAN_CLASS_LABELS[args.class_id]} status hover"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
