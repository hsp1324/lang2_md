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
DEFAULT_CLASS_ID = 0x74
ENEMY_SIDE_ID = 0x04
HIDDEN_COORDINATES = frozenset(((0x00, 0x00), (0xFF, 0xFF)))
CACHE_OWNERS = ("fixed", "dynamic", "fallback")
DYNAMIC_CACHE_TABLE = 0xA88E
DYNAMIC_CACHE_COUNT = 10
DYNAMIC_CACHE_ROW_BYTES = 4
FIXED_CACHE_TABLE = 0xA84E
FIXED_CACHE_COUNT = 16
FRAME_TILE_DELTA = 0x0100
TILE_BYTES = 32
CURSOR_X_ADDRESS = 0xA6DF
CURSOR_Y_ADDRESS = 0xA6E1


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def visible_coordinate(member: dict[str, object]) -> bool:
    """Reject both stock hidden encodings and partial sentinel positions."""
    coordinate = (int(member["x"]), int(member["y"]))
    return (
        coordinate not in HIDDEN_COORDINATES
        and all(value not in (0x00, 0xFF) for value in coordinate)
    )


def runtime_groups_with_sides(gst: Path) -> list[dict[str, object]]:
    ram = mercenary_probe.work_ram(gst)
    groups = []
    for group in mercenary_probe.runtime_groups(gst):
        group_index = int(group["group_index"])
        side_offset = (
            matrix.RUNTIME_GROUP_BASE
            + group_index * matrix.RUNTIME_GROUP_SIZE
            + matrix.RUNTIME_SIDE_OFFSET
        )
        groups.append({**group, "side_id": ram[side_offset]})
    return groups


def cursor_coordinate(gst: Path) -> tuple[int, int]:
    ram = mercenary_probe.work_ram(gst)
    return ram[CURSOR_X_ADDRESS], ram[CURSOR_Y_ADDRESS]


def runtime_target_by_key(
    groups: list[dict[str, object]],
    group_index: int,
    member_index: int,
) -> dict[str, object]:
    matches = [
        {
            **member,
            "group_index": int(group["group_index"]),
            "side_id": int(group["side_id"]),
            "role": "subordinate" if member_index > 0 else "commander",
        }
        for group in groups
        if int(group["group_index"]) == group_index
        for member in group["members"]
        if int(member["member_index"]) == member_index
    ]
    if len(matches) != 1:
        raise ValueError(
            "expected one runtime target "
            f"({group_index}, {member_index}), got {len(matches)}"
        )
    return matches[0]


