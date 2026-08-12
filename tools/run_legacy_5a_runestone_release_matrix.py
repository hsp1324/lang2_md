#!/usr/bin/env python3
# ruff: noqa: E402
"""Exercise legacy v1.3.6 0x5A markers on exact v1.3.7 ROMs.

This is intentionally separate from ``run_runestone_restart_matrix.py``.  The
existing tier-2-through-tier-5 matrix uses a temporary diagnostic ROM to place
the level-up context.  This focused compatibility regression never writes a
ROM: it builds an external, checksum-valid old-save SRAM fixture, loads that
fixture through the ordinary title LOAD UI, equips a real Rune Stone through
the preparation UI, and reaches the stock class-change handler through an
ordinary player-issued Move and Attack on an exact release ROM.  Setup and
combat remain in the one BlastEm process that loaded the SRAM; GST files are
captured only as read-only evidence and are never reloaded.

After the tier-2 choice is applied, the runner saves through the game's own
START-menu SAVE command, lets BlastEm flush cartridge SRAM, starts a new
BlastEm PID with the same HOME, and reloads manual slot 1 through the title
LOAD UI.  The cold reload therefore checks persisted state without importing
another SRAM image or restoring a GST.

Each fixture contains the legacy value ``0x5A`` at the real Keith, Lester and
Jessica cartridge-SRAM addresses.  A passing run proves all three bytes are
zero after BlastEm flushes SRAM, the selected tier-2 class is LV1 with the
stock residual EXP, the Rune Stone is gone, and Lester/Jessica did not receive
the join-only EXP grant.  The EXP part is dynamic: stock Rune Stone handling
resets the level to 1 but
preserves any residual EXP already present at the level-10 trigger (for
example, LV10/EXP1 becomes tier-2 LV1/EXP1).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import queue
import shutil
import sys
import time
from typing import Iterable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_class_change_probe_rom as class_probe
from tools import capture_class_change_application as application
from tools import run_blastem_sequence as blastem
from tools import run_hard_s1_movement_regression as movement
from tools import run_pike_acted_surface_probe as battle
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as parallel
from tools import run_runestone_restart_matrix as tier_matrix
from tools.pillow_compat import flattened_image_data
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


PROFILES = ("pure", "normal", "hard")
SCENARIO_NUMBER = 12
RUNESTONE_ITEM_ID = 0x1A
LEGACY_MARKER = 0x5A
CLEARED_MARKER = 0x00
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_GROUP_COUNT = 40
SCENARIO_12_RUNTIME_GROUP_COUNT = 18
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_Y_OFFSET = 0x07
RUNTIME_SIDE_OFFSET = 0x20
RUNTIME_AT_MODIFIER_OFFSET = 0x3A
RUNTIME_DF_MODIFIER_OFFSET = 0x3B
EQUIPPED_ITEM_OFFSET = 0x0B
SELECTED_GROUP_INDEX_ADDRESS = 0xA624
SELECTED_MEMBER_INDEX_ADDRESS = 0xA625
SELECTED_GROUP_POINTER_ADDRESS = 0xA628
SELECTED_MEMBER_POINTER_ADDRESS = 0xA62C
CURSOR_X_ADDRESS = 0xA6DF
CURSOR_Y_ADDRESS = 0xA6E1
RUNTIME_GROUP_ABSOLUTE_BASE = 0x00FF0000 + RUNTIME_GROUP_BASE
STAGED_ENEMY_GROUP = 9
STAGED_ENEMY_MEMBER = 0
STAGED_ENEMY_CLASS = 0x59
STAGED_ENEMY_NAME = 0x49
STAGED_ENEMY_LIVE_SUBORDINATES = tuple(range(1, 7))
STAGED_ENEMY_SENTINEL = 7
STOCK_EXP_CLASS_SCAN_START = 0x01480C
STOCK_EXP_CLASS_SCAN_END = 0x014D60
STOCK_EXP_CLASS_SCAN_SHA256 = (
    "692b8e924d47904f4a35c567f46eb16883b746a3ad90e52d0907af1ad3592add"
)
STOCK_RUNESTONE_ITEM_GATE = 0x014B4A
STOCK_RUNESTONE_ITEM_GATE_BYTES = bytes.fromhex("0C 28 00 1A 00 0B")
STOCK_RUNESTONE_CONSUME_ROUTINE = 0x014D2C
STOCK_RUNESTONE_CONSUME_PREFIX = bytes.fromhex("48 E7 C0 40 11 7C 00 00 00 0B")
STOCK_LEVEL_UP_GATE = 0x014856
STOCK_LEVEL_UP_GATE_BYTES = bytes.fromhex(
    "14 31 10 14 E7 0A B4 28 00 2F 62 00 04 BA 95 28 00 2F 52 28 00 2E"
)
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/legacy_5a_runestone_release_matrix"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/legacy_5a_runestone_release_runtime"
RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
LIVE_COMBAT_BOOST_AT = 80
LIVE_COMBAT_BOOST_DF = 80
ELWIN_COMMANDER_ID = 1
LIVE_OBJECTIVE_GUARD_DF = 99
LIVE_CHEAT_EMPTY_CELL = (24, 29)
BATTLE_RESULT_PANEL = (80, 150, 255, 190)
BATTLE_CLASS_READY_BANNER = (60, 95, 260, 140)
COMMANDER_STATUS_PANEL = (135, 35, 275, 145)
SAVE_CONFIRMATION_CURSOR_BOXES = (
    (80, 98, 87, 113),
    (80, 114, 87, 128),
)
STOCK_DARK_BLUE = (0, 0, 119)
POST_COMBAT_SETTLE_POLLS = 8
POST_COMBAT_SETTLE_DELAY = 0.4


class CombatRetryRequired(RuntimeError):
    """The ordinary attack completed but did not reach the LV10 boundary."""

# Every combat fixture below is reached with stock Move commands in the same
# live process that loaded the external SRAM.  The hostile coordinates are the
# exact Scenario 12 opening records; no GST is reloaded and no occupancy table
# is synthesized.  Jessica first moves Elwin off the only shortest-path cell
# that lets the General and Jessica become adjacent in one player turn.
LIVE_COMBAT_ROUTES: dict[str, dict[str, object]] = {
    "keith": {
        "pre_moves": (),
        "enemy": {
            "group": 14,
            "member": 4,
            "class_id": 0x8C,
            "origin": (22, 19),
            "destination": (22, 21),
        },
        "target_destination": (22, 24),
    },
    "lester": {
        "pre_moves": (),
        "enemy": {
            "group": 14,
            "member": 4,
            "class_id": 0x8C,
            "origin": (22, 19),
            "destination": (22, 21),
        },
        "target_destination": (23, 24),
    },
    "jessica": {
        "pre_moves": (
            {
                "group": 0,
                "member": 0,
                "class_id": 0x01,
                "origin": (15, 23),
                "destination": (14, 24),
            },
        ),
        "enemy": {
            "group": 13,
            "member": 0,
            "class_id": 0x54,
            "origin": (15, 15),
            "destination": (15, 23),
        },
        "target_destination": (15, 24),
    },
}

# One representative, naturally reachable tier-3 class per character.  The
# Rune Stone restarts each row at the character's first three tier-2 choices.
# selected_index is one-based, matching the visible UI row.
CASES: dict[str, dict[str, object]] = {
    "keith": {
        "commander_id": 7,
        "tier": 3,
        "current_class": 0x0B,
        "candidate_classes": (0x04, 0x2B, 0x08),
        "candidate_labels": ("로드", "호크로드", "힐러"),
        "label_fingerprint": (
            "e5cf981faeef5139733e62875b05cb637ff60758b7362c141e933d267b2a4587"
        ),
        "selected_index": 2,
        "selected_class": 0x2B,
    },
    "lester": {
        "commander_id": 9,
        "tier": 3,
        "current_class": 0x0C,
        "candidate_classes": (0x05, 0x2C, 0x0A),
        "candidate_labels": ("나이트", "크로코로드", "샤먼"),
        "label_fingerprint": (
            "be5d7c3e0a6a69b8d9fdbc9f50abb943f4dd60273ea697be91c4be28ca8a1657"
        ),
        "selected_index": 2,
        "selected_class": 0x2C,
    },
    "jessica": {
        "commander_id": 10,
        "tier": 3,
        "current_class": 0x11,
        "candidate_classes": (0x08, 0x09, 0x04),
        "candidate_labels": ("힐러", "소서러", "로드"),
        "label_fingerprint": (
            "3c436dfea9136f11b0be8f1cdccb97a9a5a3b20659772432f187d57fcdf89101"
        ),
        "selected_index": 1,
        "selected_class": 0x08,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def marker_address(commander_id: int) -> int:
    return int(builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]["active_marker_address"])


def marker_offset(commander_id: int) -> int:
    address = marker_address(commander_id)
    start = tier_matrix.SRAM_START_ADDRESS
    if address < start or (address - start) % 2:
        raise ValueError(
            f"commander {commander_id} marker is not an odd SRAM byte: 0x{address:08X}"
        )
    offset = (address - start) // 2
    if not 0 <= offset < tier_matrix.SRAM_BYTES:
        raise ValueError(f"commander {commander_id} marker is outside BlastEm SRAM")
    return offset


def marker_report(path: Path, expected: int) -> dict[str, object]:
    payload = path.read_bytes()
    if len(payload) != tier_matrix.SRAM_BYTES:
        raise ValueError(
            f"BlastEm SRAM size {len(payload)} != {tier_matrix.SRAM_BYTES}"
        )
    rows = []
    for character, definition in CASES.items():
        commander_id = int(definition["commander_id"])
        offset = marker_offset(commander_id)
        rows.append(
            {
                "character": character,
                "commander_id": commander_id,
                "address": f"0x{marker_address(commander_id):08X}",
                "sram_offset": f"0x{offset:04X}",
                "value": payload[offset],
            }
        )
    passed = all(row["value"] == expected for row in rows)
    return {
        "status": "pass" if passed else "fail",
        **file_report(path),
        "expected_value": expected,
        "markers": rows,
    }


def find_runtime_sram(runtime_home: Path) -> Path:
    paths = sorted(runtime_home.rglob("save.sram"))
    if len(paths) != 1:
        raise ValueError(
            f"expected one save.sram under {runtime_home}, found {len(paths)}"
        )
    return paths[0]


def live_process_identity(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    phase: str,
) -> dict[str, object]:
    """Bind one checkpoint to the exact isolated BlastEm process."""
    pids = blastem.running_blastem_pids(display=recorder.display)
    if len(pids) != 1:
        raise RuntimeError(
            f"{phase}: expected one live BlastEm PID on {recorder.display}, "
            f"found {pids}"
        )
    pid = pids[0]
    proc = Path(f"/proc/{pid}")
    argv = [
        part.decode("utf-8", errors="replace")
        for part in (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    ]
    environment: dict[str, str] = {}
    for entry in (proc / "environ").read_bytes().split(b"\0"):
        if b"=" not in entry:
            continue
        name, value = entry.split(b"=", 1)
        if name in (b"HOME", b"DISPLAY"):
            environment[name.decode("ascii")] = value.decode(
                "utf-8", errors="replace"
            )
    expected_home = str(recorder.runtime_home.resolve())
    expected_display = blastem.blastem_display.normalize_display(
        recorder.display
    )
    observed_display = blastem.blastem_display.normalize_display(
        environment.get("DISPLAY", "")
    )
    resolved_rom = str(rom.resolve())
    if environment.get("HOME") != expected_home:
        raise RuntimeError(
            f"{phase}: live BlastEm HOME {environment.get('HOME')!r} "
            f"!= {expected_home!r}"
        )
    if observed_display != expected_display:
        raise RuntimeError(
            f"{phase}: live BlastEm DISPLAY {observed_display!r} "
            f"!= {expected_display!r}"
        )
    if resolved_rom not in argv or "-s" in argv:
        raise RuntimeError(
            f"{phase}: live BlastEm argv is not an ordinary exact-ROM launch: "
            f"{argv}"
        )
    stat = (proc / "stat").read_text(encoding="ascii")
    closing = stat.rfind(")")
    fields = stat[closing + 2 :].split() if closing >= 0 else []
    if len(fields) < 20:
        raise RuntimeError(f"{phase}: cannot parse /proc/{pid}/stat")
    return {
        "phase": phase,
        "pid": pid,
        "proc_start_time_ticks": int(fields[19]),
        "argv": argv,
        "argv_has_savestate_restore_option": "-s" in argv,
        "runtime_home": expected_home,
        "observed_home": environment["HOME"],
        "display": expected_display,
        "observed_display": environment["DISPLAY"],
        "rom": resolved_rom,
        "rom_sha256": sha256(rom),
    }


def assert_same_live_process(
    baseline: dict[str, object],
    checkpoint: dict[str, object],
) -> None:
    fields = ("pid", "proc_start_time_ticks", "runtime_home", "display", "rom")
    previous = {field: baseline[field] for field in fields}
    current = {field: checkpoint[field] for field in fields}
    if current != previous:
        raise RuntimeError(
            "BlastEm process identity changed inside one accepted case: "
            f"baseline={previous}, checkpoint={current}"
        )


def manual_slot_record(path: Path, slot_index: int = 0) -> bytes:
    payload = path.read_bytes()
    if len(payload) != blastem.BLASTEM_SRAM_SIZE:
        raise ValueError("manual-slot SRAM must be exactly 8192 bytes")
    blastem.manual_slot_scenario_number(path, slot_index)
    base = blastem.MANUAL_SLOT_BASES[slot_index]
    end = base + blastem.MANUAL_SLOT_CHECKSUM_DATA_SIZE
    return payload[base:end]


def saved_commander(path: Path, commander_id: int) -> dict[str, int]:
    return saved_commander_from_record(manual_slot_record(path), commander_id)


def saved_commander_from_record(
    record: bytes,
    commander_id: int,
) -> dict[str, int]:
    start = (
        blastem.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + (commander_id - 1) * blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    row = record[start : start + blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE]
    if len(row) != blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE:
        raise ValueError("manual-slot commander record is truncated")
    return {
        "commander_id": commander_id,
        "class_id": row[blastem.MANUAL_SLOT_COMMANDER_CLASS_OFFSET],
        "level": row[blastem.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET],
        "experience": row[blastem.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET],
    }


def saved_commander_combat_stats(
    path: Path,
    commander_id: int,
) -> dict[str, int]:
    record = manual_slot_record(path)
    start = (
        blastem.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + (commander_id - 1) * blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    row = record[start : start + blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE]
    if len(row) != blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE:
        raise ValueError("manual-slot commander record is truncated")
    return {
        "commander_id": commander_id,
        "at": row[blastem.MANUAL_SLOT_COMMANDER_AT_OFFSET],
        "df": row[blastem.MANUAL_SLOT_COMMANDER_DF_OFFSET],
    }


def inventory_records_from_record(record: bytes) -> list[tuple[int, int]]:
    start = blastem.MANUAL_SLOT_ITEM_INVENTORY_OFFSET
    size = blastem.MANUAL_SLOT_ITEM_INVENTORY_RECORD_SIZE
    end = start + blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT * size
    payload = record[start:end]
    if len(payload) != blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT * size:
        raise ValueError("manual-slot item inventory is truncated")
    return [
        (payload[offset], payload[offset + 1])
        for offset in range(0, len(payload), size)
    ]


def inventory_records_from_sram(path: Path) -> list[tuple[int, int]]:
    return inventory_records_from_record(manual_slot_record(path))


def inventory_records_from_gst(path: Path) -> list[tuple[int, int]]:
    return inventory_records_from_record(preparation.manual_slot_record_from_gst(path))


def clear_saved_commander_equipment(path: Path, slot_index: int = 0) -> None:
    """Remove seed equipment before installing the one-item UI fixture.

    ``patch_manual_slot_items`` intentionally replaces the inventory table.
    Leaving the campaign seed's commander item bytes behind would create
    owner-less phantom equipment (Keith and Lester normally have items at the
    Scenario 12 boundary).  Keep the external fixture internally consistent:
    every commander starts unequipped and the inventory contains only the real
    unequipped Rune Stone selected by the UI below.
    """
    blastem.manual_slot_scenario_number(path, slot_index)
    payload = bytearray(path.read_bytes())
    base = blastem.MANUAL_SLOT_BASES[slot_index]
    for commander_index in range(blastem.MANUAL_SLOT_COMMANDER_COUNT):
        record = (
            base
            + blastem.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + commander_index * blastem.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        payload[record + EQUIPPED_ITEM_OFFSET] = 0
    checksum = base + blastem.MANUAL_SLOT_CHECKSUM_OFFSET
    payload[checksum : checksum + 2] = blastem.manual_slot_checksum(
        payload, base
    ).to_bytes(2, "big")
    path.write_bytes(payload)


def inventory_report(records: list[tuple[int, int]]) -> dict[str, object]:
    runestones = [
        {"slot": index, "item_id": item, "owner": owner}
        for index, (item, owner) in enumerate(records)
        if item == RUNESTONE_ITEM_ID
    ]
    return {
        "record_count": len(records),
        "runestone_count": len(runestones),
        "runestones": runestones,
    }


def runestone_equipment_transfer_report(
    before_records: list[tuple[int, int]],
    after_records: list[tuple[int, int]],
    target_before: dict[str, int],
    target_after: dict[str, int],
) -> dict[str, object]:
    before = inventory_report(before_records)
    after = inventory_report(after_records)
    passed = (
        before["runestone_count"] == 1
        and before["runestones"][0]["owner"]
        == blastem.MANUAL_SLOT_ITEM_UNEQUIPPED_OWNER
        and target_before["equipped_item"] == 0
        and after["runestone_count"] == 1
        and after["runestones"][0]["owner"] == target_after["commander_id"]
        and target_after["equipped_item"] == RUNESTONE_ITEM_ID
    )
    return {
        "status": "pass" if passed else "fail",
        "unequipped_inventory_before": before,
        "unequipped_inventory_after": after,
        "target_equipped_item_before": target_before["equipped_item"],
        "target_equipped_item_after": target_after["equipped_item"],
    }


def runtime_commanders(path: Path) -> dict[int, dict[str, int]]:
    ram = runtime_ram(path)
    result: dict[int, dict[str, int]] = {}
    # Scenario 12 owns only the first 18 runtime groups.  Later groups are
    # scratch/storage and can legitimately contain byte patterns that resemble
    # a commander after side-view combat (for example, group 36 can expose a
    # stale name byte of 10).  Accept only live player-side commander groups so
    # those unrelated bytes cannot be mistaken for Jessica/Keith/Lester.
    for group in range(SCENARIO_12_RUNTIME_GROUP_COUNT):
        start = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        record = ram[start : start + RUNTIME_GROUP_SIZE]
        commander_id = record[1]
        if (
            commander_id not in (7, 9, 10)
            or record[RUNTIME_SIDE_OFFSET] != 0x01
        ):
            continue
        if commander_id in result:
            raise ValueError(f"GST repeats commander {commander_id}: {path}")
        result[commander_id] = {
            "runtime_group": group,
            "class_id": record[0],
            "commander_id": commander_id,
            "level": record[0x2E],
            "experience": record[0x2F],
            "equipped_item": record[EQUIPPED_ITEM_OFFSET],
            "x": record[0x06],
            "y": record[0x07],
        }
    if set(result) != {7, 9, 10}:
        raise ValueError(f"GST commander set {sorted(result)} != [7, 9, 10]: {path}")
    return result


def runtime_ram(path: Path) -> bytes:
    gst = path.read_bytes()
    ram_start = blastem.GST_WORK_RAM_FILE_OFFSET
    ram = gst[ram_start : ram_start + 0x10000]
    if len(ram) != 0x10000:
        raise ValueError(f"GST is missing work RAM: {path}")
    return ram


def runtime_member(
    path: Path,
    group_index: int,
    member_index: int,
) -> dict[str, int]:
    if not 0 <= group_index < RUNTIME_GROUP_COUNT:
        raise ValueError("runtime group index is outside 0..39")
    if not 0 <= member_index < 8:
        raise ValueError("runtime member index is outside 0..7")
    ram = runtime_ram(path)
    group_start = RUNTIME_GROUP_BASE + group_index * RUNTIME_GROUP_SIZE
    start = group_start + member_index * RUNTIME_MEMBER_SIZE
    record = ram[start : start + RUNTIME_MEMBER_SIZE]
    return {
        "group_index": group_index,
        "member_index": member_index,
        "class_id": record[0],
        "name_id": record[1],
        "side_id": ram[group_start + RUNTIME_SIDE_OFFSET],
        "defeated_flag": record[RUNTIME_DEFEATED_FLAG_OFFSET],
        "hp": record[RUNTIME_HP_OFFSET],
        "x": record[RUNTIME_X_OFFSET],
        "y": record[RUNTIME_Y_OFFSET],
    }


def runtime_group_combat_stats(path: Path, group_index: int) -> dict[str, int]:
    if not 0 <= group_index < RUNTIME_GROUP_COUNT:
        raise ValueError("runtime group index is outside 0..39")
    ram = runtime_ram(path)
    start = RUNTIME_GROUP_BASE + group_index * RUNTIME_GROUP_SIZE
    return {
        "group_index": group_index,
        "at": ram[start + RUNTIME_AT_MODIFIER_OFFSET],
        "df": ram[start + RUNTIME_DF_MODIFIER_OFFSET],
    }


def live_occupants(path: Path, coordinate: tuple[int, int]) -> list[dict[str, int]]:
    return [
        row
        for group_index in range(SCENARIO_12_RUNTIME_GROUP_COUNT)
        for member_index in range(8)
        if (
            (row := runtime_member(path, group_index, member_index))["class_id"]
            != 0xFF
            and row["hp"] > 0
            and (row["x"], row["y"]) == coordinate
        )
    ]


def runtime_selection(path: Path) -> dict[str, int]:
    ram = runtime_ram(path)
    return {
        "selected_group_index": ram[SELECTED_GROUP_INDEX_ADDRESS],
        "selected_member_index": ram[SELECTED_MEMBER_INDEX_ADDRESS],
        "cursor_x": ram[CURSOR_X_ADDRESS],
        "cursor_y": ram[CURSOR_Y_ADDRESS],
    }


def runtime_command_selection(path: Path) -> dict[str, object]:
    ram = runtime_ram(path)
    selection = runtime_selection(path)
    group_index = selection["selected_group_index"]
    member_index = selection["selected_member_index"]
    if not 0 <= group_index < RUNTIME_GROUP_COUNT:
        raise ValueError(f"selected group is outside runtime table: {group_index}")
    if not 0 <= member_index < 8:
        raise ValueError(f"selected member is outside runtime group: {member_index}")
    group_pointer = int.from_bytes(
        ram[SELECTED_GROUP_POINTER_ADDRESS : SELECTED_GROUP_POINTER_ADDRESS + 4],
        "big",
    )
    member_pointer = int.from_bytes(
        ram[SELECTED_MEMBER_POINTER_ADDRESS : SELECTED_MEMBER_POINTER_ADDRESS + 4],
        "big",
    )
    expected_group_pointer = (
        RUNTIME_GROUP_ABSOLUTE_BASE + group_index * RUNTIME_GROUP_SIZE
    )
    expected_member_pointer = (
        expected_group_pointer + member_index * RUNTIME_MEMBER_SIZE
    )
    if (
        group_pointer != expected_group_pointer
        or member_pointer != expected_member_pointer
    ):
        raise ValueError(
            "stock command pointers do not match selected runtime record: "
            f"group=0x{group_pointer:08X}/0x{expected_group_pointer:08X}, "
            f"member=0x{member_pointer:08X}/0x{expected_member_pointer:08X}"
        )
    selected = runtime_member(path, group_index, member_index)
    if (selection["cursor_x"], selection["cursor_y"]) != (
        selected["x"],
        selected["y"],
    ):
        raise ValueError(
            "stock command cursor does not match selected runtime record: "
            f"cursor={(selection['cursor_x'], selection['cursor_y'])}, "
            f"record={(selected['x'], selected['y'])}"
        )
    return {
        **selection,
        "selected_group_pointer": f"0x{group_pointer:08X}",
        "selected_member_pointer": f"0x{member_pointer:08X}",
        "selected_runtime_record": selected,
    }


def exact_cursor_navigation(
    source: tuple[int, int],
    target: tuple[int, int],
) -> list[str]:
    if any(not 0 <= coordinate <= 0xFF for coordinate in (*source, *target)):
        raise ValueError("cursor coordinate is outside byte range")
    horizontal = "right" if target[0] >= source[0] else "left"
    vertical = "down" if target[1] >= source[1] else "up"
    return [horizontal] * abs(target[0] - source[0]) + [vertical] * abs(
        target[1] - source[1]
    )


def select_target_battle_command(
    recorder: preparation.RuntimeRecorder,
    *,
    initial_command_gst: Path,
    character: str,
) -> tuple[dict[str, object], Path, Path]:
    """Close the generic first-unit menu and open the exact target command."""
    if character not in CASES:
        raise ValueError(f"unknown character: {character}")
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    current_class = int(definition["current_class"])
    commanders = runtime_commanders(initial_command_gst)
    target = commanders[commander_id]
    initial = runtime_command_selection(initial_command_gst)
    initial_coordinate = (initial["cursor_x"], initial["cursor_y"])
    target_coordinate = (target["x"], target["y"])
    navigation = exact_cursor_navigation(initial_coordinate, target_coordinate)

    cursor_capture: Path
    cursor_gst: Path
    if initial["selected_group_index"] != target["runtime_group"]:
        recorder.send(["b"], delay=0.55)
        recorder.send(navigation, delay=0.16, batched=True)
        cursor_capture = recorder.capture("battle/target_cursor.png")
        cursor_gst = recorder.save_gst("states/target_cursor.gst")
        cursor = runtime_selection(cursor_gst)
        if (cursor["cursor_x"], cursor["cursor_y"]) != target_coordinate:
            raise RuntimeError(
                f"target cursor {cursor} did not reach {target_coordinate}"
            )
        recorder.send(["c"], delay=0.8)
    else:
        if navigation:
            raise RuntimeError(
                "selected target command cursor does not match target record"
            )
        cursor_capture = recorder.capture("battle/target_cursor.png")
        cursor_gst = recorder.save_gst("states/target_cursor.gst")

    command_capture = recorder.capture("battle/target_command.png")
    if not blastem.battle_command_menu_visible(command_capture):
        raise RuntimeError("target commander stock command menu is not visible")
    command_gst = recorder.save_gst("states/target_command.gst")
    selected = runtime_command_selection(command_gst)
    selected_record = selected["selected_runtime_record"]
    expected_selection = {
        "selected_group_index": target["runtime_group"],
        "selected_member_index": 0,
        "cursor_x": target["x"],
        "cursor_y": target["y"],
    }
    observed_selection = {field: selected[field] for field in expected_selection}
    if (
        observed_selection != expected_selection
        or selected_record["class_id"] != current_class
        or selected_record["name_id"] != commander_id
    ):
        raise RuntimeError(
            f"target command selected {observed_selection} / "
            f"{selected_record} instead of {expected_selection} / commander "
            f"{commander_id} class 0x{current_class:02X}"
        )
    return (
        {
            "status": "pass",
            "policy": "exact_map_cursor_target_then_stock_command_pointer",
            "initial_selection": initial,
            "target_runtime": target,
            "navigation": navigation,
            "cursor_capture": image_report(cursor_capture),
            "cursor_gst": state_report(cursor_gst),
            "target_selection": selected,
            "target_command_capture": image_report(command_capture),
            "target_command_gst": state_report(command_gst),
            "command_menu_visible": True,
            "portrait_name_evidence": image_report(command_capture),
            "portrait_name_binding_basis": (
                "stock command renderer with exact selected group/member "
                "pointers and target commander/class identity"
            ),
        },
        command_capture,
        command_gst,
    )




def validate_release_rom(
    path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if len(payload) != 0x400000:
        raise ValueError(f"release ROM is not exactly 4 MiB: {path}")
    if actual != expected_sha256:
        raise ValueError(f"release ROM SHA-256 mismatch: {actual} != {expected_sha256}")
    for character, definition in CASES.items():
        matrix_definition = tier_matrix.CASES[character]
        if int(matrix_definition["classes"][3]) != int(definition["current_class"]):
            raise ValueError(f"{character} tier-3 representative changed")
        if tuple(matrix_definition["first_candidates"]) != tuple(
            definition["candidate_classes"]
        ):
            raise ValueError(f"{character} first candidate row changed")
        chain = tier_matrix.read_class_change_chain(
            payload, int(definition["commander_id"])
        )
        if not chain or tuple(chain[0].candidates) != tuple(
            definition["candidate_classes"]
        ):
            raise ValueError(
                f"{character} exact-ROM first candidate row changed: "
                f"{tuple(chain[0].candidates) if chain else None}"
            )
    return {
        **file_report(path),
        "md_checksum": payload[0x18E:0x190].hex().upper(),
    }


def stock_exp_class_scan_report(rom: Path) -> dict[str, object]:
    payload = rom.read_bytes()
    scan = payload[STOCK_EXP_CLASS_SCAN_START:STOCK_EXP_CLASS_SCAN_END]
    scan_sha256 = hashlib.sha256(scan).hexdigest()
    item_gate = payload[
        STOCK_RUNESTONE_ITEM_GATE : STOCK_RUNESTONE_ITEM_GATE
        + len(STOCK_RUNESTONE_ITEM_GATE_BYTES)
    ]
    consume = payload[
        STOCK_RUNESTONE_CONSUME_ROUTINE : STOCK_RUNESTONE_CONSUME_ROUTINE
        + len(STOCK_RUNESTONE_CONSUME_PREFIX)
    ]
    level_up_gate = payload[
        STOCK_LEVEL_UP_GATE : STOCK_LEVEL_UP_GATE + len(STOCK_LEVEL_UP_GATE_BYTES)
    ]
    if scan_sha256 != STOCK_EXP_CLASS_SCAN_SHA256:
        raise ValueError(f"stock EXP/class scan changed: {scan_sha256}")
    if item_gate != STOCK_RUNESTONE_ITEM_GATE_BYTES:
        raise ValueError(f"stock Rune Stone item gate changed: {item_gate.hex()}")
    if consume != STOCK_RUNESTONE_CONSUME_PREFIX:
        raise ValueError(f"stock Rune Stone consume routine changed: {consume.hex()}")
    if level_up_gate != STOCK_LEVEL_UP_GATE_BYTES:
        raise ValueError(
            f"stock EXP compare/subtract/increment gate changed: {level_up_gate.hex()}"
        )
    return {
        "status": "pass",
        "scan_range": (
            f"0x{STOCK_EXP_CLASS_SCAN_START:06X}..0x{STOCK_EXP_CLASS_SCAN_END:06X}"
        ),
        "scan_sha256": scan_sha256,
        "level_10_branch": "0x014B00",
        "exp_compare_subtract_level_increment_gate": (f"0x{STOCK_LEVEL_UP_GATE:06X}"),
        "exp_compare_subtract_level_increment_bytes": (level_up_gate.hex().upper()),
        "full_gauge_flow": (
            "compare EXP against class gauge, subtract gauge, increment "
            "level, then fall through to 0x014B00 in the same invocation"
        ),
        "runestone_item_gate": f"0x{STOCK_RUNESTONE_ITEM_GATE:06X}",
        "runestone_item_gate_bytes": item_gate.hex().upper(),
        "runestone_consume_routine": (f"0x{STOCK_RUNESTONE_CONSUME_ROUTINE:06X}"),
        "runestone_consume_prefix": consume.hex().upper(),
        "invocation": "ordinary_combat_result_exp_pipeline",
    }




def validate_seed_gst(
    path: Path,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError(f"seed GST SHA-256 mismatch: {actual} != {expected_sha256}")
    scenario = preparation.manual_slot_scenario_from_gst(path)
    if scenario != SCENARIO_NUMBER:
        raise ValueError(
            f"old-save source must serialize Scenario {SCENARIO_NUMBER}, "
            f"found {scenario}: {path}"
        )
    return {**file_report(path), "serialized_scenario": scenario}


def build_old_save_fixture(
    seed_gst: Path,
    rom: Path,
    output: Path,
    *,
    character: str,
) -> dict[str, object]:
    """Build one external v1.3.6-compatible SRAM without touching the ROM."""
    if character not in CASES:
        raise ValueError(f"unknown character: {character}")
    if preparation.manual_slot_scenario_from_gst(seed_gst) != SCENARIO_NUMBER:
        raise ValueError(f"fixture seed must serialize Scenario {SCENARIO_NUMBER}")
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    current_class = int(definition["current_class"])
    gauge = class_probe.class_change_experience(rom.read_bytes(), current_class)
    if not 1 <= gauge <= 0xFF:
        raise ValueError(
            f"class 0x{current_class:02X} gauge {gauge} does not fit save EXP"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    blastem.recover_manual_slot_from_gst(seed_gst, output)
    before = saved_commander(output, commander_id)
    combat_stats_before = saved_commander_combat_stats(output, commander_id)
    blastem.patch_manual_slot_commander_progress(
        output,
        commander_id,
        9,
        gauge - 1,
        new_class=current_class,
        new_at=LIVE_COMBAT_BOOST_AT,
        new_df=LIVE_COMBAT_BOOST_DF,
    )
    # Scenario 12 ends immediately if the unescorted Elwin fixture is defeated.
    # The staged hostile reaches Lester/Keith only after several earlier enemy
    # groups have acted, so retain the ordinary turn flow but make the scenario
    # objective durable in the checksum-valid save itself.  This is not a
    # runtime/GST mutation and is reported explicitly in the evidence below.
    objective_guard = saved_commander(output, ELWIN_COMMANDER_ID)
    objective_guard_stats_before = saved_commander_combat_stats(
        output, ELWIN_COMMANDER_ID
    )
    blastem.patch_manual_slot_commander_progress(
        output,
        ELWIN_COMMANDER_ID,
        objective_guard["level"],
        objective_guard["experience"],
        expected_class=objective_guard["class_id"],
        new_df=LIVE_OBJECTIVE_GUARD_DF,
    )
    blastem.patch_manual_slot_items(output, [RUNESTONE_ITEM_ID])
    clear_saved_commander_equipment(output)

    payload = bytearray(output.read_bytes())
    for row in CASES.values():
        payload[marker_offset(int(row["commander_id"]))] = LEGACY_MARKER
    output.write_bytes(payload)

    after = saved_commander(output, commander_id)
    combat_stats_after = saved_commander_combat_stats(output, commander_id)
    objective_guard_stats_after = saved_commander_combat_stats(
        output, ELWIN_COMMANDER_ID
    )
    markers = marker_report(output, LEGACY_MARKER)
    inventory = inventory_report(inventory_records_from_sram(output))
    if blastem.manual_slot_scenario_number(output) != SCENARIO_NUMBER:
        raise ValueError("fixture manual-slot scenario changed")
    if after != {
        "commander_id": commander_id,
        "class_id": current_class,
        "level": 9,
        "experience": gauge - 1,
    }:
        raise ValueError(f"fixture target row differs: {after}")
    if markers["status"] != "pass":
        raise ValueError(f"fixture legacy markers differ: {markers}")
    if inventory["runestone_count"] != 1:
        raise ValueError(f"fixture Rune Stone inventory differs: {inventory}")
    if combat_stats_after != {
        "commander_id": commander_id,
        "at": LIVE_COMBAT_BOOST_AT,
        "df": LIVE_COMBAT_BOOST_DF,
    }:
        raise ValueError(
            f"fixture target combat stats differ: {combat_stats_after}"
        )
    if objective_guard_stats_after != {
        "commander_id": ELWIN_COMMANDER_ID,
        "at": objective_guard_stats_before["at"],
        "df": LIVE_OBJECTIVE_GUARD_DF,
    }:
        raise ValueError(
            "fixture objective guard combat stats differ: "
            f"{objective_guard_stats_after}"
        )
    return {
        "status": "pass",
        "policy": "external_checksum_valid_old_save_no_rom_patch",
        **file_report(output),
        "serialized_scenario": SCENARIO_NUMBER,
        "character": character,
        "commander_before": before,
        "commander_after": after,
        "bounded_live_combat_stats": {
            "status": "pass",
            "storage": "checksum_valid_manual_slot_commander_fields",
            "before": combat_stats_before,
            "after": combat_stats_after,
            "purpose": (
                "ensure the stock live battle awards EXP without modifying "
                "the release ROM or runtime occupancy"
            ),
        },
        "scenario_objective_guard": {
            "status": "pass",
            "storage": "checksum_valid_manual_slot_commander_fields",
            "commander_id": ELWIN_COMMANDER_ID,
            "before": objective_guard_stats_before,
            "after": objective_guard_stats_after,
            "purpose": (
                "keep Scenario 12 active until the staged enemy reaches the "
                "target through the ordinary enemy turn"
            ),
        },
        "level_up_boundary": {
            "level": 9,
            "experience": gauge - 1,
            "effect": (
                "one ordinary combat EXP award reaches the tier-3 LV10 "
                "class-change boundary"
            ),
        },
        "inventory": inventory,
        "commander_equipment_fixture": {
            "status": "pass",
            "policy": "all_saved_commanders_unequipped_before_real_ui_selection",
            "equipped_item": 0,
        },
        "legacy_markers": markers,
    }


def image_report(path: Path) -> dict[str, object]:
    return file_report(path)


def image_crop_sha256(
    path: Path,
    box: tuple[int, int, int, int],
) -> str:
    with Image.open(path) as source:
        crop = source.convert("RGB").crop(box)
        return hashlib.sha256(crop.tobytes()).hexdigest()


def state_report(path: Path) -> dict[str, object]:
    return file_report(path)


def launch_fixture_to_preparation(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    fixture: Path,
    runtime_name: str,
    output: Path,
    max_confirmations: int,
) -> dict[str, object]:
    """Use the normal title LOAD path, not the scenario-select cheat."""
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "load-screen",
            "--rom",
            str(rom),
            "--runtime-name",
            runtime_name,
            "--runtime-root",
            str(recorder.runtime_home.parent),
            "--manual-slot-srm",
            str(fixture),
            "--initial-delay",
            "6.0",
            "--virtual-display",
            recorder.display,
            "--replace-existing",
            "--send-event",
        ]
    )
    load_screen = recorder.capture("load/slot_screen.png")
    # The stock LOAD screen opens on the autosave row.  The external fixture
    # is manual slot 1, so select that visible row through ordinary controller
    # input before advancing its scenario briefing.  Repeated C presses while
    # the cursor remains on an empty autosave row never load the fixture.
    recorder.send(["down"], delay=0.8)
    manual_slot = recorder.capture("load/manual_slot_1_selected.png")
    recorder.send(["c"], delay=1.6)
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "detect-prep",
            "--rom",
            str(rom),
            "--no-launch",
            "--confirmation-delay",
            "0.8",
            "--max-confirmations",
            str(max_confirmations),
            "--capture-prefix",
            str(output / "load/detect.png"),
            "--virtual-display",
            recorder.display,
            "--send-event",
        ]
    )
    prep_capture = recorder.capture("preparation/loaded.png")
    gst = recorder.save_gst("states/loaded_preparation.gst")
    identity = preparation.verify_runtime_scenario_identity(
        gst,
        rom,
        SCENARIO_NUMBER,
    )
    return {
        "status": "pass",
        "method": "ordinary_title_load_slot_then_confirm_to_preparation",
        "scenario_identity": identity,
        "load_screen": image_report(load_screen),
        "manual_slot_1_selected": image_report(manual_slot),
        "preparation": image_report(prep_capture),
        "gst": state_report(gst),
    }


def return_to_preparation_action_list(
    recorder: preparation.RuntimeRecorder,
) -> Path:
    for attempt in range(1, 9):
        recorder.send(["b"], delay=1.0)
        capture = recorder.capture(f"equipment/return_attempt_{attempt}.png")
        if preparation.preparation_action_row(capture) is not None:
            return capture
    raise RuntimeError("equipment UI did not return to the action list")


def equip_runestone_through_ui(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    character: str,
) -> dict[str, object]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    commander_ids = preparation.player_commander_ids(rom.read_bytes(), SCENARIO_NUMBER)
    if commander_id not in commander_ids:
        raise ValueError(
            f"Scenario {SCENARIO_NUMBER} does not deploy commander "
            f"{commander_id}: {commander_ids}"
        )
    target_position = commander_ids.index(commander_id) + 1
    commander_navigation: list[str] = []
    for position in range(1, target_position):
        commander_navigation.extend(
            preparation.allied_next_navigation(
                position,
                len(commander_ids),
            )
        )

    before_gst = recorder.save_gst("states/before_equipment.gst")
    before_runtime = runtime_commanders(before_gst)
    target_before = before_runtime[commander_id]
    expected_before = (
        int(definition["current_class"]),
        9,
        class_probe.class_change_experience(
            rom.read_bytes(), int(definition["current_class"])
        )
        - 1,
        0,
    )
    actual_before = (
        target_before["class_id"],
        target_before["level"],
        target_before["experience"],
        target_before["equipped_item"],
    )
    if actual_before != expected_before:
        raise RuntimeError(f"loaded target state {actual_before} != {expected_before}")
    inventory_before_records = inventory_records_from_gst(before_gst)
    inventory_before = inventory_report(inventory_before_records)
    if inventory_before["runestone_count"] != 1:
        raise RuntimeError(
            f"loaded fixture has no single Rune Stone: {inventory_before}"
        )

    # Rows: hire, equipment, shop, arrangement.  Enter equipment, move the
    # real commander cursor, open its item category, and confirm until the GST
    # proves item 0x1A was equipped.  No RAM or GST byte is edited here.
    preparation.ensure_action_row(recorder, "legacy_5a_equipment", 1)
    recorder.send(["c"], delay=1.3)
    if commander_navigation:
        recorder.send(commander_navigation, delay=0.55)
    commander_capture = recorder.capture("equipment/target_commander.png")
    recorder.send(["c"], delay=1.3)
    category_capture = recorder.capture("equipment/category.png")

    cycles = []
    equipped_gst: Path | None = None
    equipped_capture: Path | None = None
    for cycle in range(1, 7):
        recorder.send(["c"], delay=1.3)
        capture = recorder.capture(f"equipment/cycle_{cycle:02d}.png")
        gst = recorder.save_gst(f"states/equipment_cycle_{cycle:02d}.gst")
        state = runtime_commanders(gst)[commander_id]
        cycles.append(
            {
                "cycle": cycle,
                "capture": image_report(capture),
                "gst": state_report(gst),
                "target_runtime": state,
            }
        )
        if state["equipped_item"] == RUNESTONE_ITEM_ID:
            equipped_gst = gst
            equipped_capture = capture
            break
    if equipped_gst is None or equipped_capture is None:
        raise RuntimeError("Rune Stone was not equipped through the UI")
    equipped_runtime = runtime_commanders(equipped_gst)
    equipped_inventory_records = inventory_records_from_gst(equipped_gst)
    equipped_inventory = inventory_report(equipped_inventory_records)
    transfer = runestone_equipment_transfer_report(
        inventory_before_records,
        equipped_inventory_records,
        target_before,
        equipped_runtime[commander_id],
    )
    # Equipped items live in the commander's 0x0B field while their C7F2
    # inventory record remains present with owner FF -> commander ID.  The
    # real UI transfer must prove both changes.  After use the item record and
    # equipped field both disappear; that is distinct from merely equipping or
    # unequipping the item.
    if transfer["status"] != "pass":
        raise RuntimeError(
            f"Rune Stone UI inventory/equipment transfer failed: {transfer}"
        )
    returned = return_to_preparation_action_list(recorder)
    return {
        "status": "pass",
        "method": "preparation_equipment_menu_real_controller_input",
        "commander_order": commander_ids,
        "target_position": target_position,
        "commander_navigation": commander_navigation,
        "before": {
            "gst": state_report(before_gst),
            "target_runtime": target_before,
            "tracked_commanders": before_runtime,
            "inventory": inventory_before,
        },
        "target_commander_capture": image_report(commander_capture),
        "category_capture": image_report(category_capture),
        "cycles": cycles,
        "equipped": {
            "capture": image_report(equipped_capture),
            "gst": state_report(equipped_gst),
            "target_runtime": equipped_runtime[commander_id],
            "tracked_commanders": equipped_runtime,
            "inventory": equipped_inventory,
            "inventory_transfer": transfer,
        },
        "returned_action_list": image_report(returned),
    }


def battle_result_overlay_visible(path: Path) -> bool:
    """Recognize stock result text or the persistent class-ready banner."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        return False
    ratios = []
    for box in (BATTLE_RESULT_PANEL, BATTLE_CLASS_READY_BANNER):
        panel = frame.crop(box)
        ratios.append(
            sum(
                pixel == STOCK_DARK_BLUE
                for pixel in flattened_image_data(panel)
            )
            / (panel.width * panel.height)
        )
    # Full level/skill result panels fill the lower crop.  The much shallower
    # `class change available` banner contributes 14.2% exact stock blue to
    # the larger center crop; a bare Scenario 12 map contributes 0%.
    return ratios[0] >= 0.45 or ratios[1] >= 0.10


