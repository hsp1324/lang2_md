from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tools import run_runestone_restart_matrix as matrix


class RunestoneRestartMatrixTests(unittest.TestCase):
    def test_definitions_cover_all_requested_characters_and_tiers(self):
        self.assertEqual(list(matrix.CASES), ["keith", "lester", "jessica"])
        for definition in matrix.CASES.values():
            self.assertEqual(sorted(definition["classes"]), [2, 3, 4, 5])
            self.assertEqual(len(definition["first_candidates"]), 3)
            self.assertEqual(len(definition["candidate_labels"]), 3)
            self.assertEqual(len(definition["label_fingerprint"]), 64)

    def test_release_profiles_have_expected_reachable_rows(self):
        for profile, path in matrix.DEFAULT_ROMS.items():
            with self.subTest(profile=profile, path=path.name):
                self.assertIn("1.3.7", path.name)
                report = matrix.validate_profile_rom(
                    path, matrix.DEFAULT_ROM_SHA256[profile]
                )
                self.assertEqual(set(report["cases"]), set(matrix.CASES))
                self.assertEqual(
                    report["sha256"], matrix.DEFAULT_ROM_SHA256[profile]
                )

    def test_release_profile_hash_lock_rejects_other_build(self):
        path = matrix.DEFAULT_ROMS["pure"]
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            matrix.validate_profile_rom(path, "0" * 64)

    def test_command_uses_release_chain_and_real_runestone(self):
        args = SimpleNamespace(
            output=Path("/tmp/runestone-test"),
            run_id="unit",
            roms=matrix.DEFAULT_ROMS,
            initial_delay=1.0,
            confirmation_delay=0.2,
            max_confirmations=20,
            stability_delay=1.0,
        )
        command = matrix.task_command(
            args,
            profile="normal",
            character="keith",
            tier=5,
            display=":777",
        )
        self.assertIn("--runestone-restart", command)
        self.assertIn("--preserve-production-resume", command)
        self.assertIn("--clear-join-marker", command)
        self.assertIn("--capture-all-candidates", command)
        self.assertIn("--bypass-join-visibility", command)
        source_index = command.index("--source-rom") + 1
        input_index = command.index("--input-rom") + 1
        self.assertEqual(command[source_index], command[input_index])
        self.assertEqual(command[command.index("--candidate-index") + 1], "2")

    def test_probe_contract_preserves_resume_and_clears_marker_first(self):
        source_bytes = bytearray(matrix.DEFAULT_ROMS["pure"].read_bytes())
        expected_wrapper = (
            matrix.application.builder.build_join_class_choice_level_wrapper()
        )
        wrapper = matrix.application.builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER
        source_bytes[wrapper : wrapper + len(expected_wrapper)] = expected_wrapper
        source = bytes(source_bytes)
        probe = bytearray(source)
        matrix.application.probe_builder.patch_probe(
            probe,
            source,
            commander_id=9,
            current_class=0x1B,
            runtime_record_index=0,
            enable_start_menu_probe=False,
            force_runtime_context=True,
            runestone_restart=True,
            preserve_production_resume=True,
            clear_join_marker=True,
        )
        production = matrix.production_resume_report(source, bytes(probe))
        marker = matrix.marker_setup_report(
            source,
            bytes(probe),
            character="lester",
            tier=4,
        )
        self.assertEqual(production["status"], "pass")
        self.assertTrue(production["release_wrapper_matches_current_builder"])
        self.assertEqual(marker["status"], "pass")
        self.assertEqual(marker["marker_address"], "0x00403FE9")
        self.assertTrue(marker["clear_precedes_stock_handler"])

    def test_runtime_marker_report_hash_binds_exact_zero_sram_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime_home = Path(directory)
            save = runtime_home / "isolated/save.sram"
            save.parent.mkdir()
            payload = bytearray(matrix.SRAM_BYTES)
            offset = (0x00403FE9 - matrix.SRAM_START_ADDRESS) // 2
            save.write_bytes(payload)
            report = matrix.runtime_join_marker_report(runtime_home, 9)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["bytes"], matrix.SRAM_BYTES)
            self.assertEqual(report["address"], "0x00403FE9")
            self.assertEqual(report["sram_offset"], f"0x{offset:04X}")
            self.assertEqual(report["value"], 0)
            self.assertEqual(len(report["sha256"]), 64)

            payload[offset] = 0xA5
            save.write_bytes(payload)
            self.assertEqual(
                matrix.runtime_join_marker_report(runtime_home, 9)["status"],
                "fail",
            )


if __name__ == "__main__":
    unittest.main()
