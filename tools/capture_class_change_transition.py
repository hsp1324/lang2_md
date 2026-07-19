#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_class_change_probe_rom as probe_builder
from tools.run_blastem_sequence import terminate_blastem_processes


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"


def artifact_stem(checksum: int, commander_id: int, current_class: int) -> str:
    return f"{checksum:04x}_c{commander_id}_s{current_class:02x}"


def build_probe(
    input_rom: Path,
    source_rom: Path,
    output_rom: Path,
    commander_id: int,
    current_class: int,
    runtime_record_index: int,
) -> tuple[int, tuple[int, ...]]:
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
    )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    return checksum, transition.candidates


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
            "Build one ignored class-change screen probe, boot it from a clean "
            "runtime, and capture every source-derived candidate row"
        )
    )
    parser.add_argument("--commander-id", type=int, required=True)
    parser.add_argument(
        "--current-class", type=lambda value: int(value, 0), required=True
    )
    parser.add_argument("--runtime-record-index", type=int, default=0)
    parser.add_argument(
        "--input-rom", type=Path, default=probe_builder.DEFAULT_INPUT_ROM
    )
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE_ROM
    )
    parser.add_argument("--output-rom", type=Path)
    parser.add_argument("--runtime-name")
    parser.add_argument("--capture-prefix", type=Path)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--max-confirmations", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_rom = args.output_rom or (
        ROOT
        / "roms/builds"
        / (
            "Langrisser II (Korean Class Change Auto Probe "
            f"C{args.commander_id}-S{args.current_class:02X}).md"
        )
    )
    checksum, candidates = build_probe(
        args.input_rom,
        args.source_rom,
        output_rom,
        args.commander_id,
        args.current_class,
        args.runtime_record_index,
    )
    stem = artifact_stem(checksum, args.commander_id, args.current_class)
    capture_prefix = args.capture_prefix or ROOT / "captures/run" / stem
    runtime_name = args.runtime_name or f"class-change-auto-{stem}"

    print(
        f"probe {checksum:04X}: commander {args.commander_id}, "
        f"class 0x{args.current_class:02X}, candidates "
        + "/".join(f"0x{candidate:02X}" for candidate in candidates)
    )
    try:
        run(
            [
                sys.executable,
                str(RUN_SEQUENCE),
                "battle-command",
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
        send_keys("b:0.8", "b:0.8", "start:2.0")
        capture(Path(f"{capture_prefix}_trigger.png"))
        send_keys("c:1.5")
        for index in range(len(candidates)):
            if index:
                send_keys("down:1.0")
            path = Path(f"{capture_prefix}_candidate{index + 1}.png")
            capture(path)
            print(path)
    finally:
        terminate_blastem_processes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