def advance_to_candidate_surface(
    recorder: preparation.RuntimeRecorder,
    *,
    max_advances: int,
    character: str | None = None,
    enemy_group: int | None = None,
    enemy_member: int | None = None,
) -> Path:
    """Advance battle/result UI without re-selecting a map unit blindly.

    C is valid while the side-view battle or a result page owns input.  Once
    the bare tactical map returns, C would instead select the unit under the
    cursor.  The stock level-up result can appear more than half a second after
    that first bare-map frame, so poll without input before reading a GST.  A
    dark-blue result overlay is advanced with C; a bare map never receives C.
    """
    if (enemy_group is None) != (enemy_member is None):
        raise ValueError("enemy group/member must be supplied together")
    commander_id = (
        int(CASES[character]["commander_id"])
        if character is not None
        else None
    )
    for step in range(max_advances + 1):
        capture = recorder.capture(f"class_change/advance_{step:03d}.png")
        if application.class_change_candidate_surface_visible(capture):
            return capture
        if blastem.game_over_visible(capture):
            raise RuntimeError("GAME OVER appeared before class choice")
        if blastem.title_screen_visible(capture):
            raise RuntimeError("title screen appeared before class choice")
        if blastem.battle_map_surface_visible(capture):
            if battle_result_overlay_visible(capture):
                if step == max_advances:
                    break
                recorder.send(["c"], delay=0.8)
                continue
            bare_map_settled = True
            for poll in range(POST_COMBAT_SETTLE_POLLS):
                time.sleep(POST_COMBAT_SETTLE_DELAY)
                stable = recorder.capture(
                    "class_change/post_combat_settle_"
                    f"{step:03d}_{poll:02d}.png"
                )
                if application.class_change_candidate_surface_visible(stable):
                    return stable
                if blastem.game_over_visible(stable):
                    raise RuntimeError("GAME OVER appeared before class choice")
                if blastem.title_screen_visible(stable):
                    raise RuntimeError("title screen appeared before class choice")
                if battle_result_overlay_visible(stable):
                    if step == max_advances:
                        bare_map_settled = False
                        break
                    recorder.send(["c"], delay=0.8)
                    bare_map_settled = False
                    break
                if not blastem.battle_map_surface_visible(stable):
                    # A delayed non-map transition took ownership without an
                    # input.  Classify it in the next outer iteration.
                    bare_map_settled = False
                    break
            if not bare_map_settled:
                continue
            if commander_id is None:
                raise RuntimeError(
                    "tactical map returned before class choice; character "
                    "runtime identity was not supplied"
                )
            gst = recorder.save_gst(
                f"states/class_change/post_combat_{step:03d}.gst"
            )
            target = runtime_commanders(gst)[commander_id]
            enemy = (
                runtime_member(gst, int(enemy_group), int(enemy_member))
                if enemy_group is not None and enemy_member is not None
                else None
            )
            diagnostic = {
                "target": target,
                "enemy": enemy,
                "bare_map_settle_polls": POST_COMBAT_SETTLE_POLLS,
                "step": step,
            }
            if target["level"] < 10:
                raise CombatRetryRequired(
                    "ordinary combat returned to the tactical map before "
                    f"the LV10 boundary; retry with fresh RNG: {diagnostic}"
                )
            raise RuntimeError(
                "ordinary combat reached the LV10 tactical state but the "
                f"class-choice surface was absent: {diagnostic}"
            )
        if step == max_advances:
            break
        recorder.send(["c"], delay=0.8)
    raise RuntimeError(
        f"class-choice surface absent after {max_advances} confirmations"
    )






