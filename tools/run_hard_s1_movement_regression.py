#!/usr/bin/env python3
# ruff: noqa: E402
"""Exercise the reported Hard Scenario 1 movement regression in BlastEm.

The release ROM is never patched.  The probe enters Scenario 1 from a fresh
save, hires and deploys six Soldiers, opens Bald's real Move range through the
stock all-factions command, advances ordinary turns until the AI damages one
exact surviving Soldier in captured side-view combat, and repeatedly reopens
that Soldier's Move range after combat and on the following turn. GST work RAM
and VDP name tables are retained for every assertion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Iterable

from PIL import Image
from Xlib import X
from Xlib.display import Display
from Xlib.ext import xtest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import send_blastem_keys as key_sender
from tools import run_mounted_lord_combat_regression as mounted
from tools import run_pike_acted_surface_probe as mercenary
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools import verify_hard_mode_first_turn as first_turn
from tools.class_hire_data import CLASS_RECORD_SIZE, CLASS_RECORD_TABLE
from tools.verify_preparation_surface_evidence import load_gst
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


DEFAULT_ROM = RELEASE_ROM_PATHS["hard"]
DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_SEED_GST = (
    ROOT
    / "tmp/v137-final/fresh-s1/hard/v137-final01/"
    "fresh_s1_preparation.gst"
)
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/v137-final/hard-s1-movement"
DEFAULT_DISPLAY = ":880"
EXPECTED_ROM_SHA256 = RELEASE_ROM_SHA256["hard"]
EXPECTED_SOURCE_SHA256 = (
    "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"
)
EXPECTED_SEED_SHA256 = (
    "2cf2fa24b2e6b9bf73d3e5d1b1238f074a8e4c3192e9f096bc1141c83a4b10aa"
)

SCENARIO = 1
ELWIN_COMMANDER_ID = 1
ELWIN_CLASS_ID = 0x01
SOLDIER_CLASS_ID = 0x64
HIRED_COUNT = 6
BALD_GROUP_INDEX = 10
BALD_NAME_ID = 0x12
BALD_CLASS_ID = 0x2E
BALD_COORDINATE = (4, 7)
SELECTED_SOLDIER_MEMBER_INDEX = 6
SELECTED_SOLDIER_COORDINATE = (12, 16)
CLASS_MOVEMENT_OFFSET = 0x0D
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_GROUP_MOVEMENT_OFFSET = 0x44
TURN_COUNTER_OFFSET = 0xA5F1
ALL_FACTIONS_INPUT = (
    "up", "left", "up", "right", "a", "left", "down", "b",
    "down", "right", "a", "b", "down", "right", "a",
)
ALL_FACTIONS_HOLD_SECONDS = 0.12
ALL_FACTIONS_GAP_SECONDS = 0.05
ALL_FACTIONS_RETRY_GAPS = (0.05, 0.08, 0.10, 0.12, 0.16, 0.20, 0.25)
ALL_FACTIONS_TABLE_OFFSET = 0x00D7B6
ALL_FACTIONS_HISTORY_ADDRESS = 0x8188
ALL_FACTIONS_HISTORY_BYTES = 0x20
ALL_FACTIONS_CURRENT_INPUT_ADDRESS = 0x8179
ALL_FACTIONS_ACTIVE_FLAG_ADDRESS = 0xA6C7
SELECTED_GROUP_INDEX_ADDRESS = 0xA624
SELECTED_MEMBER_INDEX_ADDRESS = 0xA625
SELECTED_GROUP_POINTER_ADDRESS = 0xA628
SELECTED_MEMBER_POINTER_ADDRESS = 0xA62C
RUNTIME_GROUP_ABSOLUTE_BASE = 0x00FF0000 + RUNTIME_GROUP_BASE
ALL_FACTIONS_EXPECTED_HISTORY = bytes.fromhex(
    "01 00 04 00 01 00 08 00 40 00 04 00 02 00 10 00 "
    "02 00 08 00 40 00 10 00 02 00 08 00 40"
)
GST_VSRAM_OFFSET = 0x192
VDP_TILE_PIXELS = 8
BATTLE_CELL_TILES = 3
BATTLE_CELL_PIXELS = VDP_TILE_PIXELS * BATTLE_CELL_TILES


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def file_model(path: Path) -> dict[str, object]:
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def require_sha256(path: Path, expected: str, label: str) -> None:
    actual = sha256_path(path)
    if actual != expected:
        raise ValueError(
            f"{label} SHA-256 changed: expected {expected}, got {actual}"
        )


def validate_sha256(value: str) -> str:
    """Return one normalized SHA-256 digest or reject ambiguous input."""
    normalized = value.lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise argparse.ArgumentTypeError(
            "expected exactly 64 hexadecimal SHA-256 characters"
        )
    return normalized


def require_isolated_display(display: str) -> None:
    """Fail closed before any emulator launch on a physical/unknown display."""
    match = re.fullmatch(r":(\d+)(?:\.\d+)?", display)
    if match is None or int(match.group(1)) < 100:
        raise ValueError(
            "Hard S1 runtime is restricted to an explicit high-numbered "
            f"isolated Xvfb display (for example {DEFAULT_DISPLAY}); got "
            f"{display!r}"
        )


def runtime_group(gst: Path, group_index: int) -> dict[str, object]:
    if not 0 <= group_index < mercenary.GROUP_COUNT:
        raise ValueError(f"runtime group index is outside 0..39: {group_index}")
    ram = mercenary.work_ram(gst)
    start = RUNTIME_GROUP_BASE + group_index * RUNTIME_GROUP_SIZE
    record = ram[start:start + RUNTIME_GROUP_SIZE]
    if len(record) != RUNTIME_GROUP_SIZE:
        raise ValueError(f"GST has a truncated runtime group {group_index}")
    members = []
    for member_index in range(8):
        member_start = member_index * RUNTIME_MEMBER_SIZE
        member = record[member_start:member_start + RUNTIME_MEMBER_SIZE]
        members.append({
            "member_index": member_index,
            "class_id": member[0],
            "name_id": member[1],
            "acted_flag": member[2],
            "hp": member[3],
            "x": member[6],
            "y": member[7],
            "record": member.hex(),
        })
    return {
        "group_index": group_index,
        "side_id": record[0x20],
        "movement_plus_0x44": record[RUNTIME_GROUP_MOVEMENT_OFFSET],
        "record_sha256": sha256_bytes(record),
        "record": record.hex(),
        "members": members,
    }


def public_member(member: dict[str, object]) -> dict[str, object]:
    return {
        **member,
        "class_id": f"0x{int(member['class_id']):02X}",
        "name_id": f"0x{int(member['name_id']):02X}",
    }


def public_group(group: dict[str, object]) -> dict[str, object]:
    return {
        **group,
        "members": [public_member(row) for row in group["members"]],
    }


def occupied_runtime_coordinates(gst: Path) -> set[tuple[int, int]]:
    occupied = set()
    for group_index in range(mercenary.GROUP_COUNT):
        group = runtime_group(gst, group_index)
        for row in group["members"]:
            coordinate = (int(row["x"]), int(row["y"]))
            if (
                row["class_id"] != 0xFF
                and row["hp"] > 0
                and coordinate != (0, 0)
            ):
                occupied.add(coordinate)
    return occupied


def hostile_runtime_coordinates(gst: Path) -> set[tuple[int, int]]:
    """Return live side-4 coordinates from Scenario 1's runtime groups."""
    hostile = set()
    for group_index in range(mercenary.GROUP_COUNT):
        group = runtime_group(gst, group_index)
        if group["side_id"] != 4:
            continue
        for row in group["members"]:
            coordinate = (int(row["x"]), int(row["y"]))
            if (
                row["class_id"] != 0xFF
                and row["hp"] > 0
                and all(0 <= value < 64 for value in coordinate)
            ):
                hostile.add(coordinate)
    return hostile


def runtime_occupants(
    gst: Path,
    coordinate: tuple[int, int],
) -> list[dict[str, object]]:
    """Return every live runtime unit occupying one exact world cell."""
    occupants = []
    for group_index in range(mercenary.GROUP_COUNT):
        group = runtime_group(gst, group_index)
        for row in group["members"]:
            if (
                row["class_id"] != 0xFF
                and row["hp"] > 0
                and (int(row["x"]), int(row["y"])) == coordinate
            ):
                occupants.append({
                    "group_index": group_index,
                    **public_member(row),
                })
    return occupants


