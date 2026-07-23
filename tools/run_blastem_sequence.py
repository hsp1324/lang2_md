#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
BLASTEM = ROOT / "tools/blastem/blastem"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
RUNTIME_ROOT = ROOT / "captures/runtime"
LOG_ROOT = ROOT / "captures/run"

MANUAL_SLOT_BASES = (0x194E, 0x1AF6, 0x1C9E, 0x1E46)
MANUAL_SLOT_CHECKSUM_DATA_SIZE = 0x1A6
MANUAL_SLOT_CHECKSUM_OFFSET = 0x1A6
MANUAL_SLOT_SCENARIO_OFFSET = 0x000
MANUAL_SLOT_HERO_NAME_OFFSET = 0x130
MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET = 0x142
MANUAL_SLOT_COMMANDER_ROSTER_OFFSET = 0x030
MANUAL_SLOT_COMMANDER_RECORD_SIZE = 0x018
MANUAL_SLOT_COMMANDER_COUNT = 10
MANUAL_SLOT_COMMANDER_CLASS_OFFSET = 0x00
MANUAL_SLOT_COMMANDER_LEVEL_OFFSET = 0x02
MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET = 0x03
MANUAL_SLOT_COMMANDER_AT_OFFSET = 0x04
MANUAL_SLOT_COMMANDER_DF_OFFSET = 0x05
GST_WORK_RAM_FILE_OFFSET = 0x2478
MANUAL_SLOT_WORK_RAM_SEGMENTS = (
    (0xA49C, 0x154),
    (0xBD6E, 0x002),
    (0xC7F2, 0x050),
)
SRAM_VALID_FLAGS_OFFSET = 0x1FF0
SRAM_FORMAT_MARKER_OFFSET = 0x1FEE
SRAM_FORMAT_MARKER = 0x07CA
JP_DEFAULT_HERO_NAME = bytes.fromhex("B4 D9 B3 A8 DD FF")
KO_DEFAULT_HERO_NAME = bytes.fromhex("B4 D9 FF FF FF FF")
JP_DEFAULT_HERO_DIALOGUE_NAME = bytes.fromhex(
    "00 03 00 2A 00 02 00 4C 00 27"
)
DIRECT_ELWIN_NAME_OFFSET = 0x97404
SAVED_DIALOGUE_NAME_SIZE = 10


SEQUENCES = {
    # Launch a clean test window without sending game input. Screen-guided
    # investigations can then advance one verified transition at a time.
    "launch-only": [],
    # Opening/title into the game's load-slot screen. Copy or retain a runtime
    # SRAM with at least one valid scenario save before using scenario select.
    "load-screen": ["start:2.0", "start:1.0", "down:0.8", "c:4.0"],
    # Opening/title into the name entry screen. Useful as a glyph/code probe.
    "name-entry": ["start:2.0", "start:1.0", "c:0.8"],
    # Opening/title/name/route into the scenario description screen.
    "scenario": ["start:2.0", "start:1.0", "c:0.8", "c:0.8", "c:0.8"],
    # Filled from --scenario-number after argument parsing. This uses a valid
    # manual save in the load-screen runtime SRAM to enter the built-in
    # Left, Right, Start, C scenario selector.
    "scenario-select": [],
    # Stop immediately after entering the built-in scenario selector. This is
    # the stable capture point for its title and dynamic saved-scenario number.
    "scenario-select-entry": [],
    # Scenario screen into the commander preparation screen.
    "prep": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:0.8",
    ],
    # Scenario 1 shop, first item selected/purchased-confirm screen.
    "shop-buy-list": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:0.8",
    ],
    # Scenario 1 shop, one step past the buy list. This enters the follow-up
    # item/possession path and is not the first shop title check.
    "shop": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
    ],
    # Scenario 1 shop, purchase the first item after selecting it.
    "shop-buy": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
    ],
    # Scenario 1 full shop regression path:
    # Buy the first dagger, confirm the completion popup with C, leave the item
    # list with B, re-enter the shop, enter sell, and select the bought dagger.
    "shop-buy-sell": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:3.0",
        "c:0.8",
        "c:0.8",
        "b:3.0",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "down:0.8",
        "c:3.0",
        "c:0.8",
    ],
    # Scenario 1 commander arrangement screen.
    "arrange": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:0.8",
    ],
    # Scenario 1 deploy from commander arrangement, then advance dialogue a few pages.
    "deploy-dialogue": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:1.2",
        "c:1.2",
        "c:1.2",
    ],
}

