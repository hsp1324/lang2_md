#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_class_change_probe_rom as probe_builder
from tools.run_blastem_sequence import (
    GST_WORK_RAM_FILE_OFFSET,
    RUNTIME_ROOT,
    terminate_blastem_processes,
)


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"


def artifact_stem(checksum: int, commander_id: int, current_class: int) -> str:
    return f"{checksum:04x}_c{commander_id}_s{current_class:02x}_forced_apply"


def runtime_progress(gst: bytes, runtime_record_index: int) -> tuple[int, int, int, int]:
    record = probe_builder.runtime_record_address(runtime_record_index) & 0xFFFF
    offset = GST_WORK_RAM_FILE_OFFSET + record
    end = offset + probe_builder.RUNTIME_RECORD_SIZE
    if len(gst) < end:
        raise ValueError("GST is too short to contain the runtime record")
    data = gst[offset:end]
    return (
        data[probe_builder.ELWIN_CLASS_OFFSET],
        data[0x01],
        data[probe_builder.ELWIN_LEVEL_OFFSET],
        data[probe_builder.ELWIN_EXPERIENCE_OFFSET],
    )


def build_probe(
    input_rom: Path,
    source_rom: Path,
    output_rom: Path,
    commander_id: int,
    current_class: int,
    runtime_record_index: int,
    restore_commander_id: int,
) -> tuple[int, int]:
    source = source_rom.read_bytes()
    probe = bytearray(input_rom.read_bytes())
    transition = probe_builder.selected_transition(
        source, commander_id, current_class
    )
    checksum = probe_builder.patch_probe(
        probe,
        source,
        commander_id=commander_id,
        current_class=current_class,
        runtime_record_index=runtime_record_index,
        enable_start_menu_probe=False,
        force_runtime_context=True,
        restore_commander_id=restore_commander_id,
    )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    return checksum, transition.candidates[0]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def send_keys(*keys: str) -> None:
    run([sys.executable, str(SEND_KEYS), "--send-event", *keys])


def capture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(CAPTURE_WINDOW), str(path)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply one source class-change transition through the stock end-turn "
            "handler, restore the Scenario 1 runtime identity, and verify the GST"
        )
    )
    parser.add_argument("--commander-id", type=int, required=True)
    parser.add_argument(
        "--current-class", type=lambda value: int(value, 0), required=True
    )
    parser.add_argument("--runtime-record-index", type=int, default=0)
    parser.add_argument("--restore-commander-id", type=int, default=1)
    parser.add_argument(
        "--input-rom", type=Path, default=probe_builder.DEFAULT_INPUT_ROM
    )
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE_ROM
    )
    parser.add_argument("--output-rom", type=Path)
    parser.add_argument("--runtime-name")
    parser.add_argument("--capture-prefix", type=Path)
    parser.add_argument("--gst-output", type=Path)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--max-confirmations", type=int, default=40)
    parser.add_argument("--stability-delay", type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_rom = args.output_rom or (
        ROOT
        / "roms/builds"
        / (
            "Langrisser II (Korean Class Change Forced Apply "
            f"C{args.commander_id}-S{args.current_class:02X}).md"
        )
    )
    checksum, expected_class = build_probe(
        args.input_rom,
        args.source_rom,
        output_rom,
        args.commander_id,
        args.current_class,
        args.runtime_record_index,
        args.restore_commander_id,
    )
    stem = artifact_stem(checksum, args.commander_id, args.current_class)
    prefix = args.capture_prefix or ROOT / "captures/run" / stem
    runtime_name = args.runtime_name or f"class-change-{stem}"
    gst_output = args.gst_output or ROOT / "captures/analysis" / f"{stem}.gst"

    print(
        f"probe {checksum:04X}: commander {args.commander_id}, "
        f"class 0x{args.current_class:02X} -> first candidate "
        f"0x{expected_class:02X}",
        flush=True,
    )
    try:
        run(
            [
                sys.executable,
                str(RUN_SEQUENCE),
                "first-turn-dialogue",
                "--rom",
                str(output_rom),
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
        capture(Path(f"{prefix}_trigger.png"))
        send_keys("c:1.5")
        capture(Path(f"{prefix}_candidate1.png"))
        send_keys("c:5.0")
        capture(Path(f"{prefix}_applied_map.png"))
        time.sleep(args.stability_delay)
        capture(Path(f"{prefix}_stable_map.png"))
        send_keys("save:1.0")

        states = list((RUNTIME_ROOT / runtime_name).rglob("quicksave.gst"))
        if len(states) != 1:
            raise RuntimeError(
                f"expected one quicksave.gst for {runtime_name}, found {len(states)}"
            )
        progress = runtime_progress(states[0].read_bytes(), args.runtime_record_index)
        expected = (expected_class, args.restore_commander_id, 1)
        if progress[:3] != expected:
            raise RuntimeError(
                "applied runtime mismatch: expected class/commander/LV "
                f"{expected}, found {progress[:3]} (EXP {progress[3]})"
            )
        gst_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(states[0], gst_output)

        send_keys("c:1.5")
        capture(Path(f"{prefix}_applied_status.png"))
        print(
            f"verified class 0x{progress[0]:02X}, restored commander "
            f"{progress[1]}, LV{progress[2]}, EXP{progress[3]}",
            flush=True,
        )
        print(gst_output, flush=True)
    finally:
        terminate_blastem_processes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
