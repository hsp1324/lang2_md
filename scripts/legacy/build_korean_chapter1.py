#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_korean_hybrid_wip as hybrid
import build_korean_machine_jamo as base
import build_korean_wip as opening_wip


SRC = Path("Langrisser II (English).md")
OUT = Path("Langrisser II (Korean Chapter1).md")
FONT_PATH = base.FONT_PATH
FIXED_FONT_PATH = Path("tools/fonts/Galmuri7.ttf") if Path("tools/fonts/Galmuri7.ttf").exists() else FONT_PATH

FIXED_FONT_BASE = 0x6000
FIXED_TILE_SIZE = 0x20

# Prefer high bytes so ordinary ASCII-heavy screens remain intact as much as
# possible. Bytes below 0xc0 are accepted by the dialogue conversion routine.
CODE_POOL = list(range(0x80, 0xC0)) + [
    code for code in range(0x21, 0x7F) if code not in {0x20}
]


def map_fixed_tile(code: int) -> int:
    code &= 0xFF
    specials = {
        0x0E: 0xCD,
        0x21: 0x2C,
        0x2F: 0x3E,
        0x25: 0x3B,
        0x2C: 0xD0,
        0x3A: 0xD1,
        0x3B: 0xD2,
        0x27: 0xD5,
        0x22: 0xD3,
        0x2E: 0xD6,
        0x23: 0xD7,
        0x2A: 0xD8,
        0x5B: 0xD9,
        0x5D: 0xD4,
    }
    if code in specials:
        return specials[code]
    if 0xA9 <= code <= 0xAF:
        return code
    if code >= 0x60:
        code = (code + 0x50) & 0xFF
    if code < 0x20:
        code = (code + 0x60) & 0xFF
    return code


def encode_fixed_tile(pixels: list[list[int]]) -> bytes:
    out = bytearray()
    for y in range(8):
        row = pixels[y]
        for x in range(0, 8, 2):
            out.append(((row[x] & 0x0F) << 4) | (row[x + 1] & 0x0F))
    return bytes(out)


