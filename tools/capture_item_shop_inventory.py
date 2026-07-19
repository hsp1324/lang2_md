#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as production_builder
from tools import build_item_shop_probe_rom as probe_builder
from tools.run_blastem_sequence import terminate_blastem_processes


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
ITEM_COUNT = 37
ROWS_PER_PAGE = 5


def item_position(item_id: int) -> tuple[int, int]:
    if not 1 <= item_id <= ITEM_COUNT:
        raise ValueError(f"item ID must be 1..{ITEM_COUNT}")
    return divmod(item_id - 1, ROWS_PER_PAGE)


def movement_after(item_id: int, wait: float = 0.45) -> list[str]:
    if not 1 <= item_id < ITEM_COUNT:
        if item_id == ITEM_COUNT:
            return []
        raise ValueError(f"item ID must be 1..{ITEM_COUNT}")
    _, row = item_position(item_id)
    if row + 1 < ROWS_PER_PAGE:
        return [f"down@0.02:{wait}"]
    next_page_rows = min(ROWS_PER_PAGE, ITEM_COUNT - item_id)
    return [f"right@0.02:{wait}"] + [
        f"up@0.02:{wait}"
    ] * (next_page_rows - 1)


def movement_to(item_id: int, wait: float = 0.45) -> list[str]:
    item_position(item_id)
    movement: list[str] = []
    for current_id in range(1, item_id):
        movement.extend(movement_after(current_id, wait))
    return movement


def artifact_path(prefix: Path, item_id: int) -> Path:
    item_position(item_id)
    return Path(f"{prefix}_id{item_id:02d}.png")


def shop_detail_visible(path: Path) -> bool:
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    detail = frame.crop(
        (
            round(12 * scale_x),
            round(130 * scale_y),
            round(164 * scale_x),
            round(218 * scale_y),
        )
    )
    pixels = list(detail.get_flattened_data())
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 40 <= blue <= 190
        and red < 55
        and green < 75
        and blue > red * 1.5
        and blue > green * 1.4
    )
    white = sum(
        1
        for red, green, blue in pixels
        if red > 70 and green > 70 and blue > 70
    )
    return dark_blue / len(pixels) > 0.75 and white / len(pixels) > 0.005


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def send_steps(keys: list[str]) -> None:
    if not keys:
        return
    run([sys.executable, str(SEND_KEYS), "--send-event", *keys])


def capture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(CAPTURE_WINDOW), str(path)])
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the original complete-secret-shop list, mapping each "
            "page/row directly to item IDs 1..37"
        )
    )
    parser.add_argument(
        "--input-rom", type=Path, default=probe_builder.DEFAULT_INPUT_ROM
    )
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE_ROM
    )
    parser.add_argument(
        "--output-rom", type=Path, default=probe_builder.DEFAULT_OUTPUT_ROM
    )
    parser.add_argument("--runtime-name")
    parser.add_argument(
        "--capture-prefix",
        type=Path,
    )
    parser.add_argument("--start-item", type=int, default=1)
    parser.add_argument("--end-item", type=int, default=ITEM_COUNT)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--movement-delay", type=float, default=0.45)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    item_position(args.start_item)
    item_position(args.end_item)
    if args.start_item > args.end_item:
        raise ValueError("--start-item must not exceed --end-item")
    if args.movement_delay < 0:
        raise ValueError("--movement-delay must be non-negative")

    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = probe_builder.patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    runtime_name = args.runtime_name or f"item-shop-{checksum:04x}"
    capture_prefix = args.capture_prefix or (
        ROOT / f"captures/run/{checksum:04x}_item_shop"
    )

    planned = [
        (item_id, *item_position(item_id), artifact_path(capture_prefix, item_id))
        for item_id in range(args.start_item, args.end_item + 1)
    ]
    if args.dry_run:
        print(f"probe {checksum:04X}: {args.output_rom}")
        print("entry movement:", " ".join(movement_to(args.start_item, args.movement_delay)))
        for item_id, page, row, path in planned:
            print(
                f"item {item_id:02d} {production_builder.ITEM_NAME_PATCHES[item_id - 1]} "
                f"page {page + 1} row {row + 1}: {path}"
            )
        return 0

    entry_path = Path(f"{capture_prefix}_entry.png")
    try:
        run(
            [
                sys.executable,
                str(RUN_SEQUENCE),
                "shop-buy-list",
                "--rom",
                str(args.output_rom),
                "--runtime-name",
                runtime_name,
                "--replace-existing",
                "--send-event",
                "--initial-delay",
                str(args.initial_delay),
            ]
        )
        capture(entry_path)
        if not shop_detail_visible(entry_path):
            raise RuntimeError(
                "complete-item shop detail panel was not detected; no row was accepted"
            )
        send_steps(movement_to(args.start_item, args.movement_delay))

        captured = 0
        skipped = 0
        for item_id, page, row, path in planned:
            if path.exists() and not args.overwrite:
                print(
                    f"skip item {item_id:02d}: existing capture {path}", flush=True
                )
                skipped += 1
            else:
                capture(path)
                if not shop_detail_visible(path):
                    raise RuntimeError(
                        f"shop detail panel missing for item {item_id:02d} "
                        f"at page {page + 1}, row {row + 1}"
                    )
                print(
                    f"captured item {item_id:02d} "
                    f"{production_builder.ITEM_NAME_PATCHES[item_id - 1]}: {path}",
                    flush=True,
                )
                captured += 1
            if item_id < args.end_item:
                send_steps(movement_after(item_id, args.movement_delay))
        print(f"captured {captured}, resumed {skipped}; visual review still required")
    finally:
        terminate_blastem_processes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
