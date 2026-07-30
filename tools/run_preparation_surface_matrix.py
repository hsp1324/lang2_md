#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Iterable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.class_hire_data import MERCENARY_CLASS_BASE, MERCENARY_CLASS_COUNT
from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS
from tools.run_blastem_sequence import (
    GST_WORK_RAM_FILE_OFFSET,
    MANUAL_SLOT_COMMANDER_CLASS_OFFSET,
    MANUAL_SLOT_COMMANDER_COUNT,
    MANUAL_SLOT_COMMANDER_LEVEL_OFFSET,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_COMMANDER_ROSTER_OFFSET,
    MANUAL_SLOT_WORK_RAM_SEGMENTS,
    preparation_screen_visible,
    terminate_blastem_processes,
)
from tools.scenario_data import (
    DEFAULT_REFERENCE_ROM,
    be16,
    read_scenario,
    scenario_layout,
)


SCENARIO_MIN = 1
SCENARIO_MAX = 27
PLAYER_COMMANDER_COUNT_OFFSET = 0x10
MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET = 0x0A
COMMANDER_ROSTER_PAGE_SIZE = 5
HIRE_PAGE_SIZE = 3
DEFAULT_DISPLAY = ":104"
DEFAULT_SEED_GST = (
    ROOT
    / "captures/analysis/"
    "hard_mode_current_candidate_first_turn_s27_endpoint.gst"
)
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/runtime"
PROFILE_ROMS = {
    "normal": (
        ROOT / "tmp/Langrisser II (Korean prep-pattern-pool-yal probe).md"
    ),
    "hard": (
        ROOT / "tmp/Langrisser II (Korean Hard prep-pattern-pool-yal probe).md"
    ),
}
RUNTIME_CHECKPOINT_CHARS = ("얄",)
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md_checksum(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 0x190:
        raise ValueError(f"ROM is too short: {path}")
    return f"{int.from_bytes(data[0x18E:0x190], 'big'):04X}"


def player_commander_count(data: bytes, scenario_number: int) -> int:
    layout = scenario_layout(data, scenario_number)
    count = be16(data, layout.header_offset + PLAYER_COMMANDER_COUNT_OFFSET)
    if not 1 <= count <= MANUAL_SLOT_COMMANDER_COUNT:
        raise ValueError(
            f"Scenario {scenario_number} has invalid player commander count {count}"
        )
    return count


def manual_slot_record_from_gst(gst_path: Path) -> bytes:
    gst = gst_path.read_bytes()
    parts: list[bytes] = []
    for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = GST_WORK_RAM_FILE_OFFSET + address
        end = start + size
        if len(gst) < end:
            raise ValueError(
                f"GST is too short for manual-slot RAM segment 0x{address:04X}"
            )
        parts.append(gst[start:end])
    return b"".join(parts)


def hire_rows(mask: int) -> list[dict[str, object]]:
    if not 0 <= mask <= 0xFFFF:
        raise ValueError("hire mask must fit one word")
    rows = []
    for bit in range(MERCENARY_CLASS_COUNT):
        if not mask & (1 << bit):
            continue
        class_id = MERCENARY_CLASS_BASE + bit
        rows.append(
            {
                "bit": bit,
                "class_id": class_id,
                "class_id_hex": f"0x{class_id:02X}",
                "korean": KOREAN_CLASS_LABELS[class_id],
            }
        )
    return rows


def manual_slot_roster(gst_path: Path) -> list[dict[str, object]]:
    record = manual_slot_record_from_gst(gst_path)
    rows = []
    for index in range(MANUAL_SLOT_COMMANDER_COUNT):
        offset = (
            MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + index * MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        class_id = record[offset + MANUAL_SLOT_COMMANDER_CLASS_OFFSET]
        level = record[offset + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET]
        mask_offset = offset + MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET
        mask = int.from_bytes(record[mask_offset : mask_offset + 2], "big")
        offered = hire_rows(mask)
        rows.append(
            {
                "commander_id": index + 1,
                "class_id": class_id,
                "class_id_hex": f"0x{class_id:02X}",
                "class_korean": KOREAN_CLASS_LABELS[class_id],
                "level": level,
                "hire_mask": f"0x{mask:04X}",
                "hire_rows": offered,
                "hire_page_count": max(1, math.ceil(len(offered) / HIRE_PAGE_SIZE)),
            }
        )
    return rows


def visible_fixed_records(model: dict[str, object]) -> list[dict[str, object]]:
    return [
        row
        for row in model["records"]
        if not row["hidden"] and row["x"] != 0xFF and row["y"] != 0xFF
    ]


def fixed_record_not_applicable(model: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for record in model["records"]:
        reasons = []
        if record["hidden"]:
            reasons.append("source record is hidden at preparation time")
        if record["x"] == 0xFF or record["y"] == 0xFF:
            reasons.append("source coordinates are (255,255)")
        if reasons:
            rows.append(
                {
                    "index": record["index"],
                    "name_korean": record["name"]["ko"],
                    "class_korean": record["class"]["ko"],
                    "reason": "; ".join(reasons),
                }
            )
    return rows


def manhattan(left: dict[str, object], right: dict[str, object]) -> int:
    return abs(int(left["x"]) - int(right["x"])) + abs(
        int(left["y"]) - int(right["y"])
    )


def greedy_fixed_record_route(
    records: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    remaining = list(records)
    if not remaining:
        return []
    route = [remaining.pop(0)]
    while remaining:
        current = route[-1]
        next_record = min(
            remaining,
            key=lambda row: (manhattan(current, row), int(row["index"])),
        )
        remaining.remove(next_record)
        route.append(next_record)
    return route


def directional_keys(
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[str]:
    start_x, start_y = start
    end_x, end_y = end
    keys: list[str] = []
    if end_x < start_x:
        keys.extend(["left"] * (start_x - end_x))
    else:
        keys.extend(["right"] * (end_x - start_x))
    if end_y < start_y:
        keys.extend(["up"] * (start_y - end_y))
    else:
        keys.extend(["down"] * (end_y - start_y))
    return keys


def record_slug(record: dict[str, object]) -> str:
    return f"record_{int(record['index']):02d}"


def build_plan(
    rom_path: Path,
    reference_rom_path: Path,
    seed_gst: Path,
    scenario_number: int,
) -> dict[str, object]:
    data = rom_path.read_bytes()
    reference = reference_rom_path.read_bytes()
    commander_count = player_commander_count(data, scenario_number)
    seed_roster = manual_slot_roster(seed_gst)
    model = read_scenario(data, reference, scenario_number)
    visible = visible_fixed_records(model)
    # The in-game 적군보기 surface advances preparation-visible fixed records
    # with one held Right in source-record order, skipping hidden entries.
    route = visible
    return {
        "schema_version": 1,
        "scenario": scenario_number,
        "rom": {
            "path": str(rom_path.relative_to(ROOT)),
            "md_checksum": md_checksum(rom_path),
            "sha256": sha256_path(rom_path),
        },
        "seed_gst": {
            "path": str(seed_gst.relative_to(ROOT)),
            "sha256": sha256_path(seed_gst),
            "policy": (
                "preserve the seed's actual class and offered-hire masks; "
                "do not OR diagnostic FFFF masks into acceptance runs"
            ),
        },
        "allied_commanders": {
            "count": commander_count,
            "roster_page_count": math.ceil(
                commander_count / COMMANDER_ROSTER_PAGE_SIZE
            ),
            "seed_records": seed_roster[:commander_count],
        },
        "fixed_records": {
            "count": model["record_count"],
            "visible_count": len(visible),
            "route": [
                {
                    "index": row["index"],
                    "name_korean": row["name"]["ko"],
                    "class_korean": row["class"]["ko"],
                    "mercenary_classes_korean": sorted(
                        {
                            KOREAN_CLASS_LABELS[class_id]
                            for class_id in row["mercenaries"]
                            if class_id != 0xFF
                        }
                    ),
                    "runtime_checkpoint_chars": [
                        char
                        for char in RUNTIME_CHECKPOINT_CHARS
                        if char
                        in (
                            row["name"]["ko"]
                            + row["class"]["ko"]
                            + "".join(
                                KOREAN_CLASS_LABELS[class_id]
                                for class_id in row["mercenaries"]
                                if class_id != 0xFF
                            )
                        )
                    ],
                    "side_id": f"0x{int(row['side_id']):02X}",
                    "x": row["x"],
                    "y": row["y"],
                }
                for row in route
            ],
            "not_applicable": fixed_record_not_applicable(model),
            "route_assumption": (
                "The arrangement detail cursor begins on the first visible "
                "source record; after explicitly closing its popup, one held "
                "Right advances to the next visible source record."
            ),
            "navigation": "right_cycle_source_record_order",
        },
        "required_runtime_checks": [
            "every allied commander root/status panel before and after shop",
            "every offered hire row before and after shop",
            "every arrangement roster page before and after shop",
            "every preparation-visible fixed commander detail before and after shop",
            "real shop item-list round trip in the same emulator process",
            "full-screen byte comparison plus human sprite/minimap/text review",
        ],
        "acceptance_policy": (
            "This plan and its runtime captures never change "
            "localization/preparation_surface_acceptance.json automatically."
        ),
    }


def fixed_detail_visible(path: Path) -> bool:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    panel = frame.crop(
        (
            round(8 * scale_x),
            round(30 * scale_y),
            round(190 * scale_x),
            round(125 * scale_y),
        )
    )
    map_side = frame.crop(
        (
            round(192 * scale_x),
            round(30 * scale_y),
            round(315 * scale_x),
            round(200 * scale_y),
        )
    )
    right_border = frame.crop(
        (
            round(185 * scale_x),
            round(28 * scale_y),
            round(193 * scale_x),
            round(130 * scale_y),
        )
    )
    pixels = list(panel.get_flattened_data())
    map_pixels = list(map_side.get_flattened_data())
    border_pixels = list(right_border.get_flattened_data())
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    white = sum(
        1
        for red, green, blue in pixels
        if red > 155 and green > 155 and blue > 155
    )
    map_blue = sum(
        1
        for red, green, blue in map_pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    border_gold = sum(
        1
        for red, green, blue in border_pixels
        if red > 100
        and green > 70
        and blue < 80
        and red > blue * 1.5
    )
    # Detail panels use the upper-left blue box over the arrangement map.
    # Equipment/status panels can look similar inside the box, but their
    # entire right side remains blue instead of exposing the map.
    return (
        white / len(pixels) > 0.025
        and map_blue / len(map_pixels) < 0.10
        and border_gold / len(border_pixels) > 0.10
    )


def crop_ratios(
    path: Path,
    box: tuple[int, int, int, int],
) -> tuple[float, float, float]:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    left, top, right, bottom = box
    crop = frame.crop(
        (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
    )
    pixels = list(crop.get_flattened_data())
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    white = sum(
        1
        for red, green, blue in pixels
        if red > 155 and green > 155 and blue > 155
    )
    gold = sum(
        1
        for red, green, blue in pixels
        if red > 100
        and green > 70
        and blue < 80
        and red > blue * 1.5
    )
    size = len(pixels)
    return dark_blue / size, white / size, gold / size


def hire_screen_visible(path: Path) -> bool:
    if not preparation_screen_visible(path):
        return False
    _, white, _ = crop_ratios(path, (145, 115, 318, 214))
    # The active hire list contains white class/stat rows and END. The main
    # command list is dim gray, while equipment/status has only sparse white
    # labels in this same lower-right panel.
    return white > 0.025


def arrangement_menu_visible(path: Path) -> bool:
    map_blue, _, _ = crop_ratios(path, (192, 30, 315, 200))
    panel_blue, panel_white, _ = crop_ratios(path, (8, 30, 142, 140))
    return (
        map_blue < 0.10
        and 0.55 < panel_blue < 0.70
        and panel_white > 0.10
        and not fixed_detail_visible(path)
    )


def arrangement_roster_visible(path: Path) -> bool:
    map_blue, _, _ = crop_ratios(path, (192, 30, 315, 200))
    panel_blue, panel_white, _ = crop_ratios(path, (8, 30, 142, 140))
    return (
        map_blue < 0.10
        and 0.75 < panel_blue < 0.90
        and 0.015 < panel_white < 0.060
        and not fixed_detail_visible(path)
    )


def status_dhash(path: Path) -> tuple[bool, ...]:
    with Image.open(path) as source:
        status = source.convert("L").crop((145, 32, 315, 115))
    resized = status.resize((17, 16), Image.Resampling.BILINEAR)
    pixels = list(resized.get_flattened_data())
    return tuple(
        pixels[y * 17 + x] > pixels[y * 17 + x + 1]
        for y in range(16)
        for x in range(16)
    )


def hash_distance(left: tuple[bool, ...], right: tuple[bool, ...]) -> int:
    if len(left) != len(right):
        raise ValueError("perceptual hashes must have the same length")
    return sum(a != b for a, b in zip(left, right))


def bright_ratio(
    path: Path,
    box: tuple[int, int, int, int],
) -> float:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    left, top, right, bottom = box
    crop = frame.crop(
        (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
    )
    pixels = list(crop.get_flattened_data())
    return sum(
        1
        for red, green, blue in pixels
        if red > 180 and green > 180 and blue > 180
    ) / len(pixels)


def preparation_focus_side(path: Path) -> str | None:
    left = bright_ratio(path, (12, 35, 28, 130))
    right = bright_ratio(path, (145, 112, 162, 214))
    if right > 0.025:
        return "right"
    if left > 0.018 and right < 0.015:
        return "left"
    return None


def preparation_action_row(path: Path) -> int | None:
    if preparation_focus_side(path) != "right":
        return None
    ratios = [
        bright_ratio(path, (148, top, 160, top + 18))
        for top in (118, 143, 168, 193)
    ]
    row = max(range(len(ratios)), key=ratios.__getitem__)
    return row if ratios[row] > 0.025 else None


class RuntimeRecorder:
    def __init__(
        self,
        output: Path,
        display: str,
        runtime_home: Path,
    ) -> None:
        self.output = output
        self.display = display
        self.runtime_home = runtime_home
        self.captures: list[dict[str, object]] = []
        self.actions: list[dict[str, object]] = []
        self.environment = os.environ.copy()
        self.environment["DISPLAY"] = display
        self.environment.pop("WAYLAND_DISPLAY", None)
        self.environment["SDL_VIDEODRIVER"] = "x11"

    def run_command(self, command: list[str]) -> None:
        subprocess.check_call(command, cwd=ROOT, env=self.environment)

    def send(
        self,
        keys: Iterable[str],
        *,
        delay: float = 0.75,
        batched: bool = False,
    ) -> None:
        key_list = list(keys)
        if not key_list:
            return
        specs = [
            key if ":" in key or "@" in key else f"{key}:{delay}"
            for key in key_list
        ]
        commands = [specs] if batched else [[spec] for spec in specs]
        for command_specs in commands:
            self.run_command(
                [
                    sys.executable,
                    str(SEND_KEYS),
                    "--send-event",
                    "--hold",
                    "0.08",
                    *command_specs,
                ]
            )
        self.actions.append(
            {
                "keys": key_list,
                "delay_seconds": delay,
                "batched": batched,
            }
        )

    def capture(self, relative: str) -> Path:
        path = self.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run_command(
            [
                sys.executable,
                str(CAPTURE_WINDOW),
                str(path),
                "--xlib-only",
            ]
        )
        with Image.open(path) as image:
            dimensions = [image.width, image.height]
        self.captures.append(
            {
                "path": relative,
                "sha256": sha256_path(path),
                "bytes": path.stat().st_size,
                "dimensions": dimensions,
            }
        )
        return path

    def save_gst(self, relative: str) -> Path:
        self.send(["save:1.0"])
        candidates = sorted(
            self.runtime_home.rglob("quicksave.gst"),
            key=lambda path: path.stat().st_mtime_ns,
        )
        if not candidates:
            raise RuntimeError("BlastEm did not create quicksave.gst")
        destination = self.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[-1], destination)
        return destination


def ensure_action_row(
    recorder: RuntimeRecorder,
    phase: str,
    target_row: int,
) -> None:
    if not 0 <= target_row <= 3:
        raise ValueError("preparation action row must be 0..3")

    row: int | None = None
    # Hire END returns to the left commander column. B transfers from that
    # column to the right action list; unlike an unconditional direction tap,
    # inspecting the cursor first cannot move an already focused action row.
    for attempt in range(1, 9):
        probe = recorder.capture(
            f"transitions/{phase}/action_focus_attempt_{attempt}.png"
        )
        row = preparation_action_row(probe)
        if row is not None:
            break
        if preparation_focus_side(probe) == "left":
            recorder.send(["b"], delay=1.1)
        else:
            time.sleep(0.35)
    if row is None:
        raise RuntimeError(f"{phase}: could not focus preparation action list")

    moves = 0
    while row != target_row and moves < 8:
        recorder.send(["down@0.2:0.9"])
        moves += 1
        for blink in range(1, 4):
            probe = recorder.capture(
                f"transitions/{phase}/action_row_move_{moves}_"
                f"blink_{blink}.png"
            )
            detected = preparation_action_row(probe)
            if detected is not None:
                row = detected
                break
            time.sleep(0.2)
    if row != target_row:
        raise RuntimeError(
            f"{phase}: action row {target_row} was not reached (last {row})"
        )


def scan_allied(
    recorder: RuntimeRecorder,
    phase: str,
    commander_rows: list[dict[str, object]],
) -> None:
    if any(int(row["hire_page_count"]) != 1 for row in commander_rows):
        raise RuntimeError(
            "the preserved canonical seed unexpectedly needs multi-page "
            "hire navigation"
        )
    previous_status: tuple[bool, ...] | None = None
    for index, commander in enumerate(commander_rows):
        commander_id = int(commander["commander_id"])
        root = recorder.capture(
            f"{phase}/allied/commander_{commander_id:02d}_root.png"
        )
        current_status = status_dhash(root)
        if previous_status is not None and hash_distance(
            previous_status, current_status
        ) < 15:
            raise RuntimeError(
                f"{phase}: commander {commander_id} status did not change"
            )

        page: Path | None = None
        for attempt in range(1, 4):
            recorder.send(["c"], delay=1.1)
            probe = recorder.capture(
                f"transitions/{phase}/commander_{commander_id:02d}_"
                f"hire_attempt_{attempt}.png"
            )
            if hire_screen_visible(probe):
                page = recorder.capture(
                    f"{phase}/allied/"
                    f"commander_{commander_id:02d}_hire_page_01.png"
                )
                break
        if page is None:
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire surface did not open"
            )
        if not hire_screen_visible(page):
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire surface was not visible"
            )

        # The first offered row is selected on entry. Up reaches explicit END.
        # If the following C is ignored, retrying C is safe because focus is
        # still on END.
        recorder.send(["up"], delay=1.0)
        exited = False
        for attempt in range(1, 4):
            recorder.send(["c"], delay=1.1)
            probe = recorder.capture(
                f"transitions/{phase}/commander_{commander_id:02d}_"
                f"exit_attempt_{attempt}.png"
            )
            if not hire_screen_visible(probe):
                exited = True
                break
        if not exited:
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire END did not exit"
            )

        previous_status = current_status
        if index + 1 < len(commander_rows):
            selected = False
            for attempt in range(1, 4):
                recorder.send(["left", "down"], delay=1.0)
                probe = recorder.capture(
                    f"transitions/{phase}/commander_{commander_id + 1:02d}_"
                    f"select_attempt_{attempt}.png"
                )
                if hash_distance(current_status, status_dhash(probe)) >= 15:
                    selected = True
                    break
            if not selected:
                raise RuntimeError(
                    f"{phase}: commander {commander_id + 1} could not be selected"
                )


def open_arrangement(recorder: RuntimeRecorder, phase: str) -> None:
    # Hire END returns to the commander column. Select the absolute 배치 row
    # from observed cursor geometry instead of assuming that every transition
    # key was accepted.
    ensure_action_row(recorder, f"{phase}_arrangement", 3)
    menu: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/arrangement_open_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            menu = recorder.capture(f"{phase}/arrangement/menu.png")
            break
    if menu is None:
        raise RuntimeError(f"{phase}: arrangement menu was not visible")


def scan_arrangement_roster(
    recorder: RuntimeRecorder,
    phase: str,
    roster_page_count: int,
) -> None:
    roster: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/roster_open_attempt_{attempt}.png"
        )
        if arrangement_roster_visible(probe):
            roster = probe
            break
    if roster is None:
        raise RuntimeError(f"{phase}: arrangement roster did not open")
    for page in range(1, roster_page_count + 1):
        roster = recorder.capture(
            f"{phase}/arrangement/roster_page_{page:02d}.png"
        )
        if not arrangement_roster_visible(roster):
            raise RuntimeError(
                f"{phase}: arrangement roster page {page} was not visible"
            )
        if page < roster_page_count:
            recorder.send(["right"])
    returned = False
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/roster_return_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            returned = True
            break
    if not returned:
        raise RuntimeError(f"{phase}: arrangement roster did not return")


def close_fixed_detail(
    recorder: RuntimeRecorder,
    phase: str,
    label: str,
) -> None:
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/{label}_close_attempt_{attempt}.png"
        )
        if not fixed_detail_visible(probe):
            return
    raise RuntimeError(f"{phase}: {label} detail popup did not close")


def open_current_fixed_detail(
    recorder: RuntimeRecorder,
    phase: str,
    record: dict[str, object],
) -> Path:
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/{record_slug(record)}_"
            f"open_attempt_{attempt}.png"
        )
        if fixed_detail_visible(probe):
            detail = recorder.capture(
                f"{phase}/fixed/{record_slug(record)}.png"
            )
            if fixed_detail_visible(detail):
                return detail
    raise RuntimeError(
        f"{phase}: fixed record {record['index']} detail popup did not open"
    )


def save_fixed_detail_checkpoint(
    recorder: RuntimeRecorder,
    phase: str,
    record: dict[str, object],
) -> Path | None:
    if not record.get("runtime_checkpoint_chars"):
        return None
    return recorder.save_gst(
        f"states/{phase}_fixed_{record_slug(record)}.gst"
    )


def scan_fixed_records(
    recorder: RuntimeRecorder,
    phase: str,
    route: list[dict[str, object]],
) -> None:
    if not route:
        return
    # The fourth arrangement row is 적군보기.
    recorder.send(["down", "down", "down"], delay=0.9)
    recorder.send(["c"], delay=1.1)
    entry = recorder.capture(f"{phase}/fixed/map_entry.png")
    first = route[0]
    if fixed_detail_visible(entry):
        first_path = recorder.capture(
            f"{phase}/fixed/{record_slug(first)}.png"
        )
    else:
        first_path = open_current_fixed_detail(recorder, phase, first)
    if not fixed_detail_visible(first_path):
        raise RuntimeError(f"{phase}: first fixed-record detail was not visible")
    save_fixed_detail_checkpoint(recorder, phase, first)

    prior = first
    for record in route[1:]:
        close_fixed_detail(
            recorder,
            phase,
            record_slug(prior),
        )
        recorder.send(["right@0.2:0.8"])
        open_current_fixed_detail(recorder, phase, record)
        save_fixed_detail_checkpoint(recorder, phase, record)
        prior = record

    # Close the detail, then return from the map to the arrangement submenu.
    close_fixed_detail(recorder, phase, record_slug(route[-1]))
    returned: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/arrangement_return_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            returned = recorder.capture(
                f"{phase}/arrangement/returned_menu.png"
            )
            break
    if returned is None:
        raise RuntimeError(f"{phase}: arrangement menu did not return")
    # The submenu-to-preparation transition includes a black redraw.
    recorder.send(["b"], delay=2.0)


def shop_round_trip(recorder: RuntimeRecorder) -> None:
    ensure_action_row(recorder, "shop", 2)
    recorder.send(["c"], delay=1.2)
    recorder.capture("shop/menu.png")
    recorder.send(["c"], delay=2.5)
    item_list = recorder.capture("shop/item_list.png")
    if bright_ratio(item_list, (8, 24, 312, 215)) < 0.01:
        raise RuntimeError("shop item list was captured before it finished drawing")

    returned: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["b"], delay=2.5)
        probe = recorder.capture(
            f"transitions/shop/return_attempt_{attempt}.png"
        )
        if preparation_screen_visible(probe):
            returned = recorder.capture("shop/returned_unfocused.png")
            break
    if returned is None:
        raise RuntimeError("shop B did not return to the preparation surface")

    # The observed source transition returns with right-side 용병고용 focus.
    # C transfers to the commander column. Retry only while the cursor is
    # positively still on the right; an unknown blink phase gets recaptured
    # without another input so it cannot open hire accidentally.
    focused: Path | None = None
    sent_c = False
    for attempt in range(1, 7):
        if not sent_c:
            recorder.send(["c"], delay=1.5)
            sent_c = True
        probe = recorder.capture(
            f"transitions/shop/focus_attempt_{attempt}.png"
        )
        side = preparation_focus_side(probe)
        if side == "left":
            focused = recorder.capture("shop/returned_focused.png")
            break
        if side == "right":
            sent_c = False
        else:
            time.sleep(0.3)
    if focused is None or not preparation_screen_visible(focused):
        raise RuntimeError("shop return did not restore preparation focus")


