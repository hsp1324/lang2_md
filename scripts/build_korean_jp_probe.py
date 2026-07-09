#!/usr/bin/env python3
from __future__ import annotations

from collections import OrderedDict
import ast
import argparse
from pathlib import Path
import unicodedata
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).resolve().parents[1]))
from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS


IN_ROM = Path("roms/original/Langrisser II (Japan).md")
OUT_ROM = Path("roms/builds/Langrisser II (Korean JP Probe).md")
FONT_PATH = Path("tools/fonts/Galmuri9.ttf")
EXPANDED_ROM_SIZE = 0x400000

JP_FONT_BASE = 0x40000
GLYPH_BYTES = 64

CONDITION_POINTER_TABLE = 0x98D7A
CONDITION_GLYPH_LIST_TABLE = 0x986C6
CONDITION_GLYPH_LIST_RELOC_BASE = 0x280000
ITEM_GLYPH_LIST_BASE = 0xA14AC
ITEM_GLYPH_LIST_REFS = (0x21C6E, 0x26924)
ITEM_NAME_POINTER_TABLE = 0xA1902
ITEM_NAME_GLYPH_LIST_RELOC_BASE = 0x282000
ITEM_DESCRIPTION_GLYPH_LIST_BASE = 0xA152E
ITEM_DESCRIPTION_GLYPH_LIST_REF = 0x272BC
ITEM_DESCRIPTION_POINTER_TABLE = 0xA1D7C
ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE = 0x286000
SCENARIO_POINTER_TABLE = 0x9CF7C
SCENARIO_GLYPH_LIST_TABLE = 0x9B2FC
SCENARIO_GLYPH_LIST_RELOC_BASE = 0x270000
SCENARIO_GLYPH_LIST_RELOC_LIMIT = 0x280000
CLASS_BYTE_POINTER_TABLE = 0x05E6D8
CLASS_BYTE_RECORD_COUNT = 156
DEFAULT_HERO_NAME_OFFSET = 0x061AC5
PREP_AND_NAME_GLYPH_REF_RANGE = (0x96FC0, 0x97680)
COMMON_GLYPH_PROTECT_LIMIT = 0x0060

SPACE_GLYPH = 0x0054
CUSTOM_GLYPH_RANGES = (
    (0x7000, 0x72FE),
)
CUSTOM_GLYPH_RESERVED = {0x71FF}
DEFAULT_HERO_NAME_CODES = {
    "엘": 0x80,
    "윈": 0x81,
}
NAME_ENTRY_REUSED_GLYPH_CODES = {
    "엘": 0x0003,
    "윈": 0x002A,
}
OPENING_PROBE_GLYPH_CODES = {
    "후": 0x001D,  # フ
}
OPENING_PROBE_BLANK_GLYPH_CODES = [0x0021]  # ッ
OPENING_SPACE_GLYPH = 0x71FF
CLASS_BYTE_GLYPH_CODES = [
    *range(0x01, 0x20),
    *range(0x21, 0x7F),
    *range(0x80, 0xA1),
    *range(0xE0, 0xFF),
]
CLASS_BYTE_SAFE_GLYPH_CODES = list(range(0xA1, 0xE0))
CLASS_BYTE_SUBSET_LABELS = {
    1: "파이터",
    3: "워록",
    45: "파이터",
    48: "워록",
    98: "파이크",
    99: "팔랑크스",
    100: "솔저",
    101: "검투사",
    102: "아머솔저",
    109: "가드맨",
    113: "시민",
}