def render_fixed_glyph(text: str, font: ImageFont.FreeTypeFont, bold: bool = False) -> bytes:
    scale = 8
    canvas = Image.new("L", (10 * scale, 10 * scale), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas.width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (canvas.height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)
    bbox = canvas.getbbox()
    if bbox is None:
        return bytes([0x11] * FIXED_TILE_SIZE)
    crop = canvas.crop(bbox)
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
    target_h = 8
    target_w = max(5, min(8, round(crop.width * target_h / crop.height)))
    small = crop.resize((target_w, target_h), resample)
    # The fixed UI font is only 8x8. Use a binary mask so CJK glyphs stay
    # crisp on the game's dark blue text boxes.
    mask = [[small.getpixel((xx, yy)) >= 48 for xx in range(target_w)] for yy in range(target_h)]
    if bold:
        stroke = [row[:] for row in mask]
        for yy, row in enumerate(mask):
            for xx, on in enumerate(row):
                if not on:
                    continue
                if xx + 1 < target_w:
                    stroke[yy][xx + 1] = True
        mask = stroke

    pixels: list[list[int]] = []
    xoff = (8 - target_w) // 2
    for yy in range(8):
        row = [1] * 8
        for xx in range(target_w):
            if mask[yy][xx]:
                row[xoff + xx] = 3
        pixels.append(row)
    return encode_fixed_tile(pixels)


def patch_fixed_font(rom: bytearray, code_map: dict[str, int]) -> None:
    font_size = 8 if FIXED_FONT_PATH.name.startswith("Galmuri") else 8 * 8
    font = ImageFont.truetype(str(FIXED_FONT_PATH), font_size)
    bold = not FIXED_FONT_PATH.name.startswith("Galmuri")
    used_tiles: dict[int, str] = {}
    for ch, code in code_map.items():
        tile = map_fixed_tile(code)
        if tile in used_tiles:
            raise ValueError(f"tile collision: {ch!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
        used_tiles[tile] = ch
        off = FIXED_FONT_BASE + tile * FIXED_TILE_SIZE
        rom[off : off + FIXED_TILE_SIZE] = render_fixed_glyph(ch, font, bold=bold)


def patch_vwf_font(rom: bytearray, code_map: dict[str, int]) -> None:
    font = ImageFont.truetype(str(FONT_PATH), 16 * 8)
    copy_size = base.font_copy_size(rom)
    rom[base.RELOCATED_BITMAP_TABLE : base.RELOCATED_BITMAP_TABLE + copy_size] = rom[
        base.ORIGINAL_BITMAP_TABLE : base.ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[base.BITMAP_BASE_PATCH : base.BITMAP_BASE_PATCH + 4] = base.RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    cursor = base.RELOCATED_BITMAP_TABLE + copy_size
    for ch, code in code_map.items():
        if not (0x20 <= code <= 0x7E):
            continue
        glyph = base.render_glyph(ch, font)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    opening_chars = hybrid.collect_opening_hangul()
    opening_map = hybrid.assign_opening_codes(code_map, opening_chars)
    for ch, code in opening_map.items():
        glyph = opening_wip.render_opening_glyph(ch, font)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    opening_cursor = 0x179C0C
    for name, parts in opening_wip.OPENING_PARTS.items():
        encoded = hybrid.encode_hybrid_opening(parts, opening_map)
        rom[base.OPENING_POINTER_PATCHES[name] : base.OPENING_POINTER_PATCHES[name] + 4] = opening_cursor.to_bytes(
            4, "big"
        )
        rom[opening_cursor : opening_cursor + len(encoded)] = encoded
        opening_cursor += len(encoded)
        if opening_cursor & 1:
            opening_cursor += 1


def collect_chars() -> list[str]:
    counter: Counter[str] = Counter()
    for _, _, text in TEXT_PATCHES:
        counter.update(ch for ch in text if ch != " ")
    for _, _, text in FIXED_TEXT_PATCHES:
        counter.update(ch for ch in text if ch != " ")
    chars = [ch for ch, _ in counter.most_common()]
    if len(chars) > len(CODE_POOL):
        raise ValueError(f"Need {len(chars)} Korean glyphs, only {len(CODE_POOL)} code slots")
    return chars


def encode_text(text: str, code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in text:
        if ch == " ":
            out.append(0x20)
        else:
            out.append(code_map[ch])
    return bytes(out)


def patch_text_at(rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, int], prefix: bytes = b"") -> None:
    encoded = prefix + encode_text(text, code_map)
    if len(encoded) > length:
        raise ValueError(f"patch too long at 0x{offset:x}: {len(encoded)} > {length}: {text}")
    rom[offset : offset + length] = encoded + b" " * (length - len(encoded))


def update_checksum_and_header(rom: bytearray) -> None:
    rom[0x1A0:0x1A4] = (0).to_bytes(4, "big")
    rom[0x1A4:0x1A8] = (len(rom) - 1).to_bytes(4, "big")
    checksum = 0
    for i in range(0x200, len(rom), 2):
        checksum = (checksum + ((rom[i] << 8) | rom[i + 1])) & 0xFFFF
    rom[0x18E:0x190] = checksum.to_bytes(2, "big")


# offset, original byte length, Korean text. These are fixed-width in-place
# patches, so wording is intentionally compact.
TEXT_PATCHES: list[tuple[int, int, str]] = [
    (0x9CFF8, 24, "시나리오 일"),
    (0x9D011, 22, "시작의 날"),
    (0x9D02B, 32, "홀로 여행하던 이는"),
    (0x9D04E, 25, "살라스의 작은"),
    (0x9D067, 28, "마을에서 쉬고 있었다"),
    (0x9D083, 31, "그는 마을 사람들과"),
    (0x9D0A3, 33, "젊은 마법사와도"),
    (0x9D0C6, 32, "곧 친구가 되었다"),
    (0x9D0E7, 16, "어느 조용한 날"),
    (0x9D0F8, 16, "이 여관으로"),
    (0x9D108, 10, "뛰어와"),
    (0x9D113, 18, "다급히 말했다"),
    (0x9D126, 33, "레이가드 제국군이"),
    (0x9D148, 32, "마을을 습격했고"),
    (0x9D169, 31, "소꿉친구인"),
    (0x9D189, 10, "그녀가"),
    (0x9D193, 12, "위험하다고"),
    (0x9D1A0, 23, "알려 주었다"),
    (0x9D1B8, 21, "검을 움켜쥔 그는"),
    (0x9D1CD, 9, "그녀를"),
    (0x9D1D6, 19, "구하러 달려갔다"),
    (0x165004, 24, "그냥 보내지 않겠다"),
    (0x16501E, 11, "절대로"),
    (0x16502F, 5, "크윽"),
    (0x165039, 9, "지휘관"),
    (0x16504D, 24, "들어라 저 여자를 잡아라"),
    (0x165069, 10, "네"),
    (0x165077, 22, "믿고 있겠다"),
    (0x165091, 26, "이런 곳에 숨다니"),
    (0x1650AC, 32, "그걸로 안전할 줄 알았나"),
    (0x1650CE, 17, "어리석군"),
    (0x1650E3, 7, "비켜"),
    (0x1650EC, 13, "죽고 싶나"),
    (0x1650FF, 7, "내가"),
    (0x165108, 23, "이런 자들에게 지다니"),
    (0x165125, 5, "크윽"),
    (0x16512F, 5, "크윽"),
    (0x165139, 12, "하하하"),
    (0x165146, 17, "저 여자는 우리 것이다"),
    (0x16515D, 3, "네놈"),
    (0x165162, 22, "건방진 녀석"),
    (0x16517B, 16, "우릴 못 이긴다"),
    (0x16518C, 3, "절대"),
    (0x165193, 15, "말도 안 돼"),
    (0x1651A5, 12, "덤비지 마라"),
    (0x1651B2, 7, "그만둬"),
    (0x1651BD, 16, "내가 해 보지"),
    (0x1651D1, 11, "으아악"),
    (0x1651E1, 5, "좋아"),
    (0x1651EB, 18, "이걸로 끝인가"),
    (0x1651FE, 19, "모두 쓰러뜨렸군"),
    (0x165217, 23, "어서 에스톨로 가자"),
    (0x165230, 32, "제국병이 다시 올 거야"),
    (0x165252, 16, "서둘러야 해"),
    (0x165265, 23, "에스톨로 가자"),
    (0x16527E, 24, "놈들은 반드시 돌아온다"),
    (0x16529B, 25, "아 위험했어"),
    (0x1652B6, 21, "에스톨로 서두르자"),
    (0x1652CC, 26, "분명 다시 올 거야"),
    (0x1652EB, 13, "맞아"),
    (0x1652FA, 10, "가자"),
    (0x165306, 11, "이제"),
    (0x165312, 28, "병사들에게서 벗어나야 해"),
    (0x165331, 22, "뒤로 빠져나가자"),
    (0x165348, 9, "뒤로"),
    (0x165355, 10, "알았어"),
    (0x165363, 9, "후"),
    (0x16536E, 31, "남은 싸움은 여기서 보겠다"),
    (0x16538E, 31, "저 정도 병력도 못 이기면"),
    (0x1653AE, 32, "신전까지 갈 수 없을 테지"),
    (0x1653D0, 32, "이번에는 스스로 해내야 한다"),
    (0x1653F2, 24, "좋은 경험이 될 것이다"),
    (0x16540C, 26, "게다가 이번 싸움은"),
    (0x165428, 16, "전투 경험을"),
    (0x16543A, 8, "쌓을"),
    (0x165444, 23, "좋은 기회다"),
    (0x16545F, 9, "후"),
    (0x16546A, 31, "남은 싸움은 여기서 보겠다"),
    (0x16548A, 31, "저 정도 병력도 못 이기면"),
    (0x1654AA, 32, "신전까지 갈 수 없을 테지"),
    (0x1654CC, 32, "이번에는 스스로 해내야 한다"),
    (0x1654EE, 24, "좋은 경험이 될 것이다"),
    (0x16550B, 24, "내 병사들이 이렇게"),
    (0x165524, 19, "쉽게 당하다니"),
    (0x16553C, 22, "그분을 넘기지 않겠다"),
    (0x165554, 5, "아가씨"),
    (0x16555A, 18, "네놈들에겐 못 줘"),
    (0x165570, 13, "도와줘"),
    (0x165585, 20, "금방 갈게"),
    (0x16559A, 8, "버텨"),
    (0x1655A7, 22, "하하 도망칠 수 없다"),
    (0x1655BE, 29, "내 손에서 벗어날 순 없지"),
    (0x1655DC, 10, "위대한"),
    (0x1655F2, 16, "후퇴하라"),
    (0x165608, 13, "안에 있어"),
    (0x165616, 24, "놈들을 쓰러뜨릴 때까지"),
    (0x165632, 12, "알았어"),
    (0x165643, 22, "잠깐 이 검을 받아라"),
    (0x16565A, 29, "내가 쓰던 검이다"),
    (0x16567D, 21, "그레이트소드를 얻었다"),
    (0x165697, 22, "고마워 잘 쓸게"),
    (0x1656AE, 11, "소중히 할게"),
    (0x1656BF, 20, "그래 조심해"),
    (0x1656D9, 17, "다들 고마워"),
    (0x1656EC, 24, "나 때문에 이렇게까지"),
    (0x165708, 22, "신경 쓰지 마"),
    (0x165720, 30, "우리 뜻으로 하는 일이야"),
    (0x165740, 9, "가자"),
    (0x16574F, 8, "좋아"),
    (0x16575B, 26, "큰일이야"),
    (0x16577D, 16, "무슨 일이야"),
    (0x165795, 17, "레이가드군이"),
    (0x1657A8, 26, "마을 입구를 점령했어"),
    (0x1657C4, 26, "어서 가야 해"),
    (0x1657E3, 22, "네 소꿉친구가"),
    (0x1657FA, 32, "마을 끝에 살고 있지"),
    (0x16581C, 8, "맞지"),
    (0x165829, 24, "그래 위험할 거야"),
    (0x165842, 25, "서두르지 않으면"),
    (0x16585C, 24, "넌 검을 잘 쓰잖아"),
    (0x165878, 17, "도와줘"),
    (0x16588F, 20, "물론이지 가자"),
    (0x1658A9, 24, "찾던 여자를 발견했습니다"),
    (0x1658C2, 23, "대장님"),
    (0x1658E9, 25, "좋다 서둘러라"),
    (0x165908, 12, "제국군이"),
    (0x165916, 20, "리아나를 납치하려 해"),
    (0x165931, 18, "왜지"),
    (0x165944, 31, "생각할 시간이 없어"),
    (0x165964, 27, "우리가 구해야 해"),
    (0x165983, 23, "쉽지 않겠지만"),
    (0x16599C, 30, "영주님이 올 때까지"),
    (0x1659BC, 17, "버텨야 한다"),
    (0x1659D3, 15, "창병으로도"),
    (0x1659E4, 30, "막아내기 어렵겠군"),
    (0x165A04, 30, "천하 최강의 기사들이라더니"),
    (0x165A24, 7, "과연"),
    (0x165A31, 20, "이제 끝인가"),
    (0x165A49, 15, "각오해라"),
    (0x165A5B, 26, "안 돼 싸우지 마세요"),
    (0x165A76, 30, "저 때문에 목숨을 걸지 마요"),
    (0x165A96, 5, "제발"),
    (0x165AA1, 18, "그럴 수는 없어"),
    (0x165AB4, 32, "당연히 널 도와야지"),
    (0x165AD9, 22, "내 앞을 막지 마라"),
    (0x165AF0, 4, "비켜"),
    (0x165AF9, 14, "소용없어"),
    (0x165B0A, 24, "이제 네게 달렸다"),
    (0x165B24, 13, "부탁한다"),
    (0x165B38, 20, "구하러 갈게"),
    (0x165B4E, 4, "기다려"),
    (0x165B58, 21, "안 돼 도망쳐"),
    (0x165B6E, 28, "너무 위험해"),
    (0x165B8D, 12, "젠장"),
    (0x165B9A, 28, "비켜라 베이고 싶으냐"),
    (0x165BB8, 14, "내 칼을 받아라"),
    (0x165BC9, 24, "꺼져라 제국의 쓰레기"),
    (0x165BE7, 17, "무슨 일이지"),
    (0x165BFD, 4, "대장"),
    (0x165C04, 27, "마을 사람들은 어떻게 할까요"),
    (0x165C20, 10, "말입니다"),
    (0x165C2F, 24, "해치지 마라"),
    (0x165C48, 26, "이번 임무를"),
    (0x165C64, 29, "학살로 만들 생각은 없다"),
    (0x165C85, 25, "퇴로를 확보하라"),
    (0x165CA0, 4, "그의"),
    (0x165CA6, 11, "후퇴로다"),
    (0x165CB5, 8, "명령대로"),
    (0x165CBE, 13, "하겠습니다"),
    (0x165CCF, 26, "이봐 이리 와"),
    (0x165CED, 14, "꺄악 살려줘"),
    (0x165D02, 15, "멈춰라"),
    (0x165D12, 26, "폭력은 금지다"),
    (0x165D31, 5, "크윽"),
    (0x165D3B, 19, "마을은 지켜야 해"),
    (0x165D50, 10, "반드시"),
    (0x165D5F, 16, "벌레처럼"),
    (0x165D70, 15, "뭉개 주마"),
    (0x165D85, 6, "으윽"),
    (0x165D91, 14, "제가 돕겠습니다"),
    (0x165DA7, 8, "네"),
    (0x165DB5, 10, "따라와라"),
    (0x165DC0, 9, "우리가"),
    (0x165DCA, 24, "적을 제거한다"),
    (0x165DE5, 10, "네"),
    (0x165DF3, 27, "청룡 기사단장이"),
    (0x165E10, 28, "어떻게 패배할 수가"),
    (0x165E2E, 17, "있단 말인가"),
    (0x165E43, 13, "조심해라"),
    (0x165E52, 22, "싸울 수 있겠나"),
    (0x165E6D, 20, "왜 군대가"),
    (0x165E82, 24, "어린 소녀를 납치하지"),
    (0x165E9F, 25, "우리 임무에"),
    (0x165EBA, 12, "상관 마라"),
    (0x165EC9, 20, "청룡 기사단은"),
    (0x165EDE, 32, "힘뿐 아니라 기사도도"),
    (0x165F00, 32, "중히 여긴다고 들었다"),
    (0x165F22, 25, "체면도 없는가"),
    (0x165F41, 20, "사정을 모르면"),
    (0x165F56, 26, "함부로 판단하지 마라"),
    (0x165F72, 22, "그뿐이다"),
    (0x165F8A, 31, "이 임무는 우리가 택한 게 아니다"),
    (0x165FAA, 27, "황제님의 직접 명령을"),
    (0x165FC6, 30, "따르고 있을 뿐이다"),
    (0x165FEF, 20, "사정을 모르면"),
    (0x166004, 26, "함부로 판단하지 마라"),
    (0x166020, 22, "그뿐이다"),
    (0x166038, 32, "이 임무는 우리가 택한 게 아니다"),
    (0x16605A, 27, "황제님의 직접 명령을"),
    (0x166076, 30, "따르고 있을 뿐이다"),
    (0x16609F, 22, "무리할 필요 없다"),
    (0x1660B6, 6, "알겠나"),
    (0x1660BE, 17, "쉬운 임무지만"),
    (0x1660D0, 27, "여기서 죽길 바라진 않는다"),
    (0x1660EC, 28, "몸을 아껴라"),
    (0x16610A, 4, "그리고"),
    (0x166110, 15, "기억해라"),
    (0x166120, 30, "결국 선택은 우리가 한다"),
    (0x166140, 32, "변명으로 자신을 더럽히지 마라"),
    (0x166162, 27, "명심해라"),
    (0x166181, 6, "대장"),
    (0x166188, 17, "공격을 시작합니다"),
    (0x16619A, 7, "갑니다"),
    (0x1661A5, 20, "방심하지 마라"),
    (0x1661BC, 28, "적의 창병이 문제다"),
    (0x1661DA, 18, "조심해라"),
    (0x1661F1, 23, "외곽 방어를 돌파해"),
    (0x16620A, 29, "곧장 지휘관을 치겠다"),
    (0x166228, 26, "그렇게 하십시오"),
    (0x166247, 12, "알겠습니다"),
    (0x166259, 4, "대장"),
    (0x166260, 31, "더는 버틸 수 없습니다"),
    (0x166285, 19, "걱정 마라"),
    (0x16629A, 29, "내가 직접 끝내겠다"),
    (0x1662BD, 21, "우리 기사는"),
    (0x1662D4, 24, "창병에게도 멈추지 않는다"),
    (0x1662EF, 20, "버텨라 병사들"),
    (0x166304, 4, "버텨"),
    (0x16630B, 12, "네가"),
    (0x16631A, 32, "순순히 오겠나"),
    (0x16633C, 21, "힘으로 끌고 갈까"),
    (0x166357, 24, "저에게 무슨 볼일이죠"),
    (0x166370, 3, "저요"),
    (0x166379, 18, "설명하긴 어렵다"),
    (0x16638C, 8, "지금은"),
    (0x166396, 5, "나는"),
    (0x16639C, 23, "청룡 기사단장"),
    (0x1663B4, 31, "너를 데려가라는 명을 받았다"),
    (0x1663D4, 12, "그뿐이다"),
    (0x1663E3, 8, "저를요"),
    (0x1663EF, 21, "황제님께서"),
    (0x166408, 17, "수도에서"),
    (0x16641A, 24, "너를 기다리고 있으시다"),
    (0x166437, 3, "아"),
    (0x16643C, 31, "제가 가면 마을 사람들을"),
    (0x16645C, 22, "해치지 않겠어요"),
    (0x166477, 26, "물론이다"),
    (0x166492, 32, "납치만으로도 수치다"),
    (0x1664B4, 27, "무방비한 마을 사람까지"),
    (0x1664D0, 10, "죽이진 않겠다"),
    (0x1664DC, 29, "하지만 무기를 든 자에게는"),
    (0x1664FA, 26, "자비를 베풀지 않는다"),
    (0x166516, 6, "알겠다"),
    (0x166521, 23, "그 조건이면 가겠어요"),
    (0x16653A, 24, "감사합니다"),
    (0x166557, 26, "큰 도움을 받았습니다"),
    (0x166577, 25, "검을 못 쓰면 재미없지"),
    (0x166592, 29, "저 여자에게 연습이나 해 볼까"),
    (0x1665B0, 26, "거기 있는 여자 말이야"),
    (0x1665CC, 8, "저기"),
    (0x1665D7, 10, "그만둬"),
    (0x1665E2, 26, "약속과 다르잖아"),
    (0x166601, 8, "닥쳐"),
    (0x16660A, 32, "이미 잡혔는데 그게 중요해"),
    (0x16662C, 12, "상관없어"),
    (0x16663D, 14, "움직여 여자"),
    (0x166651, 23, "그녀를 해치면"),
    (0x16666A, 29, "열 배로 갚아 주겠다"),
    (0x166688, 11, "명심해라"),
    (0x166697, 5, "대장"),
    (0x16669E, 32, "알겠습니다 조심하겠습니다"),
    (0x1666C1, 22, "멈춰라"),
    (0x1666D8, 29, "이 마을을 빼앗고 싶다면"),
    (0x1666F6, 21, "우리부터 상대해라"),
    (0x166711, 4, "대장"),
    (0x166716, 16, "마을 경비대가"),
    (0x166728, 12, "왔습니다"),
    (0x166739, 19, "상관없다"),
    (0x16674E, 25, "임무는 그대로 이어 간다"),
    (0x166768, 11, "후회할 거다"),
    (0x166779, 15, "두고 보자"),
    (0x16678A, 5, "그래"),
    (0x166793, 15, "그럴까"),
    (0x1667A5, 19, "움직인다"),
    (0x1667BB, 25, "아파요 세게 당기지 마요"),
    (0x1667D6, 13, "입 다물어"),
    (0x1667E9, 23, "여자를 확보했다"),
    (0x166805, 22, "이제 철수한다"),
    (0x16681C, 14, "떠난다"),
    (0x16682F, 7, "너는"),
    (0x16683A, 31, "날 막을 수 있을 줄 알았나"),
    (0x16685A, 9, "하하하"),
    (0x166867, 8, "하지만"),
    (0x166873, 25, "날 상대하려 하다니"),
    (0x16688E, 30, "참으로 어리석군"),
    (0x1668B1, 9, "으아악"),
    (0x1668BF, 23, "왜 이렇게 잔인하죠"),
    (0x1668DB, 21, "조용히 해라"),
    (0x1668F2, 5, "다음은"),
    (0x1668FB, 7, "멈춰"),
    (0x166904, 31, "불필요한 폭력은 금지라"),
    (0x166924, 32, "내가 분명 명했다"),
    (0x166946, 32, "명령을 어기는 자는"),
    (0x166968, 11, "기사가 아니다"),
    (0x166979, 3, "네"),
    (0x16697E, 32, "앞으로 마을 사람들은 건드리지"),
    (0x1669A0, 17, "않겠습니다"),
    (0x1669B7, 21, "큭 이 자식"),
    (0x1669CE, 7, "대장"),
    (0x1669D6, 4, "님"),
    (0x1669DD, 17, "믿을 수 없군"),
    (0x1669F2, 29, "이 간단한 임무조차"),
    (0x166A10, 7, "실패하다니"),
    (0x166A1B, 22, "누가 내 영지에"),
    (0x166A32, 10, "들어왔느냐"),
    (0x166A3E, 7, "뭐지"),
    (0x166A49, 26, "무적의 청룡 기사단이"),
    (0x166A64, 27, "패배한 모양이군"),
    (0x166A85, 21, "너무 늦게 왔구나"),
    (0x166A9C, 25, "도움이 필요 없었나"),
    (0x166ABB, 17, "내 영지를"),
    (0x166ACE, 23, "침범하는 건 금지다"),
    (0x166AEB, 21, "놈들을 몰아내라"),
    (0x166B05, 21, "영주의 군대다"),
    (0x166B1D, 27, "적 지원군이 도착했다"),
    (0x166B3A, 8, "도착"),
    (0x166B45, 20, "운이 없군"),
    (0x166B5A, 17, "철수한다"),
    (0x166B6F, 9, "젠장"),
    (0x166B7B, 12, "해냈어"),
    (0x166B8B, 24, "구해 주셔서 감사합니다"),
    (0x166BA4, 30, "검사님 저는"),
    (0x166BC6, 24, "빛의 신전 무녀"),
    (0x166BE0, 31, "리아나입니다 성함을"),
    (0x166C00, 5, "물어도"),
    (0x166C0B, 4, "나는"),
    (0x166C12, 11, "여행자다"),
    (0x166C21, 20, "정말 고마워요"),
    (0x166C36, 4, "님"),
    (0x166C3C, 14, "어떻게 갚아야"),
    (0x166C4C, 17, "할지 모르겠어요"),
    (0x166C63, 19, "그럴 필요 없어"),
    (0x166C78, 18, "다친 곳은 없어"),
    (0x166C8F, 25, "네 괜찮아요 오히려"),
    (0x166CAA, 21, "제가 묻고 싶어요"),
    (0x166CC7, 18, "제발 님이라고는"),
    (0x166CDA, 22, "부르지 않아도 돼"),
    (0x166CF2, 5, "그냥"),
    (0x166CF8, 9, "이라 불러"),
    (0x166D07, 22, "그럼 저도"),
    (0x166D1E, 3, "리아나"),
    (0x166D29, 5, "와"),
    (0x166D32, 30, "역시 생각대로 강하구나"),
    (0x166D56, 15, "도와줘서"),
    (0x166D66, 12, "고마워"),
    (0x166D75, 26, "여기 남아 있으면 위험해"),
    (0x166D90, 31, "기사들이 다시 올 거야"),
    (0x166DB0, 24, "잠시 우리 저택으로"),
    (0x166DCA, 26, "피신하자 멀지 않아"),
    (0x166DE6, 27, "그게 좋겠어"),
    (0x166E02, 12, "알겠어요"),
    (0x166E13, 24, "바로 떠나자"),
    (0x166E3D, 21, "두고 보자"),
    (0x166E55, 11, "왜"),
    (0x166E64, 16, "이런 일을"),
    (0x166E79, 3, "하나"),
    (0x166E7E, 26, "이런 임무는 처음이다"),
    (0x166E9A, 24, "어린 소녀를 납치하다니"),
    (0x166EB4, 25, "부끄러운 일이다"),
    (0x166ECE, 20, "어떤 임무라도"),
    (0x166EE7, 12, "대장님을"),
    (0x166EF4, 29, "따르는 건 영광입니다"),
    (0x166F12, 28, "그리 말해 주니 고맙다"),
    (0x166F31, 24, "용감하되 무리하지 마라"),
    (0x166F4A, 25, "좋은 말이다"),
    (0x166F64, 32, "용기를 가지고 싸워라"),
    (0x166F87, 14, "저 녀석"),
    (0x166F96, 27, "이미 내 병사를 쓰러뜨렸다"),
    (0x166FB2, 9, "제법이군"),
    (0x166FBF, 23, "첫 출전이니"),
    (0x166FD8, 28, "한 가지 충고해 주지"),
    (0x166FF6, 7, "들어라"),
    (0x166FFE, 28, "다친 병사는 지휘관 곁에"),
    (0x16701C, 32, "두면 조금씩 회복한다"),
    (0x16703E, 32, "부대를 살리는 데 중요하다"),
    (0x167060, 27, "기억해 두어라"),
    (0x16707F, 14, "명심하겠습니다"),
    (0x16708E, 8, "네"),
    (0x167099, 14, "실력을 보자"),
    (0x1670A8, 10, "간다"),
    (0x1670B5, 14, "누가 덤빌까"),
    (0x1670C4, 13, "모두 부숴주마"),
    (0x1670D5, 16, "죄송합니다"),
    (0x1670E8, 3, "님"),
]


FIXED_TEXT_PATCHES: list[tuple[int, int, str]] = [
    (0xA7415, 13, "전투 경로"),
    (0xA7425, 11, "프롤로그"),
    (0xA7432, 10, "결과"),
    (0xA743E, 7, "저장"),
    (0xA7447, 6, "불러옴"),
    (0xA744F, 17, "아이템 구매"),
    (0xA7462, 13, "아이템 판매"),
    (0xA7471, 18, "주인공 이름 입력"),
    (0xA7484, 12, "시나리오"),
    (0xA7491, 10, "승리"),
    (0xA749C, 9, "패배"),
    (0xA74A6, 9, "턴수"),
    (0xA74B0, 9, "합계"),
    (0xA8DA2, 4, "이동"),
    (0xA8DA9, 6, "공격"),
    (0xA8DB0, 5, "마법"),
    (0xA8DB6, 6, "소환"),
    (0xA8DBD, 5, "치료"),
    (0xA8DC3, 6, "명령"),
    (0xAE9A0, 5, "나이프"),
    (0x1B8E04, 5, "엘윈"),
    (0x1B8E0C, 5, "리아나"),
    (0x1B8E22, 4, "헤인"),
    (0x1B8E28, 5, "스코트"),
    (0x1B8EDC, 7, "병사"),
    (0x1B8F3E, 10, "마을 경비"),
    (0x1B92AE, 16, "제국 병사"),
    (0x1B9409, 7, "전사"),
    (0x1B9418, 7, "마법사"),
    (0x1B9810, 7, "창병"),
    (0x1B9818, 7, "팔랑크스"),
    (0x1B9820, 7, "솔저"),
    (0x1B9878, 5, "가드"),
    (0x1B9C09, 5, "엘윈"),
    (0x1B9C0F, 5, "리아나"),
    (0x1B9C21, 4, "헤인"),
    (0x1B9C26, 5, "스코트"),
    (0x1BC1DD, 5, "엘윈"),
    (0x1BC1E3, 5, "리아나"),
    (0x1BC1F5, 4, "헤인"),
    (0x1BC1FA, 5, "스코트"),
]


def main() -> int:
    if not FONT_PATH.exists():
        raise FileNotFoundError(FONT_PATH)

    chars = collect_chars()
    code_map = {ch: CODE_POOL[idx] for idx, ch in enumerate(chars)}
    rom = bytearray(SRC.read_bytes())

    patch_fixed_font(rom, code_map)
    patch_vwf_font(rom, code_map)

    for offset, length, text in TEXT_PATCHES:
        patch_text_at(rom, offset, length, text, code_map)
    for offset, length, text in FIXED_TEXT_PATCHES:
        patch_text_at(rom, offset, length, text, code_map)

    update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"complete Hangul glyphs: {len(chars)}")
    print(f"code slots used: {len(code_map)} / {len(CODE_POOL)}")
    print("sample map: " + " ".join(f"{ch}=0x{code:02x}" for ch, code in list(code_map.items())[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