def capture_pairs(output: Path) -> list[dict[str, object]]:
    rows = []
    for pre in sorted((output / "pre").rglob("*.png")):
        relative = pre.relative_to(output / "pre")
        post = output / "post" / relative
        if not post.exists():
            continue
        pre_sha = sha256_path(pre)
        post_sha = sha256_path(post)
        rows.append(
            {
                "surface": str(relative),
                "pre_sha256": pre_sha,
                "post_sha256": post_sha,
                "byte_identical": pre_sha == post_sha,
            }
        )
    return rows


def launch_to_preparation(
    recorder: RuntimeRecorder,
    rom: Path,
    seed_gst: Path,
    scenario_number: int,
    runtime_name: str,
    output: Path,
) -> None:
    recorder.run_command(
        [
            sys.executable,
            str(RUN_SEQUENCE),
            "scenario-select",
            "--rom",
            str(rom),
            "--scenario-number",
            str(scenario_number),
            "--runtime-name",
            runtime_name,
            "--manual-slot-gst",
            str(seed_gst),
            "--initial-delay",
            "6.0",
            "--virtual-display",
            recorder.display,
            "--replace-existing",
            "--send-event",
        ]
    )
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
            "80",
            "--capture-prefix",
            str(output / "briefing/detect.png"),
            "--virtual-display",
            recorder.display,
            "--send-event",
        ]
    )


