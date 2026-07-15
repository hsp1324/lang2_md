#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools.jp_text_font_analyzer import be16, be32


SCAN_END = 0x180000
MAX_GLYPH_ID = 0x07FF
CONTROLS = {0xFFF7, 0xFFFD, 0xFFFE}
TERMINATOR = 0xFFFF
MIN_GLYPHS = 3
MAX_WORDS = 64

CONFIRMED_UNPATCHED_SYSTEM_MESSAGES = {
    0x082ACE: "레벨이 올랐다.",
    0x082AE2: "AT가",
    0x082AEA: "DF가",
    0x082AF2: "MP가",
    0x082AFA: "1 올랐다.",
    0x082B08: "2 올랐다.",
    0x082B16: "을 배웠다.",
    0x082B22: "을 사용할 수 있게 됐다.",
    0x082B3C: "GAME OVER",
    0x082B56: "을 손에 넣었다!",
    0x082B66: "트레저군:",
    # 0x082B78 is a secret/debug-style message whose exact context is not yet proven.
    0x082B90: "을 장비했다.",
}

CONFIRMED_UNRESOLVED_DIRECT_MESSAGES = {
    0x082B78: "비기/디버그성 문구 `面をしないだすー` (실행 문맥 미확정)",
}


def scan_candidates(data: bytes, start: int = 0, end: int = SCAN_END) -> list[tuple[int, list[int]]]:
    entries = []
    position = start
    while position + 1 < end:
        words = []
        glyph_count = 0
        cursor = position
        terminated = False
        while cursor + 1 < end and len(words) <= MAX_WORDS:
            value = be16(data, cursor)
            cursor += 2
            if value == TERMINATOR:
                terminated = True
                break
            if value in CONTROLS:
                words.append(value)
                continue
            if value > MAX_GLYPH_ID:
                break
            words.append(value)
            glyph_count += 1
        if terminated and MIN_GLYPHS <= glyph_count and len(words) <= MAX_WORDS:
            entries.append((position, words + [TERMINATOR]))
            position = cursor
        else:
            position += 2
    return entries


def read_current_stream(data: bytes, offset: int, limit: int = 256) -> list[int] | None:
    words = []
    for _ in range(limit):
        if offset + 1 >= len(data):
            return None
        value = be16(data, offset)
        words.append(value)
        offset += 2
        if value == TERMINATOR:
            return words
    return None


def pointer_owners(data: bytes) -> dict[int, str]:
    owners = {}
    groups = {
        "conditions": (0x098D7A, 32),
        "scenario_descriptions": (0x09CF7C, 31),
        "item_names": (0x0A1902, 38),
        "item_descriptions": (0x0A1D7C, 37),
    }
    for name, (table, count) in groups.items():
        for index in range(count):
            owners[be32(data, table + index * 4)] = f"{name}[{index}]"
    glyph_groups = {
        "condition_glyph_lists": (0x0986C6, 32),
        "scenario_description_glyph_lists": (0x09B2FC, 31),
    }
    for name, (table, count) in glyph_groups.items():
        for index in range(count):
            owners[be32(data, table + index * 4)] = f"{name}[{index}]"
    return owners


def pointer_record_intervals(data: bytes) -> list[tuple[int, int, str]]:
    groups = {
        "conditions_tokens": (0x098D7A, 32, None),
        "condition_glyph_lists": (0x0986C6, 32, 0x098D7A),
        "scenario_description_tokens": (0x09CF7C, 31, None),
        "scenario_description_glyph_lists": (0x09B2FC, 31, 0x09CF7C),
        "item_name_tokens": (0x0A1902, 38, None),
        "item_description_tokens": (0x0A1D7C, 37, None),
    }
    intervals = []
    for name, (table, count, fixed_end) in groups.items():
        pointers = [be32(data, table + index * 4) for index in range(count)]
        unique = sorted(set(pointers))
        for position, start in enumerate(unique):
            if position + 1 < len(unique):
                end = unique[position + 1]
            elif fixed_end is not None:
                end = fixed_end
            else:
                terminator = data.find(b"\xff\xff", start, min(len(data), start + 0x1000))
                end = terminator + 2 if terminator >= 0 else start
            if start < end:
                intervals.append((start, end, name))
    return intervals


def declared_targets() -> dict[int, str]:
    targets = {
        offset: text
        for offset, text in builder.DIRECT_STRING_PATCHES.items()
        if offset < SCAN_END
    }
    for offset, (_, text) in builder.OPENING_TEXT_LIST_PATCHES.items():
        targets[offset] = text
    return targets


