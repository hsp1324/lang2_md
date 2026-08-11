import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.class_change_data import read_class_change_chain
from tools.class_hire_data import CLASS_RECORD_SIZE, CLASS_RECORD_TABLE
from tools.rom_update import bps_apply, md_sram_descriptor


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
MANIFEST = ROOT / "patches/v1.3.6.json"
PREVIOUS_MANIFEST = ROOT / "patches/v1.3.5.json"


class V136ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_ROM.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_ROM.read_bytes()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.targets = {}
        for row in cls.manifest["targets"]:
            patch = (ROOT / "patches" / row["patch_filename"]).read_bytes()
            cls.targets[row["id"]] = bps_apply(patch, cls.source)
        previous_manifest = json.loads(
            PREVIOUS_MANIFEST.read_text(encoding="utf-8")
        )
        cls.previous_targets = {}
        for row in previous_manifest["targets"]:
            patch = (ROOT / "patches" / row["patch_filename"]).read_bytes()
            cls.previous_targets[row["id"]] = bps_apply(patch, cls.source)

    def test_manifest_hashes_and_save_layout_match_all_three_outputs(self):
        self.assertEqual(self.manifest["release"], "v1.3.6")
        release_descriptor = bytes.fromhex("5241F8200040000100403FFF")
        for row in self.manifest["targets"]:
            payload = self.targets[row["id"]]
            with self.subTest(profile=row["id"]):
                self.assertEqual(len(payload), row["output_size"])
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(),
                    row["output_sha256"],
                )
                self.assertEqual(md_sram_descriptor(payload), release_descriptor)

    def test_runestone_first_choices_match_join_choices_at_every_tier(self):
        expected = {
            7: (0x04, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x08),
            9: (0x05, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x0A),
            10: (0x08, 0x09, 0x04),
        }
        for profile, payload in self.targets.items():
            for commander_id, candidates in expected.items():
                chain = read_class_change_chain(payload, commander_id)
                with self.subTest(profile=profile, commander_id=commander_id):
                    self.assertEqual(chain[0].candidates, candidates)
                    if commander_id in (7, 9):
                        self.assertIn(
                            candidates[1],
                            {row.current_class for row in chain},
                        )

    def test_custom_lords_have_mounted_class_and_combat_data(self):
        for profile, payload in self.targets.items():
            for custom_class, source_class in (
                builder.JOIN_CLASS_CHOICE_CUSTOM_CLASS_SOURCES.items()
            ):
                with self.subTest(profile=profile, custom_class=custom_class):
                    custom = CLASS_RECORD_TABLE + custom_class * CLASS_RECORD_SIZE
                    source = CLASS_RECORD_TABLE + source_class * CLASS_RECORD_SIZE
                    self.assertEqual(
                        payload[custom:custom + CLASS_RECORD_SIZE],
                        self.source[source:source + CLASS_RECORD_SIZE],
                    )
                    custom_combat = (
                        builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                        + custom_class * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                    )
                    source_combat = (
                        builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                        + source_class * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                    )
                    self.assertEqual(
                        payload[
                            custom_combat:
                            custom_combat + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                        ],
                        self.source[
                            source_combat:
                            source_combat + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                        ],
                    )

    def test_commander_combat_overrides_include_custom_mounted_aliases(self):
        for profile, payload in self.targets.items():
            for commander_id, custom_class, source_class in (
                (7, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x06),
                (9, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x07),
            ):
                pointer_offset = (
                    builder.COMMANDER_COMBAT_POINTER_TABLE
                    + (commander_id - 1) * 4
                )
                pointer = builder.be32(payload, pointer_offset)
                records = {}
                while builder.be16(payload, pointer) != 0xFFFF:
                    class_id = builder.be16(payload, pointer)
                    records[class_id] = bytes(
                        payload[
                            pointer:
                            pointer + builder.COMMANDER_COMBAT_RECORD_SIZE
                        ]
                    )
                    pointer += builder.COMMANDER_COMBAT_RECORD_SIZE
                with self.subTest(profile=profile, commander_id=commander_id):
                    self.assertEqual(
                        records[custom_class][2:],
                        records[source_class][2:],
                    )

    def test_hard_balance_and_shared_scenario31_fix_are_present(self):
        verify_applied_hard_mode(self.targets["hard"])
        for profile, payload in self.targets.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    payload[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET],
                    builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID,
                )

    def test_v135_delta_is_confined_to_version_and_mounted_lord_repairs(self):
        allowed = {0x18E, 0x18F}
        allowed.update(range(0x150, 0x180))
        allowed.update(
            range(
                builder.COMMANDER_SPRITE_POINTER_TABLE,
                builder.GENERIC_CLASS_SPRITE_TABLE,
            )
        )
        allowed.update(
            range(
                builder.GENERIC_CLASS_SPRITE_TABLE,
                builder.GENERIC_CLASS_SPRITE_TABLE + 157 * 2,
            )
        )
        for custom_class in builder.JOIN_CLASS_CHOICE_CUSTOM_CLASS_SOURCES:
            class_record = CLASS_RECORD_TABLE + custom_class * CLASS_RECORD_SIZE
            allowed.update(range(class_record, class_record + CLASS_RECORD_SIZE))
            combat = (
                builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                + custom_class * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
            )
            allowed.update(
                range(combat, combat + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE)
            )
        allowed.update(
            range(
                builder.COMMANDER_COMBAT_POINTER_TABLE,
                builder.COMMANDER_COMBAT_POINTER_TABLE + 10 * 4,
            )
        )
        allowed.update(
            range(
                builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER,
                builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD,
            )
        )
        allowed.update(range(0x31E400, 0x31E900))
        allowed.update(range(0x2B7EE0, 0x2B7F20))
        allowed.update(range(0x2B8A00, 0x2B8A50))

        expected_counts = {"pure": 723, "normal": 725, "hard": 727}
        for profile, payload in self.targets.items():
            previous = self.previous_targets[profile]
            changed = {
                index
                for index, (before, after) in enumerate(zip(previous, payload))
                if before != after
            }
            with self.subTest(profile=profile):
                self.assertEqual(len(changed), expected_counts[profile])
                self.assertEqual(changed - allowed, set())


if __name__ == "__main__":
    unittest.main()