def run_matrix_capture(
    profile: str,
    rom: Path,
    reference_rom: Path,
    seed_gst: Path,
    scenario_number: int,
    display: str,
    output_root: Path,
    runtime_root: Path,
    run_id: str,
) -> dict[str, object]:
    output = output_root / profile / f"s{scenario_number:02d}" / run_id
    if output.exists():
        raise FileExistsError(
            f"output already exists; choose a new --run-id: {output}"
        )
    output.mkdir(parents=True)
    runtime_name = (
        f"prep-surface-{profile}-s{scenario_number:02d}-{run_id}"
    )
    if Path(runtime_name).name != runtime_name:
        raise ValueError("--run-id must produce one safe runtime directory name")
    runtime_home = runtime_root / runtime_name
    recorder = RuntimeRecorder(output, display, runtime_home)
    plan = build_plan(rom, reference_rom, seed_gst, scenario_number)
    (output / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    commander_rows = plan["allied_commanders"]["seed_records"]
    route = plan["fixed_records"]["route"]
    roster_pages = int(plan["allied_commanders"]["roster_page_count"])
    started = time.time()
    try:
        launch_to_preparation(
            recorder,
            rom,
            seed_gst,
            scenario_number,
            runtime_name,
            output,
        )
        recorder.capture("pre/root.png")
        scan_allied(recorder, "pre", commander_rows)
        open_arrangement(recorder, "pre")
        scan_arrangement_roster(recorder, "pre", roster_pages)
        scan_fixed_records(recorder, "pre", route)
        recorder.save_gst("states/pre_shop.gst")

        shop_round_trip(recorder)

        scan_allied(recorder, "post", commander_rows)
        open_arrangement(recorder, "post")
        scan_arrangement_roster(recorder, "post", roster_pages)
        scan_fixed_records(recorder, "post", route)
        recorder.save_gst("states/post_shop.gst")

        pairs = capture_pairs(output)
        expected_pair_count = (
            sum(
                1 + int(commander["hire_page_count"])
                for commander in commander_rows
            )
            + roster_pages
            + len(route)
            + 3  # arrangement menu, map entry, and returned submenu
        )
        fixed_hashes = {
            sha256_path(output / "pre/fixed" / f"{record_slug(row)}.png")
            for row in route
        }
        all_exact = (
            len(pairs) == expected_pair_count
            and all(row["byte_identical"] for row in pairs)
        )
        result = {
            "schema_version": 1,
            "status": (
                "captured_exact_unreviewed"
                if all_exact
                else "captured_mismatch_unreviewed"
            ),
            "acceptance_updated": False,
            "profile": profile,
            "scenario": scenario_number,
            "run_id": run_id,
            "elapsed_seconds": round(time.time() - started, 3),
            "expected_pair_count": expected_pair_count,
            "actual_pair_count": len(pairs),
            "distinct_pre_fixed_detail_count": len(fixed_hashes),
            "capture_pairs": pairs,
            "captures": recorder.captures,
            "actions": recorder.actions,
            "required_human_review": [
                "all Korean commander, class, and offered mercenary labels",
                "full minimap and tile-row integrity",
                "all commander and mercenary sprites",
                "gray acted sprites and result screens in a separate battle run",
            ],
            "limitations": [
                "class-change choices are only applicable when the live seed exposes them",
                "hidden or (255,255) fixed records are source-not-applicable here",
                "gray acted sprites and battle result screens are not exercised by this preparation run",
            ],
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as exc:
        failure_gst: str | None = None
        try:
            failure_state = recorder.save_gst("states/failure.gst")
            failure_gst = str(failure_state.relative_to(output))
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "acceptance_updated": False,
            "profile": profile,
            "scenario": scenario_number,
            "run_id": run_id,
            "elapsed_seconds": round(time.time() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_gst": failure_gst,
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        terminate_blastem_processes(display=display)


def validate_scenario(value: str) -> int:
    number = int(value)
    if not SCENARIO_MIN <= number <= SCENARIO_MAX:
        raise argparse.ArgumentTypeError(
            f"scenario must be {SCENARIO_MIN}..{SCENARIO_MAX}"
        )
    return number


def validate_run_id(value: str) -> str:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise argparse.ArgumentTypeError("run ID must be one directory name")
    if not all(character.isalnum() or character in "-_" for character in value):
        raise argparse.ArgumentTypeError(
            "run ID may contain only letters, digits, '-' and '_'"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or capture the same-run Korean preparation/shop surface matrix. "
            "Runtime output remains unreviewed and never changes acceptance state."
        )
    )
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profile", choices=sorted(PROFILE_ROMS), required=True)
    parser.add_argument("--scenario", type=validate_scenario, required=True)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--reference-rom", type=Path, default=DEFAULT_REFERENCE_ROM)
    parser.add_argument("--seed-gst", type=Path, default=DEFAULT_SEED_GST)
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=validate_run_id)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom or PROFILE_ROMS[args.profile]
    for label, path in (
        ("ROM", rom),
        ("reference ROM", args.reference_rom),
        ("seed GST", args.seed_gst),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")

    if args.command == "plan":
        plan = build_plan(
            rom,
            args.reference_rom,
            args.seed_gst,
            args.scenario,
        )
        encoded = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(encoded, end="")
        else:
            if args.output.exists():
                raise FileExistsError(f"refusing to overwrite {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        return 0

    if args.run_id is None:
        parser.error("run requires --run-id")
    if args.output is not None:
        parser.error("--output is only valid with plan")
    result = run_matrix_capture(
        args.profile,
        rom,
        args.reference_rom,
        args.seed_gst,
        args.scenario,
        args.display,
        args.output_root,
        args.runtime_root,
        args.run_id,
    )
    print(
        f"{result['status']}: {result['actual_pair_count']}/"
        f"{result['expected_pair_count']} pre/post pairs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