def declared_ui_surfaces() -> dict[int, str]:
    surfaces = {}
    for patches in (
        builder.BYTE_UI_STRING_PATCHES,
        builder.BYTE_UI_FIXED_STRING_PATCHES,
        builder.BYTE_UI_WORD_STRING_PATCHES,
        builder.DIRECT_WORD_SEQUENCE_PATCHES,
        builder.DIRECT_FIXED_STRING_PATCHES,
        builder.ARRANGE_MENU_GLYPH_LIST_PATCHES,
        builder.DIRECT_FIXED_ROUTE_TITLE_PATCHES,
        builder.DIRECT_FIXED_SCENARIO_HEADER_PATCHES,
    ):
        for offset, spec in patches.items():
            surfaces[offset] = spec[1] if isinstance(spec, tuple) else spec
    surfaces.update(
        {
            builder.START_MENU_GLYPH_LIST: "Start 메뉴 글리프 목록",
            builder.LOAD_MENU_GLYPH_LIST: "불러오기 메뉴 글리프 목록",
            builder.ORDER_SUBMENU_TOKEN_STREAM: "명령 하위 메뉴 토큰",
            0x0971A2: "게임 설정/검색 메뉴 공통 글리프 목록",
        }
    )
    return surfaces


NAME_ENTRY_RESOURCES = {
    0x0A3824: "이름 입력 영문/숫자 리소스 블록",
    0x0A3864: "이름 입력 영문/숫자 글리프 목록",
    0x0A38A6: "이름 입력 로컬 토큰 레이아웃 A",
    0x0A38C2: "이름 입력 로컬 토큰 레이아웃 B",
    0x0A3BB0: "이름 확정 YES/NO 글리프 목록",
    0x0A3BC0: "이름 입력 버퍼/레이아웃 블록",
    0x0A3C50: "이름 입력 일본어 문자 리소스 블록",
    0x0A3C5A: "이름 입력 일본어 문자 글리프 목록",
    0x0A3CC0: "이름 입력 로컬 토큰 행 A",
    0x0A3CE2: "이름 입력 로컬 토큰 행 B",
}


def range_ownership(offset: int) -> tuple[str, str | None] | None:
    if offset < 0x040000:
        return "executable_code_or_table_false_positive", "68000 실행 코드/포인터·수치 테이블"
    if 0x082000 <= offset < 0x082900:
        return "structured_game_data_false_positive", "마법/전투 수치 배열"
    if 0x05F000 <= offset < 0x060000:
        return "structured_game_data_false_positive", "클래스/유닛 수치 레코드"
    if 0x060000 <= offset < 0x061000:
        return "structured_game_data_false_positive", "아이템 수치/효과/그래픽 데이터"
    if 0x087000 <= offset < 0x089000:
        return "structured_game_data_false_positive", "엔딩 캐릭터 상태/분기 수치·포인터 배열"
    if 0x089100 <= offset < 0x089600:
        return "structured_game_data_false_positive", "엔딩 후일담 포인터/선택 데이터"
    if 0x0895A2 <= offset < 0x0954E2:
        return "confirmed_untranslated_epilogue_fragment", "인물별 후일담 레코드 조각 번역 필요"
    if 0x0954E2 <= offset < 0x096D00:
        return "confirmed_untranslated_ending_fragment", "엔딩 대화 레코드 조각 번역 필요"
    if 0x096D00 <= offset < 0x096F00:
        return "structured_game_data_false_positive", "엔딩 선택/레이아웃 데이터"
    if 0x096F00 <= offset < 0x097000:
        return "local_token_stream", "공통 UI 글리프/토큰 목록"
    if 0x09A000 <= offset < 0x09B000:
        return "local_token_stream", "전투 UI 화면별 로컬 토큰/레이아웃"
    if 0x09B000 <= offset < 0x09B2FC:
        return "local_token_stream", "시스템 UI 화면별 글리프·로컬 토큰"
    if 0x0A1000 <= offset < 0x0A2000:
        return "item_shop_local_resource", "아이템/상점 화면별 글리프·토큰·포인터"
    if 0x0A2B00 <= offset < 0x0A3000:
        return "local_token_stream", "지휘관 배치/출격 화면별 글리프·토큰"
    if 0x0A30D6 <= offset <= 0x0A3154:
        return "name_entry_resource", "이름 입력 일본어 문자 선택 보조표"
    if offset in (0x0A342A, 0x0A3788):
        return "confirmed_credits_record", "제작진 크레딧 보조표"
    if 0x0A344A <= offset <= 0x0A3752:
        return "confirmed_credits_record", "제작진 크레딧"
    if 0x0A3D00 <= offset < 0x0A4000:
        return "structured_game_data_false_positive", "준비/상태 UI 레이아웃 데이터"
    if 0x0A6B20 <= offset < 0x0A7000:
        return "pointer_table_record_interior", "오프닝 텍스트 리소스 내부"
    if 0x0D0000 <= offset < SCAN_END:
        return "structured_map_event_data_false_positive", "맵/이벤트 구조·그래픽 데이터"
    return None


