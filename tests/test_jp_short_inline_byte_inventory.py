import json
from pathlib import Path
import unittest

from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

from tools.jp_short_inline_byte_inventory import (
    CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS,
    CLASS_SPRITE_GRAPHICS_REVIEWS,
    COMPRESSED_RESOURCE_BANK_SOURCE_SHA256,
    COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
    COMPRESSED_RESOURCE_POINTER_TABLE_SHA256,
    COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES,
    ENDING_SCENARIO_STRUCTURED_REVIEWS,
    EXECUTABLE_TAIL_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_TAIL_END,
    EXECUTABLE_TAIL_INSTRUCTION_REVIEWS,
    EXECUTABLE_TAIL_SOURCE_SHA256,
    EXECUTABLE_TAIL_START,
    EXECUTABLE_RENDERER_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_RENDERER_END,
    EXECUTABLE_RENDERER_SOURCE_SHA256,
    EXECUTABLE_RENDERER_START,
    EXECUTABLE_GAMEPLAY_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_GAMEPLAY_GAP_BYTES,
    EXECUTABLE_GAMEPLAY_GAP_END,
    EXECUTABLE_GAMEPLAY_GAP_START,
    EXECUTABLE_GAMEPLAY_SEGMENTS,
    EXECUTABLE_AUXILIARY_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_AUXILIARY_CODE_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_AUXILIARY_CODE_SEGMENTS,
    EXECUTABLE_AUXILIARY_SOURCE_SHA256,
    EXECUTABLE_AUXILIARY_WORD_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_A_CODE_END,
    EXECUTABLE_CORE_A_CODE_SOURCE_SHA256,
    EXECUTABLE_CORE_A_END,
    EXECUTABLE_CORE_A_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_A_SOURCE_SHA256,
    EXECUTABLE_CORE_A_START,
    EXECUTABLE_CORE_A_TABLE_SOURCE_SHA256,
    EXECUTABLE_CORE_B_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_B_END,
    EXECUTABLE_CORE_B_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_B_MARKER_END,
    EXECUTABLE_CORE_B_MARKER_SOURCE_SHA256,
    EXECUTABLE_CORE_B_SOURCE_SHA256,
    EXECUTABLE_CORE_B_START,
    EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_C_CODE_SEGMENTS,
    EXECUTABLE_CORE_C_DATA_SEGMENTS,
    EXECUTABLE_CORE_C_SOURCE_SHA256,
    EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_D_CODE_SEGMENTS,
    EXECUTABLE_CORE_D_DATA_SEGMENTS,
    EXECUTABLE_CORE_D_REFERENCE_INSTRUCTION_OWNERS,
    EXECUTABLE_CORE_D_SOURCE_SHA256,
    EXECUTABLE_CORE_E_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_E_END,
    EXECUTABLE_CORE_E_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_E_RTS_COUNT,
    EXECUTABLE_CORE_E_SOURCE_SHA256,
    EXECUTABLE_CORE_E_START,
    EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_F_CODE_END,
    EXECUTABLE_CORE_F_CODE_SOURCE_SHA256,
    EXECUTABLE_CORE_F_END,
    EXECUTABLE_CORE_F_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_F_PATTERN_REFERENCE,
    EXECUTABLE_CORE_F_PATTERN_SOURCE_SHA256,
    EXECUTABLE_CORE_F_REFERENCE_INSTRUCTION_OWNERS,
    EXECUTABLE_CORE_F_RTS_COUNT,
    EXECUTABLE_CORE_F_SOURCE_SHA256,
    EXECUTABLE_CORE_F_START,
    EXECUTABLE_CORE_G_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_G_CODE_SEGMENTS,
    EXECUTABLE_CORE_G_DATA_REFERENCE_INSTRUCTIONS,
    EXECUTABLE_CORE_G_DATA_SEGMENTS,
    EXECUTABLE_CORE_G_SOURCE_SHA256,
    EXECUTABLE_CORE_H_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_H_CANDIDATE_REFERENCES,
    EXECUTABLE_CORE_H_CODE_END,
    EXECUTABLE_CORE_H_CODE_SOURCE_SHA256,
    EXECUTABLE_CORE_H_END,
    EXECUTABLE_CORE_H_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_H_POINTER_COUNT,
    EXECUTABLE_CORE_H_POINTER_TABLE_REFERENCES,
    EXECUTABLE_CORE_H_POINTER_TABLE_SOURCE_SHA256,
    EXECUTABLE_CORE_H_REFERENCE_INSTRUCTION_OWNERS,
    EXECUTABLE_CORE_H_RTS_COUNT,
    EXECUTABLE_CORE_H_SOURCE_SHA256,
    EXECUTABLE_CORE_H_START,
    EXECUTABLE_CORE_I_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_I_CODE_SEGMENTS,
    EXECUTABLE_CORE_I_DATA_REFERENCE_INSTRUCTIONS,
    EXECUTABLE_CORE_I_DATA_SEGMENTS,
    EXECUTABLE_CORE_I_SOURCE_SHA256,
    EXECUTABLE_CORE_J_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_J_CANDIDATE_REFERENCES,
    EXECUTABLE_CORE_J_END,
    EXECUTABLE_CORE_J_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_J_REFERENCE_INSTRUCTION_OWNERS,
    EXECUTABLE_CORE_J_RTS_COUNT,
    EXECUTABLE_CORE_J_SOURCE_SHA256,
    EXECUTABLE_CORE_J_START,
    EXECUTABLE_CORE_K_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_K_CODE_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_K_CODE_END,
    EXECUTABLE_CORE_K_CODE_SOURCE_SHA256,
    EXECUTABLE_CORE_K_CODE_START,
    EXECUTABLE_CORE_K_DATA_REFERENCE_INSTRUCTIONS,
    EXECUTABLE_CORE_K_DATA_SEGMENTS,
    EXECUTABLE_CORE_K_DECIMAL_VALUES,
    EXECUTABLE_CORE_K_END,
    EXECUTABLE_CORE_K_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_K_PRIMARY_TRANSFER_DESCRIPTORS,
    EXECUTABLE_CORE_K_REGION_COUNTS,
    EXECUTABLE_CORE_K_REGION_POINTERS,
    EXECUTABLE_CORE_K_RTS_COUNT,
    EXECUTABLE_CORE_K_SECONDARY_TRANSFER_DESCRIPTORS,
    EXECUTABLE_CORE_K_SOURCE_SHA256,
    EXECUTABLE_CORE_K_START,
    EXECUTABLE_CORE_L_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_CORE_L_END,
    EXECUTABLE_CORE_L_ENTRY_REFERENCES,
    EXECUTABLE_CORE_L_INSTRUCTION_COUNT,
    EXECUTABLE_CORE_L_RTS_COUNT,
    EXECUTABLE_CORE_L_SOURCE_SHA256,
    EXECUTABLE_CORE_L_START,
    EXECUTABLE_STARTUP_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_STARTUP_CODE_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_STARTUP_CODE_SEGMENTS,
    EXECUTABLE_STARTUP_DATA_CANDIDATE_MANIFEST_SHA256,
    EXECUTABLE_STARTUP_PADDING_SHA256,
    EXECUTABLE_STARTUP_SOURCE_SHA256,
    FONT_BITMAP_BANK_END,
    FONT_BITMAP_BANK_START,
    FONT_BITMAP_GLYPH_BYTES,
    FONT_BITMAP_REPRESENTATIVE_ADDRESSES,
    FONT_BITMAP_SOURCE_SHA256,
    ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS,
    ITEM_NAME_GRAPHICS_REVIEWS,
    SCENARIO_LEVEL_PREFIX,
    SYSTEM_GRAPHICS_ENDING_REVIEWS,
    TEXT_UI_REVIEWS,
    aligned_absolute_references,
    inventory,
    is_word_stream_byte_lane,
    markdown_report,
    pc_relative_lea_pea_references,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
JSON_PATH = ROOT / "localization/short_inline_byte_candidates.json"
MARKDOWN_PATH = ROOT / "docs/short_inline_byte_candidate_inventory.md"


class JapaneseShortInlineByteInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.result = inventory(cls.japanese, KO_ROM.read_bytes())
        cls.font_bank = cls.result["font_bitmap_bank"]
        cls.class_bank = cls.result["class_sprite_graphics_bank"]
        cls.item_bank = cls.result["item_name_graphics_bank"]
        cls.system_bank = cls.result["system_graphics_ending_bank"]
        cls.ending_bank = cls.result["ending_scenario_bank"]
        cls.bank = cls.result["text_ui_bank"]
        cls.compressed_bank = cls.result["compressed_resource_bank"]
        cls.executable_tail_bank = cls.result["executable_tail_bank"]
        cls.executable_renderer_bank = cls.result[
            "executable_renderer_bank"
        ]
        cls.executable_gameplay_bank = cls.result[
            "executable_gameplay_bank"
        ]
        cls.executable_auxiliary_bank = cls.result[
            "executable_auxiliary_bank"
        ]
        cls.executable_startup_bank = cls.result[
            "executable_startup_bank"
        ]
        cls.executable_core_a_bank = cls.result[
            "executable_core_a_bank"
        ]
        cls.executable_core_b_bank = cls.result[
            "executable_core_b_bank"
        ]
        cls.executable_core_c_bank = cls.result[
            "executable_core_c_bank"
        ]
        cls.executable_core_d_bank = cls.result[
            "executable_core_d_bank"
        ]
        cls.executable_core_e_bank = cls.result[
            "executable_core_e_bank"
        ]
        cls.executable_core_f_bank = cls.result[
            "executable_core_f_bank"
        ]
        cls.executable_core_g_bank = cls.result[
            "executable_core_g_bank"
        ]
        cls.executable_core_h_bank = cls.result[
            "executable_core_h_bank"
        ]
        cls.executable_core_i_bank = cls.result[
            "executable_core_i_bank"
        ]
        cls.executable_core_j_bank = cls.result[
            "executable_core_j_bank"
        ]
        cls.executable_core_k_bank = cls.result[
            "executable_core_k_bank"
        ]
        cls.executable_core_l_bank = cls.result[
            "executable_core_l_bank"
        ]

    def test_low_signal_candidate_baseline(self):
        self.assertEqual(self.result["candidate_count"], 6612)
        self.assertEqual(
            self.result["kind_counts"],
            {"ascii": 2177, "halfwidth": 4435},
        )
        self.assertEqual(
            self.result["region_counts"]["halfwidth"]["text_ui_bank"],
            22,
        )
        self.assertEqual(
            self.result["region_counts"]["ascii"]["text_ui_bank"],
            16,
        )

    def test_compressed_resource_bank_is_source_locked_and_fully_classified(self):
        bank = self.compressed_bank
        self.assertEqual(bank["candidate_count"], 3254)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 1014, "halfwidth": 2240},
        )
        self.assertEqual(
            bank["category_counts"],
            {"compressed_resource_payload_false_positive": 3254},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(bank["pointer_table_candidate_addresses"], [])
        self.assertEqual(bank["padding_candidate_addresses"], [])
        self.assertEqual(bank["unowned_candidate_addresses"], [])
        self.assertEqual(bank["resource_count"], 429)
        self.assertEqual(bank["first_resource_pointer"], "0x0B06B4")
        self.assertEqual(bank["last_resource_pointer"], "0x13807E")
        self.assertEqual(bank["last_resource_encoded_end"], "0x138152")
        self.assertEqual(
            bank["source_sha256"], COMPRESSED_RESOURCE_BANK_SOURCE_SHA256
        )
        self.assertEqual(
            bank["pointer_table_sha256"],
            COMPRESSED_RESOURCE_POINTER_TABLE_SHA256,
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["expected_candidate_manifest_sha256"],
            COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])
        self.assertEqual(bank["encoded_payload_bytes"], 555532)
        self.assertEqual(bank["padding_bytes"], 294720)
        self.assertEqual(
            bank["padding_value_counts"],
            {"0x00": 146, "0xFF": 294574},
        )

    def test_compressed_candidates_have_exact_resource_family_ownership(self):
        bank = self.compressed_bank
        self.assertEqual(bank["resource_count_with_candidates"], 373)
        self.assertEqual(
            bank["asset_family_candidate_counts"],
            {
                "battle_background": 221,
                "battle_scene_graphics": 51,
                "battle_ui": 4,
                "character_portrait": 648,
                "combat_sprite": 867,
                "item_icon_graphics": 17,
                "map_tileset": 660,
                "opening_ending_graphics": 729,
                "platform_logo": 1,
                "title_logo_graphics": 17,
                "ui_font": 29,
                "world_map_graphics": 10,
            },
        )
        rows = {
            int(row["address"], 16): row
            for row in bank["representative_candidates"]
        }
        self.assertEqual(
            rows.keys(), COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES
        )
        self.assertEqual(bank["missing_representative_addresses"], [])
        expected = {
            0x0B0739: (0, "platform_logo"),
            0x0B0AF2: (1, "ui_font"),
            0x0B1B49: (2, "map_tileset"),
            0x0C7D7A: (23, "map_tileset"),
            0x0D4410: (47, "combat_sprite"),
            0x0FEBA8: (223, "battle_ui"),
            0x10149D: (231, "character_portrait"),
            0x11E964: (390, "world_map_graphics"),
            0x11FB91: (391, "item_icon_graphics"),
            0x120F0E: (393, "title_logo_graphics"),
            0x121B4F: (394, "opening_ending_graphics"),
        }
        for address, (index, family) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["resource_index"], index)
                self.assertEqual(rows[address]["asset_family"], family)
                self.assertEqual(
                    rows[address]["category"],
                    "compressed_resource_payload_false_positive",
                )
                self.assertTrue(rows[address]["context_words"])

    def test_compressed_candidate_reference_windows_do_not_change_ownership(self):
        bank = self.compressed_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 72)
        self.assertEqual(len(bank["aligned_absolute_32_references"]), 17)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(bank["pc_relative_lea_pea_references"], [])

    def test_executable_tail_is_source_locked_and_fully_classified(self):
        bank = self.executable_tail_bank
        self.assertEqual(bank["candidate_count"], 21)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 6, "halfwidth": 15},
        )
        self.assertEqual(
            bank["category_counts"],
            {
                "instruction_immediate_boundary_false_positive": 17,
                "instruction_opcode_boundary_false_positive": 4,
            },
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(bank["missing_review_addresses"], [])
        self.assertEqual(bank["stale_review_addresses"], [])
        self.assertEqual(bank["source_bytes"], 4256)
        self.assertEqual(bank["source_sha256"], EXECUTABLE_TAIL_SOURCE_SHA256)
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_TAIL_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])
        self.assertTrue(
            all(
                row["instruction_bytes_valid"]
                and row["candidate_inside_instruction"]
                for row in bank["candidates"]
            )
        )

    def test_executable_tail_candidates_map_to_contiguous_68000_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[EXECUTABLE_TAIL_START:EXECUTABLE_TAIL_END],
                EXECUTABLE_TAIL_START,
            )
        )
        self.assertEqual(len(instructions), 699)
        self.assertEqual(instructions[0].address, EXECUTABLE_TAIL_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_TAIL_END,
        )
        by_candidate = {
            int(row["address"], 16): row
            for row in self.executable_tail_bank["candidates"]
        }
        self.assertEqual(
            set(by_candidate), set(EXECUTABLE_TAIL_INSTRUCTION_REVIEWS)
        )
        for address, (instruction_address, expected_hex) in (
            EXECUTABLE_TAIL_INSTRUCTION_REVIEWS.items()
        ):
            with self.subTest(address=f"0x{address:06X}"):
                matches = [
                    instruction
                    for instruction in instructions
                    if instruction.address
                    <= address
                    < instruction.address + instruction.size
                ]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].address, instruction_address)
                self.assertEqual(
                    matches[0].bytes.hex(" ").upper(), expected_hex
                )
                self.assertEqual(
                    by_candidate[address]["instruction_address"],
                    f"0x{instruction_address:06X}",
                )

    def test_executable_tail_candidates_have_no_exact_reference(self):
        bank = self.executable_tail_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in bank["candidates"]
            )
        )

    def test_executable_renderer_is_source_locked_and_fully_classified(self):
        bank = self.executable_renderer_bank
        self.assertEqual(bank["candidate_count"], 108)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 36, "halfwidth": 72},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 108},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(bank["source_bytes"], 16440)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_RENDERER_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_RENDERER_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_renderer_candidates_are_inside_contiguous_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_RENDERER_START:EXECUTABLE_RENDERER_END
                ],
                EXECUTABLE_RENDERER_START,
            )
        )
        self.assertEqual(len(instructions), 3451)
        self.assertEqual(instructions[0].address, EXECUTABLE_RENDERER_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_RENDERER_END,
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in self.executable_renderer_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(
                    set(range(start, end)) <= covered_bytes
                )

    def test_executable_renderer_exact_references_are_code_entry_points(self):
        bank = self.executable_renderer_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 37)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x02C311: [0x0DF0E0],
                0x02D188: [0x02D16C],
                0x02DC40: [
                    0x02E0B6,
                    0x02FF98,
                    0x030934,
                    0x030976,
                ],
                0x02DCC2: [
                    0x02E026,
                    0x02E06E,
                    0x02E290,
                    0x02E30A,
                    0x02E352,
                    0x02E39A,
                    0x02FC82,
                    0x02FCD4,
                    0x02FD40,
                    0x02FDF6,
                    0x02FE50,
                    0x02FEBE,
                    0x02FFA6,
                    0x030030,
                    0x0300F2,
                    0x030158,
                    0x0301AA,
                    0x0302E0,
                    0x030362,
                    0x030426,
                    0x0304B2,
                    0x030586,
                    0x0305F8,
                    0x0306AA,
                    0x03078C,
                    0x03080C,
                    0x030882,
                    0x0309CC,
                    0x030AA4,
                    0x030AF4,
                    0x030B44,
                ],
            },
        )

    def test_executable_gameplay_is_source_locked_and_fully_classified(self):
        bank = self.executable_gameplay_bank
        self.assertEqual(bank["candidate_count"], 228)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 21, "halfwidth": 207},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 228},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_GAMEPLAY_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])
        gap = bank["numeric_table_gap"]
        self.assertEqual(
            gap["range"],
            (
                f"0x{EXECUTABLE_GAMEPLAY_GAP_START:06X}.."
                f"0x{EXECUTABLE_GAMEPLAY_GAP_END:06X}"
            ),
        )
        self.assertEqual(gap["source_bytes"], len(EXECUTABLE_GAMEPLAY_GAP_BYTES))
        self.assertEqual(
            gap["raw_hex"],
            EXECUTABLE_GAMEPLAY_GAP_BYTES.hex(" ").upper(),
        )
        self.assertEqual(gap["candidate_count"], 0)
        self.assertTrue(gap["source_layout_valid"])

    def test_executable_gameplay_candidates_are_inside_contiguous_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        covered_bytes = set()
        summaries = self.executable_gameplay_bank["segments"]
        self.assertEqual(len(summaries), len(EXECUTABLE_GAMEPLAY_SEGMENTS))
        for summary, (
            start,
            end,
            instruction_count,
            source_sha256,
        ) in zip(summaries, EXECUTABLE_GAMEPLAY_SEGMENTS):
            with self.subTest(segment=summary["range"]):
                instructions = list(
                    md.disasm(self.japanese[start:end], start)
                )
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(summary["source_sha256"], source_sha256)
                self.assertTrue(summary["source_layout_valid"])
                covered_bytes.update(
                    address
                    for instruction in instructions
                    for address in range(
                        instruction.address,
                        instruction.address + instruction.size,
                    )
                )
        for row in self.executable_gameplay_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_gameplay_reference_windows_are_odd_instruction_bytes(self):
        bank = self.executable_gameplay_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 7)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x020223: [0x12285C],
                0x0221E1: [0x0FDB46, 0x0FE0F4],
                0x0222F3: [0x059030],
                0x022921: [0x05D29C],
                0x024525: [0x057C92],
                0x02A555: [0x0E624E],
            },
        )
        self.assertTrue(
            all(
                row["target_is_odd"]
                for row in bank["aligned_absolute_32_references"]
            )
        )

    def test_executable_auxiliary_is_source_locked_and_fully_classified(self):
        bank = self.executable_auxiliary_bank
        self.assertEqual(bank["candidate_count"], 127)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 48, "halfwidth": 79},
        )
        self.assertEqual(
            bank["category_counts"],
            {
                "contiguous_instruction_stream_false_positive": 123,
                "pointer_indexed_16bit_word_stream_false_positive": 4,
            },
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_AUXILIARY_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_AUXILIARY_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_AUXILIARY_CODE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["word_candidate_manifest_sha256"],
            EXECUTABLE_AUXILIARY_WORD_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_auxiliary_code_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        summaries = self.executable_auxiliary_bank["code_segments"]
        self.assertEqual(len(summaries), len(EXECUTABLE_AUXILIARY_CODE_SEGMENTS))
        covered_bytes = set()
        expected_candidate_counts = [21, 16, 13, 2, 71]
        for summary, segment, candidate_count in zip(
            summaries,
            EXECUTABLE_AUXILIARY_CODE_SEGMENTS,
            expected_candidate_counts,
        ):
            (
                start,
                end,
                instruction_count,
                source_sha256,
                candidate_manifest_sha256,
            ) = segment
            with self.subTest(segment=summary["range"]):
                instructions = list(
                    md.disasm(self.japanese[start:end], start)
                )
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(summary["source_sha256"], source_sha256)
                self.assertEqual(
                    summary["candidate_manifest_sha256"],
                    candidate_manifest_sha256,
                )
                self.assertEqual(
                    summary["candidate_count"], candidate_count
                )
                self.assertTrue(summary["source_layout_valid"])
                covered_bytes.update(
                    address
                    for instruction in instructions
                    for address in range(
                        instruction.address,
                        instruction.address + instruction.size,
                    )
                )
        code_rows = [
            row
            for row in self.executable_auxiliary_bank["candidates"]
            if row["category"]
            == "contiguous_instruction_stream_false_positive"
        ]
        self.assertEqual(len(code_rows), 123)
        for row in code_rows:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_auxiliary_word_candidates_have_pointer_ownership(self):
        bank = self.executable_auxiliary_bank
        table = bank["word_pointer_table"]
        self.assertEqual(table["pointer_count"], 38)
        self.assertEqual(table["unique_pointer_count"], 36)
        self.assertEqual(table["first_pointer"], "0x0010FE")
        self.assertEqual(table["last_pointer"], "0x00118A")
        self.assertEqual(table["minimum_pointer"], "0x0010FE")
        self.assertEqual(table["maximum_pointer"], "0x0012E8")
        word_rows = {
            int(row["address"], 16): row
            for row in bank["candidates"]
            if row["category"]
            == "pointer_indexed_16bit_word_stream_false_positive"
        }
        self.assertEqual(
            set(word_rows),
            {0x001113, 0x00115B, 0x00116B, 0x00120B},
        )
        for row in word_rows.values():
            with self.subTest(address=row["address"]):
                self.assertEqual(row["containing_word"], "0x004A")
                self.assertEqual(row["following_word"], "0xFFFF")
                self.assertIsNotNone(row["record_start"])
                self.assertTrue(row["pointer_entries"])

    def test_executable_auxiliary_reference_windows_are_structural(self):
        bank = self.executable_auxiliary_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 17)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x0004AC: [
                    0x08223A,
                    0x0822BA,
                    0x08233A,
                    0x0823BA,
                    0x08243A,
                    0x097BC6,
                ],
                0x000A00: [
                    0x05F1F0,
                    0x0602BC,
                    0x0602D6,
                    0x060324,
                    0x060358,
                    0x080B66,
                ],
                0x000A08: [0x05F784],
                0x001113: [0x05714E],
                0x003839: [0x0A5C50],
                0x004555: [0x0B3570, 0x0B5EC6],
            },
        )

    def test_executable_startup_is_source_locked_and_fully_classified(self):
        bank = self.executable_startup_bank
        self.assertEqual(bank["candidate_count"], 41)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 2, "halfwidth": 39},
        )
        self.assertEqual(
            bank["category_counts"],
            {
                "contiguous_instruction_stream_false_positive": 40,
                "startup_configuration_table_false_positive": 1,
            },
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_STARTUP_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_STARTUP_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_STARTUP_CODE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["data_candidate_manifest_sha256"],
            EXECUTABLE_STARTUP_DATA_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_startup_code_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        summaries = self.executable_startup_bank["code_segments"]
        self.assertEqual(len(summaries), len(EXECUTABLE_STARTUP_CODE_SEGMENTS))
        expected_candidate_counts = [6, 17, 1, 13, 3]
        covered_bytes = set()
        for summary, segment, candidate_count in zip(
            summaries,
            EXECUTABLE_STARTUP_CODE_SEGMENTS,
            expected_candidate_counts,
        ):
            (
                start,
                end,
                instruction_count,
                source_sha256,
                candidate_manifest_sha256,
            ) = segment
            with self.subTest(segment=summary["range"]):
                instructions = list(
                    md.disasm(self.japanese[start:end], start)
                )
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(summary["source_sha256"], source_sha256)
                self.assertEqual(
                    summary["candidate_manifest_sha256"],
                    candidate_manifest_sha256,
                )
                self.assertEqual(
                    summary["candidate_count"], candidate_count
                )
                self.assertTrue(summary["source_layout_valid"])
                covered_bytes.update(
                    address
                    for instruction in instructions
                    for address in range(
                        instruction.address,
                        instruction.address + instruction.size,
                    )
                )
        code_rows = [
            row
            for row in self.executable_startup_bank["candidates"]
            if row["category"]
            == "contiguous_instruction_stream_false_positive"
        ]
        self.assertEqual(len(code_rows), 40)
        for row in code_rows:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_startup_data_tables_and_padding_are_locked(self):
        bank = self.executable_startup_bank
        padding = bank["preceding_ff_padding"]
        self.assertEqual(padding["source_bytes"], 8748)
        self.assertEqual(
            padding["source_sha256"], EXECUTABLE_STARTUP_PADDING_SHA256
        )
        self.assertTrue(padding["all_ff"])
        self.assertEqual(padding["candidate_count"], 0)
        self.assertEqual(
            [row["candidate_count"] for row in bank["data_segments"]],
            [1, 0, 0, 0],
        )
        self.assertTrue(
            all(row["source_layout_valid"] for row in bank["data_segments"])
        )
        data_rows = [
            row
            for row in bank["candidates"]
            if row["category"]
            == "startup_configuration_table_false_positive"
        ]
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0]["address"], "0x008101")
        self.assertEqual(data_rows[0]["raw_hex"], "BF DF")
        self.assertEqual(
            data_rows[0]["owner"],
            "startup hardware/register configuration table",
        )

    def test_executable_startup_reference_windows_are_odd_instruction_bytes(self):
        bank = self.executable_startup_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 3)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x008049: [0x088B48],
                0x008283: [0x0E3516],
                0x008601: [0x11BED8],
            },
        )
        self.assertTrue(
            all(
                row["target_is_odd"]
                for row in bank["aligned_absolute_32_references"]
            )
        )

    def test_executable_core_a_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_a_bank
        self.assertEqual(bank["candidate_count"], 67)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 11, "halfwidth": 56},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 67},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_A_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_segment"]["source_sha256"],
            EXECUTABLE_CORE_A_CODE_SOURCE_SHA256,
        )
        self.assertEqual(
            bank["code_segment"]["candidate_manifest_sha256"],
            EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["dispatch_table"]["source_sha256"],
            EXECUTABLE_CORE_A_TABLE_SOURCE_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_a_candidates_are_inside_exact_instructions(self):
        bank = self.executable_core_a_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_A_START:EXECUTABLE_CORE_A_CODE_END
                ],
                EXECUTABLE_CORE_A_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_A_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_A_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_A_CODE_END,
        )
        self.assertEqual(instructions[-1].mnemonic, "rts")
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)
        table = bank["dispatch_table"]
        self.assertEqual(
            table["range"],
            (
                f"0x{EXECUTABLE_CORE_A_CODE_END:06X}.."
                f"0x{EXECUTABLE_CORE_A_END:06X}"
            ),
        )
        self.assertEqual(table["source_bytes"], 10)
        self.assertEqual(table["raw_hex"], "00 30 00 48 02 20 04 0E 00 BA")
        self.assertEqual(table["candidate_count"], 0)

    def test_executable_core_a_candidate_reference_windows_are_empty(self):
        bank = self.executable_core_a_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertTrue(
            all(
                row["aligned_absolute_32_references"] == []
                and row["pc_relative_lea_pea_references"] == []
                for row in bank["candidates"]
            )
        )

    def test_executable_core_b_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_b_bank
        self.assertEqual(bank["candidate_count"], 174)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 19, "halfwidth": 155},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 174},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_B_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_B_CANDIDATE_MANIFEST_SHA256,
        )
        marker = bank["following_ascii_marker"]
        self.assertEqual(
            marker["source_sha256"],
            EXECUTABLE_CORE_B_MARKER_SOURCE_SHA256,
        )
        self.assertEqual(
            marker["raw_ascii"],
            "LOADSAVECONTINUESCENARIONOTHING !",
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_b_candidates_are_inside_exact_instructions(self):
        bank = self.executable_core_b_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_B_START:EXECUTABLE_CORE_B_END
                ],
                EXECUTABLE_CORE_B_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_B_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_B_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_B_END,
        )
        self.assertEqual(instructions[-1].mnemonic, "rts")
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)
        marker = bank["following_ascii_marker"]
        self.assertEqual(
            marker["range"],
            (
                f"0x{EXECUTABLE_CORE_B_END:06X}.."
                f"0x{EXECUTABLE_CORE_B_MARKER_END:06X}"
            ),
        )
        self.assertEqual(marker["source_bytes"], 33)

    def test_executable_core_b_candidate_reference_windows_are_structural(self):
        bank = self.executable_core_b_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 1)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {0x00A0CF: [0x100F2A]},
        )
        self.assertTrue(
            all(
                row["target_is_odd"]
                for row in bank["aligned_absolute_32_references"]
            )
        )

    def test_executable_core_c_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_c_bank
        self.assertEqual(bank["candidate_count"], 85)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 45, "halfwidth": 40},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 85},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_C_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_c_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        summaries = self.executable_core_c_bank["code_segments"]
        self.assertEqual(len(summaries), len(EXECUTABLE_CORE_C_CODE_SEGMENTS))
        expected_candidate_counts = [3, 82]
        covered_bytes = set()
        instruction_starts = set()
        for summary, segment, candidate_count in zip(
            summaries,
            EXECUTABLE_CORE_C_CODE_SEGMENTS,
            expected_candidate_counts,
        ):
            (
                start,
                end,
                instruction_count,
                source_sha256,
                candidate_manifest_sha256,
            ) = segment
            with self.subTest(segment=summary["range"]):
                instructions = list(
                    md.disasm(self.japanese[start:end], start)
                )
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(summary["source_sha256"], source_sha256)
                self.assertEqual(
                    summary["candidate_manifest_sha256"],
                    candidate_manifest_sha256,
                )
                self.assertEqual(
                    summary["candidate_count"], candidate_count
                )
                self.assertTrue(summary["source_layout_valid"])
                instruction_starts.update(
                    instruction.address for instruction in instructions
                )
                covered_bytes.update(
                    address
                    for instruction in instructions
                    for address in range(
                        instruction.address,
                        instruction.address + instruction.size,
                    )
                )
        for row in self.executable_core_c_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)
        self.assertTrue({0x00DA2A, 0x00FA28} <= instruction_starts)

    def test_executable_core_c_data_and_reference_ownership_is_locked(self):
        bank = self.executable_core_c_bank
        self.assertEqual(
            len(bank["data_segments"]),
            len(EXECUTABLE_CORE_C_DATA_SEGMENTS),
        )
        self.assertEqual(
            [row["candidate_count"] for row in bank["data_segments"]],
            [0, 0],
        )
        self.assertTrue(
            all(row["source_layout_valid"] for row in bank["data_segments"])
        )
        self.assertEqual(
            bank["layout_record_pointer_table"]["pointers"],
            [
                "0x00FD5E",
                "0x00FD76",
                "0x00FD94",
                "0x00FDB2",
                "0x00FDD0",
                "0x00FDEE",
                "0x00FE0C",
            ],
        )
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 2)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x00DA2A: [0x00DA18],
                0x00FA28: [0x00D780],
            },
        )
        self.assertTrue(
            all(
                not row["target_is_odd"]
                for row in bank["aligned_absolute_32_references"]
            )
        )

    def test_executable_core_d_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_d_bank
        self.assertEqual(bank["candidate_count"], 102)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 17, "halfwidth": 85},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 102},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_D_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_d_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        summaries = self.executable_core_d_bank["code_segments"]
        self.assertEqual(len(summaries), len(EXECUTABLE_CORE_D_CODE_SEGMENTS))
        expected_candidate_counts = [28, 4, 48, 19, 3]
        covered_bytes = set()
        for summary, segment, candidate_count in zip(
            summaries,
            EXECUTABLE_CORE_D_CODE_SEGMENTS,
            expected_candidate_counts,
        ):
            (
                start,
                end,
                instruction_count,
                source_sha256,
                candidate_manifest_sha256,
            ) = segment
            with self.subTest(segment=summary["range"]):
                instructions = list(
                    md.disasm(self.japanese[start:end], start)
                )
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(summary["source_sha256"], source_sha256)
                self.assertEqual(
                    summary["candidate_manifest_sha256"],
                    candidate_manifest_sha256,
                )
                self.assertEqual(
                    summary["candidate_count"], candidate_count
                )
                self.assertTrue(summary["source_layout_valid"])
                covered_bytes.update(
                    address
                    for instruction in instructions
                    for address in range(
                        instruction.address,
                        instruction.address + instruction.size,
                    )
                )
        for row in self.executable_core_d_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_d_data_and_reference_ownership_is_locked(self):
        bank = self.executable_core_d_bank
        self.assertEqual(
            len(bank["data_segments"]),
            len(EXECUTABLE_CORE_D_DATA_SEGMENTS),
        )
        self.assertEqual(
            [row["candidate_count"] for row in bank["data_segments"]],
            [0, 0, 0, 0, 0],
        )
        self.assertTrue(
            all(row["source_layout_valid"] for row in bank["data_segments"])
        )
        self.assertEqual(
            bank["decimal_place_values"],
            [10000, 1000, 100, 10, 1],
        )
        self.assertEqual(
            bank["numeric_record_pointer_table"]["pointers"],
            [
                "0x01095A",
                "0x010970",
                "0x010986",
                "0x01099C",
                "0x0109B2",
                "0x0109C8",
                "0x0109DE",
                "0x0109F4",
                "0x010A0A",
                "0x010A20",
            ],
        )
        self.assertEqual(bank["layout_record_count"], 14)
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 35)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x00FFED: [0x0874B2],
                0x010003: [
                    0x0109DE,
                    0x095386,
                    0x0A38A6,
                    0x0DA57A,
                    0x0EBD88,
                    0x0EBE0E,
                    0x0EDB36,
                    0x107110,
                    0x11E446,
                    0x12C5A6,
                ],
                0x010017: [
                    0x014540,
                    0x0170A4,
                    0x09E542,
                    0x09EC1C,
                ],
                0x010027: [
                    0x0011F0,
                    0x0905D6,
                    0x090684,
                    0x0906CA,
                    0x0907CA,
                    0x0908F8,
                    0x090BE0,
                    0x090DBE,
                    0x090F84,
                    0x091164,
                    0x0911D4,
                    0x091D46,
                    0x091F22,
                    0x092352,
                    0x09742C,
                    0x09B406,
                    0x09D4D0,
                    0x0A3458,
                    0x0A3522,
                    0x0A3614,
                ],
            },
        )
        self.assertEqual(
            {
                int(row["target"], 16)
                for row in bank["reference_instruction_owners"]
            },
            set(EXECUTABLE_CORE_D_REFERENCE_INSTRUCTION_OWNERS),
        )
        self.assertTrue(
            all(
                row["target_is_odd"] and row["source_layout_valid"]
                for row in bank["reference_instruction_owners"]
            )
        )

    def test_executable_core_e_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_e_bank
        self.assertEqual(bank["candidate_count"], 24)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 4, "halfwidth": 20},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 24},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_E_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_E_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_e_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[EXECUTABLE_CORE_E_START:EXECUTABLE_CORE_E_END],
                EXECUTABLE_CORE_E_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_E_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_E_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_E_END,
        )
        self.assertEqual(instructions[-1].mnemonic, "rts")
        self.assertEqual(
            sum(instruction.mnemonic == "rts" for instruction in instructions),
            EXECUTABLE_CORE_E_RTS_COUNT,
        )
        self.assertFalse(
            any(instruction.mnemonic == "dc.w" for instruction in instructions)
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in self.executable_core_e_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_e_has_no_candidate_target_references(self):
        bank = self.executable_core_e_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in bank["candidates"]
            )
        )

    def test_executable_core_f_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_f_bank
        self.assertEqual(bank["candidate_count"], 189)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 17, "halfwidth": 172},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 189},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_F_SOURCE_SHA256
        )
        self.assertEqual(
            bank["code_segment"]["source_sha256"],
            EXECUTABLE_CORE_F_CODE_SOURCE_SHA256,
        )
        self.assertEqual(
            bank["pattern_table"]["source_sha256"],
            EXECUTABLE_CORE_F_PATTERN_SOURCE_SHA256,
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["data_candidate_manifest_sha256"],
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(bank["pattern_table"]["candidate_count"], 0)
        self.assertEqual(
            bank["pattern_table"]["values"],
            [0x01DD, 0x01DE, 0x01DF, 0x01ED, 0x01EE, 0x01EF,
             0x01FD, 0x01FE, 0x01FF],
        )
        self.assertEqual(
            bank["pattern_table"]["aligned_absolute_32_references"],
            [f"0x{EXECUTABLE_CORE_F_PATTERN_REFERENCE:06X}"],
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_f_candidates_are_inside_exact_instructions(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_F_START:EXECUTABLE_CORE_F_CODE_END
                ],
                EXECUTABLE_CORE_F_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_F_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_F_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_F_CODE_END,
        )
        self.assertEqual(instructions[-1].mnemonic, "bra.w")
        self.assertEqual(
            sum(instruction.mnemonic == "rts" for instruction in instructions),
            EXECUTABLE_CORE_F_RTS_COUNT,
        )
        self.assertFalse(
            any(instruction.mnemonic == "dc.w" for instruction in instructions)
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in self.executable_core_f_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_f_reference_targets_are_instruction_owned(self):
        bank = self.executable_core_f_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 27)
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in bank["aligned_absolute_32_references"]
            },
            {
                0x01381D: [0x00B83E, 0x017B34],
                0x014DA6: [
                    0x014DA0,
                    0x014E60,
                    0x014F3A,
                    0x01507A,
                    0x0151E8,
                    0x0152E8,
                    0x015542,
                    0x015642,
                    0x0157EE,
                ],
                0x014E75: [
                    0x001524,
                    0x01089E,
                    0x0108C4,
                    0x013B10,
                    0x013C12,
                    0x013CAE,
                    0x013F78,
                    0x013FFC,
                    0x01A9B8,
                    0x01A9C2,
                    0x01AC52,
                    0x01AC60,
                    0x01B032,
                    0x01B03C,
                    0x01B094,
                    0x01B0A2,
                ],
            },
        )
        self.assertEqual(
            {
                int(row["target"], 16)
                for row in bank["reference_instruction_owners"]
            },
            set(EXECUTABLE_CORE_F_REFERENCE_INSTRUCTION_OWNERS),
        )
        self.assertEqual(
            {
                int(row["target"], 16)
                for row in bank["reference_instruction_owners"]
                if row["target_is_instruction_start"]
            },
            {0x014DA6},
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["reference_instruction_owners"]
            )
        )
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_g_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_g_bank
        self.assertEqual(bank["candidate_count"], 35)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 2, "halfwidth": 33},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 35},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_G_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_G_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_G_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["data_candidate_manifest_sha256"],
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855",
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_g_code_segments_are_exact(self):
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        covered_bytes = set()
        self.assertEqual(
            len(self.executable_core_g_bank["code_segments"]),
            len(EXECUTABLE_CORE_G_CODE_SEGMENTS),
        )
        for start, end, instruction_count, rts_count, _, _ in (
            EXECUTABLE_CORE_G_CODE_SEGMENTS
        ):
            instructions = list(md.disasm(self.japanese[start:end], start))
            with self.subTest(range=f"0x{start:06X}..0x{end:06X}"):
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(
                    sum(
                        instruction.mnemonic == "rts"
                        for instruction in instructions
                    ),
                    rts_count,
                )
                self.assertFalse(
                    any(
                        instruction.mnemonic == "dc.w"
                        for instruction in instructions
                    )
                )
            covered_bytes.update(
                address
                for instruction in instructions
                for address in range(
                    instruction.address,
                    instruction.address + instruction.size,
                )
            )
        for row in self.executable_core_g_bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_g_data_records_and_references_are_exact(self):
        bank = self.executable_core_g_bank
        self.assertEqual(
            len(bank["data_segments"]),
            len(EXECUTABLE_CORE_G_DATA_SEGMENTS),
        )
        self.assertTrue(
            all(
                row["candidate_count"] == 0
                and row["source_layout_valid"]
                for row in bank["data_segments"]
            )
        )
        self.assertEqual(bank["indexed_lookup_hex"], "6B 6C FD 00")
        self.assertEqual(bank["selection_label"], "ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ")
        self.assertEqual(bank["page_label"], "PAGE")
        self.assertEqual(
            len(bank["data_reference_instructions"]),
            len(EXECUTABLE_CORE_G_DATA_REFERENCE_INSTRUCTIONS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["data_reference_instructions"]
            )
        )
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_h_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_h_bank
        self.assertEqual(bank["candidate_count"], 18)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 2, "halfwidth": 16},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 18},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_H_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_H_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_H_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["pointer_table_candidate_manifest_sha256"],
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855",
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_h_code_stream_is_exact(self):
        bank = self.executable_core_h_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_H_START:EXECUTABLE_CORE_H_CODE_END
                ],
                EXECUTABLE_CORE_H_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_H_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_H_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_H_CODE_END,
        )
        self.assertEqual(
            sum(
                instruction.mnemonic == "rts"
                for instruction in instructions
            ),
            EXECUTABLE_CORE_H_RTS_COUNT,
        )
        self.assertFalse(
            any(
                instruction.mnemonic == "dc.w"
                for instruction in instructions
            )
        )
        self.assertEqual(
            bank["code_segment"]["source_sha256"],
            EXECUTABLE_CORE_H_CODE_SOURCE_SHA256,
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_h_pointer_table_and_references_are_exact(self):
        bank = self.executable_core_h_bank
        table = bank["pointer_table"]
        self.assertEqual(
            table["range"],
            (
                f"0x{EXECUTABLE_CORE_H_CODE_END:06X}.."
                f"0x{EXECUTABLE_CORE_H_END:06X}"
            ),
        )
        self.assertEqual(
            table["source_sha256"],
            EXECUTABLE_CORE_H_POINTER_TABLE_SOURCE_SHA256,
        )
        self.assertEqual(table["candidate_count"], 0)
        self.assertEqual(table["pointer_count"], EXECUTABLE_CORE_H_POINTER_COUNT)
        self.assertTrue(table["all_even"])
        self.assertEqual(table["minimum"], "0x018C3A")
        self.assertEqual(table["maximum"], "0x01A126")
        self.assertEqual(
            table["pointers"][:5],
            ["0x018C3A", "0x018CB8", "0x018E58", "0x018F60", "0x018F88"],
        )
        self.assertEqual(
            table["pointers"][-5:],
            ["0x019FBE", "0x01A126", "0x0191C8", "0x019BAA", "0x019008"],
        )
        self.assertEqual(
            table["aligned_absolute_32_references"],
            [
                f"0x{address:06X}"
                for address in EXECUTABLE_CORE_H_POINTER_TABLE_REFERENCES
            ],
        )
        self.assertEqual(
            {
                int(row["target"], 16): tuple(
                    int(address, 16) for address in row["addresses"]
                )
                for row in bank["aligned_absolute_32_references"]
            },
            EXECUTABLE_CORE_H_CANDIDATE_REFERENCES,
        )
        self.assertEqual(
            {
                int(row["target"], 16)
                for row in bank["reference_instruction_owners"]
            },
            set(EXECUTABLE_CORE_H_REFERENCE_INSTRUCTION_OWNERS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["reference_instruction_owners"]
            )
        )
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_i_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_i_bank
        self.assertEqual(bank["candidate_count"], 42)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 9, "halfwidth": 33},
        )
        self.assertEqual(
            bank["category_counts"],
            {
                "contiguous_instruction_stream_false_positive": 19,
                "numeric_lookup_table_false_positive": 23,
            },
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_I_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_I_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_i_code_segments_are_exact(self):
        bank = self.executable_core_i_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        covered_bytes = set()
        self.assertEqual(
            len(bank["code_segments"]),
            len(EXECUTABLE_CORE_I_CODE_SEGMENTS),
        )
        for start, end, instruction_count, rts_count, _, _ in (
            EXECUTABLE_CORE_I_CODE_SEGMENTS
        ):
            instructions = list(md.disasm(self.japanese[start:end], start))
            with self.subTest(range=f"0x{start:06X}..0x{end:06X}"):
                self.assertEqual(len(instructions), instruction_count)
                self.assertEqual(instructions[0].address, start)
                self.assertEqual(
                    instructions[-1].address + instructions[-1].size,
                    end,
                )
                self.assertEqual(
                    sum(
                        instruction.mnemonic == "rts"
                        for instruction in instructions
                    ),
                    rts_count,
                )
                self.assertFalse(
                    any(
                        instruction.mnemonic == "dc.w"
                        for instruction in instructions
                    )
                )
            covered_bytes.update(
                address
                for instruction in instructions
                for address in range(
                    instruction.address,
                    instruction.address + instruction.size,
                )
            )
        for row in bank["candidates"]:
            if row["category"] != (
                "contiguous_instruction_stream_false_positive"
            ):
                continue
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_i_numeric_tables_and_references_are_exact(self):
        bank = self.executable_core_i_bank
        self.assertEqual(
            len(bank["data_segments"]),
            len(EXECUTABLE_CORE_I_DATA_SEGMENTS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["data_segments"]
            )
        )
        self.assertEqual(
            bank["numeric_lookup_values"],
            [5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 0]
            + [0] * 11,
        )
        self.assertEqual(bank["trigonometric_value_count"], 271)
        self.assertEqual(bank["trigonometric_minimum"], -255)
        self.assertEqual(bank["trigonometric_maximum"], 256)
        self.assertEqual(
            len(bank["data_reference_instructions"]),
            len(EXECUTABLE_CORE_I_DATA_REFERENCE_INSTRUCTIONS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["data_reference_instructions"]
            )
        )
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_j_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_j_bank
        self.assertEqual(bank["candidate_count"], 69)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 3, "halfwidth": 66},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 69},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_J_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_J_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_j_code_stream_is_exact(self):
        bank = self.executable_core_j_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_J_START:EXECUTABLE_CORE_J_END
                ],
                EXECUTABLE_CORE_J_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_J_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_J_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_J_END,
        )
        self.assertEqual(
            sum(
                instruction.mnemonic == "rts"
                for instruction in instructions
            ),
            EXECUTABLE_CORE_J_RTS_COUNT,
        )
        self.assertFalse(
            any(
                instruction.mnemonic == "dc.w"
                for instruction in instructions
            )
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_j_candidate_reference_is_instruction_internal(self):
        bank = self.executable_core_j_bank
        self.assertEqual(
            {
                int(row["target"], 16): tuple(
                    int(address, 16) for address in row["addresses"]
                )
                for row in bank["aligned_absolute_32_references"]
            },
            EXECUTABLE_CORE_J_CANDIDATE_REFERENCES,
        )
        self.assertEqual(
            {
                int(row["target"], 16)
                for row in bank["reference_instruction_owners"]
            },
            set(EXECUTABLE_CORE_J_REFERENCE_INSTRUCTION_OWNERS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["reference_instruction_owners"]
            )
        )
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_k_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_k_bank
        self.assertEqual(bank["candidate_count"], 10)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 4, "halfwidth": 6},
        )
        self.assertEqual(
            bank["category_counts"],
            {
                "contiguous_instruction_stream_false_positive": 6,
                "structured_numeric_record_false_positive": 4,
            },
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_K_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_K_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["code_candidate_manifest_sha256"],
            EXECUTABLE_CORE_K_CODE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])

    def test_executable_core_k_code_stream_is_exact(self):
        bank = self.executable_core_k_bank
        code = bank["code_segment"]
        self.assertEqual(
            code["source_sha256"], EXECUTABLE_CORE_K_CODE_SOURCE_SHA256
        )
        self.assertTrue(code["source_layout_valid"])
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_K_CODE_START:EXECUTABLE_CORE_K_CODE_END
                ],
                EXECUTABLE_CORE_K_CODE_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_K_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_K_CODE_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_K_CODE_END,
        )
        self.assertEqual(instructions[-1].mnemonic, "rts")
        self.assertEqual(
            sum(
                instruction.mnemonic == "rts"
                for instruction in instructions
            ),
            EXECUTABLE_CORE_K_RTS_COUNT,
        )
        self.assertFalse(
            any(
                instruction.mnemonic == "dc.w"
                for instruction in instructions
            )
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            if row["category"] != (
                "contiguous_instruction_stream_false_positive"
            ):
                continue
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_executable_core_k_structured_tables_and_references_are_exact(self):
        bank = self.executable_core_k_bank
        self.assertEqual(
            len(bank["data_segments"]),
            len(EXECUTABLE_CORE_K_DATA_SEGMENTS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["data_segments"]
            )
        )
        self.assertEqual(
            tuple(bank["decimal_place_values"]),
            EXECUTABLE_CORE_K_DECIMAL_VALUES,
        )
        self.assertEqual(
            tuple(bank["region_element_counts"]),
            EXECUTABLE_CORE_K_REGION_COUNTS,
        )
        self.assertEqual(
            tuple(
                int(pointer, 16)
                for pointer in bank["region_start_pointers"]
            ),
            EXECUTABLE_CORE_K_REGION_POINTERS,
        )
        self.assertEqual(
            tuple(
                (int(row["address"], 16), row["count"])
                for row in bank["primary_transfer_descriptors"]
            ),
            EXECUTABLE_CORE_K_PRIMARY_TRANSFER_DESCRIPTORS,
        )
        self.assertEqual(
            tuple(
                (int(row["address"], 16), row["count"])
                for row in bank["secondary_transfer_descriptors"]
            ),
            EXECUTABLE_CORE_K_SECONDARY_TRANSFER_DESCRIPTORS,
        )
        self.assertTrue(bank["primary_descriptor_terminated"])
        self.assertTrue(bank["secondary_descriptor_terminated"])
        self.assertEqual(
            len(bank["data_reference_instructions"]),
            len(EXECUTABLE_CORE_K_DATA_REFERENCE_INSTRUCTIONS),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["data_reference_instructions"]
            )
        )
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_l_is_source_locked_and_fully_classified(self):
        bank = self.executable_core_l_bank
        self.assertEqual(bank["candidate_count"], 140)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 3, "halfwidth": 137},
        )
        self.assertEqual(
            bank["category_counts"],
            {"contiguous_instruction_stream_false_positive": 140},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(
            bank["source_sha256"], EXECUTABLE_CORE_L_SOURCE_SHA256
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            EXECUTABLE_CORE_L_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])
        self.assertEqual(
            len(bank["entry_reference_instructions"]),
            len(EXECUTABLE_CORE_L_ENTRY_REFERENCES),
        )
        self.assertTrue(
            all(
                row["source_layout_valid"]
                for row in bank["entry_reference_instructions"]
            )
        )
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(bank["aligned_absolute_32_references"], [])
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)

    def test_executable_core_l_code_stream_is_exact(self):
        bank = self.executable_core_l_bank
        md = Cs(
            CS_ARCH_M68K,
            CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000,
        )
        instructions = list(
            md.disasm(
                self.japanese[
                    EXECUTABLE_CORE_L_START:EXECUTABLE_CORE_L_END
                ],
                EXECUTABLE_CORE_L_START,
            )
        )
        self.assertEqual(len(instructions), EXECUTABLE_CORE_L_INSTRUCTION_COUNT)
        self.assertEqual(instructions[0].address, EXECUTABLE_CORE_L_START)
        self.assertEqual(
            instructions[-1].address + instructions[-1].size,
            EXECUTABLE_CORE_L_END,
        )
        self.assertEqual(
            sum(
                instruction.mnemonic == "rts"
                for instruction in instructions
            ),
            EXECUTABLE_CORE_L_RTS_COUNT,
        )
        self.assertFalse(
            any(
                instruction.mnemonic == "dc.w"
                for instruction in instructions
            )
        )
        covered_bytes = {
            address
            for instruction in instructions
            for address in range(
                instruction.address,
                instruction.address + instruction.size,
            )
        }
        for row in bank["candidates"]:
            with self.subTest(address=row["address"]):
                start = int(row["address"], 16)
                end = int(row["end"], 16)
                self.assertTrue(set(range(start, end)) <= covered_bytes)

    def test_font_bitmap_bank_is_source_locked_and_fully_classified(self):
        self.assertEqual(self.font_bank["candidate_count"], 1477)
        self.assertEqual(
            self.font_bank["kind_counts"],
            {"ascii": 762, "halfwidth": 715},
        )
        self.assertEqual(
            self.font_bank["category_counts"],
            {"font_bitmap_false_positive": 1477},
        )
        self.assertEqual(self.font_bank["unclassified_count"], 0)
        self.assertEqual(
            self.font_bank["glyph_count"],
            (FONT_BITMAP_BANK_END - FONT_BITMAP_BANK_START)
            // FONT_BITMAP_GLYPH_BYTES,
        )
        self.assertEqual(
            self.font_bank["source_sha256"], FONT_BITMAP_SOURCE_SHA256
        )
        self.assertEqual(
            self.font_bank["expected_source_sha256"],
            FONT_BITMAP_SOURCE_SHA256,
        )
        self.assertTrue(self.font_bank["source_layout_valid"])
        self.assertEqual(
            self.font_bank["candidate_manifest_sha256"],
            "f5763ec3ad9d40cf8e5ae135b9ccae984847a1aca9f388121ba17502a011b956",
        )

    def test_font_bitmap_representatives_have_exact_pixel_ownership(self):
        rows = {
            int(row["address"], 16): row
            for row in self.font_bank["representative_candidates"]
        }
        self.assertEqual(rows.keys(), FONT_BITMAP_REPRESENTATIVE_ADDRESSES)
        self.assertEqual(
            self.font_bank["missing_representative_addresses"], []
        )
        for address, row in rows.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(
                    row["category"], "font_bitmap_false_positive"
                )
                self.assertEqual(
                    row["glyph_index"],
                    (address - FONT_BITMAP_BANK_START)
                    // FONT_BITMAP_GLYPH_BYTES,
                )
                self.assertEqual(
                    row["glyph_byte_offset"],
                    (address - FONT_BITMAP_BANK_START)
                    % FONT_BITMAP_GLYPH_BYTES,
                )
                self.assertTrue(row["context_words"])

    def test_font_bitmap_reference_windows_do_not_change_bitmap_ownership(self):
        self.assertEqual(
            self.font_bank["aligned_absolute_32_reference_count"], 32
        )
        self.assertEqual(
            self.font_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in self.font_bank[
                    "aligned_absolute_32_references"
                ]
            },
            {
                0x043143: [
                    0x00C2F2,
                    0x01BA16,
                    0x01BA5A,
                    0x01BAAA,
                    0x01C170,
                    0x01C21C,
                ],
                0x04322E: [0x003BEC, 0x00571A],
                0x044A69: [0x001936],
                0x044CDF: [
                    0x00857A,
                    0x00B732,
                    0x011846,
                    0x011C64,
                    0x013678,
                    0x0139FC,
                    0x0155A8,
                    0x018A0C,
                    0x018A72,
                    0x01A9B4,
                    0x01AA00,
                    0x01ABC2,
                    0x01AC5C,
                    0x01B038,
                ],
                0x047001: [
                    0x00B3FC,
                    0x00C33A,
                    0x00CCEE,
                    0x00D260,
                    0x02A02C,
                ],
                0x04B428: [0x012D96],
                0x04C149: [0x01AE00],
                0x04E241: [0x0034B0, 0x01B1B4],
            },
        )

    def test_class_sprite_graphics_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.class_bank["candidate_count"], 62)
        self.assertEqual(
            self.class_bank["category_counts"],
            {
                "class_pointer_table_boundary_false_positive": 1,
                "commander_sprite_mapping_false_positive": 4,
                "packed_sprite_graphics_false_positive": 57,
            },
        )
        self.assertEqual(self.class_bank["unclassified_count"], 0)
        self.assertEqual(self.class_bank["missing_review_addresses"], [])
        self.assertEqual(self.class_bank["stale_review_addresses"], [])

    def test_class_sprite_graphics_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.class_bank["candidates"]
        }
        self.assertEqual(rows, set(CLASS_SPRITE_GRAPHICS_REVIEWS))

    def test_class_sprite_graphics_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.class_bank["candidates"]
        }
        expected = {
            0x050019: (
                "AB",
                "0xF4AB",
                "packed_sprite_graphics_false_positive",
            ),
            0x05DD02: (
                "41",
                "0x41FF",
                "commander_sprite_mapping_false_positive",
            ),
            0x05DDA7: (
                "47",
                "0x0047",
                "commander_sprite_mapping_false_positive",
            ),
            0x05E949: (
                "D4 20 20 20 20 20 20 20 20",
                "0xEDD4",
                "class_pointer_table_boundary_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_class_sprite_apparent_references_are_reviewed_non_pointers(self):
        self.assertEqual(
            self.class_bank["aligned_absolute_32_reference_count"], 2
        )
        self.assertEqual(
            self.class_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            self.class_bank["missing_aligned_reference_reviews"], []
        )
        self.assertEqual(
            self.class_bank["stale_aligned_reference_reviews"], []
        )
        rows = {
            (int(row["target"], 16), int(row["address"], 16)): row
            for row in self.class_bank["aligned_reference_reviews"]
        }
        self.assertEqual(
            set(rows), set(CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
        )
        self.assertEqual(
            rows[(0x050019, 0x01CAA2)]["classification"],
            "cross_operand_window",
        )
        self.assertEqual(
            rows[(0x050019, 0x095398)]["classification"],
            "coincidental_data_window",
        )

    def test_item_name_graphics_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.item_bank["candidate_count"], 83)
        self.assertEqual(
            self.item_bank["category_counts"],
            {
                "name_pointer_table_boundary_false_positive": 1,
                "packed_game_graphics_false_positive": 7,
                "packed_tile_sprite_graphics_false_positive": 75,
            },
        )
        self.assertEqual(self.item_bank["unclassified_count"], 0)
        self.assertEqual(self.item_bank["missing_review_addresses"], [])
        self.assertEqual(self.item_bank["stale_review_addresses"], [])

    def test_item_name_graphics_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.item_bank["candidates"]
        }
        self.assertEqual(rows, set(ITEM_NAME_GRAPHICS_REVIEWS))

    def test_item_name_graphics_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.item_bank["candidates"]
        }
        expected = {
            0x060D35: (
                "4F",
                "0x244F",
                "packed_game_graphics_false_positive",
            ),
            0x061ABB: (
                "BC 20 20 20 20 20 20 20 20",
                "0x1ABC",
                "name_pointer_table_boundary_false_positive",
            ),
            0x06EFF1: (
                "CC CF",
                "0xEFCC",
                "packed_tile_sprite_graphics_false_positive",
            ),
            0x070C2A: (
                "57 58",
                "0x5758",
                "packed_tile_sprite_graphics_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_item_name_graphics_apparent_references_are_reviewed_non_pointers(self):
        self.assertEqual(
            self.item_bank["aligned_absolute_32_reference_count"], 3
        )
        self.assertEqual(
            self.item_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            self.item_bank["missing_aligned_reference_reviews"], []
        )
        self.assertEqual(
            self.item_bank["stale_aligned_reference_reviews"], []
        )
        rows = {
            (int(row["target"], 16), int(row["address"], 16)): row
            for row in self.item_bank["aligned_reference_reviews"]
        }
        self.assertEqual(
            set(rows), set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
        )
        self.assertEqual(
            rows[(0x06121F, 0x0A4440)]["classification"],
            "coincidental_data_window",
        )
        self.assertEqual(
            rows[(0x070C2A, 0x01F0A6)]["classification"],
            "cross_instruction_window",
        )
        self.assertEqual(
            rows[(0x070C2A, 0x01F1A8)]["classification"],
            "cross_instruction_window",
        )

    def test_system_graphics_ending_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.system_bank["candidate_count"], 80)
        self.assertEqual(
            self.system_bank["category_counts"],
            {
                "ending_selector_false_positive": 7,
                "packed_tile_resource_false_positive": 7,
                "structured_graphics_false_positive": 53,
                "word_stream_byte_false_positive": 13,
            },
        )
        self.assertEqual(self.system_bank["unclassified_count"], 0)
        self.assertEqual(self.system_bank["missing_review_addresses"], [])
        self.assertEqual(
            self.system_bank["stale_structured_review_addresses"],
            [],
        )

    def test_system_bank_word_stream_rows_end_at_known_controls(self):
        rows = [
            row
            for row in self.system_bank["candidates"]
            if row["category"] == "word_stream_byte_false_positive"
        ]
        self.assertEqual(len(rows), 13)
        for row in rows:
            with self.subTest(address=row["address"]):
                self.assertTrue(
                    is_word_stream_byte_lane(
                        self.japanese,
                        int(row["address"], 16),
                        int(row["end"], 16),
                    )
                )

    def test_system_bank_structured_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.system_bank["candidates"]
            if row["category"] != "word_stream_byte_false_positive"
        }
        self.assertEqual(rows, set(SYSTEM_GRAPHICS_ENDING_REVIEWS))

    def test_system_bank_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.system_bank["candidates"]
        }
        expected = {
            0x082ACB: (
                "C2",
                "0x00C2",
                "word_stream_byte_false_positive",
            ),
            0x084401: (
                "45 46 2E 2E 2E",
                "0x0E45",
                "packed_tile_resource_false_positive",
            ),
            0x08721B: (
                "CE",
                "0xFFCE",
                "structured_graphics_false_positive",
            ),
            0x089286: (
                "B6 D8",
                "0xB6D8",
                "ending_selector_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_system_bank_candidates_have_no_exact_reference(self):
        self.assertEqual(
            self.system_bank["aligned_absolute_32_reference_count"], 0
        )
        self.assertEqual(
            self.system_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in self.system_bank["candidates"]
            )
        )

    def test_ending_scenario_bank_has_one_retained_ui_and_no_unknown(self):
        self.assertEqual(self.ending_bank["candidate_count"], 138)
        self.assertEqual(
            self.ending_bank["category_counts"],
            {
                "retained_compact_english_ui": 1,
                "structured_layout_false_positive": 21,
                "word_stream_byte_false_positive": 116,
            },
        )
        self.assertEqual(self.ending_bank["unclassified_count"], 0)
        self.assertEqual(self.ending_bank["missing_review_addresses"], [])
        self.assertEqual(
            self.ending_bank["stale_structured_review_addresses"],
            [],
        )

    def test_ending_scenario_word_stream_rows_end_at_known_controls(self):
        rows = [
            row
            for row in self.ending_bank["candidates"]
            if row["category"] == "word_stream_byte_false_positive"
        ]
        self.assertEqual(len(rows), 116)
        for row in rows:
            with self.subTest(address=row["address"]):
                self.assertTrue(
                    is_word_stream_byte_lane(
                        self.japanese,
                        int(row["address"], 16),
                        int(row["end"], 16),
                    )
                )

    def test_ending_scenario_structured_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.ending_bank["candidates"]
            if row["category"] == "structured_layout_false_positive"
        }
        self.assertEqual(rows, set(ENDING_SCENARIO_STRUCTURED_REVIEWS))

    def test_scenario_level_prefix_is_retained_compact_ui(self):
        rows = {
            int(row["address"], 16): row
            for row in self.ending_bank["candidates"]
        }
        row = rows[SCENARIO_LEVEL_PREFIX]
        self.assertEqual(row["original_text"], "L-")
        self.assertEqual(row["raw_hex"], "4C 2D")
        self.assertEqual(row["category"], "retained_compact_english_ui")
        self.assertEqual(row["aligned_absolute_32_references"], ["0x025CDE"])
        self.assertEqual(row["pc_relative_lea_pea_references"], [])
        self.assertEqual(
            self.ending_bank["aligned_absolute_32_reference_count"], 1
        )
        self.assertEqual(
            self.ending_bank["pc_relative_lea_pea_reference_count"], 0
        )

        prefix = self.ending_bank["retained_level_prefix"]
        self.assertEqual(prefix["source_bytes"], "4C 2D FF")
        self.assertEqual(prefix["current_bytes"], "4C 2D FF")
        self.assertEqual(prefix["hook_bytes"], "41 F9 00 09 B2 E7")
        self.assertTrue(prefix["source_hook_valid"])
        self.assertTrue(prefix["current_hook_preserved"])
        self.assertTrue(prefix["current_record_preserved"])
        self.assertTrue(prefix["live_verified"])
        self.assertTrue((ROOT / prefix["evidence"]).exists())

    def test_every_text_ui_bank_candidate_has_an_exact_review(self):
        rows = {int(row["address"], 16): row for row in self.bank["candidates"]}
        self.assertEqual(set(rows), set(TEXT_UI_REVIEWS))
        self.assertEqual(self.bank["candidate_count"], 38)
        self.assertEqual(self.bank["unclassified_count"], 0)
        self.assertEqual(self.bank["missing_review_addresses"], [])
        self.assertEqual(self.bank["stale_review_addresses"], [])
        self.assertEqual(
            self.bank["category_counts"],
            {
                "structured_layout_false_positive": 10,
                "word_stream_byte_false_positive": 28,
            },
        )

    def test_reviewed_examples_preserve_containing_word_evidence(self):
        rows = {row["address"]: row for row in self.bank["candidates"]}
        expected = {
            "0x0A1427": (
                "CE",
                "0x00CE",
                "structured_layout_false_positive",
            ),
            "0x0A3161": (
                "54",
                "0x0054",
                "word_stream_byte_false_positive",
            ),
            "0x0A4A36": (
                "A7",
                "0xA7FF",
                "structured_layout_false_positive",
            ),
            "0x0A6F27": (
                "AA",
                "0x00AA",
                "word_stream_byte_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=address):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_reviewed_candidates_have_no_exact_reference(self):
        self.assertEqual(self.bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(self.bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in self.bank["candidates"]
            )
        )

    def test_reference_scanners_find_synthetic_exact_targets(self):
        data = bytearray(32)
        target = 16
        data[0:4] = target.to_bytes(4, "big")
        self.assertEqual(aligned_absolute_references(bytes(data), {target}), {16: [0]})

        data = bytearray(32)
        data[0:4] = bytes.fromhex("41 FA 00 0E")
        data[4:8] = bytes.fromhex("48 7A 00 0A")
        references = pc_relative_lea_pea_references(bytes(data), {target})
        self.assertEqual(
            [(row["instruction"], row["address"]) for row in references[target]],
            [("LEA", 0), ("PEA", 4)],
        )

    def test_generated_reports_match(self):
        self.assertEqual(
            json.loads(JSON_PATH.read_text(encoding="utf-8")),
            self.result,
        )
        self.assertEqual(
            MARKDOWN_PATH.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
