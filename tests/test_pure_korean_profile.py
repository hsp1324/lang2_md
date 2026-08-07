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

    def test_pure_profile_keeps_all_pre_translation_game_data(self):
        data = self.expanded_source()
        expected = bytes(data)
        builder.patch_profile_user_customizations(
            data,
            self.source,
            profile_name="pure",
        )
        self.assertEqual(bytes(data), expected)

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


if __name__ == "__main__":
    unittest.main()
