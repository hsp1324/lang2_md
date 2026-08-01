#!/usr/bin/env python3
"""Run the complete normal/hard UI and battle regression in bounded parallelism."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools.class_hire_data import patch_class_hire_unlocks
from tools.scenario_data import update_checksum


REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/full_surface_regression"


def build_monk_probe_rom(source: Path, output: Path) -> dict[str, object]:
    data = bytearray(source.read_bytes())
    original = data[0x05EE12]
    patch_class_hire_unlocks(data, [{
        "class_id": 0x01,
        "hire_class_ids": [0x6C, 0xFF],
    }])
    checksum = update_checksum(data)
    output.write_bytes(data)
    return {
        "base_rom": str(source.relative_to(ROOT)),
        "base_sha256": sha256(source),
        "probe_rom": str(output.relative_to(ROOT)),
        "probe_sha256": sha256(output),
        "md_checksum": f"{checksum:04X}",
        "only_non_checksum_delta": {
            "offset": "0x05EE12",
            "before": f"0x{original:02X}",
            "after": "0x0A",
            "meaning": "Fighter hire unlock changes from Soldier to Monk",
        },
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_display_base(args: argparse.Namespace, profile: str) -> int:
    return args.display_base + (args.workers if profile == "hard" else 0)


def preparation_command(args: argparse.Namespace, profile: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/run_preparation_surface_parallel.py"),
        "run",
        "--profile", profile,
        "--rom", str(args.roms[profile]),
        "--reference-rom", str(REFERENCE_ROM),
        "--seed-gst", str(args.seed_gst),
        "--scenarios", args.scenario_spec,
        "--workers", str(args.workers),
        "--display-base", str(profile_display_base(args, profile)),
        "--run-id", args.run_id,
        "--summary", str(args.output / f"preparation-{profile}.json"),
    ]


def gray_command(args: argparse.Namespace, profile: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/run_gray_acted_surface_parallel.py"),
        "run",
        "--profile", profile,
        "--rom", str(args.roms[profile]),
        "--seed-gst", str(args.seed_gst),
        "--scenarios", args.scenario_spec,
        "--workers", str(args.workers),
        "--display-base", str(profile_display_base(args, profile)),
        "--run-id", args.run_id,
        "--summary", str(args.output / f"gray-{profile}.json"),
    ]


def all_mercenary_command(args: argparse.Namespace, profile: str) -> list[str]:
    display = args.display_base + (1 if profile == "hard" else 0)
    return [
        sys.executable,
        str(ROOT / "tools/run_all_mercenary_hire_probe.py"),
        "--rom", str(args.roms[profile]),
        "--seed-gst", str(args.seed_gst),
        "--display", f":{display}",
        "--run-id", f"{args.run_id}-{profile}",
    ]


def pike_acted_command(args: argparse.Namespace, profile: str) -> list[str]:
    display = args.display_base + (1 if profile == "hard" else 0)
    return [
        sys.executable,
        str(ROOT / "tools/run_pike_acted_surface_probe.py"),
        "--rom", str(args.roms[profile]),
        "--seed-gst", str(args.seed_gst),
        "--display", f":{display}",
        "--run-id", f"{args.run_id}-{profile}",
    ]


def monk_acted_command(args: argparse.Namespace, profile: str) -> list[str]:
    display = args.display_base + (1 if profile == "hard" else 0)
    return [
        sys.executable,
        str(ROOT / "tools/run_pike_acted_surface_probe.py"),
        "--rom", str(args.monk_probe_roms[profile]),
        "--seed-gst", str(args.seed_gst),
        "--display", f":{display}",
        "--scenario", "12",
        "--commander-id", "4",
        "--commander-class", "0x01",
        "--commander-level", "9",
        "--commander-experience", "15",
        "--hire-mask-or", "0x0400",
        "--mercenary-class", "0x6C",
        "--target-page", "0",
        "--target-row", "1",
        "--page-row-count", "2",
        "--hired-count", "1",
        "--run-id", f"{args.run_id}-monk-{profile}",
    ]


def shop_command(args: argparse.Namespace, profile: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/run_shop_necklace_probe.py"),
        "--rom", str(args.roms[profile]),
        "--display", f":{args.display_base}",
        "--run-id", f"{args.run_id}-{profile}",
    ]


def battle_verify_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/verify_battle_mercenary_sprite_cache.py"),
        "--normal-rom", str(args.roms["normal"]),
        "--hard-rom", str(args.roms["hard"]),
        "--normal-run-id", args.run_id,
        "--hard-run-id", args.run_id,
        "--scenarios", args.scenario_spec,
        "--output", str(args.output / "battle-cache.json"),
    ]


def glyph_conflict_verify_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/verify_preparation_glyph_conflicts.py"),
        "--source-rom", str(ROOT / "roms/original/Langrisser II (Japan).md"),
        "--reference-rom", str(REFERENCE_ROM),
        "--output", str(args.output / "preparation-glyph-conflicts.json"),
    ]


def preparation_identity_verify_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/verify_preparation_scenario_identity.py"),
        "--normal-rom", str(args.roms["normal"]),
        "--hard-rom", str(args.roms["hard"]),
        "--normal-run-id", args.run_id,
        "--hard-run-id", args.run_id,
        "--scenarios", args.scenario_spec,
        "--output", str(args.output / "preparation-scenario-identity.json"),
    ]


def command_manifest(args: argparse.Namespace) -> dict[str, object]:
    return {
        "preparation": {
            profile: preparation_command(args, profile)
            for profile in ("normal", "hard")
        },
        "gray_acted": {
            profile: gray_command(args, profile)
            for profile in ("normal", "hard")
        },
        "all_mercenary": {
            profile: all_mercenary_command(args, profile)
            for profile in ("normal", "hard")
        },
        "pike_acted": {
            profile: pike_acted_command(args, profile)
            for profile in ("normal", "hard")
        },
        "monk_acted": {
            profile: monk_acted_command(args, profile)
            for profile in ("normal", "hard")
        },
        # Keep these serial. Their stock navigation helper owns one global
        # keyboard/log path even though the emulator displays are isolated.
        "shop_necklace_serial": [
            shop_command(args, profile) for profile in ("normal", "hard")
        ],
        "battle_cache_verify": battle_verify_command(args),
        "preparation_glyph_conflict_verify": glyph_conflict_verify_command(args),
        "preparation_identity_verify": preparation_identity_verify_command(args),
    }


def run_command(command: list[str], log: Path) -> dict[str, object]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(completed.stdout, encoding="utf-8")
    return {
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "log": str(log.relative_to(ROOT)),
    }


def run_pair(
    commands: dict[str, list[str]],
    output: Path,
    phase: str,
) -> dict[str, object]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            profile: executor.submit(
                run_command,
                command,
                output / f"{phase}-{profile}.log",
            )
            for profile, command in commands.items()
        }
        return {profile: future.result() for profile, future in futures.items()}


def run_all(args: argparse.Namespace) -> dict[str, object]:
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    monk_probe_derivation = {
        profile: build_monk_probe_rom(
            args.roms[profile],
            args.monk_probe_roms[profile],
        )
        for profile in ("normal", "hard")
    }
    phases: dict[str, object] = {}
    commands = command_manifest(args)

    phases["preparation_glyph_conflicts"] = run_command(
        commands["preparation_glyph_conflict_verify"],
        args.output / "preparation-glyph-conflicts.log",
    )

    phases["preparation"] = run_pair(
        commands["preparation"], args.output, "preparation"
    )
    phases["preparation_identity"] = run_command(
        commands["preparation_identity_verify"],
        args.output / "preparation-identity.log",
    )
    phases["gray_acted"] = run_pair(
        commands["gray_acted"], args.output, "gray"
    )
    phases["all_mercenary"] = run_pair(
        commands["all_mercenary"], args.output, "all-mercenary"
    )
    phases["pike_acted"] = run_pair(
        commands["pike_acted"], args.output, "pike-acted"
    )
    phases["monk_acted"] = run_pair(
        commands["monk_acted"], args.output, "monk-acted"
    )
    shop_rows = []
    for profile, command in zip(
        ("normal", "hard"), commands["shop_necklace_serial"]
    ):
        shop_rows.append({
            "profile": profile,
            **run_command(command, args.output / f"shop-{profile}.log"),
        })
    phases["shop_necklace"] = shop_rows

    gray_passed = all(
        row["returncode"] == 0 for row in phases["gray_acted"].values()
    )
    if gray_passed:
        phases["battle_cache"] = run_command(
            commands["battle_cache_verify"],
            args.output / "battle-cache.log",
        )
    else:
        phases["battle_cache"] = {
            "returncode": None,
            "status": "skipped_due_to_gray_failure",
        }

    returncodes = [
        phases["preparation_glyph_conflicts"]["returncode"],
        phases["preparation_identity"]["returncode"],
    ]
    for phase in (
        "preparation", "gray_acted", "all_mercenary", "pike_acted",
        "monk_acted",
    ):
        returncodes.extend(
            row["returncode"] for row in phases[phase].values()
        )
    returncodes.extend(row["returncode"] for row in phases["shop_necklace"])
    returncodes.append(phases["battle_cache"]["returncode"])
    passed = all(code == 0 for code in returncodes)
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "run_id": args.run_id,
        "scenarios": args.scenarios,
        "workers_per_profile": args.workers,
        "maximum_simultaneous_emulators": args.workers * 2,
        "roms": {
            profile: {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "md_checksum": matrix.md_checksum(path),
            }
            for profile, path in args.roms.items()
        },
        "monk_probe_roms": monk_probe_derivation,
        "phases": phases,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "release_rom_modified": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--normal-rom", type=Path, required=True)
    parser.add_argument("--hard-rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--scenarios", default="1-31")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--display-base", type=int, default=300)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    args.roms = {
        "normal": args.normal_rom.resolve(),
        "hard": args.hard_rom.resolve(),
    }
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.output = args.output_root / args.run_id
    args.monk_probe_roms = {
        profile: args.output / f"monk-probe-{profile}.md"
        for profile in ("normal", "hard")
    }
    args.scenarios = parallel.parse_scenarios(args.scenarios)
    args.scenario_spec = ",".join(str(value) for value in args.scenarios)
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.display_base <= 999 - args.workers * 2:
        parser.error("--display-base does not leave room for both profiles")
    for label, path in (*args.roms.items(), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    return args


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        result = {
            "schema_version": 1,
            "status": "pass",
            "run_id": args.run_id,
            "scenarios": args.scenarios,
            "workers_per_profile": args.workers,
            "maximum_simultaneous_emulators": args.workers * 2,
            "commands": command_manifest(args),
        }
    else:
        result = run_all(args)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.command == "run":
        (args.output / "summary.json").write_text(encoded, encoding="utf-8")
        print(args.output / "summary.json")
    else:
        print(encoded, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
