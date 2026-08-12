#!/usr/bin/env python3
# ruff: noqa: E402
"""Build a clean Scenario 1 GST by selecting NEW GAME on isolated Xvfb.

The runner never imports SRAM or a prior save state.  It retains the title,
NEW GAME menu, name-entry transition, Scenario 1 preparation screen, and GST,
then locks Keith, Lester, and Jessica to their expected fresh-game progress.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as parallel
from tools.run_sequential_campaign_revalidation import state_snapshot


PROFILES = ("pure", "normal", "hard")
EXPECTED_ROSTER = {
    7: {"class_id": 0x06, "level": 10, "experience": 5},
    9: {"class_id": 0x07, "level": 10, "experience": 15},
    10: {"class_id": 0x03, "level": 10, "experience": 0},
}
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/fresh_s1_runtime_seeds"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/fresh_s1_runtime"
NEW_GAME_PANEL_BOX = (108, 145, 212, 199)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def valid_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError("SHA-256 must be 64 hexadecimal characters")
    return normalized


def verify_rom_hash(rom: Path, expected: str | None) -> str:
    actual = sha256(rom)
    if expected is not None and actual != expected:
        raise ValueError(f"ROM SHA-256 {actual} != expected {expected}")
    return actual


def new_game_menu_visible(path: Path) -> bool:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        return False
    pixels = list(image.crop(NEW_GAME_PANEL_BOX).getdata())
    gold = sum(
        1
        for red, green, blue in pixels
        if red > 100 and green > 70 and blue < 90 and red > blue * 1.4
    ) / len(pixels)
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 40 <= blue <= 180
        and red < 45
        and green < 65
        and blue > red * 2
        and blue > green * 1.5
    ) / len(pixels)
    white = sum(
        1 for red, green, blue in pixels if red > 150 and green > 150 and blue > 150
    ) / len(pixels)
    return gold > 0.025 and dark_blue > 0.70 and white > 0.015


def clean_title_visible(path: Path) -> bool:
    return sequence.title_screen_visible(path) and not new_game_menu_visible(path)


def locked_roster(snapshot: dict[str, object]) -> dict[int, dict[str, int]]:
    if snapshot.get("scenario") != 1:
        raise ValueError(f"fresh seed scenario is {snapshot.get('scenario')}, not 1")
    selected: dict[int, dict[str, int]] = {}
    for row in snapshot.get("commanders", []):
        commander_id = int(row["commander_id"])
        if commander_id not in EXPECTED_ROSTER:
            continue
        if commander_id in selected:
            raise ValueError(f"duplicate commander {commander_id} in fresh seed")
        selected[commander_id] = {key: int(value) for key, value in row.items()}
    missing = sorted(set(EXPECTED_ROSTER) - set(selected))
    if missing:
        raise ValueError(
            "fresh seed is missing commander IDs "
            + ", ".join(str(value) for value in missing)
        )
    for commander_id, expected in EXPECTED_ROSTER.items():
        row = selected[commander_id]
        for key, value in expected.items():
            if row[key] != value:
                raise ValueError(
                    f"commander {commander_id} {key}={row[key]}, expected {value}"
                )
    return selected


def validate_clean_targets(output: Path, runtime_home: Path) -> None:
    existing = [path for path in (output, runtime_home) if path.exists()]
    if existing:
        raise FileExistsError(
            "fresh seed requires absent output/runtime targets: "
            + ", ".join(str(path) for path in existing)
        )


def build_plan(
    *,
    profile: str,
    rom: Path,
    rom_sha256: str,
    output: Path,
    runtime_home: Path,
    display: str,
    run_id: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "pass",
        "command": "plan",
        "profile": profile,
        "run_id": run_id,
        "rom": {"path": report_path(rom), "sha256": rom_sha256},
        "virtual_display": display,
        "output": report_path(output),
        "isolation": {
            "runtime_home": report_path(runtime_home),
            "runtime_must_not_exist_before_run": True,
            "manual_sram_seed": None,
            "manual_gst_seed": None,
        },
        "required_evidence": [
            "title",
            "new_game_menu",
            "name_entry_after_new_game_selection",
            "scenario_1_preparation",
            "scenario_1_gst",
        ],
        "expected_roster": EXPECTED_ROSTER,
    }


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {
        "path": report_path(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
    }


def retain_capture(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def reach_title(
    recorder: preparation.RuntimeRecorder,
    *,
    max_start_presses: int,
) -> tuple[Path, int]:
    for attempt in range(max_start_presses + 1):
        capture = recorder.capture(f"transitions/title_{attempt:02d}.png")
        if clean_title_visible(capture):
            return retain_capture(capture, recorder.output / "title.png"), attempt
        if attempt < max_start_presses:
            recorder.send(["start"], delay=1.5)
    raise RuntimeError(
        f"title was not detected after {max_start_presses} START presses"
    )


def wait_for_new_game_menu(
    recorder: preparation.RuntimeRecorder,
    *,
    max_checks: int,
    delay: float,
) -> tuple[Path, int]:
    for check in range(max_checks + 1):
        capture = recorder.capture(f"transitions/new_game_menu_{check:02d}.png")
        if new_game_menu_visible(capture):
            return (
                retain_capture(capture, recorder.output / "new_game_menu.png"),
                check,
            )
        if check < max_checks:
            time.sleep(delay)
    raise RuntimeError(f"NEW GAME menu was not detected after {max_checks} checks")


def launch_command(args: argparse.Namespace, runtime_name: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/run_blastem_sequence.py"),
        "launch-only",
        "--rom",
        str(args.rom),
        "--runtime-name",
        runtime_name,
        "--runtime-root",
        str(args.runtime_root),
        "--initial-delay",
        str(args.initial_delay),
        "--virtual-display",
        args.display,
        "--replace-existing",
        "--send-event",
    ]


def advance_to_preparation(
    recorder: preparation.RuntimeRecorder,
    args: argparse.Namespace,
) -> None:
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-prep",
            "--rom",
            str(args.rom),
            "--no-launch",
            "--virtual-display",
            args.display,
            "--send-event",
            "--confirmation-delay",
            str(args.confirmation_delay),
            "--max-confirmations",
            str(args.max_confirmations),
            "--capture-prefix",
            str(recorder.output / "transitions/preparation.png"),
        ]
    )


def run(args: argparse.Namespace, plan: dict[str, object]) -> dict[str, object]:
    validate_clean_targets(args.output, args.runtime_home)
    xvfb = parallel.start_xvfb(args.xvfb, args.xvfb_library_path, args.display)
    args.output.mkdir(parents=True)
    recorder = preparation.RuntimeRecorder(
        args.output,
        args.display,
        args.runtime_home,
    )
    started = time.monotonic()
    report = {
        **plan,
        "command": "run",
        "status": "running",
        "fresh_title_to_new_game": True,
        "isolation": {
            **plan["isolation"],
            "output_existed_before_run": False,
            "runtime_existed_before_run": False,
            "empty_runtime_verified": True,
        },
    }
    try:
        recorder.run_command(launch_command(args, args.runtime_name))
        title, title_start_presses = reach_title(
            recorder, max_start_presses=args.max_title_start_presses
        )
        report["title"] = {
            **image_report(title),
            "start_presses_to_reach": title_start_presses,
            "detector_passed": True,
        }

        recorder.send(["start"], delay=0.8)
        new_game, new_game_checks = wait_for_new_game_menu(
            recorder,
            max_checks=args.max_new_game_checks,
            delay=args.new_game_check_delay,
        )
        report["new_game_menu"] = {
            **image_report(new_game),
            "checks_after_title_start": new_game_checks,
            "detector_passed": True,
        }

        recorder.send(["c"], delay=0.8)
        name_entry = recorder.capture("name_entry_after_new_game_selection.png")
        if new_game_menu_visible(name_entry):
            raise RuntimeError("NEW GAME confirmation did not leave the main menu")
        report["name_entry_after_new_game_selection"] = {
            **image_report(name_entry),
            "new_game_menu_absent": True,
        }

        recorder.send(
            ["c:0.8", "c:1.4", "s@3.0:0.8", "c:0.8"],
            batched=True,
        )
        advance_to_preparation(recorder, args)
        preparation_capture = recorder.capture("scenario_1_preparation.png")
        if not preparation.preparation_screen_visible(preparation_capture):
            raise RuntimeError("Scenario 1 preparation screen detector failed")
        gst = recorder.save_gst("fresh_s1_preparation.gst")
        snapshot = state_snapshot(gst)
        roster = locked_roster(snapshot)
        sram_files = sorted(args.runtime_home.rglob("save.sram"))
        report.update(
            {
                "scenario_1_preparation": {
                    **image_report(preparation_capture),
                    "detector_passed": True,
                },
                "scenario_1_gst": {
                    "path": report_path(gst),
                    "sha256": sha256(gst),
                },
                "snapshot": snapshot,
                "target_roster": roster,
                "isolation": {
                    **report["isolation"],
                    "runtime_sram_after_run": [
                        {"path": report_path(path), "sha256": sha256(path)}
                        for path in sram_files
                    ],
                },
                "actions": recorder.actions,
                "captures": recorder.captures,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "status": "pass",
            }
        )
    except Exception as exc:
        report.update(
            {
                "status": "fail",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "actions": recorder.actions,
                "captures": recorder.captures,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
    finally:
        try:
            sequence.terminate_blastem_processes(display=args.display)
        finally:
            parallel.stop_process(xvfb)
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--expected-rom-sha256", type=valid_sha256)
    parser.add_argument("--display", default=":795")
    parser.add_argument("--run-id", type=preparation.validate_run_id, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--initial-delay", type=float, default=6.0)
    parser.add_argument("--max-title-start-presses", type=int, default=3)
    parser.add_argument("--max-new-game-checks", type=int, default=8)
    parser.add_argument("--new-game-check-delay", type=float, default=0.25)
    parser.add_argument("--max-confirmations", type=int, default=80)
    parser.add_argument("--confirmation-delay", type=float, default=0.8)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    parallel.display_number(args.display)
    if not args.rom.is_file():
        raise FileNotFoundError(args.rom)
    if args.initial_delay < 0 or args.new_game_check_delay < 0:
        parser.error("delays must be nonnegative")
    if args.max_title_start_presses < 0 or args.max_new_game_checks < 0:
        parser.error("screen-detection limits must be nonnegative")
    if args.max_confirmations < 1 or args.confirmation_delay < 0:
        parser.error("preparation detector limits are invalid")
    args.output = args.output_root / args.profile / args.run_id
    args.runtime_name = f"fresh-s1-{args.profile}-{args.run_id}"
    args.runtime_home = args.runtime_root / args.runtime_name
    rom_hash = verify_rom_hash(args.rom, args.expected_rom_sha256)
    plan = build_plan(
        profile=args.profile,
        rom=args.rom,
        rom_sha256=rom_hash,
        output=args.output,
        runtime_home=args.runtime_home,
        display=args.display,
        run_id=args.run_id,
    )
    if args.command == "plan":
        report = plan
    else:
        for label, path in (
            ("Xvfb", args.xvfb),
            ("Xvfb library path", args.xvfb_library_path),
        ):
            if not path.exists():
                raise FileNotFoundError(f"{label} does not exist: {path}")
        report = run(args, plan)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