def command_cursor_row(path: Path) -> int:
    """Return the zero-based highlighted row in the stock left command box."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        raise ValueError(f"command capture dimensions changed: {frame.size}")
    scores = []
    for row in range(7):
        center = 48 + row * 16
        score = sum(
            1
            for y in range(center - 6, center + 7)
            for x in range(35, 45)
            if all(channel >= 180 for channel in frame.getpixel((x, y)))
        )
        scores.append(score)
    best = max(range(len(scores)), key=scores.__getitem__)
    if scores[best] < 12:
        raise ValueError(f"stock command cursor is not visible: scores={scores}")
    return best


def class_candidate_cursor_row(path: Path) -> int:
    """Return the one-based highlighted row in the three-class choice."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        raise ValueError(f"candidate capture dimensions changed: {frame.size}")
    boxes = ((31, 103, 51, 127), (31, 127, 51, 151), (31, 151, 51, 176))
    scores = [
        sum(
            red > 180 and green > 180 and blue > 180
            for red, green, blue in frame.crop(box).get_flattened_data()
        )
        for box in boxes
    ]
    ordered = sorted(scores, reverse=True)
    if ordered[0] - ordered[1] < 8:
        raise ValueError(f"candidate cursor row is ambiguous: {scores}, {path}")
    return scores.index(ordered[0]) + 1


