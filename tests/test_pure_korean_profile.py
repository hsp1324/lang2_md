from __future__ import annotations

import unittest

from scripts import build_korean_jp_probe as builder


class PureKoreanProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = builder.IN_ROM.read_bytes()

    def expanded_source(self) -> bytearray:
        data = bytearray(self.source)
        builder.expand_rom(data)
        return data

    def test_profile_split_is_explicit(self):
        self.assertFalse(builder.profile_includes_user_patches("pure"))
        self.assertTrue(builder.profile_includes_user_patches("normal"))
        self.assertTrue(builder.profile_includes_user_patches("hard"))
        with self.assertRaisesRegex(ValueError, "unknown ROM"):
            builder.profile_includes_user_patches("unexpected")

    def test_pure_profile_restores_original_join_roster_and_map_designs(self):
        data = self.expanded_source()
        builder.patch_profile_user_customizations(
            data,
            self.source,
            profile_name="pure",
        )
        self.assertEqual(
            data[
                builder.INITIAL_COMMANDER_ROSTER_TABLE:
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + 10 * builder.INITIAL_COMMANDER_RECORD_SIZE
            ],
            self.source[
                builder.INITIAL_COMMANDER_ROSTER_TABLE:
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + 10 * builder.INITIAL_COMMANDER_RECORD_SIZE
            ],
        )
        self.assertEqual(
            data[
                builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER:
                builder.JOIN_CLASS_CHOICE_COMBAT_RELOCATIONS[9]
                + builder.JOIN_CLASS_CHOICE_COMBAT_RELOCATED_SIZE
            ],
            b"\xFF" * (
                builder.JOIN_CLASS_CHOICE_COMBAT_RELOCATIONS[9]
                + builder.JOIN_CLASS_CHOICE_COMBAT_RELOCATED_SIZE
                - builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER
            ),
        )
        start = builder.SCENARIO6_RUNESTONE_TRIGGER
        end = start + len(builder.SCENARIO6_RUNESTONE_TRIGGER_SOURCE)
        self.assertEqual(
            data[start:end], builder.SCENARIO6_RUNESTONE_TRIGGER_SOURCE
        )
        self.assertEqual(
            data[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET],
            builder.SCENARIO31_DEMON_LORD_SOURCE_NAME_ID,
        )
        self.assertEqual(
            builder.be16(
                data,
                builder.GENERIC_CLASS_SPRITE_TABLE
                + builder.LOREN_CLASS_ID * 2,
            ),
            builder.LOREN_SOURCE_SPRITE_ID,
        )

    def test_pure_profile_keeps_original_scenario18_mechanics(self):
        data = self.expanded_source()
        expected = bytes(data)
        builder.patch_profile_scenario18_resident_loss(
            data,
            self.source,
            profile_name="pure",
        )
        self.assertEqual(bytes(data), expected)

    def test_custom_profile_still_changes_join_progression(self):
        data = self.expanded_source()
        builder.patch_profile_user_customizations(
            data,
            self.source,
            profile_name="normal",
        )
        self.assertNotEqual(
            data[
                builder.INITIAL_COMMANDER_ROSTER_TABLE:
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + 10 * builder.INITIAL_COMMANDER_RECORD_SIZE
            ],
            self.source[
                builder.INITIAL_COMMANDER_ROSTER_TABLE:
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + 10 * builder.INITIAL_COMMANDER_RECORD_SIZE
            ],
        )
        start = builder.SCENARIO6_RUNESTONE_TRIGGER
        end = start + len(builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE)
        self.assertEqual(
            data[start:end], builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
        )
        self.assertEqual(
            data[builder.SCENARIO31_DEMON_LORD_NAME_OFFSET],
            builder.SCENARIO31_DEMON_LORD_EVENT_NAME_ID,
        )

    def test_hard_profile_adds_training_items_to_every_shop_only(self):
        normal = self.expanded_source()
        builder.patch_profile_user_customizations(
            normal,
            self.source,
            profile_name="normal",
        )
        hard = self.expanded_source()
        builder.patch_profile_user_customizations(
            hard,
            self.source,
            profile_name="hard",
        )
        for index in range(builder.SHOP_LIST_COUNT):
            with self.subTest(index=index):
                source_items = builder.read_shop_item_list(self.source, index)
                self.assertEqual(
                    builder.read_shop_item_list(normal, index), source_items
                )
                hard_items = builder.read_shop_item_list(hard, index)
                self.assertEqual(
                    hard_items[:len(source_items)], source_items
                )
                for item_id in builder.HARD_SHOP_REQUIRED_ITEM_IDS:
                    self.assertIn(item_id, hard_items)
                    self.assertEqual(hard_items.count(item_id), 1)

        self.assertEqual(
            normal[
                builder.HARD_SHOP_LIST_RELOC_BASE:
                builder.HARD_SHOP_LIST_RELOC_LIMIT
            ],
            b"\xFF" * (
                builder.HARD_SHOP_LIST_RELOC_LIMIT
                - builder.HARD_SHOP_LIST_RELOC_BASE
            ),
        )


if __name__ == "__main__":
    unittest.main()
