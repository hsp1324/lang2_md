from pathlib import Path
import unittest

from tools.class_change_data import (
    CLASS_CHANGE_POINTER_TABLE,
    ClassTransition,
    class_change_chain_pointer,
    patch_class_change_chain,
    patch_class_change_chains,
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

    def test_patch_chain_round_trip_changes_only_selected_words(self):
        original = list(read_class_change_chain(self.source, 1))
        original[0] = ClassTransition(0x01, (0x05, 0x04, 0x0A))
        patched = bytearray(self.source)
        patch_class_change_chain(patched, 1, tuple(original))

        self.assertEqual(read_class_change_chain(patched, 1), tuple(original))
        pointer = class_change_chain_pointer(self.source, 1)
        changed = {
            index for index, (before, after) in enumerate(zip(self.source, patched))
            if before != after
        }
        self.assertEqual(changed, {pointer + 3, pointer + 5})

    def test_patch_all_chains_from_editor_shape(self):
        commanders = []
        for commander_id in range(1, 11):
            commanders.append({
                "commander_id": commander_id,
                "transitions": [
                    {
                        "current_class": transition.current_class,
                        "candidates": list(transition.candidates),
                    }
                    for transition in read_class_change_chain(
                        self.source, commander_id
                    )
                ],
            })
        patched = bytearray(self.source)
        patch_class_change_chains(patched, commanders)
        self.assertEqual(patched, self.source)

    def test_patch_chain_rejects_duplicate_current_class(self):
        transitions = list(read_class_change_chain(self.source, 1))
        transitions[1] = ClassTransition(
            transitions[0].current_class,
            transitions[1].candidates,
        )
        with self.assertRaisesRegex(ValueError, "repeats"):
            patch_class_change_chain(bytearray(self.source), 1, transitions)


if __name__ == "__main__":
    unittest.main()
