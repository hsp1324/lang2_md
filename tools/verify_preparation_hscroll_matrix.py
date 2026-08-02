#!/usr/bin/env python3
"""Verify H-scroll ownership in every current preparation matrix state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import analyze_preparation_vram_ownership as ownership
from tools import run_preparation_surface_matrix as matrix
from tools import verify_preparation_manual_reviews as manual


DEFAULT_CAPTURE_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_IDENTITY_REPORT = (
    ROOT / "tmp/full_surface_regression/current-source-20260802-01/"
    "preparation-scenario-identity.json"
)
DEFAULT_MANUAL_REPORT = ROOT / "localization/preparation_manual_review_current_candidate.json"
DEFAULT_OWNERSHIP_REPORT = ROOT / "localization/preparation_vram_ownership.json"
DEFAULT_NORMAL_ROM = ROOT / "tmp/current-source-audit-normal.md"
DEFAULT_HARD_ROM = ROOT / "tmp/current-source-audit-hard.md"
DEFAULT_OUTPUT = ROOT / "localization/preparation_hscroll_current_candidate.json"
PROFILES = ("normal", "hard")
SCENARIOS = tuple(range(1, 28))
PHASES = ("pre_shop", "shop_item_list", "post_shop")
EXPECTED_HSCROLL_MODE = 0
EXPECTED_HSCROLL_BASE = 0xF400
EXPECTED_HSCROLL_END = 0xF7FF


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def hscroll_payload(state: ownership.GstVdpState) -> bytes:
    start = state.hscroll_base
    return state.vram[start:start + ownership.HSCROLL_TABLE_BYTES]


def state_report(path: Path) -> dict[str, object]:
    state = ownership.load_gst(path)
    scroll = hscroll_payload(state)
    nonzero = sum(bool(value) for value in scroll)
    pool = tuple(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS)
    inside = [
        tile
        for tile in pool
        if state.hscroll_base
        <= tile * ownership.TILE_BYTES
        < state.hscroll_base + ownership.HSCROLL_TABLE_BYTES
    ]
    require_equal(state.hscroll_mode, EXPECTED_HSCROLL_MODE, f"{path} H-scroll mode")
    require_equal(state.hscroll_base, EXPECTED_HSCROLL_BASE, f"{path} H-scroll base")
    require_equal(nonzero, 0, f"{path} nonzero H-scroll bytes")
    require_equal(inside, [], f"{path} dynamic tiles inside H-scroll")
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "vdp_register_11": f"0x{state.registers[11]:02X}",
        "vdp_register_13": f"0x{state.registers[13]:02X}",
        "hscroll_mode": state.hscroll_mode,
        "hscroll_base": f"0x{state.hscroll_base:04X}",
        "hscroll_end": f"0x{state.hscroll_base + ownership.HSCROLL_TABLE_BYTES - 1:04X}",
        "hscroll_sha256": hashlib.sha256(scroll).hexdigest(),
        "nonzero_hscroll_bytes": nonzero,
        "dynamic_tiles_inside_hscroll": [f"0x{tile:04X}" for tile in inside],
        "status": "pass",
    }


def identity_row(
    document: dict[str, object], profile: str, scenario: int
) -> dict[str, object]:
    profile_report = document["profiles"][profile]
    rows = [row for row in profile_report["scenarios"] if row["scenario"] == scenario]
    if len(rows) != 1:
        raise ValueError(f"identity report has {len(rows)} rows for {profile} Scenario {scenario}")
    return rows[0]


def manual_row(
    document: dict[str, object], profile: str, scenario: int
) -> dict[str, object]:
    profile_report = document["profiles"][profile]
    rows = [row for row in profile_report["scenarios"] if row["scenario"] == scenario]
    if len(rows) != 1:
        raise ValueError(f"manual report has {len(rows)} rows for {profile} Scenario {scenario}")
    return rows[0]


def verify_scenario(
    *,
    capture_root: Path,
    identity: dict[str, object],
    manual_report: dict[str, object],
    profile: str,
    scenario: int,
) -> dict[str, object]:
    identity_evidence = identity_row(identity, profile, scenario)
    manual_evidence = manual_row(manual_report, profile, scenario)
    run_id = manual_evidence.get("run_id")
    if not isinstance(run_id, str):
        raise ValueError("manual review row has no run ID")
    require_equal(identity_evidence.get("status"), "pass", "scenario identity status")
    require_equal(manual_evidence.get("status"), "pass", "manual review status")
    require_equal(identity_evidence.get("run_id"), run_id, "identity run ID")
    require_equal(manual_evidence.get("run_id"), run_id, "manual review run ID")
    require_equal(
        identity_evidence["identity"]["identified_scenario"],
        scenario,
        "identified scenario",
    )
    evidence_path = (
        capture_root / profile / f"s{scenario:02d}" / run_id / "evidence.json"
    )
    require_equal(identity_evidence.get("evidence"), relative(evidence_path), "identity evidence path")
    require_equal(identity_evidence.get("evidence_sha256"), sha256(evidence_path), "identity evidence hash")
    state_directory = evidence_path.parent / "states"
    states = {
        phase: state_report(state_directory / f"{phase}.gst")
        for phase in PHASES
    }
    require_equal(
        identity_evidence.get("gst_sha256"),
        states["pre_shop"]["sha256"],
        "identity pre-shop GST hash",
    )
    require_equal(
        states["pre_shop"]["hscroll_sha256"],
        states["post_shop"]["hscroll_sha256"],
        "pre/post H-scroll payload hash",
    )
    return {
        "scenario": scenario,
        "run_id": run_id,
        "status": "pass",
        "identified_scenario": scenario,
        "evidence": relative(evidence_path),
        "evidence_sha256": sha256(evidence_path),
        "states": states,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    identity = json.loads(args.identity_report.read_text(encoding="utf-8"))
    manual_report = json.loads(args.manual_report.read_text(encoding="utf-8"))
    ownership_report = json.loads(args.ownership_report.read_text(encoding="utf-8"))
    require_equal(identity.get("status"), "pass", "identity report status")
    require_equal(manual_report.get("status"), "pass", "manual report status")

    roms = {"normal": args.normal_rom, "hard": args.hard_rom}
    profiles: dict[str, object] = {}
    for profile in PROFILES:
        rom = roms[profile]
        identity_rom = identity["profiles"][profile]["rom"]
        manual_rom = manual_report["candidate_roms"][profile]
        require_equal(identity_rom["sha256"], sha256(rom), f"{profile} identity ROM hash")
        require_equal(manual_rom["sha256"], sha256(rom), f"{profile} manual ROM hash")
        rows = [
            verify_scenario(
                capture_root=args.capture_root,
                identity=identity,
                manual_report=manual_report,
                profile=profile,
                scenario=scenario,
            )
            for scenario in SCENARIOS
        ]
        profiles[profile] = {
            "status": "pass",
            "rom": {
                "path": relative(rom),
                "sha256": sha256(rom),
                "md_checksum": matrix.md_checksum(rom),
            },
            "passed_scenarios": len(rows),
            "total_scenarios": len(SCENARIOS),
            "states_checked": len(rows) * len(PHASES),
            "nonzero_hscroll_states": 0,
            "scenarios": rows,
        }

    historical = ownership_report["historical_collision"]
    require_equal(historical.get("historical_tiles_inside_hscroll"), True, "historical collision location")
    if int(historical.get("nonzero_hscroll_bytes", 0)) <= 0:
        raise ValueError("historical collision report has no nonzero H-scroll bytes")
    pool = tuple(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS)
    pool_rows = [
        {
            "tile": f"0x{tile:04X}",
            "vram_start": f"0x{tile * ownership.TILE_BYTES:04X}",
            "vram_end": f"0x{tile * ownership.TILE_BYTES + ownership.TILE_BYTES - 1:04X}",
            "outside_hscroll": not (
                EXPECTED_HSCROLL_BASE
                <= tile * ownership.TILE_BYTES
                <= EXPECTED_HSCROLL_END
            ),
        }
        for tile in pool
    ]
    if not all(row["outside_hscroll"] for row in pool_rows):
        raise ValueError("current dynamic tile pool overlaps H-scroll")
    return {
        "schema_version": 1,
        "status": "pass",
        "scope": "scenario_1_to_27_pre_shop_shop_and_post_shop_hscroll_ownership",
        "requirements": {
            "profiles": list(PROFILES),
            "scenarios": list(SCENARIOS),
            "states_per_scenario": list(PHASES),
            "expected_hscroll_mode": EXPECTED_HSCROLL_MODE,
            "expected_hscroll_base": f"0x{EXPECTED_HSCROLL_BASE:04X}",
            "expected_hscroll_end": f"0x{EXPECTED_HSCROLL_END:04X}",
            "expected_nonzero_hscroll_bytes": 0,
        },
        "dynamic_tile_pool": {
            "tile_count": len(pool_rows),
            "all_outside_hscroll": True,
            "tiles": pool_rows,
        },
        "historical_collision_reference": {
            "path": relative(args.ownership_report),
            "sha256": sha256(args.ownership_report),
            "hscroll_base": historical["hscroll_base"],
            "hscroll_end": historical["hscroll_end"],
            "nonzero_hscroll_bytes": historical["nonzero_hscroll_bytes"],
            "historical_tiles_inside_hscroll": historical["historical_tiles_inside_hscroll"],
        },
        "identity_report": {
            "path": relative(args.identity_report),
            "sha256": sha256(args.identity_report),
        },
        "manual_review_report": {
            "path": relative(args.manual_report),
            "sha256": sha256(args.manual_report),
        },
        "total_profile_scenario_runs": len(PROFILES) * len(SCENARIOS),
        "total_states_checked": len(PROFILES) * len(SCENARIOS) * len(PHASES),
        "total_nonzero_hscroll_states": 0,
        "profiles": profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--identity-report", type=Path, default=DEFAULT_IDENTITY_REPORT)
    parser.add_argument("--manual-report", type=Path, default=DEFAULT_MANUAL_REPORT)
    parser.add_argument("--ownership-report", type=Path, default=DEFAULT_OWNERSHIP_REPORT)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_HARD_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name in (
        "capture_root",
        "identity_report",
        "manual_report",
        "ownership_report",
        "normal_rom",
        "hard_rom",
        "output",
    ):
        setattr(args, name, getattr(args, name).resolve())
    report = build_report(args)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"checked H-scroll matrix report is stale: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(
        f"pass: {report['total_profile_scenario_runs']} profile/scenario runs, "
        f"{report['total_states_checked']} GST states, "
        f"{report['total_nonzero_hscroll_states']} nonzero H-scroll states"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
