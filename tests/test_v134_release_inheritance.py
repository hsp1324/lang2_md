from pathlib import Path
import unittest

from tools.rom_update import bps_apply
from tools.class_change_data import read_class_change_chain
from tools.build_hard_mode_rom import (
    FIXED_RECORD_SIZE,
    SOLDIER_CORRECTION_AREA_END,
    SOLDIER_CORRECTION_HOOK,
    SOLDIER_CORRECTION_ROUTINE,
    load_applied_plan,
    verify_applied_hard_mode,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class V134ReleaseInheritanceTests(unittest.TestCase):
    """Lock the v1.3.1 through v1.3.5 regression and repair boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        if not SOURCE_ROM.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_ROM.read_bytes()

    def release_rom(self, patch_name: str) -> bytes:
        return bps_apply((ROOT / "patches" / patch_name).read_bytes(), self.source)

    def test_released_join_regression_boundary_is_v132(self) -> None:
        releases = {
            "v1.3.1": self.release_rom("normal-v1.3.1.bps"),
            "v1.3.2": self.release_rom("new-design-normal-v1.3.2.bps"),
            "v1.3.3": self.release_rom("normal-v1.3.3.bps"),
            "v1.3.4": self.release_rom("normal-v1.3.4.bps"),
            "v1.3.5": self.release_rom("normal-v1.3.5.bps"),
        }
        roster = 0x05E64A
        size = 0x0E
        records = {
            release: {
                commander_id: payload[
                    roster + (commander_id - 1) * size :
                    roster + commander_id * size
                ]
                for commander_id in (7, 9, 10)
            }
            for release, payload in releases.items()
        }

        # v1.3.1 is the last release with the legacy Fighter LV10 records.
        self.assertEqual(records["v1.3.1"][7][0:3], bytes.fromhex("01 01 0A"))
        self.assertEqual(records["v1.3.1"][9][0:3], bytes.fromhex("01 01 0A"))
        for release in ("v1.3.2", "v1.3.3", "v1.3.4", "v1.3.5"):
            self.assertEqual(records[release][7][0:3], bytes.fromhex("06 01 0A"))
            self.assertEqual(records[release][9][0:3], bytes.fromhex("07 01 0A"))
            self.assertEqual(records[release][10][0:3], bytes.fromhex("03 0E 0A"))

        # v1.3.1..v1.3.3 all enter the guard through the exact-LV10 compare,
        # which makes a damaged LV11/LV12 record unreachable. v1.3.4 starts
        # with identity dispatch so it can repair the record first.
        guard = 0x31E200
        level_compare = bytes.fromhex("0C 28 00 0A 00 2E")
        keith_identity = bytes.fromhex("0C 28 00 07 00 01")
        for release in ("v1.3.1", "v1.3.2", "v1.3.3"):
            self.assertEqual(releases[release][guard : guard + 6], level_compare)
        self.assertEqual(releases["v1.3.4"][guard : guard + 6], keith_identity)
        self.assertEqual(releases["v1.3.5"][guard : guard + 6], keith_identity)

        # The Rune Stone always restarts from the first class-chain record.
        # v1.3.2 replaced that Fighter record to make room for the join-only
        # Lord classes, so the later releases reproduce the reported wrong
        # first choices even though their join roster is otherwise repaired.
        self.assertEqual(
            read_class_change_chain(releases["v1.3.1"], 7)[0],
            read_class_change_chain(self.source, 7)[0],
        )
        self.assertEqual(
            read_class_change_chain(releases["v1.3.1"], 9)[0],
            read_class_change_chain(self.source, 9)[0],
        )
        for release in ("v1.3.2", "v1.3.3", "v1.3.4"):
            with self.subTest(release=release, commander="Keith"):
                first = read_class_change_chain(releases[release], 7)[0]
                self.assertEqual(first.current_class, 0x2B)
                self.assertEqual(first.candidates, (0x0D, 0x0F, 0x12))
            with self.subTest(release=release, commander="Lester"):
                first = read_class_change_chain(releases[release], 9)[0]
                self.assertEqual(first.current_class, 0x2C)
                self.assertEqual(first.candidates, (0x0D, 0x10, 0x12))

        # v1.3.5 relocates the longer join-only chains. Their live first rows
        # are once again the stock Runestone Fighter transitions, while the
        # new Hawk/Croco Lord rows remain reachable later in each chain.
        for commander_id, custom_class in ((7, 0x2B), (9, 0x2C)):
            with self.subTest(commander_id=commander_id):
                repaired = read_class_change_chain(
                    releases["v1.3.5"], commander_id
                )
                self.assertEqual(
                    repaired[0],
                    read_class_change_chain(self.source, commander_id)[0],
                )
                self.assertIn(custom_class, {
                    transition.current_class for transition in repaired
                })

        self.assertEqual(releases["v1.3.4"][0x1838F8], 0x65)
        self.assertEqual(releases["v1.3.5"][0x1838F8], 0x66)

    def test_v133_release_content_is_preserved_byte_for_byte(self) -> None:
        profiles = {
            "pure": {
                "old": "original-v1.3.3.bps",
                "new": "original-v1.3.4.bps",
                "version_offsets": {0x00016F, 0x2B7EEA},
                "changed_count": 225,
            },
            "normal": {
                "old": "normal-v1.3.3.bps",
                "new": "normal-v1.3.4.bps",
                "version_offsets": {0x00016A, 0x2B7EEA},
                "changed_count": 225,
            },
        }
        checksum_offsets = {0x00018E, 0x00018F}
        recovery_area = set(range(0x31E200, 0x31E316))

        for profile, spec in profiles.items():
            with self.subTest(profile=profile):
                old = self.release_rom(str(spec["old"]))
                new = self.release_rom(str(spec["new"]))
                changed = {
                    index
                    for index, (before, after) in enumerate(zip(old, new))
                    if before != after
                }
                allowed = (
                    set(spec["version_offsets"])
                    | checksum_offsets
                    | recovery_area
                )
                self.assertEqual(len(changed), spec["changed_count"])
                self.assertEqual(changed - allowed, set())
                self.assertTrue(set(spec["version_offsets"]) <= changed)
                self.assertTrue(checksum_offsets <= changed)
                self.assertTrue(changed & recovery_area)

    def test_v134_repairs_v133_standard_hard_balance_omission(self) -> None:
        old = self.release_rom("hard-v1.3.3.bps")
        new = self.release_rom("hard-v1.3.4.bps")
        verify_applied_hard_mode(new)

        plan = load_applied_plan()
        hard_record_bytes = {
            offset
            for scenario in plan["scenarios"]
            for record in scenario["records"]
            for offset in range(
                int(record["offset"], 16),
                int(record["offset"], 16) + FIXED_RECORD_SIZE,
            )
        }
        version_offsets = {0x00016A, 0x000171, 0x2B8A12, 0x2B8A32}
        checksum_offsets = {0x00018E, 0x00018F}
        recovery_area = set(range(0x31E200, 0x31E316))
        hard_loader = set(range(SOLDIER_CORRECTION_HOOK, 0x010E9C))
        hard_expansion = set(range(
            SOLDIER_CORRECTION_ROUTINE,
            SOLDIER_CORRECTION_AREA_END,
        ))
        changed = {
            index
            for index, (before, after) in enumerate(zip(old, new))
            if before != after
        }
        allowed = (
            version_offsets
            | checksum_offsets
            | recovery_area
            | hard_loader
            | hard_expansion
            | hard_record_bytes
        )
        self.assertEqual(len(changed), 1628)
        self.assertEqual(changed - allowed, set())
        self.assertTrue(version_offsets <= changed)
        self.assertTrue(hard_loader & changed)
        self.assertTrue(hard_record_bytes & changed)

    def test_standard_hard_layer_was_present_in_v132_and_missing_in_v133(self) -> None:
        v132 = self.release_rom("new-design-hard-t1.3.2-b1.3.2.bps")
        v133 = self.release_rom("hard-v1.3.3.bps")
        verify_applied_hard_mode(v132)
        with self.assertRaisesRegex(ValueError, "hook is absent"):
            verify_applied_hard_mode(v133)


if __name__ == "__main__":
    unittest.main()