def tokens(words: list[int] | None) -> str | None:
    return None if words is None else " ".join(f"{word:04X}" for word in words)


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    owners = pointer_owners(japanese)
    record_intervals = pointer_record_intervals(japanese)
    targets = declared_targets()
    unsafe_targets = builder.UNSAFE_DIRECT_NAME_PATCHES
    ui_surfaces = declared_ui_surfaces()
    ending_intervals = []
    for row in builder.load_ending_dialogue_translations():
        start = int(row["address_int"])
        capacity, _, _ = builder.direct_record_layout(japanese, start)
        ending_intervals.append((start, start + capacity * 2, str(row["text"])))
    epilogue_intervals = []
    for row in builder.load_epilogue_dialogue_translations():
        start = int(row["address_int"])
        capacity, _, _ = builder.direct_record_layout(japanese, start)
        epilogue_intervals.append((start, start + capacity * 2, str(row["text"])))
    credits_intervals = []
    credits = builder.load_credits_translations()
    for index, row in enumerate(credits["records"]):
        if row.get("synthetic"):
            continue
        start = int(row["source_address_int"])
        capacity, _, _ = builder.direct_record_layout(japanese, start)
        relocated = be32(
            korean, builder.CREDITS_POINTER_RELOC_BASE + index * 4
        )
        credits_intervals.append(
            (
                start,
                start + capacity * 2,
                str(row["target_korean"]),
                relocated,
                index,
            )
        )
    rows = []
    for offset, original in scan_candidates(japanese):
        current = read_current_stream(korean, offset)
        ranged = None
        credits_record = None
        if offset in owners:
            ownership = "pointer_table_record"
        elif offset in targets:
            ownership = "declared_direct_patch"
        elif offset in unsafe_targets:
            ownership = "known_unsafe_name_record"
        elif offset in CONFIRMED_UNPATCHED_SYSTEM_MESSAGES:
            ownership = "confirmed_unpatched_system_message"
        elif offset in CONFIRMED_UNRESOLVED_DIRECT_MESSAGES:
            ownership = "confirmed_unresolved_direct_message"
        elif offset in ui_surfaces:
            ownership = "declared_ui_surface"
        elif offset in NAME_ENTRY_RESOURCES:
            ownership = "name_entry_resource"
        else:
            interior = next(
                (owner for start, end, owner in record_intervals if start < offset < end),
                None,
            )
            if interior:
                ranged = ("pointer_table_record_interior", interior)
            else:
                ending = next(
                    (
                        (start, text)
                        for start, end, text in ending_intervals
                        if start <= offset < end
                    ),
                    None,
                )
                epilogue = next(
                    (
                        (start, text)
                        for start, end, text in epilogue_intervals
                        if start <= offset < end
                    ),
                    None,
                )
                credits_record = next(
                    (
                        (start, target, relocated, index)
                        for start, end, target, relocated, index in credits_intervals
                        if start <= offset < end
                    ),
                    None,
                )
                if ending:
                    ranged = (
                        "declared_ending_translation",
                        f"엔딩 번역 레코드 0x{ending[0]:06X}: {ending[1]}",
                    )
                elif epilogue:
                    ranged = (
                        "declared_epilogue_translation",
                        f"후일담 번역 레코드 0x{epilogue[0]:06X}: {epilogue[1]}",
                    )
                elif credits_record:
                    ranged = (
                        "declared_credits_translation",
                        f"크레딧 번역 레코드 {credits_record[3]:02d} "
                        f"0x{credits_record[0]:06X}: {credits_record[1]}",
                    )
                else:
                    ranged = range_ownership(offset)
            ownership = ranged[0] if ranged else "unclassified_candidate"
        rows.append(
            {
                "address": f"0x{offset:06X}",
                "ownership": ownership,
                "owner": owners.get(offset),
                "target_korean": (
                    targets.get(offset)
                    or unsafe_targets.get(offset)
                    or CONFIRMED_UNPATCHED_SYSTEM_MESSAGES.get(offset)
                    or CONFIRMED_UNRESOLVED_DIRECT_MESSAGES.get(offset)
                    or ui_surfaces.get(offset)
                    or NAME_ENTRY_RESOURCES.get(offset)
                    or (ranged[1] if ranged else None)
                ),
                "original_word_count": len(original),
                "original_tokens": tokens(original),
                "current_tokens": tokens(current),
                "relocated_pointer": (
                    f"0x{credits_record[2]:06X}" if credits_record else None
                ),
                # Relocated credits intentionally leave the source bytes intact.
                # Their reachable pointer changed even when this stale source
                # interval remains byte-identical.
                "modified": current != original or credits_record is not None,
                "reviewed": False,
            }
        )
    counts = {
        category: sum(row["ownership"] == category for row in rows)
        for category in (
            "pointer_table_record",
            "pointer_table_record_interior",
            "declared_direct_patch",
            "known_unsafe_name_record",
            "confirmed_unpatched_system_message",
            "confirmed_unresolved_direct_message",
            "declared_ui_surface",
            "name_entry_resource",
            "confirmed_credits_record",
            "confirmed_untranslated_ending_fragment",
            "confirmed_untranslated_epilogue_fragment",
            "declared_ending_translation",
            "declared_epilogue_translation",
            "declared_credits_translation",
            "local_token_stream",
            "item_shop_local_resource",
            "structured_game_data_false_positive",
            "executable_code_or_table_false_positive",
            "structured_map_event_data_false_positive",
            "unclassified_candidate",
        )
    }
    return {
        "scan_range": f"0x000000..0x{SCAN_END:06X}",
        "candidate_count": len(rows),
        "modified_candidate_count": sum(bool(row["modified"]) for row in rows),
        "ownership_counts": counts,
        "warning": (
            "Candidates only match a conservative glyph/control/FFFF byte pattern. "
            "Unclassified candidates may be data and require ownership proof before patching."
        ),
        "candidates": rows,
    }


