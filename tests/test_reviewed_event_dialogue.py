from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_event_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x19D4A0"],
            "늦어서 미안하다.\n아기를 안은 엘리자에게\n"
            "{000F}의 전사를 알릴 수 없었어",
        )
        self.assertNotIn("{000F}장군", text_by_address["0x19D4A0"])
        self.assertEqual(
            text_by_address["0x19D87C"],
            "죽음을 전하는 건 괴롭다\n갓 출산한 분께는 힘들겠지",
        )
        self.assertFalse(text_by_address["0x19D87C"].endswith("."))
        self.assertEqual(len(text_by_address["0x19D87C"].splitlines()), 2)
        self.assertTrue(
            all(len(line) <= 14 for line in text_by_address["0x19D87C"].splitlines())
        )
        self.assertEqual(
            text_by_address["0x19D5E2"],
            "하루빨리 대륙을 통일해\n전쟁 없는 세상을 만들겠다.",
        )
        self.assertTrue(
            all(len(line) <= 15 for line in text_by_address["0x19D5E2"].splitlines())
        )
        self.assertEqual(
            text_by_address["0x19EF3E"],
            "야망을 꺾기 위해\n랑그릿사의 가호 아래\n싸워 {0002}를 구해 내자!",
        )
        self.assertTrue(
            all(
                len(builder.EVENT_NAME_CONTROL_RE.sub("이름", line)) <= 14
                for line in text_by_address["0x19EF3E"].splitlines()
            )
        )
        self.assertEqual(
            text_by_address["0x19E31C"],
            "랑그릿사를 얻었다!",
        )
        self.assertEqual(
            text_by_address["0x19E33A"],
            "임무는 끝났다.\n더 싸울 이유는 없다.\n전군 퇴각!",
        )
        self.assertEqual(text_by_address["0x19E386"], "잘 있어!")
        self.assertEqual(text_by_address["0x19E392"], "다 끝났어….")
        self.assertEqual(
            text_by_address["0x19E3B8"],
            "조금만 더 버텼다면\n랑그릿사는 우리 것인데….",
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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x1848C0"],
            "{0005}, 마을 어귀는 네 소꿉친구가 사는 곳 아니야?",
        )

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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x18964C"],
            "가자! 모두 소녀를 잡아라!",
        )
        self.assertEqual(
            text_by_address["0x1898F4"],
            "하지만 여기까지다! 소녀는 데려가겠다!",
        )

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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(text_by_address["0x18B39A"], "시카시카!")
        self.assertEqual(text_by_address["0x18B3A6"], "시, 시카앗!")

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
        self.assertEqual(
            [row["address"] for row in rows if "\n" in row["text"]],
            ["0x1B89E2"],
        )
        self.assertEqual(
            next(row for row in rows if row["address"] == "0x1B89E2")["text"],
            "죄송합니다…\n퇴각하겠습니다…",
        )

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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x1AA75C"],
            "앗! {0060}이다!",
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
        wrapped = [row for row in rows if "\n" in row["text"]]
        self.assertEqual(
            [(row["address"], row["text"]) for row in wrapped],
            [
                (
                    "0x1ACF52",
                    "벨제리아 성 지하엔\n혼돈의 신이 잠들어 있습니다.\n"
                    "알하자드도 그곳에 있을 겁니다.",
                )
            ],
        )

    def test_scenario_22_opening_preserves_japanese_meaning(self):
        rows = {
            row["address"]: row["text"]
            for row in self.rows
            if row["scenario"] == 22
        }
        self.assertEqual(rows["0x1AB208"], "둘은 다른 사람이었나?")
        self.assertEqual(
            rows["0x1AB248"],
            "어둠의 검은 빛의 무녀가 봉인했군… 말이 되는군.",
        )
        self.assertEqual(
            rows["0x1AB2A4"],
            "봉인을 풀고 어둠의 힘을 불어넣는 역할이겠죠.",
        )
        self.assertNotIn("때가 되면 푸는군", rows["0x1AB248"])

    def test_scenario_23_dynamic_party_name_is_natural_korean(self):
        rows = {
            row["address"]: row["text"]
            for row in self.rows
            if row["scenario"] == 23
        }
        self.assertEqual(
            rows["0x1AE9F6"],
            "{0001} 일행인가? 놈들보다 먼저 찾아야 해!",
        )
        self.assertNotIn("{0001}들", rows["0x1AE9F6"])

    def test_scenario_23_completion_and_defeat_lines_preserve_context(self):
        rows = {
            row["address"]: row["text"]
            for row in self.rows
            if row["scenario"] == 23
        }
        self.assertEqual(rows["0x1AECEA"], "크윽…")
        self.assertEqual(rows["0x1AECF6"], "으아악…")
        self.assertEqual(
            rows["0x1AEE1E"],
            "성스러운 지팡이 획득!",
        )
        self.assertNotIn("바보야", rows["0x1AECEA"])
        self.assertNotIn("빼앗겼", rows["0x1AEE1E"])

    def test_scenario_25_opening_preserves_japanese_meaning(self):
        rows = {
            row["address"]: row["text"]
            for row in self.rows
            if row["scenario"] == 25
        }
        self.assertEqual(
            rows["0x1B09EA"],
            "폐하를 이계로 날려 보낸 어리석은 마술사여.",
        )
        self.assertEqual(rows["0x1B0A20"], "알하자드의 힘을 너무 얕봤구나.")
        self.assertEqual(
            rows["0x1B0A50"],
            "기다려라, {0014}. 난 비겁하게 인질을 쓰지 않는다.",
        )
        self.assertEqual(
            rows["0x1B0AEE"],
            "후후후… 무르군, {000D}. 하지만 그게 네 장점이지.",
        )
        self.assertEqual(
            rows["0x1B0B64"],
            "놈들을 맞을 준비를 하지. 헛수고로 끝나면 좋겠군.",
        )
        self.assertEqual(
            rows["0x1B0C12"],
            "{000E}가 알하자드의 힘을 풀어 세상에 큰 이변이 닥치려 해!",
        )
        rejected = "\n".join(rows[address] for address in (
            "0x1B09EA", "0x1B0A50", "0x1B0AEE", "0x1B0B64", "0x1B0C12",
        ))
        for phrase in ("이세계로", "하지 마라", "고지식하군", "헛수고가 아니길", "힘을 풀면"):
            self.assertNotIn(phrase, rejected)

    def test_scenario_26_preserves_japanese_meaning(self):
        rows = {
            row["address"]: row["text"]
            for row in self.rows
            if row["scenario"] == 26
        }
        self.assertEqual(
            rows["0x1B2A48"],
            "대륙 제일의 군사국가 앞에선 어둠의 군세도 상대가 안 된다…",
        )
        self.assertEqual(
            rows["0x1B3394"],
            "싸움은 데스타워에서 한다. 우리 힘을 키우는 내 마법탑이지.",
        )
        self.assertEqual(
            rows["0x1B34FC"],
            "…덕분에 안심하고 지옥에 갈 수 있겠군요…",
        )
        self.assertEqual(
            rows["0x1B3538"],
            "다시… 태어날 수 있다면… 한 번 더… 스승님과…",
        )
        self.assertEqual(
            rows["0x1B35B4"],
            "{0014}는 {0010}과 싸울 강대한 힘이 급히 필요했죠…",
        )
        self.assertEqual(
            rows["0x1B2EFC"],
            "잘 싸웠다. 하지만 끝이다.\n제국에 맞선 것부터 무모했군",
        )
        self.assertNotIn("대륙 규모", rows["0x1B2A48"])
        self.assertNotIn("저승", rows["0x1B34FC"])
        self.assertNotIn("스승님께", rows["0x1B3538"])
        self.assertNotIn("{0010}와 싸울", rows["0x1B35B4"])

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
        self.assertEqual(
            [row["address"] for row in rows if "\n" in row["text"]],
            ["0x1A1E44", "0x1A1F32", "0x1A1FBA"],
        )
        by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            by_address["0x1A1E44"],
            "드디어 최후의\n결전이 시작되는군.",
        )
        self.assertEqual(
            by_address["0x1A1F32"],
            "알하자드 곁에 {0002}를\n조종하는 자도 있을 거야.",
        )
        self.assertEqual(
            by_address["0x1A1FBA"],
            "그리고 {0002}도\n꼭 구하겠어!",
        )

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
        by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(by_address["0x19FF78"], "뭔 짓이야!")
        self.assertEqual(
            by_address["0x1A012A"],
            "{0015}님은 부하를 조금도 안 아끼나?",
        )
        self.assertEqual(
            by_address["0x1A01A0"],
            "각오하세요, {0015}님!",
        )
        self.assertEqual(
            by_address["0x1A03F0"],
            "{0002}! 나야, {0001}! 못 알아봐?",
        )
        self.assertEqual(
            by_address["0x1A0844"],
            "그녀에게 걸린 술법이 느껴졌어요.",
        )
        self.assertEqual(
            by_address["0x1A087E"],
            "그녀를 부른 목소리도 들어 본 적이 있어요. 어쩌면…",
        )
        self.assertEqual(
            by_address["0x1A0A6E"],
            "알았어. {0002}가 걱정돼. 서두르자!",
        )
        self.assertNotIn("{0002}도 걱정돼", by_address["0x1A0A6E"])

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
        by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            by_address["0x1A2852"],
            "…… {0002}가 없다!\n어디 간 거지!?",
        )
        self.assertEqual(
            [row["address"] for row in rows if "\n" in row["text"]],
            ["0x1A2852", "0x1A296C"],
        )
        self.assertEqual(
            by_address["0x1A296C"],
            "당신은 이용당할 뿐이다.\n알하자드는 생각대로\n힘을 주는 검이 아니다.",
        )
        self.assertEqual(
            by_address["0x1A2A98"],
            "잡담할 여유가 있다면 싸움으로 보여 줘라!",
        )
        self.assertEqual(
            by_address["0x1A2A0C"],
            "결국 그 검에 지배당하고 말 것입니다!",
        )
        self.assertEqual(
            by_address["0x1A2A54"],
            "아무리 저주받은 마검이라도 그 힘은 내가 지배해 보이겠다.",
        )
        self.assertEqual(by_address["0x1A2AE6"], "좋아! 간다, 모두!")
        self.assertEqual(by_address["0x1A2B08"], "폐하! 무사하오")
        self.assertEqual(
            by_address["0x1A2B1A"],
            "음, 잘 왔다. 적의 측면을 공격하라!",
        )

    def test_ending_player_feedback_particle_and_context_fixes(self):
        by_address = {row["address"]: row["text"] for row in self.rows}
        self.assertEqual(
            by_address["0x18D5C4"],
            "좋아! {0016}이 마을에 닿기 전에 잡자!",
        )
        self.assertEqual(
            by_address["0x18ED7C"],
            "그러고 보니 {0016}은 이 마을에서 무언가 찾는 듯했는데…",
        )
        self.assertEqual(
            by_address["0x193810"],
            "원군이라고!? {0018}가 당했나!",
        )
        self.assertEqual(by_address["0x192964"], "걱정 마.")
        self.assertEqual(by_address["0x192992"], "걱정 마.")
        self.assertEqual(
            by_address["0x199982"],
            "힘에 도취된 당신은 더는 내 제자가 아닙니다.",
        )
        self.assertEqual(
            by_address["0x1A3A66"],
            "알하자드 부활을 위해 {000E} 황제는 {0010}에게 조종당했을 거야.",
        )
        self.assertEqual(
            by_address["0x1AE9B6"],
            "이끄는 건 {000D}이 아니라 부단장 {0011}인 듯해!",
        )
        self.assertEqual(by_address["0x1AC066"], "이긴다!")
        self.assertFalse(
            any(
                bad in row["text"]
                for row in self.rows
                for bad in ("{0010}가", "{0010}를", "{0010}는", "{0010}와")
            )
        )

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
        by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            [row["address"] for row in rows if "\n" in row["text"]],
            ["0x1A497A"],
        )
        self.assertEqual(
            by_address["0x1A497A"],
            "정의로운 척하는군!\n{0010}님은 인간이 마물의\n먹이라고 하셨다.",
        )

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
        by_address = {row["address"]: row for row in rows}
        self.assertEqual(by_address["0x1A81E6"]["text"], "전하")
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
        corrected = next(row for row in rows if row["address"] == "0x193834")
        self.assertEqual(
            corrected["text"],
            "{000D}님이 없는 지금, 망설일 수 없다. 청룡기사단의 힘을 보여 주마!",
        )
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x193AD4"],
            "하지만 팔랑크스나 그리폰으로 공격하면 이길 수도 있습니다.",
        )

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
        corrected = next(row for row in rows if row["address"] == "0x195DF6")
        self.assertEqual(corrected["text"], "해적인가? 저 정도로는 못 막아. 가자!")
        corrected_text = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            corrected_text["0x19611A"],
            "그렇군. 육지에서 싸우면 우리가 더 강하겠어.",
        )
        self.assertEqual(
            corrected_text["0x196162"],
            "이 녀석들은 못 지나간다! 가자, 얘들아!",
        )
        self.assertEqual(corrected_text["0x1961A8"], "두목! 저놈들 꽤 강합니다!")
        self.assertEqual(corrected_text["0x1961D4"], "맞아요! 조심하는 게 좋겠어요.")
        self.assertEqual(
            corrected_text["0x196218"],
            "두목! 저놈들은 조심해서 상대해야 합니다.",
        )

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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(
            text_by_address["0x1986FE"],
            "뭐라고요!? …알겠습니다",
        )

    def test_scenario_12_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 12]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 113)
        self.assertEqual(len(primary), 88)
        self.assertEqual(len(continuations), 25)
        self.assertEqual(primary[0]["address"], "0x199344")
        self.assertEqual(primary[-1]["address"], "0x19A93E")
        # English 95 closes Scenario 11. Japanese page 0x199854 is the short
        # implicit {0014}! page for English record 215, so it remains a
        # physical continuation while the following primary pages resume at
        # English 216. Later death and route branches diverge in order,
        # including source-only illness and Liana-return variants.
        self.assertEqual(
            [row["english_record"] for row in primary[:28]],
            [*range(200, 215), *range(216, 229)],
        )
        self.assertTrue(primary[30]["japanese_only"])
        self.assertTrue(primary[86]["japanese_only"])
        self.assertEqual(primary[-1]["english_record"], 287)
        self.assertTrue(all("\n" not in row["text"] for row in rows))

        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(text_by_address["0x199854"], "{0014}!")
        self.assertEqual(
            text_by_address["0x199ABA"],
            "근육 신전 입구? 무슨 뜻이지… 뭐, 나중에 보자.",
        )
        self.assertEqual(text_by_address["0x199AF8"], "카벙클을 발견했다!")
        self.assertEqual(
            text_by_address["0x199B88"],
            "크윽! 여기까지인가…",
        )
        self.assertEqual(
            text_by_address["0x19A67A"],
            "검도 마찬가지입니다. 어떻게 쓰느냐가 중요합니다",
        )
        self.assertEqual(
            text_by_address["0x19A87E"],
            "{0002}가 납치됐다면 지금까지 싸운 보람이 없어",
        )
        self.assertEqual(
            text_by_address["0x19A8F4"],
            "{0002}가 납치됐다면 지금까지 싸운 보람이 없어",
        )
        for address in ("0x199638", "0x19A67A", "0x19A6D6", "0x19A87E", "0x19A8F4"):
            self.assertFalse(
                text_by_address[address].endswith("."),
                f"Scenario 12 live layout leaves final punctuation orphaned at {address}",
            )

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
        text_by_address = {row["address"]: row["text"] for row in rows}
        self.assertEqual(text_by_address["0x19B660"], "젠장! 끝인가…")

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
        self.assertEqual(
            [row["address"] for row in rows if "\n" in row["text"]],
            ["0x1B2EFC"],
        )

    def test_scenario_27_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 27]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 126)
        self.assertEqual(len(primary), 97)
        self.assertEqual(len(continuations), 29)
        self.assertEqual(primary[0]["address"], "0x1B3DF2")
        self.assertEqual(primary[-1]["address"], "0x1B54D4")
        self.assertEqual(
            [row["english_record"] for row in primary[:82]],
            list(range(1687, 1769)),
        )
        self.assertEqual(
            [row["english_record"] for row in primary[82:95]],
            list(range(1770, 1783)),
        )
        self.assertEqual(
            next(row for row in continuations if row["address"] == "0x1B51F0")["english_record"],
            1769,
        )
        self.assertTrue(
            all(
                row["english_record"] is None and row["japanese_only"]
                for row in primary[95:]
            )
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_28_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 28]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 116)
        self.assertEqual(len(primary), 104)
        self.assertEqual(len(continuations), 12)
        self.assertEqual(primary[0]["address"], "0x1B5B7A")
        self.assertEqual(primary[-1]["address"], "0x1B6B4C")
        self.assertEqual(
            [row["english_record"] for row in primary[:102]],
            list(range(96, 198)),
        )
        self.assertTrue(
            all(
                row["english_record"] is None and row["japanese_only"]
                for row in primary[102:]
            )
        )
        wrapped = [row for row in rows if "\n" in row["text"]]
        self.assertEqual(
            [(row["address"], row["text"]) for row in wrapped],
            [
                (
                    "0x1B5D92",
                    "몸이 터지기 전에 놈들을\n쓰러뜨려라! 모두 힘내라!",
                )
            ],
        )

    def test_arca_179646819_confirmed_dialogue_corrections(self):
        text_by_address = {row["address"]: row["text"] for row in self.rows}
        expected = {
            "0x1851B2": "외곽을 뚫고 {001C}을 직접 치겠습니다.",
            "0x18568C": "{000D}님, {0025}이 왔습니다!",
            "0x18905C": "건방진 놈들! 이 조름님의 전술을 비웃다니! 잔머리를 굴려 봐야 헛수고다!",
            "0x18A614": "그렇다면 순순히 죽어 주십시오…",
            "0x18B642": "술법을 건 {0016}을 쓰러뜨리면 {0002}도 돌아올 거야.",
            "0x18B68E": "알았어! {0016}을 쓰러뜨리면 돼!",
            "0x18BD66": "알았어. 그럼 서둘러 {0016}을 쫓자.",
            "0x18C7BC": "하지만 서둘러 쓰러뜨리지 않으면 {0016}을 놓쳐.",
            "0x18C94C": "시간 없어. {0016}을 쫓자.",
            "0x18CA5E": "모두 서둘러! 여기서 지체하면 {0016}을 놓친다!",
            "0x18EBAE": "{0008}은 내 검술 스승이야",
            "0x18FD7A": "그렇군! 그럼 {0005}이 슬라임을 맡아 줘.",
            "0x192986": "맡기십시오",
            "0x194B48": "사제님!",
            "0x194ED2": "그렇습니다. 하지만 문서에는 다크로드의 위치가 적혀 있지 않습니다.",
            "0x195FCE": "대체 뭐지? 왜 마물들이 우리를 노리는 거야?",
            "0x1960D4": "{003E}는 물속에서 상대하지 마! 육지로 유인해!",
            "0x196408": "이 망할 마물들! 내가 상대해 주마!",
            "0x19690E": "죽여라! 한 명도 살려 보내지 마라!",
            "0x196ADC": "너희, 제법인데? 그래서 어디로 가려던 거지?",
            "0x196DB2": "갈 곳을 알아?",
            "0x196DE4": "모르긴 뭘 몰라. 난 {000A}님의 제자 {0009}다.",
            "0x196E1E": "수상한 자들이 {000A}님께 접근하지 못하게 지키는 게 내 일이지.",
            "0x196E6E": "솔직히 말하지. 제국의 암흑검 부활을 막으려면 그 대마술사의 힘이 필요해.",
            "0x196F1E": "좋아, 내게 맡겨. 너희가 마음에 들었다!",
            "0x19B2A6": "비행 부대는 괜찮아. {0005}도 참, 거짓말을 가르치면 안 되지!",
            "0x19BE5E": "레아드, 기사단을 이끌고 그 성을 찾아라! 난 엘리자에게 알린 뒤 곧 합류하겠다.",
            "0x19EF02": "어떻게 해서든\n알하자드의 봉인을\n풀게 둘 순 없다!",
            "0x1A4FDA": "{0010}님 앞을 막는 자는 누구도 살려 두지 않겠다!",
            "0x1A6A40": "{000D}님도 지금은 참으라 하셨다. {000D}님은 사욕을 위해 힘을 쓰실 분이 아니다!",
            "0x1A719A": "네가 죽으면 {000D}님을 뵐 면목이 없으니까.",
            "0x1A82F6": "{0060}과 바다에서 싸우지 마! 배 위로 유인해!",
            "0x1A87F0": "좋아! 그대로 {0060}을 배 위로 유인하자.",
            "0x1ACD0C": "언니! {0003} 언니!",
            "0x1ACD3E": "{0003} 언니, 못 볼 줄 알았어…",
            "0x1B0A98": "이건 나와 {0001}의 싸움이다.",
            "0x1B117E": "제국이든 {0001}이든, 힘 있는 자가 대륙을 평화로 이끌 것이다.",
            "0x1B1632": "여긴… 못 지나간다…",
            "0x1B1652": "크윽…",
            "0x1B1872": "건강하십시오… 제국을 부탁드립니다.",
            "0x1B3726": "{0010} 때문에 스승과 헤어져서까지 목적을 이루어야 했다니, 참 슬픈 운명이군요…",
            "0x1B498C": "{000D}을 이겼다고 자만하지 마라.",
            "0x1B5140": "폐하! 마지막 길을 함께하게 해 주십시오!",
        }
        self.assertEqual(
            {address: text_by_address[address] for address in expected},
            expected,
        )

    def test_arca_179646819_wrong_particles_and_meanings_do_not_regress(self):
        text_by_address = {row["address"]: row["text"] for row in self.rows}
        forbidden = {
            "0x18568C": ("{0025}가",),
            "0x18B642": ("{0016}를",),
            "0x18B68E": ("{0016}를",),
            "0x18BD66": ("{0016}를",),
            "0x18EBAE": ("{0008}는",),
            "0x194ED2": ("있는 곳도 적혀",),
            "0x19690E": ("혼자 살려",),
            "0x196DE4": ("님의 동생", "모르겠는데"),
            "0x196E6E": ("암흑검을 부활시켜", "대마술사를 만나야"),
            "0x196F1E": ("안내하지", "따라와"),
            "0x19B2A6": ("책사 흉내", "군사를 따라"),
            "0x19BE5E": ("레온, 넌 병력을",),
            "0x1A6A40": ("우리를 위해 힘을 쓰실 분이 아니다", "배신하실 리 없다"),
            "0x1ACD0C": ("누나",),
            "0x1ACD3E": ("누나",),
            "0x1B1632": ("보낼 순", "지나가게"),
            "0x1B1652": ("안돼", "없다"),
            "0x1B5140": ("전하",),
        }
        for address, fragments in forbidden.items():
            for fragment in fragments:
                self.assertNotIn(fragment, text_by_address[address], address)

    def test_dynamic_name_controls_and_terminators_are_preserved(self):
        for row in self.rows:
            address = int(row["address_int"])
            korean_address = builder.relocated_event_text_address(address)
            jp_capacity, jp_terminator, jp_controls = builder.event_page_layout(
                self.japanese, address
            )
            ko_capacity, ko_terminator, ko_controls = builder.event_page_layout(
                self.korean, korean_address
            )
            self.assertEqual(ko_capacity, jp_capacity, row["address"])
            self.assertEqual(ko_terminator, jp_terminator, row["address"])
            self.assertEqual(ko_controls, jp_controls, row["address"])

    def test_declared_complete_scenarios_match_modified_pages(self):
        result = inventory(self.japanese, self.korean)
        for scenario_number in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31):
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
            0x974AA: "조름",
            0x974B2: "에그베르트",
            0x974BE: "이멜다",
            0x974C8: "모건",
            0x974D2: "기남",
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
