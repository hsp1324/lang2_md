from hashlib import sha256
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
TRANSLATIONS = ROOT / "localization/event_dialogue_ko.json"
ENGLISH_RECORDS = ROOT / "script_extract/english_records.json"


class Arca179646819HighPriorityDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.japanese = JP_ROM.read_bytes()
        cls.rows = {
            row["address"]: row
            for entries in json.loads(
                TRANSLATIONS.read_text(encoding="utf-8")
            )["scenarios"].values()
            for row in entries
        }
        cls.english = json.loads(ENGLISH_RECORDS.read_text(encoding="utf-8"))

    def test_objective_errors_use_capacity_safe_japanese_aligned_text(self) -> None:
        expected = {
            # 調子くるう means being thrown off one's usual form. The English
            # reference changes the meaning to agreeing with the old man.
            "0x1925AE": "음… 이 영감과 있으면 왠지 평소 같지 않아…",
            # 行け！ 攻め込め！ -- the old 포기 마 reverses the command.
            "0x1942FE": "가라! 공격하라!",
            # たった一体で都市も破壊すると言われる魔物を！？
            "0x194D4A": "혼자서 도시 하나를 파괴한다는 마물이라고!?",
            # おう、野郎ども！ 化け物退治だ！ -- this addresses allies.
            "0x195FAC": "얘들아! 마물 퇴치다!",
            # この先に住む大魔術師のところだ。
            "0x196D6E": "이 앞의 대마술사를 만나러 가.",
            # 足止め means delaying/holding somebody up, not blocking feet.
            "0x19BFD6": (
                "서둘러 칼자스 성으로 돌아가자. "
                "{000F}장군의 목적은 우리 발을 묶는 거였어."
            ),
            # The same source line has an alternate physical record.
            "0x19C03A": (
                "칼자스로 서둘러야 해. "
                "{000F}장군의 목적은 우리 발을 묶는 거였어."
            ),
        }
        for address, text in expected.items():
            with self.subTest(address=address):
                self.assertEqual(self.rows[address]["text"], text)
                self.assert_page_fits_source_with_original_terminator(
                    address, text
                )

    def test_english_semantic_references_support_the_five_corrections(self) -> None:
        expected_fragments = {
            2896: "Commence the attack!",
            2941: "single-handedly destroy an\nentire city",
            2989: "Hey, fools! Help us get rid of\nthese monsters!",
            3067: "heading to the\ngreat wizard's domain",
            357: "purpose was to impede us",
            358: "purpose was to impede us",
        }
        for record, fragment in expected_fragments.items():
            with self.subTest(record=record):
                self.assertEqual(self.english[record]["index"], record)
                self.assertIn(fragment, self.english[record]["text"])

    def test_scenario8_prefers_japanese_over_the_divergent_english_line(self) -> None:
        self.assertEqual(
            self.english[2805]["text"],
            "Yeah, the old guy might\nbe right.",
        )
        address = "0x1925AE"
        self.assertNotEqual(
            self.rows[address]["text"],
            "음… 이 영감 말이 맞을지도 모르겠네…",
        )
        start = int(address, 16)
        capacity, _, _ = builder.event_page_layout(self.japanese, start)
        source = self.japanese[start : start + (capacity + 1) * 2]
        self.assertEqual(
            sha256(source).hexdigest(),
            "a9077267055ff949b042eace1d3bedc56b2303aa1b4f400c081c3fbbb32aff69",
        )

    def test_two_english_only_suggestions_do_not_replace_japanese_meaning(self) -> None:
        # These English records materially differ from the Japanese ROM. Direct
        # Japanese-page review found 船足が速いので逃げられません and
        # そう死に急ぐ事もあるまい respectively, so the English-only
        # proposals would introduce new mistranslations.
        expected = {
            "0x1A7E02": "적 요격대입니다! 저쪽 배가 빨라 달아날 수 없습니다!",
            "0x1A8E82": "죽음을 서두를 것 없다…",
        }
        rejected = {
            "0x1A7E02": "적선이 접근합니다! 우리 배에 올라타려는 것 같습니다!",
            "0x1A8E82": "이렇게 죽을 순 없다…",
        }
        source_hashes = {
            "0x1A7E02": "13b47e0dfb3a9f4844a034be04a234e8e34ffbab42b975a742d1108664c456f3",
            "0x1A8E82": "4891b54caa0fb1dc275fa121f3a67fdf4f352803485e4ca602609d0445f0dccf",
        }
        self.assertIn("trying to board us", self.english[1081]["text"])
        self.assertIn("can't be killed like", self.english[1144]["text"])
        for address, text in expected.items():
            with self.subTest(address=address):
                self.assertEqual(self.rows[address]["text"], text)
                self.assertNotEqual(self.rows[address]["text"], rejected[address])
                self.assert_page_fits_source_with_original_terminator(
                    address, text
                )
                start = int(address, 16)
                capacity, _, _ = builder.event_page_layout(self.japanese, start)
                source = self.japanese[start : start + (capacity + 1) * 2]
                self.assertEqual(sha256(source).hexdigest(), source_hashes[address])

    def test_independent_japanese_audit_corrections_fit_original_pages(self) -> None:
        expected = {
            "0x18EBAE": "{0008}은 내 검술 스승이야",
            "0x192986": "맡기십시오",
            "0x196DE4": "모르긴 뭘 몰라. 난 {000A}님의 제자 {0009}다.",
            "0x196E6E": (
                "솔직히 말하지. 제국의 암흑검 부활을 막으려면 "
                "그 대마술사의 힘이 필요해."
            ),
            "0x196F1E": "좋아, 내게 맡겨. 너희가 마음에 들었다!",
            "0x19B2A6": (
                "비행 부대는 괜찮아. {0005}도 참, "
                "거짓말을 가르치면 안 되지!"
            ),
            "0x19BE5E": (
                "레아드, 기사단을 이끌고 그 성을 찾아라! "
                "난 엘리자에게 알린 뒤 곧 합류하겠다."
            ),
            "0x1A6A40": (
                "{000D}님도 지금은 참으라 하셨다. "
                "{000D}님은 사욕을 위해 힘을 쓰실 분이 아니다!"
            ),
            "0x1B1632": "여긴… 못 지나간다…",
            "0x1B1652": "크윽…",
            "0x1B1872": "건강하십시오… 제국을 부탁드립니다.",
            "0x1B3726": (
                "{0010} 때문에 스승과 헤어져서까지 목적을 "
                "이루어야 했다니, 참 슬픈 운명이군요…"
            ),
        }
        for address, text in expected.items():
            with self.subTest(address=address):
                self.assertEqual(self.rows[address]["text"], text)
                self.assert_page_fits_source_with_original_terminator(
                    address, text
                )

    def test_divergent_english_does_not_override_japanese_audit(self) -> None:
        expected_english_fragments = {
            3072: "meet this magician",
            3074: "leave it to me",
            301: "playing\ntactician",
            1009: "currently serving",
        }
        for record, fragment in expected_english_fragments.items():
            with self.subTest(record=record):
                self.assertIn(fragment, self.english[record]["text"])
        self.assertNotIn("만나야", self.rows["0x196E6E"]["text"])
        self.assertNotIn("안내", self.rows["0x196F1E"]["text"])
        self.assertNotIn("책사", self.rows["0x19B2A6"]["text"])
        self.assertNotIn("배신", self.rows["0x1A6A40"]["text"])

    def assert_page_fits_source_with_original_terminator(
        self, address: str, text: str
    ) -> None:
        start = int(address, 16)
        capacity, terminator, original_controls = builder.event_page_layout(
            self.japanese, start
        )
        translated_controls = [
            (0xFFF7, int(match.group(1), 16))
            for match in builder.EVENT_NAME_CONTROL_RE.finditer(text)
        ]
        encoded_words = len(text)
        for match in builder.EVENT_NAME_CONTROL_RE.finditer(text):
            encoded_words -= len(match.group(0))
            encoded_words += 2
        self.assertLessEqual(encoded_words, capacity)
        self.assertEqual(translated_controls, original_controls)
        self.assertIn(terminator, (0xFFFD, 0xFFFF))

    def assert_page_fits_source(self, address: str, text: str) -> None:
        start = int(address, 16)
        capacity, terminator, original_controls = builder.event_page_layout(
            self.japanese, start
        )
        translated_controls = [
            (0xFFF7, int(match.group(1), 16))
            for match in builder.EVENT_NAME_CONTROL_RE.finditer(text)
        ]
        encoded_words = len(text)
        for match in builder.EVENT_NAME_CONTROL_RE.finditer(text):
            encoded_words -= len(match.group(0))
            encoded_words += 2
        self.assertLessEqual(encoded_words, capacity)
        self.assertEqual(translated_controls, original_controls)
        self.assertEqual(terminator, 0xFFFF)


if __name__ == "__main__":
    unittest.main()
