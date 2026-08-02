#!/usr/bin/env python3
"""Build current-source normal/hard result probes for Scenarios 10 and 12..27."""

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
from tools import build_scenario10_result_surface_probe_rom as scenario10
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


DEFAULT_NORMAL_ROM = ROOT / "tmp/current-source-audit-normal.md"
DEFAULT_HARD_ROM = ROOT / "tmp/current-source-audit-hard.md"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/current-source-result-probes"
DEFAULT_SOURCE_ROM = ROOT / korean_builder.IN_ROM


PROBE_DEFINITIONS: dict[int, dict[str, object]] = {
    10: {"module": scenario10, "filename": "s10.md", "kwargs": {}},
    12: {
        "module": scenario12,
        "filename": "s12.md",
        "kwargs": {"compact_layout": True},
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


def require_valid_rom(data: bytes | bytearray, label: str) -> None:
    if len(data) != 0x400000:
        raise ValueError(f"{label} must be a 4 MiB ROM")
    header = int.from_bytes(data[0x18E:0x190], "big")
    computed = md_checksum(data)
    if header != computed:
        raise ValueError(
            f"{label} checksum mismatch: header {header:04X}, computed {computed:04X}"
        )


def patch_normal(
    scenario: int,
    normal: bytes,
    source: bytes,
) -> bytearray:
    definition = PROBE_DEFINITIONS[scenario]
    module = definition["module"]
    if not isinstance(module, ModuleType):
        raise TypeError(f"Scenario {scenario} probe module is invalid")
    probe = bytearray(normal)
    kwargs = dict(definition["kwargs"])
    if scenario == 10:
        module.patch_probe(probe, **kwargs)
    else:
        module.patch_probe(probe, source, **kwargs)
    require_valid_rom(probe, f"Scenario {scenario} normal probe")
    return probe


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
    normal = args.normal_rom.read_bytes()
    hard = args.hard_rom.read_bytes()
    source = args.source_rom.read_bytes()
    require_valid_rom(normal, "normal candidate")
    require_valid_rom(hard, "hard candidate")
    if args.output_root.exists():
        raise FileExistsError(f"output root already exists: {args.output_root}")

    normal_root = args.output_root / "normal"
    hard_root = args.output_root / "hard"
    normal_root.mkdir(parents=True)
    hard_root.mkdir(parents=True)
    rows = []
    for scenario in args.scenarios:
        definition = PROBE_DEFINITIONS[scenario]
        filename = str(definition["filename"])
        normal_probe = patch_normal(scenario, normal, source)
        hard_probe, delta, conflicts = overlay_hard(normal, normal_probe, hard)
        normal_path = normal_root / filename
        hard_path = hard_root / filename
        normal_path.write_bytes(normal_probe)
        hard_path.write_bytes(hard_probe)
        rows.append(
            {
                "scenario": scenario,
                "status": "pass",
                "builder_module": definition["module"].__name__,
                "builder_kwargs": definition["kwargs"],
                "normal": rom_report(normal_path, normal_probe),
                "hard": rom_report(hard_path, hard_probe),
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
        "candidate_roms": {
            "normal": rom_report(args.normal_rom, normal),
            "hard": rom_report(args.hard_rom, hard),
        },
        "source_rom": {
            "path": relative(args.source_rom),
            "sha256": sha256_bytes(source),
            "bytes": len(source),
        },
        "scenarios": list(args.scenarios),
        "probe_count": len(rows) * 2,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_HARD_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--scenarios",
        type=parse_scenarios,
        default=SCENARIOS,
        help="comma-separated subset of 10,12..27",
    )
    args = parser.parse_args()
    for name in ("normal_rom", "hard_rom", "source_rom", "output_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (
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
