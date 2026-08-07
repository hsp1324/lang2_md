import pytest
import scripts.build_korean_jp_probe as jp_builder

from scripts.build_korean_jp_probe import install_custom_glyphs
from tools.build_korean_empire import (
    DEFAULT_DRAFT_SCRIPT,
    EMPIRE_ARRANGE_MENU_GLYPH_LIST,
    EMPIRE_BATTLE_COMMAND_GLYPH_LIST,
    EMPIRE_BATTLE_RESULT_HEADER_GLYPH_LIST,
    EMPIRE_CLASS_CHANGE_GLYPH_LIST,
    EMPIRE_ENDING_STATUS_GLYPH_LIST,
    EMPIRE_FONT_BASE_PATCHES,
    EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_POINTER,
    EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC,
    EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_POINTER,
    EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_POINTER,
    EMPIRE_ITEM_NAME_POINTER_TABLE,
    EMPIRE_ITEM_NAME_TOKEN_RELOC_BASE,
    EMPIRE_ITEM_NAME_TOKEN_RELOC_LIMIT,
    EMPIRE_OPENING_TEXT_LIST_PATCHES,
    EMPIRE_OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES,
    EMPIRE_SHOP_POSSESSION_GLYPH_LIST,
    EMPIRE_SHOP_PURCHASE_SUFFIX,
    EMPIRE_SHOP_SELL_SUFFIX,
    EMPIRE_SHOP_SELL_TITLE_TOKEN_STREAM,
    EMPIRE_SRAM_LONG_PATCHES,
    EMPIRE_WORD_ITEM_NAME_POINTER_TABLE,
    EMPIRE_WORD_ITEM_NAME_RELOC_BASE,
    EMPIRE_WORD_ITEM_NAME_RELOC_LIMIT,
    EXPANDED_ROM_SIZE,
    JP_FONT_BASE,
    SRAM_DELTA,
    be32,
    collect_empire_glyph_chars,
    expand_empire_rom,
    load_script,
    patch_empire_font_base,
    patch_empire_byte_ui,
    patch_empire_common_ui,
    relocate_event_dialogue,
    relocate_indirect_text,
    script_texts,
    validate_empire_byte_ui_delta,
    validate_empire_common_ui_delta,
    validate_localization_only_delta,
)
from tools.empire_profile import DEFAULT_EMPIRE_ROM, load_empire_labels
from scripts.build_korean_jp_probe import collect_chars


@pytest.fixture(scope="module")
def source() -> bytes:
    if not DEFAULT_EMPIRE_ROM.exists():
        pytest.skip("Empire source ROM is not available")
    return DEFAULT_EMPIRE_ROM.read_bytes()


@pytest.fixture(scope="module")
def diagnostic_build(source: bytes) -> tuple[bytearray, dict[str, object]]:
    script = load_script(DEFAULT_DRAFT_SCRIPT, allow_draft=True)
    data = bytearray(source)
    expand_empire_rom(data)
    patch_empire_font_base(data)
    glyphs = install_custom_glyphs(data, collect_chars(*script_texts(script)))
    event = relocate_event_dialogue(data, source, script, glyphs)
    indirect = relocate_indirect_text(data, script, glyphs)
    return data, {"event": event, "indirect": indirect}


def test_empire_expansion_uses_shifted_sram_and_font_operands(
    diagnostic_build: tuple[bytearray, dict[str, object]],
) -> None:
    data, _ = diagnostic_build
    assert len(data) == EXPANDED_ROM_SIZE
    assert be32(data, 0x01A4) == EXPANDED_ROM_SIZE - 1
    assert be32(data, 0x01B4) == 0x400001
    assert be32(data, 0x01B8) == 0x403FFF
    for offset, source_value in EMPIRE_SRAM_LONG_PATCHES.items():
        assert be32(data, offset) == source_value + SRAM_DELTA
    for offset in EMPIRE_FONT_BASE_PATCHES:
        assert be32(data, offset) == JP_FONT_BASE


def test_all_empire_text_records_are_relocated(
    diagnostic_build: tuple[bytearray, dict[str, object]],
) -> None:
    _, manifest = diagnostic_build
    assert manifest["event"]["logical_pages"] == 2852
    assert manifest["event"]["physical_pages"] == 3214
    assert manifest["indirect"]["records"] == 63


