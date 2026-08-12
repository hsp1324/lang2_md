#!/usr/bin/env python3
"""Build current-source pure/normal/hard result probes for Scenarios 1..31."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as korean_builder
from tools import build_scenario1_clear_probe_rom as scenario1
from tools import build_scenario2_escape_probe_rom as scenario2
from tools import build_scenario3_clear_probe_rom as scenario3
from tools import build_scenario4_clear_probe_rom as scenario4
from tools import build_scenario5_escape_probe_rom as scenario5
from tools import build_scenario6_clear_probe_rom as scenario6
from tools import build_scenario7_clear_probe_rom as scenario7
from tools import build_scenario8_clear_probe_rom as scenario8
from tools import build_scenario9_clear_probe_rom as scenario9
from tools import build_scenario10_result_surface_probe_rom as scenario10
from tools import build_scenario11_clear_probe_rom as scenario11
from tools import build_scenario12_clear_probe_rom as scenario12
from tools import build_scenario13_clear_probe_rom as scenario13
from tools import build_scenario14_clear_probe_rom as scenario14
from tools import build_scenario15_clear_probe_rom as scenario15
from tools import build_scenario16_clear_probe_rom as scenario16
from tools import build_scenario17_clear_probe_rom as scenario17
from tools import build_scenario18_clear_probe_rom as scenario18
from tools import build_scenario19_clear_probe_rom as scenario19
from tools import build_scenario20_clear_probe_rom as scenario20
from tools import build_scenario21_clear_probe_rom as scenario21
from tools import build_scenario22_clear_probe_rom as scenario22
from tools import build_scenario23_clear_probe_rom as scenario23
from tools import build_scenario24_clear_probe_rom as scenario24
from tools import build_scenario25_clear_probe_rom as scenario25
from tools import build_scenario26_clear_probe_rom as scenario26
from tools import build_scenario27_ending_probe_rom as scenario27
from tools import build_scenario28_clear_probe_rom as scenario28
from tools import build_scenario29_clear_probe_rom as scenario29
from tools import build_scenario30_clear_probe_rom as scenario30
from tools import build_scenario31_clear_probe_rom as scenario31
from tools.v137_release_identity import (  # noqa: E402
    JAPANESE_SOURCE_ROM_BYTES,
    JAPANESE_SOURCE_ROM_SHA256,
    RELEASE_ROM_PATHS,
    RELEASE_ROM_SHA256,
)


DEFAULT_PURE_ROM = RELEASE_ROM_PATHS["pure"]
DEFAULT_NORMAL_ROM = RELEASE_ROM_PATHS["normal"]
DEFAULT_HARD_ROM = RELEASE_ROM_PATHS["hard"]
DEFAULT_ROM_SHA256 = dict(RELEASE_ROM_SHA256)
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/current-source-result-probes"
DEFAULT_SOURCE_ROM = ROOT / korean_builder.IN_ROM


PROBE_DEFINITIONS: dict[int, dict[str, object]] = {
    1: {
        "module": scenario1,
        "filename": "s01-runtime-clear.md",
        "kwargs": {"runtime_defeat_bald": True},
    },
    2: {
        "module": scenario2,
        "filename": "s02-runtime-clear.md",
        "kwargs": {"enemy_annihilation": True},
    },
    3: {
        "module": scenario3,
        "filename": "s03-runtime-clear.md",
        "kwargs": {"enemy_annihilation": True},
    },
    4: {
        "module": scenario4,
        "filename": "s04-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    5: {"module": scenario5, "filename": "s05.md", "kwargs": {}},
    6: {
        "module": scenario6,
        "filename": "s06-runtime-clear.md",
        "kwargs": {"enemy_annihilation": True},
    },
    7: {
        "module": scenario7,
        "filename": "s07-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    8: {
        "module": scenario8,
        "filename": "s08-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    9: {
        "module": scenario9,
        "filename": "s09-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    10: {"module": scenario10, "filename": "s10.md", "kwargs": {}},
    11: {
        "module": scenario11,
        "filename": "s11-completion.md",
        "kwargs": {"completion_layout": True},
    },
    12: {
        "module": scenario12,
        "filename": "s12-completion.md",
        "kwargs": {"completion_layout": True},
    },
    13: {
        "module": scenario13,
        "filename": "s13-continuation.md",
        "kwargs": {
            "completion_layout": True,
            "completion_continuation": True,
        },
    },
    14: {
        "module": scenario14,
        "filename": "s14.md",
        "kwargs": {"completion_layout": True},
    },
    15: {
        "module": scenario15,
        "filename": "s15.md",
        "kwargs": {"completion_layout": True},
    },
    16: {
        "module": scenario16,
        "filename": "s16.md",
        "kwargs": {
            "completion_layout": True,
            "protagonist_death": False,
            "turn_event": None,
        },
    },
    17: {
        "module": scenario17,
        "filename": "s17-two-hit.md",
        "kwargs": {
            "completion_layout": True,
            "two_hit_attacker": True,
        },
    },
    18: {
        "module": scenario18,
        "filename": "s18.md",
        "kwargs": {"completion_layout": True},
    },
    19: {
        "module": scenario19,
        "filename": "s19.md",
        "kwargs": {"completion_layout": True},
    },
    20: {
        "module": scenario20,
        "filename": "s20.md",
        "kwargs": {"completion_layout": True},
    },
    21: {
        "module": scenario21,
        "filename": "s21-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    22: {
        "module": scenario22,
        "filename": "s22-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    23: {
        "module": scenario23,
        "filename": "s23-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    24: {
        "module": scenario24,
        "filename": "s24-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    25: {
        "module": scenario25,
        "filename": "s25-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    26: {
        "module": scenario26,
        "filename": "s26-runtime-clear.md",
        "kwargs": {"runtime_clear": True},
    },
    27: {
        "module": scenario27,
        "filename": "s27-ending.md",
        "kwargs": {"allow_balanced_input": False},
    },
    28: {
        "module": scenario28,
        "filename": "s28-completion.md",
        "kwargs": {"completion_target_only": True},
    },
    29: {
        "module": scenario29,
        "filename": "s29-completion.md",
        "kwargs": {"completion_target_only": True},
    },
    30: {
        "module": scenario30,
        "filename": "s30-completion.md",
        "kwargs": {"completion_target_only": True},
    },
    31: {
        "module": scenario31,
        "filename": "s31-completion.md",
        "kwargs": {"completion_layout": True},
    },
}
SCENARIOS = tuple(PROBE_DEFINITIONS)
CHECKSUM_OFFSETS = frozenset((0x18E, 0x18F))


def sha256_bytes(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def md_checksum(data: bytes | bytearray) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


def require_valid_rom(
    data: bytes | bytearray,
    label: str,
    expected_sha256: str | None = None,
) -> None:
    if len(data) != 0x400000:
        raise ValueError(f"{label} must be a 4 MiB ROM")
    header = int.from_bytes(data[0x18E:0x190], "big")
    computed = md_checksum(data)
    if header != computed:
        raise ValueError(
            f"{label} checksum mismatch: header {header:04X}, computed {computed:04X}"
        )
    actual_sha256 = sha256_bytes(data)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"{label} SHA-256 mismatch: {actual_sha256} != {expected_sha256}"
        )


def require_canonical_source(data: bytes | bytearray) -> None:
    if len(data) != JAPANESE_SOURCE_ROM_BYTES:
        raise ValueError(
            "Japanese source ROM length mismatch: "
            f"{len(data)} != {JAPANESE_SOURCE_ROM_BYTES}"
        )
    actual_sha256 = sha256_bytes(data)
    if actual_sha256 != JAPANESE_SOURCE_ROM_SHA256:
        raise ValueError(
            "Japanese source ROM SHA-256 mismatch: "
            f"{actual_sha256} != {JAPANESE_SOURCE_ROM_SHA256}"
        )


def diagnostic_delta_report(
    candidate: bytes | bytearray,
    probe: bytes | bytearray,
) -> dict[str, object]:
    if len(candidate) != len(probe):
        raise ValueError("diagnostic candidate/probe lengths differ")
    changed = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, probe, strict=True))
        if before != after
    ]
    return {
        "changed_byte_count": len(changed),
        "payload_changed_byte_count": len(set(changed) - CHECKSUM_OFFSETS),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed],
    }


def patch_direct(
    scenario: int,
    candidate: bytes,
    source: bytes,
    profile: str,
) -> bytearray:
    definition = PROBE_DEFINITIONS[scenario]
    module = definition["module"]
    if not isinstance(module, ModuleType):
        raise TypeError(f"Scenario {scenario} probe module is invalid")
    probe = bytearray(candidate)
    kwargs = dict(definition["kwargs"])
    if scenario == 10:
        module.patch_probe(probe, **kwargs)
    else:
        module.patch_probe(probe, source, **kwargs)
    require_valid_rom(probe, f"Scenario {scenario} {profile} probe")
    return probe


def patch_pure(
    scenario: int,
    pure: bytes,
    source: bytes,
) -> bytearray:
    return patch_direct(scenario, pure, source, "pure")


def patch_normal(
    scenario: int,
    normal: bytes,
    source: bytes,
) -> bytearray:
    return patch_direct(scenario, normal, source, "normal")


def overlay_hard(
    normal: bytes,
    normal_probe: bytes | bytearray,
    hard: bytes,
) -> tuple[bytearray, set[int], int]:
    delta = {
        offset
        for offset, (before, after) in enumerate(zip(normal, normal_probe))
        if before != after
    }
    payload_delta = delta - CHECKSUM_OFFSETS
    conflicts = sum(normal[offset] != hard[offset] for offset in payload_delta)
    hard_probe = bytearray(hard)
    for offset in payload_delta:
        hard_probe[offset] = normal_probe[offset]
    korean_builder.update_md_checksum(hard_probe)
    require_valid_rom(hard_probe, "hard probe")
    return hard_probe, delta, conflicts


def rom_report(path: Path, data: bytes | bytearray) -> dict[str, object]:
    return {
        "path": relative(path),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "md_checksum": f"{int.from_bytes(data[0x18E:0x190], 'big'):04X}",
        "checksum_valid": int.from_bytes(data[0x18E:0x190], "big")
        == md_checksum(data),
    }


def build_matrix(args: argparse.Namespace) -> dict[str, object]:
    pure_rom_path = getattr(args, "pure_rom", DEFAULT_PURE_ROM)
    pure = pure_rom_path.read_bytes()
    normal = args.normal_rom.read_bytes()
    hard = args.hard_rom.read_bytes()
    source = args.source_rom.read_bytes()
    expected_hashes = getattr(args, "expected_rom_sha256", DEFAULT_ROM_SHA256)
    require_valid_rom(pure, "pure candidate", expected_hashes.get("pure"))
    require_valid_rom(normal, "normal candidate", expected_hashes.get("normal"))
    require_valid_rom(hard, "hard candidate", expected_hashes.get("hard"))
    require_canonical_source(source)
    if args.output_root.exists():
        raise FileExistsError(f"output root already exists: {args.output_root}")

    pure_root = args.output_root / "pure"
    normal_root = args.output_root / "normal"
    hard_root = args.output_root / "hard"
    pure_root.mkdir(parents=True)
    normal_root.mkdir(parents=True)
    hard_root.mkdir(parents=True)
    rows = []
    for scenario in args.scenarios:
        definition = PROBE_DEFINITIONS[scenario]
        filename = str(definition["filename"])
        pure_probe = patch_pure(scenario, pure, source)
        normal_probe = patch_normal(scenario, normal, source)
        hard_probe, delta, conflicts = overlay_hard(normal, normal_probe, hard)
        pure_delta = {
            offset
            for offset, (before, after) in enumerate(zip(pure, pure_probe))
            if before != after
        }
        pure_probe_path = pure_root / filename
        normal_path = normal_root / filename
        hard_path = hard_root / filename
        pure_probe_path.write_bytes(pure_probe)
        normal_path.write_bytes(normal_probe)
        hard_path.write_bytes(hard_probe)
        rows.append(
            {
                "scenario": scenario,
                "status": "pass",
                "builder_module": definition["module"].__name__,
                "builder_kwargs": definition["kwargs"],
                "diagnostic_delta": {
                    "pure": diagnostic_delta_report(pure, pure_probe),
                    "normal": diagnostic_delta_report(normal, normal_probe),
                    "hard": diagnostic_delta_report(hard, hard_probe),
                },
                "pure": rom_report(pure_probe_path, pure_probe),
                "normal": rom_report(normal_path, normal_probe),
                "hard": rom_report(hard_path, hard_probe),
                "pure_diagnostic_changed_bytes": len(pure_delta),
                "pure_diagnostic_payload_changed_bytes": len(
                    pure_delta - CHECKSUM_OFFSETS
                ),
                "pure_method": (
                    "apply the scenario diagnostic builder directly to the "
                    "pure candidate, then validate the Mega Drive checksum"
                ),
                "normal_diagnostic_changed_bytes": len(delta),
                "normal_diagnostic_payload_changed_bytes": len(
                    delta - CHECKSUM_OFFSETS
                ),
                "hard_candidate_conflicts_inside_diagnostic_delta": conflicts,
                "hard_method": (
                    "apply the exact normal diagnostic payload delta to the "
                    "hard candidate, then recalculate only the Mega Drive checksum"
                ),
            }
        )

    report = {
        "schema_version": 1,
        "status": "pass",
        "scope": "current_source_result_probe_matrix",
        "run_id": getattr(args, "run_id", None),
        "candidate_roms": {
            "pure": rom_report(pure_rom_path, pure),
            "normal": rom_report(args.normal_rom, normal),
            "hard": rom_report(args.hard_rom, hard),
        },
        "source_rom": {
            "path": relative(args.source_rom),
            "sha256": sha256_bytes(source),
            "expected_sha256": JAPANESE_SOURCE_ROM_SHA256,
            "bytes": len(source),
            "expected_bytes": JAPANESE_SOURCE_ROM_BYTES,
            "hash_locked": True,
        },
        "scenarios": list(args.scenarios),
        "probe_count": len(rows) * 3,
        "release_promoted": False,
        "version_bumped": False,
        "probes": rows,
    }
    manifest = args.output_root / "manifest.json"
    manifest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def parse_scenarios(value: str) -> tuple[int, ...]:
    scenarios = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not scenarios or any(scenario not in PROBE_DEFINITIONS for scenario in scenarios):
        allowed = ",".join(str(scenario) for scenario in SCENARIOS)
        raise argparse.ArgumentTypeError(f"scenarios must be selected from {allowed}")
    if len(set(scenarios)) != len(scenarios):
        raise argparse.ArgumentTypeError("scenarios must not repeat")
    return scenarios


def valid_run_id(value: str) -> str:
    if (
        not value
        or Path(value).name != value
        or any(not (character.isalnum() or character in "-_") for character in value)
    ):
        raise argparse.ArgumentTypeError("run ID must be one safe directory name")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pure-rom", type=Path, default=DEFAULT_PURE_ROM)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_HARD_ROM)
    parser.add_argument(
        "--expected-pure-sha256", default=DEFAULT_ROM_SHA256["pure"]
    )
    parser.add_argument(
        "--expected-normal-sha256", default=DEFAULT_ROM_SHA256["normal"]
    )
    parser.add_argument(
        "--expected-hard-sha256", default=DEFAULT_ROM_SHA256["hard"]
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=valid_run_id)
    parser.add_argument(
        "--scenarios",
        type=parse_scenarios,
        default=SCENARIOS,
        help="comma-separated subset of 1..31",
    )
    args = parser.parse_args()
    for name in (
        "pure_rom",
        "normal_rom",
        "hard_rom",
        "source_rom",
        "output_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    args.expected_rom_sha256 = {
        "pure": args.expected_pure_sha256.lower(),
        "normal": args.expected_normal_sha256.lower(),
        "hard": args.expected_hard_sha256.lower(),
    }
    for profile, digest in args.expected_rom_sha256.items():
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            parser.error(f"--expected-{profile}-sha256 must be 64 hex characters")
    for label, path in (
        ("pure ROM", args.pure_rom),
        ("normal ROM", args.normal_rom),
        ("hard ROM", args.hard_rom),
        ("source ROM", args.source_rom),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    report = build_matrix(args)
    print(
        f"pass: {len(report['scenarios'])} scenarios, "
        f"{report['probe_count']} non-release probes"
    )
    print(args.output_root / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