def stock_unit_command_menu_visible(path: Path) -> bool:
    """Recognize full player and compact all-factions unit command panels."""
    if blastem.battle_command_menu_visible(path):
        return True
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        return False
    menu = frame.crop((15, 25, 95, 110))
    interior = frame.crop((10, 28, 65, 105))
    status = frame.crop((0, 195, 320, 235))

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
    status_pixels = status.width * status.height
    ratios = {
        "menu_blue": sum(
            1 for pixel in menu.get_flattened_data() if broad_blue(pixel)
        )
        / menu_pixels,
        "menu_dark": sum(
            1 for pixel in menu.get_flattened_data() if dark_blue(pixel)
        )
        / menu_pixels,
        "interior_dark": sum(
            1 for pixel in interior.get_flattened_data() if dark_blue(pixel)
        )
        / interior_pixels,
        "interior_white": sum(
            1
            for red, green, blue in interior.get_flattened_data()
            if red > 170 and green > 170 and blue > 170
        )
        / interior_pixels,
        "status_blue": sum(
            1 for pixel in status.get_flattened_data() if broad_blue(pixel)
        )
        / status_pixels,
        "status_gold": sum(
            1
            for red, green, blue in status.get_flattened_data()
            if red > 100 and green > 70 and blue < 80 and red > blue * 1.5
        )
        / status_pixels,
    }
    try:
        command_cursor_row(path)
    except ValueError:
        return False
    return (
        0.30 < ratios["menu_blue"] < 0.85
        and ratios["menu_dark"] > 0.30
        and ratios["interior_dark"] > 0.25
        and ratios["interior_white"] > 0.035
        and 0.40 < ratios["status_blue"] < 0.505
        and ratios["status_gold"] > 0.08
    )


def live_cursor_navigation(
    recorder: preparation.RuntimeRecorder,
    *,
    source: tuple[int, int],
    target: tuple[int, int],
    phase: str,
    delay: float = 0.18,
) -> tuple[dict[str, object], Path]:
    keys = exact_cursor_navigation(source, target)
    recorder.send(keys, delay=delay, batched=True)
    capture = recorder.capture(f"live/{phase}/cursor.png")
    gst = recorder.save_gst(f"states/live/{phase}/cursor.gst")
    selection = runtime_selection(gst)
    observed = (selection["cursor_x"], selection["cursor_y"])
    if observed != target:
        raise RuntimeError(
            f"{phase} cursor {observed} != requested live cell {target}"
        )
    return (
        {
            "status": "pass",
            "source": list(source),
            "target": list(target),
            "keys": keys,
            "capture": image_report(capture),
            "gst": state_report(gst),
            "selection": selection,
        },
        gst,
    )


def open_live_unit_command(
    recorder: preparation.RuntimeRecorder,
    *,
    expected_group: int,
    expected_member: int,
    expected_class: int,
    expected_coordinate: tuple[int, int],
    phase: str,
) -> tuple[dict[str, object], Path]:
    recorder.send(["c"], delay=0.8)
    capture = recorder.capture(f"live/{phase}/command.png")
    if not stock_unit_command_menu_visible(capture):
        raise RuntimeError(f"{phase}: stock unit command menu is absent")
    gst = recorder.save_gst(f"states/live/{phase}/command.gst")
    selected = runtime_command_selection(gst)
    record = selected["selected_runtime_record"]
    observed = (
        selected["selected_group_index"],
        selected["selected_member_index"],
        record["class_id"],
        record["x"],
        record["y"],
    )
    expected = (
        expected_group,
        expected_member,
        expected_class,
        expected_coordinate[0],
        expected_coordinate[1],
    )
    if observed != expected:
        raise RuntimeError(f"{phase}: selected live unit {observed} != {expected}")
    return (
        {
            "status": "pass",
            "capture": image_report(capture),
            "gst": state_report(gst),
            "selection": selected,
            "command_cursor_row": command_cursor_row(capture),
        },
        gst,
    )


def live_move_and_standby(
    recorder: preparation.RuntimeRecorder,
    *,
    group: int,
    member: int,
    class_id: int,
    origin: tuple[int, int],
    destination: tuple[int, int],
    phase: str,
    allow_destination_fallback: bool = False,
) -> dict[str, object]:
    command, command_gst = open_live_unit_command(
        recorder,
        expected_group=group,
        expected_member=member,
        expected_class=class_id,
        expected_coordinate=origin,
        phase=phase,
    )
    before_member = runtime_member(command_gst, group, member)
    if command["command_cursor_row"] != 0:
        raise RuntimeError(f"{phase}: stock command did not begin on Move")
    recorder.send(["c"], delay=0.8)
    overlay = recorder.capture(f"live/{phase}/move_overlay.png")
    overlay_gst = recorder.save_gst(f"states/live/{phase}/move_overlay.gst")
    reach = movement.reach_coordinate_report(
        movement.plane_delta(command_gst, overlay_gst),
        origin,
        movement=0xFF,
        overlay_capture=overlay,
        overlay_gst=overlay_gst,
    )
    occupied = {
        (row["x"], row["y"])
        for group_index in range(SCENARIO_12_RUNTIME_GROUP_COUNT)
        for member_index in range(8)
        if (
            (row := runtime_member(command_gst, group_index, member_index))[
                "class_id"
            ]
            != 0xFF
            and row["hp"] > 0
            and row["x"] != 0xFF
            and (group_index, member_index) != (group, member)
        )
    }
    candidates = [destination]
    if destination != origin and live_occupants(command_gst, destination):
        if not allow_destination_fallback:
            raise RuntimeError(
                f"{phase}: requested Move destination is occupied: "
                f"{live_occupants(command_gst, destination)}"
            )
        candidates = []
    if allow_destination_fallback:
        candidates.extend(
            sorted(
                {
                    (int(x), int(y))
                    for x, y in reach["coordinates"]
                    if (int(x), int(y)) != origin
                    and (int(x), int(y)) not in occupied
                    and (int(x), int(y)) != destination
                },
                key=lambda coordinate: (
                    -coordinate[1],
                    abs(coordinate[0] - destination[0]),
                    abs(coordinate[0] - origin[0])
                    + abs(coordinate[1] - origin[1]),
                    coordinate,
                ),
            )
        )
    attempts = []
    cursor = origin
    navigation = None
    destination_gst = None
    accepted_destination = None
    for attempt, candidate in enumerate(candidates, 1):
        navigation, destination_gst = live_cursor_navigation(
            recorder,
            source=cursor,
            target=candidate,
            phase=f"{phase}/destination_attempt_{attempt:02d}",
            delay=0.22,
        )
        cursor = candidate
        target_capture = Path(str(navigation["capture"]["path"]))
        if not target_capture.is_absolute():
            target_capture = ROOT / target_capture
        try:
            cell = movement.selection_frame_cell_top_left(target_capture)
            valid = True
        except ValueError:
            cell = None
            valid = False
        attempts.append(
            {
                "candidate": list(candidate),
                "stock_valid_orange_cursor": valid,
                "screen_cell_top_left": list(cell) if cell is not None else None,
                "navigation": navigation,
            }
        )
        if valid:
            accepted_destination = candidate
            break
    if accepted_destination is None or navigation is None or destination_gst is None:
        raise RuntimeError(
            f"{phase}: no stock-valid Move destination: "
            + json.dumps(attempts, ensure_ascii=False)
        )
    destination = accepted_destination
    recorder.send(["c"], delay=0.9)
    post_move = recorder.capture(f"live/{phase}/post_move_menu.png")
    post_move_gst = recorder.save_gst(f"states/live/{phase}/post_move_menu.gst")
    moved = runtime_member(post_move_gst, group, member)
    if (
        moved["class_id"] != class_id
        or (moved["x"], moved["y"]) != destination
        or any(
            moved[field] != before_member[field]
            for field in ("name_id", "side_id", "hp")
        )
    ):
        raise RuntimeError(f"{phase}: stock Move did not commit: {moved}")
    destination_occupants = live_occupants(post_move_gst, destination)
    origin_occupants = live_occupants(post_move_gst, origin)
    if destination_occupants != [moved] or moved in origin_occupants:
        raise RuntimeError(
            f"{phase}: post-Move occupancy differs: destination="
            f"{destination_occupants}, origin={origin_occupants}"
        )
    standby_row = (
        command_cursor_row(post_move)
        if stock_unit_command_menu_visible(post_move)
        else None
    )
    recorder.send(["c"], delay=1.0)
    standby = recorder.capture(f"live/{phase}/after_standby.png")
    standby_gst = recorder.save_gst(f"states/live/{phase}/after_standby.gst")
    acted = runtime_member(standby_gst, group, member)
    if (
        acted["class_id"] != class_id
        or (acted["x"], acted["y"]) != destination
        or acted["defeated_flag"] != 1
    ):
        raise RuntimeError(f"{phase}: stock Standby did not commit: {acted}")
    return {
        "status": "pass",
        "method": "stock_move_overlay_destination_then_standby",
        "group": group,
        "member": member,
        "class_id": f"0x{class_id:02X}",
        "origin": list(origin),
        "requested_destination": list(candidates[0]),
        "destination": list(destination),
        "command": command,
        "command_gst": state_report(command_gst),
        "move_overlay": image_report(overlay),
        "move_overlay_gst": state_report(overlay_gst),
        "reach_coordinate_report": reach,
        "destination_attempts": attempts,
        "destination_navigation": navigation,
        "destination_gst": state_report(destination_gst),
        "post_move_menu": image_report(post_move),
        "post_move_gst": state_report(post_move_gst),
        "post_move_cursor_row": standby_row,
        "after_standby": image_report(standby),
        "after_standby_gst": state_report(standby_gst),
        "observed_member": acted,
        "before_member": before_member,
        "post_move_destination_occupants": destination_occupants,
        "post_move_origin_occupants": origin_occupants,
    }


