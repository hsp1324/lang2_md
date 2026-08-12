#!/usr/bin/env python3
# ruff: noqa: E402
"""Exercise a Rune Stone while retaining the production join-EXP resume.

The ordinary forced class-change probe replaces the production operand at
0x014D0C with a diagnostic post-apply wrapper.  That is appropriate for its
LV1 application proof, but it cannot reveal whether the release join-EXP
wrapper runs again after a later Rune Stone.  This focused probe keeps the
release operand byte-exact, clears the commander's release marker before the
stock level-up handler, consumes a real Rune Stone, and requires the selected
tier-2 class to remain at the stock LV1/EXP0 result in BlastEm GST.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import blastem_display
from tools import build_class_change_probe_rom as probe_builder
from tools import capture_class_change_application as application
from tools.run_blastem_sequence import RUNTIME_ROOT, terminate_blastem_processes
from tools.run_runestone_restart_matrix import runtime_join_marker_report
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


DEFAULT_ROM = RELEASE_ROM_PATHS["pure"]
DEFAULT_ROM_SHA256 = RELEASE_ROM_SHA256["pure"]
DEFAULT_OUTPUT = ROOT / "tmp/production-runestone-resume-probe"
RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"

# One naturally reachable class at each requested pre-Runestone tier.  The
# stock Rune Stone handler replaces all of these lookup keys with the first
# current-class row in the owner's release chain.
CASES: dict[str, dict[str, object]] = {
    "keith": {
        "commander_id": 7,
        "classes": {3: 0x0B, 4: 0x17, 5: 0x24},
        "selected_class": 0x04,
        "marker_address": 0x00403FE7,
    },
    "lester": {
        "commander_id": 9,
        "classes": {3: 0x0C, 4: 0x1B, 5: 0x2A},
        "selected_class": 0x05,
        "marker_address": 0x00403FE9,
    },
    "jessica": {
        "commander_id": 10,
        "classes": {3: 0x11, 4: 0x16, 5: 0x26},
        "selected_class": 0x08,
        "marker_address": 0x00403FEB,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def marker_clear_instruction(address: int) -> bytes:
    # CLR.B absolute-long.  This is diagnostic setup, not production code.
    return bytes.fromhex("42 39") + address.to_bytes(4, "big")


def unscoped_fixed_grant_prediction(
    rom: bytes,
    *,
    commander_id: int,
    selected_class: int,
) -> dict[str, int]:
    """Model an erroneous regrant using the current fixed-raw policy."""
    raw_experience = builder.join_raw_experience(commander_id)
    gauge = probe_builder.class_change_experience(rom, selected_class)
    if gauge <= 0:
        raise ValueError(
            f"class 0x{selected_class:02X} has invalid EXP gauge {gauge}"
        )
    gained_levels, residual = divmod(raw_experience, gauge)
    return {
        "class_id": selected_class,
        "commander_id": commander_id,
        "level": 1 + gained_levels,
        "experience": residual,
        "fixed_raw_experience": raw_experience,
        "class_experience_gauge": gauge,
    }


def build_probe(
    rom_path: Path,
    output_path: Path,
    *,
    character: str,
    tier: int,
    expected_sha256: str | None,
) -> dict[str, object]:
    if character not in CASES:
        raise ValueError(f"unknown character {character!r}")
    definition = CASES[character]
    classes = dict(definition["classes"])
    if tier not in classes:
        raise ValueError(f"{character} probe tier must be 3, 4, or 5")

    source = rom_path.read_bytes()
    actual_sha256 = hashlib.sha256(source).hexdigest()
    if len(source) != 0x400000:
        raise ValueError("release probe input must be exactly 4 MiB")
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"release ROM SHA-256 mismatch: {actual_sha256} != {expected_sha256}"
        )

    resume_offset = probe_builder.CLASS_CHANGE_RESUME_OPERAND
    production_resume = source[resume_offset : resume_offset + 4]
    expected_resume = builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER.to_bytes(4, "big")
    if production_resume != expected_resume:
        raise ValueError(
            "input does not use the production join-EXP resume: "
            f"{production_resume.hex()} != {expected_resume.hex()}"
        )

    commander_id = int(definition["commander_id"])
    current_class = int(classes[tier])
    probe = bytearray(source)
    probe_builder.patch_probe(
        probe,
        source,
        commander_id=commander_id,
        current_class=current_class,
        runtime_record_index=0,
        enable_start_menu_probe=False,
        force_runtime_context=True,
        restore_commander_id=commander_id,
        runestone_restart=True,
    )

    # The forced fixture runs on Scenario 1's map.  Restore the stock LV10
    # compare exactly as the established Rune Stone matrix does; otherwise
    # the release pre-join visibility guard correctly rejects Keith/Lester/
    # Jessica before this diagnostic can reach its candidate screen.  This
    # bypass is independent of the post-selection resume under audit.
    visibility_hook = builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK
    installed_visibility = (
        bytes.fromhex("4E B9")
        + builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD.to_bytes(4, "big")
    )
    if probe[
        visibility_hook : visibility_hook + len(installed_visibility)
    ] != installed_visibility:
        raise ValueError("release join visibility guard is not installed")
    probe[
        visibility_hook : visibility_hook
        + len(builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL)
    ] = builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL

    original_wrapper = probe_builder.wrapper_code(
        runtime_record_index=0,
        expected_class=current_class,
        forced_commander_id=commander_id,
        probe_experience=probe_builder.class_change_experience(
            source, current_class
        ),
        equipped_item=probe_builder.RUNESTONE_ITEM_ID,
    )
    wrapper = marker_clear_instruction(int(definition["marker_address"]))
    wrapper += original_wrapper
    wrapper_start = probe_builder.PROBE_WRAPPER
    wrapper_end = wrapper_start + len(wrapper)
    if wrapper_end > probe_builder.POST_APPLY_WRAPPER:
        raise ValueError("marker setup no longer fits before the next probe area")
    if probe[wrapper_start : wrapper_start + len(original_wrapper)] != (
        original_wrapper
    ):
        raise ValueError("forced-context wrapper differs before marker setup")
    if any(
        value != 0xFF
        for value in probe[
            wrapper_start + len(original_wrapper) : wrapper_end
        ]
    ):
        raise ValueError("marker setup extension area is occupied")
    probe[wrapper_start:wrapper_end] = wrapper

    # Restore the exact release continuation that the ordinary diagnostic
    # intentionally replaced.  The unused post-apply bytes remain diagnostic
    # data but are unreachable from this probe.
    probe[resume_offset : resume_offset + 4] = production_resume
    checksum = builder.update_md_checksum(probe)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(probe)
    return {
        "input": relative(rom_path),
        "input_sha256": actual_sha256,
        "probe": relative(output_path),
        "probe_sha256": hashlib.sha256(probe).hexdigest(),
        "md_checksum": f"{checksum:04X}",
        "character": character,
        "commander_id": commander_id,
        "tier": tier,
        "current_class": f"0x{current_class:02X}",
        "selected_class": f"0x{int(definition['selected_class']):02X}",
        "marker_address": f"0x{int(definition['marker_address']):08X}",
        "marker_setup": "clear_before_stock_level_up_handler",
        "forced_fixture_visibility": "stock_compare_restored_for_scenario1",
        "class_change_resume_operand": {
            "offset": f"0x{resume_offset:06X}",
            "target": f"0x{int.from_bytes(production_resume, 'big'):06X}",
            "preserved_from_release": True,
        },
    }


def quicksave(runtime_name: str) -> Path:
    states = list((RUNTIME_ROOT / runtime_name).rglob("quicksave.gst"))
    if len(states) != 1:
        raise RuntimeError(
            f"expected one quicksave.gst for {runtime_name}, found {len(states)}"
        )
    return states[0]


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output / args.character / f"tier{args.tier}"
    output.mkdir(parents=True, exist_ok=False)
    probe_path = output / "probe.md"
    build = build_probe(
        args.rom,
        probe_path,
        character=args.character,
        tier=args.tier,
        expected_sha256=args.expected_sha256,
    )
    runtime_name = args.runtime_name or (
        f"production-runestone-resume-{args.character}-tier{args.tier}"
    )
    definition = CASES[args.character]
    captures: list[Path] = []
    started = time.monotonic()

    if blastem_display.configure_display(args):
        application.XLIB_ONLY_CAPTURE = True
    try:
        command = [
            sys.executable,
            str(RUN_SEQUENCE),
            "first-turn-dialogue",
            "--rom",
            str(probe_path),
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
            *blastem_display.sequence_display_args(args.desktop_display),
        ]
        subprocess.run(command, cwd=ROOT, check=True)

        trigger = output / "trigger.png"
        application.capture(trigger)
        captures.append(trigger)
        prefix = output / "candidate"
        candidate = application.advance_to_candidate_surface(
            prefix,
            max_advances=args.max_candidate_advances,
        )
        captures.append(candidate)

        # Select the first visible row through the real class-choice UI.  A
        # held confirm also advances the immediately following stock notices.
        application.send_keys(f"c:{args.apply_hold}")
        after_apply = output / "after_apply.png"
        application.capture(after_apply)
        captures.append(after_apply)

        observations: list[dict[str, object]] = []
        previous_progress: tuple[int, int, int, int] | None = None
        stable = 0
        for step in range(1, args.max_post_apply_confirmations + 1):
            application.send_keys("save:0.4")
            state_path = quicksave(runtime_name)
            state = state_path.read_bytes()
            progress = application.runtime_progress(state, 0)
            item = application.runtime_equipped_item(state, 0)
            observations.append(
                {
                    "step": step,
                    "class_id": f"0x{progress[0]:02X}",
                    "commander_id": progress[1],
                    "level": progress[2],
                    "experience": progress[3],
                    "equipped_item": f"0x{item:02X}",
                }
            )
            if progress == previous_progress and item == 0:
                stable += 1
            else:
                stable = 0
            previous_progress = progress
            if stable >= 2:
                break
            application.send_keys(f"c:{args.post_apply_delay}")
        else:
            raise RuntimeError("post-apply runtime state did not stabilize")

        final_state = quicksave(runtime_name)
        retained_gst = output / "final.gst"
        shutil.copy2(final_state, retained_gst)
        final_capture = output / "final.png"
        application.capture(final_capture)
        captures.append(final_capture)
        progress = application.runtime_progress(final_state.read_bytes(), 0)
        equipped_item = application.runtime_equipped_item(
            final_state.read_bytes(), 0
        )
        prediction = unscoped_fixed_grant_prediction(
            args.rom.read_bytes(),
            commander_id=int(definition["commander_id"]),
            selected_class=int(definition["selected_class"]),
        )
        predicted = (
            prediction["class_id"],
            prediction["commander_id"],
            prediction["level"],
            prediction["experience"],
        )
        expected_stock = (
            int(definition["selected_class"]),
            int(definition["commander_id"]),
            1,
            0,
        )
        # BlastEm flushes cartridge SRAM when the emulator process exits.
        # Retain every screen/GST first, then stop only this Xvfb-owned process
        # before binding the consumed marker byte into the report.
        terminate_blastem_processes(display=os.environ.get("DISPLAY"))
        runtime_marker = runtime_join_marker_report(
            RUNTIME_ROOT / runtime_name,
            int(definition["commander_id"]),
        )
        if (
            progress == expected_stock
            and equipped_item == 0
            and runtime_marker["status"] == "pass"
        ):
            status = "stock_restart_preserved"
        elif progress == predicted and equipped_item == 0:
            status = "reproduced_unscoped_fixed_join_grant_after_runestone"
        else:
            status = "production_resume_observed_other_state"
        report = {
            "schema_version": 1,
            "status": status,
            "build": build,
            "runtime": {
                "display": os.environ.get("DISPLAY"),
                "runtime_name": runtime_name,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "expected_stock_restart_state": {
                    "class_id": build["selected_class"],
                    "commander_id": int(definition["commander_id"]),
                    "level": 1,
                    "experience": 0,
                    "equipped_item": "0x00",
                },
                "predicted_unscoped_fixed_join_grant_state": {
                    "class_id": f"0x{predicted[0]:02X}",
                    "commander_id": predicted[1],
                    "level": predicted[2],
                    "experience": predicted[3],
                    "equipped_item": "0x00",
                    "fixed_raw_experience": prediction[
                        "fixed_raw_experience"
                    ],
                    "class_experience_gauge": prediction[
                        "class_experience_gauge"
                    ],
                },
                "observed": {
                    "class_id": f"0x{progress[0]:02X}",
                    "commander_id": progress[1],
                    "level": progress[2],
                    "experience": progress[3],
                    "equipped_item": f"0x{equipped_item:02X}",
                },
                "observations": observations,
                "join_marker": runtime_marker,
                "gst": relative(retained_gst),
                "gst_sha256": sha256(retained_gst),
            },
            "captures": [
                {"path": relative(path), "sha256": sha256(path)}
                for path in captures
            ],
        }
        summary = output / "summary.json"
        summary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        terminate_blastem_processes(display=os.environ.get("DISPLAY"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retain the production join-EXP resume during Rune Stone use"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--expected-sha256", default=DEFAULT_ROM_SHA256)
    parser.add_argument("--character", choices=tuple(CASES), required=True)
    parser.add_argument("--tier", type=int, choices=(3, 4, 5), required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runtime-name")
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument("--max-confirmations", type=int, default=40)
    parser.add_argument("--max-candidate-advances", type=int, default=8)
    parser.add_argument("--apply-hold", type=float, default=5.0)
    parser.add_argument("--post-apply-delay", type=float, default=0.9)
    parser.add_argument("--max-post-apply-confirmations", type=int, default=24)
    blastem_display.add_display_arguments(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_probe(args)
    observed = report["runtime"]["observed"]
    print(
        f"{report['status']}: {args.character} tier {args.tier} -> "
        f"{observed['class_id']} LV{observed['level']} "
        f"EXP{observed['experience']}"
    )
    return 0 if report["status"] == "stock_restart_preserved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
