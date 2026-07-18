from pathlib import Path
import unittest

from tools.class_change_data import (
    CLASS_CHANGE_POINTER_TABLE,
    ClassTransition,
    class_change_chain_pointer,
    read_class_change_chain,
    transition_for_class,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ClassChangeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()

    def test_ten_source_pointers_and_chain_shapes(self):
        pointers = [
            class_change_chain_pointer(self.source, commander_id)
            for commander_id in range(1, 11)
        ]
        self.assertEqual(pointers[0], 0x082562)
        self.assertEqual(pointers[-1], 0x0828C2)
        self.assertEqual(len(set(pointers)), 10)
        self.assertEqual(CLASS_CHANGE_POINTER_TABLE, 0x08253A)

        for commander_id in range(1, 11):
            chain = read_class_change_chain(self.source, commander_id)
            self.assertEqual(len(chain), 10)
            self.assertTrue(all(len(row.candidates) == 3 for row in chain[:9]))
            self.assertEqual(len(chain[-1].candidates), 1)

    def test_fighter_elwin_source_branch(self):
        self.assertEqual(
            read_class_change_chain(self.source, 1)[0],
            ClassTransition(0x01, (0x04, 0x05, 0x0A)),
        )
        self.assertEqual(
            transition_for_class(self.source, 1, 0x1A),
            ClassTransition(0x1A, (0x22,)),
        )

    def test_representative_other_commander_branches(self):
        self.assertEqual(
            read_class_change_chain(self.source, 4)[0],
            ClassTransition(0x01, (0x04, 0x06, 0x0A)),
        )
        self.assertEqual(
            transition_for_class(self.source, 9, 0x10),
            ClassTransition(0x10, (0x1D, 0x1F, 0x19)),
        )
        self.assertEqual(
            read_class_change_chain(self.source, 10)[-1],
            ClassTransition(0x14, (0x26,)),
        )

    def test_rejects_invalid_commander_and_missing_class(self):
        with self.assertRaisesRegex(ValueError, "commander ID"):
            read_class_change_chain(self.source, 0)
        with self.assertRaisesRegex(ValueError, "no class-change transition"):
            transition_for_class(self.source, 1, 0x7F)

    def test_rejects_missing_terminal_sentinel(self):
        source = bytearray(self.source)
        pointer = class_change_chain_pointer(source, 1)
        source[pointer + 0x4C : pointer + 0x4E] = b"\x00\x00"
        with self.assertRaisesRegex(ValueError, "no terminal sentinel"):
            read_class_change_chain(source, 1)


if __name__ == "__main__":
    unittest.main()