def live_move_and_attack_to_candidate(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    character: str,
    target_origin: tuple[int, int],
    target_destination: tuple[int, int] | None,
    enemy_group: int,
    enemy_member: int,
    enemy_coordinate: tuple[int, int],
    max_advances: int,
) -> tuple[dict[str, object], Path]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    target_group = int(runtime_commanders(
        recorder.output / "states/target_command.gst"
    )[commander_id]["runtime_group"])
    command, command_gst = open_live_unit_command(
        recorder,
        expected_group=target_group,
        expected_member=0,
        expected_class=int(definition["current_class"]),
        expected_coordinate=target_origin,
        phase="target_attack",
    )
    target_before_move = runtime_member(command_gst, target_group, 0)
    if command["command_cursor_row"] != 0:
        raise RuntimeError("target live command did not begin on Move")
    recorder.send(["c"], delay=0.8)
    overlay = recorder.capture("live/target_attack/move_overlay.png")
    overlay_gst = recorder.save_gst(
        "states/live/target_attack/move_overlay.gst"
    )
    reach = movement.reach_coordinate_report(
        movement.plane_delta(command_gst, overlay_gst),
        target_origin,
        movement=0xFF,
        overlay_capture=overlay,
        overlay_gst=overlay_gst,
    )
    occupied = {
        (row["x"], row["y"])
        for group_index in range(SCENARIO_12_RUNTIME_GROUP_COUNT)
        for member_index in range(7)
        if (
            (row := runtime_member(command_gst, group_index, member_index))[
                "class_id"
            ]
            != 0xFF
            and row["hp"] > 0
            and row["x"] != 0xFF
            and (group_index, member_index) != (target_group, 0)
        )
    }
    enemy_x, enemy_y = enemy_coordinate
    adjacent = [
        (enemy_x, enemy_y + 1),
        (enemy_x - 1, enemy_y),
        (enemy_x + 1, enemy_y),
        (enemy_x, enemy_y - 1),
    ]
    candidates: list[tuple[int, int]] = []
    if target_destination is not None and target_destination in adjacent:
        candidates.append(target_destination)
    candidates.extend(
        coordinate
        for coordinate in sorted(
            adjacent,
            key=lambda coordinate: (
                abs(coordinate[0] - target_origin[0])
                + abs(coordinate[1] - target_origin[1]),
                coordinate,
            ),
        )
        if coordinate not in candidates
        and coordinate != target_origin
        and coordinate not in occupied
        and coordinate in {
            (int(x), int(y)) for x, y in reach["coordinates"]
        }
    )
    if not candidates:
        raise RuntimeError(
            "target has no unoccupied stock reach cell adjacent to enemy "
            f"{enemy_coordinate}"
        )
    destination_attempts = []
    cursor = target_origin
    navigation = None
    accepted_destination = None
    destination_gst = None
    for attempt, candidate in enumerate(candidates, 1):
        navigation, destination_gst = live_cursor_navigation(
            recorder,
            source=cursor,
            target=candidate,
            phase=f"target_attack/destination_attempt_{attempt:02d}",
            delay=0.22,
        )
        cursor = candidate
        target_capture = Path(str(navigation["capture"]["path"]))
        if not target_capture.is_absolute():
            target_capture = ROOT / target_capture
        try:
            cell = movement.selection_frame_cell_top_left(target_capture)
            valid = True
        except ValueError:
            cell = None
            valid = False
        destination_attempts.append(
            {
                "candidate": list(candidate),
                "stock_valid_orange_cursor": valid,
                "screen_cell_top_left": list(cell) if cell is not None else None,
                "navigation": navigation,
            }
        )
        if valid:
            accepted_destination = candidate
            break
    if (
        accepted_destination is None
        or navigation is None
        or destination_gst is None
    ):
        raise RuntimeError(
            "target has no stock-valid adjacent Move destination: "
            + json.dumps(destination_attempts, ensure_ascii=False)
        )
    target_destination = accepted_destination
    if target_destination == target_origin:
        raise RuntimeError("target Attack route did not issue a distinct Move")
    recorder.send(["c"], delay=0.9)
    move_preview = recorder.capture("live/target_attack/move_preview.png")
    move_preview_gst = recorder.save_gst(
        "states/live/target_attack/move_preview.gst"
    )
    moved = runtime_member(move_preview_gst, target_group, 0)
    if (
        (moved["x"], moved["y"]) != target_destination
        or any(
            moved[field] != target_before_move[field]
            for field in ("class_id", "name_id", "side_id", "hp")
        )
    ):
        raise RuntimeError(f"target stock Move did not commit: {moved}")
    target_destination_occupants = live_occupants(
        move_preview_gst, target_destination
    )
    target_origin_occupants = live_occupants(move_preview_gst, target_origin)
    if target_destination_occupants != [moved] or moved in target_origin_occupants:
        raise RuntimeError(
            "target post-Move occupancy differs: destination="
            f"{target_destination_occupants}, origin={target_origin_occupants}"
        )
    # The stock Mega Drive flow is `Move -> position -> confirm move ->
    # Attack select` when a hostile unit is in range.  The destination C above
    # already committed the movement and opened the orange/red-X attack
    # cursor retained in ``move_preview``.  There is no second left-side
    # command panel and no additional move-confirm C: pressing C again on the
    # commander exits attack selection toward Standby.  Navigate directly
    # from this first post-Move attack cursor to the adjacent hostile unit.
    post_move = move_preview
    post_move_gst = move_preview_gst
    move_confirmation_count = 1
    post_move_attempts = [
        {
            "phase": "stock_attack_target_selection",
            "capture": image_report(post_move),
            "gst": state_report(post_move_gst),
            "command_menu_visible": stock_unit_command_menu_visible(post_move),
        }
    ]
    confirmed_target = runtime_member(post_move_gst, target_group, 0)
    if any(
        confirmed_target[field] != moved[field]
        for field in ("class_id", "name_id", "side_id", "hp", "x", "y")
    ) or confirmed_target["defeated_flag"] != 0:
        raise RuntimeError(
            "target changed or became acted before stock attack selection: "
            f"{confirmed_target}"
        )
    post_move_selection = runtime_selection(post_move_gst)
    observed_cursor = (
        post_move_selection["cursor_x"],
        post_move_selection["cursor_y"],
    )
    if observed_cursor != enemy_coordinate:
        navigation_to_enemy, attack_gst = live_cursor_navigation(
            recorder,
            source=observed_cursor,
            target=enemy_coordinate,
            phase="target_attack/enemy",
            delay=0.3,
        )
        attack_cursor = Path(str(navigation_to_enemy["capture"]["path"]))
        if not attack_cursor.is_absolute():
            attack_cursor = ROOT / attack_cursor
        attack_selection = runtime_selection(attack_gst)
    else:
        navigation_to_enemy = None
        attack_cursor = post_move
        attack_gst = post_move_gst
        attack_selection = post_move_selection
    enemy_before = runtime_member(attack_gst, enemy_group, enemy_member)
    if (
        (enemy_before["x"], enemy_before["y"]) != enemy_coordinate
        or enemy_before["side_id"] != 4
        or enemy_before["hp"] <= 0
    ):
        raise RuntimeError(f"stock attack cursor has no exact live enemy: {enemy_before}")
    recorder.send(["c"], delay=0.35)
    ordinary_combat = recorder.capture("live/target_attack/ordinary_combat.png")
    first_candidate = advance_to_candidate_surface(
        recorder,
        max_advances=max_advances,
        character=character,
        enemy_group=enemy_group,
        enemy_member=enemy_member,
    )
    candidate_gst = recorder.save_gst("states/class_choice_visible.gst")
    candidate_target = runtime_commanders(candidate_gst)[commander_id]
    candidate_inventory_records = inventory_records_from_gst(candidate_gst)
    expected_empty_inventory = [
        (0xFF, 0xFF)
    ] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
    enemy_after = runtime_member(candidate_gst, enemy_group, enemy_member)
    if (
        enemy_after["hp"] >= enemy_before["hp"]
        or any(
            enemy_after[field] != enemy_before[field]
            for field in ("group_index", "member_index", "class_id", "name_id", "side_id")
        )
        or (enemy_after["x"], enemy_after["y"]) != enemy_coordinate
        or (enemy_after["hp"] == 0) != bool(enemy_after["defeated_flag"] & 0x80)
    ):
        raise RuntimeError(
            "ordinary target attack did not preserve/damage the exact live enemy: "
            f"before={enemy_before}, after={enemy_after}"
        )
    expected_gauge = class_probe.class_change_experience(
        rom.read_bytes(),
        int(definition["current_class"]),
    )
    if (
        candidate_target["class_id"] != int(definition["current_class"])
        or candidate_target["level"] != 10
        or candidate_target["equipped_item"] != 0
        or candidate_inventory_records != expected_empty_inventory
    ):
        raise RuntimeError(
            "live stock combat did not reach the consumed-Rune-Stone tier-3 "
            f"LV10 choice: {candidate_target}, inventory="
            f"{candidate_inventory_records}, gauge={expected_gauge}"
        )
    return (
        {
            "status": "pass",
            "trigger": "same_process_stock_move_then_adjacent_attack",
            "gst_relaunch_count": 0,
            "external_runtime_state_loaded": False,
            "exact_release_rom_patched": False,
            "target_command": command,
            "target_command_gst": state_report(command_gst),
            "move_overlay": image_report(overlay),
            "move_overlay_gst": state_report(overlay_gst),
            "reach_coordinate_report": reach,
            "requested_destination": (
                list(candidates[0]) if candidates else None
            ),
            "destination": list(target_destination),
            "destination_attempts": destination_attempts,
            "destination_navigation": navigation,
            "destination_gst": state_report(destination_gst),
            "move_preview": image_report(move_preview),
            "move_preview_gst": state_report(move_preview_gst),
            "move_confirmation_count": move_confirmation_count,
            "post_move_attempts": post_move_attempts,
            "target_before_move": target_before_move,
            "target_destination_occupants": target_destination_occupants,
            "target_origin_occupants": target_origin_occupants,
            "post_move_menu": image_report(post_move),
            "post_move_gst": state_report(post_move_gst),
            "post_move_cursor_row": None,
            "post_move_selection": post_move_selection,
            "confirmed_target_before_attack": confirmed_target,
            "navigation_to_enemy": navigation_to_enemy,
            "attack_cursor": image_report(attack_cursor),
            "attack_gst": state_report(attack_gst),
            "attack_selection": attack_selection,
            "enemy_before": enemy_before,
            "enemy_after": enemy_after,
            "ordinary_combat": image_report(ordinary_combat),
            "candidate_gst": state_report(candidate_gst),
            "candidate_target": candidate_target,
            "candidate_inventory": inventory_report(candidate_inventory_records),
            "runestone_consumed_before_candidate_selection": True,
        },
        first_candidate,
    )


def advance_live_enemy_phase(
    recorder: preparation.RuntimeRecorder,
    *,
    character: str,
    max_advances: int,
) -> tuple[str, dict[str, object], Path]:
    """End the stock turn and retain either a class choice or Turn 2 command."""
    turn_end = movement.first_turn.select_turn_end(
        env=recorder.environment,
        display=recorder.display,
        opening_checks=max_advances,
        delay=0.7,
    )
    observations = []
    commander_id = int(CASES[character]["commander_id"])
    for step in range(max_advances + 1):
        capture = recorder.capture(f"live/enemy_phase/frame_{step:03d}.png")
        observations.append(image_report(capture))
        if application.class_change_candidate_surface_visible(capture):
            gst = recorder.save_gst("states/live/enemy_phase/class_choice.gst")
            target = runtime_commanders(gst)[commander_id]
            if (
                target["level"] != 10
                or target["equipped_item"] != RUNESTONE_ITEM_ID
            ):
                raise RuntimeError(
                    "enemy-phase combat reached a false class-choice surface: "
                    f"{target}"
                )
            return (
                "candidate",
                {
                    "status": "pass",
                    "turn_end": turn_end,
                    "endpoint": "class_change_candidate",
                    "confirmations": step,
                    "observations": observations,
                    "gst": state_report(gst),
                    "target": target,
                },
                capture,
            )
        if blastem.battle_command_menu_visible(capture):
            gst = recorder.save_gst("states/live/enemy_phase/turn2_command.gst")
            return (
                "turn2_command",
                {
                    "status": "observed",
                    "turn_end": turn_end,
                    "endpoint": "turn2_command",
                    "confirmations": step,
                    "observations": observations,
                    "gst": state_report(gst),
                    "tracked_commanders": runtime_commanders(gst),
                    "enemy_group14_root": runtime_member(gst, 14, 0),
                    "enemy_group14_member4": runtime_member(gst, 14, 4),
                },
                capture,
            )
        if blastem.game_over_visible(capture):
            raise RuntimeError("GAME OVER appeared during the live enemy phase")
        if blastem.title_screen_visible(capture):
            raise RuntimeError("title screen appeared during the live enemy phase")
        if step < max_advances:
            recorder.send(["c"], delay=0.7)
    raise RuntimeError(
        f"live enemy phase reached neither class choice nor Turn 2 after "
        f"{max_advances} confirmations"
    )