def markdown_report(result: dict[str, object]) -> str:
    counts = result["ownership_counts"]
    return "\n".join(
        [
            "# Direct Word-String Candidate Inventory",
            "",
            "Generated by `python3 tools/jp_direct_string_inventory.py`.",
            "",
            "The scanner accepts at least three Japanese glyph IDs (`0000..07FF`), known",
            "controls, and an `FFFF` terminator outside the scenario event blocks. A match is",
            "a candidate, not proof that the data is visible text.",
            "",
            f"- Scan range: `{result['scan_range']}`",
            f"- Candidates: {result['candidate_count']}",
            f"- Modified candidates: {result['modified_candidate_count']}",
            f"- Exact pointer-table records: {counts['pointer_table_record']}",
            f"- Pointer-table record interiors: {counts['pointer_table_record_interior']}",
            f"- Existing declared direct patches: {counts['declared_direct_patch']}",
            f"- Known unsafe name records: {counts['known_unsafe_name_record']}",
            f"- Confirmed unpatched system messages: {counts['confirmed_unpatched_system_message']}",
            f"- Confirmed unresolved direct messages: {counts['confirmed_unresolved_direct_message']}",
            f"- Declared UI surfaces: {counts['declared_ui_surface']}",
            f"- Name-entry resources: {counts['name_entry_resource']}",
            f"- Credits records: {counts['confirmed_credits_record']}",
            f"- Declared credits translation fragments: {counts['declared_credits_translation']}",
            f"- Untranslated ending fragments: {counts['confirmed_untranslated_ending_fragment']}",
            f"- Untranslated epilogue fragments: {counts['confirmed_untranslated_epilogue_fragment']}",
            f"- Declared ending translation fragments: {counts['declared_ending_translation']}",
            f"- Declared epilogue translation fragments: {counts['declared_epilogue_translation']}",
            f"- Screen-local token streams: {counts['local_token_stream']}",
            f"- Item/shop local resources: {counts['item_shop_local_resource']}",
            f"- Structured-data false positives: {counts['structured_game_data_false_positive']}",
            f"- Executable/table false positives: {counts['executable_code_or_table_false_positive']}",
            f"- Map/event-data false positives: {counts['structured_map_event_data_false_positive']}",
            f"- Unclassified candidates: {counts['unclassified_candidate']}",
            "",
            "Unclassified records must be rendered or cross-referenced from code before they are",
            "added to the builder. Detailed tokens and ownership are in",
            "`localization/direct_word_candidates.json`.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory conservative direct word-string candidates")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom", type=Path, default=Path("roms/builds/Langrisser II (Korean JP Probe).md")
    )
    parser.add_argument("--json", type=Path, default=Path("localization/direct_word_candidates.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/direct_word_candidate_inventory.md"))
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['candidate_count']} candidates; "
        f"{result['ownership_counts']['unclassified_candidate']} unclassified"
    )


if __name__ == "__main__":
    main()
