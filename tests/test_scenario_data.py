from pathlib import Path
import unittest

from tools.scenario_data import (
    KOREAN_NAME_BY_ID,
    NAME_COUNT,
    SCENARIO_COUNT,
    patch_scenario,
    read_scenario,
    scenario_layout,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ScenarioDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

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

    def test_scenario_two_through_ten_editor_records_match_original_rom(self):
        expected = {
            2: (10, [
                (0, "로렌", "하이로드", 7, 28, 28, 19, 19, False,
                 [100, 100, 106, 106, 255, 255]),
                (3, "리아나", "클레릭", 1, 20, 17, 8, 18, False,
                 [255, 255, 255, 255, 255, 255]),
                (8, "제국지휘관", "파이터", 3, 20, 18, 255, 255, True,
                 [114, 114, 114, 114, 117, 117]),
            ]),
            3: (10, [
                (0, "리아나", "클레릭", 1, 20, 17, 17, 18, False,
                 [109, 109, 109, 109, 255, 255]),
                (1, "수수께끼의 기사", "파이터", 9, 22, 20, 255, 255, True,
                 [99, 99, 99, 99, 99, 99]),
                (9, "발가스", "제너럴", 1, 40, 30, 255, 255, True,
                 [121, 121, 121, 121, 121, 121]),
            ]),
            4: (11, [
                (3, "사제", "프리스트", 2, 26, 25, 7, 5, False,
                 [109, 109, 109, 109, 255, 255]),
                (7, "모건", "소서러", 1, 26, 16, 7, 21, False,
                 [118, 118, 121, 121, 114, 114]),
                (8, "제국지휘관", "샤먼", 1, 25, 18, 7, 25, False,
                 [118, 118, 117, 117, 117, 117]),
            ]),
            5: (9, [
                (0, "웨어울프", "웨어울프", 1, 21, 19, 12, 42, False,
                 [131, 131, 131, 131, 131, 131]),
                (2, "모건", "소서러", 10, 30, 19, 9, 31, False,
                 [118, 118, 118, 118, 121, 121]),
                (7, "웨어울프", "웨어울프", 5, 22, 21, 255, 255, True,
                 [131, 131, 131, 131, 255, 255]),
            ]),
            6: (13, [
                (0, "아론", "파이터", 8, 23, 20, 14, 10, False,
                 [101, 101, 101, 100, 100, 100]),
                (1, "주민", "클레릭", 3, 21, 17, 5, 5, False,
                 [113, 113, 113, 113, 255, 255]),
                (12, "제국지휘관", "호크나이트", 1, 23, 21, 255, 255, True,
                 [125, 125, 125, 125, 125, 125]),
            ]),
            7: (12, [
                (3, "키스", "호크나이트", 2, 23, 20, 255, 255, True,
                 [111, 111, 111, 111, 111, 111]),
                (4, "기남", "네크로맨서", 7, 34, 19, 6, 6, False,
                 [129, 129, 129, 129, 129, 129]),
                (11, "제국지휘관", "어새신", 1, 32, 22, 255, 255, True,
                 [114, 114, 114, 114, 114, 114]),
            ]),
            8: (11, [
                (5, "크레이머", "하이로드", 1, 25, 26, 38, 8, False,
                 [126, 126, 126, 126, 114, 114]),
                (9, "발가스", "제너럴", 1, 40, 30, 255, 255, True,
                 [126, 126, 126, 126, 255, 255]),
                (10, "조름", "로드", 5, 24, 23, 255, 255, True,
                 [114, 114, 114, 114, 255, 255]),
            ]),
            9: (13, [
                (3, "레아드", "실버나이트", 1, 36, 26, 14, 15, False,
                 [122, 122, 122, 122, 255, 255]),
                (4, "레온", "로얄가드", 1, 46, 35, 16, 15, False,
                 [123, 123, 123, 123, 255, 255]),
                (9, "제국지휘관", "매직나이트", 6, 33, 25, 8, 14, False,
                 [114, 114, 114, 114, 121, 121]),
            ]),
            10: (13, [
                (1, "레스터", "크로코나이트", 6, 25, 21, 16, 13, False,
                 [110, 110, 110, 110, 110, 110]),
                (3, "스큐라", "스큐라", 6, 34, 20, 255, 255, True,
                 [120, 120, 120, 120, 120, 120]),
                (8, "그레이트슬라임", "그레이트슬라임", 8, 20, 24,
                 255, 255, True, [140, 140, 140, 140, 140, 140]),
            ]),
        }
        for number, (record_count, samples) in expected.items():
            model = read_scenario(self.rom, self.rom, number)
            self.assertEqual(model["record_count"], record_count)
            for (index, name, class_name, level, at, df, x, y, hidden,
                 mercenaries) in samples:
                record = model["records"][index]
                with self.subTest(scenario=number, record=index):
                    self.assertEqual(
                        (record["name"]["ko"], record["class"]["ko"],
                         record["level"], record["at"], record["df"],
                         record["x"], record["y"], record["hidden"]),
                        (name, class_name, level, at, df, x, y, hidden),
                    )
                    self.assertEqual(record["mercenaries"], mercenaries)

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

    def test_scenario_sixteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 16)
        self.assertEqual(model["record_count"], 10)

        leon = model["records"][0]
        dragon_lord = model["records"][1]
        hidden_lana = model["records"][8]
        self.assertEqual(
            (leon["name"]["ko"], leon["class"]["ko"], leon["level"],
             leon["at"], leon["df"], leon["x"], leon["y"]),
            ("레온", "로얄가드", 4, 46, 35, 13, 10),
        )
        self.assertEqual(leon["mercenaries"], [123, 123, 123, 123, 119, 119])
        self.assertEqual(
            (dragon_lord["name"]["ko"], dragon_lord["class"]["ko"],
             dragon_lord["level"], dragon_lord["at"], dragon_lord["df"],
             dragon_lord["x"], dragon_lord["y"]),
            ("제국지휘관", "드래곤로드", 1, 35, 28, 20, 12),
        )
        self.assertEqual(dragon_lord["mercenaries"], [125, 125, 125, 125, 125, 125])
        self.assertEqual(
            (hidden_lana["name"]["ko"], hidden_lana["class"]["ko"],
             hidden_lana["level"], hidden_lana["at"], hidden_lana["df"],
             hidden_lana["x"], hidden_lana["y"], hidden_lana["hidden"]),
            ("라나", "다크프린세스", 1, 36, 33, 255, 255, True),
        )
        self.assertEqual(hidden_lana["mercenaries"], [136, 136, 136, 136, 118, 118])

    def test_scenario_seventeen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 17)
        self.assertEqual(model["record_count"], 11)

        bernhardt = model["records"][0]
        bozel = model["records"][1]
        hidden_magic_knight = model["records"][9]
        self.assertEqual(
            (bernhardt["name"]["ko"], bernhardt["class"]["ko"],
             bernhardt["level"], bernhardt["at"], bernhardt["df"],
             bernhardt["x"], bernhardt["y"]),
            ("베른하르트", "엠퍼러", 1, 52, 37, 15, 4),
        )
        self.assertEqual(bernhardt["mercenaries"], [119, 119, 119, 119, 123, 123])
        self.assertEqual(
            (bozel["name"]["ko"], bozel["class"]["ko"], bozel["level"],
             bozel["at"], bozel["df"], bozel["x"], bozel["y"]),
            ("보젤", "다크마스터", 1, 38, 29, 18, 6),
        )
        self.assertEqual(bozel["mercenaries"], [124, 124, 124, 124, 124, 124])
        self.assertEqual(
            (hidden_magic_knight["name"]["ko"], hidden_magic_knight["class"]["ko"],
             hidden_magic_knight["level"], hidden_magic_knight["at"],
             hidden_magic_knight["df"], hidden_magic_knight["x"],
             hidden_magic_knight["y"], hidden_magic_knight["hidden"]),
            ("제국지휘관", "매직나이트", 10, 36, 27, 255, 255, True),
        )
        self.assertEqual(
            hidden_magic_knight["mercenaries"], [122, 122, 122, 122, 122, 122]
        )

    def test_scenario_eighteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 18)
        self.assertEqual(model["record_count"], 11)

        resident = model["records"][0]
        great_dragon = model["records"][5]
        lana = model["records"][6]
        self.assertEqual(
            (resident["name"]["ko"], resident["class"]["ko"], resident["level"],
             resident["at"], resident["df"], resident["x"], resident["y"]),
            ("주민", "클레릭", 2, 20, 17, 15, 20),
        )
        self.assertEqual(resident["mercenaries"], [113, 113, 113, 113, 255, 255])
        self.assertEqual(
            (great_dragon["name"]["ko"], great_dragon["class"]["ko"],
             great_dragon["level"], great_dragon["at"], great_dragon["df"],
             great_dragon["x"], great_dragon["y"]),
            ("그레이트드래곤", "그레이트드래곤", 1, 39, 34, 35, 4),
        )
        self.assertEqual(great_dragon["mercenaries"], [130, 130, 130, 130, 255, 255])
        self.assertEqual(
            (lana["name"]["ko"], lana["class"]["ko"], lana["level"],
             lana["at"], lana["df"], lana["x"], lana["y"]),
            ("라나", "다크프린세스", 3, 37, 34, 37, 2),
        )
        self.assertEqual(lana["mercenaries"], [136, 136, 136, 136, 136, 136])

    def test_scenario_nineteen_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 19)
        self.assertEqual(model["record_count"], 10)

        saint = model["records"][0]
        imelda = model["records"][2]
        hidden_laird = model["records"][7]
        self.assertEqual(
            (saint["name"]["ko"], saint["class"]["ko"], saint["level"],
             saint["at"], saint["df"], saint["x"], saint["y"]),
            ("제국지휘관", "세인트", 5, 34, 30, 26, 17),
        )
        self.assertEqual(saint["mercenaries"], [115, 115, 115, 115, 115, 115])
        self.assertEqual(
            (imelda["name"]["ko"], imelda["class"]["ko"], imelda["level"],
             imelda["at"], imelda["df"], imelda["x"], imelda["y"]),
            ("이멜다", "제너럴", 10, 48, 33, 37, 23),
        )
        self.assertEqual(imelda["mercenaries"], [119, 119, 119, 119, 127, 127])
        self.assertEqual(
            (hidden_laird["name"]["ko"], hidden_laird["class"]["ko"],
             hidden_laird["level"], hidden_laird["at"], hidden_laird["df"],
             hidden_laird["x"], hidden_laird["y"], hidden_laird["hidden"]),
            ("레아드", "실버나이트", 9, 42, 29, 255, 255, True),
        )
        self.assertEqual(hidden_laird["mercenaries"], [122, 122, 122, 122, 116, 116])

    def test_scenario_twenty_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 20)
        self.assertEqual(model["record_count"], 10)

        scylla = model["records"][0]
        faias = model["records"][5]
        hidden_kraken = model["records"][8]
        self.assertEqual(
            (scylla["name"]["ko"], scylla["class"]["ko"], scylla["level"],
             scylla["at"], scylla["df"], scylla["x"], scylla["y"]),
            ("스큐라", "스큐라", 10, 36, 22, 18, 8),
        )
        self.assertEqual(scylla["mercenaries"], [133, 133, 133, 133, 133, 133])
        self.assertEqual(
            (faias["name"]["ko"], faias["class"]["ko"], faias["level"],
             faias["at"], faias["df"], faias["x"], faias["y"]),
            ("파이어스", "데몬로드", 1, 46, 32, 22, 23),
        )
        self.assertEqual(faias["mercenaries"], [134, 134, 137, 137, 137, 137])
        self.assertEqual(
            (hidden_kraken["name"]["ko"], hidden_kraken["class"]["ko"],
             hidden_kraken["level"], hidden_kraken["at"], hidden_kraken["df"],
             hidden_kraken["x"], hidden_kraken["y"], hidden_kraken["hidden"]),
            ("크라켄", "크라켄", 4, 39, 32, 255, 255, True),
        )
        self.assertEqual(hidden_kraken["mercenaries"], [133, 133, 133, 133, 133, 133])

    def test_scenario_twenty_one_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 21)
        self.assertEqual(model["record_count"], 11)

        lich = model["records"][2]
        lana = model["records"][3]
        hidden_kraken = model["records"][8]
        self.assertEqual(
            (lich["name"]["ko"], lich["class"]["ko"], lich["level"],
             lich["at"], lich["df"], lich["x"], lich["y"]),
            ("리치", "리치", 5, 35, 29, 31, 7),
        )
        self.assertEqual(lich["mercenaries"], [119, 119, 119, 119, 138, 138])
        self.assertEqual(
            (lana["name"]["ko"], lana["class"]["ko"], lana["level"],
             lana["at"], lana["df"], lana["x"], lana["y"]),
            ("라나", "다크프린세스", 6, 39, 36, 37, 11),
        )
        self.assertEqual(lana["mercenaries"], [136, 136, 136, 136, 136, 136])
        self.assertEqual(
            (hidden_kraken["name"]["ko"], hidden_kraken["class"]["ko"],
             hidden_kraken["level"], hidden_kraken["at"], hidden_kraken["df"],
             hidden_kraken["x"], hidden_kraken["y"], hidden_kraken["hidden"]),
            ("크라켄", "크라켄", 8, 41, 35, 255, 255, True),
        )
        self.assertEqual(hidden_kraken["mercenaries"], [133, 133, 133, 133, 133, 133])

    def test_scenario_twenty_two_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 22)
        self.assertEqual(model["record_count"], 12)

        liana = model["records"][0]
        bozel = model["records"][2]
        hidden_bernhardt = model["records"][3]
        self.assertEqual(
            (liana["name"]["ko"], liana["class"]["ko"], liana["level"],
             liana["at"], liana["df"], liana["x"], liana["y"]),
            ("리아나", "클레릭", 2, 20, 17, 14, 4),
        )
        self.assertEqual(liana["mercenaries"], [255, 255, 255, 255, 255, 255])
        self.assertEqual(
            (bozel["name"]["ko"], bozel["class"]["ko"], bozel["level"],
             bozel["at"], bozel["df"], bozel["x"], bozel["y"]),
            ("보젤", "다크마스터", 6, 42, 32, 15, 5),
        )
        self.assertEqual(bozel["mercenaries"], [255, 255, 255, 255, 255, 255])
        self.assertEqual(
            (hidden_bernhardt["name"]["ko"], hidden_bernhardt["class"]["ko"],
             hidden_bernhardt["level"], hidden_bernhardt["at"],
             hidden_bernhardt["df"], hidden_bernhardt["x"],
             hidden_bernhardt["y"], hidden_bernhardt["hidden"]),
            ("베른하르트", "엠퍼러", 10, 58, 41, 255, 255, True),
        )
        self.assertEqual(hidden_bernhardt["mercenaries"], [124, 124, 124, 124, 124, 124])

    def test_scenario_twenty_three_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 23)
        self.assertEqual(model["record_count"], 11)

        dragon_lord = model["records"][0]
        laird = model["records"][4]
        wizard = model["records"][10]
        self.assertEqual(
            (dragon_lord["name"]["ko"], dragon_lord["class"]["ko"],
             dragon_lord["level"], dragon_lord["at"], dragon_lord["df"],
             dragon_lord["x"], dragon_lord["y"]),
            ("제국지휘관", "드래곤로드", 10, 45, 31, 23, 13),
        )
        self.assertEqual(dragon_lord["mercenaries"], [136, 136, 136, 255, 255, 255])
        self.assertEqual(
            (laird["name"]["ko"], laird["class"]["ko"], laird["level"],
             laird["at"], laird["df"], laird["x"], laird["y"]),
            ("레아드", "실버나이트", 10, 43, 30, 23, 7),
        )
        self.assertEqual(laird["mercenaries"], [123, 123, 123, 123, 255, 255])
        self.assertEqual(
            (wizard["name"]["ko"], wizard["class"]["ko"], wizard["level"],
             wizard["at"], wizard["df"], wizard["x"], wizard["y"]),
            ("제국지휘관", "위저드", 10, 35, 31, 30, 3),
        )
        self.assertEqual(wizard["mercenaries"], [127, 127, 119, 119, 119, 119])

    def test_scenario_twenty_four_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 24)
        self.assertEqual(model["record_count"], 11)

        bernhardt = model["records"][0]
        demon_lord = model["records"][1]
        vampire_lord = model["records"][10]
        self.assertEqual(
            (bernhardt["name"]["ko"], bernhardt["class"]["ko"],
             bernhardt["level"], bernhardt["at"], bernhardt["df"],
             bernhardt["x"], bernhardt["y"]),
            ("베른하르트", "엠퍼러", 10, 58, 41, 16, 19),
        )
        self.assertEqual(bernhardt["mercenaries"], [255, 255, 255, 255, 255, 255])
        self.assertEqual(
            (demon_lord["name"]["ko"], demon_lord["class"]["ko"],
             demon_lord["level"], demon_lord["at"], demon_lord["df"],
             demon_lord["x"], demon_lord["y"]),
            ("데몬로드", "데몬로드", 1, 46, 30, 29, 9),
        )
        self.assertEqual(demon_lord["mercenaries"], [137, 137, 137, 137, 136, 136])
        self.assertEqual(
            (vampire_lord["name"]["ko"], vampire_lord["class"]["ko"],
             vampire_lord["level"], vampire_lord["at"], vampire_lord["df"],
             vampire_lord["x"], vampire_lord["y"]),
            ("뱀파이어로드", "뱀파이어로드", 1, 43, 34, 16, 23),
        )
        self.assertEqual(vampire_lord["mercenaries"], [137, 137, 137, 137, 135, 135])

    def test_scenario_twenty_five_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 25)
        self.assertEqual(model["record_count"], 12)

        jessica = model["records"][0]
        leon = model["records"][1]
        hidden_dragon_lord = model["records"][11]
        self.assertEqual(
            (jessica["name"]["ko"], jessica["class"]["ko"], jessica["level"],
             jessica["at"], jessica["df"], jessica["x"], jessica["y"]),
            ("제시카", "워록", 2, 20, 17, 16, 18),
        )
        self.assertEqual(jessica["mercenaries"], [255, 255, 255, 255, 255, 255])
        self.assertEqual(
            (leon["name"]["ko"], leon["class"]["ko"], leon["level"],
             leon["at"], leon["df"], leon["x"], leon["y"]),
            ("레온", "로얄가드", 10, 51, 39, 16, 14),
        )
        self.assertEqual(leon["mercenaries"], [123, 123, 123, 123, 123, 123])
        self.assertEqual(
            (hidden_dragon_lord["name"]["ko"],
             hidden_dragon_lord["class"]["ko"], hidden_dragon_lord["level"],
             hidden_dragon_lord["at"], hidden_dragon_lord["df"],
             hidden_dragon_lord["x"], hidden_dragon_lord["y"],
             hidden_dragon_lord["hidden"]),
            ("제국지휘관", "드래곤로드", 10, 45, 31, 255, 255, True),
        )
        self.assertEqual(hidden_dragon_lord["mercenaries"], [125, 125, 125, 125, 125, 125])

    def test_scenario_twenty_six_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 26)
        self.assertEqual(model["record_count"], 10)

        archmage = model["records"][0]
        knight_master = model["records"][8]
        egbert = model["records"][9]
        self.assertEqual(
            (archmage["name"]["ko"], archmage["class"]["ko"],
             archmage["level"], archmage["at"], archmage["df"],
             archmage["x"], archmage["y"]),
            ("제국지휘관", "아크메이지", 5, 38, 27, 24, 20),
        )
        self.assertEqual(archmage["mercenaries"], [118, 118, 118, 118, 119, 119])
        self.assertEqual(
            (knight_master["name"]["ko"], knight_master["class"]["ko"],
             knight_master["level"], knight_master["at"], knight_master["df"],
             knight_master["x"], knight_master["y"]),
            ("제국지휘관", "나이트마스터", 10, 46, 29, 15, 5),
        )
        self.assertEqual(knight_master["mercenaries"], [122, 122, 122, 122, 124, 124])
        self.assertEqual(
            (egbert["name"]["ko"], egbert["class"]["ko"], egbert["level"],
             egbert["at"], egbert["df"], egbert["x"], egbert["y"]),
            ("에그베르트", "자베라", 10, 45, 33, 15, 8),
        )
        self.assertEqual(egbert["mercenaries"], [136, 136, 136, 136, 136, 136])

    def test_scenario_twenty_seven_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 27)
        self.assertEqual(model["record_count"], 10)
        demon_lord = model["records"][0]
        bernhardt = model["records"][8]
        hidden_leon = model["records"][9]
        self.assertEqual(
            (demon_lord["name"]["ko"], demon_lord["class"]["ko"],
             demon_lord["level"], demon_lord["at"], demon_lord["df"],
             demon_lord["x"], demon_lord["y"]),
            ("데몬로드", "데몬로드", 10, 50, 34, 15, 12),
        )
        self.assertEqual(demon_lord["mercenaries"], [137, 137, 137, 137, 136, 136])
        self.assertEqual(
            (bernhardt["name"]["ko"], bernhardt["class"]["ko"],
             bernhardt["level"], bernhardt["at"], bernhardt["df"],
             bernhardt["x"], bernhardt["y"]),
            ("베른하르트", "엠퍼러", 10, 58, 41, 15, 3),
        )
        self.assertEqual(bernhardt["mercenaries"], [124, 124, 124, 124, 118, 118])
        self.assertEqual(
            (hidden_leon["name"]["ko"], hidden_leon["class"]["ko"],
             hidden_leon["level"], hidden_leon["at"], hidden_leon["df"],
             hidden_leon["x"], hidden_leon["y"], hidden_leon["hidden"]),
            ("레온", "로얄가드", 10, 51, 39, 255, 255, True),
        )
        self.assertEqual(hidden_leon["mercenaries"], [123, 123, 123, 123, 124, 124])

    def test_scenario_twenty_eight_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 28)
        self.assertEqual(model["record_count"], 9)
        brother = model["records"][0]
        adon = model["records"][3]
        baran = model["records"][8]
        self.assertEqual(
            (brother["name"]["ko"], brother["class"]["ko"], brother["level"],
             brother["at"], brother["df"], brother["x"], brother["y"]),
            ("형님", "빌더", 1, 38, 26, 14, 16),
        )
        self.assertEqual(brother["mercenaries"], [117, 117, 117, 117, 117, 117])
        self.assertEqual(
            (adon["name"]["ko"], adon["class"]["ko"], adon["level"],
             adon["at"], adon["df"], adon["x"], adon["y"]),
            ("아돈", "빌더", 9, 45, 30, 12, 10),
        )
        self.assertEqual(adon["mercenaries"], [134, 134, 134, 134, 138, 138])
        self.assertEqual(
            (baran["name"]["ko"], baran["class"]["ko"], baran["level"],
             baran["at"], baran["df"], baran["x"], baran["y"]),
            ("바란", "빌더", 10, 47, 31, 15, 9),
        )
        self.assertEqual(baran["mercenaries"], [134, 134, 134, 134, 138, 138])

    def test_scenario_twenty_nine_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 29)
        self.assertEqual(model["record_count"], 9)
        serpent_lord = model["records"][0]
        seigal = model["records"][7]
        folger = model["records"][8]
        self.assertEqual(
            (serpent_lord["name"]["ko"], serpent_lord["class"]["ko"],
             serpent_lord["level"], serpent_lord["at"], serpent_lord["df"],
             serpent_lord["x"], serpent_lord["y"]),
            ("제국지휘관", "서펜로드", 4, 35, 32, 16, 3),
        )
        self.assertEqual(serpent_lord["mercenaries"], [120, 120, 120, 120, 120, 120])
        self.assertEqual(
            (seigal["name"]["ko"], seigal["class"]["ko"], seigal["level"],
             seigal["at"], seigal["df"], seigal["x"], seigal["y"]),
            ("세이갈", "드래곤로드", 9, 44, 31, 35, 25),
        )
        self.assertEqual(seigal["mercenaries"], [125, 125, 125, 125, 125, 125])
        self.assertEqual(
            (folger["name"]["ko"], folger["class"]["ko"], folger["level"],
             folger["at"], folger["df"], folger["x"], folger["y"]),
            ("폴거", "드래곤로드", 9, 44, 31, 36, 20),
        )
        self.assertEqual(folger["mercenaries"], [125, 125, 125, 125, 125, 125])

    def test_scenario_thirty_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 30)
        self.assertEqual(model["record_count"], 11)
        dragon = model["records"][0]
        mage_witch = model["records"][9]
        hidden_saint_witch = model["records"][10]
        self.assertEqual(
            (dragon["name"]["ko"], dragon["class"]["ko"], dragon["level"],
             dragon["at"], dragon["df"], dragon["x"], dragon["y"]),
            ("그레이트드래곤", "그레이트드래곤", 1, 39, 34, 3, 11),
        )
        self.assertEqual(dragon["mercenaries"], [132, 132, 132, 132, 135, 135])
        self.assertEqual(
            (mage_witch["name"]["ko"], mage_witch["class"]["ko"],
             mage_witch["level"], mage_witch["at"], mage_witch["df"],
             mage_witch["x"], mage_witch["y"]),
            ("마녀", "메이지", 1, 30, 21, 15, 6),
        )
        self.assertEqual(mage_witch["mercenaries"], [132, 132, 132, 132, 135, 135])
        self.assertEqual(
            (hidden_saint_witch["name"]["ko"],
             hidden_saint_witch["class"]["ko"], hidden_saint_witch["level"],
             hidden_saint_witch["at"], hidden_saint_witch["df"],
             hidden_saint_witch["x"], hidden_saint_witch["y"],
             hidden_saint_witch["hidden"]),
            ("마녀", "세인트", 7, 36, 31, 255, 255, True),
        )
        self.assertEqual(hidden_saint_witch["mercenaries"], [136, 136, 136, 136, 255, 255])

    def test_scenario_thirty_one_editor_records_match_original_rom(self):
        model = read_scenario(self.rom, self.rom, 31)
        self.assertEqual(model["record_count"], 10)
        vargas = model["records"][0]
        bozel = model["records"][7]
        bernhardt = model["records"][9]
        self.assertEqual(
            (vargas["name"]["ko"], vargas["class"]["ko"], vargas["level"],
             vargas["at"], vargas["df"], vargas["x"], vargas["y"]),
            ("발가스", "제너럴", 10, 75, 54, 15, 55),
        )
        self.assertEqual(vargas["mercenaries"], [115, 115, 115, 115, 122, 122])
        self.assertEqual(
            (bozel["name"]["ko"], bozel["class"]["ko"], bozel["level"],
             bozel["at"], bozel["df"], bozel["x"], bozel["y"]),
            ("보젤", "다크마스터", 10, 69, 54, 15, 15),
        )
        self.assertEqual(bozel["mercenaries"], [137, 137, 137, 137, 136, 136])
        self.assertEqual(
            (bernhardt["name"]["ko"], bernhardt["class"]["ko"],
             bernhardt["level"], bernhardt["at"], bernhardt["df"],
             bernhardt["x"], bernhardt["y"]),
            ("베른하르트", "엠퍼러", 10, 87, 61, 15, 4),
        )
        self.assertEqual(bernhardt["mercenaries"], [124, 124, 124, 124, 119, 119])

    def test_all_name_ids_have_explicit_labels(self):
        self.assertEqual(set(KOREAN_NAME_BY_ID), set(range(NAME_COUNT)))
        self.assertEqual(KOREAN_NAME_BY_ID[0x34], "웨어울프")
        self.assertEqual(KOREAN_NAME_BY_ID[0x68], "형님")
        self.assertEqual(KOREAN_NAME_BY_ID[0x73], "파이어스")

    def test_no_change_patch_is_byte_identical_for_all_scenarios(self):
        for number in range(1, SCENARIO_COUNT + 1):
            with self.subTest(scenario=number):
                data = bytearray(self.korean)
                model = read_scenario(bytes(data), self.rom, number)
                patch_scenario(data, number, model["records"])
                self.assertEqual(bytes(data), self.korean)

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
