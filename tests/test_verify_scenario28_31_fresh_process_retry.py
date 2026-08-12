from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools import verify_scenario28_31_fresh_process_retry as verifier


ROOT = Path(__file__).resolve().parents[1]


class VerifyScenario28To31FreshProcessRetryTests(unittest.TestCase):
    def test_distinct_processes_and_homes_with_same_seed_pass(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            seed = root / "seed.gst"
            rom = root / "probe.md"
            seed.write_bytes(b"seed")
            rom.write_bytes(b"rom")

            def evidence(attempt: int, status: str) -> Path:
                path = root / f"attempt-{attempt}.json"
                data = {
                    "status": status,
                    "retry_policy": "external_fresh_process_only",
                    "fresh_process_attempt": attempt,
                    "input_seed_gst": {
                        "path": str(seed),
                        "sha256": verifier.sha256(seed),
                    },
                    "runtime_session": {
                        "pid": 100 + attempt,
                        "proc_start_time_ticks": 1000 + attempt,
                        "runtime_home": str(root / f"runtime-{attempt}"),
                        "observed_home": str(root / f"runtime-{attempt}"),
                        "display": ":977",
                        "observed_display": ":977",
                        "isolated_virtual_display": True,
                        "probe_rom": str(rom),
                        "probe_rom_sha256": verifier.sha256(rom),
                    },
                    "actions": [{"keys": ["c"], "delay_seconds": 1.0}],
                }
                path.write_text(json.dumps(data), encoding="utf-8")
                return path

            report = verifier.verify_pair(
                evidence(1, "failed_attempt"),
                evidence(2, "pass"),
            )

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["same_input_seed"])
        self.assertEqual(report["synthetic_load_actions"]["failed"], [])

    def test_reused_home_and_load_alias_fail(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            seed = root / "seed.gst"
            rom = root / "probe.md"
            seed.write_bytes(b"seed")
            rom.write_bytes(b"rom")
            paths = []
            for attempt, status in ((1, "failed_attempt"), (2, "pass")):
                path = root / f"attempt-{attempt}.json"
                path.write_text(
                    json.dumps(
                        {
                            "status": status,
                            "retry_policy": "external_fresh_process_only",
                            "fresh_process_attempt": attempt,
                            "input_seed_gst": {
                                "path": str(seed),
                                "sha256": verifier.sha256(seed),
                            },
                            "runtime_session": {
                                "pid": attempt,
                                "proc_start_time_ticks": attempt,
                                "runtime_home": str(root / "same-runtime"),
                                "observed_home": str(root / "same-runtime"),
                                "display": ":977",
                                "observed_display": ":977",
                                "isolated_virtual_display": True,
                                "probe_rom": str(rom),
                                "probe_rom_sha256": verifier.sha256(rom),
                            },
                            "actions": [{"keys": ["load"]}],
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
            report = verifier.verify_pair(*paths)

        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("reused one runtime HOME" in e for e in report["errors"]))
        self.assertTrue(any("synthetic load actions" in e for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
