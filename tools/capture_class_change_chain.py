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
from tools import capture_class_change_transition as capture_tool
from tools.class_change_data import ClassTransition, read_class_change_chain
from tools.class_change_inventory import (
    live_verified_combinations,
    transition_signature,
)


def pending_transitions(
    source: bytes,
    commander_id: int,
    include_verified: bool = False,
) -> list[ClassTransition]:
    transitions = read_class_change_chain(source, commander_id)
    if include_verified:
        return transitions
    verified = live_verified_combinations(source)
    return [
        transition
        for transition in transitions
        if transition_signature(transition) not in verified
    ]


def expected_capture_paths(
    checksum: int,
    commander_id: int,
    current_class: int,
    candidate_count: int,
) -> list[Path]:
    prefix = ROOT / "captures/run" / capture_tool.artifact_stem(
        checksum, commander_id, current_class
    )
    return [
        Path(f"{prefix}_trigger.png"),
        *[
            Path(f"{prefix}_candidate{index}.png")
            for index in range(1, candidate_count + 1)
        ],
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture every pending unique class-change transition for one "
            "source commander, resuming from complete capture sets"
        )
    )
    parser.add_argument("--commander-id", type=int, required=True)
    parser.add_argument("--runtime-record-index", type=int, default=0)
    parser.add_argument(
        "--input-rom", type=Path, default=probe_builder.DEFAULT_INPUT_ROM
    )
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE_ROM
    )
    parser.add_argument("--include-verified", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--max-confirmations", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    transitions = pending_transitions(
        source, args.commander_id, include_verified=args.include_verified
    )
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        transitions = transitions[: args.limit]
    print(
        f"commander {args.commander_id}: {len(transitions)} transition(s) "
        "selected",
        flush=True,
    )

    completed = 0
    skipped = 0
    for transition in transitions:
        output_rom = (
            ROOT
            / "roms/builds"
            / (
                "Langrisser II (Korean Class Change Auto Probe "
                f"C{args.commander_id}-S{transition.current_class:02X}).md"
            )
        )
        checksum, candidates = capture_tool.build_probe(
            args.input_rom,
            args.source_rom,
            output_rom,
            args.commander_id,
            transition.current_class,
            args.runtime_record_index,
        )
        paths = expected_capture_paths(
            checksum,
            args.commander_id,
            transition.current_class,
            len(candidates),
        )
        if not args.overwrite and all(path.is_file() for path in paths):
            print(
                f"skip 0x{transition.current_class:02X}: complete capture set",
                flush=True,
            )
            skipped += 1
            continue
        command = [
            sys.executable,
            str(ROOT / "tools/capture_class_change_transition.py"),
            "--commander-id",
            str(args.commander_id),
            "--current-class",
            f"0x{transition.current_class:02X}",
            "--runtime-record-index",
            str(args.runtime_record_index),
            "--input-rom",
            str(args.input_rom),
            "--source-rom",
            str(args.source_rom),
            "--output-rom",
            str(output_rom),
            "--initial-delay",
            str(args.initial_delay),
            "--confirmation-delay",
            str(args.confirmation_delay),
            "--max-confirmations",
            str(args.max_confirmations),
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        completed += 1

    print(f"completed {completed}, resumed {skipped}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
