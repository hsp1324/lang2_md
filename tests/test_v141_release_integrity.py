import hashlib
import json
from pathlib import Path
import unittest

from patcher import langrisser_ii_korean_patcher as patcher
from scripts import build_korean_jp_probe as builder
from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.build_v141_release_patches import MANIFEST_PATH, SOURCE_PATH, TARGETS, build
from tools.rom_update import bps_apply, md_sram_descriptor
from tools.rom_version import get_profile


ROOT = Path(__file__).resolve().parents[1]


class V141ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")
        cls.source = SOURCE_PATH.read_bytes()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.targets = {
            row["id"]: bps_apply(
                (ROOT / "patches" / row["patch_filename"]).read_bytes(),
                cls.source,
            )
            for row in cls.manifest["targets"]
        }

    def test_manifest_bps_and_release_roms_are_reproducible(self):
        self.assertEqual(build(check=True), self.manifest)
        self.assertEqual(self.manifest["release"], "v1.4.1")
        specs = {str(spec["id"]): spec for spec in TARGETS}
        for row in self.manifest["targets"]:
            target = self.targets[row["id"]]
            with self.subTest(profile=row["id"]):
                self.assertEqual(len(target), 4_194_304)
                self.assertEqual(
                    hashlib.sha256(target).hexdigest(), row["output_sha256"]
                )
                self.assertEqual(
                    target, Path(specs[row["id"]]["rom_path"]).read_bytes()
                )
                self.assertEqual(
                    md_sram_descriptor(target),
                    bytes.fromhex("5241F8200040000100403FFF"),
                )
        verify_applied_hard_mode(self.targets["hard"])

    def test_profiles_and_patcher_name_the_same_release(self):
        expected = {
            "pure": ("ko-original-1.4.1", None, "ko-original-1.4.0"),
            "normal": ("ko-normal-1.4.1", None, "ko-normal-1.4.0"),
            "hard": ("ko-hard-1.4.1", "1.4.1", "ko-hard-1.4.0"),
        }
        for profile_name, values in expected.items():
            profile = get_profile(profile_name)
            with self.subTest(profile=profile_name):
                self.assertEqual(profile["release_id"], values[0])
                self.assertEqual(profile["translation_version"], "1.4.1")
                self.assertEqual(profile["balance_version"], values[1])
                self.assertEqual(profile["base_release"], values[2])
        self.assertEqual(patcher.PATCHER_RELEASE, "v1.4.1")
        self.assertEqual(patcher.MANIFEST_FILENAME, "v1.4.1.json")

    def test_original_uses_stock_tier_two_join_records(self):
        pure = self.targets["pure"]
        normal = self.targets["normal"]
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            offset = (
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + (commander_id - 1) * builder.INITIAL_COMMANDER_RECORD_SIZE
            )
            with self.subTest(commander_id=commander_id):
                self.assertEqual(
                    pure[offset:offset + len(row["source"])], row["source"]
                )
                self.assertEqual(
                    normal[offset:offset + len(row["target"])], row["target"]
                )

    def test_hard_every_shop_has_training_items_without_duplicates(self):
        hard = self.targets["hard"]
        normal = self.targets["normal"]
        for index in range(builder.SHOP_LIST_COUNT):
            with self.subTest(index=index):
                source_items = builder.read_shop_item_list(self.source, index)
                self.assertEqual(
                    builder.read_shop_item_list(normal, index), source_items
                )
                hard_items = builder.read_shop_item_list(hard, index)
                self.assertEqual(hard_items[:len(source_items)], source_items)
                for item_id in builder.HARD_SHOP_REQUIRED_ITEM_IDS:
                    self.assertEqual(hard_items.count(item_id), 1)

    def test_elf_hire_name_routes_peu_away_from_the_icon_cache(self):
        scratch = bytearray(self.source)
        builder.expand_rom(scratch)
        codes = builder.patch_byte_ui_strings(scratch)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(codes)
        peu_index = index_by_char["프"]
        self.assertEqual(tile_by_index[peu_index], 0x03F7)
        for profile_name, target in self.targets.items():
            with self.subTest(profile=profile_name):
                pointer = builder.be32(
                    target,
                    builder.CLASS_BYTE_POINTER_TABLE + 0x6A * 4,
                )
                self.assertEqual(
                    target[pointer:pointer + 5],
                    bytes((
                        builder.BYTE_UI_LOCAL_MARKER,
                        index_by_char["엘"],
                        builder.BYTE_UI_LOCAL_MARKER,
                        peu_index,
                        0xFF,
                    )),
                )
                slot = target[
                    builder.BYTE_UI_PREP_DYNAMIC_SLOT_TABLE + peu_index
                ]
                self.assertEqual(slot, 24)
                self.assertEqual(
                    builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS[slot],
                    0x07EB,
                )

    def test_v140_delta_is_only_version_checksum_and_hire_glyph_slots(self):
        previous_manifest = json.loads(
            (ROOT / "patches/v1.4.0.json").read_text(encoding="utf-8")
        )
        previous = {
            row["id"]: bps_apply(
                (ROOT / "patches" / row["patch_filename"]).read_bytes(),
                self.source,
            )
            for row in previous_manifest["targets"]
        }
        expected = {
            "pure": {
                0x00016F,
                0x00018E,
                0x00018F,
                0x2B7EEA,
                0x2BE9E1,
                0x2BEA08,
            },
            "normal": {
                0x00016A,
                0x00018E,
                0x00018F,
                0x2B7EEA,
                0x2BE9E1,
                0x2BEA08,
            },
            "hard": {
                0x00016A,
                0x000171,
                0x00018E,
                0x00018F,
                0x2B8A12,
                0x2B8A32,
                0x2BE9E1,
                0x2BEA08,
            },
        }
        for profile_name, target in self.targets.items():
            changed = {
                offset
                for offset, (before, after) in enumerate(
                    zip(previous[profile_name], target)
                )
                if before != after
            }
            with self.subTest(profile=profile_name):
                self.assertEqual(changed, expected[profile_name])
                self.assertEqual(target[0x2BE9E1], 24)
                self.assertEqual(target[0x2BEA08], 25)