DIRECT_STRING_PATCHES = {
    0x96086: "잘가!",
    0x96248: "잘가!",
    0x96390: "그럼잘있어!",
    0x96502: "잠깐기다려",
    0x96788: "고마웠어…",
    0x967EC: "돌아오길기다렸어…",
    0x96868: "평화를위해떠나야해…",
    0x96898: "나도같이가도돼?",
    0x968B6: "뭐?!",
    0x968DA: "네가갈곳으로…",
    0x968F4: "……",
    0x9693E: "그럼걱정돼?",
    0x96988: "위험한눈에띄기싫어!",
    0x96A2A: "함께가게해줘!",
    0x96A64: "그래너혼자는아니야…",
    0x96C48: "조심해…",
    0x18488A: "마을밖에제국군이쳐들어왔어!",
    0x184884: "왜?",
    0x1848C0: "마을밖?\n리아나가있는곳아냐?",
    0x184918: "맞아!\n그곳이야!\n제발도와줘!",
    0x1849A4: "바로가자!",
    0x1849CA: "찾았습니다!",
    0x1849E0: "서둘러.",
    0x184A1C: "진심이야!",
    0x184A52: "일단서두르자!",
    0x184A98: "진군하며싸워라!",
    0x184AF2: "거짓은아닌듯하다.",
    0x184B14: "여기까지…",
    0x184B24: "여기까지!",
    0x184B96: "그래…",
    0x184BAE: "반드시구하겠어.",
    0x184BCE: "멋대로하게두지않아!",
    0x184BFC: "뒤는맡길게!",
    0x184C12: "지금구해줄게!",
    0x184C32: "위험해도망쳐!",
    0x184C5A: "죽기싫으면비켜!",
    0x184C84: "너희나라로돌아가!",
    0x184CA2: "살려줘!",
    0x184CD0: "우리움직임을봤나?",
    0x184D06: "우리임무는살인이아니다.",
    0x184D38: "붙잡아!",
    0x184D46: "예!",
    0x184D5A: "비켜!방해다!",
    0x184D6C: "꺄악!살려줘!",
    0x184D90: "멋대로굴지마!",
    0x184DA6: "으악!",
    0x184DB0: "마을은내가지킨다!",
    0x184DC4: "얕보지마라!",
    0x184DDC: "으악!",
    0x184DFC: "돌아가자!",
    0x184E08: "핫!",
    0x184E24: "적을쓸어버려라!",
    0x184E38: "핫!",
    0x184E70: "뭐라고…",
    0x184E9A: "어디까지버틸까!",
    0x184EDE: "여자하나를노리다니!",
    0x184F12: "발설금지다.",
    0x184F6A: "왜이런짓을하는거야!",
    0x185010: "있는거야!!",
    0x1850A2: "있는거야!!",
    0x185156: "받아가마.",
    0x185174: "가자!",
    0x185192: "적은파이크병이다.",
    0x1851CC: "사람을노린다.",
    0x1851DE: "음.",
    0x1851E8: "님!",
    0x185200: "뒤는내가한다!!",
    0x185240: "물러서지않아!",
    0x185260: "덤벼봐라!",
    0x1852BC: "받아가마.",
    0x1852CA: "나한테무슨일이?",
    0x185350: "졌다.",
    0x18535A: "나를…?",
    0x185386: "제도까지와주겠나…",
    0x1853E8: "괜찮겠나?",
    0x185490: "누구든베겠다.",
    0x1854BE: "그럼따라가죠.",
    0x1854E6: "감사를받아주게.",
    0x185568: "해볼까!",
    0x18557C: "약속이다르잖아!",
    0x1855DA: "이봐!",
    0x1855F2: "빨리따라와!",
    0x185628: "단정중하게.",
    0x18564E: "앞으론조심합니다.",
    0x18566C: "이마을에서멋대로못해!",
    0x18569C: "적이나타났다!",
    0x1856E6: "작전을계속한다!",
    0x18572E: "해라!",
    0x185736: "훗재미있군.",
    0x185760: "와라!",
    0x185790: "따라가겠습니다.",
    0x1857AA: "포로주제에건방진계집애!",
    0x1857E0: "본진으로간다.",
    0x185836: "하하하…",
    0x18584E: "이럴수가…",
    0x1858CA: "해보자고!!",
    0x1858E0: "꺄아!",
    0x185900: "그런짓…",
    0x18593E: "인가!?",
    0x1859CE: "내부대엔필요없다!!",
    0x1859F4: "죄송합니다.",
    0x185A1E: "님!!",
    0x185A34: "실패인가…",
    0x185A58: "음?!",
    0x185A88: "쓰러진듯합니다!",
    0x185AB2: "조금늦었군.",
    0x185AE2: "악행은용서못한다.",
    0x185B0E: "갑시다!",
    0x185B1A: "영주의군이다!",
    0x185B2A: "적원군이다!",
    0x185B4A: "어쩔수없다철수!",
    0x185B64: "핫!",
    0x185B6C: "끝난듯하군.",
    0x185BFA: "아닌가?",
    0x185C16: "정처없는여행중이다…",
    0x185C7E: "괜찮은가…",
    0x185C9C: "그보다그분은?",
    0x185CC0: "그쪽이야말로…",
    0x185CE2: "그냥불러.",
    0x185D04: "불러주세요.",
    0x185D34: "정말멋졌어!",
    0x185D50: "도와줘서고마워.",
    0x185DEC: "저택으로피난합시다.",
    0x185E16: "어서그리로갑시다.",
    0x185E38: "이놈건방지다!",
    0x185E76: "합니다!",
    0x185EC4: "미안하게생각한다.",
    0x185F12: "영광입니다.",
    0x185F2E: "무리는하지마라.",
    0x185F6E: "쓰러뜨려주마…",
    0x186042: "그럴수는없다.",
    0x186054: "알겠습니다!",
    0x186062: "가자!!",
    0x18606E: "질수없다!",
    0x18608A: "죄송합니다…",
    0x1860A6: "죽게하다니…",
    0x186962: "말할수있을까…",
    0x18698E: "님?",
    0x1869FA: "뭔가이상해.",
    0x186B10: "갑자기이상한말을…",
    0x186B6E: "듣고왔어.",
    0x186C38: "아니야.",
    0x186C42: "그렇구나…",
    0x186C7E: "괜찮다면알려줘.",
    0x186DB6: "그저…",
    0x186DC0: "…그저?",
    0x186E16: "여행중이야.",
    0x186E54: "떠올리게했구나…",
    0x186EA6: "이제쉬자.",
    0x186ED2: "…",
    0x186EE6: "어젯밤잘잤어?",
    0x186F0C: "푹잘잤어.",
    0x186FC0: "나혼자는무리겠지…",
    0x187090: "노리고있는게아닐까…",
    0x1870F2: "농담이군.",
    0x18718E: "줄거라생각해.",
    0x187212: "좋아나도따라갈게.",
    0x187272: "나도같이가자.",
    0x18728A: "고마워모두!",
    0x1872D6: "그런듯해.",
    0x187368: "너도조심해…",
    0x18737E: "예아버지.",
    0x1873B0: "긴여행이될테니…",
    0x1873D4: "왜그래?",
    0x1873EA: "누군가숨어있습니다.",
    0x187474: "가자!",
    0x18748A: "어느새?!",
    0x1874D2: "뒷문으로빠져주세요.",
    0x187500: "가자모두!",
    0x187534: "서둘러소녀를잡아!",
    0x18757A: "없습니다.",
    0x187594: "매복인가!",
    0x1875A2: "뭐?!매복!?",
    0x1875C2: "매복이라고!?",
    0x1875D4: "으악적이다!",
    0x1875E6: "꺄악!",
    0x18760C: "추격자를따돌리자!!",
    0x187624: "네,네!",
    0x18764E: "놈들아뒤쫓아라!",
    0x187674: "반드시지킨다!",
    0x187688: "스피드부츠를찾았다!",
    0x1876A4: "가자!",
    0x1876C0: "내가당하다니…",
    0x1876DE: "당했다…",
    0x1876EC: "으악!",
    0x187716: "이제와서뭘해도소용없다!",
    0x187746: "순순히우릴따라와!",
    0x187762: "싫어놔줘!",
    0x187784: "철수한다!",
    0x1877A0: "내힘이미치지못해…",
    0x18781E: "다시오자.",
    0x18782C: "방해못한다!",
    0x18784C: "아직내힘은부족한가!",
    0x18787C: "한다!",
    0x18789C: "용서할수없다!",
    0x1878C4: "수없어…",
    0x1878F4: "물러나세요.",
    0x187914: "뒤를맡긴다…",
    0x187926: "무사할줄마라!",
    0x187944: "님…",
    0x18794E: "못지나간다!",
    0x18795E: "으악!",
    0x187994: "꿈꾸지마!",
    0x1879CE: "도망칠수없다.",
    0x1879E6: "윽!",
    0x1879F2: "대장!",
    0x187A06: "소녀만이라도잡아라!",
    0x187A22: "맡겨!",
    0x187A2E: "부탁한다!",
    0x187A60: "좀위험해!",
    0x187A7E: "잔챙이들은죽어라!",
    0x187ACA: "크흑!",
    0x187AD4: "으악!",
    0x187ADE: "으악!",
    0x187AF6: "그여자는우리가데려간다!",
    0x187B16: "건방진!",
    0x187B38: "그래!",
    0x187B40: "말도안돼…",
    0x187B4C: "소용없다!",
    0x187B68: "따라와!",
    0x187B76: "크흑!",
    0x187B80: "해냈다!",
    0x187B98: "놈들을다쓰러뜨렸군.",
    0x187C0A: "적이올겁니다.",
    0x187C6E: "놈들이올거야.",
    0x187CF2: "놈들이올거야.",
    0x187D34: "유인하자.",
    0x187D52: "서둘러뒷문으로탈출해!",
    0x187D70: "네.",
    0x187E40: "놔두는게낫겠지.",
    0x187ED2: "당하다니…",
    0x187F14: "넘겨줄수없다!",
    0x187F52: "안돼!",
    0x187F9E: "그때까지버텨라!",
    0x188000: "어림없다!!",
    0x188018: "일단저택으로돌아가!",
    0x188058: "저택에서대기해라!",
    0x188074: "네,네!",
    0x1880AC: "내가쓰던검이다.",
    0x1880C2: "그레이트소드를얻었다!",
    0x1880EE: "소중히쓸게요.",
    0x188106: "조심해서가거라.",
    0x18814E: "줘서…",
    0x188196: "자가자!",
    0x1881A6: "네!",
    0x18884E: "괜찮아?",
    0x188886: "나도힘든걸.",
    0x1888D6: "덕분에…",
    0x18894C: "제국도진심이군.",
    0x188A76: "보통일이아닙니다.",
    0x188AC2: "별일없었지.",
    0x188AD4: "그건글쎄!",
    0x188B0C: "데려가겠다!",
    0x188B20: "끈질긴아저씨군.",
    0x188B64: "가는게좋겠지.",
    0x188B90: "바꿀까요?",
    0x188BB2: "따라올래?",
    0x188C00: "방해가될거야.",
    0x188C1E: "그럼나한테맡겨!",
    0x188C46: "날따라와.",
    0x188C76: "야!",
    0x188C9A: "내곁에서떨어지마.",
    0x188CBA: "네.",
    0x188CD6: "갈래?",
    0x188CE2: "네부탁합니다.",
    0x188CF8: "부탁한다!",
    0x188D0C: "힘내겠습니다!",
    0x188D3C: "기다려줄래?",
    0x188D9C: "붙어서…",
    0x188DD8: "가만있을수없어…",
    0x188E26: "무리는하지마.",
    0x188E50: "응!",
    0x188E56: "변경을그만둘까?",
    0x188EE6: "보병은유리하게싸웁니다.",
    0x188F28: "파이크병이있나?",
    0x188FB0: "그런셈입니다.",
    0x188FCE: "박식하시네요.",
    0x82BFE: "마법화살",
    0x82C0E: "블래스트",
    0x82C18: "썬더",
    0x82C22: "파이어볼",
    0x82C34: "메테오",
    0x82C3C: "블리자드",
    0x82C48: "토네이도",
    0x82C54: "턴언데드",
    0x82C66: "어스퀘이크",
    0x82C76: "힐1",
    0x82C80: "힐2",
    0x82C8A: "포스힐1",
    0x82C9C: "포스힐2",
    0x82CAE: "수면",
    0x82CB8: "침묵",
    0x82CC2: "보호",
    0x82CD2: "공격",
    0x82CDC: "존",
    0x82CE4: "순간이동",
    0x82CF0: "환영",
    0x82D00: "저항",
    0x82D0A: "매혹",
    0x82D14: "소환마법",
    0x82D5A: "파이크",
    0x82D62: "팔랑크스",
    0x82D70: "솔저",
    0x82D7C: "검투사",
    0x82D8E: "장갑병",
    0x82DA0: "기병",
    0x82DAC: "중기병",
    0x82DBE: "드라군",
    0x82DCA: "엘프",
    0x82DD2: "발리스타",
    0x82DDC: "몽크",
    0x82DE4: "가드맨",
    0x82DF0: "머맨",
    0x82DFA: "그리폰",
    0x82E06: "엔젤",
    0x971F4: "마나부족",
    0x97202: "수면상태",
    0x97214: "마법봉인",
    0xA16B0: "아이템가득찼음버리세요",
    0xA16D4: "버릴아이템선택",
    0xA16F2: "버리겠습니까예아니오",
    0xA1716: "구입판매더이상소지불가",
}

