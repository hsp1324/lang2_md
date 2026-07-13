from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_event_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ReviewedEventDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.rows = builder.load_reviewed_event_translations(
            ROOT / "localization/event_dialogue_ko.json"
        )

    def test_scenario_14_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 14]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 162)
        self.assertEqual(len(primary), 125)
        self.assertEqual(len(continuations), 37)
        self.assertEqual(primary[0]["address"], "0x19CF7C")
        self.assertEqual(primary[-1]["address"], "0x19EF02")
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(385, 396), *range(397, 511)],
        )

    def test_scenario_1_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 1]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 145)
        self.assertEqual(len(primary), 121)
        self.assertEqual(len(continuations), 24)
        self.assertEqual(primary[0]["address"], "0x184858")
        self.assertEqual(primary[-1]["address"], "0x18609C")
        # The English project split Japanese record 0x1849B4's second physical
        # page (0x1849DA) into its own record 2108.
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(2101, 2108), *range(2109, 2223)],
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_2_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 2]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 137)
        self.assertEqual(len(primary), 110)
        self.assertEqual(len(continuations), 27)
        self.assertEqual(primary[0]["address"], "0x18688E")
        self.assertEqual(primary[-1]["address"], "0x1881A6")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(1991, 2101)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_3_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 3]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 106)
        self.assertEqual(len(primary), 89)
        self.assertEqual(len(continuations), 17)
        self.assertEqual(primary[0]["address"], "0x188846")
        self.assertEqual(primary[-1]["address"], "0x189B64")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(2223, 2312)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_4_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 4]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 155)
        self.assertEqual(len(primary), 129)
        self.assertEqual(len(continuations), 26)
        self.assertEqual(primary[0]["address"], "0x18A3A0")
        self.assertEqual(primary[-1]["address"], "0x18C028")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(2312, 2441)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_31_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 31]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 46)
        self.assertEqual(len(primary), 44)
        self.assertEqual(len(continuations), 2)
        self.assertEqual(primary[0]["address"], "0x1B87C2")
        self.assertEqual(primary[-1]["address"], "0x1B8D1A")
        # English record 1434 is a stray cross-scenario mapping. The 44
        # Japanese records align with the contiguous Death Tower run instead.
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(1572, 1616)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_29_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 29]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 55)
        self.assertEqual(len(primary), 49)
        self.assertEqual(len(continuations), 6)
        self.assertEqual(primary[0]["address"], "0x1B6F00")
        self.assertEqual(primary[-1]["address"], "0x1B764C")
        self.assertEqual(
            [row["english_record"] for row in primary[:47]],
            list(range(1170, 1217)),
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in primary[47:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_30_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 30]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 70)
        self.assertEqual(len(primary), 65)
        self.assertEqual(len(continuations), 5)
        self.assertEqual(primary[0]["address"], "0x1B7B0C")
        self.assertEqual(primary[-1]["address"], "0x1B832A")
        self.assertEqual(
            [row["english_record"] for row in primary[:64]],
            list(range(1370, 1434)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_24_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 24]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 65)
        self.assertEqual(len(primary), 53)
        self.assertEqual(len(continuations), 12)
        self.assertEqual(primary[0]["address"], "0x1AF8E8")
        self.assertEqual(primary[-1]["address"], "0x1B03A8")
        # The English project split and merged several physical Japanese
        # pages differently. Records 1569..1571 are stray mappings, while
        # the Japanese block ends in two source-only resolution lines.
        self.assertEqual(
            [row["english_record"] for row in rows[:63]],
            [
                1435, 1436, 1437, 1438, 1439, 1440, 1441, 1442,
                1443, 1443, 1444, 1445, 1446, 1447, 1447, 1447,
                1448, 1449, 1450, 1451, 1452, 1453, 1454, 1455,
                1456, 1457, 1458, 1459, 1460, 1461, 1462, 1463,
                1464, 1465, 1466, 1466, 1467, 1468, 1469, 1470,
                1471, 1472, 1472, 1473, 1474, 1475, 1476, 1476,
                1477, 1477, 1478, 1479, 1479, 1480, 1481, 1481,
                1482, 1482, 1482, 1483, 1484, 1485, 1486,
            ],
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in rows[63:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_21_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 21]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 80)
        self.assertEqual(len(primary), 71)
        self.assertEqual(len(continuations), 9)
        self.assertEqual(primary[0]["address"], "0x1A9A8A")
        self.assertEqual(primary[-1]["address"], "0x1AA884")
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(912, 981), 1168, 1169],
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_22_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 22]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 191)
        self.assertEqual(len(primary), 151)
        self.assertEqual(len(continuations), 40)
        self.assertEqual(primary[0]["address"], "0x1AB182")
        self.assertEqual(primary[-1]["address"], "0x1AD326")
        # English 981/982 are cross-scenario residue. The 150 aligned records
        # are 1219..1368, followed by one Japanese-only resolution record.
        self.assertEqual(
            [row["english_record"] for row in primary[:150]],
            list(range(1219, 1369)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_16_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 16]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 98)
        self.assertEqual(len(primary), 87)
        self.assertEqual(len(continuations), 11)
        self.assertEqual(primary[0]["address"], "0x1A1058")
        self.assertEqual(primary[-1]["address"], "0x1A1F78")
        # English 705/706 physically complete Scenario 15. The final Japanese
        # record is a source-only two-page resolve to defeat the Emperor and
        # rescue the controlled ally.
        self.assertEqual(
            [row["english_record"] for row in primary[:86]],
            list(range(511, 597)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_15_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 15]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 118)
        self.assertEqual(len(primary), 110)
        self.assertEqual(len(continuations), 8)
        self.assertEqual(primary[0]["address"], "0x19F782")
        self.assertEqual(primary[-1]["address"], "0x1A0A6E")
        # The English project grouped 598..704 under Scenario 15 and the two
        # final Rayguard-castle lines 705/706 under Scenario 16. The Japanese
        # event block proves that all 109 records belong to this scenario;
        # duplicate short Japanese battle reactions reuse their closest
        # semantic English reference.
        self.assertEqual(primary[0]["english_record"], 598)
        self.assertEqual(primary[-2]["english_record"], 705)
        self.assertEqual(primary[-1]["english_record"], 706)
        self.assertTrue(all(row["english_record"] is not None for row in rows))
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_17_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 17]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 135)
        self.assertEqual(len(primary), 108)
        self.assertEqual(len(continuations), 27)
        self.assertEqual(primary[0]["address"], "0x1A2716")
        self.assertEqual(primary[-1]["address"], "0x1A416E")
        # English 597 is the final Scenario 16 resolve. The Japanese throne
        # battle then aligns one-for-one with English records 804..911.
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(804, 912)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_18_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 18]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 117)
        self.assertEqual(len(primary), 95)
        self.assertEqual(len(continuations), 22)
        self.assertEqual(primary[0]["address"], "0x1A48AA")
        self.assertEqual(primary[-1]["address"], "0x1A5DD0")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(707, 802)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_19_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 19]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 116)
        self.assertEqual(len(primary), 98)
        self.assertEqual(len(continuations), 18)
        self.assertEqual(primary[0]["address"], "0x1A6456")
        self.assertEqual(primary[-1]["address"], "0x1A7868")
        # English 802/803 physically close Scenario 18. Scenario 19 aligns
        # with 983..1077 and ends in three Japanese-only sortie-delay lines.
        self.assertEqual(
            [row["english_record"] for row in primary[:95]],
            list(range(983, 1078)),
        )
        self.assertTrue(
            all(
                row["english_record"] is None and row["japanese_only"]
                for row in primary[95:]
            )
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_20_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 20]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 111)
        self.assertEqual(len(primary), 88)
        self.assertEqual(len(continuations), 23)
        self.assertEqual(primary[0]["address"], "0x1A7E02")
        self.assertEqual(primary[-1]["address"], "0x1A94BA")
        # English 1078..1080 physically close Scenario 19. Japanese page
        # grouping differs around multi-page battle lines, and three final
        # route variants deliberately share the closest English row 1167.
        self.assertEqual(
            {row["english_record"] for row in rows},
            set(range(1081, 1168)),
        )
        self.assertEqual(
            [row["english_record"] for row in primary[-3:]],
            [1167, 1167, 1167],
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_5_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 5]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 87)
        self.assertEqual(len(primary), 79)
        self.assertEqual(len(continuations), 8)
        self.assertEqual(primary[0]["address"], "0x18C6D2")
        self.assertEqual(primary[-1]["address"], "0x18D5C4")
        # English 2442/2443 are previous-scenario residue. Its single final
        # village line 2520 represents three route-specific Japanese rows.
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(2444, 2521), 2520, 2520],
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_6_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 6]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 122)
        self.assertEqual(len(primary), 102)
        self.assertEqual(len(continuations), 20)
        self.assertEqual(primary[0]["address"], "0x18DCC0")
        self.assertEqual(primary[-1]["address"], "0x18F24C")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(2521, 2623)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_7_has_all_real_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 7]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 117)
        self.assertEqual(len(primary), 100)
        self.assertEqual(len(continuations), 17)
        self.assertEqual(primary[0]["address"], "0x18F88A")
        self.assertEqual(primary[-1]["address"], "0x190CEC")
        self.assertNotIn("0x18F610", {row["address"] for row in rows})
        self.assertEqual(
            [row["english_record"] for row in primary[:-2]],
            list(range(2625, 2723)),
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in primary[-2:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_8_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 8]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 128)
        self.assertEqual(len(primary), 103)
        self.assertEqual(len(continuations), 25)
        self.assertEqual(primary[0]["address"], "0x191416")
        self.assertEqual(primary[-1]["address"], "0x192B14")
        # English 2723/2724 physically close Scenario 7. The first 102
        # Japanese records then align with 2725..2826; the final two-page
        # observation exists only in the Japanese event block.
        self.assertEqual(
            [row["english_record"] for row in primary[:-1]],
            list(range(2725, 2827)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_9_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 9]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 169)
        self.assertEqual(len(primary), 147)
        self.assertEqual(len(continuations), 22)
        self.assertEqual(primary[0]["address"], "0x1934B0")
        self.assertEqual(primary[-1]["address"], "0x195426")
        # English 2827 closes Scenario 8. The first 146 Japanese records align
        # with 2828..2973 and the final two-page assault order is source-only.
        self.assertEqual(
            [row["english_record"] for row in primary[:-1]],
            list(range(2828, 2974)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_10_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 10]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 112)
        self.assertEqual(len(primary), 108)
        self.assertEqual(len(continuations), 4)
        self.assertEqual(primary[0]["address"], "0x195CB6")
        self.assertEqual(primary[-1]["address"], "0x197046")
        # English 2974 closes Scenario 9. Japanese 0..103 align with
        # 2975..3078, followed by four source-only Necklace reward records.
        self.assertEqual(
            [row["english_record"] for row in primary[:104]],
            list(range(2975, 3079)),
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in primary[104:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_11_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 11]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 117)
        self.assertEqual(len(primary), 96)
        self.assertEqual(len(continuations), 21)
        self.assertEqual(primary[0]["address"], "0x197680")
        self.assertEqual(primary[-1]["address"], "0x198D98")
        # English 3079..3081 close Scenario 10. English numbering then wraps
        # by ROM-bank order; Japanese records 0..94 align with English 0..94,
        # followed by one source-only fire-escape instruction.
        self.assertEqual(
            [row["english_record"] for row in primary[:95]],
            list(range(95)),
        )
        self.assertIsNone(primary[-1]["english_record"])
        self.assertTrue(primary[-1]["japanese_only"])
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_12_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 12]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 113)
        self.assertEqual(len(primary), 88)
        self.assertEqual(len(continuations), 25)
        self.assertEqual(primary[0]["address"], "0x199344")
        self.assertEqual(primary[-1]["address"], "0x19A93E")
        # English 95 closes Scenario 11. The opening 28 Japanese records align
        # with English 200..227; later death and route branches diverge in
        # order, including source-only illness and Liana-return variants.
        self.assertEqual(
            [row["english_record"] for row in primary[:28]],
            list(range(200, 228)),
        )
        self.assertTrue(primary[30]["japanese_only"])
        self.assertTrue(primary[86]["japanese_only"])
        self.assertEqual(primary[-1]["english_record"], 287)
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_13_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 13]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 126)
        self.assertEqual(len(primary), 96)
        self.assertEqual(len(continuations), 30)
        self.assertEqual(primary[0]["address"], "0x19AEE0")
        self.assertEqual(primary[-1]["address"], "0x19C6F4")
        # English 288 closes Scenario 12. Japanese 0..93 align with
        # English 289..382, followed by two source-only final vows.
        self.assertEqual(
            [row["english_record"] for row in primary[:94]],
            list(range(289, 383)),
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in primary[94:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_23_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 23]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 92)
        self.assertEqual(len(primary), 83)
        self.assertEqual(len(continuations), 9)
        self.assertEqual(primary[0]["address"], "0x1AE846")
        self.assertEqual(primary[-1]["address"], "0x1AF506")
        # English 1369 is previous-scenario residue. Records 1569..1571 were
        # grouped under Scenario 24 in that project, but physically complete
        # this Japanese Holy Rod / Langrisser-seal block.
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(1489, 1572)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_25_has_all_reviewed_dialogue_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 25]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 131)
        self.assertEqual(len(primary), 99)
        self.assertEqual(len(continuations), 32)
        self.assertEqual(primary[0]["address"], "0x1B0982")
        self.assertEqual(primary[0]["english_record"], 1799)
        self.assertEqual(primary[15]["english_record"], 1815)
        self.assertEqual(primary[90]["english_record"], 1891)
        self.assertEqual(primary[96]["english_record"], 1898)
        self.assertEqual(
            [row["english_record"] for row in continuations if row["address"] in ("0x1B09AC", "0x1B0E5A", "0x1B1E80")],
            [1800, 1816, 1892],
        )
        self.assertTrue(
            all(row["english_record"] is None and row["japanese_only"] for row in primary[-2:])
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_26_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 26]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 102)
        self.assertEqual(len(primary), 71)
        self.assertEqual(len(continuations), 31)
        self.assertEqual(primary[0]["address"], "0x1B2494")
        self.assertEqual(primary[-1]["address"], "0x1B3832")
        self.assertEqual(
            [row["english_record"] for row in primary[:69]],
            list(range(1616, 1685)),
        )
        self.assertTrue(
            all(
                row["english_record"] is None and row["japanese_only"]
                for row in primary[69:]
            )
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_dynamic_name_controls_and_terminators_are_preserved(self):
        for row in self.rows:
            address = int(row["address_int"])
            jp_capacity, jp_terminator, jp_controls = builder.event_page_layout(
                self.japanese, address
            )
            ko_capacity, ko_terminator, ko_controls = builder.event_page_layout(
                self.korean, address
            )
            self.assertEqual(ko_capacity, jp_capacity, row["address"])
            self.assertEqual(ko_terminator, jp_terminator, row["address"])
            self.assertEqual(ko_controls, jp_controls, row["address"])

    def test_declared_complete_scenarios_match_modified_pages(self):
        result = inventory(self.japanese, self.korean)
        for scenario_number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31):
            rows = [row for row in self.rows if row["scenario"] == scenario_number]
            scenario = result["scenarios"][scenario_number - 1]
            modified = [page["address"] for page in scenario["pages"] if page["modified"]]
            declared = [row["address"] for row in rows if not row.get("continuation")]
            self.assertEqual(modified, declared)
            modified_physical = {
                physical["address"]
                for page in scenario["pages"]
                for physical in page["physical_pages"]
                if physical["modified"]
            }
            self.assertEqual(modified_physical, {row["address"] for row in rows})

    def test_live_reached_scenario_speaker_names_are_in_safe_patch_set(self):
        expected = {
            0x97404: "엘윈",
            0x97418: "라나",
            0x97420: "쉐리",
            0x97432: "스코트",
            0x9743C: "키스",
            0x97444: "아론",
            0x9744E: "레스터",
            0x97458: "제시카",
            0x97474: "베른하르트",
            0x97482: "발가스",
            0x9748C: "보젤",
            0x974AA: "졸름",
            0x974B2: "에그베르트",
            0x974BE: "이멜다",
            0x974C8: "모건",
            0x974DA: "크레이머",
            0x97504: "지휘관",
            0x97526: "로렌",
            0x97594: "리치",
            0x97648: "신관",
        }
        for address, text in expected.items():
            self.assertEqual(builder.DIRECT_STRING_PATCHES[address], text)
            capacity = builder.direct_string_capacity_words(self.japanese, address)
            self.assertEqual(
                builder.be16(self.korean, address + (capacity - 1) * 2),
                0xFFFF,
            )
            self.assertNotEqual(
                self.korean[address : address + capacity * 2],
                self.japanese[address : address + capacity * 2],
            )


if __name__ == "__main__":
    unittest.main()
