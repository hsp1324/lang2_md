from __future__ import annotations

import argparse
import ast
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_current_result_revalidation_parallel as result_parallel
from tools import run_scenario28_31_result_surface as surface
from tools import run_sequential_campaign_revalidation as campaign
from tools import run_v137_final_gate as final_gate


ROOT = Path(__file__).resolve().parents[1]
AFFECTED_SCENARIOS = (11, 12, 13, 18, 19, 20, 28, 29, 30, 31)


class Scenario28To31RetrySafetyTests(unittest.TestCase):
    def campaign_retry_row(self) -> dict[str, object]:
        seed = ROOT / "tmp/retry-safety-seed.gst"
        sessions = [
            {
                "pid": 101,
                "proc_start_time_ticks": 1001,
                "runtime_home": "/tmp/runtime-attempt-1",
                "observed_home": "/tmp/runtime-attempt-1",
                "display": ":977",
                "observed_display": ":977",
                "isolated_virtual_display": True,
            },
            {
                "pid": 202,
                "proc_start_time_ticks": 2002,
                "runtime_home": "/tmp/runtime-attempt-2",
                "observed_home": "/tmp/runtime-attempt-2",
                "display": ":977",
                "observed_display": ":977",
                "isolated_virtual_display": True,
            },
        ]
        return {
            "display": ":977",
            "attempt": 2,
            "retry_policy": "external_fresh_process_only",
            "runtime_session": sessions[1],
            "input_state": {
                "path": str(seed),
                "gst_sha256": "a" * 64,
            },
            "attempt_history": [
                {
                    "attempt": 1,
                    "returncode": 1,
                    "status": "failed_attempt",
                    "fresh_process_attempt": 1,
                    "runtime_session": sessions[0],
                    "input_seed_gst": {
                        "path": str(seed),
                        "sha256": "a" * 64,
                    },
                },
                {
                    "attempt": 2,
                    "returncode": 0,
                    "status": "pass",
                    "fresh_process_attempt": 2,
                    "runtime_session": sessions[1],
                    "input_seed_gst": {
                        "path": str(seed),
                        "sha256": "a" * 64,
                    },
                },
            ],
            "command": [
                "tools/run_scenario28_31_result_surface.py",
                "--fresh-process-attempt",
                "2",
            ],
        }

    def test_final_gate_accepts_only_distinct_whole_process_retry_proof(
        self,
    ) -> None:
        row = self.campaign_retry_row()
        errors: list[str] = []
        final_gate.verify_campaign_process_retry(
            row,
            scenario=28,
            errors=errors,
        )
        self.assertEqual(errors, [])

        row["attempt_history"][1]["runtime_session"]["runtime_home"] = (
            "/tmp/runtime-attempt-1"
        )
        row["attempt_history"][1]["runtime_session"]["observed_home"] = (
            "/tmp/runtime-attempt-1"
        )
        errors = []
        final_gate.verify_campaign_process_retry(
            row,
            scenario=28,
            errors=errors,
        )
        self.assertTrue(any("reused one runtime HOME" in error for error in errors))

    def test_final_gate_rejects_removed_internal_attack_retry_options(self) -> None:
        row = self.campaign_retry_row()
        row["command"].extend(("--attack-attempts", "2"))
        errors: list[str] = []
        final_gate.verify_campaign_process_retry(
            row,
            scenario=31,
            errors=errors,
        )
        self.assertTrue(any("removed in-process retry" in error for error in errors))

    def test_fresh_runner_has_no_fake_load_or_restore_path(self) -> None:
        path = ROOT / "tools/run_scenario28_31_result_surface.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        self.assertFalse(hasattr(surface, "restore_quicksave"))
        self.assertFalse(
            hasattr(surface, "attack_scenario31_until_defeated")
        )
        self.assertFalse(
            hasattr(surface, "attack_scenario13_vargas_until_defeated")
        )
        load_literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and (node.value == "load" or node.value.startswith("load:"))
        }
        self.assertEqual(load_literals, set())

    def test_all_affected_routes_use_the_single_attempt_fresh_runner(self) -> None:
        args = argparse.Namespace(
            probe_root=ROOT / "tmp/probes",
            seed_gst=ROOT / "tmp/input.gst",
            output_root=ROOT / "tmp/output",
            runtime_root=ROOT / "tmp/runtime",
            run_id="retry-safety",
        )
        for scenario in AFFECTED_SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    result_parallel.RUNNERS[scenario],
                    "run_scenario28_31_result_surface.py",
                )
                command = result_parallel.task_command(
                    args,
                    "pure",
                    scenario,
                    ":977",
                )
                self.assertIn(str(args.seed_gst), command)
                self.assertEqual(
                    command[command.index("--fresh-process-attempt") + 1],
                    "1",
                )
                self.assertNotIn("--attack-attempts", command)
                self.assertNotIn("--retry-rng-delay", command)

    def test_s28_failure_retries_whole_runner_from_same_seed_then_branches(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            initial = root / "initial.gst"
            initial.write_bytes(b"initial")
            s28_output = root / "s28"
            s13_output = root / "s13"
            s28_save = s28_output / "states/save_menu.gst"
            args = argparse.Namespace(
                seed_gsts={"pure": initial},
                release_roms={
                    "pure": {"path": "pure.md", "sha256": "1" * 64}
                },
                attempts=2,
                output_root=root,
                run_id="s28-whole-runner-retry",
            )
            input_calls = 0
            runner_seeds: list[Path] = []
            fresh_attempts: list[int] = []
            runner_calls = 0

            def snapshot(path: Path) -> dict[str, object]:
                nonlocal input_calls
                if path == s28_save:
                    return {"scenario": 13, "record_sha256": "after-s28"}
                input_calls += 1
                if input_calls == 2:
                    return {"scenario": 13, "record_sha256": "before-s28"}
                return {"scenario": 1, "record_sha256": "initial"}

            def task_output(
                _root: Path,
                _profile: str,
                scenario: int,
                _run_id: str,
            ) -> Path:
                return s28_output if scenario == 28 else s13_output

            def run_one(
                task_args: argparse.Namespace,
                _profile: str,
                scenario: int,
                _display: str,
            ) -> dict[str, object]:
                nonlocal runner_calls
                runner_calls += 1
                runner_seeds.append(task_args.seed_gst)
                fresh_attempts.append(task_args.fresh_process_attempt)
                output = s28_output if scenario == 28 else s13_output
                output.mkdir(parents=True, exist_ok=True)
                if scenario == 28 and runner_calls == 1:
                    (output / "failed-attempt-marker").write_bytes(b"failed")
                    return {
                        "profile": "pure",
                        "scenario": scenario,
                        "returncode": 1,
                        "status": "failed_attempt",
                    }
                self.assertFalse((output / "failed-attempt-marker").exists())
                if scenario == 28:
                    s28_save.parent.mkdir(parents=True, exist_ok=True)
                    s28_save.write_bytes(b"after-s28")
                return {
                    "profile": "pure",
                    "scenario": scenario,
                    "returncode": 0,
                    "status": "pass",
                }

            with (
                mock.patch.object(campaign, "FULL_ROUTE_ORDER", (28, 13)),
                mock.patch.object(
                    campaign,
                    "NEXT_SCENARIO",
                    {28: 13, 13: None},
                ),
                mock.patch.object(
                    campaign,
                    "expected_input_scenario",
                    side_effect=(13, 13),
                ),
                mock.patch.object(
                    campaign,
                    "state_snapshot",
                    side_effect=snapshot,
                ),
                mock.patch.object(
                    campaign.result_parallel,
                    "task_output",
                    side_effect=task_output,
                ),
                mock.patch.object(
                    campaign.result_parallel,
                    "run_one",
                    side_effect=run_one,
                ),
                mock.patch.object(
                    campaign,
                    "save_menu_gst",
                    return_value=s28_save,
                ),
                mock.patch.object(
                    campaign.matrix,
                    "terminate_blastem_processes",
                ) as terminate,
            ):
                report = campaign.run_profile(args, "pure", ":977")

        self.assertEqual(report["status"], "pass")
        self.assertEqual(runner_seeds, [initial, initial, s28_save])
        self.assertEqual(fresh_attempts, [1, 2, 1])
        self.assertEqual(
            [row["scenario"] for row in report["results"]],
            [28, 13],
        )
        self.assertEqual(
            report["results"][0]["attempt_history"],
            [
                {
                    "attempt": 1,
                    "returncode": 1,
                    "status": "failed_attempt",
                    "elapsed_seconds": None,
                    "xvfb_restarted_before_attempt": False,
                    "fresh_process_attempt": None,
                    "runtime_session": None,
                    "input_seed_gst": None,
                },
                {
                    "attempt": 2,
                    "returncode": 0,
                    "status": "pass",
                    "elapsed_seconds": None,
                    "xvfb_restarted_before_attempt": False,
                    "fresh_process_attempt": None,
                    "runtime_session": None,
                    "input_seed_gst": None,
                },
            ],
        )
        terminate.assert_called_once_with(display=":977")


if __name__ == "__main__":
    unittest.main()
