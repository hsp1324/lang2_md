from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from tools import build_current_result_probe_matrix as matrix
from tools import build_scenario27_ending_probe_rom as scenario27


ROOT = Path(__file__).resolve().parents[1]


class BuildCurrentResultProbeMatrixTests(unittest.TestCase):
    def test_default_candidates_are_exact_v137_release_roms(self):
        paths = {
            "pure": matrix.DEFAULT_PURE_ROM,
            "normal": matrix.DEFAULT_NORMAL_ROM,
            "hard": matrix.DEFAULT_HARD_ROM,
        }
        for profile, path in paths.items():
            with self.subTest(profile=profile):
                self.assertIn("1.3.7", path.name)
                data = path.read_bytes()
                matrix.require_valid_rom(
                    data,
                    profile,
                    matrix.DEFAULT_ROM_SHA256[profile],
                )

    def test_candidate_hash_lock_rejects_another_release(self):
        data = matrix.DEFAULT_PURE_ROM.read_bytes()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            matrix.require_valid_rom(data, "pure", "0" * 64)

    def test_canonical_japanese_source_lock_rejects_one_byte_mutation(self):
        source = bytearray(matrix.DEFAULT_SOURCE_ROM.read_bytes())
        matrix.require_canonical_source(source)
        source[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, "source ROM SHA-256 mismatch"):
            matrix.require_canonical_source(source)

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
                pure_rom=matrix.DEFAULT_PURE_ROM,
                normal_rom=matrix.DEFAULT_NORMAL_ROM,
                hard_rom=matrix.DEFAULT_HARD_ROM,
                source_rom=matrix.DEFAULT_SOURCE_ROM,
                output_root=output,
                scenarios=(14, 15),
            )
            report = matrix.build_matrix(args)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["probe_count"], 6)
            self.assertFalse(report["release_promoted"])
            self.assertFalse(report["version_bumped"])
            self.assertEqual(
                json.loads((output / "manifest.json").read_text()),
                report,
            )
            for row in report["probes"]:
                self.assertGreater(row["normal_diagnostic_payload_changed_bytes"], 0)
                for profile in ("pure", "normal", "hard"):
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

    def test_scenario27_one_hp_wrapper_is_identical_in_all_probe_profiles(self):
        pure = matrix.DEFAULT_PURE_ROM.read_bytes()
        normal = matrix.DEFAULT_NORMAL_ROM.read_bytes()
        hard = matrix.DEFAULT_HARD_ROM.read_bytes()
        source = matrix.DEFAULT_SOURCE_ROM.read_bytes()
        pure_probe = matrix.patch_pure(27, pure, source)
        normal_probe = matrix.patch_normal(27, normal, source)
        hard_probe, delta, _ = matrix.overlay_hard(normal, normal_probe, hard)
        direct_hard = bytearray(hard)
        scenario27.patch_probe(
            direct_hard,
            source,
            allow_balanced_input=True,
        )
        self.assertEqual(bytes(direct_hard), bytes(hard_probe))
        for before, after in (
            (pure, pure_probe),
            (normal, normal_probe),
            (hard, hard_probe),
        ):
            self.assertEqual(
                sum(left != right for left, right in zip(before, after)),
                31,
            )
            self.assertEqual(
                after[
                    scenario27.RUNTIME_WRAPPER :
                    scenario27.RUNTIME_WRAPPER
                    + len(scenario27.completion_hp_wrapper_code())
                ],
                scenario27.completion_hp_wrapper_code(),
            )
        self.assertEqual(len(delta), 31)
        expected_delta = matrix.diagnostic_delta_report(normal, normal_probe)
        self.assertEqual(expected_delta["changed_byte_count"], 31)
        self.assertEqual(expected_delta["payload_changed_byte_count"], 29)
        self.assertEqual(
            matrix.diagnostic_delta_report(hard, hard_probe),
            expected_delta,
        )

    def test_every_scenario_builds_a_checksum_valid_pure_probe(self):
        pure = matrix.DEFAULT_PURE_ROM.read_bytes()
        source = matrix.DEFAULT_SOURCE_ROM.read_bytes()
        for scenario in matrix.SCENARIOS:
            with self.subTest(scenario=scenario):
                probe = matrix.patch_pure(scenario, pure, source)
                self.assertEqual(len(probe), len(pure))
                self.assertEqual(
                    int.from_bytes(probe[0x18E:0x190], "big"),
                    matrix.md_checksum(probe),
                )
        self.assertEqual(pure, matrix.DEFAULT_PURE_ROM.read_bytes())

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