# These candidate strings were found by scanning, but they are not the visible
# name table used by the JP name-entry screen. Patching them can break the flow
# after name confirmation, so they stay out of the default build until their
# renderer/data ownership is identified.
UNSAFE_DIRECT_NAME_PATCHES = {
    0x97404: "엘윈",
    0x97410: "리아나",
    0x97418: "라나",
    0x97420: "쉐리",
    0x9742A: "헤인",
    0x97432: "스코트",
    0x9743C: "키스",
    0x97444: "아론",
    0x9744E: "레스터",
    0x97458: "제시카",
    0x97462: "가면기사",
    0x9746C: "레온",
    0x97474: "베른하르트",
    0x97482: "발가스",
    0x9748C: "보젤",
    0x97496: "레아드",
    0x974A0: "볼도",
    0x974AA: "졸름",
    0x974B2: "에그베르트",
    0x974BE: "이멜다",
    0x974C8: "모건",
    0x974D2: "기잠",
    0x974DA: "클레이머",
    0x974E6: "세이갈",
    0x974F0: "폴거",
    0x974FC: "일반병",
    0x97504: "지휘관",
    0x9750C: "사제",
    0x97512: "주민",
    0x97518: "해적",
    0x9751E: "자경단",
    0x97526: "로렌",
    0x97530: "아돈",
    0x97538: "삼손",
    0x97542: "바란",
    0x9754A: "제국군지휘관",
    0x97558: "웨어울프",
    0x97566: "그레이트슬라임",
    0x97578: "스큐라",
    0x97582: "아이언골렘",
    0x97594: "리치",
    0x9759C: "리빙아머",
    0x975AE: "뱀파이어로드",
    0x975C0: "고스트",
    0x975CA: "케르베로스",
    0x975D6: "마스터디노",
    0x975E8: "와이번",
    0x975F4: "대드래곤",
    0x97606: "미노타우로스",
    0x97614: "크라켄",
    0x97620: "서큐버스",
    0x9762C: "데몬로드",
    0x9763C: "형님",
    0x97642: "마녀",
    0x97648: "신관",
    0x9764E: "제국병",
    0x97656: "파이어스",
}

DIRECT_ELWIN_NAME_PATCH = {
    0x97404: "엘윈",
}

NAME_ENTRY_DEFAULT_WORD_OFFSET = 0x0A3B0C
NAME_ENTRY_DEFAULT_WORDS = 5

DIRECT_FIXED_STRING_PATCHES = {
    0x9702C: (4, "출격준비"),
    0x97034: (4, "용병고용"),
    0x9703C: (6, "장비착용"),
    0x97048: (4, "상점"),
    0x97050: (5, "지휘관배치"),
    0x9705A: (2, "구입"),
    0x9705E: (2, "판매"),
    0x97062: (3, "취소"),
    0x9706C: (2, "이동"),
    0x97070: (2, "공격"),
    0x97074: (2, "마법"),
    0x97078: (2, "소환"),
    0x9707C: (2, "치료"),
    0x97080: (2, "명령"),
    0xA37A0: (4, "시나리오"),
    0xA37AA: (5, "합계"),
    0xA37B6: (3, "턴"),
    0xA37BE: (20, "이름을정해주세요"),
}

DIRECT_FIXED_ROUTE_TITLE_PATCHES = {
    0xA10E0: (5, "진군루트"),
}

OPENING_TEXT_LIST_PATCHES = OrderedDict(
    [
        (0xA6B20, (0x21, "후후후…")),
        (0xA6B54, (0x2A, "알하자드… 전설의마검… 내가 바라던 무한한 힘…")),
        (0xA6BA8, (0x40, "대륙을... 아니 세계를 모두 내 손에 넣겠다!!")),
        (0xA6BEA, (0x40, "싸움은 아무것도 낳지 않는다. 남는 것은 슬픔뿐...")),
        (0xA6C2A, (0x40, "하늘이... 하늘이 어두워지고 있어... 모든 것이 끝난 걸까...")),
        (0xA6CA6, (0x40, "엘윈, 조심해. 무언가 심상치 않은 기운이 느껴져.")),
        (0xA6CEC, (0x40, "제국군이 마을로 오고 있어! 리아나가 위험해!")),
        (0xA6D5E, (0x40, "알겠어. 지금 바로 가자. 더 늦기 전에 막아야 해.")),
        (0xA6DB8, (0x40, "리아나를 구하고, 이 싸움의 이유를 알아내겠어.")),
        (0xA6DFE, (0x40, "검을 들어라. 운명은 이미 움직이기 시작했다.")),
        (0xA6E80, (0x40, "누구도 피할 수 없는 전란의 그림자가 대륙을 덮는다.")),
        (0xA6F02, (0x40, "그리고 성검 랑그릿사의 전설이 다시 깨어난다.")),
    ]
)

SCENARIO0_TITLE = "시나리오 1"
SCENARIO0_SUBTITLE = "서장"
SCENARIO0_BODY = (
    "엘윈은 살라스 마을에서 쉬고 있었다. "
    "그때 헤인이 달려와 리아나의 위기를 알렸다. "
    "엘윈은 그녀를 구하고 검을 들었다."
)
SCENARIO0_CONDITIONS = "승리조건\n-볼도 격파\n패배조건\n-주인공 사망\n-볼도 우하단 도주"

SCENARIO_TEXT_OVERRIDES = {
    0: f"{SCENARIO0_TITLE}\n{SCENARIO0_SUBTITLE}\n{SCENARIO0_BODY}\n{SCENARIO0_CONDITIONS}",
    10: (
        "시나리오 11\n"
        "불길 속에서\n"
        "랄 강의 수호자는 엘윈 일행을 오래 산 마법사 제시카에게 안내했다. "
        "그녀라면 다크 로드의 행방을 알지도 모른다. "
        "하지만 제국과 에그베르트도 그곳을 노리고 있었다."
    ),
    25: (
        "시나리오 26\n"
        "흑룡마도단의 함정\n"
        "레온을 물리친 엘윈 일행은 벨제리아 성의 지하 신전으로 향했다. "
        "넓은 홀에 이르자 에그베르트가 기다리고 있었다. "
        "사방의 적과 강한 마법이 일행을 덮쳤다."
    ),
}

