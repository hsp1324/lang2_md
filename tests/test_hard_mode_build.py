import hashlib
import json
from pathlib import Path
import unittest

from tools import build_hard_mode_rom as hard_builder
from tools import hard_mode_approval
from tools import hard_mode_baseline
from tools import hard_mode_plan
from tools import rom_version
from tools import rom_update


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
UPDATE_REGISTRY = (
    ROOT / "localization/hard_mode_update_releases.json"
)
PLAYTEST_ROM = (
    ROOT / "roms/releases/"
    "Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)


class HardModeBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = BASE_ROM.read_bytes()
        cls.plan = hard_mode_plan.build_plan()
        cls.approval = hard_mode_approval.require_approved()
        cls.hard, cls.manifest = hard_builder.apply_hard_mode(
            cls.base,
            cls.plan,
            cls.approval,
        )

    def test_build_applies_every_planned_record(self):
        pairs = sorted({
            (
                int(record["enemy_soldier_correction"]["at"]["planned"]),
                int(record["enemy_soldier_correction"]["df"]["planned"]),
            )
            for scenario in self.plan["scenarios"]
            for record in scenario["records"]
        })
        for scenario in self.plan["scenarios"]:
            for record in scenario["records"]:
                offset = int(record["offset"], 16)
                commander = record["commander"]
                soldier = record["enemy_soldier_correction"]
                mercenaries = record["mercenaries"]
                with self.subTest(
                    scenario=scenario["number"],
                    offset=record["offset"],
                ):
                    self.assertEqual(
                        hard_builder._signed_byte(
                            self.hard[
                                offset + hard_builder.COMMANDER_AT_OFFSET
                            ]
                        ),
                        commander["at"]["planned"],
                    )
                    self.assertEqual(
                        hard_builder._signed_byte(
                            self.hard[
                                offset + hard_builder.COMMANDER_DF_OFFSET
                            ]
                        ),
                        commander["df"]["planned"],
                    )
                    index = self.hard[
                        offset + hard_builder.HARD_CORRECTION_INDEX_OFFSET
                    ]
                    self.assertEqual(
                        pairs[index],
                        (
                            soldier["at"]["planned"],
                            soldier["df"]["planned"],
                        ),
                    )
                    self.assertEqual(
                        list(
                            self.hard[
                                offset + hard_builder.MERCENARY_OFFSET:
                                offset + hard_builder.FIXED_RECORD_SIZE
                            ]
                        ),
                        mercenaries["planned"],
                    )

    def test_scenario_one_exclusions_and_shared_classes_stay_unchanged(self):
        for offset in (0x1802FC, 0x180320):
            self.assertEqual(
                self.hard[offset:offset + hard_builder.FIXED_RECORD_SIZE],
                self.base[offset:offset + hard_builder.FIXED_RECORD_SIZE],
            )
        start = hard_mode_baseline.CLASS_RECORD_TABLE
        end = start + 157 * hard_mode_baseline.CLASS_RECORD_SIZE
        self.assertEqual(self.hard[start:end], self.base[start:end])

    def test_loader_uses_the_record_tag_and_expansion_pair_table(self):
        hook = hard_builder.correction_hook()
        routine = hard_builder.correction_routine()
        self.assertEqual(
            self.hard[
                hard_builder.SOLDIER_CORRECTION_HOOK:
                hard_builder.SOLDIER_CORRECTION_HOOK + len(hook)
            ],
            hook,
        )
        self.assertEqual(
            self.hard[
                hard_builder.SOLDIER_CORRECTION_ROUTINE:
                hard_builder.SOLDIER_CORRECTION_ROUTINE + len(routine)
            ],
            routine,
        )
        self.assertEqual(
            self.manifest["implementation"]["correction_pair_count"],
            67,
        )
        self.assertFalse(
            self.manifest["implementation"]["shared_class_records_modified"]
        )

    def test_only_owned_balance_ranges_change(self):
        allowed = {0x18E, 0x18F}
        allowed.update(
            range(
                hard_builder.SOLDIER_CORRECTION_HOOK,
                hard_builder.SOLDIER_CORRECTION_HOOK
                + len(hard_builder.correction_hook()),
            )
        )
        allowed.update(
            range(
                hard_builder.SOLDIER_CORRECTION_ROUTINE,
                hard_builder.SOLDIER_CORRECTION_ROUTINE
                + len(hard_builder.correction_routine()),
            )
        )
        pair_bytes = (
            self.manifest["implementation"]["correction_pair_count"] * 2
        )
        allowed.update(
            range(
                hard_builder.SOLDIER_CORRECTION_TABLE,
                hard_builder.SOLDIER_CORRECTION_TABLE + pair_bytes,
            )
        )
        for scenario in self.plan["scenarios"]:
            for record in scenario["records"]:
                offset = int(record["offset"], 16)
                allowed.update({
                    offset + hard_builder.COMMANDER_AT_OFFSET,
                    offset + hard_builder.COMMANDER_DF_OFFSET,
                    offset + hard_builder.HARD_CORRECTION_INDEX_OFFSET,
                })
                allowed.update(
                    range(
                        offset + hard_builder.MERCENARY_OFFSET,
                        offset + hard_builder.FIXED_RECORD_SIZE,
                    )
                )
        changed = {
            index
            for index, (before, after) in enumerate(
                zip(self.base, self.hard)
            )
            if before != after
        }
        self.assertTrue(changed)
        self.assertEqual(changed - allowed, set())

    def test_save_layout_size_and_checksum_remain_valid(self):
        self.assertEqual(len(self.hard), len(self.base))
        self.assertEqual(
            rom_update.md_sram_descriptor(self.hard),
            rom_update.md_sram_descriptor(self.base),
        )
        self.assertEqual(
            rom_update.md_checksum(self.hard),
            rom_update.md_header_checksum(self.hard),
        )
        self.assertTrue(
            self.manifest["save_compatibility"][
                "sram_descriptor_unchanged"
            ]
        )

    def test_playtest_candidate_registry_matches_the_built_rom(self):
        registry = json.loads(
            UPDATE_REGISTRY.read_text(encoding="utf-8")
        )
        self.assertEqual(
            registry["current_release"],
            "ko-hard-t1.0.0-b1.0.0",
        )
        self.assertTrue(
            registry["version_policy"][
                "keep_candidate_version_until_user_declares_release"
            ]
        )
        release = registry["releases"][0]
        playtest_payload = PLAYTEST_ROM.read_bytes()
        self.assertEqual(
            release["release_id"],
            rom_version.get_profile("hard")["release_id"],
        )
        self.assertEqual(
            release["sha256"],
            hashlib.sha256(playtest_payload).hexdigest(),
        )
        self.assertEqual(
            release["md_checksum"],
            f"{rom_update.md_header_checksum(playtest_payload):04X}",
        )
        self.assertEqual(
            release["sram_descriptor"],
            rom_update.md_sram_descriptor(playtest_payload).hex().upper(),
        )


if __name__ == "__main__":
    unittest.main()
