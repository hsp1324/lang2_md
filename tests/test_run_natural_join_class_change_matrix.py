from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from tools import run_natural_join_class_change_matrix as matrix


class NaturalJoinClassChangeMatrixTests(unittest.TestCase):
    @staticmethod
    def candidate_rom() -> bytes:
        source = matrix.builder.IN_ROM.read_bytes()
        candidate = bytearray(source)
        matrix.builder.expand_rom(candidate)
        matrix.builder.patch_join_class_choice_class_data(candidate, source)
        return bytes(candidate)

    def test_natural_matrix_covers_every_tier_two_branch(self) -> None:
        rows = {case.slug: case for case in matrix.NATURAL_CASES}
        self.assertEqual(len(rows), 9)
        self.assertEqual(
            {
                (case.character.commander_id, case.candidate_index)
                for case in rows.values()
            },
            {
                (commander_id, candidate_index)
                for commander_id in (7, 9, 10)
                for candidate_index in (1, 2, 3)
            },
        )
        self.assertEqual(
            rows["natural-keith-default"].character.candidate_labels,
            ("로드", "호크로드", "힐러"),
        )
        self.assertEqual(rows["natural-keith-hawk-lord"].selected_class, 0x2B)
        self.assertEqual(rows["natural-keith-healer"].selected_class, 0x08)
        self.assertEqual(rows["natural-lester-croco-lord"].selected_class, 0x2C)
        self.assertEqual(
            rows["natural-jessica-default"].character.candidate_labels,
            ("힐러", "소서러", "로드"),
        )
        self.assertEqual(rows["natural-jessica-sorcerer"].selected_class, 0x09)
        self.assertEqual(rows["natural-jessica-lord"].selected_class, 0x04)

    def test_pending_probes_collapse_only_identical_natural_choice_screens(self) -> None:
        natural = matrix.pending_probe_representatives(matrix.NATURAL_CASES)
        self.assertEqual(
            [key for key, _case in natural],
            ["natural:keith", "natural:lester", "natural:jessica"],
        )
        self.assertEqual(
            [case.slug for _key, case in natural],
            [
                "natural-keith-default",
                "natural-lester-default",
                "natural-jessica-default",
            ],
        )

        legacy = matrix.pending_probe_representatives(matrix.LEGACY_CASES)
        self.assertEqual(len(legacy), 6)
        self.assertEqual(len({key for key, _case in legacy}), 6)
        self.assertTrue(all(":lv" in key for key, _case in legacy))

    def test_progression_expectations_use_one_profile_invariant_raw_grant(self) -> None:
        rom = self.candidate_rom()
        expected = {
            "natural-keith-default": (0x04, 1, 0),
            "natural-keith-hawk-lord": (0x2B, 1, 0),
            "natural-keith-healer": (0x08, 1, 0),
            "natural-lester-default": (0x05, 5, 16),
            "natural-lester-croco-lord": (0x2C, 7, 0),
            "natural-lester-shaman": (0x0A, 7, 0),
            "natural-jessica-default": (0x08, 7, 0),
            "natural-jessica-sorcerer": (0x09, 5, 0),
            "natural-jessica-lord": (0x04, 5, 0),
        }
        for profile in matrix.PROFILES:
            for case in matrix.NATURAL_CASES:
                with self.subTest(profile=profile, case=case.slug):
                    expectation = matrix.progression_expectation(
                        profile, case, rom
                    )
                    self.assertEqual(
                        matrix.expected_result_tuple(expectation),
                        expected[case.slug],
                    )
                    self.assertFalse(expectation["reaches_another_class_choice"])

    def test_original_level_basis_deliberately_excludes_residual_bars(self) -> None:
        report = matrix.original_experience_basis(
            matrix.builder.IN_ROM.read_bytes()
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            [row["fixed_raw_experience"] for row in report["rows"]],
            [0x00, 0x90, 0x60],
        )
        self.assertEqual(
            [row["original_residual_experience_excluded"] for row in report["rows"]],
            [5, 15, 0],
        )

    def test_runtime_sram_markers_use_odd_addresses_and_exact_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_home = Path(directory)
            save_path = runtime_home / "isolated/save.sram"
            save_path.parent.mkdir()
            expected_offsets = {
                matrix.KEITH.commander_id: 0x1FF3,
                matrix.LESTER.commander_id: 0x1FF4,
                matrix.JESSICA.commander_id: 0x1FF5,
            }
            for character in matrix.CHARACTERS:
                payload = bytearray(matrix.SRAM_BYTES)
                offset = expected_offsets[character.commander_id]
                payload[offset] = matrix.builder.JOIN_CLASS_CHOICE_PENDING_MARKER
                save_path.write_bytes(payload)
                marker = matrix.runtime_sram_marker(runtime_home, character)
                self.assertEqual(marker["sram_offset"], f"0x{offset:04X}")
                self.assertEqual(
                    marker["value"],
                    matrix.builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
                )
                self.assertEqual(
                    int(marker["address"], 16) & 1,
                    1,
                )

    def test_flush_checkpoint_proves_disk_marker_after_process_exit(self) -> None:
        class FakeRecorder:
            def __init__(self, runtime_home: Path) -> None:
                self.runtime_home = runtime_home
                self.display = ":910"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_home = root / "runtime-name"
            save = runtime_home / "isolated/save.sram"
            save.parent.mkdir(parents=True)
            payload = bytearray(matrix.SRAM_BYTES)
            payload[0x1FF3] = matrix.builder.JOIN_CLASS_CHOICE_PENDING_MARKER
            save.write_bytes(payload)
            recorder = FakeRecorder(runtime_home)

            with mock.patch.object(
                matrix.preparation,
                "terminate_blastem_processes",
            ) as terminate:
                report = matrix.flush_sram_checkpoint(
                    recorder,  # type: ignore[arg-type]
                    matrix.KEITH,
                    root / "marker.sram",
                    matrix.builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
                )

            terminate.assert_called_once_with(display=":910")
            self.assertEqual(report["status"], "pass")
            self.assertEqual(
                report["flushed_marker"]["value"],
                matrix.builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
            )
            self.assertEqual(report["policy"], "process_exit_flush")

    def test_legacy_matrix_exposes_fighter_lv10_through_lv12(self) -> None:
        self.assertEqual(len(matrix.LEGACY_CASES), 6)
        self.assertEqual(
            {
                (case.character.commander_id, case.legacy_level, case.scenario)
                for case in matrix.LEGACY_CASES
            },
            {
                (7, 10, 7),
                (7, 11, 7),
                (7, 12, 7),
                (9, 10, 10),
                (9, 11, 10),
                (9, 12, 10),
            },
        )

    def test_optional_later_legacy_matrix_is_distinct(self) -> None:
        self.assertEqual(len(matrix.LEGACY_LATER_CASES), 6)
        self.assertEqual(
            {
                (case.character.commander_id, case.legacy_level, case.scenario)
                for case in matrix.LEGACY_LATER_CASES
            },
            {
                (7, 10, 8),
                (7, 11, 8),
                (7, 12, 8),
                (9, 10, 11),
                (9, 11, 11),
                (9, 12, 11),
            },
        )
        self.assertTrue(
            all(case.group == "legacy-later" for case in matrix.LEGACY_LATER_CASES)
        )

    def test_case_selection_rejects_unknown_and_excluded_ids(self) -> None:
        selected = matrix.selected_cases(("natural",), ("natural-lester-croco-lord",))
        self.assertEqual(
            [case.slug for case in selected], ["natural-lester-croco-lord"]
        )
        with self.assertRaisesRegex(ValueError, "unknown case IDs"):
            matrix.selected_cases(("natural",), ("missing",))
        with self.assertRaisesRegex(ValueError, "excluded by --case-groups"):
            matrix.selected_cases(("natural",), ("legacy-lester-fighter-lv12",))

    def test_legacy_manual_slot_patch_is_exact_and_natural_is_none(self) -> None:
        natural = matrix.CASES_BY_SLUG["natural-lester-default"]
        legacy = matrix.CASES_BY_SLUG["legacy-lester-fighter-lv12"]
        self.assertIsNone(matrix.legacy_manual_slot_args(natural))
        self.assertEqual(
            matrix.legacy_manual_slot_args(legacy),
            [
                "--manual-slot-commander-id",
                "9",
                "--manual-slot-level",
                "12",
                "--manual-slot-experience",
                "15",
                "--manual-slot-expected-class",
                "0x07",
                "--manual-slot-class",
                "0x01",
            ],
        )

    def test_legacy_diagnostic_identity_override_is_exact_and_bounded(self) -> None:
        keith = matrix.CASES_BY_SLUG["legacy-keith-fighter-lv10"]
        lester = matrix.CASES_BY_SLUG["legacy-lester-fighter-lv12"]
        later = matrix.CASES_BY_SLUG["legacy-later-lester-fighter-lv12"]
        natural = matrix.CASES_BY_SLUG["natural-lester-default"]
        self.assertEqual(
            matrix.legacy_diagnostic_exact_overrides(keith),
            {(7, 3): {"name_id": 7, "class_id": 0x01, "level": 10}},
        )
        self.assertEqual(
            matrix.legacy_diagnostic_exact_overrides(lester),
            {(10, 1): {"name_id": 9, "class_id": 0x01, "level": 12}},
        )
        self.assertIsNone(matrix.legacy_diagnostic_exact_overrides(later))
        self.assertIsNone(matrix.legacy_diagnostic_exact_overrides(natural))
        self.assertEqual(
            matrix.diagnostic_override_report(lester),
            [
                {
                    "scenario": 10,
                    "fixed_record_index": 1,
                    "name_id": 9,
                    "class_id": 0x01,
                    "level": 12,
                }
            ],
        )

    def test_legacy_recovery_guard_truth_table(self) -> None:
        eligible = matrix.legacy_recovery_eligible
        self.assertTrue(
            eligible(
                matrix.KEITH,
                scenario=7,
                result_next_scenario=8,
                x=6,
                y=18,
                class_id=0x01,
                level=11,
            )
        )
        self.assertTrue(
            eligible(
                matrix.LESTER,
                scenario=10,
                result_next_scenario=11,
                x=0,
                y=12,
                class_id=0x01,
                level=12,
            )
        )
        negative = (
            # Pre-join scenario.
            dict(scenario=10, x=0, y=12, class_id=0x01, level=12),
            # Preparation placeholder and off-map reinforcement.
            dict(scenario=11, x=0, y=0, class_id=0x01, level=12),
            dict(scenario=11, x=0xFF, y=0xFF, class_id=0x01, level=12),
            # Already selected non-Fighter and Runestone Fighter below LV10.
            dict(scenario=11, x=0, y=12, class_id=0x07, level=12),
            dict(scenario=11, x=0, y=12, class_id=0x01, level=9),
        )
        for row in negative:
            with self.subTest(row=row):
                self.assertFalse(eligible(matrix.LESTER, **row))
        self.assertFalse(
            eligible(
                matrix.JESSICA,
                scenario=12,
                x=10,
                y=10,
                class_id=0x01,
                level=12,
            )
        )

    def test_effective_recovery_scenario_matches_result_boundary(self) -> None:
        exact = matrix.CASES_BY_SLUG["legacy-lester-fighter-lv12"]
        later = matrix.CASES_BY_SLUG["legacy-later-lester-fighter-lv12"]
        natural = matrix.CASES_BY_SLUG["natural-lester-default"]
        self.assertEqual(matrix.effective_recovery_scenario(exact), 11)
        self.assertEqual(matrix.effective_recovery_scenario(later), 11)
        self.assertEqual(matrix.effective_recovery_scenario(natural), 10)

    def test_group_parser_accepts_optional_later_group(self) -> None:
        self.assertEqual(
            matrix.parse_groups("legacy-later,natural"),
            ("legacy-later", "natural"),
        )

    def test_candidate_fingerprints_are_complete_and_unique(self) -> None:
        fingerprints = [row.label_fingerprint for row in matrix.CHARACTERS]
        self.assertEqual(len(set(fingerprints)), 3)
        self.assertTrue(all(len(value) == 64 for value in fingerprints))
        self.assertEqual(
            matrix.LESTER.candidates,
            (0x05, 0x2C, 0x0A),
        )

    def test_candidate_fingerprint_uses_only_bright_text_mask(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            changed = Path(directory) / "changed.png"
            images = [Image.new("RGB", (320, 240), (0, 0, 119)) for _ in range(3)]
            images[0].putpixel((90, 90), (255, 255, 255))
            images[1].putpixel((90, 90), (200, 200, 200))
            images[1].putpixel((100, 100), (149, 255, 255))
            images[2].putpixel((91, 90), (255, 255, 255))
            for image, path in zip(images, (first, second, changed)):
                image.save(path)
            self.assertEqual(
                matrix.candidate_label_fingerprint(first),
                matrix.candidate_label_fingerprint(second),
            )
            self.assertNotEqual(
                matrix.candidate_label_fingerprint(first),
                matrix.candidate_label_fingerprint(changed),
            )

    def test_candidate_fingerprint_rejects_wrong_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.png"
            Image.new("RGB", (160, 120)).save(path)
            with self.assertRaisesRegex(ValueError, "320x240"):
                matrix.candidate_label_fingerprint(path)

    def test_fresh_seed_requires_all_three_tier1_lv10_rows(self) -> None:
        snapshot = {
            "scenario": 1,
            "commanders": [
                {
                    "commander_id": commander_id,
                    "class_id": class_id,
                    "level": level,
                    "experience": experience,
                }
                for commander_id, class_id, level, experience in (
                    (7, 0x06, 10, 5),
                    (9, 0x07, 10, 15),
                    (10, 0x03, 10, 0),
                )
            ],
        }
        matrix.validate_fresh_seed(snapshot)
        snapshot["commanders"][1]["level"] = 11
        with self.assertRaisesRegex(ValueError, "Lester"):
            matrix.validate_fresh_seed(snapshot)
        snapshot["commanders"][1]["level"] = 10
        snapshot["commanders"][1]["experience"] = 16
        with self.assertRaisesRegex(ValueError, "Lester"):
            matrix.validate_fresh_seed(snapshot)

    def test_candidate_applied_result_and_save_validators(self) -> None:
        case = matrix.CASES_BY_SLUG["natural-lester-croco-lord"]
        candidate = {
            "class_id": 0x07,
            "level": 10,
            # Stock result EXP is awarded before this screen and is not the
            # fixed post-selection join grant.
            "experience": 25,
            "x": 16,
            "y": 13,
        }
        expectation = matrix.progression_expectation(
            "normal", case, self.candidate_rom()
        )
        matrix.validate_candidate_runtime(case, candidate)
        settling = {"class_id": 0x2C, "level": 2, "experience": 120}
        settlement = matrix.validate_applied_runtime(
            case, settling, expectation
        )
        self.assertEqual(settlement["status"], "settling")
        self.assertEqual(settlement["consumed_raw_experience"], 24)
        self.assertEqual(settlement["remaining_raw_experience"], 120)
        with self.assertRaisesRegex(ValueError, "mandatory stock scan"):
            matrix.validate_applied_runtime(
                case,
                {"class_id": 0x2C, "level": 1, "experience": 144},
                expectation,
            )
        result = {"class_id": 0x2C, "level": 7, "experience": 0}
        settled = matrix.validate_applied_runtime(case, result, expectation)
        self.assertEqual(settled["status"], "settled")
        matrix.validate_result_runtime(case, result, expectation)
        snapshot = {
            "scenario": 11,
            "commanders": [
                {
                    "commander_id": 9,
                    "class_id": 0x2C,
                    "level": 7,
                    "experience": 0,
                }
            ],
        }
        matrix.validate_save_persistence(case, snapshot, expectation)

        with self.assertRaisesRegex(ValueError, "candidate runtime"):
            matrix.validate_candidate_runtime(case, {**candidate, "x": 0xFF})
        with self.assertRaisesRegex(ValueError, "immediate application"):
            matrix.validate_applied_runtime(
                case,
                {"class_id": 0x05, "level": 1, "experience": 0},
                expectation,
            )
        with self.assertRaisesRegex(ValueError, "immediate application"):
            matrix.validate_applied_runtime(
                case,
                {"class_id": 0x2C, "level": 2, "experience": 119},
                expectation,
            )
        with self.assertRaisesRegex(ValueError, "result"):
            matrix.validate_result_runtime(
                case,
                {"class_id": 0x2C, "level": 8, "experience": 0},
                expectation,
            )
        with self.assertRaisesRegex(ValueError, "save scenario"):
            matrix.validate_save_persistence(
                case,
                {**snapshot, "scenario": 10},
                expectation,
            )

    def test_probe_paths_use_standard_matrix_filenames(self) -> None:
        root = Path("/tmp/probes")
        self.assertEqual(
            matrix.probe_path(root, "normal", 7),
            root / "normal/s07-runtime-clear.md",
        )
        self.assertEqual(
            matrix.probe_path(root, "normal", 10),
            root / "normal/s10.md",
        )
        self.assertEqual(
            matrix.probe_path(root, "normal", 11),
            root / "normal/s11-completion.md",
        )


if __name__ == "__main__":
    unittest.main()