def live_ordinary_attack_to_candidate_surface(
    recorder: preparation.RuntimeRecorder,
    *,
    source_command_gst: Path,
    rom: Path,
    character: str,
    max_advances: int,
) -> tuple[dict[str, object], Path]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    route = LIVE_COMBAT_ROUTES[character]
    target = runtime_commanders(source_command_gst)[commander_id]
    target_origin = (target["x"], target["y"])
    # Elwin is always runtime group 0 in the exact Scenario 12 opening, while
    # the target group is resolved from the live commander table.  Lock both
    # checksum-save combat safeguards after the title LOAD has materialized
    # them into runtime WRAM.
    objective_guard_runtime = runtime_group_combat_stats(source_command_gst, 0)
    target_boost_runtime = runtime_group_combat_stats(
        source_command_gst, int(target["runtime_group"])
    )
    if objective_guard_runtime["df"] != LIVE_OBJECTIVE_GUARD_DF:
        raise RuntimeError(
            "Scenario objective guard did not materialize in live WRAM: "
            f"{objective_guard_runtime}"
        )
    if (
        target_boost_runtime["at"],
        target_boost_runtime["df"],
    ) != (LIVE_COMBAT_BOOST_AT, LIVE_COMBAT_BOOST_DF):
        raise RuntimeError(
            "target combat safeguard did not materialize in live WRAM: "
            f"{target_boost_runtime}"
        )
    cursor = target_origin
    enemy_destination = tuple(route["enemy"]["destination"])
    pre_moves = []
    cheat: dict[str, object] | None = None

    # The source capture is the target command menu. Normalize to the bare map
    # whenever another unit must be positioned before the target moves.
    needs_setup = bool(route["pre_moves"]) or (
        tuple(route["enemy"]["origin"]) != tuple(route["enemy"]["destination"])
    )
    if needs_setup:
        recorder.send(["b"], delay=0.6)
        for index, row in enumerate(route["pre_moves"], 1):
            navigation, _ = live_cursor_navigation(
                recorder,
                source=cursor,
                target=tuple(row["origin"]),
                phase=f"pre_move_{index}/origin",
            )
            moved = live_move_and_standby(
                recorder,
                group=int(row["group"]),
                member=int(row["member"]),
                class_id=int(row["class_id"]),
                origin=tuple(row["origin"]),
                destination=tuple(row["destination"]),
                phase=f"pre_move_{index}",
            )
            pre_moves.append({"navigation": navigation, "move": moved})
            cursor = tuple(row["destination"])

        to_empty, empty_before_activate_gst = live_cursor_navigation(
            recorder,
            source=cursor,
            target=LIVE_CHEAT_EMPTY_CELL,
            phase="cheat/empty_before_activate",
        )
        empty_before_activate = live_occupants(
            empty_before_activate_gst, LIVE_CHEAT_EMPTY_CELL
        )
        if empty_before_activate:
            raise RuntimeError(
                f"all-factions activation cell is occupied: {empty_before_activate}"
            )
        activated_gst, activated, activation_attempts = (
            movement.activate_all_factions(recorder)
        )
        activated_cursor = runtime_selection(activated_gst)
        cursor = (activated_cursor["cursor_x"], activated_cursor["cursor_y"])
        enemy = route["enemy"]
        to_enemy, _ = live_cursor_navigation(
            recorder,
            source=cursor,
            target=tuple(enemy["origin"]),
            phase="enemy/origin",
        )
        enemy_move = live_move_and_standby(
            recorder,
            group=int(enemy["group"]),
            member=int(enemy["member"]),
            class_id=int(enemy["class_id"]),
            origin=tuple(enemy["origin"]),
            destination=tuple(enemy["destination"]),
            phase="enemy",
            allow_destination_fallback=True,
        )
        enemy_destination = tuple(enemy_move["destination"])
        cursor = enemy_destination
        to_empty_disable, empty_before_deactivate_gst = live_cursor_navigation(
            recorder,
            source=cursor,
            target=LIVE_CHEAT_EMPTY_CELL,
            phase="cheat/empty_before_deactivate",
        )
        empty_before_deactivate = live_occupants(
            empty_before_deactivate_gst, LIVE_CHEAT_EMPTY_CELL
        )
        if empty_before_deactivate:
            raise RuntimeError(
                "all-factions deactivation cell is occupied: "
                f"{empty_before_deactivate}"
            )
        deactivated_gst, deactivated, deactivation_attempts = (
            movement.deactivate_all_factions(recorder)
        )
        deactivated_cursor = runtime_selection(deactivated_gst)
        cursor = (deactivated_cursor["cursor_x"], deactivated_cursor["cursor_y"])
        cheat = {
            "status": "pass",
            "stock_static_source_lock": movement.all_factions_static_report(
                rom.read_bytes()
            ),
            "activation_empty_cell": to_empty,
            "activation_empty_cell_occupants": empty_before_activate,
            "activation": activated,
            "activation_attempts": activation_attempts,
            "enemy_origin_navigation": to_enemy,
            "enemy_move": enemy_move,
            "deactivation_empty_cell": to_empty_disable,
            "deactivation_empty_cell_occupants": empty_before_deactivate,
            "deactivation": deactivated,
            "deactivation_attempts": deactivation_attempts,
            "active_flag_after_setup": deactivated["active_flag"],
        }
        if deactivated["active_flag"] != 0:
            raise RuntimeError(f"all-factions flag remained active: {deactivated}")
        target_navigation, _ = live_cursor_navigation(
            recorder,
            source=cursor,
            target=target_origin,
            phase="target_attack/origin",
        )
    else:
        # The original target command is already open; close/reopen it so the
        # same live command proof is used by every character.
        recorder.send(["b"], delay=0.6)
        target_navigation = {
            "status": "pass",
            "source": list(target_origin),
            "target": list(target_origin),
            "keys": [],
            "policy": "target remained on its original stock cursor cell",
        }

    if character in ("keith", "lester"):
        staged_target = live_move_and_standby(
            recorder,
            group=int(target["runtime_group"]),
            member=0,
            class_id=int(definition["current_class"]),
            origin=target_origin,
            destination=tuple(route["target_destination"]),
            phase="target_stage_turn1",
        )
        endpoint, enemy_phase, first_candidate = advance_live_enemy_phase(
            recorder,
            character=character,
            max_advances=max_advances,
        )
        if endpoint != "turn2_command":
            raise RuntimeError(
                "live Turn 1 setup triggered class choice before the required "
                "player-issued Move and Attack"
            )
        turn2_gst = Path(str(enemy_phase["gst"]["path"]))
        if not turn2_gst.is_absolute():
            turn2_gst = ROOT / turn2_gst
        turn2_selection = runtime_selection(turn2_gst)
        turn2_target = runtime_commanders(turn2_gst)[commander_id]
        staged_turn2_enemy = runtime_member(
            turn2_gst,
            int(route["enemy"]["group"]),
            int(route["enemy"]["member"]),
        )
        if staged_turn2_enemy["hp"] <= 0 or staged_turn2_enemy["side_id"] != 4:
            raise RuntimeError(
                "staged live enemy is unavailable on Turn 2: "
                f"{staged_turn2_enemy}"
            )
        # The staged mercenary proves a real hostile Move was accepted.  During
        # the ordinary enemy phase group 14 reforms southward.  Member 2 then
        # occupies (23, 23), leaving an unoccupied side cell for a distinct
        # player-issued Move followed by Attack on Turn 2.
        attack_enemy_member = 2
        turn2_enemy = runtime_member(
            turn2_gst,
            int(route["enemy"]["group"]),
            attack_enemy_member,
        )
        if turn2_enemy["hp"] <= 0 or turn2_enemy["side_id"] != 4:
            raise RuntimeError(
                f"live enemy root is unavailable on Turn 2: {turn2_enemy}"
            )
        recorder.send(["b"], delay=0.6)
        turn2_target_navigation, _ = live_cursor_navigation(
            recorder,
            source=(turn2_selection["cursor_x"], turn2_selection["cursor_y"]),
            target=(turn2_target["x"], turn2_target["y"]),
            phase="target_attack/turn2_origin",
        )
        player_attack, first_candidate = live_move_and_attack_to_candidate(
            recorder,
            rom=rom,
            character=character,
            target_origin=(turn2_target["x"], turn2_target["y"]),
            target_destination=None,
            enemy_group=int(route["enemy"]["group"]),
            enemy_member=attack_enemy_member,
            enemy_coordinate=(turn2_enemy["x"], turn2_enemy["y"]),
            max_advances=max_advances,
        )
        combat = {
            **player_attack,
            "status": "pass",
            "trigger": "same_process_turn2_stock_move_then_player_attack",
            "gst_relaunch_count": 0,
            "external_runtime_state_loaded": False,
            "exact_release_rom_patched": False,
            "target_turn1_move": staged_target,
            "enemy_phase": enemy_phase,
            "staged_enemy_after_phase": staged_turn2_enemy,
            "player_attack_enemy": turn2_enemy,
            "turn2_target_navigation": turn2_target_navigation,
        }
    else:
        combat, first_candidate = live_move_and_attack_to_candidate(
            recorder,
            rom=rom,
            character=character,
            target_origin=target_origin,
            target_destination=tuple(route["target_destination"]),
            enemy_group=int(route["enemy"]["group"]),
            enemy_member=int(route["enemy"]["member"]),
            enemy_coordinate=enemy_destination,
            max_advances=max_advances,
        )
    return (
        {
            **combat,
            "natural_full_scenario_play": False,
            "same_live_process_from_title_load": True,
            "stock_exp_class_scan_source_lock": stock_exp_class_scan_report(rom),
            "pre_moves": pre_moves,
            "all_factions_setup": cheat,
            "target_origin_navigation": target_navigation,
            "route": route,
            "objective_guard_runtime": objective_guard_runtime,
            "target_combat_safeguard_runtime": target_boost_runtime,
        },
        first_candidate,
    )




def class_candidate_report(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    character: str,
    first_capture: Path,
) -> tuple[dict[str, object], Path]:
    definition = CASES[character]
    chain = tier_matrix.read_class_change_chain(
        rom.read_bytes(), int(definition["commander_id"])
    )
    source_candidates = tuple(chain[0].candidates) if chain else ()
    if source_candidates != tuple(definition["candidate_classes"]):
        raise RuntimeError(
            f"{character} exact-ROM candidate tuple differs: {source_candidates}"
        )
    captures = [first_capture]
    for index in (2, 3):
        recorder.send(["down"], delay=0.7)
        captures.append(recorder.capture(f"class_change/candidate_{index}.png"))
    # Retain a stable name for row 1 as well.
    row_one = recorder.output / "class_change/candidate_1.png"
    shutil.copy2(first_capture, row_one)
    captures[0] = row_one

    fingerprints = [
        tier_matrix.candidate_class_label_fingerprint(path) for path in captures
    ]
    expected_fingerprint = str(definition["label_fingerprint"])
    if fingerprints != [expected_fingerprint] * 3:
        raise RuntimeError(
            f"{character} class-label fingerprints differ: {fingerprints}"
        )
    cursor_rows = [class_candidate_cursor_row(path) for path in captures]
    if cursor_rows != [1, 2, 3]:
        raise RuntimeError(
            f"{character} class-choice cursor rows differ: {cursor_rows}"
        )
    selected_index = int(definition["selected_index"])
    for _ in range(3 - selected_index):
        recorder.send(["up"], delay=0.7)
    selected = recorder.capture("class_change/selected.png")
    selected_cursor_row = class_candidate_cursor_row(selected)
    if selected_cursor_row != selected_index:
        raise RuntimeError(
            f"{character} selected cursor row {selected_cursor_row} "
            f"!= {selected_index}"
        )
    return (
        {
            "status": "pass",
            "candidate_classes": [
                f"0x{int(value):02X}" for value in definition["candidate_classes"]
            ],
            "exact_rom_candidate_classes": [
                f"0x{int(value):02X}" for value in source_candidates
            ],
            "exact_rom_candidate_source_locked": True,
            "candidate_labels": list(definition["candidate_labels"]),
            "expected_label_fingerprint": expected_fingerprint,
            "observed_label_fingerprints": fingerprints,
            "observed_cursor_rows": cursor_rows,
            "row_captures": [image_report(path) for path in captures],
            "selected_index": selected_index,
            "selected_class": f"0x{int(definition['selected_class']):02X}",
            "selected_capture": image_report(selected),
            "selected_cursor_row": selected_cursor_row,
        },
        selected,
    )


def progression_without_join_regrant(
    rom: Path,
    character: str,
    initial_experience: int = 0,
) -> dict[str, int]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    selected_class = int(definition["selected_class"])
    raw = builder.join_raw_experience(commander_id)
    gauge = class_probe.class_change_experience(rom.read_bytes(), selected_class)
    gained, residual = divmod(raw + initial_experience, gauge)
    return {
        "class_id": selected_class,
        "level": 1 + gained,
        "experience": residual,
        "join_raw_experience": raw,
        "initial_experience": initial_experience,
        "class_experience_gauge": gauge,
    }


def settle_applied_state(
    recorder: preparation.RuntimeRecorder,
    *,
    character: str,
    expected_experience: int,
    max_confirmations: int,
) -> dict[str, object]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    expected = (
        int(definition["selected_class"]),
        1,
        expected_experience,
        0,
    )
    expected_empty_inventory = [
        (0xFF, 0xFF)
    ] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
    observations = []
    for step in range(max_confirmations + 1):
        capture = recorder.capture(f"class_change/applied_{step:02d}.png")
        gst = recorder.save_gst(f"states/applied_{step:02d}.gst")
        commanders = runtime_commanders(gst)
        target = commanders[commander_id]
        inventory_records = inventory_records_from_gst(gst)
        inventory = inventory_report(inventory_records)
        actual = (
            target["class_id"],
            target["level"],
            target["experience"],
            target["equipped_item"],
        )
        observations.append(
            {
                "step": step,
                "capture": image_report(capture),
                "gst": state_report(gst),
                "target_runtime": target,
                "inventory": inventory,
            }
        )
        if actual == expected and inventory_records == expected_empty_inventory:
            # The selected class is already committed when this tuple first
            # appears.  A further C does not confirm the class: on the bare
            # tactical map it selects the commander under the cursor and
            # leaves a status/action panel open, which in turn prevents START
            # from opening the game-save menu.  Prove stability passively.
            time.sleep(0.9)
            stable_capture = recorder.capture("class_change/applied_stable.png")
            stable_gst = recorder.save_gst("states/applied_stable.gst")
            stable_commanders = runtime_commanders(stable_gst)
            stable_target = stable_commanders[commander_id]
            stable_inventory_records = inventory_records_from_gst(stable_gst)
            stable_actual = (
                stable_target["class_id"],
                stable_target["level"],
                stable_target["experience"],
                stable_target["equipped_item"],
            )
            if (
                stable_actual != expected
                or stable_inventory_records != expected_empty_inventory
            ):
                raise RuntimeError(
                    "Rune Stone application was not stable after a passive "
                    f"map wait: {stable_actual}, "
                    f"inventory={stable_inventory_records}"
                )
            return {
                "status": "pass",
                "expected": {
                    "class_id": expected[0],
                    "level": expected[1],
                    "experience": expected[2],
                    "equipped_item": expected[3],
                    "runestone_inventory_count": 0,
                },
                "observed": observations[-1],
                "tracked_commanders": stable_commanders,
                "inventory_records": inventory_records,
                "inventory_exactly_empty": True,
                "stable_after_passive_wait": {
                    "status": "pass",
                    "capture": image_report(stable_capture),
                    "gst": state_report(stable_gst),
                    "target_runtime": stable_target,
                    "inventory_records": stable_inventory_records,
                },
                "observations": observations,
            }
        if step == max_confirmations:
            break
        recorder.send(["c"], delay=0.8)
    raise RuntimeError(f"Rune Stone application did not settle to {expected}")