# Same regression path, stopped on the sell list before confirming the dagger.
SEQUENCES["shop-sell-list"] = list(SEQUENCES["shop-buy-sell"][:-1])

# This sequence uses the deploy/dialogue inputs, then advances one confirmation
# at a time until the full command menu is detected. Fixed confirmation counts
# are timing-sensitive and can accidentally choose Move on faster hosts.
SEQUENCES["battle-command"] = list(SEQUENCES["deploy-dialogue"])
SEQUENCES["first-turn-dialogue"] = list(SEQUENCES["deploy-dialogue"])
# Reuse an already running emulator and advance only until a full unit command
# panel is visible. This is useful for later scenarios with long opening events.
SEQUENCES["detect-command"] = []
# Reuse an already running emulator and advance briefing pages only until the
# commander preparation panel appears. Unlike fixed C loops, this cannot spill
# into commander selection or hire actions when briefing lengths differ.
SEQUENCES["detect-prep"] = []


def scenario_select_entry_keys() -> list[str]:
    # The game accepts this cheat as a short sequence. Human-scale waits such
    # as 0.8 seconds between these four keys silently perform a normal load.
    return [
        *SEQUENCES["load-screen"],
        "down:0.8",
        "left@0.12:0.05",
        "right@0.12:0.05",
        "start@0.12:0.05",
        # The cheat is complete after this C. Leave enough time for a stable
        # capture before any scenario-row movement or confirmation.
        "c@0.12:2.0",
    ]


def scenario_select_keys(
    scenario_number: int,
    current_scenario_number: int = 1,
) -> list[str]:
    for value in (scenario_number, current_scenario_number):
        if not 1 <= value <= 31:
            raise ValueError("scenario number must be 1..31")
    # The selector opens on the loaded slot's scenario number and wraps after
    # 31. Earlier automation incorrectly added target-1 moves, so a Scenario
    # 26 save plus 25 Down presses entered Scenario 20.
    movement_count = (scenario_number - current_scenario_number) % 31
    movement = ["down:0.08"] * movement_count
    return [
        *scenario_select_entry_keys(),
        *movement,
        "c:4.0",
    ]


def running_blastem_pids(proc_root: Path = Path("/proc")) -> list[int]:
    pids = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text(encoding="ascii").strip() != "blastem":
                continue
            stat = (entry / "stat").read_text(encoding="ascii")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        closing_parenthesis = stat.rfind(")")
        if closing_parenthesis < 0 or len(stat) <= closing_parenthesis + 2:
            continue
        if stat[closing_parenthesis + 2] != "Z":
            pids.append(int(entry.name))
    return sorted(pids)


def terminate_blastem_processes(timeout: float = 2.0) -> None:
    pids = running_blastem_pids()
    if not pids:
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + timeout
    while running_blastem_pids() and time.monotonic() < deadline:
        time.sleep(0.05)

    survivors = running_blastem_pids()
    for pid in survivors:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + timeout
    while running_blastem_pids() and time.monotonic() < deadline:
        time.sleep(0.05)
    survivors = running_blastem_pids()
    if survivors:
        raise RuntimeError(
            "BlastEm did not terminate (PID "
            + ", ".join(str(pid) for pid in survivors)
            + ")"
        )


def manual_slot_checksum(data: bytes | bytearray, base: int) -> int:
    end = base + MANUAL_SLOT_CHECKSUM_DATA_SIZE
    return (
        sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(base, end, 2)
        )
        + 1
    ) & 0xFFFF


def manual_slot_scenario_number(
    sram_path: Path,
    slot_index: int = 0,
) -> int:
    if not 0 <= slot_index < len(MANUAL_SLOT_BASES):
        raise ValueError("manual slot index must be 0..3")
    data = sram_path.read_bytes()
    if len(data) != 0x2000:
        raise ValueError("BlastEm SRAM must be exactly 8192 bytes")
    marker = int.from_bytes(
        data[SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2], "big"
    )
    if marker != SRAM_FORMAT_MARKER:
        raise ValueError(
            f"BlastEm SRAM has invalid format marker "
            f"0x{marker:04X} != 0x{SRAM_FORMAT_MARKER:04X}"
        )
    flags = int.from_bytes(
        data[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2], "big"
    )
    if not flags & (1 << (slot_index + 1)):
        raise ValueError(f"manual slot {slot_index + 1} is not valid")
    base = MANUAL_SLOT_BASES[slot_index]
    checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
    stored = int.from_bytes(data[checksum_offset : checksum_offset + 2], "big")
    calculated = manual_slot_checksum(data, base)
    if stored != calculated:
        raise ValueError(
            f"manual slot at 0x{base:04X} has invalid checksum "
            f"0x{stored:04X} != 0x{calculated:04X}"
        )
    offset = base + MANUAL_SLOT_SCENARIO_OFFSET
    scenario_number = int.from_bytes(data[offset : offset + 2], "big")
    if not 1 <= scenario_number <= 31:
        raise ValueError(
            f"manual slot {slot_index + 1} has invalid scenario "
            f"number {scenario_number}"
        )
    return scenario_number


