#!/usr/bin/env python3
# ruff: noqa: E402
"""Run every Keith/Lester/Jessica Rune Stone restart on release profiles."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import capture_class_change_application as application
from tools import run_blastem_sequence as sequence
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as parallel
from tools.class_change_data import read_class_change_chain
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


DEFAULT_OUTPUT_ROOT = ROOT / "tmp/runestone_restart_matrix"
DEFAULT_ROMS = dict(RELEASE_ROM_PATHS)
DEFAULT_ROM_SHA256 = dict(RELEASE_ROM_SHA256)
CLASS_LABEL_BOX = (65, 103, 120, 163)
SRAM_START_ADDRESS = 0x00400001
SRAM_BYTES = 0x2000

# One reachable class on the first route at each requested current tier. The
# stock Rune Stone handler must restart all of them from the first chain row.
CASES: dict[str, dict[str, object]] = {
    "keith": {
        "commander_id": 7,
        "classes": {2: 0x04, 3: 0x0B, 4: 0x17, 5: 0x24},
        "first_candidates": (0x04, 0x2B, 0x08),
        "candidate_labels": ("로드", "호크로드", "힐러"),
        "label_fingerprint": (
            "e5cf981faeef5139733e62875b05cb637ff60758b7362c141e933d267b2a4587"
        ),
        "selected_index": 2,
        "selected_class": 0x2B,
    },
    "lester": {
        "commander_id": 9,
        "classes": {2: 0x05, 3: 0x0C, 4: 0x1B, 5: 0x2A},
        "first_candidates": (0x05, 0x2C, 0x0A),
        "candidate_labels": ("나이트", "크로코로드", "샤먼"),
        "label_fingerprint": (
            "be5d7c3e0a6a69b8d9fdbc9f50abb943f4dd60273ea697be91c4be28ca8a1657"
        ),
        "selected_index": 2,
        "selected_class": 0x2C,
    },
    "jessica": {
        "commander_id": 10,
        "classes": {2: 0x08, 3: 0x11, 4: 0x16, 5: 0x26},
        "first_candidates": (0x08, 0x09, 0x04),
        "candidate_labels": ("힐러", "소서러", "로드"),
        "label_fingerprint": (
            "3c436dfea9136f11b0be8f1cdccb97a9a5a3b20659772432f187d57fcdf89101"
        ),
        "selected_index": 1,
        "selected_class": 0x08,
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


def candidate_class_label_fingerprint(path: Path) -> str:
    """Hash only the three rendered class labels, excluding sprites/cursor."""
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"candidate capture must be 320x240: {path}")
    crop = image.crop(CLASS_LABEL_BOX)
    mask = bytes(
        1 if red > 150 and green > 150 and blue > 150 else 0
        for red, green, blue in crop.getdata()
    )
    return hashlib.sha256(mask).hexdigest()


def reachable_tiers(rom: bytes, commander_id: int) -> list[set[int]]:
    chain = read_class_change_chain(rom, commander_id)
    transitions = {row.current_class: row.candidates for row in chain}
    tiers = [{chain[0].current_class}]
    for _ in range(4):
        tiers.append({
            candidate
            for current in tiers[-1]
            for candidate in transitions.get(current, ())
        })
    return tiers


def validate_profile_rom(
    path: Path,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    rom = path.read_bytes()
    if len(rom) != 0x400000:
        raise ValueError(f"release ROM must be 4 MiB: {path}")
    actual_sha256 = hashlib.sha256(rom).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"release ROM SHA-256 mismatch for {path}: "
            f"{actual_sha256} != {expected_sha256}"
        )
    cases = {}
    for name, definition in CASES.items():
        commander_id = int(definition["commander_id"])
        chain = read_class_change_chain(rom, commander_id)
        expected = tuple(int(value) for value in definition["first_candidates"])
        if chain[0].candidates != expected:
            raise ValueError(
                f"{name} first candidates changed: {chain[0].candidates!r}"
            )
        tiers = reachable_tiers(rom, commander_id)
        for tier, class_id in dict(definition["classes"]).items():
            if int(class_id) not in tiers[int(tier) - 1]:
                raise ValueError(
                    f"{name} class 0x{int(class_id):02X} is not reachable "
                    f"at tier {tier}"
                )
        cases[name] = {
            "commander_id": commander_id,
            "first_candidates": [f"0x{value:02X}" for value in expected],
            "tier_classes": {
                str(tier): f"0x{int(class_id):02X}"
                for tier, class_id in dict(definition["classes"]).items()
            },
        }
    return {
        "path": relative(path),
        "sha256": actual_sha256,
        "md_checksum": preparation.md_checksum(path),
        "cases": cases,
    }


def task_paths(
    output: Path,
    profile: str,
    character: str,
    tier: int,
) -> dict[str, Path]:
    root = output / profile / character / f"tier{tier}"
    prefix = root / "capture"
    return {
        "root": root,
        "probe": root / "probe.md",
        "gst": root / "applied.gst",
        "log": root / "run.log",
        "prefix": prefix,
    }


def task_command(
    args: argparse.Namespace,
    *,
    profile: str,
    character: str,
    tier: int,
    display: str,
) -> list[str]:
    definition = CASES[character]
    paths = task_paths(args.output, profile, character, tier)
    current_class = int(dict(definition["classes"])[tier])
    runtime_name = (
        f"runestone-{args.run_id}-{profile}-{character}-tier{tier}"
    )
    return [
        sys.executable,
        str(ROOT / "tools/capture_class_change_application.py"),
        "--commander-id", str(definition["commander_id"]),
        "--current-class", f"0x{current_class:02X}",
        "--runtime-record-index", "0",
        "--restore-commander-id", "1",
        "--runestone-restart",
        "--preserve-production-resume",
        "--clear-join-marker",
        "--bypass-join-visibility",
        "--candidate-index", str(definition["selected_index"]),
        "--capture-all-candidates",
        "--input-rom", str(args.roms[profile]),
        # The release chain, not the Japanese chain, owns Hawk/Croco Lord.
        "--source-rom", str(args.roms[profile]),
        "--output-rom", str(paths["probe"]),
        "--runtime-name", runtime_name,
        "--capture-prefix", str(paths["prefix"]),
        "--gst-output", str(paths["gst"]),
        "--initial-delay", str(args.initial_delay),
        "--confirmation-delay", str(args.confirmation_delay),
        "--max-confirmations", str(args.max_confirmations),
        "--stability-delay", str(args.stability_delay),
        "--virtual-display", display,
    ]


def capture_paths(prefix: Path) -> list[Path]:
    return [
        Path(f"{prefix}_trigger.png"),
        Path(f"{prefix}_candidate1.png"),
        Path(f"{prefix}_candidate2.png"),
        Path(f"{prefix}_candidate3.png"),
        Path(f"{prefix}_applied_map.png"),
        Path(f"{prefix}_stable_map.png"),
        Path(f"{prefix}_applied_status.png"),
    ]


def production_resume_report(
    release: bytes,
    probe: bytes,
) -> dict[str, object]:
    operand = application.probe_builder.CLASS_CHANGE_RESUME_OPERAND
    wrapper = application.builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER
    expected_wrapper = application.builder.build_join_class_choice_level_wrapper()
    wrapper_size = len(expected_wrapper)
    release_target = int.from_bytes(release[operand : operand + 4], "big")
    probe_target = int.from_bytes(probe[operand : operand + 4], "big")
    release_wrapper = release[wrapper : wrapper + wrapper_size]
    probe_wrapper = probe[wrapper : wrapper + wrapper_size]
    operand_identical = probe[operand : operand + 4] == release[operand : operand + 4]
    wrapper_identical = probe_wrapper == release_wrapper
    release_matches_builder = release_wrapper == expected_wrapper
    passed = (
        release_target == wrapper
        and probe_target == wrapper
        and operand_identical
        and wrapper_identical
        and release_matches_builder
    )
    return {
        "status": "pass" if passed else "fail",
        "resume_operand": f"0x{operand:06X}",
        "expected_production_target": f"0x{wrapper:06X}",
        "release_target": f"0x{release_target:06X}",
        "probe_target": f"0x{probe_target:06X}",
        "operand_byte_identical": operand_identical,
        "wrapper_range": f"0x{wrapper:06X}..0x{wrapper + wrapper_size - 1:06X}",
        "wrapper_size": wrapper_size,
        "release_wrapper_sha256": hashlib.sha256(release_wrapper).hexdigest(),
        "probe_wrapper_sha256": hashlib.sha256(probe_wrapper).hexdigest(),
        "expected_wrapper_sha256": hashlib.sha256(expected_wrapper).hexdigest(),
        "wrapper_byte_identical": wrapper_identical,
        "release_wrapper_matches_current_builder": release_matches_builder,
    }


def marker_setup_report(
    release: bytes,
    probe: bytes,
    *,
    character: str,
    tier: int,
) -> dict[str, object]:
    """Prove the marker is zeroed immediately before the stock handler."""
    definition = CASES[character]
    commander_id = int(definition["commander_id"])
    current_class = int(dict(definition["classes"])[tier])
    marker_address = int(
        application.builder.JOIN_CLASS_CHOICE_RECORDS[commander_id][
            "active_marker_address"
        ]
    )
    clear_instruction = (
        application.probe_builder.join_marker_clear_instruction(commander_id)
    )
    forced_wrapper = application.probe_builder.wrapper_code(
        runtime_record_index=0,
        expected_class=current_class,
        forced_commander_id=commander_id,
        probe_experience=application.probe_builder.class_change_experience(
            release, current_class
        ),
        equipped_item=application.probe_builder.RUNESTONE_ITEM_ID,
    )
    expected = clear_instruction + forced_wrapper
    wrapper = application.probe_builder.PROBE_WRAPPER
    entry_operand = application.probe_builder.END_TURN_LEVEL_UP_ENTRY_OPERAND
    entry_target = int.from_bytes(probe[entry_operand : entry_operand + 4], "big")
    observed = probe[wrapper : wrapper + len(expected)]
    release_region_empty = release[wrapper : wrapper + len(expected)] == (
        b"\xFF" * len(expected)
    )
    passed = (
        entry_target == wrapper
        and observed == expected
        and release_region_empty
        and expected.endswith(bytes.fromhex("4E F9 00 01 48 0C"))
    )
    return {
        "status": "pass" if passed else "fail",
        "entry_operand": f"0x{entry_operand:06X}",
        "entry_target": f"0x{entry_target:06X}",
        "probe_wrapper": f"0x{wrapper:06X}",
        "marker_address": f"0x{marker_address:08X}",
        "clear_instruction": clear_instruction.hex(),
        "clear_instruction_offset": f"0x{wrapper:06X}",
        "stock_handler_target": "0x01480C",
        "clear_precedes_stock_handler": observed == expected,
        "release_probe_region_empty": release_region_empty,
        "setup_sha256": hashlib.sha256(observed).hexdigest(),
        "expected_setup_sha256": hashlib.sha256(expected).hexdigest(),
    }


def runtime_join_marker_report(
    runtime_home: Path,
    commander_id: int,
) -> dict[str, object]:
    """Read the compact BlastEm SRAM byte owned by the join marker."""
    paths = sorted(runtime_home.rglob("save.sram"))
    if len(paths) != 1:
        raise ValueError(
            f"expected one isolated save.sram, found {len(paths)} under "
            f"{runtime_home}"
        )
    path = paths[0]
    payload = path.read_bytes()
    if len(payload) != SRAM_BYTES:
        raise ValueError(f"BlastEm SRAM size {len(payload)} != {SRAM_BYTES}")
    address = int(
        application.builder.JOIN_CLASS_CHOICE_RECORDS[commander_id][
            "active_marker_address"
        ]
    )
    if address < SRAM_START_ADDRESS or (address - SRAM_START_ADDRESS) % 2:
        raise ValueError(f"join marker is not an odd SRAM byte: {address:#x}")
    offset = (address - SRAM_START_ADDRESS) // 2
    value = payload[offset]
    return {
        "status": "pass" if value == 0 else "fail",
        "path": relative(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "address": f"0x{address:08X}",
        "sram_offset": f"0x{offset:04X}",
        "value": value,
    }


def run_one(
    args: argparse.Namespace,
    *,
    profile: str,
    character: str,
    tier: int,
    display: str,
) -> dict[str, object]:
    paths = task_paths(args.output, profile, character, tier)
    paths["root"].mkdir(parents=True, exist_ok=False)
    command = task_command(
        args,
        profile=profile,
        character=character,
        tier=tier,
        display=display,
    )
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    paths["log"].write_text(completed.stdout, encoding="utf-8")
    definition = CASES[character]
    captures = capture_paths(paths["prefix"])
    candidate_captures = [
        Path(f"{paths['prefix']}_candidate{index}.png")
        for index in (1, 2, 3)
    ]
    candidate_fingerprints = [
        candidate_class_label_fingerprint(path)
        for path in candidate_captures
        if path.is_file()
    ]
    expected_label_fingerprint = str(definition["label_fingerprint"])
    candidate_labels_passed = (
        len(candidate_fingerprints) == 3
        and all(
            value == expected_label_fingerprint
            for value in candidate_fingerprints
        )
    )
    state = None
    state_error = None
    if paths["gst"].is_file():
        try:
            gst = paths["gst"].read_bytes()
            progress = application.runtime_progress(gst, 0)
            item = application.runtime_equipped_item(gst, 0)
            state = {
                "class_id": f"0x{progress[0]:02X}",
                "commander_id_after_apply": progress[1],
                "level": progress[2],
                "experience": progress[3],
                "equipped_item_after_use": f"0x{item:02X}",
            }
        except Exception as exc:
            state_error = f"{type(exc).__name__}: {exc}"
    expected_state = (
        int(definition["selected_class"]),
        int(definition["commander_id"]),
        1,
        0,
        0,
    )
    actual_state = None if state is None else (
        int(str(state["class_id"]), 16),
        int(state["commander_id_after_apply"]),
        int(state["level"]),
        int(state["experience"]),
        int(str(state["equipped_item_after_use"]), 16),
    )
    runtime_name = (
        f"runestone-{args.run_id}-{profile}-{character}-tier{tier}"
    )
    runtime_marker = None
    runtime_marker_error = None
    try:
        runtime_marker = runtime_join_marker_report(
            sequence.RUNTIME_ROOT / runtime_name,
            int(definition["commander_id"]),
        )
    except Exception as exc:
        runtime_marker_error = f"{type(exc).__name__}: {exc}"
    passed = (
        completed.returncode == 0
        and paths["probe"].is_file()
        and paths["gst"].is_file()
        and all(path.is_file() for path in captures)
        and candidate_labels_passed
        and actual_state == expected_state
        and runtime_marker is not None
        and runtime_marker["status"] == "pass"
    )
    base = args.roms[profile].read_bytes()
    probe_delta = None
    production_resume = None
    marker_setup = None
    if paths["probe"].is_file():
        probe = paths["probe"].read_bytes()
        probe_delta = sum(before != after for before, after in zip(base, probe))
        production_resume = production_resume_report(base, probe)
        marker_setup = marker_setup_report(
            base,
            probe,
            character=character,
            tier=tier,
        )
        passed = (
            passed
            and production_resume["status"] == "pass"
            and marker_setup["status"] == "pass"
        )
    return {
        "profile": profile,
        "character": character,
        "commander_id": int(definition["commander_id"]),
        "current_tier": tier,
        "current_class": f"0x{int(dict(definition['classes'])[tier]):02X}",
        "visible_candidates": [
            f"0x{int(value):02X}" for value in definition["first_candidates"]
        ],
        "candidate_labels": list(definition["candidate_labels"]),
        "candidate_label_surface": {
            "status": "pass" if candidate_labels_passed else "fail",
            "box": list(CLASS_LABEL_BOX),
            "expected_fingerprint": expected_label_fingerprint,
            "observed_fingerprints": candidate_fingerprints,
        },
        "selected_index": int(definition["selected_index"]),
        "selected_class": f"0x{int(definition['selected_class']):02X}",
        "status": "pass" if passed else "fail",
        "returncode": completed.returncode,
        "display": display,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "probe": relative(paths["probe"]) if paths["probe"].is_file() else None,
        "probe_sha256": sha256(paths["probe"]) if paths["probe"].is_file() else None,
        "probe_changed_bytes_including_checksum": probe_delta,
        "production_resume": production_resume,
        "marker_setup": marker_setup,
        "runtime_join_marker": runtime_marker,
        "runtime_join_marker_error": runtime_marker_error,
        "gst": relative(paths["gst"]) if paths["gst"].is_file() else None,
        "gst_sha256": sha256(paths["gst"]) if paths["gst"].is_file() else None,
        "state": state,
        "state_error": state_error,
        "captures": [
            {"path": relative(path), "sha256": sha256(path)}
            for path in captures if path.is_file()
        ],
        "log": relative(paths["log"]),
    }


def run_matrix(args: argparse.Namespace) -> dict[str, object]:
    args.output.mkdir(parents=True, exist_ok=False)
    initial_roms = {
        profile: validate_profile_rom(
            path, args.expected_rom_sha256[profile]
        )
        for profile, path in args.roms.items()
        if profile in args.profiles
    }
    tasks = [
        (profile, character, tier)
        for profile in args.profiles
        for character in CASES
        for tier in range(2, 6)
    ]
    workers = min(args.workers, len(tasks))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    available: queue.SimpleQueue[str] = queue.SimpleQueue()
    xvfb_processes = []
    rows = []
    started = time.monotonic()
    try:
        for display in displays:
            xvfb_processes.append(
                parallel.start_xvfb(args.xvfb, args.xvfb_library_path, display)
            )
            available.put(display)

        def assigned(profile: str, character: str, tier: int):
            display = available.get()
            try:
                last = None
                for attempt in range(1, args.attempts + 1):
                    if attempt > 1:
                        root = task_paths(
                            args.output, profile, character, tier
                        )["root"]
                        if root.exists():
                            import shutil
                            shutil.rmtree(root)
                    last = run_one(
                        args,
                        profile=profile,
                        character=character,
                        tier=tier,
                        display=display,
                    )
                    last["attempt"] = attempt
                    if last["status"] == "pass":
                        break
                return last
            finally:
                sequence.terminate_blastem_processes(display=display)
                available.put(display)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(assigned, *task): task for task in tasks
            }
            for future in as_completed(futures):
                profile, character, tier = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = {
                        "profile": profile,
                        "character": character,
                        "current_tier": tier,
                        "status": "orchestrator_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                rows.append(row)
                print(
                    f"{profile} {character} tier {tier}: {row['status']}",
                    flush=True,
                )
    finally:
        for process in xvfb_processes:
            parallel.stop_process(process)

    rows.sort(key=lambda row: (
        str(row["profile"]),
        str(row["character"]),
        int(row["current_tier"]),
    ))
    final_roms = {
        profile: validate_profile_rom(
            path, args.expected_rom_sha256[profile]
        )
        for profile, path in args.roms.items()
        if profile in args.profiles
    }
    release_unchanged = all(
        initial_roms[profile]["sha256"] == final_roms[profile]["sha256"]
        for profile in args.profiles
    )
    passed = sum(row.get("status") == "pass" for row in rows)
    return {
        "schema_version": 1,
        "status": (
            "pass" if passed == len(rows) and release_unchanged else "fail"
        ),
        "run_id": args.run_id,
        "profiles": args.profiles,
        "tiers": [2, 3, 4, 5],
        "characters": list(CASES),
        "passed_tasks": passed,
        "total_tasks": len(rows),
        "workers": workers,
        "displays": displays,
        "release_roms_before": initial_roms,
        "release_roms_after": final_roms,
        "release_roms_unchanged": release_unchanged,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "results": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--pure-rom", type=Path, default=DEFAULT_ROMS["pure"])
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_ROMS["normal"])
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_ROMS["hard"])
    parser.add_argument(
        "--expected-pure-sha256", default=DEFAULT_ROM_SHA256["pure"]
    )
    parser.add_argument(
        "--expected-normal-sha256", default=DEFAULT_ROM_SHA256["normal"]
    )
    parser.add_argument(
        "--expected-hard-sha256", default=DEFAULT_ROM_SHA256["hard"]
    )
    parser.add_argument(
        "--profiles",
        default="pure,normal,hard",
        help="comma-separated subset of pure,normal,hard",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--display-base", type=int, default=700)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=preparation.validate_run_id, required=True)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--initial-delay", type=float, default=6.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.45)
    parser.add_argument("--max-confirmations", type=int, default=50)
    parser.add_argument("--stability-delay", type=float, default=3.0)
    args = parser.parse_args()
    args.roms = {
        "pure": args.pure_rom.resolve(),
        "normal": args.normal_rom.resolve(),
        "hard": args.hard_rom.resolve(),
    }
    args.expected_rom_sha256 = {
        "pure": args.expected_pure_sha256.lower(),
        "normal": args.expected_normal_sha256.lower(),
        "hard": args.expected_hard_sha256.lower(),
    }
    args.profiles = [part.strip() for part in args.profiles.split(",") if part.strip()]
    if not args.profiles or any(profile not in args.roms for profile in args.profiles):
        parser.error("--profiles must contain pure, normal, and/or hard")
    if len(set(args.profiles)) != len(args.profiles):
        parser.error("--profiles must not repeat")
    for profile, digest in args.expected_rom_sha256.items():
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            parser.error(f"--expected-{profile}-sha256 must be 64 hex characters")
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if not (
        parallel.MIN_ISOLATED_DISPLAY_NUMBER
        <= args.display_base
        <= 999 - args.workers
    ):
        parser.error(
            "--display-base must reserve only high-numbered isolated Xvfb "
            "displays and leave enough room"
        )
    for profile in args.profiles:
        if not args.roms[profile].is_file():
            raise FileNotFoundError(args.roms[profile])
    args.output_root = args.output_root.resolve()
    args.output = args.output_root / args.run_id
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    return args


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        result = {
            "schema_version": 1,
            "status": "pass",
            "run_id": args.run_id,
            "profiles": args.profiles,
            "task_count": len(args.profiles) * len(CASES) * 4,
            "tasks": [
                task_command(
                    args,
                    profile=profile,
                    character=character,
                    tier=tier,
                    display=f":{args.display_base}",
                )
                for profile in args.profiles
                for character in CASES
                for tier in range(2, 6)
            ],
        }
    else:
        result = run_matrix(args)
        (args.output / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