CONDITION_SCREENS = [
    ["승리조건", "-볼도 격파", "", "패배조건", "-주인공 사망", "-볼도 우하단 도주"],
    ["승리조건", "-리아나 북쪽 도착", "-적 전멸", "패배조건", "-리아나 사망", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-리아나 사망", "-주인공 사망"],
    ["승리조건", "-모건 격파", "", "패배조건", "-신관 전멸", "-리아나/주인공 사망"],
    ["승리조건", "-2턴 안에 적 전멸", "-주인공 목표 이동", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-목표 적 격파", "-맵 위쪽 도착", "패배조건", "-시민 전멸", "-주인공 사망"],
    ["승리조건", "-기잠 격파", "", "패배조건", "-조비리안 전멸", "-주인공 사망"],
    ["승리조건", "-3턴 안에 클레이머 격파", "", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-레아드 격파", "", "패배조건", "-NPC 전멸", "-주인공 사망"],
    ["승리조건", "-레스터 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망", "-제시카 사망"],
    ["승리조건", "-적 전멸", "-다크로드 획득", "패배조건", "-주인공 사망"],
    ["승리조건", "-발가스 장군 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-랑그릿사 도달", "-레온 격파", "패배조건", "-레온 도달", "-주인공 사망"],
    ["승리조건", "-이멜다 장군 격파", "-주인공 아래 이동", "패배조건", "-주인공 사망"],
    ["승리조건", "-레온 격파", "-성문으로 이동", "패배조건", "-주인공 사망"],
    ["승리조건", "-베른하르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-레드드래곤 격파", "-프린세스 격파", "패배조건", "-주인공 사망", "-주민 전멸"],
    ["승리조건", "-3턴 안에 이멜다 격파", "", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망", "-제시카 사망"],
    ["승리조건", "-소드마스터 도달", "-적 전멸", "패배조건", "-롯시 납치", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-에그베르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-베른하르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-마녀 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
]

ITEM_NAME_PATCHES = [
    "단검",
    "워해머",
    "그레이트소드",
    "완드",
    "플레임랜스",
    "데빌액스",
    "D슬레이어",
    "랑그릿사",
    "랑그릿사",
    "메사이얀소드",
    "철아령",
    "홀리로드",
    "다크로드",
    "알하자드",
    "롱보우",
    "아발레스트",
    "소형방패",
    "대형방패",
    "체인메일",
    "플레이트아머",
    "어설트슈츠",
    "로브",
    "드래곤스케일",
    "미라쥬로브",
    "오딘방패",
    "룬스톤",
    "크로스",
    "목걸이",
    "오브",
    "스피드부츠",
    "크라운",
    "아우로라",
    "천사날개",
    "카벙클",
    "그레이프닐",
    "갸라르혼",
    "아뮬렛",
    "홀리로드",
]

ITEM_DESCRIPTION_PATCHES = [
    "호신용 단검\nAT+1",
    "묵직한 워해머\nAT+2",
    "그레이트소드\nAT+4",
    "마력을 높이는 완드\n사거리+2 마법+1",
    "마법의 창\nAT+6",
    "저주받은 대형도끼\nAT+8 DF-3",
    "D슬레이어\nAT+7",
    "루시리스의 성검\nAT+4 DF+1",
    "빛의 성검\nAT+9 DF+2",
    "전설의 검\nAT-4 DF-3",
    "몸을 단련하는 추\nAT+1 MV-1",
    "랑그릿사를 깨우는\n성스러운 로드",
    "알하자드를 깨우는\n어둠의 로드",
    "나무로 만든 강한 활\nAT-2 MV-2\n사거리1-3",
    "강력한 쇠뇌\nAT-4 MV-2\n사거리1-6",
    "소형 방패\nDF+1",
    "대형 방패\nDF+2",
    "고리로 엮은 갑옷\nDF+3",
    "판금 갑옷\nDF+4",
    "인형 같은 철 갑옷\nAT+10 DF+10",
    "낡은 옷\nDF+1 마법저항+10",
    "용비늘 갑옷\nDF+4",
    "미라쥬로브\nDF+2 마법저항+20",
    "오딘방패\nDF+3 D보정+1",
    "불가사의한 룬스톤\n레벨10",
    "신의 가호를 받은 십자가\nD보정+2",
    "목걸이\nD보정+3",
    "마력을 봉한 수정\nMP소모2배 마법+3",
    "발이 빨라지는 부츠\nMV+2",
    "아름다운 왕관\n지휘범위+3 A+2",
    "아우로라\nAT+2",
    "성천사의 날개\n마법저항+10",
    "카벙클\n마법대미지+2",
    "네 가지 보석\n소환부대+1",
    "아뮬렛\nA보정+2 D보정+2",
    "루시리스의 부적\n마법저항+15",
    "성스러운 로드\n마법능력 상승",
]


def be16(data: bytes | bytearray, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def be32(data: bytes | bytearray, offset: int) -> int:
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )


def word_swapped_pointer(data: bytes | bytearray, offset: int) -> int:
    return (be16(data, offset + 2) << 16) | be16(data, offset)


def put16(data: bytearray, offset: int, value: int) -> None:
    data[offset] = (value >> 8) & 0xFF
    data[offset + 1] = value & 0xFF


def put32(data: bytearray, offset: int, value: int) -> None:
    data[offset] = (value >> 24) & 0xFF
    data[offset + 1] = (value >> 16) & 0xFF
    data[offset + 2] = (value >> 8) & 0xFF
    data[offset + 3] = value & 0xFF


def expand_rom(data: bytearray) -> None:
    if len(data) > EXPANDED_ROM_SIZE:
        raise ValueError(f"ROM is larger than expansion target: 0x{len(data):X}")
    data.extend([0xFF] * (EXPANDED_ROM_SIZE - len(data)))
    # Mega Drive header ROM end address. The checksum is updated separately.
    put32(data, 0x1A4, EXPANDED_ROM_SIZE - 1)


def glyph_data_offset(glyph_id: int) -> int:
    return JP_FONT_BASE + glyph_id * GLYPH_BYTES


def install_blank_custom_space(data: bytearray) -> None:
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    opening_space_offset = glyph_data_offset(OPENING_SPACE_GLYPH)
    data[opening_space_offset : opening_space_offset + GLYPH_BYTES] = data[
        blank_offset : blank_offset + GLYPH_BYTES
    ]


def read_word_list(data: bytes | bytearray, offset: int) -> list[int]:
    values: list[int] = []
    pos = offset
    while pos + 1 < len(data):
        value = be16(data, pos)
        if value == 0xFFFF:
            break
        values.append(value)
        pos += 2
    return values


def write_word_list(data: bytearray, offset: int, values: list[int], max_words: int) -> None:
    if len(values) + 1 > max_words:
        raise ValueError(f"word list needs {len(values) + 1} words, only {max_words} available")
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)
    put16(data, offset + len(values) * 2, 0xFFFF)
    for i in range(len(values) + 1, max_words):
        put16(data, offset + i * 2, 0xFFFF)


def write_word_list_exact(data: bytearray, offset: int, values: list[int]) -> int:
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)
    put16(data, offset + len(values) * 2, 0xFFFF)
    return offset + (len(values) + 1) * 2


def write_token_stream(data: bytearray, offset: int, tokens: list[int], max_words: int) -> None:
    if len(tokens) + 1 > max_words:
        raise ValueError(f"token stream needs {len(tokens) + 1} words, only {max_words} available")
    for i, token in enumerate(tokens):
        put16(data, offset + i * 2, token)
    put16(data, offset + len(tokens) * 2, 0xFFFF)
    for i in range(len(tokens) + 1, max_words):
        put16(data, offset + i * 2, 0xFFFF)


def byte_string_capacity(data: bytes | bytearray, offset: int) -> int:
    pos = offset
    while pos < len(data):
        value = data[pos]
        pos += 1
        if value == 0xFF:
            return pos - offset
    raise ValueError(f"unterminated byte string at 0x{offset:06X}")


def write_byte_string(data: bytearray, offset: int, values: list[int], capacity: int) -> None:
    if len(values) + 1 > capacity:
        raise ValueError(f"byte string needs {len(values) + 1} bytes, only {capacity} available")
    data[offset : offset + len(values)] = bytes(values)
    data[offset + len(values)] = 0xFF
    for pos in range(offset + len(values) + 1, offset + capacity):
        data[pos] = 0xFF


def read_pointer_table_until(data: bytes | bytearray, offset: int, low: int, high: int) -> list[int]:
    ptrs: list[int] = []
    pos = offset
    while pos + 3 < len(data):
        ptr = be32(data, pos)
        if not (low <= ptr < high):
            break
        ptrs.append(ptr)
        pos += 4
    return ptrs


def direct_string_capacity_words(data: bytes | bytearray, offset: int) -> int:
    pos = offset
    while pos + 1 < len(data):
        value = be16(data, pos)
        pos += 2
        if value == 0xFFFF:
            return (pos - offset) // 2
    raise ValueError(f"unterminated direct string at 0x{offset:06X}")


def write_direct_string(data: bytearray, offset: int, text: str, glyph_by_char: dict[str, int]) -> None:
    values = []
    for char in text:
        if char == " ":
            continue
        if char == "\n":
            values.append(0xFFFE)
            continue
        if char == "\f":
            values.append(0xFFFD)
            continue
        values.append(glyph_by_char[char])
    capacity = direct_string_capacity_words(data, offset)
    if len(values) + 1 > capacity:
        raise ValueError(
            f"direct string at 0x{offset:06X} needs {len(values) + 1} words, only {capacity}"
        )
    write_word_list(data, offset, values, capacity)


def write_fixed_direct_string(
    data: bytearray,
    offset: int,
    max_words: int,
    text: str,
    glyph_by_char: dict[str, int],
) -> None:
    values = [SPACE_GLYPH if char == " " else glyph_by_char[char] for char in text]
    if len(values) > max_words:
        raise ValueError(
            f"fixed direct string at 0x{offset:06X} needs {len(values)} words, only {max_words}"
        )
    values.extend([SPACE_GLYPH] * (max_words - len(values)))
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)


def capacity_words(data: bytes | bytearray, table_offset: int, index: int, record_count: int) -> int:
    start = be32(data, table_offset + index * 4)
    if index + 1 < record_count:
        end = be32(data, table_offset + (index + 1) * 4)
    elif table_offset == SCENARIO_POINTER_TABLE:
        return direct_string_capacity_words(data, start)
    else:
        end = start + 0x400
    return (end - start) // 2


def glyph_list_capacity_words(data: bytes | bytearray, table_offset: int, index: int, record_count: int) -> int:
    start = be32(data, table_offset + index * 4)
    if index + 1 < record_count:
        end = be32(data, table_offset + (index + 1) * 4)
    elif table_offset == SCENARIO_GLYPH_LIST_TABLE:
        end = SCENARIO_POINTER_TABLE
    elif table_offset == CONDITION_GLYPH_LIST_TABLE:
        end = CONDITION_POINTER_TABLE
    else:
        end = start + 0x100
    return (end - start) // 2


def render_hangul_glyph(char: str, font: ImageFont.FreeTypeFont, blank_template: bytes) -> bytes:
    img = Image.new("L", (16, 16), 255)
    draw = ImageDraw.Draw(img)
    if char == "…":
        for x in (4, 7, 10):
            draw.rectangle((x, 12, x + 1, 13), fill=0)
    else:
        bbox = draw.textbbox((0, 0), char, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (16 - w) // 2 - bbox[0]
        y = (16 - h) // 2 - bbox[1] - 1
        draw.text((x, y), char, font=font, fill=0)

    # Convert one 16x16 bitmap into the Japanese source format consumed by
    # routine 0x2C390: four 8x8 tiles, each row stored as two identical 1bpp
    # planes so the resulting 2bpp pixel is solid dark.
    out = bytearray(blank_template)
    for tile in range(4):
        tx = tile % 2
        ty = tile // 2
        for row in range(8):
            source_row = tile * 8 + row
            high = out[source_row * 2]
            low = out[source_row * 2 + 1]
            for x in range(8):
                px = tx * 8 + x
                py = ty * 8 + row
                dark = img.getpixel((px, py)) < 180
                if dark:
                    high |= 1 << (7 - x)
                    low |= 1 << (7 - x)
            out[source_row * 2] = high
            out[source_row * 2 + 1] = low
    return bytes(out)


def render_halfwidth_hangul_glyph(
    char: str,
    font: ImageFont.FreeTypeFont,
    blank_template: bytes,
) -> bytes:
    img = Image.new("L", (8, 16), 255)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (8 - w) // 2 - bbox[0]
    y = (16 - h) // 2 - bbox[1] - 1
    draw.text((x, y), char, font=font, fill=0)

    out = bytearray(blank_template)
    # Half-width JP UI strings consume the left 8x16 column from the same
    # 16x16 source glyph format. Keep the right column blank.
    for tile, y_base in ((0, 0), (2, 8)):
        for row in range(8):
            source_row = tile * 8 + row
            high = out[source_row * 2]
            low = out[source_row * 2 + 1]
            for x_pos in range(8):
                dark = img.getpixel((x_pos, y_base + row)) < 180
                if dark:
                    high |= 1 << (7 - x_pos)
                    low |= 1 << (7 - x_pos)
            out[source_row * 2] = high
            out[source_row * 2 + 1] = low
    return bytes(out)


def collect_chars(*texts: str) -> list[str]:
    chars: OrderedDict[str, None] = OrderedDict()
    for text in texts:
        for char in text:
            if char in {"\n", " "}:
                continue
            if unicodedata.category(char).startswith("C"):
                continue
            chars[char] = None
    return list(chars)


def install_custom_glyphs(data: bytearray, chars: list[str]) -> dict[str, int]:
    glyph_ids = [
        glyph_id
        for start, end in CUSTOM_GLYPH_RANGES
        for glyph_id in range(start, end + 1)
        if glyph_id not in CUSTOM_GLYPH_RESERVED
    ]
    if len(chars) > len(glyph_ids):
        raise ValueError(f"need {len(chars)} custom glyphs, only {len(glyph_ids)} reserved slots")
    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    mapping: dict[str, int] = {}
    for i, char in enumerate(chars):
        glyph_id = glyph_ids[i]
        mapping[char] = glyph_id
        offset = glyph_data_offset(glyph_id)
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)
    return mapping


def make_record_encoding(
    text: str,
    glyph_by_char: dict[str, int],
    base_glyphs: list[int] | None = None,
) -> tuple[list[int], list[int]]:
    glyphs: list[int] = list(base_glyphs) if base_glyphs is not None else [SPACE_GLYPH]
    if SPACE_GLYPH not in glyphs:
        glyphs.insert(0, SPACE_GLYPH)
    local_by_glyph = {glyph: index for index, glyph in enumerate(glyphs)}
    tokens: list[int] = []
    for char in text:
        if char == "\n":
            tokens.append(0xFFFE)
            continue
        if char == "\f":
            tokens.extend([0xFFF7, 0x0001])
            continue
        glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
        if glyph not in local_by_glyph:
            local_by_glyph[glyph] = len(glyphs)
            glyphs.append(glyph)
        tokens.append(local_by_glyph[glyph])
    return glyphs, tokens


def make_record_encoding_reusing_slots(
    text: str,
    glyph_by_char: dict[str, int],
    base_glyphs: list[int],
) -> tuple[list[int], list[int]]:
    glyphs = list(base_glyphs)
    if not glyphs:
        raise ValueError("cannot reuse slots from an empty glyph list")
    if glyphs[0] != SPACE_GLYPH:
        glyphs[0] = SPACE_GLYPH
    char_to_local: dict[str, int] = {" ": 0}
    next_slot = 1
    tokens: list[int] = []
    for char in text:
        if char == "\n":
            tokens.append(0xFFFE)
            continue
        if char == "\f":
            tokens.extend([0xFFF7, 0x0001])
            continue
        if char == " ":
            tokens.append(0)
            continue
        if char not in char_to_local:
            if next_slot >= len(glyphs):
                raise ValueError(
                    f"record needs more reusable glyph slots than available ({len(glyphs)}): {text!r}"
                )
            char_to_local[char] = next_slot
            glyphs[next_slot] = glyph_by_char[char]
            next_slot += 1
        tokens.append(char_to_local[char])
    return glyphs, tokens


def make_condition_screen(lines: list[str], glyph_by_char: dict[str, int]) -> tuple[list[int], list[int]]:
    if len(lines) > 6:
        raise ValueError("condition screen supports at most 6 rows")
    rows = [[" "] * 18 for _ in range(6)]

    def put(row: int, col: int, text: str) -> None:
        if len(text) > 18:
            raise ValueError(f"condition row too long ({len(text)} > 18): {text!r}")
        for i, char in enumerate(text):
            rows[row][col + i] = char

    for row, line in enumerate(lines):
        put(row, 0, line)

    glyphs: list[int] = [SPACE_GLYPH]
    local_by_glyph = {SPACE_GLYPH: 0}
    tokens: list[int] = []
    for row in rows:
        for char in row:
            glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
            if glyph not in local_by_glyph:
                local_by_glyph[glyph] = len(glyphs)
                glyphs.append(glyph)
            tokens.append(local_by_glyph[glyph])
    return glyphs, tokens


def make_scenario_title_screen(
    text: str,
    glyph_by_char: dict[str, int],
    base_glyphs: list[int] | None = None,
) -> tuple[list[int], list[int]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 2:
        raise ValueError(f"scenario title screen supports at most 2 lines: {text!r}")
    rows = [[" "] * 18 for _ in range(6)]
    start_row = 1
    for row_offset, line in enumerate(lines):
        if len(line) > 18:
            raise ValueError(f"scenario title row too long ({len(line)} > 18): {line!r}")
        col = (18 - len(line)) // 2
        for i, char in enumerate(line):
            rows[start_row + row_offset][col + i] = char

    glyphs: list[int] = list(base_glyphs) if base_glyphs is not None else [SPACE_GLYPH]
    if SPACE_GLYPH not in glyphs:
        glyphs.insert(0, SPACE_GLYPH)
    local_by_glyph = {glyph: index for index, glyph in enumerate(glyphs)}
    tokens: list[int] = []
    for row in rows:
        for char in row:
            glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
            if glyph not in local_by_glyph:
                local_by_glyph[glyph] = len(glyphs)
                glyphs.append(glyph)
            tokens.append(local_by_glyph[glyph])
    return glyphs, tokens


def make_controlled_scenario_record(
    original_tokens: list[int],
    title: str,
    subtitle: str,
    body: str,
    glyph_by_char: dict[str, int],
    base_glyphs: list[int] | None = None,
) -> tuple[list[int], list[int]]:
    glyphs: list[int] = list(base_glyphs) if base_glyphs is not None else [SPACE_GLYPH]
    if not glyphs:
        glyphs = [SPACE_GLYPH]
    glyphs[0] = SPACE_GLYPH
    local_by_char: dict[str, int] = {" ": 0}
    next_slot = 1

    def local_index(char: str) -> int:
        nonlocal next_slot
        if char == " ":
            return 0
        if char not in local_by_char:
            if next_slot >= len(glyphs):
                raise ValueError("controlled scenario has no reusable glyph slots left")
            local_by_char[char] = next_slot
            glyphs[next_slot] = glyph_by_char[char]
            next_slot += 1
        return local_by_char[char]

    tokens = list(original_tokens)
    if tokens[-1] != 0xFFFF:
        raise ValueError("scenario source record must include terminator")

    fff7_params = {
        index + 1
        for index, token in enumerate(tokens[:-1])
        if token == 0xFFF7 and index + 1 < len(tokens)
    }

    def fill_span(start: int, end: int, text: str) -> None:
        width = end - start
        if len(text) > width:
            raise ValueError(f"controlled scenario span too short ({width}): {text!r}")
        padded = text.center(width)
        for pos, char in zip(range(start, end), padded):
            tokens[pos] = local_index(char)

    fill_span(1, 14, title)
    fill_span(15, 26, subtitle)

    body_chars = [char for char in body if char != "\n"]
    body_pos = 0
    for pos, token in enumerate(tokens):
        if pos < 28 or pos in fff7_params or token >= 0xFF00:
            continue
        char = body_chars[body_pos] if body_pos < len(body_chars) else " "
        tokens[pos] = local_index(char)
        body_pos += 1
    if body_pos < len(body_chars):
        raise ValueError("controlled scenario body did not fit original record")
    return glyphs, tokens[:-1]


def make_scenario0_record(
    original_tokens: list[int],
    glyph_by_char: dict[str, int],
    base_glyphs: list[int],
    protected_slots: set[int] | None = None,
) -> tuple[list[int], list[int]]:
    glyphs = list(base_glyphs)
    glyphs[0] = SPACE_GLYPH
    local_by_char: dict[str, int] = {" ": 0}
    next_slot = 1
    protected_slots = set(protected_slots or set()) | {0}


    def local_index(char: str) -> int:
        nonlocal next_slot
        if char == " ":
            return 0
        if char not in local_by_char:
            while next_slot in protected_slots:
                next_slot += 1
            if next_slot >= len(glyphs):
                raise ValueError("scenario 0 has no reusable glyph slots left")
            local_by_char[char] = next_slot
            glyphs[next_slot] = glyph_by_char[char]
            next_slot += 1
        return local_by_char[char]

    tokens = list(original_tokens)
    if tokens[-1] != 0xFFFF:
        raise ValueError("scenario 0 source record must include terminator")

    def fill_span(start: int, end: int, text: str, center: bool = False) -> None:
        width = end - start
        if len(text) > width:
            raise ValueError(f"scenario 0 span too short ({width}): {text!r}")
        padded = text.center(width) if center else text.ljust(width)
        for pos, char in zip(range(start, end), padded):
            tokens[pos] = local_index(char)

    def fill_positions(positions: list[int], text: str) -> None:
        if len(text) > len(positions):
            raise ValueError(f"scenario 0 body too long ({len(text)} > {len(positions)})")
        padded = text.ljust(len(positions))
        for pos, char in zip(positions, padded):
            tokens[pos] = local_index(char)

    fill_span(1, 14, SCENARIO0_TITLE, center=True)
    fill_span(15, 26, SCENARIO0_SUBTITLE, center=True)

    control_param_positions = {
        pos
        for pos, token in enumerate(tokens[:-1])
        if token == 0xFFF7
        for pos in (pos, pos + 1)
    }
    body_positions = [
        pos
        for pos in [*range(28, 165), *range(166, 256), *range(257, 283)]
        if pos not in control_param_positions
    ]
    body_text = SCENARIO0_BODY.replace("\n", " ")
    fill_positions(body_positions, body_text)

    fill_span(285, 290, "승리조건", center=True)
    fill_span(291, 300, "-볼도격파", center=False)
    fill_span(301, 306, "패배조건", center=True)
    fill_span(307, 314, "-엘윈사망", center=False)
    fill_span(315, 330, "-볼도우하단도주", center=False)
    return glyphs, tokens[:-1]


def wrap_korean(text: str, width: int = 18) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def fixed_text_tokens(
    text: str,
    width: int,
    rows: int,
    local_index,
    space_index: int,
) -> list[int]:
    wrapped: list[str] = []
    for paragraph in text.splitlines():
        wrapped.extend(wrap_korean(paragraph, width))
    if len(wrapped) > rows:
        raise ValueError(f"fixed text has too many rows ({len(wrapped)} > {rows}): {text!r}")

    tokens: list[int] = []
    for row in range(rows):
        line = wrapped[row] if row < len(wrapped) else ""
        if len(line) > width:
            raise ValueError(f"fixed text row too long ({len(line)} > {width}): {line!r}")
        tokens.extend(local_index(char) for char in line)
        tokens.extend([space_index] * (width - len(line)))
    return tokens


def load_scenario_texts() -> list[str]:
    src = Path("build_korean_complete_wip.py").read_text()
    module = ast.parse(src)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SCENARIO_DESCRIPTIONS":
                descriptions = ast.literal_eval(node.value)
                if len(descriptions) != 31:
                    raise ValueError(f"expected 31 scenario descriptions, got {len(descriptions)}")
                scenario_texts = []
                for index, description in enumerate(descriptions):
                    lines = [line.strip() for line in description.splitlines() if line.strip()]
                    if len(lines) < 2:
                        raise ValueError(f"scenario {index + 1} has no title line")
                    if index in SCENARIO_TEXT_OVERRIDES:
                        scenario_texts.append(SCENARIO_TEXT_OVERRIDES[index])
                        continue
                    scenario_texts.append("\n".join(lines))
                return scenario_texts
    raise ValueError("SCENARIO_DESCRIPTIONS not found")


def patch_condition(
    data: bytearray,
    index: int,
    lines: list[str],
    glyph_by_char: dict[str, int],
    glyph_cursor: int,
) -> int:
    glyphs, tokens = make_condition_screen(lines, glyph_by_char)
    token_ptr = be32(data, CONDITION_POINTER_TABLE + index * 4)
    put32(data, CONDITION_GLYPH_LIST_TABLE + index * 4, glyph_cursor)
    glyph_cursor = write_word_list_exact(data, glyph_cursor, glyphs)
    if glyph_cursor & 1:
        glyph_cursor += 1
    write_token_stream(
        data,
        token_ptr,
        tokens,
        capacity_words(data, CONDITION_POINTER_TABLE, index, 32),
    )
    return glyph_cursor


def patch_conditions(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    if len(CONDITION_SCREENS) != 32:
        raise ValueError(f"expected 32 condition screens, got {len(CONDITION_SCREENS)}")
    glyph_cursor = CONDITION_GLYPH_LIST_RELOC_BASE
    for index, lines in enumerate(CONDITION_SCREENS):
        glyph_cursor = patch_condition(data, index, lines, glyph_by_char, glyph_cursor)
    if glyph_cursor >= ITEM_NAME_GLYPH_LIST_RELOC_BASE:
        raise ValueError(f"relocated condition glyph lists overflow: 0x{glyph_cursor:06X}")


def normalize_scenario_text(text: str) -> str:
    normalized_pages: list[str] = []
    for page in text.split("\f"):
        normalized_lines: list[str] = []
        for line in page.splitlines():
            if not line.strip():
                normalized_lines.append("")
                continue
            normalized_lines.extend(wrapped.center(18) for wrapped in wrap_korean(line, 18))
        normalized_pages.append("\n".join(normalized_lines))
    return "\f".join(normalized_pages)


def patch_scenario(
    data: bytearray,
    index: int,
    text: str,
    glyph_by_char: dict[str, int],
    glyph_cursor: int | None = None,
) -> int | None:
    glyph_ptr = be32(data, SCENARIO_GLYPH_LIST_TABLE + index * 4)
    token_ptr = be32(data, SCENARIO_POINTER_TABLE + index * 4)
    original_glyphs = read_word_list(data, glyph_ptr)
    original_glyph_to_local = {glyph: slot for slot, glyph in enumerate(original_glyphs)}
    protected_slots: set[int] = {
        slot for slot, glyph in enumerate(original_glyphs) if glyph < COMMON_GLYPH_PROTECT_LIMIT
    }
    for pos in range(*PREP_AND_NAME_GLYPH_REF_RANGE, 2):
        value = be16(data, pos)
        slot = original_glyph_to_local.get(value)
        if slot is not None:
            protected_slots.add(slot)
    if index in SCENARIO_TEXT_OVERRIDES:
        original_tokens = []
        pos = token_ptr
        while True:
            token = be16(data, pos)
            original_tokens.append(token)
            pos += 2
            if token == 0xFFFF:
                break
        if index == 0:
            glyphs, tokens = make_scenario0_record(
                original_tokens, glyph_by_char, original_glyphs, protected_slots
            )
        else:
            scenario_text = normalize_scenario_text(text)
            glyphs, tokens = make_record_encoding_reusing_slots(
                scenario_text, glyph_by_char, original_glyphs
            )
    else:
        scenario_text = "\n".join(line for line in text.splitlines() if line.strip())
        glyphs, tokens = make_record_encoding_reusing_slots(
            normalize_scenario_text(scenario_text), glyph_by_char, original_glyphs
        )
    if glyph_cursor is None:
        write_word_list(
            data,
            glyph_ptr,
            glyphs,
            glyph_list_capacity_words(data, SCENARIO_GLYPH_LIST_TABLE, index, 31),
        )
    else:
        put32(data, SCENARIO_GLYPH_LIST_TABLE + index * 4, glyph_cursor)
        glyph_cursor = write_word_list_exact(data, glyph_cursor, glyphs)
        if glyph_cursor & 1:
            glyph_cursor += 1
    write_token_stream(
        data,
        token_ptr,
        tokens,
        capacity_words(data, SCENARIO_POINTER_TABLE, index, 31),
    )
    return glyph_cursor


def patch_scenarios(data: bytearray, descriptions: list[str], glyph_by_char: dict[str, int]) -> None:
    glyph_cursor = SCENARIO_GLYPH_LIST_RELOC_BASE
    for index, text in enumerate(descriptions):
        glyph_cursor = patch_scenario(data, index, text, glyph_by_char, glyph_cursor)
    if glyph_cursor is not None and glyph_cursor >= SCENARIO_GLYPH_LIST_RELOC_LIMIT:
        raise ValueError(f"relocated scenario glyph lists overflow: 0x{glyph_cursor:06X}")


def patch_direct_strings(
    data: bytearray,
    glyph_by_char: dict[str, int],
    direct_patches: dict[int, str],
    fixed_patches: dict[int, tuple[int, str]],
) -> None:
    for offset, text in direct_patches.items():
        write_direct_string(data, offset, text, glyph_by_char)
    for offset, (max_words, text) in fixed_patches.items():
        write_fixed_direct_string(data, offset, max_words, text, glyph_by_char)


def patch_route_title(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    for offset, (max_words, text) in DIRECT_FIXED_ROUTE_TITLE_PATCHES.items():
        values = [glyph_by_char[char] for char in text]
        if len(values) > max_words:
            raise ValueError(f"route title needs {len(values)} glyphs, only {max_words}: {text!r}")
        values.extend([OPENING_SPACE_GLYPH] * (max_words - len(values)))
        for i, value in enumerate(values):
            put16(data, offset + i * 2, value)


def patch_item_names(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    ptrs = read_pointer_table_until(data, ITEM_NAME_POINTER_TABLE, 0xA1990, 0xA1B90)
    if len(ptrs) != len(ITEM_NAME_PATCHES):
        raise ValueError(f"expected {len(ITEM_NAME_PATCHES)} item name pointers, got {len(ptrs)}")

    item_glyphs = read_word_list(data, ITEM_GLYPH_LIST_BASE)
    local_by_glyph = {glyph: i for i, glyph in enumerate(item_glyphs)}

    def local_index(char: str) -> int:
        glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
        if glyph not in local_by_glyph:
            local_by_glyph[glyph] = len(item_glyphs)
            item_glyphs.append(glyph)
        return local_by_glyph[glyph]

    for ptr, text in zip(ptrs, ITEM_NAME_PATCHES):
        capacity = direct_string_capacity_words(data, ptr)
        tokens = [local_index(char) for char in text if char != " "]
        if len(tokens) + 1 > capacity:
            raise ValueError(
                f"item name at 0x{ptr:06X} needs {len(tokens) + 1} words, only {capacity}: {text!r}"
            )
        write_token_stream(data, ptr, tokens, capacity)

    for ref in ITEM_GLYPH_LIST_REFS:
        put32(data, ref, ITEM_NAME_GLYPH_LIST_RELOC_BASE)
    end = write_word_list_exact(data, ITEM_NAME_GLYPH_LIST_RELOC_BASE, item_glyphs)
    if end >= ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE:
        raise ValueError(f"relocated item glyph list overflow: 0x{end:06X}")


def patch_item_descriptions(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    ptrs = read_pointer_table_until(data, ITEM_DESCRIPTION_POINTER_TABLE, 0xA1E10, 0xA2C00)
    if len(ptrs) != len(ITEM_DESCRIPTION_PATCHES):
        raise ValueError(
            f"expected {len(ITEM_DESCRIPTION_PATCHES)} item description pointers, got {len(ptrs)}"
        )

    desc_glyphs = read_word_list(data, ITEM_DESCRIPTION_GLYPH_LIST_BASE)
    local_by_glyph = {glyph: i for i, glyph in enumerate(desc_glyphs)}
    if SPACE_GLYPH not in local_by_glyph:
        raise ValueError("item description glyph list has no known space glyph")
    space_index = local_by_glyph[SPACE_GLYPH]

    def local_index(char: str) -> int:
        glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
        if glyph not in local_by_glyph:
            local_by_glyph[glyph] = len(desc_glyphs)
            desc_glyphs.append(glyph)
        return local_by_glyph[glyph]

    for i, (ptr, text) in enumerate(zip(ptrs, ITEM_DESCRIPTION_PATCHES)):
        if i + 1 < len(ptrs):
            capacity = (ptrs[i + 1] - ptr) // 2
        else:
            capacity = direct_string_capacity_words(data, ptr)
        if capacity < 46:
            raise ValueError(f"item description at 0x{ptr:06X} is too small: {capacity} words")
        tokens = fixed_text_tokens(text, 15, 3, local_index, space_index)
        if len(tokens) + 1 > capacity:
            raise ValueError(
                f"item description at 0x{ptr:06X} needs {len(tokens) + 1} words, only {capacity}: {text!r}"
            )
        write_token_stream(data, ptr, tokens, capacity)

    put32(data, ITEM_DESCRIPTION_GLYPH_LIST_REF, ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE)
    end = write_word_list_exact(data, ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE, desc_glyphs)
    if end >= EXPANDED_ROM_SIZE:
        raise ValueError(f"relocated item description glyph list overflow: 0x{end:06X}")


def patch_class_byte_table(data: bytearray) -> None:
    labels = KOREAN_CLASS_LABELS
    if len(labels) != CLASS_BYTE_RECORD_COUNT:
        raise ValueError(f"expected {CLASS_BYTE_RECORD_COUNT} class labels, got {len(labels)}")

    chars = collect_chars(*labels)
    if len(chars) > len(CLASS_BYTE_GLYPH_CODES):
        raise ValueError(
            f"class byte table needs {len(chars)} glyph codes, only {len(CLASS_BYTE_GLYPH_CODES)} available"
        )

    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    code_by_char = {char: CLASS_BYTE_GLYPH_CODES[i] for i, char in enumerate(chars)}
    for char, code in code_by_char.items():
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)

    for index, text in enumerate(labels):
        ptr = word_swapped_pointer(data, CLASS_BYTE_POINTER_TABLE + index * 4)
        capacity = byte_string_capacity(data, ptr)
        values = [0x20 if char == " " else code_by_char[char] for char in text]
        if len(values) + 1 > capacity:
            raise ValueError(
                f"class byte string {index} at 0x{ptr:06X} needs {len(values) + 1} bytes, "
                f"only {capacity}: {text!r}"
            )
        write_byte_string(data, ptr, values, capacity)


def patch_class_byte_subset(data: bytearray) -> None:
    labels = CLASS_BYTE_SUBSET_LABELS
    chars = collect_chars(*labels.values())
    if len(chars) > len(CLASS_BYTE_SAFE_GLYPH_CODES):
        raise ValueError(
            f"class byte subset needs {len(chars)} glyph codes, "
            f"only {len(CLASS_BYTE_SAFE_GLYPH_CODES)} available"
        )

    half_font = Path("tools/fonts/Galmuri7.ttf")
    font = ImageFont.truetype(str(half_font if half_font.exists() else FONT_PATH), 8)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    code_by_char = {char: CLASS_BYTE_SAFE_GLYPH_CODES[i] for i, char in enumerate(chars)}
    for char, code in code_by_char.items():
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = render_halfwidth_hangul_glyph(
            char, font, blank_template
        )

    for index, text in labels.items():
        ptr = word_swapped_pointer(data, CLASS_BYTE_POINTER_TABLE + index * 4)
        capacity = byte_string_capacity(data, ptr)
        values = [code_by_char[char] for char in text]
        if len(values) + 1 > capacity:
            raise ValueError(
                f"class byte subset {index} at 0x{ptr:06X} needs {len(values) + 1} bytes, "
                f"only {capacity}: {text!r}"
            )
        write_byte_string(data, ptr, values, capacity)


def patch_default_hero_name(data: bytearray) -> None:
    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    for char, code in DEFAULT_HERO_NAME_CODES.items():
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)

    original_capacity = byte_string_capacity(data, DEFAULT_HERO_NAME_OFFSET)
    values = [DEFAULT_HERO_NAME_CODES["엘"], DEFAULT_HERO_NAME_CODES["윈"]]
    write_byte_string(data, DEFAULT_HERO_NAME_OFFSET, values, original_capacity)


def patch_name_entry_default_word_buffer(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    values = [glyph_by_char["엘"], glyph_by_char["윈"]]
    values.extend([SPACE_GLYPH] * (NAME_ENTRY_DEFAULT_WORDS - len(values)))
    for i, value in enumerate(values):
        put16(data, NAME_ENTRY_DEFAULT_WORD_OFFSET + i * 2, value)


def patch_name_entry_reused_glyphs(data: bytearray) -> None:
    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    for char, code in NAME_ENTRY_REUSED_GLYPH_CODES.items():
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)

    values = [
        NAME_ENTRY_REUSED_GLYPH_CODES["엘"],
        NAME_ENTRY_REUSED_GLYPH_CODES["윈"],
        *([SPACE_GLYPH] * (NAME_ENTRY_DEFAULT_WORDS - 2)),
    ]
    for i, value in enumerate(values):
        put16(data, NAME_ENTRY_DEFAULT_WORD_OFFSET + i * 2, value)


def patch_opening_glyph_probe(data: bytearray) -> None:
    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = glyph_data_offset(SPACE_GLYPH)
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    for char, code in OPENING_PROBE_GLYPH_CODES.items():
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)
    for code in OPENING_PROBE_BLANK_GLYPH_CODES:
        offset = glyph_data_offset(code)
        data[offset : offset + GLYPH_BYTES] = blank_template


def patch_opening_text_lists(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    for offset, (capacity, text) in OPENING_TEXT_LIST_PATCHES.items():
        values = [OPENING_SPACE_GLYPH if char == " " else glyph_by_char[char] for char in text]
        if len(values) > capacity:
            raise ValueError(
                f"opening text list at 0x{offset:06X} needs {len(values)} glyphs, only {capacity}: {text!r}"
            )
        values.extend([OPENING_SPACE_GLYPH] * (capacity - len(values)))
        for i, value in enumerate(values):
            put16(data, offset + i * 2, value)
        # Keep the original terminator for records that have one immediately
        # after the counted range. The renderer primarily uses the count, but
        # later maintenance tools can still stop cleanly on FFFF.
        if offset + capacity * 2 + 1 < len(data) and be16(data, offset + capacity * 2) == 0xFFFF:
            put16(data, offset + capacity * 2, 0xFFFF)


def update_md_checksum(data: bytearray) -> int:
    checksum = 0
    for offset in range(0x200, len(data), 2):
        checksum = (checksum + be16(data, offset)) & 0xFFFF
    put16(data, 0x18E, checksum)
    return checksum


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_ROM)
    parser.add_argument(
        "--scenario-count",
        type=int,
        default=31,
        help="number of scenario description records to patch from the start",
    )
    parser.add_argument(
        "--skip-condition",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="skip standalone condition-screen table patching; enabled by default because that table shares prep UI state",
    )
    parser.add_argument("--skip-scenarios", action="store_true")
    parser.add_argument("--skip-direct", action="store_true")
    parser.add_argument(
        "--include-unsafe-direct-names",
        action="store_true",
        help="patch the 0x974xx candidate name table; experimental and can break name confirmation",
    )
    parser.add_argument(
        "--patch-elwin-name-only",
        action="store_true",
        help="experimental: patch only the first 0x974xx Elwin name entry",
    )
    parser.add_argument("--skip-items", action="store_true")
    parser.add_argument(
        "--patch-class-byte-table",
        action="store_true",
        help="patch JP one-byte class/mercenary labels; experimental because shared byte slots collide with unpatched JP UI",
    )
    parser.add_argument(
        "--patch-class-byte-subset",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "experimental: patch early-game one-byte class/mercenary labels. Disabled by "
            "default because the prep class field uses a separate one-byte display path."
        ),
    )
    parser.add_argument(
        "--patch-default-name",
        action="store_true",
        help="experimental: patch the byte-string default hero name; not used by the visible JP name-entry buffer yet",
    )
    parser.add_argument(
        "--patch-name-entry-default",
        action="store_true",
        help="experimental: patch the visible JP name-entry default name word buffer",
    )
    parser.add_argument(
        "--patch-name-entry-reused-glyphs",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "experimental: render Elwin as Korean by reusing existing JP name-entry glyph slots; "
            "disabled by default because those slots are shared with other JP text"
        ),
    )
    parser.add_argument(
        "--patch-opening-glyph-probe",
        action="store_true",
        help="experimental: replace JP opening フ/ッ glyphs to verify the opening font path",
    )
    args = parser.parse_args()

    data = bytearray(IN_ROM.read_bytes())
    expand_rom(data)
    install_blank_custom_space(data)
    scenario_texts = load_scenario_texts()
    if not 0 <= args.scenario_count <= len(scenario_texts):
        raise ValueError(f"--scenario-count must be 0..{len(scenario_texts)}")
    active_condition_chars = "" if args.skip_condition else "\n".join(
        line for screen in CONDITION_SCREENS for line in screen
    )
    active_descriptions = [] if args.skip_scenarios else scenario_texts[: args.scenario_count]
    direct_patches = {} if args.skip_direct else dict(DIRECT_STRING_PATCHES)
    fixed_patches = {} if args.skip_direct else dict(DIRECT_FIXED_STRING_PATCHES)
    route_title_patches = {} if args.skip_direct else dict(DIRECT_FIXED_ROUTE_TITLE_PATCHES)
    if args.include_unsafe_direct_names:
        direct_patches.update(UNSAFE_DIRECT_NAME_PATCHES)
    elif args.patch_elwin_name_only:
        direct_patches.update(DIRECT_ELWIN_NAME_PATCH)
    active_direct_strings = list(direct_patches.values())
    active_fixed_strings = [text for _, text in fixed_patches.values()]
    active_route_title_strings = [text for _, text in route_title_patches.values()]
    active_item_names = [] if args.skip_items else ITEM_NAME_PATCHES
    active_item_descriptions = [] if args.skip_items else ITEM_DESCRIPTION_PATCHES
    active_opening_texts = [text for _, text in OPENING_TEXT_LIST_PATCHES.values()]
    chars = collect_chars(
        active_condition_chars,
        *active_descriptions,
        *active_direct_strings,
        *active_fixed_strings,
        *active_route_title_strings,
        *active_item_names,
        *active_item_descriptions,
        *active_opening_texts,
    )
    glyph_by_char = install_custom_glyphs(data, chars)
    if args.patch_default_name:
        patch_default_hero_name(data)
    if args.patch_name_entry_default:
        patch_name_entry_default_word_buffer(data, glyph_by_char)
    if args.patch_name_entry_reused_glyphs:
        patch_name_entry_reused_glyphs(data)
    if args.patch_opening_glyph_probe:
        patch_opening_glyph_probe(data)
    patch_opening_text_lists(data, glyph_by_char)
    if args.patch_class_byte_table:
        patch_class_byte_table(data)
    elif args.patch_class_byte_subset:
        patch_class_byte_subset(data)
    if not args.skip_condition:
        patch_conditions(data, glyph_by_char)
    if not args.skip_scenarios:
        patch_scenarios(data, scenario_texts[: args.scenario_count], glyph_by_char)
    if not args.skip_direct:
        patch_direct_strings(data, glyph_by_char, direct_patches, fixed_patches)
        patch_route_title(data, glyph_by_char)
    if not args.skip_items:
        patch_item_names(data, glyph_by_char)
        patch_item_descriptions(data, glyph_by_char)
    checksum = update_md_checksum(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    print(f"wrote {args.out}")
    used = sorted(glyph_by_char.values())
    if used:
        print(f"custom glyphs: {len(glyph_by_char)} ({used[0]:04X}-{used[-1]:04X})")
    else:
        print("custom glyphs: 0")
    print(f"checksum: {checksum:04X}")


if __name__ == "__main__":
    main()