def patch_manual_slot_commander_progress(
    sram_path: Path,
    commander_id: int,
    level: int,
    experience: int,
    slot_index: int = 0,
    expected_class: int | None = None,
    new_class: int | None = None,
    new_at: int | None = None,
    new_df: int | None = None,
) -> tuple[int, int, int]:
    if not 1 <= commander_id <= MANUAL_SLOT_COMMANDER_COUNT:
        raise ValueError(
            f"commander ID must be 1..{MANUAL_SLOT_COMMANDER_COUNT}"
        )
    if not 1 <= level <= 10:
        raise ValueError("commander level must be 1..10")
    if not 0 <= experience <= 0xFF:
        raise ValueError("commander experience must be 0..255")
    if new_class is not None and not 0 <= new_class <= 0x9C:
        raise ValueError("commander class must be 0..156")
    for label, value in (("AT", new_at), ("DF", new_df)):
        if value is not None and not 0 <= value <= 99:
            raise ValueError(f"commander {label} must be 0..99")

    # This validates the format marker, slot flag, checksum, and scenario before
    # any byte is changed.
    manual_slot_scenario_number(sram_path, slot_index)
    data = bytearray(sram_path.read_bytes())
    base = MANUAL_SLOT_BASES[slot_index]
    record = (
        base
        + MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + (commander_id - 1) * MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    current_class = data[record + MANUAL_SLOT_COMMANDER_CLASS_OFFSET]
    old_level = data[record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET]
    old_experience = data[record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET]
    if expected_class is not None and current_class != expected_class:
        raise ValueError(
            f"commander {commander_id} class changed: "
            f"0x{current_class:02X} != 0x{expected_class:02X}"
        )
    if new_class is not None:
        data[record + MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = new_class
    if new_at is not None:
        data[record + MANUAL_SLOT_COMMANDER_AT_OFFSET] = new_at
    if new_df is not None:
        data[record + MANUAL_SLOT_COMMANDER_DF_OFFSET] = new_df
    data[record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = level
    data[record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = experience
    checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
    data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
        data, base
    ).to_bytes(2, "big")
    sram_path.write_bytes(data)
    return current_class, old_level, old_experience


def recover_manual_slot_from_gst(
    gst_path: Path,
    sram_path: Path,
    slot_index: int = 0,
) -> None:
    if not 0 <= slot_index < len(MANUAL_SLOT_BASES):
        raise ValueError("manual slot index must be 0..3")
    gst = gst_path.read_bytes()
    record_parts = []
    for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = GST_WORK_RAM_FILE_OFFSET + address
        end = start + size
        if len(gst) < end:
            raise ValueError(
                "GST is too short to contain the manual-slot work RAM segments"
            )
        record_parts.append(gst[start:end])
    record = b"".join(record_parts)
    if len(record) != MANUAL_SLOT_CHECKSUM_DATA_SIZE:
        raise ValueError("manual-slot work RAM segment sizes changed")
    hero_name = record[
        MANUAL_SLOT_HERO_NAME_OFFSET :
        MANUAL_SLOT_HERO_NAME_OFFSET + len(JP_DEFAULT_HERO_NAME)
    ]
    if 0xFF not in hero_name:
        raise ValueError("GST manual-slot record has no hero-name terminator")

    if sram_path.exists():
        sram = bytearray(sram_path.read_bytes())
        if len(sram) != 0x2000:
            raise ValueError("BlastEm SRAM must be exactly 8192 bytes")
    else:
        sram = bytearray(0x2000)
    marker = int.from_bytes(
        sram[SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2], "big"
    )
    if marker not in (0, SRAM_FORMAT_MARKER):
        raise ValueError(
            f"BlastEm SRAM has unexpected format marker 0x{marker:04X}"
        )
    sram[
        SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
    ] = SRAM_FORMAT_MARKER.to_bytes(2, "big")
    base = MANUAL_SLOT_BASES[slot_index]
    sram[base : base + MANUAL_SLOT_CHECKSUM_DATA_SIZE] = record
    checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
    sram[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
        sram, base
    ).to_bytes(2, "big")
    flags = int.from_bytes(
        sram[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2], "big"
    )
    flags |= 1 << (slot_index + 1)
    sram[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = flags.to_bytes(
        2, "big"
    )
    sram_path.parent.mkdir(parents=True, exist_ok=True)
    sram_path.write_bytes(sram)


def korean_default_dialogue_name(rom: Path = DEFAULT_ROM) -> bytes:
    data = rom.read_bytes()
    encoded = bytearray()
    for offset in range(
        DIRECT_ELWIN_NAME_OFFSET,
        DIRECT_ELWIN_NAME_OFFSET + SAVED_DIALOGUE_NAME_SIZE,
        2,
    ):
        word = data[offset : offset + 2]
        encoded.extend(word)
        if word == b"\xFF\xFF":
            return bytes(encoded).ljust(SAVED_DIALOGUE_NAME_SIZE, b"\xFF")
    raise ValueError("built ROM Elwin speaker name has no terminator")


def migrate_scenario_select_default_name(
    path: Path,
    korean_dialogue_name: bytes | None = None,
) -> int:
    if not path.exists():
        return 0
    if korean_dialogue_name is None:
        korean_dialogue_name = korean_default_dialogue_name()
    if len(korean_dialogue_name) != SAVED_DIALOGUE_NAME_SIZE:
        raise ValueError("saved dialogue name must occupy five words")
    data = bytearray(path.read_bytes())
    migrated = 0
    for base in MANUAL_SLOT_BASES:
        name_start = base + MANUAL_SLOT_HERO_NAME_OFFSET
        name_end = name_start + len(JP_DEFAULT_HERO_NAME)
        dialogue_start = base + MANUAL_SLOT_HERO_DIALOGUE_NAME_OFFSET
        dialogue_end = dialogue_start + len(JP_DEFAULT_HERO_DIALOGUE_NAME)
        byte_name = bytes(data[name_start:name_end])
        dialogue_name = bytes(data[dialogue_start:dialogue_end])
        if byte_name not in (JP_DEFAULT_HERO_NAME, KO_DEFAULT_HERO_NAME):
            continue
        if dialogue_name not in (
            JP_DEFAULT_HERO_DIALOGUE_NAME,
            korean_dialogue_name,
        ):
            continue
        if (
            byte_name == KO_DEFAULT_HERO_NAME
            and dialogue_name == korean_dialogue_name
        ):
            continue
        checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
        stored = int.from_bytes(data[checksum_offset : checksum_offset + 2], "big")
        calculated = manual_slot_checksum(data, base)
        if stored != calculated:
            raise ValueError(
                f"manual slot at 0x{base:04X} has invalid checksum "
                f"0x{stored:04X} != 0x{calculated:04X}"
            )
        if byte_name == JP_DEFAULT_HERO_NAME:
            data[name_start:name_end] = KO_DEFAULT_HERO_NAME
        if dialogue_name == JP_DEFAULT_HERO_DIALOGUE_NAME:
            data[dialogue_start:dialogue_end] = korean_dialogue_name
        data[checksum_offset : checksum_offset + 2] = manual_slot_checksum(
            data, base
        ).to_bytes(2, "big")
        migrated += 1
    if migrated:
        path.write_bytes(data)
    return migrated


def disable_host_gamepad_bindings(config: str) -> str:
    start_marker = "\tpads {"
    end_marker = "\tmice {"
    start = config.find(start_marker)
    end = config.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise ValueError("BlastEm config gamepad binding block was not found")
    return config[:start] + "\tpads {\n\t}\n" + config[end:]


def make_key_command(args: argparse.Namespace, keys: list[str]) -> list[str]:
    command = [
        sys.executable,
        str(SEND_KEYS),
        "--hold",
        str(args.hold),
        *keys,
    ]
    if args.send_event:
        command.insert(2, "--send-event")
    if args.click_window:
        command.insert(2, "--click-window")
    return command


def battle_command_menu_visible(path: Path) -> bool:
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    image = frame.crop(
        (
            round(15 * scale_x),
            round(25 * scale_y),
            round(95 * scale_x),
            round(110 * scale_y),
        )
    )
    pixels = image.load()
    blue_pixels = 0
    dark_panel_pixels = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            if blue > 70 and blue > red * 1.3 and blue > green * 1.2:
                blue_pixels += 1
            if 50 <= blue <= 180 and red < 45 and green < 65 and blue > red * 2 and blue > green * 1.8:
                dark_panel_pixels += 1
    # The full command menu has a large, contiguous dark-blue interior on the
    # left. Blue roofs and unit-selection highlights can satisfy the broader
    # color totals above, but do not fill this stable interior rectangle.
    command_interior = frame.crop(
        (
            round(10 * scale_x),
            round(28 * scale_y),
            round(65 * scale_x),
            round(105 * scale_y),
        )
    )
    command_interior_dark_pixels = sum(
        1
        for red, green, blue in command_interior.get_flattened_data()
        if 50 <= blue <= 180
        and red < 45
        and green < 65
        and blue > red * 2
        and blue > green * 1.8
    )
    command_interior_white_pixels = sum(
        1
        for red, green, blue in command_interior.get_flattened_data()
        if red > 170 and green > 170 and blue > 170
    )
    # Command panels can be 64 or 72 source pixels wide depending on the row
    # set. Their right gold frame always crosses this shared band; preparation,
    # dialogue, and result panels use much wider frame positions. This extra
    # geometry check lets high-resolution captures use a lower text-density
    # threshold without accepting those other blue screens.
    command_right_border = frame.crop(
        (
            round(94 * scale_x),
            round(42 * scale_y),
            round(107 * scale_x),
            round(145 * scale_y),
        )
    )
    command_right_border_gold_pixels = sum(
        1
        for red, green, blue in command_right_border.get_flattened_data()
        if red > 100
        and green > 70
        and blue < 80
        and red > blue * 1.5
    )
    # Portrait cut-ins also have a broad blue background and used to trigger
    # this detector early. A real command menu is only available with the blue
    # battle status bar visible across the bottom of the frame.
    status = frame.crop((0, round(195 * scale_y), frame.width, round(235 * scale_y)))
    status_blue_pixels = sum(
        1
        for red, green, blue in status.get_flattened_data()
        if blue > 70 and blue > red * 1.3 and blue > green * 1.2
    )
    return (
        blue_pixels > image.width * image.height * 0.44
        # Water-heavy maps can fill this entire crop with blue pixels. A real
        # command panel also contains its gold frame, labels, and portrait/map
        # content, so reject nearly solid-blue backgrounds.
        and blue_pixels < image.width * image.height * 0.85
        and dark_panel_pixels > 1000 * scale_x * scale_y
        and command_interior_dark_pixels
        > command_interior.width * command_interior.height * 0.30
        # Water, roofs, and selection highlights have no dense command labels.
        # The sparse four-row panel in a 960x720 Scenario 9 capture occupies
        # only about 4.1% of this crop. Geometry and the status-bar checks keep
        # the relaxed threshold from accepting wide dialogue/result panels.
        and command_interior_white_pixels
        > command_interior.width * command_interior.height * 0.035
        and command_right_border_gold_pixels
        > command_right_border.width * command_right_border.height * 0.05
        # The ornate status-bar frame occupies a little over half of this
        # crop on some maps; 45% still distinguishes it from dialogue views.
        # Preparation/hire screens fill more of the same crop with solid blue
        # (about 52%), so cap the ratio as well as enforcing the lower bound.
        and status_blue_pixels > status.width * status.height * 0.45
        and status_blue_pixels < status.width * status.height * 0.505
    )


def game_over_visible(path: Path) -> bool:
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240

    def crop(box: tuple[int, int, int, int]) -> Image.Image:
        left, top, right, bottom = box
        return frame.crop(
            (
                round(left * scale_x),
                round(top * scale_y),
                round(right * scale_x),
                round(bottom * scale_y),
            )
        )

    def white_ratio(image: Image.Image) -> float:
        return sum(
            1
            for red, green, blue in image.get_flattened_data()
            if red > 170 and green > 170 and blue > 170
        ) / (image.width * image.height)

    panel = crop((24, 97, 294, 170))
    panel_dark_ratio = sum(
        1
        for red, green, blue in panel.get_flattened_data()
        if 50 <= blue <= 180
        and red < 45
        and green < 65
        and blue > red * 2
        and blue > green * 1.8
    ) / (panel.width * panel.height)
    top = crop((30, 101, 288, 119))
    middle = crop((30, 119, 288, 146))
    bottom = crop((30, 146, 288, 166))
    # GAME OVER is the only runtime panel with one centered white row in this
    # vertical band. Ordinary dialogue starts in the top band, even when it
    # contains only one line.
    return (
        panel_dark_ratio > 0.80
        and white_ratio(top) < 0.01
        and white_ratio(middle) > 0.04
        and white_ratio(bottom) < 0.01
    )


def preparation_screen_visible(path: Path) -> bool:
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240

    def crop(box: tuple[int, int, int, int]) -> Image.Image:
        left, top, right, bottom = box
        return frame.crop(
            (
                round(left * scale_x),
                round(top * scale_y),
                round(right * scale_x),
                round(bottom * scale_y),
            )
        )

    def ratios(image: Image.Image) -> tuple[float, float]:
        pixels = list(image.get_flattened_data())
        dark_blue = sum(
            1
            for red, green, blue in pixels
            if 50 <= blue <= 180
            and red < 45
            and green < 65
            and blue > red * 2
            and blue > green * 1.8
        )
        gold = sum(
            1
            for red, green, blue in pixels
            if red > 100 and green > 70 and blue < 80 and red > blue * 1.5
        )
        return dark_blue / len(pixels), gold / len(pixels)

    top_left_blue, _ = ratios(crop((10, 32, 142, 136)))
    command_blue, _ = ratios(crop((145, 115, 318, 214)))
    money_blue, _ = ratios(crop((10, 214, 142, 239)))
    divider_blue, divider_gold = ratios(crop((141, 32, 147, 215)))

    # The preparation UI has two large blue columns split by a continuous gold
    # divider and a small blue money panel at bottom left. Briefings have no
    # money panel; battle/status screens lack the narrow gold divider.
    return (
        top_left_blue > 0.8
        and command_blue > 0.75
        and money_blue > 0.23
        and divider_blue < 0.25
        # The ornate divider is partly blue/black in the real 640x480
        # preparation screen. Scenario 11 measured about 14.9% gold; the old
        # 18% threshold skipped the screen and let detector confirmations enter
        # the mercenary-hire submenu.
        and divider_gold > 0.14
    )


def capture_window(path: Path, *, xlib_only: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(CAPTURE_WINDOW), str(path)]
    if xlib_only:
        command.append("--xlib-only")
    subprocess.check_call(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
    )


def detection_capture_path(args: argparse.Namespace, fallback: Path, step: int) -> Path:
    if args.capture_prefix is None:
        return fallback
    prefix = args.capture_prefix
    suffix = prefix.suffix or ".png"
    stem = prefix.stem if prefix.suffix else prefix.name
    return prefix.with_name(f"{stem}_{step:02d}{suffix}")


def advance_to_preparation_screen(args: argparse.Namespace) -> int:
    probe = LOG_ROOT / "preparation_probe.png"
    for step in range(args.max_confirmations + 1):
        frame = detection_capture_path(args, probe, step)
        capture_window(frame, xlib_only=args.xlib_capture)
        if preparation_screen_visible(frame):
            print(f"preparation screen detected after {step} confirmations")
            return 0
        if step == args.max_confirmations:
            break
        status = subprocess.call(
            make_key_command(args, [f"c:{args.confirmation_delay}"]), cwd=ROOT
        )
        if status:
            return status
    raise RuntimeError(
        "preparation screen was not detected after "
        f"{args.max_confirmations} confirmations"
    )


def advance_to_battle_command(args: argparse.Namespace) -> int:
    probe = LOG_ROOT / "battle_command_probe.png"
    for step in range(1, args.max_confirmations + 1):
        status = subprocess.call(
            make_key_command(args, [f"c:{args.confirmation_delay}"]), cwd=ROOT
        )
        if status:
            return status
        frame = detection_capture_path(args, probe, step)
        capture_window(frame, xlib_only=args.xlib_capture)
        if game_over_visible(frame):
            print(f"game over detected after {step} confirmations")
            return 2
        if battle_command_menu_visible(frame):
            time.sleep(2.0)
            capture_window(frame, xlib_only=args.xlib_capture)
            if battle_command_menu_visible(frame):
                print(f"battle command menu detected after {step} confirmations")
                return 0
    raise RuntimeError(
        "battle command menu was not detected after "
        f"{args.max_confirmations} confirmations"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sequence", choices=sorted(SEQUENCES))
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--window-width", type=int, default=320)
    parser.add_argument("--window-height", type=int, default=240)
    parser.add_argument("--scenario-number", type=int, default=14)
    parser.add_argument(
        "--max-confirmations",
        type=int,
        default=80,
        help="maximum single C presses used by a screen-detection sequence",
    )
    parser.add_argument(
        "--confirmation-delay",
        type=float,
        default=0.9,
        help="seconds to wait after each detector C press (use 2+ for full dialogue text)",
    )
    parser.add_argument("--click-window", action="store_true")
    parser.add_argument(
        "--xlib-capture",
        action="store_true",
        help=(
            "capture the BlastEm X11 client directly so detection remains "
            "valid while another Windows application covers the emulator"
        ),
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="terminate existing BlastEm processes before launching the test window",
    )
    parser.add_argument("--send-event", action="store_true", help="send direct window events instead of global XTest input")
    parser.add_argument(
        "--reuse-runtime-state",
        action="store_true",
        help="reuse the isolated test SRAM/save-state directory for this sequence",
    )
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument(
        "--manual-slot-gst",
        type=Path,
        help="recover isolated manual slot 1 from a BlastEm GST work-RAM record",
    )
    parser.add_argument(
        "--runtime-name",
        help="override the isolated runtime directory name for a diagnostic run",
    )
    parser.add_argument("--manual-slot-commander-id", type=int)
    parser.add_argument("--manual-slot-level", type=int)
    parser.add_argument("--manual-slot-experience", type=int)
    parser.add_argument(
        "--manual-slot-expected-class", type=lambda value: int(value, 0)
    )
    parser.add_argument(
        "--manual-slot-class",
        type=lambda value: int(value, 0),
        help="set the selected commander's class in the recovered manual slot",
    )
    parser.add_argument("--manual-slot-at", type=int)
    parser.add_argument("--manual-slot-df", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--capture-prefix",
        type=Path,
        help="retain each screen-detection frame as PREFIX_NN.png",
    )
    args = parser.parse_args()

    if not 1 <= args.scenario_number <= 31:
        raise ValueError("--scenario-number must be 1..31")
    if args.confirmation_delay < 0:
        raise ValueError("--confirmation-delay must be non-negative")
    progress_args = (
        args.manual_slot_commander_id,
        args.manual_slot_level,
        args.manual_slot_experience,
    )
    if any(value is not None for value in progress_args) and any(
        value is None for value in progress_args
    ):
        raise ValueError(
            "commander ID, level, and experience must be supplied together"
        )
    if args.runtime_name is not None and (
        not args.runtime_name
        or Path(args.runtime_name).name != args.runtime_name
        or args.runtime_name in (".", "..")
    ):
        raise ValueError("--runtime-name must be one directory name")
    scenario_selector_sequences = {"scenario-select", "scenario-select-entry"}
    if args.sequence == "scenario-select":
        SEQUENCES[args.sequence] = scenario_select_keys(args.scenario_number)
    elif args.sequence == "scenario-select-entry":
        SEQUENCES[args.sequence] = scenario_select_entry_keys()

    if not args.no_launch:
        if not args.dry_run:
            existing_pids = running_blastem_pids()
            if existing_pids and not args.replace_existing:
                raise RuntimeError(
                    "BlastEm is already running (PID "
                    + ", ".join(str(pid) for pid in existing_pids)
                    + "); close it or pass --replace-existing"
                )
            if existing_pids:
                terminate_blastem_processes()
        runtime_name = args.runtime_name or (
            "load-screen"
            if args.sequence in scenario_selector_sequences | {"launch-only"}
            else args.sequence
        )
        runtime_home = RUNTIME_ROOT / runtime_name
        # The scenario selector requires a valid manual save slot. Preserve its
        # dedicated runtime by default; recreating it requires an in-game save.
        if not args.reuse_runtime_state and runtime_name != "load-screen":
            shutil.rmtree(runtime_home, ignore_errors=True)
        runtime_home.mkdir(parents=True, exist_ok=True)
        sram_path = (
            runtime_home
            / ".local/share/blastem"
            / args.rom.stem
            / "save.sram"
        )
        if args.manual_slot_gst is not None:
            recover_manual_slot_from_gst(args.manual_slot_gst, sram_path)
            print(f"recovered cached manual slot 1 from {args.manual_slot_gst}")
        if (
            args.sequence in scenario_selector_sequences
            and args.rom.resolve() == DEFAULT_ROM.resolve()
        ):
            migrated = migrate_scenario_select_default_name(sram_path)
            if migrated:
                print(f"migrated Japanese default hero name in {migrated} manual slot(s)")
        if args.manual_slot_commander_id is not None:
            current_class, old_level, old_experience = (
                patch_manual_slot_commander_progress(
                    sram_path,
                    args.manual_slot_commander_id,
                    args.manual_slot_level,
                    args.manual_slot_experience,
                    expected_class=args.manual_slot_expected_class,
                    new_class=args.manual_slot_class,
                    new_at=args.manual_slot_at,
                    new_df=args.manual_slot_df,
                )
            )
            class_summary = (
                f"0x{current_class:02X}->0x{args.manual_slot_class:02X}"
                if args.manual_slot_class is not None
                else f"0x{current_class:02X}"
            )
            print(
                f"patched commander {args.manual_slot_commander_id} "
                f"class {class_summary} progress "
                f"LV{old_level}/EXP{old_experience} -> "
                f"LV{args.manual_slot_level}/EXP{args.manual_slot_experience}"
                + (
                    f", AT {args.manual_slot_at}"
                    if args.manual_slot_at is not None
                    else ""
                )
                + (
                    f", DF {args.manual_slot_df}"
                    if args.manual_slot_df is not None
                    else ""
                )
            )
        if args.sequence in scenario_selector_sequences:
            current_scenario_number = manual_slot_scenario_number(sram_path)
            if args.sequence == "scenario-select":
                SEQUENCES[args.sequence] = scenario_select_keys(
                    args.scenario_number,
                    current_scenario_number,
                )
                print(
                    "scenario selector uses valid saved Scenario "
                    f"{current_scenario_number} and starts on that scenario; "
                    f"targeting Scenario {args.scenario_number}"
                )
            else:
                print(
                    "entering scenario selector at saved Scenario "
                    f"{current_scenario_number} without confirming it"
                )
        config_dir = runtime_home / ".config/blastem"
        config_dir.mkdir(parents=True, exist_ok=True)
        default_config = (BLASTEM.parent / "default.cfg").read_text(encoding="utf-8")
        test_config = disable_host_gamepad_bindings(default_config).replace(
            "state_format native", "state_format gst"
        )
        (config_dir / "blastem.cfg").write_text(test_config, encoding="utf-8")
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        log_path = LOG_ROOT / f"blastem_{args.sequence}.log"

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(ROOT / "tools/blastem/lib")
        env["HOME"] = str(runtime_home)
        if "microsoft" in platform.release().lower():
            env.setdefault("SDL_AUDIODRIVER", "dummy")
        command = [
            str(BLASTEM),
            str(args.rom.resolve()),
            str(args.window_width),
            str(args.window_height),
        ]
        if args.dry_run:
            print("launch:", " ".join(command))
            print("runtime home:", runtime_home)
            print("log:", log_path)
        else:
            with log_path.open("w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    command,
                    cwd=BLASTEM.parent,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            time.sleep(args.initial_delay)
            if process.poll() is not None:
                log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(
                    f"BlastEm exited with status {process.returncode} before input; "
                    f"log: {log_path}\n{log_tail}"
                )

    initial_keys = list(SEQUENCES[args.sequence])
    if not args.no_launch and args.click_window:
        # A fresh SDL window starts with keyboard capture disabled. Remote
        # desktop focus changes can otherwise make the complete sequence vanish.
        initial_keys.insert(0, "capture:0.4")
    key_command = make_key_command(args, initial_keys)
    if args.dry_run:
        print("keys:", " ".join(key_command))
        if args.sequence in {
            "battle-command",
            "first-turn-dialogue",
            "detect-command",
        }:
            print("then: confirm and capture until the full command menu is detected")
        if args.sequence == "detect-prep":
            print("then: confirm and capture until the preparation screen is detected")
        if args.sequence == "first-turn-dialogue":
            print("then: close the unit menu and choose Start > 턴 종료")
        return 0
    status = subprocess.call(key_command, cwd=ROOT) if initial_keys else 0
    if not status and args.sequence == "detect-prep":
        return advance_to_preparation_screen(args)
    if status or args.sequence not in {
        "battle-command",
        "first-turn-dialogue",
        "detect-command",
    }:
        return status
    status = advance_to_battle_command(args)
    if status or args.sequence in {"battle-command", "detect-command"}:
        return status
    return subprocess.call(
        make_key_command(
            args,
            [
                "b:0.8",
                "start:1.0",
                "down:0.8",
                "down:0.8",
                "down:0.8",
                "down:1.0",
                "c:4.0",
            ],
        ),
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
