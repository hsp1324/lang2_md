from pathlib import Path
import unittest

from tools.class_ability_data import (
    MAGIC_COMMAND_MASK,
    SUMMON_COMMAND_MASK,
    ability_ids_for_classes,
    ability_ids_from_runtime_mask,
    all_class_ability_unlocks,
    learned_runtime_mask,
    natural_class_paths,
    read_ability_definitions,
    read_class_ability_unlocks,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ClassAbilityDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()

    def test_ability_requirements_and_masks_match_source_tables(self):
        definitions = read_ability_definitions(self.source)
        self.assertEqual(
            [definition.required_level for definition in definitions],
            [1, 6, 5, 3, 2, 3, 2, 2, 3, 2, 4, 3, 5, 2, 4, 6, 5, 7, 4, 2, 4, 3, 1],
        )
        self.assertEqual(
            [definition.runtime_mask for definition in definitions],
            [1 << bit for bit in range(1, 24)],
        )

    def test_player_class_ability_slots(self):
        self.assertEqual(
            read_class_ability_unlocks(self.source, 0x03).ability_ids,
            (0, 16),
        )
        self.assertEqual(
            read_class_ability_unlocks(self.source, 0x15).ability_ids,
            (1, 17, 20),
        )
        self.assertEqual(
            read_class_ability_unlocks(self.source, 0x28).ability_ids,
            (4, 15, 22),
        )
        self.assertEqual(
            read_class_ability_unlocks(self.source, 0x25).ability_ids,
            (4, 16, 18, 21),
        )
        self.assertEqual(len(all_class_ability_unlocks(self.source)), 157)

    def test_level_gate_and_runtime_decode(self):
        self.assertEqual(
            ability_ids_from_runtime_mask(
                learned_runtime_mask(self.source, 0x28, 1)
            ),
            (22,),
        )
        self.assertEqual(
            ability_ids_from_runtime_mask(
                learned_runtime_mask(self.source, 0x28, 2)
            ),
            (4, 22),
        )
        self.assertTrue(
            learned_runtime_mask(self.source, 0x28, 1)
            & MAGIC_COMMAND_MASK
        )
        self.assertTrue(
            learned_runtime_mask(self.source, 0x28, 1)
            & SUMMON_COMMAND_MASK
        )

    def test_all_natural_paths_exclude_only_teleport(self):
        all_classes = set()
        for commander_id in range(1, 11):
            paths = natural_class_paths(self.source, commander_id)
            self.assertEqual(len(paths), 27)
            all_classes.update(value for path in paths for value in path)
        self.assertNotIn(0x25, all_classes)
        self.assertEqual(
            set(range(23))
            - set(ability_ids_for_classes(self.source, all_classes)),
            {18},
        )

    def test_hein_and_jessica_maximal_source_paths(self):
        hein_path = (0x03, 0x0A, 0x11, 0x15, 0x28)
        jessica_path = (0x03, 0x08, 0x13, 0x14, 0x26)
        self.assertIn(hein_path, natural_class_paths(self.source, 5))
        self.assertIn(jessica_path, natural_class_paths(self.source, 10))
        self.assertEqual(
            ability_ids_for_classes(self.source, hein_path),
            (0, 1, 2, 4, 7, 10, 14, 15, 16, 17, 19, 20, 22),
        )
        self.assertEqual(
            ability_ids_for_classes(self.source, jessica_path),
            (0, 1, 4, 5, 6, 7, 8, 9, 11, 13, 15, 16, 17, 20),
        )


if __name__ == "__main__":
    unittest.main()
