from pathlib import Path
import unittest

from tools.scenario_data import KOREAN_NAME_BY_ID, NAME_COUNT, patch_scenario, read_scenario, scenario_layout


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ScenarioDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()

    def test_all_scenario_fixed_lists_are_valid(self):
        counts = [scenario_layout(self.rom, number).record_count for number in range(1, 32)]
        self.assertEqual(counts[0], 12)
        self.assertTrue(all(1 <= count <= 64 for count in counts))
        for number in range(1, 32):
            model = read_scenario(self.rom, self.rom, number)
            self.assertEqual(len(model["records"]), model["record_count"])

    def test_scenario_one_known_enemy_records(self):
        model = read_scenario(self.rom, self.rom, 1)
        leon = model["records"][9]
        laird = model["records"][10]
        self.assertEqual((leon["name"]["ko"], leon["class"]["ko"]), ("레온", "나이트마스터"))
        self.assertEqual((leon["at"], leon["df"], leon["mercenaries"][0]), (40, 31, 123))
        self.assertEqual((laird["name"]["ko"], laird["class"]["ko"]), ("레아드", "매직나이트"))

    def test_all_name_ids_have_explicit_labels(self):
        self.assertEqual(set(KOREAN_NAME_BY_ID), set(range(NAME_COUNT)))
        self.assertEqual(KOREAN_NAME_BY_ID[0x34], "웨어울프")
        self.assertEqual(KOREAN_NAME_BY_ID[0x68], "형님")
        self.assertEqual(KOREAN_NAME_BY_ID[0x73], "파이어스")

    def test_patch_is_limited_to_requested_fields_and_checksum(self):
        data = bytearray(self.rom)
        before = bytes(data)
        model = read_scenario(bytes(data), self.rom, 1)
        target = model["records"][9]["offset"] + 0x12
        model["records"][9]["at"] = 41
        checksum = patch_scenario(data, 1, model["records"])
        reread = read_scenario(bytes(data), self.rom, 1)
        changed = {index for index, (old, new) in enumerate(zip(before, data)) if old != new}
        self.assertEqual(reread["records"][9]["at"], 41)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), checksum)
        self.assertIn(target, changed)
        self.assertLessEqual(changed, {target, 0x18E, 0x18F})


if __name__ == "__main__":
    unittest.main()