def reachable_empty_destinations(
    reach_report: dict[str, object],
    origin: tuple[int, int],
    occupied: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return overlay cells worth probing for a stock-valid Move cursor."""
    candidates = {
        (int(x), int(y))
        for x, y in reach_report["coordinates"]
        if (int(x), int(y)) != origin
        and (int(x), int(y)) not in occupied
    }
    # Scenario 1's northern roof cells can be overlay-tinted yet reject a
    # stop with the stock red-X cursor. Prefer the unobstructed southern floor,
    # then let the live orange-cursor detector decide rather than assuming.
    return sorted(
        candidates,
        key=lambda coordinate: (
            coordinate[1] < origin[1],
            abs(coordinate[0] - origin[0])
            + abs(coordinate[1] - origin[1]),
            -coordinate[1],
            coordinate[0],
        ),
    )


def member(group: dict[str, object], member_index: int) -> dict[str, object]:
    return group["members"][member_index]


def turn_counter(gst: Path) -> int:
    return mercenary.work_ram(gst)[TURN_COUNTER_OFFSET]


def selected_runtime_pointer_report(
    gst: Path,
    *,
    expected_group_index: int,
    expected_member_index: int,
) -> dict[str, object]:
    """Require the stock command UI to target one exact runtime record."""
    ram = mercenary.work_ram(gst)
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
        + expected_group_index * RUNTIME_GROUP_SIZE
    )
    expected_member_pointer = (
        expected_group_pointer
        + expected_member_index * RUNTIME_MEMBER_SIZE
    )
    matches = (
        group_index == expected_group_index
        and member_index == expected_member_index
        and group_pointer == expected_group_pointer
        and member_pointer == expected_member_pointer
    )
    report = {
        "gst": file_model(gst),
        "group_index": group_index,
        "member_index": member_index,
        "group_pointer": f"0x{group_pointer:08X}",
        "member_pointer": f"0x{member_pointer:08X}",
        "expected_group_index": expected_group_index,
        "expected_member_index": expected_member_index,
        "expected_group_pointer": f"0x{expected_group_pointer:08X}",
        "expected_member_pointer": f"0x{expected_member_pointer:08X}",
        "matches_exact_runtime_record": matches,
    }
    if not matches:
        raise RuntimeError(
            "stock command UI selected the wrong runtime record: "
            + json.dumps(report, ensure_ascii=False)
        )
    return report


def all_factions_static_report(rom: bytes) -> dict[str, object]:
    length = int.from_bytes(
        rom[ALL_FACTIONS_TABLE_OFFSET:ALL_FACTIONS_TABLE_OFFSET + 2], "big"
    )
    history = rom[
        ALL_FACTIONS_TABLE_OFFSET + 2:
        ALL_FACTIONS_TABLE_OFFSET + 2 + length
    ]
    held_mask = rom[ALL_FACTIONS_TABLE_OFFSET + 2 + length]
    return {
        "matcher_call": "0x00D788 -> 0x008A20",
        "table_offset": f"0x{ALL_FACTIONS_TABLE_OFFSET:06X}",
        "history_length": length,
        "history": history.hex(),
        "expected_history": ALL_FACTIONS_EXPECTED_HISTORY.hex(),
        "history_matches_documented_sequence": (
            history == ALL_FACTIONS_EXPECTED_HISTORY
        ),
        "required_current_held_mask": f"0x{held_mask:02X}",
        "toggle_instruction": "eori.b #1,$FFFFA6C7",
        "active_flag_work_ram": f"0x{ALL_FACTIONS_ACTIVE_FLAG_ADDRESS:04X}",
    }


def all_factions_runtime_report(gst: Path) -> dict[str, object]:
    ram = mercenary.work_ram(gst)
    history = ram[
        ALL_FACTIONS_HISTORY_ADDRESS:
        ALL_FACTIONS_HISTORY_ADDRESS + ALL_FACTIONS_HISTORY_BYTES
    ]
    expected = ALL_FACTIONS_EXPECTED_HISTORY
    return {
        "gst": file_model(gst),
        "active_flag": ram[ALL_FACTIONS_ACTIVE_FLAG_ADDRESS],
        "current_input": f"0x{ram[ALL_FACTIONS_CURRENT_INPUT_ADDRESS]:02X}",
        "history_32_bytes": history.hex(),
        "expected_history_29_bytes": expected.hex(),
        # The game keeps a 32-byte rolling buffer while the documented
        # matcher consumes 29 bytes.  Depending on the input edge sampled
        # immediately after the toggle, the exact sequence can begin a few
        # bytes before the retained suffix, so require a contiguous match.
        "history_contains_expected": expected in history,
        "expected_history_offset": history.find(expected),
    }


def class_record(rom: bytes, class_id: int) -> bytes:
    start = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
    record = rom[start:start + CLASS_RECORD_SIZE]
    if len(record) != CLASS_RECORD_SIZE:
        raise ValueError(f"ROM has a truncated class 0x{class_id:02X}")
    return record


def static_movement_report(
    source_rom: Path,
    hard_rom: Path,
) -> dict[str, object]:
    source = source_rom.read_bytes()
    hard = hard_rom.read_bytes()
    rows = []
    for label, class_id in (
        ("Bald", BALD_CLASS_ID),
        ("Soldier", SOLDIER_CLASS_ID),
    ):
        source_record = class_record(source, class_id)
        hard_record = class_record(hard, class_id)
        rows.append({
            "label": label,
            "class_id": f"0x{class_id:02X}",
            "record_offset": (
                f"0x{CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE:06X}"
            ),
            "movement_byte_offset": (
                f"0x{CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE + CLASS_MOVEMENT_OFFSET:06X}"
            ),
            "source_record_sha256": sha256_bytes(source_record),
            "hard_record_sha256": sha256_bytes(hard_record),
            "records_byte_identical": source_record == hard_record,
            "source_movement": source_record[CLASS_MOVEMENT_OFFSET],
            "hard_movement": hard_record[CLASS_MOVEMENT_OFFSET],
        })
    return {
        "source_rom": file_model(source_rom),
        "hard_rom": file_model(hard_rom),
        "runtime_loader_movement_destination": "runtime group +0x44",
        "classes": rows,
        "all_records_byte_identical": all(
            row["records_byte_identical"] for row in rows
        ),
        "all_expected_movement_five": all(
            row["source_movement"] == row["hard_movement"] == 5
            for row in rows
        ),
    }


def plane_words(gst: Path, plane: str) -> tuple[int, int, list[int]]:
    state = load_gst(gst)
    base = state.plane_bases[plane]
    words = [
        int.from_bytes(state.vram[offset:offset + 2], "big")
        for offset in range(
            base,
            base + state.plane_width * state.plane_height * 2,
            2,
        )
    ]
    return state.plane_width, state.plane_height, words


def plane_table_report(gst: Path) -> dict[str, object]:
    state = load_gst(gst)
    planes = {}
    combined = bytearray()
    for plane in ("plane_a", "plane_b"):
        base = state.plane_bases[plane]
        size = state.plane_width * state.plane_height * 2
        payload = state.vram[base:base + size]
        combined.extend(payload)
        planes[plane] = {
            "base": f"0x{base:04X}",
            "sha256": sha256_bytes(payload),
            "bytes": size,
        }
    return {
        "width_8px_cells": state.plane_width,
        "height_8px_cells": state.plane_height,
        "combined_plane_a_b_sha256": sha256_bytes(bytes(combined)),
        "planes": planes,
    }


def plane_delta(before_gst: Path, overlay_gst: Path) -> dict[str, object]:
    rows = {}
    combined_changes = []
    for plane in ("plane_a", "plane_b"):
        width, height, before = plane_words(before_gst, plane)
        overlay_width, overlay_height, after = plane_words(overlay_gst, plane)
        if (width, height) != (overlay_width, overlay_height):
            raise ValueError("VDP plane dimensions changed while Move was open")
        changes = []
        for index, (old, new) in enumerate(zip(before, after)):
            if old == new:
                continue
            x = index % width
            y = index // width
            changes.append({
                "x_8px": x,
                "y_8px": y,
                "before": f"0x{old:04X}",
                "after": f"0x{new:04X}",
                "tile_unchanged": (old & 0x07FF) == (new & 0x07FF),
                "palette_before": (old >> 13) & 0x03,
                "palette_after": (new >> 13) & 0x03,
            })
        row = {
            "changed_8px_cell_count": len(changes),
            "changed_8px_cells": changes,
            "changed_name_table_tile_coordinates": [
                [int(change["x_8px"]), int(change["y_8px"])]
                for change in changes
            ],
            "all_changes_keep_tile_index": all(
                change["tile_unchanged"] for change in changes
            ),
        }
        rows[plane] = row
        combined_changes.extend((plane, change) for change in changes)
    return {
        "baseline_gst": file_model(before_gst),
        "overlay_gst": file_model(overlay_gst),
        "planes": rows,
        "changed_cell_count": len(combined_changes),
    }


def unwrap_axis(values: Iterable[int], modulus: int) -> dict[int, int]:
    """Unwrap a compact circular tile span across the name-table boundary."""
    unique = sorted(set(int(value) for value in values))
    if not unique:
        raise ValueError("cannot unwrap an empty tile axis")
    gaps = []
    for index, value in enumerate(unique):
        following = unique[(index + 1) % len(unique)]
        distance = (following - value) % modulus
        gaps.append((distance, index))
    largest = max(distance for distance, _ in gaps)
    cut_indices = [index for distance, index in gaps if distance == largest]
    if len(cut_indices) != 1 and len(unique) != modulus:
        raise ValueError(f"ambiguous circular tile span: {unique}")
    start = unique[(cut_indices[0] + 1) % len(unique)]
    return {
        value: value if value >= start else value + modulus
        for value in unique
    }


def movement_palette_blocks(
    delta: dict[str, object],
) -> dict[str, object]:
    """Group Plane-B palette changes into Langrisser's 3x3-tile cells."""
    plane = delta["planes"]["plane_b"]
    changes = plane["changed_8px_cells"]
    if not changes or not plane["all_changes_keep_tile_index"]:
        raise ValueError("Move overlay did not make palette-only Plane-B changes")
    points = {
        (int(change["x_8px"]), int(change["y_8px"]))
        for change in changes
    }
    width = 64
    height = 32
    unwrapped_x = unwrap_axis((x for x, _ in points), width)
    unwrapped_y = unwrap_axis((y for _, y in points), height)
    unwrapped = {
        (unwrapped_x[x], unwrapped_y[y]) for x, y in points
    }
    tilings = []
    for phase_x in range(BATTLE_CELL_TILES):
        for phase_y in range(BATTLE_CELL_TILES):
            groups: dict[tuple[int, int], set[tuple[int, int]]] = {}
            for x, y in unwrapped:
                block_x = (x - phase_x) // BATTLE_CELL_TILES
                block_y = (y - phase_y) // BATTLE_CELL_TILES
                groups.setdefault((block_x, block_y), set()).add((x, y))
            valid = True
            starts = []
            for block_x, block_y in groups:
                start_x = phase_x + block_x * BATTLE_CELL_TILES
                start_y = phase_y + block_y * BATTLE_CELL_TILES
                expected = {
                    (start_x + dx, start_y + dy)
                    for dx in range(BATTLE_CELL_TILES)
                    for dy in range(BATTLE_CELL_TILES)
                }
                if groups[(block_x, block_y)] != expected:
                    valid = False
                    break
                starts.append((start_x % width, start_y % height))
            if valid:
                tilings.append({
                    "phase": [phase_x, phase_y],
                    "raw_block_starts": sorted(starts),
                })
    if len(tilings) != 1:
        raise ValueError(
            "Plane-B palette tiles do not have one exact 3x3 battle-cell "
            f"tiling: {tilings}"
        )
    tiling = tilings[0]
    return {
        **tiling,
        "changed_name_table_tile_count": len(points),
        "battle_cell_tile_dimensions": [3, 3],
        "battle_cell_pixel_dimensions": [24, 24],
        "battle_cell_count": len(tiling["raw_block_starts"]),
    }


def selection_frame_cell_top_left(path: Path) -> tuple[int, int]:
    """Locate the unique stock 28px Move cursor and return its 24px cell."""
    frame = Image.open(path).convert("RGB")
    pixels = list(frame.get_flattened_data())

    def orange(x: int, y: int) -> bool:
        red, green, blue = pixels[y * frame.width + x]
        return (
            red > 180 and 40 < green < 210 and blue < 80
            and red > green * 1.15
        )

    candidates = []
    for top in range(0, min(190, frame.height) - 27):
        for left in range(0, frame.width - 27):
            probes = []
            for delta in (*range(1, 6), *range(22, 27)):
                probes.extend((
                    (left + delta, top),
                    (left + delta, top + 27),
                    (left, top + delta),
                    (left + 27, top + delta),
                ))
            score = sum(orange(x, y) for x, y in probes)
            if score >= 36:
                candidates.append((score, left, top))
    if not candidates:
        raise ValueError(f"Move overlay has no stock selection frame: {path}")
    best = max(score for score, _, _ in candidates)
    selected = [(left, top) for score, left, top in candidates if score == best]
    if len(selected) != 1:
        raise ValueError(f"Move overlay selection frame is ambiguous: {selected}")
    left, top = selected[0]
    return left + 2, top + 1


def plane_b_scroll(gst: Path) -> tuple[int, int, int, int]:
    state = load_gst(gst)
    hscroll = int.from_bytes(
        state.vram[state.hscroll_base + 2:state.hscroll_base + 4],
        "big",
        signed=True,
    )
    payload = gst.read_bytes()
    vscroll = int.from_bytes(
        payload[GST_VSRAM_OFFSET + 2:GST_VSRAM_OFFSET + 4],
        "little",
    ) & 0x03FF
    return hscroll, vscroll, state.plane_width, state.plane_height


def raw_origin_from_selection(
    capture: Path,
    gst: Path,
) -> tuple[tuple[int, int], dict[str, object]]:
    screen_x, screen_y = selection_frame_cell_top_left(capture)
    hscroll, vscroll, width, height = plane_b_scroll(gst)
    raw_x = [
        tile for tile in range(width)
        if (tile * VDP_TILE_PIXELS + hscroll) % (width * VDP_TILE_PIXELS)
        == screen_x
    ]
    raw_y = [
        tile for tile in range(height)
        if (
            tile * VDP_TILE_PIXELS - vscroll + VDP_TILE_PIXELS
        ) % (height * VDP_TILE_PIXELS) == screen_y
    ]
    if len(raw_x) != 1 or len(raw_y) != 1:
        raise ValueError(
            "selection frame does not resolve to one Plane-B raw cell: "
            f"screen={(screen_x, screen_y)} raw_x={raw_x} raw_y={raw_y}"
        )
    return (raw_x[0], raw_y[0]), {
        "screen_cell_top_left": [screen_x, screen_y],
        "plane_b_hscroll_pixels": hscroll,
        "plane_b_vscroll_pixels": vscroll,
        "name_table_tile_dimensions": [width, height],
    }


def battle_cell_delta(raw: int, origin: int, modulus: int) -> int:
    inverse = pow(BATTLE_CELL_TILES, -1, modulus)
    value = ((raw - origin) * inverse) % modulus
    if value > modulus // 2:
        value -= modulus
    return value


def reach_coordinate_report(
    delta: dict[str, object],
    world_origin: tuple[int, int],
    *,
    movement: int,
    overlay_capture: Path,
    overlay_gst: Path,
) -> dict[str, object]:
    """Translate exact 3x3 Plane-B Move cells into world coordinates."""
    blocks = movement_palette_blocks(delta)
    raw_origin, scroll = raw_origin_from_selection(
        overlay_capture, overlay_gst
    )
    coordinates = sorted({
        (
            world_origin[0] + battle_cell_delta(int(x), raw_origin[0], 64),
            world_origin[1] + battle_cell_delta(int(y), raw_origin[1], 32),
        )
        for x, y in blocks["raw_block_starts"]
    })
    distances = [
        abs(x - world_origin[0]) + abs(y - world_origin[1])
        for x, y in coordinates
    ]
    return {
        "world_origin": list(world_origin),
        "raw_plane_b_origin_modulo_name_table": list(raw_origin),
        "selection_and_scroll": scroll,
        "palette_blocks": blocks,
        "movement_allowance": movement,
        "reachable_cell_count": len(coordinates),
        "coordinates": [[x, y] for x, y in coordinates],
        "maximum_manhattan_distance": max(distances),
        "all_coordinates_within_movement_allowance": all(
            distance <= movement for distance in distances
        ),
        "origin_is_reachable": world_origin in coordinates,
    }


def actual_reachable_coordinates(
    delta: dict[str, object],
    origin: tuple[int, int],
    overlay_capture: Path,
    overlay_gst: Path,
    movement: int = 5,
) -> list[list[int]]:
    """Backward-compatible coordinate-only view of the reach report."""
    return reach_coordinate_report(
        delta,
        origin,
        movement=movement,
        overlay_capture=overlay_capture,
        overlay_gst=overlay_gst,
    )["coordinates"]


def send_precise(
    recorder: matrix.RuntimeRecorder,
    keys: Iterable[str],
    *,
    hold: float,
    gap: float,
) -> None:
    key_list = list(keys)
    display = Display(recorder.display)
    try:
        window = key_sender.wait_for_blastem_window(display, 5.0)
        key_sender.activate_window(display, window)
        neutral = ("up", "down", "left", "right")
        for key in key_list:
            if key not in key_sender.KEYSYMS:
                raise ValueError(f"unknown all-factions key: {key}")
            # Unlike the general sender, this historical command must not add
            # a 40 ms neutral sleep before every edge. Release stale controls
            # synchronously, then apply the documented 120/50 ms timing.
            for released in (*neutral, key):
                xtest.fake_input(
                    display,
                    X.KeyRelease,
                    display.keysym_to_keycode(key_sender.KEYSYMS[released]),
                )
            display.sync()
            keycode = display.keysym_to_keycode(key_sender.KEYSYMS[key])
            xtest.fake_input(display, X.KeyPress, keycode)
            display.sync()
            time.sleep(hold)
            xtest.fake_input(display, X.KeyRelease, keycode)
            display.sync()
            time.sleep(gap)
    finally:
        display.close()
    recorder.actions.append({
        "keys": key_list,
        "hold_seconds": hold,
        "gap_seconds": gap,
        "purpose": "stock all-factions command",
    })


def set_all_factions_flag(
    recorder: matrix.RuntimeRecorder,
    *,
    expected_flag: int,
    phase: str,
) -> tuple[Path, dict[str, object], list[dict[str, object]]]:
    """Toggle the stock command to an exact flag and retain every attempt.

    BlastEm samples controller edges on emulated frame boundaries.  A 50 ms
    neutral gap normally records the documented zero between keys, but a busy
    host can occasionally collapse one release/press pair. Retry with an
    increasing neutral gap and retain each rejected GST.
    """
    if expected_flag not in (0, 1):
        raise ValueError("all-factions expected flag must be zero or one")
    attempts = []
    for attempt, gap in enumerate(ALL_FACTIONS_RETRY_GAPS, start=1):
        send_precise(
            recorder,
            ALL_FACTIONS_INPUT,
            hold=ALL_FACTIONS_HOLD_SECONDS,
            gap=gap,
        )
        gst = recorder.save_gst(
            f"states/cheat/{phase}_attempt_{attempt:02d}.gst"
        )
        report = all_factions_runtime_report(gst)
        attempts.append({
            "attempt": attempt,
            "hold_seconds": ALL_FACTIONS_HOLD_SECONDS,
            "gap_seconds": gap,
            **report,
        })
        if (
            report["active_flag"] == expected_flag
            and report["history_contains_expected"]
        ):
            accepted = recorder.save_gst(
                f"states/cheat/{phase}_accepted.gst"
            )
            accepted_report = all_factions_runtime_report(accepted)
            return accepted, accepted_report, attempts
    raise RuntimeError(
        "all-factions toggle did not produce both the exact 29-byte "
        f"history and $FFFFA6C7={expected_flag}: "
        + json.dumps(attempts, ensure_ascii=False)
    )


def activate_all_factions(
    recorder: matrix.RuntimeRecorder,
) -> tuple[Path, dict[str, object], list[dict[str, object]]]:
    return set_all_factions_flag(
        recorder, expected_flag=1, phase="activate"
    )


def deactivate_all_factions(
    recorder: matrix.RuntimeRecorder,
) -> tuple[Path, dict[str, object], list[dict[str, object]]]:
    return set_all_factions_flag(
        recorder, expected_flag=0, phase="deactivate"
    )


def status_distance(first: Path, second: Path) -> float:
    """Return normalized RGB distance for the stable bottom status surface."""
    with Image.open(first) as opened:
        left = opened.convert("RGB").crop((0, 198, 320, 236))
    with Image.open(second) as opened:
        right = opened.convert("RGB").crop((0, 198, 320, 236))
    if left.size != right.size:
        raise ValueError("status reference dimensions changed")
    difference = sum(
        abs(a - b)
        for left_pixel, right_pixel in zip(
            left.get_flattened_data(), right.get_flattened_data()
        )
        for a, b in zip(left_pixel, right_pixel)
    )
    return difference / (left.width * left.height * 3 * 255)


def synchronize_player_commander_cursor(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
    elwin_reference: Path,
    liana_reference: Path,
    max_cycles: int = 24,
) -> tuple[tuple[int, int], dict[str, object]]:
    observations = []
    for cycle in range(1, max_cycles + 1):
        recorder.send(["a"], delay=0.9)
        capture = recorder.capture(
            f"battle/{phase}/cursor_cycle_{cycle:02d}.png"
        )
        distances = {
            "elwin": status_distance(capture, elwin_reference),
            "liana": status_distance(capture, liana_reference),
        }
        closest = min(distances, key=distances.get)
        observations.append({
            "cycle": cycle,
            "capture": file_model(capture),
            "status_distance": distances,
            "closest": closest,
        })
        # Map animation changes a small fraction of the crop. Commander name,
        # class, HP, and numeric fields make a wrong commander much farther
        # away than this conservative 5% normalized threshold.
        if distances[closest] < 0.05:
            coordinate = (
                (11, 17) if closest == "elwin" else (13, 20)
            )
            # Depending on the exact map sub-state, A can leave either the
            # stock movement-range surface or the unit-information popup
            # open.  Normalize both with B before issuing directional input.
            # Runtime23 proved that navigating while the popup remained open
            # silently kept the cursor on Elwin and invalidated the probe.
            recorder.send(["b"], delay=0.8)
            normalized = recorder.capture(
                f"battle/{phase}/cursor_normalized.png"
            )
            normalized_gst = recorder.save_gst(
                f"states/{phase}/cursor_normalized.gst"
            )
            if (
                not sequence.battle_map_surface_visible(normalized)
                or sequence.battle_command_menu_visible(normalized)
            ):
                raise RuntimeError(
                    f"{phase}: commander cursor did not normalize to the "
                    "bare battle map"
                )
            raw_origin, raw_report = raw_origin_from_selection(
                normalized, normalized_gst
            )
            return coordinate, {
                "selected": closest,
                "coordinate": list(coordinate),
                "observations": observations,
                "normalized_capture": file_model(normalized),
                "normalized_gst": file_model(normalized_gst),
                "raw_plane_b_origin_modulo_name_table": list(raw_origin),
                "selection_and_scroll": raw_report,
            }
    raise RuntimeError(
        "could not synchronize the post-cheat cursor to Elwin or Liana"
    )


def navigate_and_verify_cursor(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
    before: tuple[int, int],
    after: tuple[int, int],
    before_raw_origin: tuple[int, int],
) -> dict[str, object]:
    """Navigate and prove the live cursor reached the requested world cell.

    Battle cells are exactly 3x3 VDP name-table tiles.  Comparing raw cursor
    origins before/after therefore remains exact even when the map scrolls or
    wraps around the 64x32 Plane-B name table.
    """
    keys = navigate(recorder, before, after)
    capture = recorder.capture(f"battle/{phase}/target_cursor.png")
    gst = recorder.save_gst(f"states/{phase}/target_cursor.gst")
    raw_origin, scroll = raw_origin_from_selection(capture, gst)
    expected_raw = (
        (before_raw_origin[0] + BATTLE_CELL_TILES * (after[0] - before[0]))
        % int(scroll["name_table_tile_dimensions"][0]),
        (before_raw_origin[1] + BATTLE_CELL_TILES * (after[1] - before[1]))
        % int(scroll["name_table_tile_dimensions"][1]),
    )
    if raw_origin != expected_raw:
        raise RuntimeError(
            f"{phase}: live cursor did not reach world coordinate {after}; "
            f"expected raw Plane-B origin {expected_raw}, got {raw_origin}"
        )
    occupants = runtime_occupants(gst, after)
    return {
        "from_world_coordinate": list(before),
        "to_world_coordinate": list(after),
        "keys": keys,
        "capture": file_model(capture),
        "gst": file_model(gst),
        "before_raw_plane_b_origin": list(before_raw_origin),
        "expected_raw_plane_b_origin": list(expected_raw),
        "actual_raw_plane_b_origin": list(raw_origin),
        "selection_and_scroll": scroll,
        "runtime_occupants": occupants,
    }


def commit_verified_move(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
    origin: tuple[int, int],
    reach_report: dict[str, object],
    selected_member_index: int,
) -> dict[str, object]:
    """Commit one stock-valid Move and Standby for the exact hired Soldier."""
    command = open_unit_command(recorder, phase=phase)
    command_gst = recorder.save_gst(f"states/{phase}/command.gst")
    selected_pointer = selected_runtime_pointer_report(
        command_gst,
        expected_group_index=0,
        expected_member_index=selected_member_index,
    )
    occupied = occupied_runtime_coordinates(command_gst)
    candidates = reachable_empty_destinations(
        reach_report, origin, occupied
    )
    threats = hostile_runtime_coordinates(command_gst)
    if threats:
        candidates.sort(
            key=lambda coordinate: (
                -min(
                    abs(coordinate[0] - threat[0])
                    + abs(coordinate[1] - threat[1])
                    for threat in threats
                ),
                -coordinate[1],
                -abs(coordinate[0] - origin[0])
                - abs(coordinate[1] - origin[1]),
                coordinate,
            )
        )
    if not candidates:
        raise RuntimeError(f"{phase}: overlay has no empty Move candidate")

    recorder.send(["c"], delay=0.8)
    overlay = recorder.capture(f"battle/{phase}/move_overlay.png")
    overlay_gst = recorder.save_gst(f"states/{phase}/move_overlay.gst")
    delta = plane_delta(command_gst, overlay_gst)
    try:
        movement_palette_blocks(delta)
        selection_frame_cell_top_left(overlay)
    except ValueError as exc:
        raise RuntimeError(
            f"{phase}: Move confirmation did not open the stock overlay: {exc}"
        ) from exc

    destination = None
    attempts = []
    cursor = origin
    for attempt_number, candidate in enumerate(candidates, 1):
        keys = navigate(recorder, cursor, candidate, delay=0.6)
        target = recorder.capture(
            f"battle/{phase}/move_target_{attempt_number:02d}.png"
        )
        try:
            cursor_cell = selection_frame_cell_top_left(target)
            valid = True
        except ValueError:
            cursor_cell = None
            valid = False
        attempts.append({
            "candidate": list(candidate),
            "keys": keys,
            "capture": file_model(target),
            "stock_valid_orange_cursor": valid,
            "screen_cell_top_left": (
                list(cursor_cell) if cursor_cell is not None else None
            ),
        })
        cursor = candidate
        if valid:
            destination = candidate
            break
    if destination is None:
        recorder.send(["b"], delay=0.8)
        raise RuntimeError(
            f"{phase}: every empty overlay candidate showed the invalid cursor"
        )

    recorder.send(["c"], delay=0.9)
    moved_capture = recorder.capture(f"battle/{phase}/after_destination.png")
    moved_gst = recorder.save_gst(f"states/{phase}/after_destination.gst")
    moved_group = runtime_group(moved_gst, 0)
    moved = member(moved_group, selected_member_index)
    if (
        moved["class_id"] != SOLDIER_CLASS_ID
        or (int(moved["x"]), int(moved["y"])) != destination
        or destination == origin
        or moved_group["movement_plus_0x44"] != 5
    ):
        raise RuntimeError(f"{phase}: exact Soldier Move failed: {moved_group}")

    # Stock post-Move menu defaults to Standby.  Confirm it so the unit is
    # gray/acted for the remainder of this turn and the next-turn reset is
    # independently observable.
    recorder.send(["c"], delay=1.2)
    standby_capture = recorder.capture(f"battle/{phase}/after_standby.png")
    standby_gst = recorder.save_gst(f"states/{phase}/after_standby.gst")
    standby_group = runtime_group(standby_gst, 0)
    standby = member(standby_group, selected_member_index)
    if (
        standby["class_id"] != SOLDIER_CLASS_ID
        or (int(standby["x"]), int(standby["y"])) != destination
        or standby["acted_flag"] != 1
    ):
        raise RuntimeError(
            f"{phase}: moved Soldier did not enter stock Standby: "
            f"{standby_group}"
        )
    return {
        "origin": list(origin),
        "command_capture": file_model(command),
        "command_gst": file_model(command_gst),
        "selected_runtime_pointer": selected_pointer,
        "move_overlay_capture": file_model(overlay),
        "move_overlay_gst": file_model(overlay_gst),
        "candidate_order": [list(row) for row in candidates],
        "hostile_coordinates": [list(row) for row in sorted(threats)],
        "attempts": attempts,
        "destination": list(destination),
        "after_destination_capture": file_model(moved_capture),
        "after_destination_gst": file_model(moved_gst),
        "after_destination_member": public_member(moved),
        "after_standby_capture": file_model(standby_capture),
        "after_standby_gst": file_model(standby_gst),
        "after_standby_member": public_member(standby),
    }


def require_command_menu(path: Path, label: str) -> None:
    if not (
        sequence.battle_command_menu_visible(path)
        or short_battle_command_menu_visible(path)
    ):
        raise RuntimeError(f"{label}: stock battle command menu did not open")


def short_battle_command_menu_visible(path: Path) -> bool:
    """Recognize stock enemy command panels missed by the shared detector.

    Enemy two-row panels and the five-row commander panel can leave only
    44.1% of the status crop blue.  Retain the exact panel geometry checks and
    additionally require the ornate gold status frame before accepting that
    lower blue threshold.
    """
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    menu = frame.crop((
        round(15 * scale_x), round(25 * scale_y),
        round(95 * scale_x), round(110 * scale_y),
    ))
    interior = frame.crop((
        round(10 * scale_x), round(28 * scale_y),
        round(65 * scale_x), round(105 * scale_y),
    ))
    right_border = frame.crop((
        round(94 * scale_x), round(42 * scale_y),
        round(107 * scale_x), round(145 * scale_y),
    ))
    status = frame.crop((
        0, round(195 * scale_y), frame.width, round(235 * scale_y)
    ))

    def dark_blue(pixel: tuple[int, int, int]) -> bool:
        red, green, blue = pixel
        return (
            50 <= blue <= 180
            and red < 45
            and green < 65
            and blue > red * 2
            and blue > green * 1.8
        )

    def broad_blue(pixel: tuple[int, int, int]) -> bool:
        red, green, blue = pixel
        return blue > 70 and blue > red * 1.3 and blue > green * 1.2

    menu_pixels = menu.width * menu.height
    interior_pixels = interior.width * interior.height
    border_pixels = right_border.width * right_border.height
    status_pixels = status.width * status.height
    menu_blue = sum(1 for pixel in menu.get_flattened_data() if broad_blue(pixel))
    menu_dark = sum(1 for pixel in menu.get_flattened_data() if dark_blue(pixel))
    interior_dark = sum(
        1 for pixel in interior.get_flattened_data() if dark_blue(pixel)
    )
    interior_white = sum(
        1
        for red, green, blue in interior.get_flattened_data()
        if red > 170 and green > 170 and blue > 170
    )
    border_gold = sum(
        1
        for red, green, blue in right_border.get_flattened_data()
        if red > 100 and green > 70 and blue < 80 and red > blue * 1.5
    )
    status_blue = sum(
        1 for pixel in status.get_flattened_data() if broad_blue(pixel)
    )
    status_gold = sum(
        1
        for red, green, blue in status.get_flattened_data()
        if red > 100 and green > 70 and blue < 80 and red > blue * 1.5
    )
    return (
        0.30 < menu_blue / menu_pixels < 0.85
        and menu_dark / menu_pixels > 0.30
        and interior_dark / interior_pixels > 0.25
        and interior_white / interior_pixels > 0.035
        and border_gold / border_pixels > 0.05
        and 0.40 < status_blue / status_pixels < 0.505
        and status_gold / status_pixels > 0.08
    )


def repeat_move_range(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
    repetitions: int,
) -> dict[str, object]:
    command = recorder.capture(f"battle/{phase}/command_initial.png")
    require_command_menu(command, phase)
    command_gst = recorder.save_gst(f"states/{phase}/command_initial.gst")
    ranges = []
    for repetition in range(1, repetitions + 1):
        recorder.send(["c"], delay=0.9)
        overlay = recorder.capture(
            f"battle/{phase}/move_{repetition:02d}.png"
        )
        overlay_gst = recorder.save_gst(
            f"states/{phase}/move_{repetition:02d}.gst"
        )
        delta = plane_delta(command_gst, overlay_gst)
        try:
            palette_blocks = movement_palette_blocks(delta)
            selection_cell = selection_frame_cell_top_left(overlay)
        except ValueError as exc:
            raise RuntimeError(
                f"{phase} repetition {repetition}: confirming Move did not "
                f"open the stock movement overlay: {exc}"
            ) from exc
        ranges.append({
            "repetition": repetition,
            "capture": file_model(overlay),
            "gst": file_model(overlay_gst),
            "name_tables": plane_table_report(overlay_gst),
            "delta_from_command": delta,
            "palette_blocks": palette_blocks,
            "selection_frame_cell_top_left": list(selection_cell),
        })
        recorder.send(["b"], delay=0.9)
        returned = recorder.capture(
            f"battle/{phase}/map_return_{repetition:02d}.png"
        )
        if (
            not sequence.battle_map_surface_visible(returned)
            or sequence.battle_command_menu_visible(returned)
        ):
            raise RuntimeError(
                f"{phase} repetition {repetition}: Move cancel did not "
                "return to the bare battle map"
            )
        if repetition < repetitions:
            recorder.send(["c"], delay=0.9)
            reopened = recorder.capture(
                f"battle/{phase}/command_reopen_{repetition:02d}.png"
            )
            require_command_menu(
                reopened, f"{phase} reopen after repetition {repetition}"
            )
            command_gst = recorder.save_gst(
                f"states/{phase}/command_reopen_{repetition:02d}.gst"
            )
    hashes = [
        row["name_tables"]["combined_plane_a_b_sha256"] for row in ranges
    ]
    delta_cells = [
        row["delta_from_command"]["planes"]["plane_b"][
            "changed_name_table_tile_coordinates"
        ]
        for row in ranges
    ]
    return {
        "repetitions": repetitions,
        "ranges": ranges,
        "overlay_name_tables_identical": len(set(hashes)) == 1,
        "plane_b_reach_cells_identical": all(
            cells == delta_cells[0] for cells in delta_cells
        ),
        "combined_plane_a_b_sha256": hashes[0],
        "changed_plane_b_name_table_tiles": delta_cells[0],
    }


def retained_turn_combat_report(
    capture_prefix: Path,
    accepted_capture: Path,
) -> dict[str, object]:
    """Inventory actual side-view frames retained by the turn detector."""
    candidates = list(
        capture_prefix.parent.glob(
            f"{capture_prefix.stem}_*{capture_prefix.suffix}"
        )
    )

    def frame_index(path: Path) -> int:
        match = re.search(r"_(\d+)$", path.stem)
        return int(match.group(1)) if match else -1

    captures = sorted(candidates, key=frame_index)
    battle_frames = []
    episode_count = 0
    inside_battle = False
    for capture in captures:
        report = mounted.battle_surface_report(capture)
        visible = bool(report["battle_surface_visible"])
        if visible and not inside_battle:
            episode_count += 1
        inside_battle = visible
        if visible:
            battle_frames.append({
                "frame": frame_index(capture),
                "capture": file_model(capture),
                "battle_ui_dark_blue_ratio": report[
                    "battle_ui_dark_blue_ratio"
                ],
            })
    accepted = None
    if battle_frames:
        source = Path(battle_frames[0]["capture"]["path"])
        if not source.is_absolute():
            source = ROOT / source
        accepted_capture.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, accepted_capture)
        accepted = file_model(accepted_capture)
    return {
        "detector_capture_count": len(captures),
        "combat_episode_count": episode_count,
        "combat_frame_count": len(battle_frames),
        "combat_frames": battle_frames,
        "accepted_combat_capture": accepted,
    }


