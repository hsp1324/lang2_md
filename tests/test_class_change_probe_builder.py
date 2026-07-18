from pathlib import Path
import unittest

from tools import build_class_change_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ClassChangeProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_probe_changes_only_entry_operand_wrapper_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        operand = probe_builder.END_TURN_LEVEL_UP_ENTRY_OPERAND
        wrapper = probe_builder.PROBE_WRAPPER
        code = probe_builder.wrapper_code()
        start_operand = probe_builder.START_MENU_ENTRY_OPERAND
        start_wrapper = probe_builder.START_MENU_PROBE_WRAPPER
        start_code = probe_builder.start_menu_wrapper_code()

        self.assertEqual(
            probe[operand : operand + 4], wrapper.to_bytes(4, "big")
        )
        self.assertEqual(probe[wrapper : wrapper + len(code)], code)
        self.assertEqual(
            probe[start_operand : start_operand + 4],
            start_wrapper.to_bytes(4, "big"),
        )
        self.assertEqual(
            probe[start_wrapper : start_wrapper + len(start_code)], start_code
        )
        self.assertEqual(probe[0x18E:0x190], checksum.to_bytes(2, "big"))

        allowed = set(range(0x18E, 0x190))
        allowed.update(range(operand, operand + 4))
        allowed.update(range(wrapper, wrapper + len(code)))
        allowed.update(range(start_operand, start_operand + 4))
        allowed.update(range(start_wrapper, start_wrapper + len(start_code)))
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)

    def test_wrapper_guards_fighter_and_jumps_to_stock_handler(self):
        code = probe_builder.wrapper_code()
        self.assertEqual(code[:8], bytes.fromhex("0C 39 00 01 FF FF 60 3C"))
        self.assertEqual(code[8:12], bytes.fromhex("66 00 00 12"))
        self.assertIn(bytes.fromhex("13 FC 00 09 FF FF 60 6A"), code)
        self.assertIn(bytes.fromhex("13 FC 00 10 FF FF 60 6B"), code)
        self.assertEqual(code[-6:], bytes.fromhex("4E F9 00 01 48 0C"))

    def test_probe_rejects_unexpected_input_operand(self):
        probe = bytearray(self.production)
        probe[probe_builder.END_TURN_LEVEL_UP_ENTRY_OPERAND] ^= 0xFF
        with self.assertRaisesRegex(
            ValueError, "input end-turn level-up operand changed"
        ):
            probe_builder.patch_probe(probe, self.source)

    def test_start_wrapper_uses_source_elwin_candidate_ids(self):
        code = probe_builder.start_menu_wrapper_code()
        self.assertIn(bytes.fromhex("30 FC 00 01"), code)
        for class_id in (4, 5, 10):
            self.assertIn(bytes.fromhex(f"30 FC {class_id:04X}"), code)
        self.assertEqual(code[-6:], bytes.fromhex("4E F9 00 02 BB 48"))


if __name__ == "__main__":
    unittest.main()
