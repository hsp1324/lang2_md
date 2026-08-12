from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from tools import run_first_turn_surface_parallel as first_turn
from tools import verify_hard_mode_first_turn as hard_first_turn


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FirstTurnSurfaceParallelTests(unittest.TestCase):
    def test_seed_gst_is_a_required_cli_argument(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "run_first_turn_surface_parallel.py",
                "--profile",
                "pure",
                "--rom",
                "candidate.md",
                "--campaign-summary",
                "campaign.json",
                "--run-id",
                "unit-test",
            ],
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    first_turn.parse_args()
        self.assertEqual(raised.exception.code, 2)

    def test_campaign_summary_is_a_required_cli_argument(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "run_first_turn_surface_parallel.py",
                "--profile",
                "pure",
                "--rom",
                "candidate.md",
                "--seed-gst",
                "fresh.gst",
                "--run-id",
                "unit-test",
            ],
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    first_turn.parse_args()
        self.assertEqual(raised.exception.code, 2)

    def test_load_campaign_scenario_seeds_maps_the_complete_route(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            rom = root / "candidate.md"
            fresh = root / "fresh-s1.gst"
            summary = root / "campaign.json"
            rom.write_bytes(b"rom")
            fresh.write_bytes(b"fresh")
            rows = []
            expected_paths = {}
            expected_hashes = {}
            for route_index, scenario in enumerate(
                first_turn.campaign.FULL_ROUTE_ORDER
            ):
                serialized_scenario = (
                    first_turn.campaign.expected_input_scenario(route_index)
                )
                if scenario == 1:
                    state = fresh
                else:
                    state = root / f"route-input-{route_index:02d}-s{scenario:02d}.gst"
                    state.write_bytes(
                        f"campaign-input-{route_index}-{scenario}".encode()
                    )
                expected_paths[scenario] = state.resolve()
                expected_hashes[scenario] = digest(state)
                rows.append(
                    {
                        "scenario": scenario,
                        "status": "pass",
                        "returncode": 0,
                        "route_index": route_index,
                        "run_id": "unit-test",
                        "manual_intervention": False,
                        "input_state": {
                            "scenario": serialized_scenario,
                            "path": str(state),
                            "gst_sha256": expected_hashes[scenario],
                            "record_sha256": hashlib.sha256(
                                f"record-{route_index}-{scenario}".encode()
                            ).hexdigest(),
                        },
                    }
                )
            summary.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "run_id": "unit-test",
                        "profiles": list(first_turn.campaign.PROFILES),
                        "manual_intervention": False,
                        "automation_only": True,
                        "continuous_save_chain": True,
                        "release_roms_unchanged": True,
                        "release_roms": {
                            "normal": {"sha256": digest(rom)}
                        },
                        "release_roms_after": {
                            "normal": {"sha256": digest(rom)}
                        },
                        "route_order": list(
                            first_turn.campaign.FULL_ROUTE_ORDER
                        ),
                        "results": [
                            {
                                "profile": "normal",
                                "status": "pass",
                                "run_id": "unit-test",
                                "release_rom": {"sha256": digest(rom)},
                                "manual_intervention": False,
                                "passed_steps": len(rows),
                                "total_steps": len(rows),
                                "results": rows,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = first_turn.load_campaign_scenario_seeds(
                summary,
                profile="normal",
                run_id="unit-test",
                rom_sha256=digest(rom),
                fresh_seed=fresh,
                fresh_seed_sha256=digest(fresh),
            )

        self.assertEqual(set(result), set(range(1, 32)))
        self.assertEqual(
            first_turn.resolve_report_path(result[1]["path"]),
            expected_paths[1],
        )
        self.assertEqual(result[1]["source"], "fresh_s1_seed")
        s20_index = list(first_turn.campaign.FULL_ROUTE_ORDER).index(20)
        self.assertEqual(result[20]["route_index"], s20_index)
        self.assertEqual(result[20]["source"], "continuous_campaign_input")
        self.assertEqual(result[28]["serialized_scenario"], 13)
        self.assertEqual(result[29]["serialized_scenario"], 20)
        self.assertEqual(result[30]["serialized_scenario"], 23)
        self.assertEqual(result[31]["serialized_scenario"], 27)
        self.assertEqual(
            first_turn.resolve_report_path(result[20]["path"]),
            expected_paths[20],
        )
        self.assertEqual(result[20]["sha256"], expected_hashes[20])
        self.assertEqual(
            result[20]["record_sha256"],
            rows[s20_index]["input_state"]["record_sha256"],
        )

    def test_old_loader_seed_fallback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            fresh = root / "fresh.gst"
            legacy = root / "legacy-captures-analysis.gst"
            entry = root / "entry.gst"
            loader_results = root / "loader.json"
            fresh.write_bytes(b"fresh")
            legacy.write_bytes(b"legacy")
            entry.write_bytes(b"entry")
            loader_data = {
                "hard_rom": {"sha256": "r" * 64},
                "scenarios": [
                    {
                        "number": 20,
                        "seed": str(legacy),
                        "seed_sha256": digest(legacy),
                        "gst": str(entry),
                        "gst_sha256": digest(entry),
                    }
                ],
            }
            first_turn_data = {
                "scenarios": [
                    {
                        "number": 20,
                        "entry_evidence": {
                            "kind": "loader_smoke",
                            "manifest": str(loader_results),
                            "manifest_rom_sha256": "r" * 64,
                            "gst": str(entry),
                            "gst_sha256": digest(entry),
                            "manifest_gst_sha256": digest(entry),
                        },
                    }
                ]
            }
            with self.assertRaisesRegex(
                RuntimeError,
                "explicit_seed_path_match",
            ):
                first_turn.verify_loader_entry_source_lineage(
                    scenario=20,
                    loader_data=loader_data,
                    first_turn_data=first_turn_data,
                    loader_results=loader_results,
                    first_turn_results=root / "first-turn.json",
                    seed_gst=fresh,
                    seed_sha256=digest(fresh),
                    rom_sha256="r" * 64,
                )

    def test_strict_first_turn_entry_forbids_deep_manifest_fallback(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            loader = root / "loader.json"
            deep = root / "deep.json"
            loader.write_text('{"scenarios": []}', encoding="utf-8")
            deep.write_text(
                json.dumps(
                    {
                        "hard_rom": {"sha256": "d" * 64},
                        "scenarios": [
                            {
                                "number": 20,
                                "status": "runtime_loader_verified",
                                "gst": "historical.gst",
                                "gst_sha256": "e" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "no entry in required loader manifest",
            ):
                hard_first_turn.entry_evidence(
                    20,
                    loader_results_path=loader,
                    deep_results_path=deep,
                    require_loader_entry=True,
                )

    def test_run_one_passes_exact_seed_to_loader_and_records_lineage(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            rom = root / "candidate.md"
            seed = root / "fresh-s1.gst"
            entry = root / "s20-entry.gst"
            rom.write_bytes(b"rom")
            seed.write_bytes(b"fresh-seed")
            entry.write_bytes(b"entry")
            rom_sha256 = digest(rom)
            commands: list[list[str]] = []

            def fake_run(command: list[str]) -> str:
                commands.append(command)
                results = Path(command[command.index("--results") + 1])
                if command[1].endswith("verify_hard_mode_scenario_runtime.py"):
                    results.write_text(
                        json.dumps(
                            {
                                "hard_rom": {"sha256": rom_sha256},
                                "scenarios": [
                                    {
                                        "number": 20,
                                        "seed": str(seed),
                                        "seed_sha256": digest(seed),
                                        "gst": str(entry),
                                        "gst_sha256": digest(entry),
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )
                else:
                    loader_results = root / "s20" / "loader.json"
                    results.write_text(
                        json.dumps(
                            {
                                "scenarios": [
                                    {
                                        "number": 20,
                                        "endpoint": "turn_2_command",
                                        "turn_counter": 2,
                                        "entry_evidence": {
                                            "kind": "loader_smoke",
                                            "manifest": str(loader_results),
                                            "manifest_rom_sha256": rom_sha256,
                                            "gst": str(entry),
                                            "gst_sha256": digest(entry),
                                            "manifest_gst_sha256": digest(entry),
                                        },
                                    }
                                ]
                            }
                        ),
                        encoding="utf-8",
                    )
                return "ok\n"

            with (
                mock.patch.object(first_turn, "run", side_effect=fake_run),
                mock.patch.object(
                    first_turn.parallel,
                    "start_xvfb",
                    return_value=mock.Mock(),
                ),
                mock.patch.object(first_turn.parallel, "stop_process"),
                mock.patch.object(
                    first_turn.sequence,
                    "running_blastem_pids",
                    return_value=[],
                ),
            ):
                result = first_turn.run_one(
                    20,
                    rom=rom,
                    display=":977",
                    output_root=root,
                    evidence_prefix="unit",
                    xvfb=Path("xvfb"),
                    xvfb_library_path=Path("xvfb-lib"),
                    emulator_speed=4,
                    profile="pure",
                    allow_unapproved_defeat=False,
                    seed_gst=seed,
                    seed_sha256=digest(seed),
                    seed_origin={
                        "path": str(seed),
                        "sha256": digest(seed),
                        "source": "continuous_campaign_input",
                    },
                )

        loader_command = commands[0]
        self.assertEqual(
            loader_command[loader_command.index("--entry-source-gst") + 1],
            str(seed),
        )
        self.assertIn("--require-loader-entry", commands[1])
        self.assertEqual(result["status"], "pass")
        self.assertTrue(
            result["entry_source_lineage"]["all_checks_pass"]
        )

    def test_missing_loader_row_stops_before_first_turn_fallback(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            rom = root / "candidate.md"
            seed = root / "fresh-s1.gst"
            rom.write_bytes(b"rom")
            seed.write_bytes(b"fresh-seed")
            commands: list[list[str]] = []

            def fake_run(command: list[str]) -> str:
                commands.append(command)
                results = Path(command[command.index("--results") + 1])
                results.write_text(
                    json.dumps(
                        {
                            "hard_rom": {"sha256": digest(rom)},
                            "scenarios": [],
                        }
                    ),
                    encoding="utf-8",
                )
                return "loader finished without the requested row\n"

            with (
                mock.patch.object(first_turn, "run", side_effect=fake_run),
                mock.patch.object(
                    first_turn.parallel,
                    "start_xvfb",
                    return_value=mock.Mock(),
                ),
                mock.patch.object(first_turn.parallel, "stop_process"),
                mock.patch.object(
                    first_turn.sequence,
                    "running_blastem_pids",
                    return_value=[],
                ),
            ):
                result = first_turn.run_one(
                    20,
                    rom=rom,
                    display=":977",
                    output_root=root,
                    evidence_prefix="unit",
                    xvfb=Path("xvfb"),
                    xvfb_library_path=Path("xvfb-lib"),
                    emulator_speed=4,
                    profile="pure",
                    allow_unapproved_defeat=False,
                    seed_gst=seed,
                    seed_sha256=digest(seed),
                    seed_origin={
                        "path": str(seed),
                        "sha256": digest(seed),
                        "source": "continuous_campaign_input",
                    },
                )

        self.assertEqual(len(commands), 1)
        self.assertEqual(result["status"], "fail")
        self.assertIn("exactly one Scenario 20 row", result["error"])


if __name__ == "__main__":
    unittest.main()
