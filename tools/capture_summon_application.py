#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as production_builder
from tools import build_summon_application_probe_rom as probe_builder
from tools import capture_magic_application as magic_capture
from tools.run_blastem_sequence import (
    battle_command_menu_visible,
    terminate_blastem_processes,
)


SUMMON_COUNT = 8
SUMMON_ROWS_PER_PAGE = 6
SUMMON_MP_COSTS = (5, 10, 12, 10, 8, 10, 10, 15)
SUMMON_CLASS_BASE = 0x8D
MEMBER_RECORD_SIZE = 0x0C
SUMMONED_MEMBER_INDEX = 7
HEIN_X = 13
HEIN_Y = 20


def summon_position(summon_id: int) -> tuple[int, int]:
    if not 0 <= summon_id < SUMMON_COUNT:
        raise ValueError(f"summon ID must be 0..{SUMMON_COUNT - 1}")
    return divmod(summon_id, SUMMON_ROWS_PER_PAGE)


def runtime_member(gst: bytes, member_index: int) -> tuple[int, int, int]:
    member_count = magic_capture.RUNTIME_RECORD_SIZE // MEMBER_RECORD_SIZE
    if not 0 <= member_index < member_count:
        raise ValueError("member index must be 0..7")
    record = (
        magic_capture.RUNTIME_RECORD_BASE
        + magic_capture.HEIN_RUNTIME_RECORD * magic_capture.RUNTIME_RECORD_SIZE
    )
    offset = (
        magic_capture.GST_WORK_RAM_FILE_OFFSET
        + record
        + member_index * MEMBER_RECORD_SIZE
    )
    end = offset + MEMBER_RECORD_SIZE
    if len(gst) < end:
        raise ValueError("GST is too short to contain the runtime member")
    return gst[offset], gst[offset + 6], gst[offset + 7]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture one forced summon list, target selection, application, "
            "and post-effect MP state on Hein"
        )
    )
    parser.add_argument("--summon-id", type=int, default=0)
    parser.add_argument(
        "--target-key",
        action="append",
        choices=("up", "down", "left", "right"),
        default=[],
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
    parser.add_argument("--capture-prefix", type=Path)
    parser.add_argument("--gst-output", type=Path)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--effect-delay", type=float, default=8.0)
    parser.add_argument("--final-confirmations", type=int, default=2)
    parser.add_argument("--max-event-confirmations", type=int, default=12)
    parser.add_argument("--max-confirmations", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    page, row = summon_position(args.summon_id)
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = probe_builder.patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)

    summon_name = production_builder.MAGIC_LIST_NAMES[23 + args.summon_id]
    stem = f"{checksum:04x}_summon_{args.summon_id:02d}"
    prefix = args.capture_prefix or ROOT / "captures/run" / stem
    runtime_name = args.runtime_name or f"summon-apply-{stem}"
    gst_output = args.gst_output or ROOT / "captures/analysis" / f"{stem}.gst"
    print(
        f"probe {checksum:04X}: summon {args.summon_id} {summon_name}, "
        f"page {page + 1}, row {row + 1}",
        flush=True,
    )

    try:
        magic_capture.run(
            [
                sys.executable,
                str(magic_capture.RUN_SEQUENCE),
                "battle-command",
                "--rom",
                str(args.output_rom),
                "--runtime-name",
                runtime_name,
                "--replace-existing",
                "--send-event",
                "--initial-delay",
                str(args.initial_delay),
                "--max-confirmations",
                str(args.max_confirmations),
                "--confirmation-delay",
                str(args.confirmation_delay),
            ]
        )
        magic_capture.send_keys("b:0.5")
        magic_capture.send_steps(magic_capture.movement_specs(0, 3, wait=0.45))
        magic_capture.send_steps(magic_capture.movement_specs(2, 0, wait=0.45))
        magic_capture.send_keys("c:0.7")
        command = magic_capture.capture(Path(f"{prefix}_hein_command.png"))
        if not battle_command_menu_visible(command):
            raise RuntimeError("Hein command menu was not detected")

        magic_capture.send_steps(["down@0.02:0.35"] * 3)
        magic_capture.send_keys("c:0.7")
        magic_capture.send_steps(["right@0.02:0.4"] * page)
        magic_capture.send_steps(["down@0.02:0.35"] * row)
        magic_capture.capture(Path(f"{prefix}_selected.png"))
        magic_capture.send_keys("c:1.0")
        magic_capture.capture(Path(f"{prefix}_target_or_result.png"))

        magic_capture.send_steps(
            [f"{key}@0.02:0.35" for key in args.target_key]
        )
        magic_capture.capture(Path(f"{prefix}_target.png"))
        if args.final_confirmations < 1:
            raise ValueError("final confirmations must be at least one")
        for index in range(args.final_confirmations):
            delay = args.effect_delay if index + 1 == args.final_confirmations else 0.8
            magic_capture.send_keys(f"c@0.12:{delay}")
            if index + 1 < args.final_confirmations:
                magic_capture.capture(
                    Path(f"{prefix}_target_confirmed_{index + 1:02d}.png")
                )

        state, current_mp, max_mp = magic_capture.save_and_read_mp(runtime_name)
        for event_index in range(args.max_event_confirmations):
            if current_mp < max_mp:
                break
            magic_capture.capture(Path(f"{prefix}_event_{event_index + 1:02d}.png"))
            magic_capture.send_keys(f"c@0.12:{args.effect_delay}")
            state, current_mp, max_mp = magic_capture.save_and_read_mp(runtime_name)

        result = magic_capture.capture(Path(f"{prefix}_result.png"))
        for event_index in range(args.max_event_confirmations):
            if not magic_capture.portrait_dialogue_visible(result):
                break
            magic_capture.send_keys(f"c@0.12:{args.effect_delay}")
            result = magic_capture.capture(
                Path(f"{prefix}_post_event_{event_index + 1:02d}.png")
            )
        time.sleep(1.2)
        magic_capture.capture(Path(f"{prefix}_result_stable.png"))
        state, final_current_mp, final_max_mp = magic_capture.save_and_read_mp(
            runtime_name
        )
        expected_mp = max_mp - SUMMON_MP_COSTS[args.summon_id]
        if current_mp != expected_mp or final_current_mp != expected_mp:
            raise RuntimeError(
                f"summon MP mismatch: expected {expected_mp}/{max_mp}, "
                f"saw {current_mp}/{max_mp} then {final_current_mp}/{final_max_mp}"
            )
        summon_class, summon_x, summon_y = runtime_member(
            state.read_bytes(), SUMMONED_MEMBER_INDEX
        )
        expected_class = SUMMON_CLASS_BASE + args.summon_id
        if summon_class != expected_class:
            raise RuntimeError(
                f"summoned class mismatch: expected {expected_class:02X}, "
                f"saw {summon_class:02X}"
            )
        gst_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(state, gst_output)
        magic_capture.send_steps(
            magic_capture.movement_specs(summon_x - HEIN_X, summon_y - HEIN_Y)
        )
        magic_capture.send_keys("c:0.8")
        magic_capture.capture(Path(f"{prefix}_summoned_status.png"))
        print(f"verified post-summon MP {final_current_mp}/{final_max_mp}", flush=True)
        print(
            f"verified summoned class {summon_class:02X} at ({summon_x},{summon_y})",
            flush=True,
        )
        print(gst_output, flush=True)
    finally:
        terminate_blastem_processes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
