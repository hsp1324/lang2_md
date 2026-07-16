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

    def test_scenario_twelve_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 12)
        self.assertEqual(model["record_count"], 11)

        lich = model["records"][0]
        living_armor = model["records"][1]
        hidden_egbert = model["records"][10]
        self.assertEqual(
            (lich["name"]["ko"], lich["class"]["ko"], lich["level"],
             lich["at"], lich["df"], lich["x"], lich["y"]),
            ("리치", "리치", 1, 32, 27, 15, 8),
        )
        self.assertEqual(lich["mercenaries"], [138, 138, 138, 138, 255, 255])
        self.assertEqual(
            (living_armor["name"]["ko"], living_armor["class"]["ko"],
             living_armor["level"], living_armor["at"], living_armor["df"],
             living_armor["x"], living_armor["y"]),
            ("리빙아머", "리빙아머", 1, 31, 30, 13, 10),
        )
        self.assertEqual(living_armor["mercenaries"], [130, 130, 130, 130, 130, 130])
        self.assertEqual(
            (hidden_egbert["name"]["ko"], hidden_egbert["class"]["ko"],
             hidden_egbert["level"], hidden_egbert["at"], hidden_egbert["df"],
             hidden_egbert["x"], hidden_egbert["y"], hidden_egbert["hidden"]),
            ("에그베르트", "자베라", 7, 43, 32, 255, 255, True),
        )
        self.assertEqual(hidden_egbert["mercenaries"], [255, 255, 255, 255, 255, 255])

    def test_scenario_thirteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 13)
        self.assertEqual(model["record_count"], 13)

        zorum = model["records"][8]
        hidden_vargas = model["records"][10]
        hidden_leon = model["records"][11]
        hidden_laird = model["records"][12]
        self.assertEqual(
            (zorum["name"]["ko"], zorum["class"]["ko"], zorum["level"],
             zorum["at"], zorum["df"], zorum["x"], zorum["y"]),
            ("조름", "하이로드", 9, 29, 31, 19, 27),
        )
        self.assertEqual(zorum["mercenaries"], [116, 116, 116, 116, 121, 121])
        self.assertEqual(
            (hidden_vargas["name"]["ko"], hidden_vargas["class"]["ko"],
             hidden_vargas["level"], hidden_vargas["at"], hidden_vargas["df"],
             hidden_vargas["x"], hidden_vargas["y"], hidden_vargas["hidden"]),
            ("발가스", "제너럴", 8, 48, 35, 255, 255, True),
        )
        self.assertEqual(hidden_vargas["mercenaries"], [115, 115, 115, 115, 122, 122])
        self.assertEqual(
            (hidden_leon["name"]["ko"], hidden_leon["class"]["ko"],
             hidden_leon["level"], hidden_leon["at"], hidden_leon["df"]),
            ("레온", "로얄가드", 2, 45, 34),
        )
        self.assertEqual(
            (hidden_laird["name"]["ko"], hidden_laird["class"]["ko"],
             hidden_laird["level"], hidden_laird["at"], hidden_laird["df"]),
            ("레아드", "실버나이트", 5, 39, 28),
        )

    def test_scenario_fourteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 14)
        self.assertEqual(model["record_count"], 11)

        dragon_knight = model["records"][0]
        laird = model["records"][9]
        hidden_leon = model["records"][10]
        self.assertEqual(
            (dragon_knight["name"]["ko"], dragon_knight["class"]["ko"],
             dragon_knight["level"], dragon_knight["at"], dragon_knight["df"],
             dragon_knight["x"], dragon_knight["y"]),
            ("제국지휘관", "드래곤나이트", 4, 31, 25, 6, 2),
        )
        self.assertEqual(dragon_knight["mercenaries"], [125, 125, 125, 125, 255, 255])
        self.assertEqual(
            (laird["name"]["ko"], laird["class"]["ko"], laird["level"],
             laird["at"], laird["df"], laird["x"], laird["y"]),
            ("레아드", "실버나이트", 5, 39, 28, 6, 28),
        )
        self.assertEqual(laird["mercenaries"], [118, 118, 118, 118, 116, 116])
        self.assertEqual(
            (hidden_leon["name"]["ko"], hidden_leon["class"]["ko"],
             hidden_leon["level"], hidden_leon["at"], hidden_leon["df"],
             hidden_leon["x"], hidden_leon["y"], hidden_leon["hidden"]),
            ("레온", "로얄가드", 2, 45, 34, 255, 255, True),
        )
        self.assertEqual(hidden_leon["mercenaries"], [123, 123, 123, 123, 115, 115])

    def test_scenario_fifteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 15)
        self.assertEqual(model["record_count"], 12)

        serpent_knight = model["records"][1]
        imelda = model["records"][3]
        hidden_lana = model["records"][9]
        self.assertEqual(
            (serpent_knight["name"]["ko"], serpent_knight["class"]["ko"],
             serpent_knight["level"], serpent_knight["at"], serpent_knight["df"],
             serpent_knight["x"], serpent_knight["y"]),
            ("제국지휘관", "서펜나이트", 1, 29, 23, 11, 13),
        )
        self.assertEqual(
            serpent_knight["mercenaries"], [120, 120, 120, 120, 255, 255]
        )
        self.assertEqual(
            (imelda["name"]["ko"], imelda["class"]["ko"], imelda["level"],
             imelda["at"], imelda["df"], imelda["x"], imelda["y"]),
            ("이멜다", "제너럴", 6, 46, 32, 23, 21),
        )
        self.assertEqual(imelda["mercenaries"], [115, 115, 122, 122, 119, 119])
        self.assertEqual(
            (hidden_lana["name"]["ko"], hidden_lana["class"]["ko"],
             hidden_lana["level"], hidden_lana["at"], hidden_lana["df"],
             hidden_lana["x"], hidden_lana["y"], hidden_lana["hidden"]),
            ("라나", "다크프린세스", 1, 36, 33, 255, 255, True),
        )
        self.assertEqual(hidden_lana["mercenaries"], [135, 135, 135, 135, 255, 255])

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
