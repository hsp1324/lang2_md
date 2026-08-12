from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_preparation_surface_matrix as matrix


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class RuntimeFixedRecordLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rom = REFERENCE_ROM.read_bytes()

    def synthetic_fixed_runtime(self, scenario: int) -> bytearray:
        model = matrix.read_scenario(self.rom, self.rom, scenario)
        player_groups = matrix.player_commander_count(self.rom, scenario)
        runtime_size = (
            matrix.GST_WORK_RAM_FILE_OFFSET
            + matrix.RUNTIME_GROUP_BASE
            + (player_groups + model["record_count"])
            * matrix.RUNTIME_GROUP_SIZE
        )
        manual_slot_size = matrix.GST_WORK_RAM_FILE_OFFSET + max(
            address + size
            for address, size in matrix.MANUAL_SLOT_WORK_RAM_SEGMENTS
        )
        gst = bytearray(max(runtime_size, manual_slot_size))
        for row in model["records"]:
            group = player_groups + int(row["index"])
            start = (
                matrix.GST_WORK_RAM_FILE_OFFSET
                + matrix.RUNTIME_GROUP_BASE
                + group * matrix.RUNTIME_GROUP_SIZE
            )
            gst[start] = int(row["class_id"])
            gst[start + 1] = int(row["name"]["id"])
            gst[start + matrix.RUNTIME_SIDE_OFFSET] = int(row["side_id"])
            gst[start + matrix.RUNTIME_LEVEL_OFFSET] = int(row["level"])
            gst[start + 0x06] = int(row["x"])
            gst[start + 0x07] = int(row["y"])
            for member, class_id in enumerate(row["mercenaries"], 1):
                gst[start + member * matrix.RUNTIME_MEMBER_SIZE] = int(
                    class_id
                )
        # Opening/event progression imports are accepted only when the loaded
        # fixed record exactly matches that commander's serialized save row.
        for (override_scenario, record_index), override in (
            matrix.RUNTIME_FIXED_PROGRESS_OVERRIDES.items()
        ):
            if override_scenario != scenario:
                continue
            row = model["records"][record_index]
            commander_id = int(override["name_id"])
            serialized = (
                matrix.GST_WORK_RAM_FILE_OFFSET
                + matrix.MANUAL_SLOT_WORK_RAM_SEGMENTS[0][0]
                + matrix.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
                + (commander_id - 1)
                * matrix.MANUAL_SLOT_COMMANDER_RECORD_SIZE
            )
            gst[
                serialized + matrix.MANUAL_SLOT_COMMANDER_CLASS_OFFSET
            ] = int(row["class_id"])
            gst[
                serialized + matrix.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
            ] = int(row["level"])
        return gst

    def set_saved_progression(
        self,
        gst: bytearray,
        commander_id: int,
        *,
        class_id: int,
        level: int,
    ) -> None:
        serialized = (
            matrix.GST_WORK_RAM_FILE_OFFSET
            + matrix.MANUAL_SLOT_WORK_RAM_SEGMENTS[0][0]
            + matrix.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + (commander_id - 1) * matrix.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        gst[
            serialized + matrix.MANUAL_SLOT_COMMANDER_CLASS_OFFSET
        ] = class_id
        gst[
            serialized + matrix.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
        ] = level

    def record_start(self, scenario: int, record_index: int) -> int:
        player_groups = matrix.player_commander_count(self.rom, scenario)
        return (
            matrix.GST_WORK_RAM_FILE_OFFSET
            + matrix.RUNTIME_GROUP_BASE
            + (player_groups + record_index) * matrix.RUNTIME_GROUP_SIZE
        )

    def test_late_layout_checks_every_structural_fixed_record_field(self) -> None:
        scenario = 31
        gst = self.synthetic_fixed_runtime(scenario)
        report = matrix.verify_runtime_fixed_record_layout(
            bytes(gst),
            self.rom,
            self.rom,
            scenario,
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["fixed_record_count"], 10)
        self.assertEqual(report["mismatch_count"], 0)

        start = self.record_start(scenario, 0)
        protected_offsets = {
            "class_id": 0,
            "name_id": 1,
            "side_id": matrix.RUNTIME_SIDE_OFFSET,
            "level": matrix.RUNTIME_LEVEL_OFFSET,
            "x": 0x06,
            "y": 0x07,
            "mercenaries": matrix.RUNTIME_MEMBER_SIZE,
        }
        for field, relative in protected_offsets.items():
            with self.subTest(field=field):
                changed = bytearray(gst)
                changed[start + relative] ^= 1
                with self.assertRaisesRegex(
                    RuntimeError,
                    rf"record 0 .*{field}",
                ):
                    matrix.verify_runtime_fixed_record_layout(
                        bytes(changed),
                        self.rom,
                        self.rom,
                        scenario,
                    )

    def test_declared_progression_does_not_mask_identity_or_placement(self) -> None:
        scenario = 25
        gst = self.synthetic_fixed_runtime(scenario)
        start = self.record_start(scenario, 0)
        # This exact Scenario 25 Jessica record is declared to import her
        # class/level from the carried save during the opening.
        gst[start] ^= 1
        gst[start + matrix.RUNTIME_LEVEL_OFFSET] ^= 1
        self.set_saved_progression(
            gst,
            0x0A,
            class_id=gst[start],
            level=gst[start + matrix.RUNTIME_LEVEL_OFFSET],
        )
        report = matrix.verify_runtime_fixed_record_layout(
            bytes(gst),
            self.rom,
            self.rom,
            scenario,
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            set(report["records"][0]["progression_overrides"]),
            {"class_id", "level"},
        )

        for field, relative in {
            "name_id": 1,
            "side_id": matrix.RUNTIME_SIDE_OFFSET,
            "x": 0x06,
            "y": 0x07,
            "mercenaries": matrix.RUNTIME_MEMBER_SIZE,
        }.items():
            with self.subTest(field=field):
                changed = bytearray(gst)
                changed[start + relative] ^= 1
                with self.assertRaisesRegex(RuntimeError, field):
                    matrix.verify_runtime_fixed_record_layout(
                        bytes(changed),
                        self.rom,
                        self.rom,
                        scenario,
                    )

    def test_progression_override_must_match_the_identity_locked_save_row(self) -> None:
        scenario = 25
        gst = self.synthetic_fixed_runtime(scenario)
        start = self.record_start(scenario, 0)
        for field, relative in (
            ("class_id", 0),
            ("level", matrix.RUNTIME_LEVEL_OFFSET),
        ):
            with self.subTest(field=field):
                changed = bytearray(gst)
                changed[start + relative] ^= 1
                with self.assertRaisesRegex(RuntimeError, field):
                    matrix.verify_runtime_fixed_record_layout(
                        bytes(changed),
                        self.rom,
                        self.rom,
                        scenario,
                    )

        # Scenario 6 resident record 1 is also side 03, but it is not a saved
        # commander progression import and therefore gets no class exception.
        scenario = 6
        gst = self.synthetic_fixed_runtime(scenario)
        start = self.record_start(scenario, 1)
        gst[start] ^= 1
        with self.assertRaisesRegex(RuntimeError, "class_id"):
            matrix.verify_runtime_fixed_record_layout(
                bytes(gst),
                self.rom,
                self.rom,
                scenario,
            )

    def test_legacy_diagnostic_override_is_exact_closed_and_auditable(self) -> None:
        for scenario, record, name_id in ((7, 3, 0x07), (10, 1, 0x09)):
            for level in (10, 11, 12):
                with self.subTest(scenario=scenario, level=level):
                    gst = self.synthetic_fixed_runtime(scenario)
                    start = self.record_start(scenario, record)
                    gst[start] = 0x01
                    gst[start + matrix.RUNTIME_LEVEL_OFFSET] = level
                    exact = {
                        (scenario, record): {
                            "name_id": name_id,
                            "class_id": 0x01,
                            "level": level,
                        }
                    }

                    # Default release verification remains source/save strict.
                    with self.assertRaisesRegex(RuntimeError, "class_id"):
                        matrix.verify_runtime_fixed_record_layout(
                            bytes(gst), self.rom, self.rom, scenario
                        )

                    report = matrix.verify_runtime_fixed_record_layout(
                        bytes(gst),
                        self.rom,
                        self.rom,
                        scenario,
                        diagnostic_exact_overrides=exact,
                    )
                    self.assertEqual(report["status"], "pass")
                    self.assertEqual(
                        report["diagnostic_exact_overrides_requested"],
                        report["diagnostic_exact_overrides_used"],
                    )
                    self.assertEqual(
                        report["records"][record]["diagnostic_exact_override"],
                        exact[(scenario, record)],
                    )

                    wrong_runtime = bytearray(gst)
                    wrong_runtime[
                        start + matrix.RUNTIME_LEVEL_OFFSET
                    ] = 10 if level != 10 else 11
                    with self.assertRaisesRegex(RuntimeError, "level"):
                        matrix.verify_runtime_fixed_record_layout(
                            bytes(wrong_runtime),
                            self.rom,
                            self.rom,
                            scenario,
                            diagnostic_exact_overrides=exact,
                        )

    def test_legacy_diagnostic_override_rejects_any_scope_expansion(self) -> None:
        scenario = 7
        gst = self.synthetic_fixed_runtime(scenario)
        valid = {"name_id": 0x07, "class_id": 0x01, "level": 10}
        cases = (
            ({(6, 3): valid}, "scenario does not match"),
            ({(7, 2): valid}, "target is not permitted"),
            (
                {(7, 3): {**valid, "name_id": 0x09}},
                "name identity is not permitted",
            ),
            (
                {(7, 3): {**valid, "class_id": 0x02}},
                "class is not permitted",
            ),
            (
                {(7, 3): {**valid, "level": 9}},
                "level is not permitted",
            ),
            (
                {(7, 3): {"name_id": 0x07, "class_id": 0x01}},
                "must specify exactly",
            ),
        )
        for override, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    matrix.verify_runtime_fixed_record_layout(
                        bytes(gst),
                        self.rom,
                        self.rom,
                        scenario,
                        diagnostic_exact_overrides=override,
                    )

    def test_launch_forwards_the_exact_override_into_saved_gst_identity(self) -> None:
        exact = {
            (7, 3): {"name_id": 0x07, "class_id": 0x01, "level": 12}
        }

        class Recorder:
            def __init__(self) -> None:
                self.runtime_home = Path("/tmp/runtime/name")
                self.display = ":199"
                self.commands = []

            def run_command(self, command):
                self.commands.append(command)

            def save_gst(self, relative):
                return Path("/tmp") / relative

        recorder = Recorder()
        with mock.patch.object(
            matrix,
            "verify_runtime_scenario_identity",
            return_value={"status": "pass"},
        ) as verify:
            result = matrix.launch_to_preparation(
                recorder,
                Path("candidate.md"),
                Path("seed.gst"),
                7,
                "runtime-name",
                Path("output"),
                diagnostic_exact_overrides=exact,
            )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["attempt"], 1)
        verify.assert_called_once_with(
            Path("/tmp/briefing/attempt_1/scenario_identity.gst"),
            Path("candidate.md"),
            7,
            diagnostic_exact_overrides=exact,
        )

    def test_save_menu_scenario_reader_uses_the_serialized_runtime_record(self) -> None:
        highest = max(
            address + size
            for address, size in matrix.MANUAL_SLOT_WORK_RAM_SEGMENTS
        )
        gst = bytearray(matrix.GST_WORK_RAM_FILE_OFFSET + highest)
        scenario_address = (
            matrix.GST_WORK_RAM_FILE_OFFSET
            + matrix.MANUAL_SLOT_WORK_RAM_SEGMENTS[0][0]
        )
        gst[scenario_address : scenario_address + 2] = (27).to_bytes(2, "big")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "save-menu.gst"
            path.write_bytes(gst)
            self.assertEqual(matrix.manual_slot_scenario_from_gst(path), 27)

            gst[scenario_address : scenario_address + 2] = (0).to_bytes(2, "big")
            path.write_bytes(gst)
            with self.assertRaisesRegex(ValueError, "invalid scenario 0"):
                matrix.manual_slot_scenario_from_gst(path)


if __name__ == "__main__":
    unittest.main()
