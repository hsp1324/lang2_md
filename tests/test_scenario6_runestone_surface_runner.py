from pathlib import Path
import tempfile
import unittest

from tools import build_scenario6_runestone_probe_rom as probe_builder
from tools import run_blastem_sequence as blastem
from tools import run_preparation_surface_matrix as preparation
from tools import run_scenario6_runestone_surface as runner


class Scenario6RunestoneSurfaceRunnerTests(unittest.TestCase):
    def test_inventory_reader_uses_the_serialized_c7f2_table(self) -> None:
        highest = max(
            address + size
            for address, size in preparation.MANUAL_SLOT_WORK_RAM_SEGMENTS
        )
        gst = bytearray(preparation.GST_WORK_RAM_FILE_OFFSET + highest)
        inventory = (
            preparation.GST_WORK_RAM_FILE_OFFSET
            + preparation.MANUAL_SLOT_WORK_RAM_SEGMENTS[-1][0]
        )
        gst[inventory:inventory + 6] = bytes.fromhex("01 FF 1A FF FF FF")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "inventory.gst"
            path.write_bytes(gst)
            records = runner.inventory_records(path)
        self.assertEqual(len(records), 40)
        self.assertEqual(records[:3], [(0x01, 0xFF), (0x1A, 0xFF), (0xFF, 0xFF)])

    def test_acquisition_requires_one_empty_to_unequipped_runestone_change(self) -> None:
        empty = [(0xFF, 0xFF)] * blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT
        after = list(empty)
        after[7] = (runner.RUNESTONE_ITEM_ID, 0xFF)
        report = runner.runestone_acquisition_report(empty, after)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["changed_record_count"], 1)
        self.assertEqual(report["changes"][0]["slot"], 7)
        self.assertEqual(report["runestone_count_before"], 0)
        self.assertEqual(report["runestone_count_after"], 1)

        corruptions = []
        wrong_owner = list(after)
        wrong_owner[7] = (runner.RUNESTONE_ITEM_ID, 0x01)
        corruptions.append(wrong_owner)
        extra_change = list(after)
        extra_change[8] = (0x01, 0xFF)
        corruptions.append(extra_change)
        no_change = list(empty)
        corruptions.append(no_change)
        for changed in corruptions:
            with self.subTest(changed=changed[7:9]):
                self.assertEqual(
                    runner.runestone_acquisition_report(empty, changed)["status"],
                    "fail",
                )

    def test_acquisition_allows_existing_items_but_not_replacing_them(self) -> None:
        before = [(0x01, 0xFF), (0x1A, 0xFF)] + [
            (0xFF, 0xFF)
        ] * (blastem.MANUAL_SLOT_ITEM_INVENTORY_COUNT - 2)
        after = list(before)
        after[2] = (0x1A, 0xFF)
        report = runner.runestone_acquisition_report(before, after)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["runestone_count_before"], 1)
        self.assertEqual(report["runestone_count_after"], 2)

        replaced = list(before)
        replaced[0] = (0x1A, 0xFF)
        self.assertEqual(
            runner.runestone_acquisition_report(before, replaced)["status"],
            "fail",
        )

    def test_probe_delta_accepts_only_checksum_and_two_coordinate_bytes(self) -> None:
        size = probe_builder.FIRST_PLAYER_DEPLOYMENT + 8
        candidate = bytearray(size)
        probe = bytearray(candidate)
        for offset in (
            0x18F,
            probe_builder.FIRST_PLAYER_DEPLOYMENT + 1,
            probe_builder.FIRST_PLAYER_DEPLOYMENT + 3,
        ):
            probe[offset] ^= 1
        report = runner.probe_delta_report(bytes(candidate), bytes(probe))
        self.assertEqual(report["status"], "pass")

        probe[probe_builder.FIRST_PLAYER_DEPLOYMENT + 2] ^= 1
        self.assertEqual(
            runner.probe_delta_report(bytes(candidate), bytes(probe))["status"],
            "fail",
        )

    def test_runner_is_profile_complete_and_version_neutral(self) -> None:
        self.assertEqual(runner.PROFILES, ("pure", "normal", "hard"))
        self.assertEqual(runner.SCENARIO_NUMBER, 6)
        self.assertEqual(runner.EXPECTED_START, (6, 4))
        self.assertEqual(runner.EXPECTED_DESTINATION, (7, 4))
        self.assertNotIn("v1.3.6", runner.__doc__ or "")


if __name__ == "__main__":
    unittest.main()