def select_visible_enemy_subordinate(
    groups: list[dict[str, object]],
    class_id: int,
    cursor: tuple[int, int],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Select exactly one live hostile subordinate by a stable policy.

    A class may occur in several hostile groups (stock Scenario 13 has many
    Berserkers), so uniqueness means one explicit runtime group/member tuple,
    not an accidental dependency on iteration order.
    """
    candidates = []
    for group in groups:
        if int(group.get("side_id", -1)) != ENEMY_SIDE_ID:
            continue
        for member in group["members"][1:]:
            if (
                int(member["class_id"]) != class_id
                or int(member["hp"]) <= 0
                or not visible_coordinate(member)
            ):
                continue
            candidates.append(
                {
                    **member,
                    "group_index": int(group["group_index"]),
                    "side_id": int(group["side_id"]),
                    "role": "subordinate",
                }
            )
    if not candidates:
        raise RuntimeError(
            "no live visible side-0x04 subordinate "
            f"class 0x{class_id:02X}"
        )
    candidates.sort(
        key=lambda member: (
            abs(int(member["x"]) - cursor[0])
            + abs(int(member["y"]) - cursor[1]),
            int(member["group_index"]),
            int(member["member_index"]),
        )
    )
    selected = candidates[0]
    selected_key = (
        int(selected["group_index"]),
        int(selected["member_index"]),
    )
    if sum(
        (
            int(member["group_index"]),
            int(member["member_index"]),
        )
        == selected_key
        for member in candidates
    ) != 1:
        raise ValueError(f"ambiguous runtime target identity: {selected_key}")
    return selected, candidates


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
        references = [
            {
                "tile": f"0x{current:04X}",
                "hits": plane_tile_hits(state, current),
            }
            for current in range(tile, tile + 4)
        ]
        frames.append({
            "frame": frame,
            "rom_source_range": (
                f"0x{source:06X}.."
                f"0x{source + builder.MAP_SPRITE_BYTES - 1:06X}"
            ),
            "tile_range": f"0x{tile:04X}..0x{tile + 3:04X}",
            "vram_range": (
                f"0x{vram_start:04X}.."
                f"0x{vram_start + builder.MAP_SPRITE_BYTES - 1:04X}"
            ),
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "actual_sha256": hashlib.sha256(actual).hexdigest(),
            "matches_rom_source": actual == expected,
            "plane_references": references,
            "complete_plane_a_sprite_occurrences": (
                mercenary_probe.complete_plane_a_sprite_occurrences(
                    references
                )
            ),
        })
    return {
        "requested_class_id": f"0x{class_id:02X}",
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
        "one_animation_frame_referenced_by_plane_a": any(
            frame["complete_plane_a_sprite_occurrences"] > 0
            for frame in frames
        ),
    }


def expected_rendered_class_id(requested_class_id: int, owner: str) -> int:
    if owner != "fallback":
        return requested_class_id
    index = requested_class_id - builder.ENEMY_ADVANCED_MERCENARY_FIRST_CLASS
    if not 0 <= index < len(builder.ENEMY_ADVANCED_MERCENARY_FALLBACK_CLASSES):
        raise ValueError(
            "fallback cache owner is invalid for requested class "
            f"0x{requested_class_id:02X}"
        )
    return builder.ENEMY_ADVANCED_MERCENARY_FALLBACK_CLASSES[index]


def frame_contract(report: dict[str, object]) -> bool:
    frames = report.get("frames", [])
    return (
        len(frames) == 2
        and {int(frame["frame"]) for frame in frames} == {0, 1}
        and all(bool(frame["matches_rom_source"]) for frame in frames)
    )


def cache_contract_checks(
    before: dict[str, object],
    hover: dict[str, object],
    requested_class_id: int,
    *,
    target: dict[str, object],
    target_after_hover: dict[str, object],
    target_candidates: list[dict[str, object]],
    hover_cursor: tuple[int, int],
    rom_hash_before: str,
    rom_hash_after: str,
    seed_hash_before: str,
    seed_hash_after: str,
    expected_cache_owner: str,
    expected_group_index: int,
    expected_member_index: int,
    expected_rom_sha256: str,
    expected_seed_sha256: str,
) -> dict[str, bool]:
    requested = f"0x{requested_class_id:02X}"
    before_owner = str(before.get("cache_owner"))
    hover_owner = str(hover.get("cache_owner"))
    try:
        expected_rendered = expected_rendered_class_id(
            requested_class_id,
            expected_cache_owner,
        )
    except ValueError:
        expected_rendered = -1
    rendered_expected = f"0x{expected_rendered:02X}"
    selected_key = (
        int(target.get("group_index", -1)),
        int(target.get("member_index", -1)),
    )
    selected_key_count = sum(
        (
            int(member.get("group_index", -2)),
            int(member.get("member_index", -2)),
        )
        == selected_key
        for member in target_candidates
    )
    return {
        "target_is_one_exact_runtime_member": selected_key_count == 1,
        "target_runtime_key_matches_source_lock": selected_key
        == (expected_group_index, expected_member_index),
        "target_is_enemy_side_0x04": int(target.get("side_id", -1)) == ENEMY_SIDE_ID,
        "target_is_subordinate": (
            target.get("role") == "subordinate"
            and int(target.get("member_index", 0)) > 0
        ),
        "target_requested_class_matches": int(target.get("class_id", -1))
        == requested_class_id,
        "target_is_alive_and_visible": (
            int(target.get("hp", 0)) > 0 and visible_coordinate(target)
        ),
        "hover_cursor_matches_exact_target": hover_cursor
        == (int(target.get("x", -1)), int(target.get("y", -1))),
        "target_runtime_record_unchanged_by_hover": (
            target_after_hover.get("group_index") == target.get("group_index")
            and target_after_hover.get("member_index")
            == target.get("member_index")
            and target_after_hover.get("side_id") == target.get("side_id")
            and target_after_hover.get("record") == target.get("record")
        ),
        "cache_owner_unchanged": before_owner == hover_owner,
        "before_cache_owner_matches_source_lock": before_owner
        == expected_cache_owner,
        "hover_cache_owner_matches_source_lock": hover_owner
        == expected_cache_owner,
        "cache_index_unchanged": before.get("cache_index")
        == hover.get("cache_index"),
        "cache_base_tile_unchanged": before.get("base_tile")
        == hover.get("base_tile"),
        "requested_class_preserved": (
            before.get("requested_class_id")
            == hover.get("requested_class_id")
            == requested
        ),
        "before_rendered_class_contract": before.get("rendered_class_id")
        == rendered_expected,
        "hover_rendered_class_contract": hover.get("rendered_class_id")
        == rendered_expected,
        "before_frame0_frame1_match_rom_exact": frame_contract(before),
        "hover_frame0_frame1_match_rom_exact": frame_contract(hover),
        # The selected unit may be outside the initial camera viewport, so a
        # Plane A reference is not required before navigation.  Hover is the
        # linkage proof: after the camera reaches the target, one complete
        # four-tile animation frame must point at the verified cache payload.
        "hover_has_required_plane_a_reference": bool(
            hover.get("one_animation_frame_referenced_by_plane_a")
        ),
        "rom_input_unchanged": rom_hash_before == rom_hash_after,
        "seed_gst_input_unchanged": seed_hash_before == seed_hash_after,
        "rom_matches_source_locked_sha256": rom_hash_before
        == expected_rom_sha256,
        "seed_gst_matches_source_locked_sha256": seed_hash_before
        == expected_seed_sha256,
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
    rom_hash_before = sha256(args.rom)
    seed_hash_before = sha256(args.seed_gst)
    rom_data = args.rom.read_bytes()
    try:
        launch_to_battle(recorder, args, output, runtime_name)
        command_capture = recorder.capture("battle/command_open.png")
        command_gst = recorder.save_gst("states/command_open.gst")
        recorder.send(["b"], delay=0.8)
        before_capture = recorder.capture("battle/before_hover.png")
        before_gst = recorder.save_gst("states/before_hover.gst")
        groups = runtime_groups_with_sides(before_gst)
        cursor_before = cursor_coordinate(before_gst)
        target, target_candidates = select_visible_enemy_subordinate(
            groups,
            args.class_id,
            cursor_before,
        )
        navigation = mercenary_probe.move_keys(
            cursor_before,
            (int(target["x"]), int(target["y"])),
        )
        before_cache = cache_report(rom_data, before_gst, args.class_id)
        recorder.send(navigation, delay=0.18)
        time.sleep(0.8)
        hover_capture = recorder.capture("battle/target_hover.png")
        hover_gst = recorder.save_gst("states/target_hover.gst")
        cursor_after = cursor_coordinate(hover_gst)
        target_after_hover = runtime_target_by_key(
            runtime_groups_with_sides(hover_gst),
            int(target["group_index"]),
            int(target["member_index"]),
        )
        hover_cache = cache_report(rom_data, hover_gst, args.class_id)
        rom_hash_after = sha256(args.rom)
        seed_hash_after = sha256(args.seed_gst)
        checks = cache_contract_checks(
            before_cache,
            hover_cache,
            args.class_id,
            target=target,
            target_after_hover=target_after_hover,
            target_candidates=target_candidates,
            hover_cursor=cursor_after,
            rom_hash_before=rom_hash_before,
            rom_hash_after=rom_hash_after,
            seed_hash_before=seed_hash_before,
            seed_hash_after=seed_hash_after,
            expected_cache_owner=args.expected_cache_owner,
            expected_group_index=args.expected_group_index,
            expected_member_index=args.expected_member_index,
            expected_rom_sha256=args.expected_rom_sha256,
            expected_seed_sha256=args.expected_seed_sha256,
        )
        passed = all(checks.values())
        result = {
            "schema_version": 2,
            "status": "pass" if passed else "fail",
            "rom": {
                "path": relative(args.rom),
                "sha256": rom_hash_before,
                "sha256_before": rom_hash_before,
                "sha256_after": rom_hash_after,
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "seed_gst": {
                "path": relative(args.seed_gst),
                "sha256": seed_hash_before,
                "sha256_before": seed_hash_before,
                "sha256_after": seed_hash_after,
            },
            "scenario": args.scenario,
            "acceptance_contract": {
                "cache_owner": args.expected_cache_owner,
                "runtime_key": {
                    "group_index": args.expected_group_index,
                    "member_index": args.expected_member_index,
                },
                "rom_sha256": args.expected_rom_sha256,
                "seed_gst_sha256": args.expected_seed_sha256,
                "expected_rendered_class_id": (
                    f"0x{expected_rendered_class_id(args.class_id, args.expected_cache_owner):02X}"
                ),
            },
            "target": member_summary(target),
            "target_after_hover": member_summary(target_after_hover),
            "target_selection": {
                "policy": (
                    "nearest live visible side-0x04 subordinate, then "
                    "runtime group/member index"
                ),
                "candidate_count": len(target_candidates),
                "candidate_runtime_keys": [
                    {
                        "group_index": int(member["group_index"]),
                        "member_index": int(member["member_index"]),
                        "x": int(member["x"]),
                        "y": int(member["y"]),
                    }
                    for member in target_candidates
                ],
            },
            "cursor": {
                "before_navigation": list(cursor_before),
                "after_navigation": list(cursor_after),
                "target": [int(target["x"]), int(target["y"])],
            },
            "plane_reference_contract": {
                "before": (
                    "observed but optional because the selected target may "
                    "start outside the camera viewport"
                ),
                "hover": (
                    "required: one complete four-tile animation frame must "
                    "be referenced by Plane A after navigation"
                ),
            },
            "navigation": navigation,
            "command_capture": relative(command_capture),
            "command_gst": relative(command_gst),
            "before_capture": relative(before_capture),
            "before_gst": relative(before_gst),
            "hover_capture": relative(hover_capture),
            "hover_gst": relative(hover_gst),
            "before_cache": before_cache,
            "hover_cache": hover_cache,
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
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--scenario", type=int, default=13)
    parser.add_argument(
        "--class-id",
        type=lambda value: int(value, 0),
        default=DEFAULT_CLASS_ID,
    )
    parser.add_argument(
        "--expected-cache-owner",
        choices=CACHE_OWNERS,
        required=True,
        help="source-locked cache owner required for fail-closed acceptance",
    )
    parser.add_argument("--expected-group-index", type=int, required=True)
    parser.add_argument("--expected-member-index", type=int, required=True)
    parser.add_argument("--expected-rom-sha256", required=True)
    parser.add_argument("--expected-seed-sha256", required=True)
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
    if not 0 <= args.expected_group_index < 20:
        parser.error("--expected-group-index must be 0..19")
    if not 1 <= args.expected_member_index <= 7:
        parser.error("--expected-member-index must be 1..7")
    for label, value in (
        ("--expected-rom-sha256", args.expected_rom_sha256),
        ("--expected-seed-sha256", args.expected_seed_sha256),
    ):
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            parser.error(f"{label} must be a lowercase SHA-256")
    result = run_probe(args)
    print(
        f"{result['status']}: Scenario {args.scenario} "
        f"{builder.KOREAN_CLASS_LABELS[args.class_id]} status hover"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