def test_empire_structured_event_records_are_not_relocated_as_dialogue(
    source: bytes,
    diagnostic_build: tuple[bytearray, dict[str, object]],
) -> None:
    data, _ = diagnostic_build
    for address, word_count, source_ref, embedded_pointer_offsets in (
        (0x18F690, 13, 0x18F3D0, (4, 12, 20)),
        (0x1B0592, 17, 0x1B0460, ()),
    ):
        mutable = set()
        for offset in embedded_pointer_offsets:
            mutable.update(range(offset, offset + 4))
            target = be32(data, address + offset)
            assert 0x320000 <= target < 0x360000
        for offset in range(word_count * 2):
            if offset not in mutable:
                assert data[address + offset] == source[address + offset]
        assert be32(data, source_ref) == address


def test_machine_draft_is_not_release_input() -> None:
    with pytest.raises(ValueError, match="not fully human reviewed"):
        load_script(DEFAULT_DRAFT_SCRIPT, allow_draft=False)


def test_empire_byte_ui_uses_reordered_class_and_name_tables(
    source: bytes,
) -> None:
    baseline = bytearray(source)
    expand_empire_rom(baseline)
    patch_empire_font_base(baseline)
    data = bytearray(baseline)
    code_by_char = patch_empire_byte_ui(data)
    byte_ui_offsets = validate_empire_byte_ui_delta(
        baseline, data, source_size=len(source)
    )
    assert len(byte_ui_offsets) == 1208
    # The Empire item pointer table begins 0x10 earlier than the normal one;
    # byte-UI category labels must not overwrite it.
    assert be32(data, EMPIRE_ITEM_NAME_POINTER_TABLE) == 0x0A198A
    assert be32(data, EMPIRE_ITEM_NAME_POINTER_TABLE + 4) == 0x0A1992
    assert "마" in code_by_char
    class_labels, _ = load_empire_labels()
    for label in ("마샬", "퀸"):
        index = class_labels.index(label)
        pointer = be32(
            data, jp_builder.CLASS_BYTE_POINTER_TABLE + index * 4
        )
        assert jp_builder.BYTE_UI_CLASS_STRING_RELOC_BASE <= pointer
        payload = data[pointer : pointer + len(label) * 2 + 1]
        assert payload[-1] == 0xFF
        assert payload[::2][:-1] == bytes([jp_builder.BYTE_UI_LOCAL_MARKER]) * len(label)

    # Empire inserted 0x64 bytes in the title code and already renders its
    # existing copyright record in the preceding routine.  The localized
    # edition/version hook must call the shifted renderer without replaying
    # the normal-edition copyright record as text.
    title_routine = bytes(
        data[
            jp_builder.TITLE_CREDIT_RENDER_ROUTINE:
            jp_builder.TITLE_CREDIT_TEXT_RECORD
        ]
    )
    shifted_call = bytes.fromhex("4E B9 00 02 D9 EA")
    normal_call = bytes.fromhex("4E B9 00 02 D9 86")
    normal_copyright_record = bytes.fromhex("45 F9 00 0A 44 F8")
    assert title_routine.count(shifted_call) == 2
    assert normal_call not in title_routine
    assert normal_copyright_record not in title_routine


def test_empire_byte_ui_delta_is_allowed_only_after_fingerprint(
    source: bytes,
) -> None:
    baseline = bytearray(source)
    expand_empire_rom(baseline)
    patch_empire_font_base(baseline)
    data = bytearray(baseline)
    patch_empire_byte_ui(data)
    byte_ui_offsets = validate_empire_byte_ui_delta(
        baseline, data, source_size=len(source)
    )
    assert validate_localization_only_delta(
        source,
        data,
        additional_allowed_offsets=byte_ui_offsets,
    ) > 0

    mutated = bytearray(data)
    mutated[0x05EDDC] ^= 0x01
    with pytest.raises(ValueError, match="gameplay-owned byte 0x05EDDC"):
        validate_localization_only_delta(
            source,
            mutated,
            additional_allowed_offsets=byte_ui_offsets,
        )


