from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from tools import build_current_result_probe_matrix as matrix


ROOT = Path(__file__).resolve().parents[1]


class BuildCurrentResultProbeMatrixTests(unittest.TestCase):
    def test_early_and_scenario11_definitions_use_deterministic_completion(self):
        self.assertEqual(tuple(range(1, 32)), matrix.SCENARIOS)
        for scenario in (1, 2, 3, 4, 6, 7, 8, 9):
            self.assertTrue(
                matrix.PROBE_DEFINITIONS[scenario]["filename"].endswith(
                    "runtime-clear.md"
                )
            )
        self.assertEqual(
            matrix.PROBE_DEFINITIONS[4]["kwargs"],
            {"runtime_clear": True},
        )
        self.assertEqual(
            matrix.PROBE_DEFINITIONS[8]["kwargs"],
            {"runtime_clear": True},
        )
        self.assertEqual(
            matrix.PROBE_DEFINITIONS[11]["kwargs"],
            {"completion_layout": True},
        )
        self.assertEqual(
            matrix.PROBE_DEFINITIONS[30]["kwargs"],
            {"completion_target_only": True},
        )
        self.assertEqual(
            matrix.PROBE_DEFINITIONS[31]["kwargs"],
            {"completion_layout": True},
        )

    def test_scenario14_and_15_current_probes_are_valid_and_source_bound(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            output = Path(directory) / "probes"
            args = argparse.Namespace(
                normal_rom=matrix.DEFAULT_NORMAL_ROM,
                hard_rom=matrix.DEFAULT_HARD_ROM,
                source_rom=matrix.DEFAULT_SOURCE_ROM,
                output_root=output,
                scenarios=(14, 15),
            )
            report = matrix.build_matrix(args)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["probe_count"], 4)
            self.assertFalse(report["release_promoted"])
            self.assertFalse(report["version_bumped"])
            self.assertEqual(
                json.loads((output / "manifest.json").read_text()),
                report,
            )
            for row in report["probes"]:
                self.assertGreater(row["normal_diagnostic_payload_changed_bytes"], 0)
                for profile in ("normal", "hard"):
                    rom = output / profile / matrix.PROBE_DEFINITIONS[
                        row["scenario"]
                    ]["filename"]
                    data = rom.read_bytes()
                    self.assertEqual(len(data), 0x400000)
                    self.assertEqual(
                        int.from_bytes(data[0x18E:0x190], "big"),
                        matrix.md_checksum(data),
                    )

    def test_hard_overlay_changes_only_normal_diagnostic_delta_and_checksum(self):
        normal = matrix.DEFAULT_NORMAL_ROM.read_bytes()
        hard = matrix.DEFAULT_HARD_ROM.read_bytes()
        source = matrix.DEFAULT_SOURCE_ROM.read_bytes()
        normal_probe = matrix.patch_normal(14, normal, source)
        hard_probe, delta, _ = matrix.overlay_hard(normal, normal_probe, hard)
        actual = {
            offset
            for offset, (before, after) in enumerate(zip(hard, hard_probe))
            if before != after
        }
        self.assertTrue(actual <= (delta | matrix.CHECKSUM_OFFSETS))

    def test_output_root_must_be_new(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            args = argparse.Namespace(
                normal_rom=matrix.DEFAULT_NORMAL_ROM,
                hard_rom=matrix.DEFAULT_HARD_ROM,
                source_rom=matrix.DEFAULT_SOURCE_ROM,
                output_root=Path(directory),
                scenarios=(14,),
            )
            with self.assertRaisesRegex(FileExistsError, "output root already exists"):
                matrix.build_matrix(args)


if __name__ == "__main__":
    unittest.main()
