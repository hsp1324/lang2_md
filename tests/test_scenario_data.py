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

    def test_scenario_eleven_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 11)
        self.assertEqual(model["record_count"], 11)

        jessica = model["records"][0]
        egbert = model["records"][1]
        hidden_hawk = model["records"][10]
        self.assertEqual(
            (jessica["name"]["ko"], jessica["class"]["ko"], jessica["level"],
             jessica["at"], jessica["df"], jessica["x"], jessica["y"]),
            ("제시카", "소서러", 7, 30, 17, 18, 6),
        )
        self.assertEqual(jessica["mercenaries"], [100, 100, 100, 100, 255, 255])
        self.assertEqual(
            (egbert["name"]["ko"], egbert["class"]["ko"], egbert["level"],
             egbert["at"], egbert["df"], egbert["x"], egbert["y"]),
            ("에그베르트", "자베라", 7, 43, 32, 2, 13),
        )
        self.assertEqual(egbert["mercenaries"], [115, 115, 115, 115, 255, 255])
        self.assertEqual(
            (hidden_hawk["name"]["ko"], hidden_hawk["class"]["ko"],
             hidden_hawk["level"], hidden_hawk["at"], hidden_hawk["df"],
             hidden_hawk["x"], hidden_hawk["y"], hidden_hawk["hidden"]),
            ("제국지휘관", "호크나이트", 6, 27, 22, 255, 255, True),
        )
        self.assertEqual(hidden_hawk["mercenaries"], [125, 125, 125, 125, 255, 255])

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