def navigate(
    recorder: matrix.RuntimeRecorder,
    before: tuple[int, int],
    after: tuple[int, int],
    *,
    delay: float = 0.45,
) -> list[str]:
    keys = mercenary.move_keys(before, after)
    recorder.send(keys, delay=delay)
    return keys


def open_unit_command(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
) -> Path:
    recorder.send(["c"], delay=0.9)
    capture = recorder.capture(f"battle/{phase}/command.png")
    require_command_menu(capture, phase)
    return capture


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    require_isolated_display(args.display)
    require_sha256(
        args.rom, args.expected_rom_sha256, "exact supplied Hard v1.3.7 ROM"
    )
    require_sha256(
        args.source_rom,
        args.expected_source_sha256,
        "Japanese source ROM",
    )
    require_sha256(
        args.seed_gst,
        args.expected_seed_sha256,
        "fresh Scenario 1 seed",
    )
    static = static_movement_report(args.source_rom, args.rom)
    all_factions_static = all_factions_static_report(args.rom.read_bytes())
    if (
        not all_factions_static["history_matches_documented_sequence"]
        or all_factions_static["required_current_held_mask"] != "0x40"
    ):
        raise ValueError(f"all-factions matcher changed: {all_factions_static}")
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"hard-s1-movement-{args.run_id}"
    runtime_home = args.runtime_root / runtime_name
    recorder = matrix.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
        hire_args = argparse.Namespace(
            rom=args.rom,
            seed_gst=args.seed_gst,
            scenario=SCENARIO,
            commander_id=ELWIN_COMMANDER_ID,
            commander_class=ELWIN_CLASS_ID,
            commander_level=1,
            commander_experience=0,
            hire_mask_or=0,
            target_page=0,
            target_row=0,
            page_row_count=1,
            hired_count=HIRED_COUNT,
            mercenary_class=SOLDIER_CLASS_ID,
            display=args.display,
        )
        hired_gst = mercenary.launch_and_hire(
            recorder, hire_args, output, runtime_name
        )
        mercenary.enter_battle_command(recorder, args.rom, output)
        opening_command = recorder.capture("battle/opening_command.png")
        require_command_menu(opening_command, "opening Elwin")
        opening_gst = recorder.save_gst("states/opening_command.gst")
        if turn_counter(opening_gst) != 1:
            raise RuntimeError("fresh Scenario 1 did not enter Turn 1")
        elwin_opening = runtime_group(opening_gst, 0)
        soldier_classes = [
            member(elwin_opening, index)["class_id"]
            for index in range(1, HIRED_COUNT + 1)
        ]
        if soldier_classes != [SOLDIER_CLASS_ID] * HIRED_COUNT:
            raise RuntimeError(f"six deployed Soldier identities changed: {soldier_classes}")
        selected_before = member(
            elwin_opening, SELECTED_SOLDIER_MEMBER_INDEX
        )
        if (selected_before["x"], selected_before["y"]) != SELECTED_SOLDIER_COORDINATE:
            raise RuntimeError(f"selected Soldier deployment changed: {selected_before}")

        # Build live status references before the cheat. They let the runner
        # synchronize the cursor after the command's embedded A presses and
        # avoid assuming where a long scrolling input happened to finish.
        recorder.send(["b"], delay=0.8)
        elwin_reference = recorder.capture(
            "battle/cheat/elwin_status_reference.png"
        )
        recorder.send(["a"], delay=0.9)
        liana_reference = recorder.capture(
            "battle/cheat/liana_status_reference.png"
        )
        recorder.send(["a"], delay=0.9)
        elwin_return = recorder.capture(
            "battle/cheat/elwin_status_return.png"
        )
        if (
            status_distance(elwin_return, elwin_reference)
            >= status_distance(elwin_return, liana_reference)
        ):
            raise RuntimeError("pre-cheat A-cycle did not return to Elwin")

        # Activate the stock all-factions command on a known empty map cell.
        empty = (9, 16)
        navigate(recorder, (11, 17), empty)
        post_cheat_gst, cheat_runtime, cheat_attempts = (
            activate_all_factions(recorder)
        )
        post_cheat_cursor, cheat_cursor_sync = (
            synchronize_player_commander_cursor(
                recorder,
                phase="cheat/activated_cursor",
                elwin_reference=elwin_reference,
                liana_reference=liana_reference,
            )
        )

        # Bald remains completely unmodified.  Select him by his exact loaded
        # coordinate and retain three actual Move overlays.
        bald_cursor_target = navigate_and_verify_cursor(
            recorder,
            phase="bald",
            before=post_cheat_cursor,
            after=BALD_COORDINATE,
            before_raw_origin=tuple(
                cheat_cursor_sync[
                    "raw_plane_b_origin_modulo_name_table"
                ]
            ),
        )
        if [
            (
                int(row["group_index"]),
                int(row["member_index"]),
                row["class_id"],
                row["name_id"],
            )
            for row in bald_cursor_target["runtime_occupants"]
        ] != [(BALD_GROUP_INDEX, 0, "0x2E", "0x12")]:
            raise RuntimeError(
                "Bald cursor cell did not contain only exact Bald: "
                f"{bald_cursor_target['runtime_occupants']}"
            )
        bald_command = open_unit_command(recorder, phase="bald")
        bald_command_gst = recorder.save_gst("states/bald/command.gst")
        bald_selected_pointer = selected_runtime_pointer_report(
            bald_command_gst,
            expected_group_index=BALD_GROUP_INDEX,
            expected_member_index=0,
        )
        bald_group = runtime_group(bald_command_gst, BALD_GROUP_INDEX)
        bald_commander = member(bald_group, 0)
        if (
            bald_commander["class_id"] != BALD_CLASS_ID
            or bald_commander["name_id"] != BALD_NAME_ID
            or (bald_commander["x"], bald_commander["y"]) != BALD_COORDINATE
            or bald_group["movement_plus_0x44"] != 5
        ):
            raise RuntimeError(f"Bald runtime identity/movement changed: {bald_group}")
        bald_ranges = repeat_move_range(
            recorder,
            phase="bald",
            repetitions=args.bald_repetitions,
        )
        bald_first_delta = bald_ranges["ranges"][0]["delta_from_command"]
        bald_ranges["reach_coordinate_report"] = reach_coordinate_report(
            bald_first_delta,
            BALD_COORDINATE,
            movement=5,
            overlay_capture=output / "battle/bald/move_01.png",
            overlay_gst=output / "states/bald/move_01.gst",
        )
        bald_ranges["actual_reachable_coordinates"] = bald_ranges[
            "reach_coordinate_report"
        ]["coordinates"]

        # Return to ordinary player/AI ownership before natural progression.
        # The same stock sequence is a toggle; retain exact history plus the
        # authoritative zero flag, then synchronize back to a player cursor.
        cheat_off_gst, cheat_off_runtime, cheat_off_attempts = (
            deactivate_all_factions(recorder)
        )
        normal_play_cursor, normal_play_cursor_sync = (
            synchronize_player_commander_cursor(
                recorder,
                phase="cheat/deactivated_cursor",
                elwin_reference=elwin_reference,
                liana_reference=liana_reference,
            )
        )

        # Let the unmodified Scenario 1 AI supply the combat. At each genuine
        # player-turn boundary, compare all six exact hired-member HP bytes and
        # retain every side-view frame from the intervening enemy turn. This
        # avoids diagnostic ROM/GST edits and selects only a surviving Soldier
        # whose HP actually decreased during a captured combat transition.
        natural_turns = []
        previous_turn_gst = opening_gst
        previous_turn_group = elwin_opening
        selected_soldier_member_index = None
        selected_soldier_coordinate = None
        selected_pre_combat = None
        selected_post_combat = None
        post_combat_gst = None
        post_combat_group = None
        combat = None
        post_combat_cursor = None
        post_combat_cursor_sync = None
        for expected_turn in range(2, args.max_natural_combat_turn + 1):
            turn_end = first_turn.select_turn_end(
                env=recorder.environment,
                display=args.display,
                opening_checks=args.max_turn_confirmations,
                delay=args.turn_confirmation_delay,
            )
            capture_prefix = output / f"natural_turns/turn_{expected_turn}/detect.png"
            endpoint, confirmations = first_turn.run_detector(
                display=args.display,
                max_checks=args.max_turn_confirmations,
                delay=args.turn_confirmation_delay,
                capture_prefix=capture_prefix,
            )
            if endpoint != "turn_command":
                raise RuntimeError(
                    f"Scenario 1 natural combat stopped before Turn "
                    f"{expected_turn}: {endpoint}"
                )
            opening_capture = recorder.capture(
                f"battle/natural_turns/turn_{expected_turn}_command.png"
            )
            require_command_menu(
                opening_capture, f"natural Turn {expected_turn} opening"
            )
            opening_turn_gst = recorder.save_gst(
                f"states/natural_turns/turn_{expected_turn}_command.gst"
            )
            if turn_counter(opening_turn_gst) != expected_turn:
                raise RuntimeError(
                    f"natural Turn counter changed: expected {expected_turn}, "
                    f"got {turn_counter(opening_turn_gst)}"
                )
            opening_turn_group = runtime_group(opening_turn_gst, 0)
            combat_report = retained_turn_combat_report(
                capture_prefix,
                output
                / f"battle/natural_combat/turn_{expected_turn}_side_view.png",
            )
            damaged_survivors = []
            hp_deltas = []
            for member_index in range(1, HIRED_COUNT + 1):
                before_member = member(previous_turn_group, member_index)
                after_member = member(opening_turn_group, member_index)
                if (
                    before_member["class_id"] != SOLDIER_CLASS_ID
                    or after_member["class_id"] != SOLDIER_CLASS_ID
                ):
                    raise RuntimeError(
                        f"hired Soldier identity changed at member {member_index}"
                    )
                delta = int(after_member["hp"]) - int(before_member["hp"])
                if delta:
                    hp_deltas.append({
                        "member_index": member_index,
                        "before_hp": int(before_member["hp"]),
                        "after_hp": int(after_member["hp"]),
                        "delta": delta,
                    })
                if delta < 0 and int(after_member["hp"]) > 0:
                    damaged_survivors.append(member_index)
            transition = {
                "from_turn": expected_turn - 1,
                "to_turn": expected_turn,
                "before_gst": file_model(previous_turn_gst),
                "opening_capture": file_model(opening_capture),
                "opening_gst": file_model(opening_turn_gst),
                "turn_end": turn_end,
                "detector_endpoint": endpoint,
                "detector_confirmations": confirmations,
                "hired_soldier_hp_deltas": hp_deltas,
                "damaged_surviving_member_indices": damaged_survivors,
                "combat": combat_report,
            }
            natural_turns.append(transition)
            if damaged_survivors:
                if combat_report["combat_frame_count"] == 0:
                    raise RuntimeError(
                        "Soldier HP decreased without a retained side-view combat frame"
                    )
                selected_soldier_member_index = min(damaged_survivors)
                selected_pre_combat = member(
                    previous_turn_group, selected_soldier_member_index
                )
                selected_post_combat = member(
                    opening_turn_group, selected_soldier_member_index
                )
                selected_soldier_coordinate = (
                    int(selected_post_combat["x"]),
                    int(selected_post_combat["y"]),
                )
                post_combat_gst = opening_turn_gst
                post_combat_group = opening_turn_group
                combat = combat_report
                recorder.send(["b"], delay=0.8)
                post_combat_cursor, post_combat_cursor_sync = (
                    synchronize_player_commander_cursor(
                        recorder,
                        phase="soldier_post_combat/commander_cursor",
                        elwin_reference=elwin_reference,
                        liana_reference=liana_reference,
                    )
                )
                break
            previous_turn_gst = opening_turn_gst
            previous_turn_group = opening_turn_group
        if selected_soldier_member_index is None:
            raise RuntimeError(
                "no hired Soldier survived HP damage through natural Turn "
                f"{args.max_natural_combat_turn}"
            )
        if selected_post_combat["acted_flag"] != 0:
            raise RuntimeError("defending Soldier incorrectly consumed its action")
        hp_changed = True
        selected_soldier_damaged = True

        post_combat_cursor_target = navigate_and_verify_cursor(
            recorder,
            phase="soldier_post_combat",
            before=post_combat_cursor,
            after=selected_soldier_coordinate,
            before_raw_origin=tuple(
                post_combat_cursor_sync[
                    "raw_plane_b_origin_modulo_name_table"
                ]
            ),
        )
        expected_occupant = (
            0,
            selected_soldier_member_index,
            f"0x{SOLDIER_CLASS_ID:02X}",
            f"0x{ELWIN_COMMANDER_ID:02X}",
        )
        actual_occupants = [
            (
                int(row["group_index"]),
                int(row["member_index"]),
                row["class_id"],
                row["name_id"],
            )
            for row in post_combat_cursor_target["runtime_occupants"]
        ]
        if actual_occupants != [expected_occupant]:
            raise RuntimeError(
                "post-combat cursor cell did not contain only the exact "
                f"damaged Soldier: {actual_occupants}"
            )
        open_unit_command(recorder, phase="soldier_post_combat")
        post_combat_command_gst = recorder.save_gst(
            "states/soldier_post_combat/command.gst"
        )
        post_combat_selected_pointer = selected_runtime_pointer_report(
            post_combat_command_gst,
            expected_group_index=0,
            expected_member_index=selected_soldier_member_index,
        )
        post_combat_command_group = runtime_group(post_combat_command_gst, 0)
        selected_command = member(
            post_combat_command_group, selected_soldier_member_index
        )
        if selected_command != selected_post_combat:
            raise RuntimeError("post-combat command selected a changed Soldier record")
        post_combat_ranges = repeat_move_range(
            recorder,
            phase="soldier_post_combat",
            repetitions=args.soldier_repetitions,
        )
        post_combat_ranges["reach_coordinate_report"] = (
            reach_coordinate_report(
                post_combat_ranges["ranges"][0]["delta_from_command"],
                selected_soldier_coordinate,
                movement=5,
                overlay_capture=(
                    output / "battle/soldier_post_combat/move_01.png"
                ),
                overlay_gst=(
                    output / "states/soldier_post_combat/move_01.gst"
                ),
            )
        )
        post_combat_ranges["actual_reachable_coordinates"] = (
            post_combat_ranges["reach_coordinate_report"]["coordinates"]
        )

        # Move the wounded unit behind the allied formation and confirm
        # Standby before ending the turn.  An earlier exploratory run left an
        # HP8 Soldier beside the enemy; it was naturally killed on the next
        # enemy turn, so the intended same-member reset check had no subject.
        post_combat_survival_move = commit_verified_move(
            recorder,
            phase="soldier_post_combat_survival_move",
            origin=selected_soldier_coordinate,
            reach_report=post_combat_ranges["reach_coordinate_report"],
            selected_member_index=selected_soldier_member_index,
        )

        combat_turn = turn_counter(post_combat_gst)
        next_turn = combat_turn + 1
        # Advance one more complete stock turn after the observed combat, then
        # require the same surviving member to retain class, MV5, and a stable
        # repeated overlay before committing one real highlighted Move.
        post_combat_turn_end = first_turn.select_turn_end(
            env=recorder.environment,
            display=args.display,
            opening_checks=args.max_turn_confirmations,
            delay=args.turn_confirmation_delay,
        )
        post_combat_endpoint, post_combat_confirmations = first_turn.run_detector(
            display=args.display,
            max_checks=args.max_turn_confirmations,
            delay=args.turn_confirmation_delay,
            capture_prefix=output / f"turn{next_turn}/detect.png",
        )
        if post_combat_endpoint != "turn_command":
            raise RuntimeError(
                f"Scenario 1 did not return to Turn {next_turn}: "
                f"{post_combat_endpoint}"
            )
        next_turn_command = recorder.capture(
            f"battle/turn{next_turn}/opening_command.png"
        )
        require_command_menu(next_turn_command, f"Turn {next_turn} opening")
        next_turn_gst = recorder.save_gst(
            f"states/turn{next_turn}/opening_command.gst"
        )
        if turn_counter(next_turn_gst) != next_turn:
            raise RuntimeError(
                f"Turn {next_turn} counter changed: {turn_counter(next_turn_gst)}"
            )
        next_turn_group = runtime_group(next_turn_gst, 0)
        selected_next_turn = member(
            next_turn_group, selected_soldier_member_index
        )
        if (
            selected_next_turn["class_id"] != SOLDIER_CLASS_ID
            or selected_next_turn["hp"] <= 0
            or selected_next_turn["acted_flag"] != 0
            or next_turn_group["movement_plus_0x44"] != 5
        ):
            raise RuntimeError(
                f"selected Soldier Turn {next_turn} state changed: "
                f"{next_turn_group}"
            )

        # Synchronize rather than assuming which player commander the detector
        # opened, then navigate to the exact dynamic member selected by HP.
        recorder.send(["b"], delay=0.8)
        next_turn_cursor, next_turn_cursor_sync = (
            synchronize_player_commander_cursor(
                recorder,
                phase=f"soldier_turn{next_turn}/commander_cursor",
                elwin_reference=elwin_reference,
                liana_reference=liana_reference,
            )
        )
        selected_next_turn_coordinate = (
            int(selected_next_turn["x"]), int(selected_next_turn["y"])
        )
        next_turn_cursor_target = navigate_and_verify_cursor(
            recorder,
            phase=f"soldier_turn{next_turn}",
            before=next_turn_cursor,
            after=selected_next_turn_coordinate,
            before_raw_origin=tuple(
                next_turn_cursor_sync[
                    "raw_plane_b_origin_modulo_name_table"
                ]
            ),
        )
        actual_next_occupants = [
            (
                int(row["group_index"]),
                int(row["member_index"]),
                row["class_id"],
                row["name_id"],
            )
            for row in next_turn_cursor_target["runtime_occupants"]
        ]
        if actual_next_occupants != [expected_occupant]:
            raise RuntimeError(
                "next-turn cursor cell did not contain only the same exact "
                f"Soldier: {actual_next_occupants}"
            )
        next_turn_phase = f"soldier_turn{next_turn}"
        open_unit_command(recorder, phase=next_turn_phase)
        next_turn_selected_pointer_gst = recorder.save_gst(
            f"states/{next_turn_phase}/selected_pointer.gst"
        )
        next_turn_selected_pointer = selected_runtime_pointer_report(
            next_turn_selected_pointer_gst,
            expected_group_index=0,
            expected_member_index=selected_soldier_member_index,
        )
        next_turn_ranges = repeat_move_range(
            recorder,
            phase=next_turn_phase,
            repetitions=args.next_turn_repetitions,
        )
        next_turn_ranges["reach_coordinate_report"] = reach_coordinate_report(
            next_turn_ranges["ranges"][0]["delta_from_command"],
            selected_next_turn_coordinate,
            movement=5,
            overlay_capture=output / f"battle/{next_turn_phase}/move_01.png",
            overlay_gst=output / f"states/{next_turn_phase}/move_01.gst",
        )
        next_turn_ranges["actual_reachable_coordinates"] = next_turn_ranges[
            "reach_coordinate_report"
        ]["coordinates"]

        # Finally commit one ordinary Move and stock Standby to a cell proven
        # by the exact prior overlay.
        commit_phase = f"soldier_turn{next_turn}_commit"
        next_turn_move = commit_verified_move(
            recorder,
            phase=commit_phase,
            origin=selected_next_turn_coordinate,
            reach_report=next_turn_ranges["reach_coordinate_report"],
            selected_member_index=selected_soldier_member_index,
        )
        ordinary_destination = tuple(next_turn_move["destination"])
        moved_capture = output / f"battle/{commit_phase}/after_destination.png"
        moved_gst = output / f"states/{commit_phase}/after_destination.gst"
        moved_group = runtime_group(moved_gst, 0)
        selected_moved = member(
            moved_group, selected_soldier_member_index
        )

        checks = {
            "exact_hard_rom_hash_locked": (
                sha256_path(args.rom) == args.expected_rom_sha256
            ),
            "fresh_s1_seed_hash_locked": (
                sha256_path(args.seed_gst) == args.expected_seed_sha256
            ),
            "product_rom_unchanged": (
                sha256_path(args.rom) == args.expected_rom_sha256
            ),
            "source_and_hard_class_records_identical": static["all_records_byte_identical"],
            "source_hard_bald_soldier_movement_is_five": static["all_expected_movement_five"],
            "six_soldiers_hired_and_deployed": soldier_classes == [SOLDIER_CLASS_ID] * 6,
            "bald_identity_class_coordinate_exact": (
                bald_commander["class_id"] == BALD_CLASS_ID
                and bald_commander["name_id"] == BALD_NAME_ID
                and (bald_commander["x"], bald_commander["y"]) == BALD_COORDINATE
            ),
            "bald_runtime_plus_0x44_is_five": bald_group["movement_plus_0x44"] == 5,
            "bald_repeated_reach_map_invariant": (
                bald_ranges["plane_b_reach_cells_identical"]
            ),
            "all_factions_disabled_before_natural_play": (
                cheat_off_runtime["active_flag"] == 0
                and cheat_off_runtime["history_contains_expected"]
            ),
            "natural_combat_transition_captured": (
                combat["combat_frame_count"] > 0
                and selected_soldier_member_index
                in natural_turns[-1]["damaged_surviving_member_indices"]
            ),
            "actual_side_view_combat_observed": combat["combat_frame_count"] > 0,
            "exact_combat_units_changed_hp": hp_changed,
            "exact_selected_soldier_damaged": selected_soldier_damaged,
            "same_soldier_survived_combat_unacted": (
                selected_post_combat["hp"] > 0
                and selected_post_combat["acted_flag"] == 0
            ),
            "post_combat_runtime_plus_0x44_is_five": post_combat_group["movement_plus_0x44"] == 5,
            "post_combat_repeated_reach_map_invariant": (
                post_combat_ranges["plane_b_reach_cells_identical"]
            ),
            "post_combat_real_move_and_standby_committed": (
                tuple(post_combat_survival_move["destination"])
                != selected_soldier_coordinate
                and post_combat_survival_move[
                    "after_standby_member"
                ]["acted_flag"] == 1
            ),
            "combat_turn_is_natural_scenario_progression": (
                2 <= combat_turn <= args.max_natural_combat_turn
            ),
            "real_next_turn_reached": turn_counter(next_turn_gst) == next_turn,
            "same_soldier_next_turn_unacted": (
                selected_next_turn["acted_flag"] == 0
            ),
            "next_turn_runtime_plus_0x44_is_five": (
                next_turn_group["movement_plus_0x44"] == 5
            ),
            "next_turn_repeated_reach_map_invariant": (
                next_turn_ranges["plane_b_reach_cells_identical"]
            ),
            "same_soldier_real_move_committed": (
                (selected_moved["x"], selected_moved["y"])
                == ordinary_destination
                and ordinary_destination != selected_next_turn_coordinate
            ),
        }
        result = {
            "schema_version": 1,
            "status": "pass" if all(checks.values()) else "fail",
            "scope": "exact supplied unmodified Hard v1.3.7 Scenario 1 movement regression",
            "expected_sha256": {
                "rom": args.expected_rom_sha256,
                "source_rom": args.expected_source_sha256,
                "seed_gst": args.expected_seed_sha256,
            },
            "rom": file_model(args.rom),
            "seed": file_model(args.seed_gst),
            "scenario": SCENARIO,
            "static_movement": static,
            "all_factions_static": all_factions_static,
            "hire_and_deployment": {
                "hired_count": HIRED_COUNT,
                "hired_class_id": f"0x{SOLDIER_CLASS_ID:02X}",
                "hired_gst": file_model(hired_gst),
                "opening_gst": file_model(opening_gst),
                "elwin_group": public_group(elwin_opening),
            },
            "bald": {
                "all_factions_runtime": cheat_runtime,
                "all_factions_attempts": cheat_attempts,
                "post_cheat_cursor_synchronization": cheat_cursor_sync,
                "cursor_target_proof": bald_cursor_target,
                "command_capture": file_model(bald_command),
                "command_gst": file_model(bald_command_gst),
                "selected_runtime_pointer": bald_selected_pointer,
                "runtime_group": public_group(bald_group),
                "ranges": bald_ranges,
                "all_factions_disable_gst": file_model(cheat_off_gst),
                "all_factions_disable_runtime": cheat_off_runtime,
                "all_factions_disable_attempts": cheat_off_attempts,
                "normal_play_cursor": list(normal_play_cursor),
                "normal_play_cursor_synchronization": normal_play_cursor_sync,
            },
            "combat": {
                "turn": combat_turn,
                "natural_turn_transitions": natural_turns,
                "selected_soldier": {
                    "group_index": 0,
                    "member_index": selected_soldier_member_index,
                    "coordinate": list(selected_soldier_coordinate),
                    "before": public_member(selected_pre_combat),
                    "after": public_member(selected_post_combat),
                },
                "post_combat_gst": file_model(post_combat_gst),
                "post_combat_cursor_synchronization": post_combat_cursor_sync,
                "post_combat_cursor_target_proof": post_combat_cursor_target,
                "post_combat_selected_runtime_pointer": (
                    post_combat_selected_pointer
                ),
                "hp_changed": hp_changed,
                "selected_soldier_damaged": selected_soldier_damaged,
                "runtime": combat,
            },
            "same_soldier_post_combat_ranges": post_combat_ranges,
            "post_combat_survival_move": post_combat_survival_move,
            "post_combat_turn_end": {
                **post_combat_turn_end,
                "detector_endpoint": post_combat_endpoint,
                "detector_confirmations": post_combat_confirmations,
            },
            f"turn{next_turn}": {
                "opening_command_capture": file_model(next_turn_command),
                "opening_gst": file_model(next_turn_gst),
                "counter": turn_counter(next_turn_gst),
                "cursor_synchronization": next_turn_cursor_sync,
                "cursor_target_proof": next_turn_cursor_target,
                "selected_runtime_pointer": next_turn_selected_pointer,
                "selected_soldier": public_member(selected_next_turn),
                "runtime_group": public_group(next_turn_group),
                "ranges": next_turn_ranges,
                "move": next_turn_move,
                "move_destination_attempts": next_turn_move["attempts"],
                "move_destination": list(ordinary_destination),
                "moved_capture": file_model(moved_capture),
                "moved_gst": file_model(moved_gst),
                "selected_soldier_after_move": public_member(selected_moved),
            },
            "checks": checks,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        evidence = output / "evidence.json"
        evidence.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--seed-gst", type=Path, default=DEFAULT_SEED_GST)
    parser.add_argument(
        "--expected-rom-sha256",
        type=validate_sha256,
        default=EXPECTED_ROM_SHA256,
        help="required SHA-256 for --rom (default: current release identity)",
    )
    parser.add_argument(
        "--expected-source-sha256",
        type=validate_sha256,
        default=EXPECTED_SOURCE_SHA256,
        help="required SHA-256 for --source-rom",
    )
    parser.add_argument(
        "--expected-seed-sha256",
        type=validate_sha256,
        default=EXPECTED_SEED_SHA256,
        help="required SHA-256 for --seed-gst",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--bald-repetitions", type=int, default=3)
    parser.add_argument("--soldier-repetitions", type=int, default=5)
    parser.add_argument("--next-turn-repetitions", type=int, default=3)
    parser.add_argument("--max-natural-combat-turn", type=int, default=10)
    parser.add_argument("--max-turn-confirmations", type=int, default=1200)
    parser.add_argument("--turn-confirmation-delay", type=float, default=0.18)
    args = parser.parse_args()
    for name in (
        "rom", "source_rom", "seed_gst", "output_root", "runtime_root",
        "xvfb", "xvfb_library_path",
    ):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (
        ("ROM", args.rom),
        ("source ROM", args.source_rom),
        ("seed GST", args.seed_gst),
        ("Xvfb", args.xvfb),
        ("Xvfb library path", args.xvfb_library_path),
    ):
        if not path.exists():
            parser.error(f"{label} does not exist: {path}")
    for name in (
        "bald_repetitions",
        "soldier_repetitions",
        "next_turn_repetitions",
    ):
        if getattr(args, name) < 2:
            parser.error(f"--{name.replace('_', '-')} must be at least 2")
    if not 2 <= args.max_natural_combat_turn <= 10:
        parser.error("--max-natural-combat-turn must be between 2 and 10")
    if args.max_turn_confirmations < 10:
        parser.error("turn detector limit must be at least 10")
    result = run_probe(args)
    print(
        f"{result['status']}: exact supplied Hard S1 combat movement probe; "
        f"evidence={relative(args.output_root / args.run_id / 'evidence.json')}"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