def commander_status_panel_visible(path: Path) -> bool:
    """Recognize the stock commander detail panel over the tactical map."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        return False
    panel = frame.crop(COMMANDER_STATUS_PANEL)
    exact_blue = sum(
        pixel == STOCK_DARK_BLUE for pixel in flattened_image_data(panel)
    ) / (panel.width * panel.height)
    return exact_blue >= 0.50 and blastem.battle_map_surface_visible(path)


def bare_battle_map_visible(path: Path) -> bool:
    """Require the tactical map with no unit/result/START overlay open."""
    return (
        blastem.battle_map_surface_visible(path)
        and not blastem.battle_command_menu_visible(path)
        and not commander_status_panel_visible(path)
        and not battle_result_overlay_visible(path)
        and not movement.first_turn.start_menu_visible(path)
    )


def game_save_confirmation_visible(path: Path) -> bool:
    """Recognize the stock `save? yes/no` prompt opened from START."""
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    if frame.size != (320, 240):
        return False
    panel = frame.crop((40, 30, 200, 145))
    exact_blue = sum(
        pixel == STOCK_DARK_BLUE for pixel in flattened_image_data(panel)
    ) / (panel.width * panel.height)
    return (
        exact_blue >= 0.50
        and blastem.battle_map_surface_visible(path)
        and not movement.first_turn.start_menu_visible(path)
    )


def game_save_confirmation_cursor_row(path: Path) -> int | None:
    """Return 0 for Yes or 1 for No in the stock save confirmation."""
    if not game_save_confirmation_visible(path):
        return None
    with Image.open(path) as opened:
        frame = opened.convert("RGB")
    scores = []
    for box in SAVE_CONFIRMATION_CURSOR_BOXES:
        cursor = frame.crop(box)
        scores.append(
            sum(
                red > 140 and green > 140 and blue > 140
                for red, green, blue in flattened_image_data(cursor)
            )
        )
    selected = max(range(len(scores)), key=scores.__getitem__)
    other = 1 - selected
    if scores[selected] < 20 or scores[selected] - scores[other] < 8:
        return None
    return selected


def save_applied_state_through_game_ui(
    recorder: preparation.RuntimeRecorder,
    *,
    character: str,
    expected_experience: int,
) -> dict[str, object]:
    """Use START > Save > Yes and bind the serialized manual-slot record."""
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    expected = {
        "commander_id": commander_id,
        "class_id": int(definition["selected_class"]),
        "level": 1,
        "experience": expected_experience,
    }
    start_capture: Path | None = None
    start_row: int | None = None
    opening = []
    for attempt in range(1, 13):
        capture = recorder.capture(
            f"persistence/save/open_start_attempt_{attempt:02d}.png"
        )
        row = movement.first_turn.start_menu_cursor_row(capture)
        surface = (
            "start_menu"
            if row is not None
            else "result_overlay"
            if battle_result_overlay_visible(capture)
            else "unit_command"
            if blastem.battle_command_menu_visible(capture)
            else "commander_status"
            if commander_status_panel_visible(capture)
            else "bare_battle_map"
            if bare_battle_map_visible(capture)
            else "other"
        )
        opening.append(
            {
                "attempt": attempt,
                "capture": image_report(capture),
                "cursor_row": row,
                "surface": surface,
            }
        )
        if row is not None:
            start_capture = capture
            start_row = row
            break
        if surface == "result_overlay":
            recorder.send(["c"], delay=0.8)
        elif surface in {"unit_command", "commander_status"}:
            # Observe the result of B on its own.  Pairing B and START without
            # an intervening capture can send START while the panel-close
            # transition is still active, reopening the unit command instead.
            recorder.send(["b"], delay=0.9)
        elif surface == "bare_battle_map":
            recorder.send(["start"], delay=1.0)
        elif blastem.battle_map_surface_visible(capture):
            recorder.send(["b"], delay=0.9)
        else:
            recorder.send(["c"], delay=0.8)
    if start_capture is None or start_row is None:
        raise RuntimeError("START menu did not open after Rune Stone application")

    for _ in range(start_row):
        recorder.send(["up"], delay=0.45)
    save_row = recorder.capture("persistence/save/start_save_row.png")
    if movement.first_turn.start_menu_cursor_row(save_row) != 0:
        raise RuntimeError("START menu did not select the Save row")
    recorder.send(["c"], delay=1.0)
    confirmation_default = recorder.capture(
        "persistence/save/confirmation_default_no.png"
    )
    if not game_save_confirmation_visible(confirmation_default):
        raise RuntimeError("in-game Save confirmation did not appear")
    default_row = game_save_confirmation_cursor_row(confirmation_default)
    if default_row != 1:
        raise RuntimeError(
            "stock Save confirmation did not open on No: "
            f"cursor_row={default_row}"
        )
    recorder.send(["up"], delay=0.8)
    confirmation_yes = recorder.capture(
        "persistence/save/confirmation_yes.png"
    )
    yes_row = game_save_confirmation_cursor_row(confirmation_yes)
    if yes_row != 0:
        raise RuntimeError(
            "in-game Save confirmation did not select Yes: "
            f"cursor_row={yes_row}"
        )
    # Confirm through the real UI and read the resulting SRAM mirror from a
    # new, never-reloaded GST snapshot.
    recorder.send(["c"], delay=2.0)
    completed = recorder.capture("persistence/save/completed.png")
    completed_gst = recorder.save_gst("states/persistence/game_saved.gst")
    saved_record = preparation.manual_slot_record_from_gst(completed_gst)
    saved_target = saved_commander_from_record(saved_record, commander_id)
    saved_inventory = inventory_records_from_record(saved_record)
    expected_empty_inventory = [
        (0xFF, 0xFF)
    ] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
    if saved_target != expected or saved_inventory != expected_empty_inventory:
        raise RuntimeError(
            "in-game Save did not serialize applied class/item state: "
            f"target={saved_target}, inventory={saved_inventory}"
        )
    return {
        "status": "pass",
        "method": "real_start_menu_save_yes_controller_input",
        "opening_attempts": opening,
        "initial_start_cursor_row": start_row,
        "save_row": image_report(save_row),
        "confirmation_default_no": image_report(confirmation_default),
        "confirmation_default_cursor_row": default_row,
        "confirmation_yes": image_report(confirmation_yes),
        "confirmation_yes_cursor_row": yes_row,
        "completed": image_report(completed),
        "saved_gst": state_report(completed_gst),
        "serialized_scenario": int.from_bytes(saved_record[:2], "big"),
        "serialized_target": saved_target,
        "serialized_inventory": inventory_report(saved_inventory),
    }


def relaunch_saved_runtime_to_preparation(
    recorder: preparation.RuntimeRecorder,
    *,
    rom: Path,
    runtime_name: str,
    max_confirmations: int,
) -> dict[str, object]:
    """Cold-launch the same HOME/SRAM and use the ordinary title LOAD UI."""
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "load-screen",
            "--rom",
            str(rom),
            "--runtime-name",
            runtime_name,
            "--runtime-root",
            str(recorder.runtime_home.parent),
            "--reuse-runtime-state",
            "--initial-delay",
            "6.0",
            "--virtual-display",
            recorder.display,
            "--replace-existing",
            "--send-event",
        ]
    )
    slot_screen = recorder.capture("persistence/reload/slot_screen.png")
    recorder.send(["down"], delay=0.8)
    manual_slot = recorder.capture(
        "persistence/reload/manual_slot_1_selected.png"
    )
    recorder.send(["c"], delay=1.6)
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "detect-prep",
            "--rom",
            str(rom),
            "--no-launch",
            "--confirmation-delay",
            "0.8",
            "--max-confirmations",
            str(max_confirmations),
            "--capture-prefix",
            str(recorder.output / "persistence/reload/detect.png"),
            "--virtual-display",
            recorder.display,
            "--send-event",
        ]
    )
    preparation_capture = recorder.capture(
        "persistence/reload/preparation.png"
    )
    gst = recorder.save_gst("states/persistence/reloaded_preparation.gst")
    scenario_identity = preparation.verify_runtime_scenario_identity(
        gst,
        rom,
        SCENARIO_NUMBER,
    )
    return {
        "status": "pass",
        "method": "cold_process_same_home_ordinary_title_load_manual_slot_1",
        "slot_screen": image_report(slot_screen),
        "manual_slot_1_selected": image_report(manual_slot),
        "preparation": image_report(preparation_capture),
        "gst": state_report(gst),
        "scenario_identity": scenario_identity,
    }


def unchanged_non_target_lester_jessica(
    before: dict[int, dict[str, int]],
    after: dict[int, dict[str, int]],
    target_commander_id: int,
) -> dict[str, object]:
    rows = []
    for commander_id in (7, 9, 10):
        if commander_id == target_commander_id:
            continue
        fields = ("class_id", "level", "experience", "equipped_item")
        previous = {field: before[commander_id][field] for field in fields}
        current = {field: after[commander_id][field] for field in fields}
        rows.append(
            {
                "commander_id": commander_id,
                "before": previous,
                "after": current,
                "unchanged": previous == current,
            }
        )
    passed = all(row["unchanged"] for row in rows)
    return {
        "status": "pass" if passed else "fail",
        "checked_fields": [
            "class_id",
            "level",
            "experience",
            "equipped_item",
        ],
        "rows": rows,
    }


def application_acceptance_report(
    *,
    character: str,
    before_commanders: dict[int, dict[str, int]],
    after_commanders: dict[int, dict[str, int]],
    after_inventory: list[tuple[int, int]],
    expected_experience: int = 0,
) -> dict[str, object]:
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    target = after_commanders[commander_id]
    expected = {
        "class_id": int(definition["selected_class"]),
        "level": 1,
        "experience": expected_experience,
        "equipped_item": 0,
    }
    observed = {field: target[field] for field in expected}
    inventory = inventory_report(after_inventory)
    inventory_exactly_empty = after_inventory == [
        (0xFF, 0xFF)
    ] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
    non_target = unchanged_non_target_lester_jessica(
        before_commanders,
        after_commanders,
        commander_id,
    )
    passed = (
        observed == expected
        and inventory_exactly_empty
        and non_target["status"] == "pass"
    )
    return {
        "status": "pass" if passed else "fail",
        "expected_target": expected,
        "observed_target": observed,
        "inventory_after_use": inventory,
        "inventory_records_after_use": after_inventory,
        "inventory_exactly_empty": inventory_exactly_empty,
        "non_target_tracked_commanders": non_target,
        "non_target_lester_jessica": non_target,
    }


def run_attempt(
    args: argparse.Namespace,
    *,
    profile: str,
    character: str,
    display: str,
    attempt: int,
) -> dict[str, object]:
    output = args.output / profile / character / f"attempt-{attempt}"
    output.mkdir(parents=True, exist_ok=False)
    runtime_name = f"legacy5a-{args.run_id}-{profile}-{character}-a{attempt}"
    runtime_home = args.runtime_root / runtime_name
    recorder = preparation.RuntimeRecorder(output, display, runtime_home)
    rom = args.roms[profile]
    seed = args.seeds[profile]
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    fixture = output / "fixture/v136-old-save.sram"
    started = time.monotonic()
    release_before = validate_release_rom(rom, args.expected_rom_sha256[profile])
    evidence_scope = getattr(args, "evidence_scope", "preflight_diagnostic_only")
    final_acceptance_eligible = evidence_scope == "final_acceptance"
    process_checkpoints: list[dict[str, object]] = []
    try:
        fixture_build = build_old_save_fixture(
            seed,
            rom,
            fixture,
            character=character,
        )
        launch = launch_fixture_to_preparation(
            recorder,
            rom=rom,
            fixture=fixture,
            runtime_name=runtime_name,
            output=output,
            max_confirmations=args.max_load_confirmations,
        )
        process_checkpoints = [
            live_process_identity(
                recorder,
                rom=rom,
                phase="after_ordinary_title_load",
            )
        ]

        live_sram = find_runtime_sram(runtime_home)
        imported = output / "fixture/imported-live-before.sram"
        shutil.copy2(live_sram, imported)
        imported_markers = marker_report(imported, LEGACY_MARKER)
        if imported_markers["status"] != "pass":
            raise RuntimeError(
                f"BlastEm did not import all legacy markers: {imported_markers}"
            )

        equipment = equip_runestone_through_ui(
            recorder,
            rom=rom,
            character=character,
        )
        process_checkpoints.append(
            live_process_identity(recorder, rom=rom, phase="after_equipment_ui")
        )
        assert_same_live_process(process_checkpoints[0], process_checkpoints[-1])
        before_commanders = equipment["equipped"]["tracked_commanders"]
        battle.enter_battle_command(recorder, rom, output)
        initial_command_capture = recorder.capture("battle/turn1_initial_command.png")
        initial_command_gst = recorder.save_gst("states/turn1_initial_command.gst")
        command_targeting, command_capture, command_gst = select_target_battle_command(
            recorder,
            initial_command_gst=initial_command_gst,
            character=character,
        )
        command_state = runtime_commanders(command_gst)[commander_id]
        command_expected = (
            int(definition["current_class"]),
            9,
            class_probe.class_change_experience(
                rom.read_bytes(), int(definition["current_class"])
            )
            - 1,
            RUNESTONE_ITEM_ID,
        )
        command_actual = (
            command_state["class_id"],
            command_state["level"],
            command_state["experience"],
            command_state["equipped_item"],
        )
        if command_actual != command_expected:
            raise RuntimeError(
                f"pre-combat target {command_actual} != {command_expected}"
            )

        combat_trigger, first_candidate = live_ordinary_attack_to_candidate_surface(
            recorder,
            source_command_gst=command_gst,
            rom=rom,
            character=character,
            max_advances=args.max_candidate_advances,
        )
        process_checkpoints.append(
            live_process_identity(
                recorder,
                rom=rom,
                phase="class_choice_visible_after_actual_attack",
            )
        )
        assert_same_live_process(process_checkpoints[0], process_checkpoints[-1])
        candidates, _ = class_candidate_report(
            recorder,
            rom=rom,
            character=character,
            first_capture=first_candidate,
        )
        residual_experience = int(
            combat_trigger["candidate_target"]["experience"]
        )
        recorder.send(["c"], delay=1.5)
        applied = settle_applied_state(
            recorder,
            character=character,
            expected_experience=residual_experience,
            max_confirmations=args.max_apply_confirmations,
        )
        process_checkpoints.append(
            live_process_identity(
                recorder,
                rom=rom,
                phase="after_runestone_application",
            )
        )
        assert_same_live_process(process_checkpoints[0], process_checkpoints[-1])

        target_after = applied["tracked_commanders"][commander_id]
        expected_target = (
            int(definition["selected_class"]),
            1,
            residual_experience,
            0,
        )
        actual_target = (
            target_after["class_id"],
            target_after["level"],
            target_after["experience"],
            target_after["equipped_item"],
        )
        if actual_target != expected_target:
            raise RuntimeError(f"applied target {actual_target} != {expected_target}")
        application_acceptance = application_acceptance_report(
            character=character,
            before_commanders=before_commanders,
            after_commanders=applied["tracked_commanders"],
            expected_experience=residual_experience,
            after_inventory=inventory_records_from_gst(
                Path(str(applied["observed"]["gst"]["path"]))
                if Path(str(applied["observed"]["gst"]["path"])).is_absolute()
                else ROOT / str(applied["observed"]["gst"]["path"])
            ),
        )
        if application_acceptance["status"] != "pass":
            raise RuntimeError(
                f"Rune Stone application acceptance failed: {application_acceptance}"
            )
        non_target = application_acceptance["non_target_lester_jessica"]
        erroneous = progression_without_join_regrant(
            rom,
            character,
            residual_experience,
        )
        erroneous_tuple = (
            erroneous["class_id"],
            erroneous["level"],
            erroneous["experience"],
        )
        observed_tuple = actual_target[:3]
        if character in ("lester", "jessica") and (
            observed_tuple == erroneous_tuple or erroneous_tuple == expected_target[:3]
        ):
            raise RuntimeError(
                f"{character} stale marker did not distinguish join regrant: "
                f"observed={observed_tuple} erroneous={erroneous_tuple}"
            )

        persistence_save = save_applied_state_through_game_ui(
            recorder,
            character=character,
            expected_experience=residual_experience,
        )
        process_checkpoints.append(
            live_process_identity(
                recorder,
                rom=rom,
                phase="after_real_game_save",
            )
        )
        assert_same_live_process(process_checkpoints[0], process_checkpoints[-1])

        # Flush the real game save, then cold-launch the same HOME.  This is a
        # deliberate new PID only after the uninterrupted load/equip/combat/
        # class-choice/application/save chain is complete; no GST is loaded.
        first_process = process_checkpoints[-1]
        blastem.terminate_blastem_processes(display=display)
        flushed_after_save = find_runtime_sram(runtime_home)
        flushed_save_snapshot = output / "fixture/flushed-after-game-save.sram"
        shutil.copy2(flushed_after_save, flushed_save_snapshot)
        serialized_target = saved_commander(
            flushed_save_snapshot,
            commander_id,
        )
        expected_serialized_target = {
            "commander_id": commander_id,
            "class_id": expected_target[0],
            "level": expected_target[1],
            "experience": expected_target[2],
        }
        if serialized_target != expected_serialized_target:
            raise RuntimeError(
                "flushed in-game Save target differs: "
                f"{serialized_target} != {expected_serialized_target}"
            )
        persistence_reload = relaunch_saved_runtime_to_preparation(
            recorder,
            rom=rom,
            runtime_name=runtime_name,
            max_confirmations=args.max_load_confirmations,
        )
        reload_process = live_process_identity(
            recorder,
            rom=rom,
            phase="cold_same_home_title_reload",
        )
        if (
            reload_process["pid"] == first_process["pid"]
            or reload_process["proc_start_time_ticks"]
            == first_process["proc_start_time_ticks"]
        ):
            raise RuntimeError("persistence reload did not use a fresh process")
        if (
            reload_process["runtime_home"] != first_process["runtime_home"]
            or reload_process["display"] != first_process["display"]
            or reload_process["rom"] != first_process["rom"]
        ):
            raise RuntimeError(
                "persistence reload changed HOME/display/ROM identity: "
                f"before={first_process}, after={reload_process}"
            )
        reloaded_gst_path = Path(str(persistence_reload["gst"]["path"]))
        if not reloaded_gst_path.is_absolute():
            reloaded_gst_path = ROOT / reloaded_gst_path
        reloaded_target = runtime_commanders(reloaded_gst_path)[commander_id]
        reloaded_actual = (
            reloaded_target["class_id"],
            reloaded_target["level"],
            reloaded_target["experience"],
            reloaded_target["equipped_item"],
        )
        if reloaded_actual != expected_target:
            raise RuntimeError(
                f"cold title LOAD target {reloaded_actual} != {expected_target}"
            )
        reloaded_inventory = inventory_records_from_gst(reloaded_gst_path)
        if any(item == RUNESTONE_ITEM_ID for item, _owner in reloaded_inventory):
            raise RuntimeError("Rune Stone reappeared after cold title LOAD")

        # BlastEm flushes cartridge SRAM on process exit.  Stop only this
        # isolated display, then bind the actual runtime save.sram bytes.
        blastem.terminate_blastem_processes(display=display)
        flushed = find_runtime_sram(runtime_home)
        flushed_snapshot = output / "fixture/flushed-after-use.sram"
        shutil.copy2(flushed, flushed_snapshot)
        flushed_markers = marker_report(flushed_snapshot, CLEARED_MARKER)
        if flushed_markers["status"] != "pass":
            raise RuntimeError(
                f"legacy markers were not cleared after flush: {flushed_markers}"
            )
        release_after = validate_release_rom(rom, args.expected_rom_sha256[profile])
        release_unchanged = release_before["sha256"] == release_after["sha256"]
        if not release_unchanged:
            raise RuntimeError("exact release ROM changed during the run")

        report = {
            "schema_version": 1,
            "status": "pass",
            "evidence_scope": evidence_scope,
            "final_acceptance_eligible": final_acceptance_eligible,
            "run_id": args.run_id,
            "attempt": attempt,
            "profile": profile,
            "character": character,
            "scenario": SCENARIO_NUMBER,
            "tier": int(definition["tier"]),
            "virtual_display": display,
            "exact_release_rom_before": release_before,
            "exact_release_rom_after": release_after,
            "exact_release_rom_unchanged": release_unchanged,
            "seed_gst": validate_seed_gst(seed, args.expected_seed_sha256[profile]),
            "fixture": fixture_build,
            "imported_live_sram": imported_markers,
            "load": launch,
            "same_process_proof": {
                "status": "pass",
                "gst_relaunch_count": 0,
                "external_runtime_state_loaded": False,
                "checkpoints": process_checkpoints,
                "stable_pid_and_start_time": True,
                "all_argv_exclude_savestate_restore_option": all(
                    not row["argv_has_savestate_restore_option"]
                    for row in process_checkpoints
                ),
            },
            "persistence_roundtrip": {
                "status": "pass",
                "game_save": persistence_save,
                "flushed_save_sram": file_report(flushed_save_snapshot),
                "flushed_serialized_target": serialized_target,
                "cold_title_reload": persistence_reload,
                "fresh_reload_process": reload_process,
                "fresh_pid_and_start_time": True,
                "same_home_display_rom": True,
                "reloaded_target": reloaded_target,
                "reloaded_inventory": inventory_report(reloaded_inventory),
            },
            "equipment_ui": equipment,
            "combat_trigger": {
                "initial_command_capture": image_report(initial_command_capture),
                "initial_command_gst": state_report(initial_command_gst),
                "target_command_selection": command_targeting,
                "command_capture": image_report(command_capture),
                "command_gst": state_report(command_gst),
                "command_target_runtime": command_state,
                **combat_trigger,
            },
            "class_choice": candidates,
            "application": applied,
            "application_acceptance": application_acceptance,
            "stale_marker_policy": {
                "status": "pass",
                "legacy_value": LEGACY_MARKER,
                "expected_action": "clear_without_join_experience_grant",
                "observed_target": {
                    "class_id": target_after["class_id"],
                    "level": target_after["level"],
                    "experience": target_after["experience"],
                    "equipped_item": target_after["equipped_item"],
                },
                "erroneous_pending_join_regrant_prediction": erroneous,
                "observed_differs_from_erroneous_prediction": (
                    character == "keith" or observed_tuple != erroneous_tuple
                ),
                "non_target_lester_jessica": non_target,
                "flushed_markers": flushed_markers,
            },
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        failure_capture = None
        failure_gst = None
        try:
            failure_capture = image_report(recorder.capture("failure/final.png"))
        except Exception:
            pass
        try:
            failure_gst = state_report(recorder.save_gst("failure/final.gst"))
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "evidence_scope": evidence_scope,
            "final_acceptance_eligible": False,
            "run_id": args.run_id,
            "attempt": attempt,
            "profile": profile,
            "character": character,
            "scenario": SCENARIO_NUMBER,
            "virtual_display": display,
            "exact_release_rom_before": release_before,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_capture": failure_capture,
            "failure_gst": failure_gst,
            "process_checkpoints": process_checkpoints,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return failure
    finally:
        blastem.terminate_blastem_processes(display=display)


def task_plan(
    args: argparse.Namespace,
    profile: str,
    character: str,
    display: str,
) -> dict[str, object]:
    definition = CASES[character]
    return {
        "profile": profile,
        "character": character,
        "scenario": SCENARIO_NUMBER,
        "tier": int(definition["tier"]),
        "current_class": f"0x{int(definition['current_class']):02X}",
        "selected_class": f"0x{int(definition['selected_class']):02X}",
        "display": display,
        "rom": relative(args.roms[profile]),
        "rom_sha256": args.expected_rom_sha256[profile],
        "seed_gst": relative(args.seeds[profile]),
        "expected_seed_sha256": args.expected_seed_sha256[profile],
        "fixture_policy": "external_sram_with_three_real_0x5a_markers",
        "same_live_process_from_title_load": True,
        "gst_relaunch_count": 0,
        "external_runtime_state_loaded": False,
        "rom_patch": None,
    }


def plan_matrix(args: argparse.Namespace) -> dict[str, object]:
    tasks = [
        task_plan(
            args,
            profile,
            character,
            f":{args.display_base + index % args.workers}",
        )
        for index, (profile, character) in enumerate(
            (profile, character)
            for profile in args.profiles
            for character in args.characters
        )
    ]
    return {
        "schema_version": 1,
        "status": "planned",
        "evidence_scope": getattr(
            args, "evidence_scope", "preflight_diagnostic_only"
        ),
        "final_acceptance_eligible": getattr(
            args, "evidence_scope", "preflight_diagnostic_only"
        )
        == "final_acceptance",
        "run_id": args.run_id,
        "execution": "exact_release_rom_old_sram_one_live_process_real_ui",
        "existing_tier_2_to_5_matrix_modified": False,
        "task_count": len(tasks),
        "tasks": tasks,
    }


def run_matrix(args: argparse.Namespace) -> dict[str, object]:
    evidence_scope = getattr(args, "evidence_scope", "final_acceptance")
    if (
        tuple(args.profiles) != PROFILES
        and evidence_scope != "preflight_diagnostic_only"
    ):
        raise ValueError("release compatibility matrix requires pure, normal, and hard")
    if (
        tuple(getattr(args, "characters", CASES)) != tuple(CASES)
        and evidence_scope != "preflight_diagnostic_only"
    ):
        raise ValueError(
            "release compatibility matrix requires Keith, Lester, and Jessica"
        )
    missing_seed_hashes = [
        profile
        for profile in args.profiles
        if args.expected_seed_sha256[profile] is None
    ]
    if missing_seed_hashes:
        raise ValueError(
            "release compatibility matrix requires exact seed SHA-256 for: "
            + ", ".join(missing_seed_hashes)
        )
    args.output.mkdir(parents=True, exist_ok=False)
    roms_before = {
        profile: validate_release_rom(
            args.roms[profile], args.expected_rom_sha256[profile]
        )
        for profile in args.profiles
    }
    seeds = {
        profile: validate_seed_gst(
            args.seeds[profile], args.expected_seed_sha256[profile]
        )
        for profile in args.profiles
    }
    tasks = [
        (profile, character)
        for profile in args.profiles
        for character in args.characters
    ]
    workers = min(args.workers, len(tasks))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    available: queue.SimpleQueue[str] = queue.SimpleQueue()
    xvfb_processes = []
    rows = []
    started = time.monotonic()
    try:
        for display in displays:
            xvfb_processes.append(
                parallel.start_xvfb(
                    args.xvfb,
                    args.xvfb_library_path,
                    display,
                )
            )
            available.put(display)

        def assigned(profile: str, character: str) -> dict[str, object]:
            display = available.get()
            try:
                attempts = []
                selected: dict[str, object] | None = None
                for attempt in range(1, args.attempts + 1):
                    result = run_attempt(
                        args,
                        profile=profile,
                        character=character,
                        display=display,
                        attempt=attempt,
                    )
                    evidence_path = (
                        args.output
                        / profile
                        / character
                        / f"attempt-{attempt}"
                        / (
                            "evidence.json"
                            if result["status"] == "pass"
                            else "failure.json"
                        )
                    )
                    attempts.append(
                        {
                            "attempt": attempt,
                            "status": result["status"],
                            "evidence": file_report(evidence_path),
                        }
                    )
                    selected = result
                    if result["status"] == "pass":
                        break
                if selected is None:
                    raise AssertionError("attempt loop did not run")
                return {
                    "profile": profile,
                    "character": character,
                    "status": selected["status"],
                    "selected_attempt": int(selected["attempt"]),
                    "selected_evidence": attempts[-1]["evidence"],
                    "attempts": attempts,
                }
            finally:
                blastem.terminate_blastem_processes(display=display)
                available.put(display)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(assigned, profile, character): (
                    profile,
                    character,
                )
                for profile, character in tasks
            }
            for future in as_completed(futures):
                profile, character = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = {
                        "profile": profile,
                        "character": character,
                        "status": "orchestrator_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                rows.append(row)
                print(
                    f"{profile} {character} tier 3 stale-0x5A: {row['status']}",
                    flush=True,
                )
    finally:
        for process in xvfb_processes:
            parallel.stop_process(process)

    rows.sort(
        key=lambda row: (
            PROFILES.index(str(row["profile"])),
            list(CASES).index(str(row["character"])),
        )
    )
    roms_after = {
        profile: validate_release_rom(
            args.roms[profile], args.expected_rom_sha256[profile]
        )
        for profile in args.profiles
    }
    roms_unchanged = all(
        roms_before[profile]["sha256"] == roms_after[profile]["sha256"]
        for profile in args.profiles
    )
    passed = sum(row.get("status") == "pass" for row in rows)
    return {
        "schema_version": 1,
        "status": ("pass" if passed == len(tasks) and roms_unchanged else "fail"),
        "evidence_scope": args.evidence_scope,
        "final_acceptance_eligible": (
            args.evidence_scope == "final_acceptance"
            and passed == len(tasks)
            and roms_unchanged
        ),
        "run_id": args.run_id,
        "execution": "exact_release_rom_old_sram_one_live_process_real_ui",
        "existing_tier_2_to_5_matrix_modified": False,
        "profiles": args.profiles,
        "characters": list(args.characters),
        "tier": 3,
        "scenario": SCENARIO_NUMBER,
        "workers": workers,
        "displays": displays,
        "passed_tasks": passed,
        "total_tasks": len(tasks),
        "release_roms_before": roms_before,
        "release_roms_after": roms_after,
        "release_roms_unchanged": roms_unchanged,
        "seed_gsts": seeds,
        "results": rows,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def valid_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError(
            "SHA-256 must be exactly 64 hexadecimal characters"
        )
    return normalized


def comma_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--pure-rom", type=Path, default=RELEASE_ROM_PATHS["pure"])
    parser.add_argument("--normal-rom", type=Path, default=RELEASE_ROM_PATHS["normal"])
    parser.add_argument("--hard-rom", type=Path, default=RELEASE_ROM_PATHS["hard"])
    parser.add_argument(
        "--expected-pure-sha256",
        type=valid_sha256,
        default=RELEASE_ROM_SHA256["pure"],
    )
    parser.add_argument(
        "--expected-normal-sha256",
        type=valid_sha256,
        default=RELEASE_ROM_SHA256["normal"],
    )
    parser.add_argument(
        "--expected-hard-sha256",
        type=valid_sha256,
        default=RELEASE_ROM_SHA256["hard"],
    )
    for profile in PROFILES:
        parser.add_argument(f"--seed-{profile}", type=Path)
        parser.add_argument(
            f"--expected-seed-{profile}-sha256",
            type=valid_sha256,
        )
    parser.add_argument("--profiles", type=comma_list, default=list(PROFILES))
    parser.add_argument("--characters", type=comma_list, default=list(CASES))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--display-base", type=int, default=960)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--max-load-confirmations", type=int, default=100)
    parser.add_argument("--max-candidate-advances", type=int, default=160)
    parser.add_argument("--max-apply-confirmations", type=int, default=24)
    parser.add_argument(
        "--evidence-scope",
        choices=("preflight_diagnostic_only", "final_acceptance"),
        default="preflight_diagnostic_only",
        help=(
            "classify generated evidence; final acceptance must be selected "
            "explicitly only after the verifier source and tests are frozen"
        ),
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=preparation.validate_run_id, required=True)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    args = parser.parse_args(argv)
    args.roms = {
        "pure": args.pure_rom.resolve(),
        "normal": args.normal_rom.resolve(),
        "hard": args.hard_rom.resolve(),
    }
    args.expected_rom_sha256 = {
        "pure": args.expected_pure_sha256,
        "normal": args.expected_normal_sha256,
        "hard": args.expected_hard_sha256,
    }
    args.seeds = {profile: getattr(args, f"seed_{profile}") for profile in PROFILES}
    args.expected_seed_sha256 = {
        profile: getattr(args, f"expected_seed_{profile}_sha256")
        for profile in PROFILES
    }
    if (
        not args.profiles
        or len(set(args.profiles)) != len(args.profiles)
        or any(profile not in PROFILES for profile in args.profiles)
    ):
        parser.error("--profiles must be a unique subset of pure,normal,hard")
    if (
        not args.characters
        or len(set(args.characters)) != len(args.characters)
        or any(character not in CASES for character in args.characters)
    ):
        parser.error("--characters must be a unique subset of keith,lester,jessica")
    if args.evidence_scope == "final_acceptance" and tuple(args.profiles) != PROFILES:
        parser.error(
            "--profiles must be exactly pure,normal,hard for release acceptance"
        )
    if (
        args.evidence_scope == "final_acceptance"
        and tuple(args.characters) != tuple(CASES)
    ):
        parser.error(
            "--characters must be exactly keith,lester,jessica for release acceptance"
        )
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if not (
        parallel.MIN_ISOLATED_DISPLAY_NUMBER <= args.display_base <= 999 - args.workers
    ):
        parser.error("--display-base must reserve high-numbered isolated displays")
    for profile in args.profiles:
        if not args.roms[profile].is_file():
            parser.error(f"{profile} ROM does not exist: {args.roms[profile]}")
        if args.seeds[profile] is None:
            parser.error(f"--seed-{profile} is required for selected profile")
        args.seeds[profile] = args.seeds[profile].resolve()
        if not args.seeds[profile].is_file():
            parser.error(f"{profile} seed GST does not exist: {args.seeds[profile]}")
        if args.command == "run" and args.expected_seed_sha256[profile] is None:
            parser.error(f"--expected-seed-{profile}-sha256 is required for run")
    args.output_root = args.output_root.resolve()
    args.output = args.output_root / args.run_id
    args.runtime_root = args.runtime_root.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    if args.command == "run":
        if not args.xvfb.is_file():
            parser.error(f"Xvfb executable does not exist: {args.xvfb}")
        if not args.xvfb_library_path.is_dir():
            parser.error(
                f"Xvfb library directory does not exist: {args.xvfb_library_path}"
            )
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        report = plan_matrix(args)
    else:
        report = run_matrix(args)
        (args.output / "summary.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in ("planned", "pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
