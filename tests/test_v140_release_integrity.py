import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.build_hard_mode_rom import verify_applied_hard_mode
from tools.build_v140_release_patches import MANIFEST_PATH, SOURCE_PATH, TARGETS, build
from tools.rom_update import bps_apply, md_sram_descriptor


ROOT = Path(__file__).resolve().parents[1]


class V140ReleaseIntegrityTests(unittest.TestCase):
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
        self.assertEqual(self.manifest["release"], "v1.4.0")
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

    def test_historical_manifest_keeps_the_v140_filename_contract(self):
        self.assertEqual(
            {row["id"]: row["output_filename"] for row in self.manifest["targets"]},
            {
                "pure": "Langrisser II (Korean Original v1.4.0).md",
                "normal": "Langrisser II (Korean Normal v1.4.0).md",
                "hard": "Langrisser II (Korean Hard v1.4.0).md",
            },
        )

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
