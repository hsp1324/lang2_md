import json
from pathlib import Path
import re
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
LOCALIZATION = ROOT / "localization"
JAPANESE_OR_REPLACEMENT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\ufffd]")
OUTPUT_FIELDS = {
    "credits_ko.json": ("target_korean", 61),
    "ending_dialogue_ko.json": ("text", 23),
    "epilogue_dialogue_ko.json": ("text", 90),
    "event_dialogue_ko.json": ("text", 3565),
    "global_strings.json": ("target_korean", 312),
    "shared_word_resources.json": ("target_korean", 366),
    "ui_patch_surfaces.json": ("target_korean", 94),
}
DEPRECATED_OUTPUT_TERMS = (
    "레이가드",
    "흑룡마도단",
    "랄 강",
    "라이텔",
    "다크 로드",
    "홀리 로드",
    "화룡군",
    "화룡병단",
    "빙룡수병단",
    "염룡군단",
    "빙룡군단",
    "빙룡 해군",
    "졸름",
    "다크 프린세스",
    "발티아",
)


def collect_strings(value, path):
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        return [
            row
            for index, child in enumerate(value)
            for row in collect_strings(child, f"{path}[{index}]")
        ]
    return []


def collect_field_values(value, field, path=""):
    rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key == field:
                rows.extend(collect_strings(child, child_path))
            else:
                rows.extend(collect_field_values(child, field, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(collect_field_values(child, field, f"{path}[{index}]"))
    return rows


class TranslationTargetResidueTests(unittest.TestCase):
    def test_output_targets_have_no_japanese_or_replacement_characters(self):
        for filename, (field, expected_count) in OUTPUT_FIELDS.items():
            with self.subTest(filename=filename):
                data = json.loads((LOCALIZATION / filename).read_text(encoding="utf-8"))
                rows = collect_field_values(data, field)
                self.assertEqual(len(rows), expected_count)
                residue = [
                    f"{path}: {text!r}"
                    for path, text in rows
                    if JAPANESE_OR_REPLACEMENT.search(text)
                ]
                self.assertEqual(residue, [])

    def test_output_targets_use_standardized_faction_names(self):
        residue = []
        for filename, (field, _) in OUTPUT_FIELDS.items():
            data = json.loads((LOCALIZATION / filename).read_text(encoding="utf-8"))
            for path, text in collect_field_values(data, field):
                for term in DEPRECATED_OUTPUT_TERMS:
                    if term in text:
                        residue.append(f"{filename}:{path}: {term}")
        self.assertEqual(residue, [])

    def test_scenario_place_name_uses_production_build_source(self):
        scenario_texts = builder.load_scenario_texts()
        self.assertIn("랄강의 수호자", scenario_texts[9])
        self.assertIn("마법사를 찾아 랄강으로", scenario_texts[9])
        self.assertIn("다크로드라는 마법 도구가", scenario_texts[9])
        self.assertIn("다크로드만 손에 넣으면\n제국의 야망을 막을 수 있었다.", scenario_texts[9])
        self.assertNotIn("마법 물건 다크로드", scenario_texts[9])
        self.assertIn("레스터의 안내를 받은", scenario_texts[10])
        self.assertIn("그때를 노려 몰래 함정을 파 두었다.", scenario_texts[10])
        self.assertNotIn("그때를 노리고 함정을 파 두었다.", scenario_texts[10])
        self.assertNotIn("랄 강", scenario_texts[9])
        self.assertNotIn("랄 강", scenario_texts[10])

    def test_production_scenario_terms_are_canonical(self):
        scenario_texts = builder.load_scenario_texts()
        joined = "\n".join(scenario_texts)
        for term in DEPRECATED_OUTPUT_TERMS:
            self.assertNotIn(term, joined)
        self.assertIn("성지 레이텔", scenario_texts[11])
        self.assertIn("다크로드를 지키라는 명", scenario_texts[11])
        self.assertIn("염룡병단과의 결전", scenario_texts[12])
        self.assertIn("빙룡병단", scenario_texts[14])
        self.assertIn("발디아 왕국", scenario_texts[13])
        self.assertIn("발디아 성", scenario_texts[13])
        self.assertIn("홀리로드를 찾아", scenario_texts[22])
        self.assertIn("흑룡마도사단의 함정", scenario_texts[25])

    def test_late_scenario_descriptions_preserve_japanese_source_events(self):
        scenario_texts = builder.load_scenario_texts()
        self.assertIn("제시카의 마법으로 베른하르트는", scenario_texts[22])
        self.assertIn("엘라드에서 청룡기사 레아드와", scenario_texts[23])
        self.assertIn("제국 청룡기사단장\n레온과 에그베르트", scenario_texts[24])
        self.assertIn("수천 년에 걸친 빛과 어둠의", scenario_texts[26])
        self.assertIn("바셀린을", scenario_texts[27])
        self.assertIn("이멜다 장군을\n지원하러 가던 중", scenario_texts[28])
        self.assertIn("그레이트드래곤", scenario_texts[29])
        self.assertIn("각 층에 붙잡혀 세뇌당했고", scenario_texts[30])
        self.assertIn("엘윈의 전술에 달려 있었다", scenario_texts[30])
        self.assertNotIn("제시카의 희생", "\n".join(scenario_texts))
        self.assertNotIn("헤인과 남은 엘윈", "\n".join(scenario_texts))

    def test_early_scenario_descriptions_preserve_japanese_source_events(self):
        scenario_texts = builder.load_scenario_texts()
        self.assertIn("살라스 영주\n로렌의 저택", scenario_texts[1])
        self.assertIn("조름이 이끄는 추격대", scenario_texts[2])
        self.assertIn("수많은 신관전사", scenario_texts[3])
        self.assertIn("새로 동료가 된 소녀 쉐리", scenario_texts[4])
        self.assertIn("늙은 검객 한 사람", scenario_texts[5])
        self.assertIn("사악하고\n불길한 존재", scenario_texts[6])
        self.assertIn("키스마저 자리를 비운 성", scenario_texts[7])
        self.assertIn("레온과 레아드", scenario_texts[8])
        self.assertIn("눈앞에 랄강이\n가로놓여 있었다", scenario_texts[9])
        self.assertNotIn("키스도\n길잡이로 합류", "\n".join(scenario_texts))

    def test_middle_scenario_descriptions_preserve_japanese_source_events(self):
        scenario_texts = builder.load_scenario_texts()
        self.assertIn("그때를 노려 몰래 함정을", scenario_texts[10])
        self.assertIn("교묘히 숨겨진 입구", scenario_texts[11])
        self.assertIn("순간이동으로 사라졌다", scenario_texts[12])
        self.assertIn("같은 목적을 지닌\n청룡기사단", scenario_texts[13])
        self.assertIn("깊은 호수\n밑에서", scenario_texts[13])
        self.assertIn("빙룡병단장 이멜다", scenario_texts[14])
        self.assertIn("롤렉 강을 건너야 했다.", scenario_texts[14])
        self.assertIn("불리한 전황이지만 다른 길을", scenario_texts[14])
        self.assertEqual(set(builder.TRAILING_SCENARIO_DESCRIPTION_GLYPH_TEXT), {"롤", "렉"})
        self.assertNotIn("롤", builder.scenario_description_glyph_text(scenario_texts[14]))
        self.assertNotIn("렉", builder.scenario_description_glyph_text(scenario_texts[14]))
        self.assertIn("대륙 절반을\n정복한 베른하르트", scenario_texts[15])
        self.assertIn("정예부대를 뚫고 온 일행", scenario_texts[16])
        self.assertIn("마물을\n조종하고 있던 사람", scenario_texts[17])
        self.assertIn("배를 탈취할 작전", scenario_texts[18])
        self.assertIn("두 배 사이에 건널판", scenario_texts[19])
        self.assertIn("혼돈의 신이\n봉인되었다", scenario_texts[20])
        self.assertIn("알하자드의\n봉인이 곧 풀린다", scenario_texts[21])
        joined = "\n".join(scenario_texts)
        self.assertNotIn("제시카의 도움으로 엘윈", joined)
        self.assertNotIn("혼돈의 신도 이 저주받은\n땅에 산다", joined)

    def test_scenario_one_description_preserves_japanese_source_events(self):
        scenario_text = builder.load_scenario_texts()[0]
        self.assertIn("며칠 새 주민들과 친해졌다", scenario_text)
        self.assertIn("둘은 오랜 친구처럼 가까워졌다", scenario_text)
        self.assertIn("소꿉친구 리아나", scenario_text)
        self.assertIn("위험에 처한 이는", scenario_text)
        self.assertIn("소꿉친구 리아나였다", scenario_text)
        self.assertIn("검을 들었다", scenario_text)
        self.assertNotIn("적장은 발드였다", scenario_text)
        self.assertNotIn("훗날 대륙의 운명", scenario_text)


if __name__ == "__main__":
    unittest.main()
