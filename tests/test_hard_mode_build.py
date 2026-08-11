import hashlib
import json
from pathlib import Path
import unittest

from tools import build_hard_mode_rom as hard_builder
from tools import hard_mode_approval
from tools import hard_mode_baseline
from tools import rom_version
from tools import rom_update


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
UPDATE_REGISTRY = (
    ROOT / "localization/hard_mode_update_releases.json"
)
CURRENT_HARD_PROFILE = rom_version.get_profile("hard")
PLAYTEST_ROM = ROOT / "roms/builds" / CURRENT_HARD_PROFILE["rom_filename"]
PLAYTEST_BUILD = PLAYTEST_ROM
SUPERSEDED_PLAYTEST_ROM = (
    ROOT / "roms/releases/archive/"
    "Langrisser II (Korean Hard T1.0.0 B1.0.0 checksum-1011).md"
)
SUPERSEDED_5BE8_PLAYTEST_ROM = (
    ROOT / "roms/releases/archive/"
    "Langrisser II (Korean Hard T1.0.0 B1.0.0 checksum-5BE8).md"
)
SUPERSEDED_120_PLAYTEST_ROM = (
    ROOT / "roms/releases/"
    "Langrisser II (Korean Hard T1.2.0 B1.2.0).md"
)
SUPERSEDED_121_PLAYTEST_ROM = (
    ROOT / "roms/builds/"
    "Langrisser II (Korean Hard T1.2.1 B1.2.1).md"
)
SUPERSEDED_122_PLAYTEST_ROM = (
    ROOT / "roms/builds/"
    "Langrisser II (Korean Hard T1.2.2 B1.2.2).md"
)
SUPERSEDED_123_PLAYTEST_ROM = (
    ROOT / "roms/builds/"
    "Langrisser II (Korean Hard T1.2.3 B1.2.3).md"
)
SUPERSEDED_132_PLAYTEST_ROM = (
    ROOT / "roms/builds/"
    "Langrisser II (Korean Hard T1.3.2 B1.3.2).md"
)
SUPERSEDED_134_PLAYTEST_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Hard v1.3.4).md"
)


class HardModeBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = BASE_ROM.read_bytes()
        cls.plan = hard_builder.load_applied_plan()
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
            CURRENT_HARD_PROFILE["release_id"],
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
        self.assertEqual(playtest_payload, PLAYTEST_BUILD.read_bytes())

    def test_superseded_playtest_candidate_is_hash_locked(self):
        registry = json.loads(
            UPDATE_REGISTRY.read_text(encoding="utf-8")
        )
        history = registry["candidate_history"]
        self.assertEqual(len(history), 8)
        for predecessor, successor in zip(history, history[1:]):
            self.assertEqual(predecessor["superseded_by"], successor["sha256"])
        self.assertEqual(
            history[-1]["superseded_by"],
            registry["releases"][0]["sha256"],
        )
        retained = (
            SUPERSEDED_PLAYTEST_ROM,
            SUPERSEDED_5BE8_PLAYTEST_ROM,
            SUPERSEDED_120_PLAYTEST_ROM,
            SUPERSEDED_121_PLAYTEST_ROM,
            SUPERSEDED_122_PLAYTEST_ROM,
            SUPERSEDED_123_PLAYTEST_ROM,
            SUPERSEDED_132_PLAYTEST_ROM,
            SUPERSEDED_134_PLAYTEST_ROM,
        )
        if not all(path.is_file() for path in retained):
            self.skipTest("ignored superseded hard ROMs are absent")
        predecessor = history[0]
        payload = SUPERSEDED_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor["md_checksum"], "1011")
        self.assertEqual(
            predecessor["sha256"],
            hashlib.sha256(payload).hexdigest(),
        )
        self.assertEqual(
            predecessor["sram_descriptor"],
            rom_update.md_sram_descriptor(payload).hex().upper(),
        )
        self.assertEqual(
            predecessor["superseded_by"],
            history[1]["sha256"],
        )
        predecessor_5be8 = history[1]
        payload_5be8 = SUPERSEDED_5BE8_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_5be8["md_checksum"], "5BE8")
        self.assertEqual(
            predecessor_5be8["sha256"],
            hashlib.sha256(payload_5be8).hexdigest(),
        )
        self.assertEqual(
            predecessor_5be8["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_5be8).hex().upper(),
        )
        self.assertEqual(
            predecessor_5be8["superseded_by"],
            history[2]["sha256"],
        )
        predecessor_120 = history[2]
        payload_120 = SUPERSEDED_120_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_120["md_checksum"], "98BA")
        self.assertEqual(
            predecessor_120["sha256"],
            hashlib.sha256(payload_120).hexdigest(),
        )
        self.assertEqual(
            predecessor_120["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_120).hex().upper(),
        )
        self.assertEqual(
            predecessor_120["superseded_by"],
            history[3]["sha256"],
        )
        predecessor_121 = history[3]
        payload_121 = SUPERSEDED_121_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_121["md_checksum"], "C9BA")
        self.assertEqual(
            predecessor_121["sha256"],
            hashlib.sha256(payload_121).hexdigest(),
        )
        self.assertEqual(
            predecessor_121["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_121).hex().upper(),
        )
        self.assertEqual(
            predecessor_121["superseded_by"],
            history[4]["sha256"],
        )
        predecessor_122 = history[4]
        payload_122 = SUPERSEDED_122_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_122["md_checksum"], "2D37")
        self.assertEqual(
            predecessor_122["sha256"],
            hashlib.sha256(payload_122).hexdigest(),
        )
        self.assertEqual(
            predecessor_122["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_122).hex().upper(),
        )
        self.assertEqual(
            predecessor_122["superseded_by"],
            history[5]["sha256"],
        )
        predecessor_123 = history[5]
        payload_123 = SUPERSEDED_123_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_123["md_checksum"], "709E")
        self.assertEqual(
            predecessor_123["sha256"],
            hashlib.sha256(payload_123).hexdigest(),
        )
        self.assertEqual(
            predecessor_123["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_123).hex().upper(),
        )
        self.assertEqual(
            predecessor_123["superseded_by"],
            history[6]["sha256"],
        )
        predecessor_132 = history[6]
        payload_132 = SUPERSEDED_132_PLAYTEST_ROM.read_bytes()
        self.assertEqual(predecessor_132["md_checksum"], "F8E7")
        self.assertEqual(
            predecessor_132["sha256"],
            hashlib.sha256(payload_132).hexdigest(),
        )
        self.assertEqual(
            predecessor_132["sram_descriptor"],
            rom_update.md_sram_descriptor(payload_132).hex().upper(),
        )
        self.assertEqual(
            predecessor_132["superseded_by"],
            registry["releases"][0]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
