from pathlib import Path
import tempfile
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_class_change_probe_rom as class_probe
from tools import run_production_runestone_resume_probe as resume_probe


ROOT = Path(__file__).resolve().parents[1]


class ProductionRunestoneResumeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not resume_probe.DEFAULT_ROM.is_file():
            raise unittest.SkipTest("exact v1.3.7 Original ROM is absent")
        cls.release = resume_probe.DEFAULT_ROM.read_bytes()

    def test_cases_cover_three_commanders_and_tiers_three_through_five(self):
        self.assertEqual(set(resume_probe.CASES), {"keith", "lester", "jessica"})
        for definition in resume_probe.CASES.values():
            self.assertEqual(sorted(definition["classes"]), [3, 4, 5])
            self.assertEqual(
                definition["marker_address"],
                builder.JOIN_CLASS_CHOICE_RECORDS[
                    definition["commander_id"]
                ]["active_marker_address"],
            )
            self.assertNotIn("unexpected_join_bonus_state", definition)

    def test_unscoped_regrant_prediction_uses_current_fixed_raw_policy(self):
        expected = {
            "keith": (0x04, 7, 1, 0, 0x00),
            "lester": (0x05, 9, 5, 16, 0x90),
            "jessica": (0x08, 10, 7, 0, 0x60),
        }
        for name, definition in resume_probe.CASES.items():
            with self.subTest(character=name):
                result = resume_probe.unscoped_fixed_grant_prediction(
                    self.release,
                    commander_id=definition["commander_id"],
                    selected_class=definition["selected_class"],
                )
                self.assertEqual(
                    (
                        result["class_id"],
                        result["commander_id"],
                        result["level"],
                        result["experience"],
                        result["fixed_raw_experience"],
                    ),
                    expected[name],
                )

    def test_probe_preserves_production_resume_and_clears_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "probe.md"
            report = resume_probe.build_probe(
                resume_probe.DEFAULT_ROM,
                output,
                character="lester",
                tier=4,
                expected_sha256=resume_probe.DEFAULT_ROM_SHA256,
            )
            probe = output.read_bytes()

        resume = class_probe.CLASS_CHANGE_RESUME_OPERAND
        self.assertEqual(
            self.release[resume : resume + 4],
            builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER.to_bytes(4, "big"),
        )
        self.assertEqual(probe[resume : resume + 4], self.release[resume : resume + 4])
        visibility = builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK
        self.assertEqual(
            probe[
                visibility : visibility
                + len(builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL)
            ],
            builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK_ORIGINAL,
        )
        setup = resume_probe.marker_clear_instruction(0x00403FE9)
        wrapper = class_probe.PROBE_WRAPPER
        self.assertEqual(probe[wrapper : wrapper + len(setup)], setup)
        expected_forced = class_probe.wrapper_code(
            runtime_record_index=0,
            expected_class=0x1B,
            forced_commander_id=9,
            probe_experience=class_probe.class_change_experience(
                self.release, 0x1B
            ),
            equipped_item=class_probe.RUNESTONE_ITEM_ID,
        )
        self.assertEqual(
            probe[
                wrapper + len(setup) : wrapper + len(setup) + len(expected_forced)
            ],
            expected_forced,
        )
        self.assertTrue(report["class_change_resume_operand"]["preserved_from_release"])

    def test_existing_forced_application_probe_bypasses_production_resume(self):
        probe = bytearray(self.release)
        class_probe.patch_probe(
            probe,
            self.release,
            commander_id=9,
            current_class=0x1B,
            runtime_record_index=0,
            enable_start_menu_probe=False,
            force_runtime_context=True,
            restore_commander_id=1,
            runestone_restart=True,
        )
        resume = class_probe.CLASS_CHANGE_RESUME_OPERAND
        self.assertEqual(
            probe[resume : resume + 4],
            class_probe.POST_APPLY_WRAPPER.to_bytes(4, "big"),
        )
        self.assertNotEqual(
            probe[resume : resume + 4],
            self.release[resume : resume + 4],
        )


if __name__ == "__main__":
    unittest.main()
