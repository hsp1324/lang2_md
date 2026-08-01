#!/usr/bin/env python3
"""Exercise all 16 mercenary hire rows with one isolated synthetic commander."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.analyze_preparation_vram_ownership import load_gst, referenced_tiles
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
DEFAULT_ROM = ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.3).md"
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/all_mercenary_hire_probe"
DEFAULT_DISPLAY = ":170"
DEFAULT_SCENARIO = 11
DEFAULT_COMMANDER_ID = 1
DEFAULT_CLASS_ID = 0x4D  # Royal Guard includes slot-5 `가` on the same screen.
HIRE_MASK = 0xFFFF
HIRE_PAGE_SIZE = 3
HISTORICAL_COLLISION_TILE = 0x036D
MERCENARY_ICON_TILE_FIRST = 0x0348
MERCENARY_ICON_TILE_LAST = 0x0387


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plane_hits(state, tile: int) -> list[dict[str, object]]:
    hits = []
    cells = state.plane_width * state.plane_height
    for name, base in state.plane_bases.items():
        for index in range(cells):
            word = int.from_bytes(
                state.vram[base + index * 2:base + index * 2 + 2],
                "big",
            )
            if word & 0x07FF != tile:
                continue
            hits.append(
                {
                    "surface": name,
                    "x": index % state.plane_width,
                    "y": index // state.plane_width,
                    "tile_word": f"0x{word:04X}",
                }
            )
    return hits


def expected_pages() -> list[list[dict[str, object]]]:
    rows = matrix.hire_rows(HIRE_MASK)
    return [
        rows[index:index + HIRE_PAGE_SIZE]
        for index in range(0, len(rows), HIRE_PAGE_SIZE)
    ]


def dynamic_glyph_payloads(rom: bytes) -> set[bytes]:
    payloads = set()
    for offset in range(
        builder.BYTE_UI_DYNAMIC_GLYPH_TABLE,
        builder.BYTE_UI_DYNAMIC_GLYPH_TABLE_LIMIT,
        32,
    ):
        payload = rom[offset:offset + 32]
        if len(payload) == 32 and payload != b"\xFF" * 32:
            payloads.add(payload)
    return payloads


def mercenary_icon_cache_check(state_path: Path, glyphs: set[bytes]) -> dict[str, object]:
    state = load_gst(state_path)
    referenced = referenced_tiles(state)
    cache_tiles = sorted(
        tile
        for tile in referenced
        if MERCENARY_ICON_TILE_FIRST <= tile <= MERCENARY_ICON_TILE_LAST
    )
    glyph_collisions = []
    for tile in cache_tiles:
        payload = state.vram[tile * 32:(tile + 1) * 32]
        if payload in glyphs:
            glyph_collisions.append(f"0x{tile:04X}")
    return {
        "referenced_cache_tiles": [f"0x{tile:04X}" for tile in cache_tiles],
        "dynamic_glyph_collisions": glyph_collisions,
        "pass": bool(cache_tiles) and not glyph_collisions,
    }


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"all-mercenary-{args.run_id}"
    runtime_home = ROOT / "captures/runtime" / runtime_name
    recorder = matrix.RuntimeRecorder(output, args.display, runtime_home)
    xvfb = parallel.start_xvfb(
        args.xvfb,
        args.xvfb_library_path,
        args.display,
    )
    started = time.monotonic()
    try:
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
                "--manual-slot-level", "2",
                "--manual-slot-experience", "0",
                "--manual-slot-class", f"0x{args.class_id:02X}",
                "--manual-slot-hire-mask-or", "0xFFFF",
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
        if args.commander_id not in commander_ids:
            raise RuntimeError(
                f"commander {args.commander_id} is not present in "
                f"Scenario {args.scenario}"
            )
        selection_steps = commander_ids.index(args.commander_id)
        if selection_steps:
            recorder.send(["down"] * selection_steps, delay=0.9)
        recorder.capture_brightest("root.png")
        recorder.send(["c"], delay=1.1)
        first = recorder.capture("transitions/hire_open.png")
        # detect-prep may return one input frame before commander 1 is focused.
        # In that state the first confirm enters the commander roster and the
        # second confirm opens the same hire list.
        if not matrix.hire_screen_visible(first):
            recorder.send(["c"], delay=1.1)
            first = recorder.capture("transitions/hire_open_retry.png")
        if not matrix.hire_screen_visible(first):
            raise RuntimeError("synthetic all-mercenary hire screen did not open")

        pages = expected_pages()
        page_rows = []
        page_states = []
        for page_number, rows in enumerate(pages, 1):
            capture = recorder.capture(f"pages/page_{page_number:02d}.png")
            if not matrix.hire_screen_visible(capture):
                raise RuntimeError(f"hire page {page_number} was not visible")
            state = recorder.save_gst(f"states/page_{page_number:02d}.gst")
            page_states.append(state)
            page_rows.append(
                {
                    "page": page_number,
                    "expected_labels": [row["korean"] for row in rows],
                    "capture": str(capture.relative_to(ROOT)),
                    "capture_sha256": sha256(capture),
                    "gst": str(state.relative_to(ROOT)),
                    "gst_sha256": sha256(state),
                }
            )
            if page_number < len(pages):
                recorder.send(["right"], delay=0.9)

        glyphs = dynamic_glyph_payloads(args.rom.read_bytes())
        icon_checks = [
            mercenary_icon_cache_check(path, glyphs)
            for path in page_states
        ]
        collision_page = 4
        state = load_gst(page_states[collision_page - 1])
        relocated_tile = builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[5]
        old_payload = state.vram[
            HISTORICAL_COLLISION_TILE * 32:
            (HISTORICAL_COLLISION_TILE + 1) * 32
        ]
        relocated_payload = state.vram[
            relocated_tile * 32:(relocated_tile + 1) * 32
        ]
        old_hits = plane_hits(state, HISTORICAL_COLLISION_TILE)
        relocated_hits = plane_hits(state, relocated_tile)
        collision_cleared = all(row["pass"] for row in icon_checks)
        result = {
            "schema_version": 1,
            "status": "pass" if collision_cleared else "fail",
            "rom": {
                "path": str(args.rom.relative_to(ROOT)),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario": args.scenario,
            "synthetic_commander": {
                "commander_id": args.commander_id,
                "class_id": f"0x{args.class_id:02X}",
                "class_korean": matrix.KOREAN_CLASS_LABELS[args.class_id],
                "hire_mask": "0xFFFF",
                "release_rom_modified": False,
            },
            "mercenary_count": sum(len(page) for page in pages),
            "page_count": len(pages),
            "pages": page_rows,
            "mercenary_icon_cache_checks": [
                {"page": index, **row}
                for index, row in enumerate(icon_checks, 1)
            ],
            "slot_5_collision_regression": {
                "page": collision_page,
                "historical_tile": f"0x{HISTORICAL_COLLISION_TILE:04X}",
                "relocated_tile": f"0x{relocated_tile:04X}",
                "historical_payload_sha256": hashlib.sha256(old_payload).hexdigest(),
                "relocated_payload_sha256": hashlib.sha256(relocated_payload).hexdigest(),
                "payloads_are_distinct": old_payload != relocated_payload,
                "historical_tile_plane_hits": old_hits,
                "relocated_tile_plane_hits": relocated_hits,
                "ballista_icon_cell_restored": collision_cleared,
            },
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
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--scenario", type=matrix.validate_scenario, default=DEFAULT_SCENARIO)
    parser.add_argument("--commander-id", type=int, default=DEFAULT_COMMANDER_ID)
    parser.add_argument("--class-id", type=lambda value: int(value, 0), default=DEFAULT_CLASS_ID)
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument("--xvfb-library-path", type=Path, default=parallel.DEFAULT_XVFB_LIBRARY_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    args.output_root = args.output_root.resolve()
    if not 1 <= args.commander_id <= matrix.MANUAL_SLOT_COMMANDER_COUNT:
        parser.error("--commander-id is outside the saved roster")
    if not 0 <= args.class_id < len(matrix.KOREAN_CLASS_LABELS):
        parser.error("--class-id is outside the class table")
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    result = run_probe(args)
    print(
        f"{result['status']}: {result['mercenary_count']} mercenaries on "
        f"{result['page_count']} pages"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