def test_empire_common_ui_subset_is_fingerprinted_and_localization_only(
    source: bytes,
) -> None:
    script = load_script(DEFAULT_DRAFT_SCRIPT, allow_draft=True)
    data = bytearray(source)
    expand_empire_rom(data)
    patch_empire_font_base(data)
    glyphs = install_custom_glyphs(data, collect_empire_glyph_chars(script))
    _, common_ui_offsets = patch_empire_common_ui(
        data,
        glyphs,
        source_size=len(source),
    )
    assert len(common_ui_offsets) == 13412
    item_pointers = [
        be32(data, EMPIRE_ITEM_NAME_POINTER_TABLE + index * 4)
        for index in range(len(jp_builder.ITEM_NAME_PATCHES))
    ]
    assert all(
        EMPIRE_ITEM_NAME_TOKEN_RELOC_BASE
        <= pointer
        < EMPIRE_ITEM_NAME_TOKEN_RELOC_LIMIT
        for pointer in item_pointers
    )
    word_item_pointers = [
        jp_builder.word_swapped_pointer(
            data, EMPIRE_WORD_ITEM_NAME_POINTER_TABLE + index * 4
        )
        for index in range(37)
    ]
    assert all(
        EMPIRE_WORD_ITEM_NAME_RELOC_BASE
        <= pointer
        < EMPIRE_WORD_ITEM_NAME_RELOC_LIMIT
        for pointer in word_item_pointers
    )

    reverse_glyph = {glyph: char for char, glyph in glyphs.items()}
    reverse_glyph[jp_builder.SPACE_GLYPH] = " "
    reverse_glyph[jp_builder.OPENING_SPACE_GLYPH] = " "
    direct_rows = (
        (EMPIRE_BATTLE_COMMAND_GLYPH_LIST, 12, "이동공격마법소환치료명령"),
        (EMPIRE_BATTLE_RESULT_HEADER_GLYPH_LIST, 4, "전과보고"),
        (EMPIRE_ENDING_STATUS_GLYPH_LIST, 8, "격파횟수퇴각횟수"),
        (
            EMPIRE_CLASS_CHANGE_GLYPH_LIST,
            15,
            jp_builder.CLASS_CHANGE_GLYPH_TEXT,
        ),
        (EMPIRE_ARRANGE_MENU_GLYPH_LIST, 6, "이동순변경자"),
    )
    for offset, count, expected in direct_rows:
        assert "".join(
            reverse_glyph[jp_builder.be16(data, offset + index * 2)]
            for index in range(count)
        ) == expected
    for source_offset, (renderer_count, text) in (
        EMPIRE_OPENING_TEXT_LIST_PATCHES.items()
    ):
        terminator_index = (
            EMPIRE_OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES[source_offset]
        )
        capacity = renderer_count if terminator_index is None else terminator_index
        rendered = "".join(
            reverse_glyph[jp_builder.be16(data, source_offset - 0x10 + index * 2)]
            for index in range(capacity)
        )
        assert rendered == text.ljust(capacity)
        if terminator_index is not None:
            assert jp_builder.be16(
                data,
                source_offset - 0x10 + terminator_index * 2,
            ) == 0xFFFF
    item_glyphs = jp_builder.read_word_list(
        data, jp_builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE
    )
    for index in (0, 1, 27, 36):
        tokens = jp_builder.read_word_list(data, item_pointers[index])
        rendered = "".join(reverse_glyph[item_glyphs[token]] for token in tokens)
        assert rendered == jp_builder.ITEM_NAME_PATCHES[index].replace(" ", "")

    # The Empire edit compacts the shop resources by 0x10 bytes.  These
    # assertions guard against accidentally applying the stock JP offsets,
    # which silently overwrite the first item-name pointers and only show up
    # later as broken item/mercenary glyphs in game.
    assert jp_builder.read_word_list(
        data, EMPIRE_SHOP_PURCHASE_SUFFIX
    )[:5] == [6, 7, 8, 9, 10]
    assert jp_builder.read_word_list(
        data, EMPIRE_SHOP_SELL_SUFFIX
    )[:5] == [6, 7, 11, 12, 10]
    assert be32(data, EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_POINTER) == (
        jp_builder.ITEM_DISCARD_NOTICE_RELOC_GLYPH_LIST
    )
    assert be32(data, EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_POINTER) == (
        jp_builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM
    )
    assert be32(data, EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_POINTER) == (
        EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC
    )
    assert [
        reverse_glyph[
            jp_builder.be16(
                data,
                EMPIRE_SHOP_POSSESSION_GLYPH_LIST + slot * 2,
            )
        ]
        for slot in range(6)
    ] == list("아이템 구입")
    assert [
        jp_builder.be16(data, EMPIRE_SHOP_SELL_TITLE_TOKEN_STREAM + slot * 2)
        for slot in range(6)
    ] == [0, 1, 2, 3, 11, 12]
    assert validate_localization_only_delta(
        source,
        data,
        additional_allowed_offsets=common_ui_offsets,
    ) > 0


def test_localization_delta_guard_rejects_balance_mutation(
    source: bytes,
    diagnostic_build: tuple[bytearray, dict[str, object]],
) -> None:
    data, _ = diagnostic_build
    assert validate_localization_only_delta(source, data) > 0
    mutated = bytearray(data)
    mutated[0x05EDDC] ^= 0x01
    with pytest.raises(ValueError, match="gameplay-owned byte 0x05EDDC"):
        validate_localization_only_delta(source, mutated)
