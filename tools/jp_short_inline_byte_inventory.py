#!/usr/bin/env python3
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.jp_inline_byte_string_inventory import SCAN_END, scan_runs
from tools.jp_compressed_resource_inventory import (
    RESOURCE_TABLE,
    asset_family,
    resource_encoded_end,
    resource_pointers,
)


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EXECUTABLE_END = 0x040000
FONT_BITMAP_BANK_START = 0x040000
FONT_BITMAP_BANK_END = 0x050000
FONT_BITMAP_GLYPH_BYTES = 64
FONT_BITMAP_SOURCE_SHA256 = (
    "665c71c0bcd73a3a097f181d84eb3f4022e32f9c37628bcb22a840025433b5ed"
)
FONT_BITMAP_REPRESENTATIVE_ADDRESSES = {
    0x040285,
    0x043143,
    0x04322E,
    0x044CDF,
    0x047001,
    0x04E241,
    0x04FDDE,
}
CLASS_SPRITE_GRAPHICS_BANK_START = 0x050000
CLASS_SPRITE_GRAPHICS_BANK_END = 0x060000
ITEM_NAME_GRAPHICS_BANK_START = 0x060000
ITEM_NAME_GRAPHICS_BANK_END = 0x080000
SYSTEM_GRAPHICS_ENDING_BANK_START = 0x080000
SYSTEM_GRAPHICS_ENDING_BANK_END = 0x090000
ENDING_SCENARIO_BANK_START = 0x090000
ENDING_SCENARIO_BANK_END = 0x0A0000
TEXT_UI_BANK_START = 0x0A0000
TEXT_UI_BANK_END = 0x0B0000
COMPRESSED_RESOURCE_BANK_START = RESOURCE_TABLE
COMPRESSED_RESOURCE_BANK_END = SCAN_END
COMPRESSED_RESOURCE_BANK_SOURCE_SHA256 = (
    "9c906c718b449f3b5288e115bc804e0fd30c26991eb7b4777ab84f76632d1163"
)
COMPRESSED_RESOURCE_POINTER_TABLE_SHA256 = (
    "3a319874035415d264944f87faa897a8d84d95390173d27fc76447f31862528b"
)
COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256 = (
    "f0c731570dea4403306522bc4422efb1b51943d422f712476bc5cf63dffcf995"
)
COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES = {
    0x0B0739,
    0x0B0AF2,
    0x0B1B49,
    0x0C7D7A,
    0x0D4410,
    0x0FEBA8,
    0x10149D,
    0x11E964,
    0x11FB91,
    0x120F0E,
    0x121B4F,
}
EXECUTABLE_TAIL_START = 0x030000
EXECUTABLE_TAIL_END = 0x0310A0
EXECUTABLE_TAIL_SOURCE_SHA256 = (
    "6fcf21965cccf311dbf8b8a14d1afc215f00e9d289e1a254865a678ba1c2b6d8"
)
EXECUTABLE_TAIL_CANDIDATE_MANIFEST_SHA256 = (
    "2a39fe8e38ee8f746d0321cab98ef4f7339433cf191b6292721b4bfa1aeceda3"
)
EXECUTABLE_TAIL_INSTRUCTION_REVIEWS = {
    0x0300DB: (0x0300D8, "33 FC 00 C0 FF FF F3 70"),
    0x03012D: (0x030128, "23 FC 00 0A 3F A2 FF FF F3 7C"),
    0x03017F: (0x03017A, "23 FC 00 0A 3F C6 FF FF F3 7C"),
    0x03018B: (0x030188, "33 FC E5 A4 FF FF F3 64"),
    0x0302C9: (0x0302C8, "33 C0 FF FF F3 70"),
    0x0303E5: (0x0303E2, "33 FC 00 B4 FF FF F3 4A"),
    0x0303FB: (0x0303F6, "23 FC 00 0A 40 4A FF FF F3 7C"),
    0x03040F: (0x03040C, "33 FC 00 C0 FF FF F3 70"),
    0x030487: (0x030482, "23 FC 00 0A 40 A4 FF FF F3 7C"),
    0x03056F: (0x03056C, "33 FC 00 C0 FF FF F3 70"),
    0x030693: (0x030690, "33 FC 00 D0 FF FF F3 70"),
    0x03073B: (0x030738, "33 FC 00 5A FF FF F3 4A"),
    0x030775: (0x030774, "33 C0 FF FF F3 70"),
    0x030856: (0x030852, "23 FC 00 0A 41 46 FF FF F3 7C"),
    0x03091D: (0x03091A, "33 FC 00 D0 FF FF F3 70"),
    0x030957: (0x030954, "33 FC E5 48 FF FF F3 64"),
    0x030A53: (0x030A50, "33 FC 00 5A FF FF F3 4A"),
    0x030A8D: (0x030A8C, "33 C0 FF FF F3 70"),
    0x030B03: (0x030B00, "33 FC 00 B4 FF FF F3 4A"),
    0x030B19: (0x030B14, "23 FC 00 0A 41 A8 FF FF F3 7C"),
    0x03109A: (0x03109A, "42 39 FF FF F3 77"),
}
EXECUTABLE_TAIL_OPCODE_BOUNDARY_ADDRESSES = {
    0x0302C9,
    0x030775,
    0x030A8D,
    0x03109A,
}
EXECUTABLE_RENDERER_START = 0x02BFC8
EXECUTABLE_RENDERER_END = 0x030000
EXECUTABLE_RENDERER_SOURCE_SHA256 = (
    "edb590da0da63058e15da20aff12b3ec185ca9ba699f255212e62ac4ff1b5797"
)
EXECUTABLE_RENDERER_CANDIDATE_MANIFEST_SHA256 = (
    "7617dc0672ad2a47e0bacf10051a5ccd12f7c7060d5b7bfad103f58bc1c0c805"
)
EXECUTABLE_GAMEPLAY_SEGMENTS = (
    (
        0x020000,
        0x02A19C,
        10094,
        "c01b6c215be237c758a5fd6c6c7d923e0da926818c8cdf49e77838536fe045cd",
    ),
    (
        0x02A1B0,
        0x02BFC8,
        1754,
        "4343cc0a8786c911aa4b59e76c2b6e962f179fe25657e54f1849086db9ad787e",
    ),
)
EXECUTABLE_GAMEPLAY_GAP_START = 0x02A19C
EXECUTABLE_GAMEPLAY_GAP_END = 0x02A1B0
EXECUTABLE_GAMEPLAY_GAP_BYTES = bytes.fromhex(
    "27 10 03 E8 00 64 00 0A 00 01 00 07 04 00 08 00 80 00 20 00"
)
EXECUTABLE_GAMEPLAY_CANDIDATE_MANIFEST_SHA256 = (
    "749a6c28493c0907e733a997745f3d035e1ed6834ae4cb96021c42efae31263d"
)
EXECUTABLE_GAMEPLAY_SEGMENT_CANDIDATE_MANIFEST_SHA256 = {
    (0x020000, 0x02A19C): (
        "a369a4971c6d87976375e82372c28125096f69aa47bdb54be99c171b5205ae96"
    ),
    (0x02A1B0, 0x02BFC8): (
        "0d82f38f8a23c0225df88de3c6b731387dd940bba06947c91591349dd03a150c"
    ),
}
EXECUTABLE_AUXILIARY_START = 0x000270
EXECUTABLE_AUXILIARY_END = 0x005DD4
EXECUTABLE_AUXILIARY_SOURCE_SHA256 = (
    "d1ae52bac4f581a1064838c465d4165b88c71e6c60e4c07f48fe8e68a525a8d7"
)
EXECUTABLE_AUXILIARY_CANDIDATE_MANIFEST_SHA256 = (
    "95c704b17e29e1f400c8d048880b31820174df7083dbdd61d6caa8c0dd1270cb"
)
EXECUTABLE_AUXILIARY_CODE_CANDIDATE_MANIFEST_SHA256 = (
    "b9462ee081d305a2e43ec944835a3b3606596126be4d91562fa861ee678f8d3d"
)
EXECUTABLE_AUXILIARY_WORD_CANDIDATE_MANIFEST_SHA256 = (
    "842d384c439d3299bb9a02dc5932b011956ec94a0c17ed9b161f9cfec33054f0"
)
EXECUTABLE_AUXILIARY_CODE_SEGMENTS = (
    (
        0x000270,
        0x00090C,
        399,
        "ef247174565f4d28fcface0980b5622c6da9e37573e794435465c009088b21be",
        "7d81628127fa8ccbdaf960ef0252614b2b1dd6d8fd27181de45be2d9f636b670",
    ),
    (
        0x000916,
        0x001066,
        452,
        "01718f697efff2689ce6315c1130cdd42b38d2d67954d499e784a70516a77c89",
        "a984633763f4b095290434be9eb564994c9b5e49d2c92c84dd72e368bc50db52",
    ),
    (
        0x0012F6,
        0x001770,
        333,
        "dcb7f997e0ad83c2d07b7807b1036fa9d67e4aa0dd1b9fb7e1e5d66352a8a5bc",
        "be2425c3a9d309473996a9cc3f14e3144b2c5c40f19ad6fd7eb0af3579eacd72",
    ),
    (
        0x001788,
        0x001D9A,
        430,
        "42a30d50b91e90c6438658e58e8c0fb9065fdaff09d7ef8c4979070d29a10ff8",
        "92a59080fde758aa5b1132322035c171f3c11f60601202d96f57f0167a72766d",
    ),
    (
        0x001DA6,
        0x005DD4,
        4176,
        "2ac368f7baae23c6892262f8cb1ed5654fc4b37c4d3b0692c46c904b9009b9b7",
        "c8b8167a72f70590be31c64de2d3e9a22cc818b0f2de4b3e4b445c6a5f278bcc",
    ),
)
EXECUTABLE_AUXILIARY_DATA_SEGMENTS = (
    (
        0x00090C,
        0x000916,
        "byte lookup table",
        "c34811b4832cf38c15f83e94fc16032990157f40f1ae61f750b4611ac8625cc1",
    ),
    (
        0x001066,
        0x0012F6,
        "pointer-indexed 16-bit word records",
        "6a268783c273e671a0a6311a309c4fa6245de0c6f0a4d2569901fd6a5a98943d",
    ),
    (
        0x001770,
        0x001788,
        "16-bit code-offset table",
        "1983371e27eeac98e0805be367f5469417857328b44ef1d245b7aed58e6f50fa",
    ),
    (
        0x001D9A,
        0x001DA6,
        "16-bit code-offset table",
        "222c75b94c4717a1b4fe6d4d06b67117127613bed7a7b1c05b3a2141b5ad08e9",
    ),
)
EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_START = 0x001066
EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_END = 0x0010FE
EXECUTABLE_AUXILIARY_WORD_RECORD_START = 0x0010FE
EXECUTABLE_AUXILIARY_WORD_RECORD_END = 0x0012F6
EXECUTABLE_STARTUP_PADDING_START = 0x005DD4
EXECUTABLE_STARTUP_START = 0x008000
EXECUTABLE_STARTUP_END = 0x008F4E
EXECUTABLE_STARTUP_PADDING_SHA256 = (
    "efbb843b08b0ee9f83c721907ce3d853bdfc16378357c0d82f644ed4f1d30913"
)
EXECUTABLE_STARTUP_SOURCE_SHA256 = (
    "21083420fa6207834d7410193a3148bd1843b61b8802e79a2bee618970e8406a"
)
EXECUTABLE_STARTUP_CANDIDATE_MANIFEST_SHA256 = (
    "1a1af1e7e551c373c9e75c22bc7c8e9bd2eb851774b23bdcdad34fff563d005d"
)
EXECUTABLE_STARTUP_CODE_CANDIDATE_MANIFEST_SHA256 = (
    "1282c6309cae702bd5a14b779a15be85da269a67c754b8f0242b22c753cf0360"
)
EXECUTABLE_STARTUP_DATA_CANDIDATE_MANIFEST_SHA256 = (
    "853b7b9d4ef2e4fcea270ce5fa06fe7b42cb35c0cbde6c6cceefbd8694bff400"
)
EXECUTABLE_STARTUP_CODE_SEGMENTS = (
    (
        0x008000,
        0x00809A,
        55,
        "ce1724cf9b267c4923b3aa558a7e97ec1bca4d4bb087e1ecc4eb6be7b025eff3",
        "432172d8a96ad7d6a16d615c6c642f5cfd6c0f364d5887005d5297c63f625204",
    ),
    (
        0x008104,
        0x00861C,
        287,
        "a161e90bbeb36058bc8e725302766a3a1bde2a801222192b234d21ff7a03a90e",
        "5482c226b10733a21a18244a03d99bfb63bc51b1b41bb45d4a33487b24b4cee4",
    ),
    (
        0x00866C,
        0x00868E,
        10,
        "e731ba9ada61f65120bf4e7bb7c9b657956fe0e8d7654a51bf2fea579198a3aa",
        "2c74f0d69971100a61a7820d93d94df4e3c08f450986c5ae778504ff50d75ced",
    ),
    (
        0x0086B4,
        0x008B0E,
        295,
        "197c0818a23184fe36de773950cdecb357cd732c5d340b3c6835018ed4e9b853",
        "fd19637634c28c1c86404702a1c28b23bfc8ca82872500f3a59bf0a90c8c104f",
    ),
    (
        0x008B24,
        0x008F4E,
        393,
        "afeeff1180047d9a134181551166c4dabe278e99fe63acfa289765759408e23a",
        "f7622f3ade40c7181e733ffd7d3743deccfae86def8389bd783b2a74a0b6859b",
    ),
)
EXECUTABLE_STARTUP_DATA_SEGMENTS = (
    (
        0x00809A,
        0x008104,
        "startup hardware/register configuration table",
        "0e7ed0e76239d6ebf0961fdee838efa526cbd722670f91758d80748246d57932",
        "853b7b9d4ef2e4fcea270ce5fa06fe7b42cb35c0cbde6c6cceefbd8694bff400",
    ),
    (
        0x00861C,
        0x00866C,
        "startup button and input bit-mask tables",
        "73b549daddddfe9ffde0a1873bd330caca5d9bcbdab8a9213f1b0116967480b8",
        EMPTY_SHA256,
    ),
    (
        0x00868E,
        0x0086B4,
        "startup indexed 16-bit configuration records",
        "ab35a810740431c5b0b4f02760b650e988d96e947d44b0c9860a672d6652ea61",
        EMPTY_SHA256,
    ),
    (
        0x008B0E,
        0x008B24,
        "indexed jump-table 16-bit offsets",
        "933223c8098848974610a8845b253eb4b929f4dd6739e767d7ecd66b9666525a",
        EMPTY_SHA256,
    ),
)
EXECUTABLE_CORE_A_START = 0x008F4E
EXECUTABLE_CORE_A_CODE_END = 0x0099F0
EXECUTABLE_CORE_A_END = 0x0099FA
EXECUTABLE_CORE_A_SOURCE_SHA256 = (
    "822ea425d6fb92e0d1686aacd19e138a52e5b6560d2b8f0a57d7a20865420384"
)
EXECUTABLE_CORE_A_CODE_SOURCE_SHA256 = (
    "85f6868fa9cb4ad3e5c1c28abf98277abff2a932bae62d1f5736e9b471ed97cf"
)
EXECUTABLE_CORE_A_TABLE_SOURCE_SHA256 = (
    "ccde039e43d027c427414cdd2213be9e863f78e1be0c1b601162794cb749d2f3"
)
EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256 = (
    "6a06784c5a2d07c753844dee2ff201553785de3c44b9c303ddb2f2d97ed83d64"
)
EXECUTABLE_CORE_A_INSTRUCTION_COUNT = 742
EXECUTABLE_CORE_B_START = 0x0099FA
EXECUTABLE_CORE_B_END = 0x00D47E
EXECUTABLE_CORE_B_MARKER_END = 0x00D49F
EXECUTABLE_CORE_B_SOURCE_SHA256 = (
    "79034afb5b8b33a9d06d6ce209bbd2df5edb514cc5bceeed8bc09a7589403f0e"
)
EXECUTABLE_CORE_B_MARKER_SOURCE_SHA256 = (
    "928c52fe19267c02951cacbc21167fc40c0b8a874936b226887355eb94340692"
)
EXECUTABLE_CORE_B_CANDIDATE_MANIFEST_SHA256 = (
    "6bf6db8d02acea60f7a01868dec1e2fb967cdd8ad7771cb560e43ed7cd35897c"
)
EXECUTABLE_CORE_B_INSTRUCTION_COUNT = 3980
EXECUTABLE_CORE_C_START = 0x00D49E
EXECUTABLE_CORE_C_END = 0x00FE28
EXECUTABLE_CORE_C_SOURCE_SHA256 = (
    "d1913fc42d1ee942998c90be00824691f635964f647a81820b41690b6d65e27e"
)
EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256 = (
    "67dff3bcfc092e79e36c70607523ac284d1fefafea989cf1f8075c997032e715"
)
EXECUTABLE_CORE_C_CODE_SEGMENTS = (
    (
        0x00D49E,
        0x00D7B6,
        131,
        "6b7ebd588cba655e2e4ec510d782f5f1883c72d4e85bf9d03b7d3293d0ab5f41",
        "714cb3fc51f67442311f70beba165d2b8cfed019607a9291b8aa58e8fb985b32",
    ),
    (
        0x00D7D6,
        0x00FD42,
        2133,
        "6f9f0b9ba0634b2ea7830d4e4291538873f061c9f8591bba776e5ce542535dbc",
        "e62a9871ba1b9424987a86cede0593402380bd9bcd89faf7189aa4873698b3ab",
    ),
)
EXECUTABLE_CORE_C_DATA_SEGMENTS = (
    (
        0x00D7B6,
        0x00D7D6,
        "input and selection pattern table",
        "ee1e957def3d929d8965253f6b14049258f15b72a3fa938d1c190fdbe368b282",
    ),
    (
        0x00FD42,
        0x00FE28,
        "seven-pointer layout-record table",
        "250ee5465c85e58924609b7f2ed6d4cbd0cab3050e36e9a4d71e7103a38ed155",
    ),
)
EXECUTABLE_CORE_D_START = 0x00FE28
EXECUTABLE_CORE_D_END = 0x011FC8
EXECUTABLE_CORE_D_SOURCE_SHA256 = (
    "06eeb2fbee39f135e077893dc876854395a2772eb599558783b5b8db95550f3a"
)
EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256 = (
    "8c9852d9b2c340b8b9ca95877a64fcc2f4d4c5de0cf449bc89b5377ebf7a51ab"
)
EXECUTABLE_CORE_D_CODE_SEGMENTS = (
    (
        0x00FE28,
        0x0106EC,
        555,
        "618f2711e8d7d1cc2464f4deac820ddc66e3f07cbf9f7da1ce952490715a0bca",
        "f218dc7736ba1f55691f1037dc8e55752b4f2153207af1db6442eb626057e953",
    ),
    (
        0x0106F6,
        0x010932,
        156,
        "ce3d6560e1b081a11ce13f92fdd873c9b1266d66315f847a4b4850a598963e36",
        "4d7398fad92d26546817cbd6910d84c7daee258a631faf719ee9d69a4d50255e",
    ),
    (
        0x010A34,
        0x01179E,
        930,
        "42716efc78ac6c0bcdca2df8fd539287d60647384ea38adcfbb4a4f14fe7fa8e",
        "e2bcaab1ae92ad1c71f01cb53a1c3c51565d8f6e0bade940e5107c0c05ccd094",
    ),
    (
        0x0117AE,
        0x011EBA,
        434,
        "d99cadb143d42389fcacd63f6b4bf97184d57717ee1de92805b88ed6063b22e4",
        "d00e8597397de7564d2f7a1c3673a23e44e888e95aa83dc97a1c5fc1d52ec5fd",
    ),
    (
        0x011F46,
        0x011FA8,
        29,
        "6ea709b158dfba50fae83ec76342f025d60ceeaf413284d767ac40fe466be37d",
        "f6a23bba19f1daf02dbd0358392b3f9c2a8d9838600788d7b3a142ed11523663",
    ),
)
EXECUTABLE_CORE_D_DATA_SEGMENTS = (
    (
        0x0106EC,
        0x0106F6,
        "decimal place-value table",
        "b8456acf5b863805584ae3ddd08fa48936a9d75a821eaf39fe4e09080cb7c1ca",
    ),
    (
        0x010932,
        0x010A34,
        "ten-pointer numeric-record table",
        "cf6b8495b1faff6e3c4788c35dea07630b985dcf8bdc44e27fa52e5554d3150d",
    ),
    (
        0x01179E,
        0x0117AE,
        "bit and direction pattern table",
        "9495ccc78ccca6f4ee5d3836675805a8c7c17ff86d1ede18076eee8a25f6c133",
    ),
    (
        0x011EBA,
        0x011F46,
        "fourteen ten-byte layout records",
        "88667c472e04944f5138caee6de922dc50bb7750d3e20b079a1682ce490b8fb4",
    ),
    (
        0x011FA8,
        0x011FC8,
        "configuration and numeric table",
        "0f9728d816d2e4cf5d45e9cd47e3a9429226212fac9a448716af3af50f96352a",
    ),
)
EXECUTABLE_CORE_D_REFERENCE_INSTRUCTION_OWNERS = {
    0x00FFED: (0x00FFEC, 0x00FFF0, "DBRA D1,$FFEA", "51 C9 FF FC"),
    0x010003: (
        0x010002,
        0x010008,
        "MOVE.W D0,$FFFFA70A.L",
        "33 C0 FF FF A7 0A",
    ),
    0x010017: (
        0x010016,
        0x01001C,
        "MOVE.B D0,$FFFFA7F4.L",
        "13 C0 FF FF A7 F4",
    ),
    0x010027: (
        0x010026,
        0x01002C,
        "MOVE.B D1,$FFFFA7F5.L",
        "13 C1 FF FF A7 F5",
    ),
}
EXECUTABLE_CORE_E_START = 0x011FC8
EXECUTABLE_CORE_E_END = 0x012EBE
EXECUTABLE_CORE_E_SOURCE_SHA256 = (
    "41c3a2f3e03710ff517dcbb2de5399727198d5a0b0df161cd04d1effcbb71e37"
)
EXECUTABLE_CORE_E_CANDIDATE_MANIFEST_SHA256 = (
    "abe211f72f2d9820f9873a5c316d0a5e526b0079f38ec2a28a4310b096d234f6"
)
EXECUTABLE_CORE_E_INSTRUCTION_COUNT = 853
EXECUTABLE_CORE_E_RTS_COUNT = 20
EXECUTABLE_CORE_F_START = 0x012EBE
EXECUTABLE_CORE_F_CODE_END = 0x017374
EXECUTABLE_CORE_F_END = 0x017386
EXECUTABLE_CORE_F_SOURCE_SHA256 = (
    "e12667e53945c6578d6c800efdeabb1dcb4c7f99f541d9c95cd5990065a618f8"
)
EXECUTABLE_CORE_F_CODE_SOURCE_SHA256 = (
    "444c9bc8134da816907df942bc943c861264cd4763e6394ab64421d9deb39770"
)
EXECUTABLE_CORE_F_PATTERN_SOURCE_SHA256 = (
    "e3e60880cfae8ce6804686ae27db96de6238da5a8433bbd4005826c494fd51b2"
)
EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256 = (
    "fdb02f906aeefe9150ad1b4fd0931077e34429ba105c97e3d7942a1d937e8a64"
)
EXECUTABLE_CORE_F_INSTRUCTION_COUNT = 4317
EXECUTABLE_CORE_F_RTS_COUNT = 61
EXECUTABLE_CORE_F_PATTERN_REFERENCE = 0x017208
EXECUTABLE_CORE_F_REFERENCE_INSTRUCTION_OWNERS = {
    0x01381D: (
        0x01381C,
        0x013822,
        "MOVE.L $FFFFA9F8.L,(A6)",
        "2C B9 FF FF A9 F8",
        False,
    ),
    0x014DA6: (
        0x014DA6,
        0x014DAC,
        "TST.B $FFFFAA11.L",
        "4A 39 FF FF AA 11",
        True,
    ),
    0x014E75: (
        0x014E74,
        0x014E7A,
        "MOVE.L A0,$FFFFAA12.L",
        "23 C8 FF FF AA 12",
        False,
    ),
}
MAX_LOW_SIGNAL = 2
WORD_STREAM_CONTROLS = {
    0xFFF3,
    0xFFF7,
    0xFFF8,
    0xFFFA,
    0xFFFD,
    0xFFFE,
    0xFFFF,
}
SCENARIO_LEVEL_PREFIX = 0x09B2E7
SCENARIO_LEVEL_PREFIX_HOOK = 0x025CDC
SCENARIO_LEVEL_PREFIX_HOOK_BYTES = bytes.fromhex("41 F9 00 09 B2 E7")
SCENARIO_LEVEL_PREFIX_EVIDENCE = "captures/run/1391_s19_canonical_brief_06.png"

HALFWIDTH_ALLOWED = {0x20, *range(0xA1, 0xE0)}
ASCII_ALLOWED = {
    *range(ord("0"), ord("9") + 1),
    *range(ord("A"), ord("Z") + 1),
    0x20,
    ord("."),
    ord("+"),
    ord("-"),
    ord(":"),
}

PACKED_SPRITE_GRAPHICS_REVIEW_ADDRESSES = {
    0x050019,
    0x0501B1,
    0x0501B3,
    0x0502DE,
    0x05061E,
    0x050709,
    0x050725,
    0x050F9B,
    0x05124D,
    0x0512C5,
    0x0512CD,
    0x0512E9,
    0x051564,
    0x051857,
    0x051917,
    0x051A99,
    0x051AD7,
    0x051C19,
    0x051C57,
    0x051D4F,
    0x051D8F,
    0x051DCF,
    0x0521C9,
    0x05224F,
    0x0523B9,
    0x0525C9,
    0x0525E9,
    0x0525EB,
    0x053078,
    0x0531C0,
    0x054BE6,
    0x054FD1,
    0x054FDE,
    0x0553E6,
    0x056F5E,
    0x057056,
    0x057748,
    0x057CE0,
    0x057DA0,
    0x05897C,
    0x058AC4,
    0x05A085,
    0x05A4E8,
    0x05A4EA,
    0x05A8CC,
    0x05A8D5,
    0x05ACE8,
    0x05ACEA,
    0x05C3DB,
    0x05C59E,
    0x05C7DB,
    0x05C862,
    0x05C952,
    0x05CFBA,
    0x05D5DC,
    0x05D5F4,
    0x05D836,
}

COMMANDER_SPRITE_MAPPING_REVIEW_ADDRESSES = {
    0x05DD02,
    0x05DD38,
    0x05DD6E,
    0x05DDA7,
}

CLASS_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS = 0x05E949

CLASS_SPRITE_GRAPHICS_REVIEWS = {
    **{
        address: (
            "packed_sprite_graphics_false_positive",
            "packed 4bpp sprite/tile graphics bytes",
        )
        for address in PACKED_SPRITE_GRAPHICS_REVIEW_ADDRESSES
    },
    **{
        address: (
            "commander_sprite_mapping_false_positive",
            "commander class-to-sprite mapping record",
        )
        for address in COMMANDER_SPRITE_MAPPING_REVIEW_ADDRESSES
    },
    CLASS_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS: (
        "class_pointer_table_boundary_false_positive",
        "low byte of final class pointer 0x0005E94A plus space padding",
    ),
}

CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS = {
    (0x050019, 0x01CAA2): (
        "cross_operand_window",
        "`MOVE.B 5(A0),25(A1)` source/destination displacement bytes",
    ),
    (0x050019, 0x095398): (
        "coincidental_data_window",
        "16-bit numeric/index row `0005 0019 0008 000C`",
    ),
}

PACKED_GAME_GRAPHICS_REVIEW_ADDRESSES = {
    0x060D35,
    0x060D39,
    0x060D41,
    0x060D50,
    0x061212,
    0x06121F,
    0x06146D,
}

NAME_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS = 0x061ABB

PACKED_TILE_SPRITE_GRAPHICS_REVIEW_ADDRESSES = {
    0x06EFF1,
    0x06EFFB,
    0x06F039,
    0x06F043,
    0x06F8F1,
    0x06F8FB,
    0x06F939,
    0x06F943,
    0x0701F1,
    0x0701FB,
    0x070239,
    0x070243,
    0x070AF1,
    0x070AFB,
    0x070B39,
    0x070B43,
    0x070C2A,
    0x0713F1,
    0x0713FB,
    0x071439,
    0x071443,
    0x071CF1,
    0x071CFB,
    0x071D39,
    0x071D43,
    0x0725F1,
    0x0725FB,
    0x072639,
    0x072643,
    0x072EF1,
    0x072EFB,
    0x072F39,
    0x072F43,
    0x0737F1,
    0x0737FB,
    0x073839,
    0x073843,
    0x0740F1,
    0x0740FB,
    0x074139,
    0x074143,
    0x0749F1,
    0x0749FB,
    0x074A39,
    0x074A43,
    0x07542A,
    0x0764F1,
    0x0764FB,
    0x076539,
    0x076543,
    0x076DF1,
    0x076DFB,
    0x076E39,
    0x076E43,
    0x0776F1,
    0x0776FB,
    0x077739,
    0x077743,
    0x0788F1,
    0x0788FB,
    0x078939,
    0x078943,
    0x07A3F1,
    0x07A3FB,
    0x07A439,
    0x07A443,
    0x07B72A,
    0x07BEF1,
    0x07BEFB,
    0x07BF39,
    0x07BF43,
    0x07C7F1,
    0x07C7FB,
    0x07C839,
    0x07C843,
}

ITEM_NAME_GRAPHICS_REVIEWS = {
    **{
        address: (
            "packed_game_graphics_false_positive",
            "packed 4bpp item/system tile bytes",
        )
        for address in PACKED_GAME_GRAPHICS_REVIEW_ADDRESSES
    },
    NAME_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS: (
        "name_pointer_table_boundary_false_positive",
        "low byte of final name pointer 0x00061ABC plus space padding",
    ),
    **{
        address: (
            "packed_tile_sprite_graphics_false_positive",
            "repeating packed 4bpp tile/sprite bytes",
        )
        for address in PACKED_TILE_SPRITE_GRAPHICS_REVIEW_ADDRESSES
    },
}

# The aligned four-byte scanner deliberately over-approximates. These three
# apparent references are pinned with their decoded context so they cannot be
# mistaken for live pointers merely because their four bytes equal a candidate
# address.
ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS = {
    (0x06121F, 0x0A4440): (
        "coincidental_data_window",
        "numeric/graphics index row `00 06 12 1F 2E 3C`",
    ),
    (0x070C2A, 0x01F0A6): (
        "cross_instruction_window",
        "`MOVE.W #$0007,D7` immediate followed by `CMPI.B` opcode `0C2A`",
    ),
    (0x070C2A, 0x01F1A8): (
        "cross_instruction_window",
        "`MOVE.W #$0007,D7` immediate followed by `CMPI.B` opcode `0C2A`",
    ),
}

# Each address was reviewed as an address within the containing 16-bit
# word/layout record. Pinning the exact set makes a new text/UI-bank candidate
# fail closed instead of inheriting a broad false-positive label.
WORD_STREAM_REVIEWS = {
    0x0A02A9: "screen-local 16-bit glyph stream",
    0x0A02C3: "screen-local 16-bit glyph stream",
    0x0A0813: "screen-local 16-bit glyph stream",
    0x0A0B1F: "screen-local 16-bit glyph stream",
    0x0A152B: "item/shop 16-bit glyph stream",
    0x0A16AD: "item/shop 16-bit glyph stream",
    0x0A16D1: "item/shop 16-bit glyph stream",
    0x0A1713: "item/shop 16-bit glyph stream",
    0x0A3161: "title START/LOAD 16-bit glyph stream",
    0x0A316B: "title START/LOAD 16-bit glyph stream",
    0x0A3447: "credits 16-bit glyph stream",
    0x0A34E1: "credits 16-bit glyph stream",
    0x0A3509: "credits 16-bit glyph stream",
    0x0A3513: "credits 16-bit glyph stream",
    0x0A353D: "credits 16-bit glyph stream",
    0x0A356D: "credits 16-bit glyph stream",
    0x0A35C9: "credits 16-bit glyph stream",
    0x0A3601: "credits 16-bit glyph stream",
    0x0A3639: "credits 16-bit glyph stream",
    0x0A368F: "credits 16-bit glyph stream",
    0x0A369B: "credits 16-bit glyph stream",
    0x0A3703: "credits 16-bit glyph stream",
    0x0A3733: "credits 16-bit glyph stream",
    0x0A3741: "credits 16-bit glyph stream",
    0x0A37B3: "declared scenario/total/turn UI glyph stream",
    0x0A37E3: "name-entry prompt glyph stream",
    0x0A3C99: "name-entry character glyph list",
    0x0A6F27: "opening text 16-bit glyph stream",
}

STRUCTURED_LAYOUT_REVIEWS = {
    0x0A1427: "item/shop structured word record",
    0x0A1437: "item/shop structured word record",
    0x0A143B: "item/shop structured word record",
    0x0A14A5: "item/shop structured word record",
    0x0A14A9: "item/shop structured word record",
    0x0A3B08: "name-entry byte/layout resource",
    0x0A46F4: "graphics/layout record immediately before referenced 0x0A46F6",
    0x0A4A36: "layout record terminator immediately before referenced 0x0A4A38",
    0x0A4F39: "layout record terminator immediately before referenced 0x0A4F3C",
    0x0A4FB3: "layout record terminator immediately before referenced 0x0A4FB6",
}

TEXT_UI_REVIEWS = {
    **{
        address: ("word_stream_byte_false_positive", owner)
        for address, owner in WORD_STREAM_REVIEWS.items()
    },
    **{
        address: ("structured_layout_false_positive", owner)
        for address, owner in STRUCTURED_LAYOUT_REVIEWS.items()
    },
}

ENDING_SCENARIO_STRUCTURED_REVIEWS = {
    0x096C75: "ending graphics/numeric record",
    0x096C8F: "ending graphics/numeric record",
    0x096CA3: "ending graphics/numeric record",
    0x096CA5: "ending graphics/numeric record",
    0x096CA7: "ending graphics/numeric record",
    0x096D77: "ending signed coordinate/layout table",
    0x096D7B: "ending signed coordinate/layout table",
    0x096D7F: "ending signed coordinate/layout table",
    0x096DD1: "ending signed coordinate/layout table",
    0x096DD5: "ending signed coordinate/layout table",
    0x096DD9: "ending signed coordinate/layout table",
    0x096DDD: "ending signed coordinate/layout table",
    0x096DE3: "ending signed coordinate/layout table",
    0x096DE7: "ending signed coordinate/layout table",
    0x096DEB: "ending signed coordinate/layout table",
    0x096DFF: "ending signed coordinate/layout table",
    0x09B0C6: "system-local byte lookup/layout record",
    0x09B0CE: "system-local byte lookup/layout record",
    0x09B0D2: "system-local byte lookup/layout record",
    0x09B0D6: "system-local byte lookup/layout record",
    0x09CFF7: "scenario token/layout word",
}

PACKED_TILE_RESOURCE_REVIEW_ADDRESSES = {
    0x083F76,
    0x084401,
    0x0845E6,
    0x08546B,
    0x08554C,
    0x0859F4,
    0x0860B4,
}

STRUCTURED_GRAPHICS_REVIEW_ADDRESSES = {
    0x0861AD,
    0x0861BB,
    0x0861CD,
    0x08664D,
    0x086689,
    0x086717,
    0x086771,
    0x08679B,
    0x08681B,
    0x08687B,
    0x08689F,
    0x0869A7,
    0x086A1D,
    0x086A9F,
    0x086B3F,
    0x086B61,
    0x086B6F,
    0x086B9F,
    0x086BA9,
    0x086C99,
    0x086CB7,
    0x086CC7,
    0x086CE9,
    0x086CF7,
    0x086D27,
    0x086D45,
    0x086D55,
    0x086D67,
    0x086F79,
    0x086F9B,
    0x086FB3,
    0x086FBD,
    0x086FD5,
    0x08709B,
    0x0870BD,
    0x0870D7,
    0x087185,
    0x0871B7,
    0x0871E9,
    0x08721B,
    0x08724D,
    0x08727F,
    0x0872B1,
    0x0872E3,
    0x0873B1,
    0x0873DB,
    0x087405,
    0x08742F,
    0x087459,
    0x087483,
    0x0874AD,
    0x0874D7,
    0x08767B,
}

ENDING_SELECTOR_REVIEW_ADDRESSES = {
    0x08913E,
    0x089286,
    0x0892F4,
    0x0893D1,
    0x089545,
    0x089552,
    0x089561,
}

SYSTEM_GRAPHICS_ENDING_REVIEWS = {
    **{
        address: (
            "packed_tile_resource_false_positive",
            "packed tilemap/render-script bytes",
        )
        for address in PACKED_TILE_RESOURCE_REVIEW_ADDRESSES
    },
    **{
        address: (
            "structured_graphics_false_positive",
            "sprite frame, coordinate, or animation record",
        )
        for address in STRUCTURED_GRAPHICS_REVIEW_ADDRESSES
    },
    **{
        address: (
            "ending_selector_false_positive",
            "character-epilogue pointer or selector record",
        )
        for address in ENDING_SELECTOR_REVIEW_ADDRESSES
    },
}


def region_name(address: int) -> str:
    if address < 0x040000:
        return "executable_or_numeric"
    if address < 0x050000:
        return "font_bitmap"
    if address < 0x060000:
        return "other_50000"
    if address < 0x061000:
        return "structured_game_data"
    if address < 0x080000:
        return "other_61000_7ffff"
    if address < 0x090000:
        return "glyph_tile"
    if address < 0x0A0000:
        return "other_90000_9ffff"
    if address < 0x0B0000:
        return "text_ui_bank"
    return "compressed"


def low_signal_runs(data: bytes) -> list[dict[str, object]]:
    rows = []
    specs = (
        (
            "halfwidth",
            HALFWIDTH_ALLOWED,
            lambda value: value != 0x20,
            32,
            "cp932",
        ),
        (
            "ascii",
            ASCII_ALLOWED,
            lambda value: ord("A") <= value <= ord("Z"),
            40,
            "ascii",
        ),
    )
    for kind, allowed, signal, maximum_length, encoding in specs:
        for start, end, raw in scan_runs(
            data,
            allowed,
            minimum_signal=1,
            signal=signal,
            maximum_length=maximum_length,
        ):
            signal_count = sum(bool(signal(value)) for value in raw)
            if signal_count > MAX_LOW_SIGNAL:
                continue
            rows.append(
                {
                    "kind": kind,
                    "start_int": start,
                    "end_int": end,
                    "signal_count": signal_count,
                    "raw": raw,
                    "text": raw.decode(encoding),
                    "region": region_name(start),
                }
            )
    rows.sort(key=lambda row: (int(row["start_int"]), str(row["kind"])))
    return rows


def aligned_absolute_references(
    data: bytes, targets: set[int]
) -> dict[int, list[int]]:
    references: dict[int, list[int]] = defaultdict(list)
    end = min(len(data), SCAN_END)
    for offset in range(0, end - 3, 2):
        target = int.from_bytes(data[offset : offset + 4], "big")
        if target in targets:
            references[target].append(offset)
    return dict(references)


def pc_relative_lea_pea_references(
    data: bytes, targets: set[int]
) -> dict[int, list[dict[str, object]]]:
    references: dict[int, list[dict[str, object]]] = defaultdict(list)
    end = min(len(data), EXECUTABLE_END)
    for offset in range(0, end - 3, 2):
        opcode = int.from_bytes(data[offset : offset + 2], "big")
        if opcode == 0x487A:
            instruction = "PEA"
        elif opcode & 0xF1FF == 0x41FA:
            instruction = "LEA"
        else:
            continue
        displacement = int.from_bytes(
            data[offset + 2 : offset + 4], "big", signed=True
        )
        target = offset + 2 + displacement
        if target in targets:
            references[target].append(
                {
                    "instruction": instruction,
                    "address": offset,
                    "displacement": displacement,
                }
            )
    return dict(references)


def word_context(data: bytes, start: int, end: int) -> tuple[int, str]:
    context_start = max(0, (start - 16) & ~1)
    context_end = min(len(data), (end + 17) & ~1)
    words = [
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(context_start, context_end, 2)
    ]
    return context_start, " ".join(f"{word:04X}" for word in words)


def candidate_manifest_sha256(rows: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(int(row["start_int"]).to_bytes(4, "big"))
        digest.update(int(row["end_int"]).to_bytes(4, "big"))
        digest.update(str(row["kind"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes(row["raw"]))
        digest.update(b"\0")
    return digest.hexdigest()


def compressed_resource_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    pointers = resource_pointers(data)
    encoded_ends = [
        resource_encoded_end(data, pointer) for pointer in pointers
    ]
    allocation_ends = [
        *pointers[1:],
        COMPRESSED_RESOURCE_BANK_END,
    ]
    table_end = pointers[0]
    payload_rows: list[tuple[dict[str, object], int]] = []
    pointer_table_rows: list[dict[str, object]] = []
    padding_rows: list[dict[str, object]] = []
    unowned_rows: list[dict[str, object]] = []

    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        if start < table_end:
            pointer_table_rows.append(row)
            continue
        index = bisect_right(pointers, start) - 1
        if index < 0 or index >= len(pointers):
            unowned_rows.append(row)
        elif start >= encoded_ends[index]:
            if end <= allocation_ends[index]:
                padding_rows.append(row)
            else:
                unowned_rows.append(row)
        elif end <= encoded_ends[index]:
            payload_rows.append((row, index))
        else:
            unowned_rows.append(row)

    payload_addresses = {
        int(row["start_int"]) for row, _ in payload_rows
    }
    absolute = aligned_absolute_references(data, payload_addresses)
    pc_relative = pc_relative_lea_pea_references(data, payload_addresses)
    rows_by_resource: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row, index in payload_rows:
        rows_by_resource[index].append(row)

    resource_summaries = []
    for index, rows in sorted(rows_by_resource.items()):
        pointer = pointers[index]
        encoded_end = encoded_ends[index]
        allocation_end = allocation_ends[index]
        kind_counts = Counter(str(row["kind"]) for row in rows)
        resource_summaries.append(
            {
                "index": index,
                "asset_family": asset_family(index),
                "resource_type": data[pointer],
                "pointer": f"0x{pointer:06X}",
                "encoded_end": f"0x{encoded_end:06X}",
                "allocation_end": f"0x{allocation_end:06X}",
                "padding_bytes": allocation_end - encoded_end,
                "candidate_count": len(rows),
                "kind_counts": dict(sorted(kind_counts.items())),
                "first_candidate": (
                    f"0x{min(int(row['start_int']) for row in rows):06X}"
                ),
                "last_candidate": (
                    f"0x{max(int(row['start_int']) for row in rows):06X}"
                ),
            }
        )

    representatives = []
    for row, index in payload_rows:
        start = int(row["start_int"])
        if start not in COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES:
            continue
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        representatives.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "compressed_resource_payload_false_positive",
                "owner": "encoded compressed graphics/resource bytes",
                "resource_index": index,
                "asset_family": asset_family(index),
                "resource_pointer": f"0x{pointers[index]:06X}",
                "resource_encoded_end": f"0x{encoded_ends[index]:06X}",
                "encoded_byte_offset": start - pointers[index],
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
            }
        )

    bank_bytes = data[
        COMPRESSED_RESOURCE_BANK_START:COMPRESSED_RESOURCE_BANK_END
    ]
    table_bytes = data[RESOURCE_TABLE:table_end]
    padding_values = Counter()
    for encoded_end, allocation_end in zip(
        encoded_ends, allocation_ends
    ):
        padding_values.update(data[encoded_end:allocation_end])
    family_counts = Counter(
        asset_family(index) for _, index in payload_rows
    )
    kind_counts = Counter(str(row["kind"]) for row, _ in payload_rows)
    unclassified_count = (
        len(pointer_table_rows) + len(padding_rows) + len(unowned_rows)
    )
    return {
        "range": "0x0B0000..0x180000",
        "pointer_table_range": (
            f"0x{RESOURCE_TABLE:06X}..0x{table_end:06X}"
        ),
        "resource_count": len(pointers),
        "first_resource_pointer": f"0x{pointers[0]:06X}",
        "last_resource_pointer": f"0x{pointers[-1]:06X}",
        "last_resource_encoded_end": f"0x{encoded_ends[-1]:06X}",
        "source_sha256": hashlib.sha256(bank_bytes).hexdigest(),
        "expected_source_sha256": COMPRESSED_RESOURCE_BANK_SOURCE_SHA256,
        "pointer_table_sha256": hashlib.sha256(table_bytes).hexdigest(),
        "expected_pointer_table_sha256": (
            COMPRESSED_RESOURCE_POINTER_TABLE_SHA256
        ),
        "source_layout_valid": (
            hashlib.sha256(bank_bytes).hexdigest()
            == COMPRESSED_RESOURCE_BANK_SOURCE_SHA256
            and hashlib.sha256(table_bytes).hexdigest()
            == COMPRESSED_RESOURCE_POINTER_TABLE_SHA256
            and len(pointers) == 429
            and pointers[0] == 0x0B06B4
            and pointers[-1] == 0x13807E
            and encoded_ends[-1] == 0x138152
            and all(
                pointer < encoded_end <= allocation_end
                for pointer, encoded_end, allocation_end in zip(
                    pointers, encoded_ends, allocation_ends
                )
            )
            and set(padding_values) <= {0x00, 0xFF}
        ),
        "encoded_payload_bytes": sum(
            encoded_end - pointer
            for pointer, encoded_end in zip(pointers, encoded_ends)
        ),
        "padding_bytes": sum(padding_values.values()),
        "padding_value_counts": {
            f"0x{value:02X}": count
            for value, count in sorted(padding_values.items())
        },
        "candidate_count": len(payload_rows),
        "kind_counts": dict(sorted(kind_counts.items())),
        "category_counts": {
            "compressed_resource_payload_false_positive": len(payload_rows)
        },
        "unclassified_count": unclassified_count,
        "pointer_table_candidate_addresses": [
            f"0x{int(row['start_int']):06X}" for row in pointer_table_rows
        ],
        "padding_candidate_addresses": [
            f"0x{int(row['start_int']):06X}" for row in padding_rows
        ],
        "unowned_candidate_addresses": [
            f"0x{int(row['start_int']):06X}" for row in unowned_rows
        ],
        "candidate_manifest_sha256": candidate_manifest_sha256(
            [row for row, _ in payload_rows]
        ),
        "expected_candidate_manifest_sha256": (
            COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256
        ),
        "resource_count_with_candidates": len(rows_by_resource),
        "asset_family_candidate_counts": dict(sorted(family_counts.items())),
        "resources_with_candidates": resource_summaries,
        "missing_representative_addresses": [
            f"0x{address:06X}"
            for address in sorted(
                COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES
                - payload_addresses
            )
        ],
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "addresses": [
                    f"0x{address:06X}" for address in addresses
                ],
            }
            for target, addresses in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "pc_relative_lea_pea_references": [
            {
                "target": f"0x{target:06X}",
                "references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in references
                ],
            }
            for target, references in sorted(pc_relative.items())
        ],
        "representative_candidates": representatives,
    }


def executable_tail_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        review = EXECUTABLE_TAIL_INSTRUCTION_REVIEWS.get(start)
        if review is None:
            instruction_address = None
            instruction_bytes = b""
            instruction_bytes_valid = False
            category = "unclassified"
            owner = "requires exact 68000 instruction-boundary review"
        else:
            instruction_address, expected_hex = review
            instruction_bytes = bytes.fromhex(expected_hex)
            instruction_bytes_valid = (
                data[
                    instruction_address :
                    instruction_address + len(instruction_bytes)
                ]
                == instruction_bytes
            )
            if start in EXECUTABLE_TAIL_OPCODE_BOUNDARY_ADDRESSES:
                category = "instruction_opcode_boundary_false_positive"
                owner = "68000 opcode followed by absolute FFFFFxxx operand"
            else:
                category = "instruction_immediate_boundary_false_positive"
                owner = "68000 immediate followed by absolute FFFFFxxx operand"
        context_start, context = word_context(data, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "instruction_address": (
                    None
                    if instruction_address is None
                    else f"0x{instruction_address:06X}"
                ),
                "instruction_bytes": instruction_bytes.hex(" ").upper(),
                "instruction_bytes_valid": instruction_bytes_valid,
                "candidate_inside_instruction": (
                    instruction_address is not None
                    and instruction_address <= start
                    and end
                    <= instruction_address + len(instruction_bytes)
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_TAIL_START:EXECUTABLE_TAIL_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    return {
        "range": "0x030000..0x0310A0",
        "source_bytes": EXECUTABLE_TAIL_END - EXECUTABLE_TAIL_START,
        "linear_instruction_count": 699,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_TAIL_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_TAIL_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": (
            source_sha256 == EXECUTABLE_TAIL_SOURCE_SHA256
            and manifest_sha256
            == EXECUTABLE_TAIL_CANDIDATE_MANIFEST_SHA256
            and addresses == set(EXECUTABLE_TAIL_INSTRUCTION_REVIEWS)
            and all(
                row["instruction_bytes_valid"]
                and row["candidate_inside_instruction"]
                for row in detailed_rows
            )
        ),
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "missing_review_addresses": [
            f"0x{address:06X}"
            for address in sorted(
                addresses - set(EXECUTABLE_TAIL_INSTRUCTION_REVIEWS)
            )
        ],
        "stale_review_addresses": [
            f"0x{address:06X}"
            for address in sorted(
                set(EXECUTABLE_TAIL_INSTRUCTION_REVIEWS) - addresses
            )
        ],
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_renderer_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "contiguous_instruction_stream_false_positive",
                "owner": "68000 executable instruction bytes",
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_RENDERER_START:EXECUTABLE_RENDERER_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    return {
        "range": "0x02BFC8..0x030000",
        "source_bytes": (
            EXECUTABLE_RENDERER_END - EXECUTABLE_RENDERER_START
        ),
        "linear_instruction_count": 3451,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_RENDERER_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_RENDERER_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": (
            source_sha256 == EXECUTABLE_RENDERER_SOURCE_SHA256
            and manifest_sha256
            == EXECUTABLE_RENDERER_CANDIDATE_MANIFEST_SHA256
        ),
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": {
            "contiguous_instruction_stream_false_positive": len(
                detailed_rows
            )
        },
        "unclassified_count": 0,
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_gameplay_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "contiguous_instruction_stream_false_positive",
                "owner": "68000 gameplay/system executable instruction bytes",
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    segment_summaries = []
    segment_layout_valid = True
    for start, end, instruction_count, expected_source_sha256 in (
        EXECUTABLE_GAMEPLAY_SEGMENTS
    ):
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        expected_manifest_sha256 = (
            EXECUTABLE_GAMEPLAY_SEGMENT_CANDIDATE_MANIFEST_SHA256[
                (start, end)
            ]
        )
        valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        segment_layout_valid &= valid
        segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "source_bytes": end - start,
                "linear_instruction_count": instruction_count,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "kind_counts": dict(
                    sorted(Counter(str(row["kind"]) for row in rows).items())
                ),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": valid,
            }
        )

    gap = data[
        EXECUTABLE_GAMEPLAY_GAP_START:EXECUTABLE_GAMEPLAY_GAP_END
    ]
    gap_candidates = [
        row
        for row in low_signal_runs(data)
        if EXECUTABLE_GAMEPLAY_GAP_START
        <= int(row["start_int"])
        < EXECUTABLE_GAMEPLAY_GAP_END
    ]
    manifest_sha256 = candidate_manifest_sha256(candidates)
    source_layout_valid = (
        segment_layout_valid
        and gap == EXECUTABLE_GAMEPLAY_GAP_BYTES
        and not gap_candidates
        and manifest_sha256
        == EXECUTABLE_GAMEPLAY_CANDIDATE_MANIFEST_SHA256
        and sum(
            int(summary["candidate_count"])
            for summary in segment_summaries
        )
        == len(candidates)
    )
    return {
        "range": "0x020000..0x02BFC8 excluding 0x02A19C..0x02A1B0",
        "segments": segment_summaries,
        "numeric_table_gap": {
            "range": (
                f"0x{EXECUTABLE_GAMEPLAY_GAP_START:06X}.."
                f"0x{EXECUTABLE_GAMEPLAY_GAP_END:06X}"
            ),
            "source_bytes": len(gap),
            "raw_hex": gap.hex(" ").upper(),
            "expected_raw_hex": (
                EXECUTABLE_GAMEPLAY_GAP_BYTES.hex(" ").upper()
            ),
            "candidate_count": len(gap_candidates),
            "source_layout_valid": gap == EXECUTABLE_GAMEPLAY_GAP_BYTES,
        },
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": {
            "contiguous_instruction_stream_false_positive": len(
                detailed_rows
            )
        },
        "unclassified_count": 0,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_GAMEPLAY_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_auxiliary_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    word_pointers = [
        int.from_bytes(data[offset : offset + 4], "big")
        for offset in range(
            EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_START,
            EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_END,
            4,
        )
    ]
    unique_word_pointers = sorted(set(word_pointers))

    code_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _, _ in EXECUTABLE_AUXILIARY_CODE_SEGMENTS
        )
    ]
    word_rows = [
        row
        for row in candidates
        if EXECUTABLE_AUXILIARY_WORD_RECORD_START
        <= int(row["start_int"])
        < EXECUTABLE_AUXILIARY_WORD_RECORD_END
    ]
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        if row in code_rows:
            category = "contiguous_instruction_stream_false_positive"
            owner = "68000 executable instruction bytes"
            containing_word = None
            following_word = None
            record_start = None
            pointer_entries = []
        elif row in word_rows:
            category = "pointer_indexed_16bit_word_stream_false_positive"
            owner = "pointer-indexed 16-bit glyph/control word record"
            word_address = start & ~1
            containing_word = int.from_bytes(
                data[word_address : word_address + 2], "big"
            )
            following_word = int.from_bytes(
                data[word_address + 2 : word_address + 4], "big"
            )
            pointer_index = bisect_right(
                unique_word_pointers, word_address
            ) - 1
            record_start = (
                unique_word_pointers[pointer_index]
                if pointer_index >= 0
                else None
            )
            pointer_entries = [
                EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_START + index * 4
                for index, pointer in enumerate(word_pointers)
                if pointer == record_start
            ]
        else:
            category = "unclassified"
            owner = "requires executable/data ownership review"
            containing_word = None
            following_word = None
            record_start = None
            pointer_entries = []
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word": (
                    None
                    if containing_word is None
                    else f"0x{containing_word:04X}"
                ),
                "following_word": (
                    None
                    if following_word is None
                    else f"0x{following_word:04X}"
                ),
                "record_start": (
                    None
                    if record_start is None
                    else f"0x{record_start:06X}"
                ),
                "pointer_entries": [
                    f"0x{offset:06X}" for offset in pointer_entries
                ],
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    code_segment_summaries = []
    code_layout_valid = True
    for (
        start,
        end,
        instruction_count,
        expected_source_sha256,
        expected_manifest_sha256,
    ) in EXECUTABLE_AUXILIARY_CODE_SEGMENTS:
        rows = [
            row
            for row in code_rows
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        code_layout_valid &= valid
        code_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "source_bytes": end - start,
                "linear_instruction_count": instruction_count,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": valid,
            }
        )

    data_segment_summaries = []
    data_layout_valid = True
    for start, end, owner, expected_source_sha256 in (
        EXECUTABLE_AUXILIARY_DATA_SEGMENTS
    ):
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        valid = source_sha256 == expected_source_sha256
        data_layout_valid &= valid
        data_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "source_bytes": end - start,
                "owner": owner,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "source_layout_valid": valid,
            }
        )

    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_AUXILIARY_START:EXECUTABLE_AUXILIARY_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    source_layout_valid = (
        source_sha256 == EXECUTABLE_AUXILIARY_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_AUXILIARY_CANDIDATE_MANIFEST_SHA256
        and candidate_manifest_sha256(code_rows)
        == EXECUTABLE_AUXILIARY_CODE_CANDIDATE_MANIFEST_SHA256
        and candidate_manifest_sha256(word_rows)
        == EXECUTABLE_AUXILIARY_WORD_CANDIDATE_MANIFEST_SHA256
        and code_layout_valid
        and data_layout_valid
        and len(code_rows) == 123
        and len(word_rows) == 4
        and len(code_rows) + len(word_rows) == len(candidates)
        and len(word_pointers) == 38
        and all(
            EXECUTABLE_AUXILIARY_WORD_RECORD_START
            <= pointer
            < EXECUTABLE_AUXILIARY_WORD_RECORD_END
            for pointer in word_pointers
        )
        and all(
            row["containing_word"] == "0x004A"
            and row["following_word"] == "0xFFFF"
            and row["record_start"] is not None
            and row["pointer_entries"]
            for row in detailed_rows
            if row["category"]
            == "pointer_indexed_16bit_word_stream_false_positive"
        )
    )
    return {
        "range": (
            f"0x{EXECUTABLE_AUXILIARY_START:06X}.."
            f"0x{EXECUTABLE_AUXILIARY_END:06X}"
        ),
        "source_bytes": (
            EXECUTABLE_AUXILIARY_END - EXECUTABLE_AUXILIARY_START
        ),
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_AUXILIARY_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_AUXILIARY_CANDIDATE_MANIFEST_SHA256
        ),
        "code_candidate_manifest_sha256": candidate_manifest_sha256(
            code_rows
        ),
        "expected_code_candidate_manifest_sha256": (
            EXECUTABLE_AUXILIARY_CODE_CANDIDATE_MANIFEST_SHA256
        ),
        "word_candidate_manifest_sha256": candidate_manifest_sha256(
            word_rows
        ),
        "expected_word_candidate_manifest_sha256": (
            EXECUTABLE_AUXILIARY_WORD_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "code_segments": code_segment_summaries,
        "data_segments": data_segment_summaries,
        "word_pointer_table": {
            "range": (
                f"0x{EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_START:06X}.."
                f"0x{EXECUTABLE_AUXILIARY_WORD_POINTER_TABLE_END:06X}"
            ),
            "pointer_count": len(word_pointers),
            "unique_pointer_count": len(set(word_pointers)),
            "first_pointer": f"0x{word_pointers[0]:06X}",
            "last_pointer": f"0x{word_pointers[-1]:06X}",
            "minimum_pointer": f"0x{min(word_pointers):06X}",
            "maximum_pointer": f"0x{max(word_pointers):06X}",
        },
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_startup_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    code_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _, _ in EXECUTABLE_STARTUP_CODE_SEGMENTS
        )
    ]
    data_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _, _ in EXECUTABLE_STARTUP_DATA_SEGMENTS
        )
    ]

    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        if row in code_rows:
            category = "contiguous_instruction_stream_false_positive"
            owner = "startup/interrupt 68000 instruction bytes"
        elif row in data_rows:
            category = "startup_configuration_table_false_positive"
            owner = next(
                segment_owner
                for segment_start, segment_end, segment_owner, _, _ in (
                    EXECUTABLE_STARTUP_DATA_SEGMENTS
                )
                if segment_start <= start < segment_end
            )
        else:
            category = "unclassified"
            owner = "requires startup code/data ownership review"
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    code_segment_summaries = []
    code_layout_valid = True
    for (
        start,
        end,
        instruction_count,
        expected_source_sha256,
        expected_manifest_sha256,
    ) in EXECUTABLE_STARTUP_CODE_SEGMENTS:
        rows = [
            row
            for row in code_rows
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        code_layout_valid &= valid
        code_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "source_bytes": end - start,
                "linear_instruction_count": instruction_count,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": valid,
            }
        )

    data_segment_summaries = []
    data_layout_valid = True
    for (
        start,
        end,
        segment_owner,
        expected_source_sha256,
        expected_manifest_sha256,
    ) in EXECUTABLE_STARTUP_DATA_SEGMENTS:
        rows = [
            row
            for row in data_rows
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        data_layout_valid &= valid
        data_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "source_bytes": end - start,
                "owner": segment_owner,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": valid,
            }
        )

    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_STARTUP_START:EXECUTABLE_STARTUP_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    code_manifest_sha256 = candidate_manifest_sha256(code_rows)
    data_manifest_sha256 = candidate_manifest_sha256(data_rows)
    padding = data[
        EXECUTABLE_STARTUP_PADDING_START:EXECUTABLE_STARTUP_START
    ]
    padding_sha256 = hashlib.sha256(padding).hexdigest()
    source_layout_valid = (
        source_sha256 == EXECUTABLE_STARTUP_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_STARTUP_CANDIDATE_MANIFEST_SHA256
        and code_manifest_sha256
        == EXECUTABLE_STARTUP_CODE_CANDIDATE_MANIFEST_SHA256
        and data_manifest_sha256
        == EXECUTABLE_STARTUP_DATA_CANDIDATE_MANIFEST_SHA256
        and code_layout_valid
        and data_layout_valid
        and len(code_rows) == 40
        and len(data_rows) == 1
        and len(code_rows) + len(data_rows) == len(candidates)
        and padding_sha256 == EXECUTABLE_STARTUP_PADDING_SHA256
        and set(padding) == {0xFF}
    )
    return {
        "range": (
            f"0x{EXECUTABLE_STARTUP_START:06X}.."
            f"0x{EXECUTABLE_STARTUP_END:06X}"
        ),
        "source_bytes": EXECUTABLE_STARTUP_END - EXECUTABLE_STARTUP_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_STARTUP_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_STARTUP_CANDIDATE_MANIFEST_SHA256
        ),
        "code_candidate_manifest_sha256": code_manifest_sha256,
        "expected_code_candidate_manifest_sha256": (
            EXECUTABLE_STARTUP_CODE_CANDIDATE_MANIFEST_SHA256
        ),
        "data_candidate_manifest_sha256": data_manifest_sha256,
        "expected_data_candidate_manifest_sha256": (
            EXECUTABLE_STARTUP_DATA_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "preceding_ff_padding": {
            "range": (
                f"0x{EXECUTABLE_STARTUP_PADDING_START:06X}.."
                f"0x{EXECUTABLE_STARTUP_START:06X}"
            ),
            "source_bytes": len(padding),
            "source_sha256": padding_sha256,
            "expected_source_sha256": EXECUTABLE_STARTUP_PADDING_SHA256,
            "all_ff": set(padding) == {0xFF},
            "candidate_count": 0,
        },
        "code_segments": code_segment_summaries,
        "data_segments": data_segment_summaries,
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_a_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    code_rows = [
        row
        for row in candidates
        if int(row["start_int"]) < EXECUTABLE_CORE_A_CODE_END
    ]
    table_rows = [
        row
        for row in candidates
        if int(row["start_int"]) >= EXECUTABLE_CORE_A_CODE_END
    ]

    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        if start < EXECUTABLE_CORE_A_CODE_END:
            category = "contiguous_instruction_stream_false_positive"
            owner = "core 68000 instruction bytes"
        else:
            category = "pc_indexed_dispatch_table_false_positive"
            owner = "PC-indexed 16-bit dispatch offset table"
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_CORE_A_START:EXECUTABLE_CORE_A_END]
    ).hexdigest()
    code_source_sha256 = hashlib.sha256(
        data[EXECUTABLE_CORE_A_START:EXECUTABLE_CORE_A_CODE_END]
    ).hexdigest()
    table_source_sha256 = hashlib.sha256(
        data[EXECUTABLE_CORE_A_CODE_END:EXECUTABLE_CORE_A_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    code_manifest_sha256 = candidate_manifest_sha256(code_rows)
    table_manifest_sha256 = candidate_manifest_sha256(table_rows)
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_A_SOURCE_SHA256
        and code_source_sha256 == EXECUTABLE_CORE_A_CODE_SOURCE_SHA256
        and table_source_sha256 == EXECUTABLE_CORE_A_TABLE_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256
        and code_manifest_sha256
        == EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256
        and table_manifest_sha256 == EMPTY_SHA256
        and len(code_rows) == 67
        and len(table_rows) == 0
        and len(code_rows) == len(candidates)
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_A_START:06X}.."
            f"0x{EXECUTABLE_CORE_A_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_A_END - EXECUTABLE_CORE_A_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_A_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_A_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "code_segment": {
            "range": (
                f"0x{EXECUTABLE_CORE_A_START:06X}.."
                f"0x{EXECUTABLE_CORE_A_CODE_END:06X}"
            ),
            "source_bytes": (
                EXECUTABLE_CORE_A_CODE_END - EXECUTABLE_CORE_A_START
            ),
            "linear_instruction_count": EXECUTABLE_CORE_A_INSTRUCTION_COUNT,
            "source_sha256": code_source_sha256,
            "expected_source_sha256": (
                EXECUTABLE_CORE_A_CODE_SOURCE_SHA256
            ),
            "candidate_count": len(code_rows),
            "candidate_manifest_sha256": code_manifest_sha256,
        },
        "dispatch_table": {
            "range": (
                f"0x{EXECUTABLE_CORE_A_CODE_END:06X}.."
                f"0x{EXECUTABLE_CORE_A_END:06X}"
            ),
            "source_bytes": EXECUTABLE_CORE_A_END - EXECUTABLE_CORE_A_CODE_END,
            "source_sha256": table_source_sha256,
            "expected_source_sha256": (
                EXECUTABLE_CORE_A_TABLE_SOURCE_SHA256
            ),
            "raw_hex": data[
                EXECUTABLE_CORE_A_CODE_END:EXECUTABLE_CORE_A_END
            ].hex(" ").upper(),
            "candidate_count": len(table_rows),
            "candidate_manifest_sha256": table_manifest_sha256,
        },
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_b_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "contiguous_instruction_stream_false_positive",
                "owner": "core 68000 instruction bytes",
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    source = data[EXECUTABLE_CORE_B_START:EXECUTABLE_CORE_B_END]
    marker = data[EXECUTABLE_CORE_B_END:EXECUTABLE_CORE_B_MARKER_END]
    source_sha256 = hashlib.sha256(source).hexdigest()
    marker_source_sha256 = hashlib.sha256(marker).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_B_SOURCE_SHA256
        and marker_source_sha256
        == EXECUTABLE_CORE_B_MARKER_SOURCE_SHA256
        and marker == b"LOADSAVECONTINUESCENARIONOTHING !"
        and manifest_sha256
        == EXECUTABLE_CORE_B_CANDIDATE_MANIFEST_SHA256
        and len(candidates) == 174
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_B_START:06X}.."
            f"0x{EXECUTABLE_CORE_B_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_B_END - EXECUTABLE_CORE_B_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_B_SOURCE_SHA256,
        "linear_instruction_count": EXECUTABLE_CORE_B_INSTRUCTION_COUNT,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_B_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "following_ascii_marker": {
            "range": (
                f"0x{EXECUTABLE_CORE_B_END:06X}.."
                f"0x{EXECUTABLE_CORE_B_MARKER_END:06X}"
            ),
            "source_bytes": len(marker),
            "source_sha256": marker_source_sha256,
            "expected_source_sha256": (
                EXECUTABLE_CORE_B_MARKER_SOURCE_SHA256
            ),
            "raw_ascii": marker.decode("ascii"),
        },
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_c_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    code_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _, _ in EXECUTABLE_CORE_C_CODE_SEGMENTS
        )
    ]
    data_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _ in EXECUTABLE_CORE_C_DATA_SEGMENTS
        )
    ]

    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        in_code = any(
            segment_start <= start < segment_end
            for segment_start, segment_end, _, _, _ in (
                EXECUTABLE_CORE_C_CODE_SEGMENTS
            )
        )
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": (
                    "contiguous_instruction_stream_false_positive"
                    if in_code
                    else "unclassified"
                ),
                "owner": (
                    "core 68000 instruction bytes"
                    if in_code
                    else "requires core-C data ownership review"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    code_segment_summaries = []
    code_layout_valid = True
    for (
        start,
        end,
        instruction_count,
        expected_source_sha256,
        expected_manifest_sha256,
    ) in EXECUTABLE_CORE_C_CODE_SEGMENTS:
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        segment_valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        code_layout_valid &= segment_valid
        code_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "source_bytes": end - start,
                "linear_instruction_count": instruction_count,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": segment_valid,
            }
        )

    data_segment_summaries = []
    data_layout_valid = True
    for start, end, owner, expected_source_sha256 in (
        EXECUTABLE_CORE_C_DATA_SEGMENTS
    ):
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        segment_valid = (
            source_sha256 == expected_source_sha256 and not rows
        )
        data_layout_valid &= segment_valid
        data_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "owner": owner,
                "source_bytes": end - start,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "source_layout_valid": segment_valid,
            }
        )

    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_CORE_C_START:EXECUTABLE_CORE_C_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    code_manifest_sha256 = candidate_manifest_sha256(code_rows)
    data_manifest_sha256 = candidate_manifest_sha256(data_rows)
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_C_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256
        and code_manifest_sha256
        == EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256
        and data_manifest_sha256 == EMPTY_SHA256
        and code_layout_valid
        and data_layout_valid
        and len(code_rows) == 85
        and len(data_rows) == 0
        and len(code_rows) == len(candidates)
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_C_START:06X}.."
            f"0x{EXECUTABLE_CORE_C_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_C_END - EXECUTABLE_CORE_C_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_C_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_C_CANDIDATE_MANIFEST_SHA256
        ),
        "code_candidate_manifest_sha256": code_manifest_sha256,
        "data_candidate_manifest_sha256": data_manifest_sha256,
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "code_segments": code_segment_summaries,
        "data_segments": data_segment_summaries,
        "layout_record_pointer_table": {
            "range": "0x00FD42..0x00FD5E",
            "pointer_count": 7,
            "pointers": [
                f"0x{int.from_bytes(data[offset : offset + 4], 'big'):06X}"
                for offset in range(0x00FD42, 0x00FD5E, 4)
            ],
        },
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_d_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    code_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _, _ in EXECUTABLE_CORE_D_CODE_SEGMENTS
        )
    ]
    data_rows = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _ in EXECUTABLE_CORE_D_DATA_SEGMENTS
        )
    ]

    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        in_code = any(
            segment_start <= start < segment_end
            for segment_start, segment_end, _, _, _ in (
                EXECUTABLE_CORE_D_CODE_SEGMENTS
            )
        )
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": (
                    "contiguous_instruction_stream_false_positive"
                    if in_code
                    else "unclassified"
                ),
                "owner": (
                    "core 68000 instruction bytes"
                    if in_code
                    else "requires core-D data ownership review"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    code_segment_summaries = []
    code_layout_valid = True
    for (
        start,
        end,
        instruction_count,
        expected_source_sha256,
        expected_manifest_sha256,
    ) in EXECUTABLE_CORE_D_CODE_SEGMENTS:
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        manifest_sha256 = candidate_manifest_sha256(rows)
        segment_valid = (
            source_sha256 == expected_source_sha256
            and manifest_sha256 == expected_manifest_sha256
        )
        code_layout_valid &= segment_valid
        code_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "source_bytes": end - start,
                "linear_instruction_count": instruction_count,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "candidate_manifest_sha256": manifest_sha256,
                "expected_candidate_manifest_sha256": (
                    expected_manifest_sha256
                ),
                "source_layout_valid": segment_valid,
            }
        )

    data_segment_summaries = []
    data_layout_valid = True
    for start, end, owner, expected_source_sha256 in (
        EXECUTABLE_CORE_D_DATA_SEGMENTS
    ):
        rows = [
            row
            for row in candidates
            if start <= int(row["start_int"]) < end
        ]
        source_sha256 = hashlib.sha256(data[start:end]).hexdigest()
        segment_valid = (
            source_sha256 == expected_source_sha256 and not rows
        )
        data_layout_valid &= segment_valid
        data_segment_summaries.append(
            {
                "range": f"0x{start:06X}..0x{end:06X}",
                "owner": owner,
                "source_bytes": end - start,
                "source_sha256": source_sha256,
                "expected_source_sha256": expected_source_sha256,
                "candidate_count": len(rows),
                "source_layout_valid": segment_valid,
            }
        )

    reference_instruction_owners = []
    reference_instruction_owners_valid = True
    for target, (
        start,
        end,
        instruction,
        expected_raw_hex,
    ) in EXECUTABLE_CORE_D_REFERENCE_INSTRUCTION_OWNERS.items():
        raw_hex = data[start:end].hex(" ").upper()
        valid = (
            start <= target < end
            and bool(target & 1)
            and raw_hex == expected_raw_hex
        )
        reference_instruction_owners_valid &= valid
        reference_instruction_owners.append(
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "instruction_range": f"0x{start:06X}..0x{end:06X}",
                "instruction": instruction,
                "raw_hex": raw_hex,
                "source_layout_valid": valid,
            }
        )

    source_sha256 = hashlib.sha256(
        data[EXECUTABLE_CORE_D_START:EXECUTABLE_CORE_D_END]
    ).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    code_manifest_sha256 = candidate_manifest_sha256(code_rows)
    data_manifest_sha256 = candidate_manifest_sha256(data_rows)
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_D_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256
        and code_manifest_sha256
        == EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256
        and data_manifest_sha256 == EMPTY_SHA256
        and code_layout_valid
        and data_layout_valid
        and reference_instruction_owners_valid
        and set(absolute) == set(EXECUTABLE_CORE_D_REFERENCE_INSTRUCTION_OWNERS)
        and all(target & 1 for target in absolute)
        and not pc_relative
        and len(code_rows) == 102
        and len(data_rows) == 0
        and len(code_rows) == len(candidates)
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_D_START:06X}.."
            f"0x{EXECUTABLE_CORE_D_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_D_END - EXECUTABLE_CORE_D_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_D_SOURCE_SHA256,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_D_CANDIDATE_MANIFEST_SHA256
        ),
        "code_candidate_manifest_sha256": code_manifest_sha256,
        "data_candidate_manifest_sha256": data_manifest_sha256,
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "code_segments": code_segment_summaries,
        "data_segments": data_segment_summaries,
        "decimal_place_values": [
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x0106EC, 0x0106F6, 2)
        ],
        "numeric_record_pointer_table": {
            "range": "0x010932..0x01095A",
            "pointer_count": 10,
            "pointers": [
                f"0x{int.from_bytes(data[offset : offset + 4], 'big'):06X}"
                for offset in range(0x010932, 0x01095A, 4)
            ],
        },
        "bit_direction_pattern_hex": data[
            0x01179E:0x0117AE
        ].hex(" ").upper(),
        "layout_record_count": (
            (0x011F46 - 0x011EBA) // 10
        ),
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "reference_instruction_owners": reference_instruction_owners,
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_e_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "contiguous_instruction_stream_false_positive",
                "owner": "core 68000 instruction bytes",
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    source = data[EXECUTABLE_CORE_E_START:EXECUTABLE_CORE_E_END]
    source_sha256 = hashlib.sha256(source).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_E_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_CORE_E_CANDIDATE_MANIFEST_SHA256
        and len(candidates) == 24
        and not absolute
        and not pc_relative
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_E_START:06X}.."
            f"0x{EXECUTABLE_CORE_E_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_E_END - EXECUTABLE_CORE_E_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_E_SOURCE_SHA256,
        "linear_instruction_count": EXECUTABLE_CORE_E_INSTRUCTION_COUNT,
        "rts_instruction_count": EXECUTABLE_CORE_E_RTS_COUNT,
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_E_CANDIDATE_MANIFEST_SHA256
        ),
        "source_layout_valid": source_layout_valid,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def executable_core_f_candidate_inventory(
    data: bytes, candidates: list[dict[str, object]]
) -> dict[str, object]:
    addresses = {int(row["start_int"]) for row in candidates}
    absolute = aligned_absolute_references(data, addresses)
    pc_relative = pc_relative_lea_pea_references(data, addresses)
    code_rows = [
        row
        for row in candidates
        if EXECUTABLE_CORE_F_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_F_CODE_END
    ]
    data_rows = [
        row
        for row in candidates
        if EXECUTABLE_CORE_F_CODE_END
        <= int(row["start_int"])
        < EXECUTABLE_CORE_F_END
    ]
    detailed_rows = []
    for row in candidates:
        start = int(row["start_int"])
        end = int(row["end_int"])
        context_start, context = word_context(data, start, end)
        in_code = start < EXECUTABLE_CORE_F_CODE_END
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": (
                    "contiguous_instruction_stream_false_positive"
                    if in_code
                    else "unclassified"
                ),
                "owner": (
                    "core 68000 instruction bytes"
                    if in_code
                    else "requires core-F pattern ownership review"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    reference_instruction_owners = []
    reference_instruction_owners_valid = True
    for target, (
        start,
        end,
        instruction,
        expected_raw_hex,
        expected_instruction_start,
    ) in EXECUTABLE_CORE_F_REFERENCE_INSTRUCTION_OWNERS.items():
        raw_hex = data[start:end].hex(" ").upper()
        target_is_instruction_start = target == start
        valid = (
            start <= target < end
            and raw_hex == expected_raw_hex
            and target_is_instruction_start == expected_instruction_start
        )
        reference_instruction_owners_valid &= valid
        reference_instruction_owners.append(
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "target_is_instruction_start": target_is_instruction_start,
                "instruction_range": f"0x{start:06X}..0x{end:06X}",
                "instruction": instruction,
                "raw_hex": raw_hex,
                "source_layout_valid": valid,
            }
        )

    source = data[EXECUTABLE_CORE_F_START:EXECUTABLE_CORE_F_END]
    code = data[EXECUTABLE_CORE_F_START:EXECUTABLE_CORE_F_CODE_END]
    pattern = data[EXECUTABLE_CORE_F_CODE_END:EXECUTABLE_CORE_F_END]
    source_sha256 = hashlib.sha256(source).hexdigest()
    code_source_sha256 = hashlib.sha256(code).hexdigest()
    pattern_source_sha256 = hashlib.sha256(pattern).hexdigest()
    manifest_sha256 = candidate_manifest_sha256(candidates)
    code_manifest_sha256 = candidate_manifest_sha256(code_rows)
    data_manifest_sha256 = candidate_manifest_sha256(data_rows)
    pattern_absolute = aligned_absolute_references(
        data, {EXECUTABLE_CORE_F_CODE_END}
    )
    pattern_pc_relative = pc_relative_lea_pea_references(
        data, {EXECUTABLE_CORE_F_CODE_END}
    )
    category_counts = Counter(
        str(row["category"]) for row in detailed_rows
    )
    source_layout_valid = (
        source_sha256 == EXECUTABLE_CORE_F_SOURCE_SHA256
        and code_source_sha256 == EXECUTABLE_CORE_F_CODE_SOURCE_SHA256
        and pattern_source_sha256
        == EXECUTABLE_CORE_F_PATTERN_SOURCE_SHA256
        and manifest_sha256
        == EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256
        and code_manifest_sha256
        == EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256
        and data_manifest_sha256 == EMPTY_SHA256
        and len(code_rows) == 189
        and not data_rows
        and len(code_rows) == len(candidates)
        and set(absolute)
        == set(EXECUTABLE_CORE_F_REFERENCE_INSTRUCTION_OWNERS)
        and reference_instruction_owners_valid
        and not pc_relative
        and pattern_absolute
        == {EXECUTABLE_CORE_F_CODE_END: [EXECUTABLE_CORE_F_PATTERN_REFERENCE]}
        and not pattern_pc_relative
    )
    return {
        "range": (
            f"0x{EXECUTABLE_CORE_F_START:06X}.."
            f"0x{EXECUTABLE_CORE_F_END:06X}"
        ),
        "source_bytes": EXECUTABLE_CORE_F_END - EXECUTABLE_CORE_F_START,
        "source_sha256": source_sha256,
        "expected_source_sha256": EXECUTABLE_CORE_F_SOURCE_SHA256,
        "source_layout_valid": source_layout_valid,
        "code_segment": {
            "range": (
                f"0x{EXECUTABLE_CORE_F_START:06X}.."
                f"0x{EXECUTABLE_CORE_F_CODE_END:06X}"
            ),
            "source_bytes": (
                EXECUTABLE_CORE_F_CODE_END - EXECUTABLE_CORE_F_START
            ),
            "source_sha256": code_source_sha256,
            "expected_source_sha256": (
                EXECUTABLE_CORE_F_CODE_SOURCE_SHA256
            ),
            "linear_instruction_count": EXECUTABLE_CORE_F_INSTRUCTION_COUNT,
            "rts_instruction_count": EXECUTABLE_CORE_F_RTS_COUNT,
            "candidate_count": len(code_rows),
        },
        "pattern_table": {
            "range": (
                f"0x{EXECUTABLE_CORE_F_CODE_END:06X}.."
                f"0x{EXECUTABLE_CORE_F_END:06X}"
            ),
            "source_bytes": EXECUTABLE_CORE_F_END - EXECUTABLE_CORE_F_CODE_END,
            "source_sha256": pattern_source_sha256,
            "expected_source_sha256": (
                EXECUTABLE_CORE_F_PATTERN_SOURCE_SHA256
            ),
            "candidate_count": len(data_rows),
            "values": [
                int.from_bytes(data[offset : offset + 2], "big")
                for offset in range(
                    EXECUTABLE_CORE_F_CODE_END,
                    EXECUTABLE_CORE_F_END,
                    2,
                )
            ],
            "aligned_absolute_32_references": [
                f"0x{address:06X}"
                for address in pattern_absolute.get(
                    EXECUTABLE_CORE_F_CODE_END, []
                )
            ],
        },
        "candidate_manifest_sha256": manifest_sha256,
        "expected_candidate_manifest_sha256": (
            EXECUTABLE_CORE_F_CANDIDATE_MANIFEST_SHA256
        ),
        "code_candidate_manifest_sha256": code_manifest_sha256,
        "data_candidate_manifest_sha256": data_manifest_sha256,
        "candidate_count": len(detailed_rows),
        "kind_counts": dict(
            sorted(Counter(str(row["kind"]) for row in detailed_rows).items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "unclassified_count": category_counts.get("unclassified", 0),
        "aligned_absolute_32_reference_count": sum(
            len(references) for references in absolute.values()
        ),
        "aligned_absolute_32_references": [
            {
                "target": f"0x{target:06X}",
                "target_is_odd": bool(target & 1),
                "addresses": [
                    f"0x{address:06X}" for address in references
                ],
            }
            for target, references in sorted(absolute.items())
        ],
        "reference_instruction_owners": reference_instruction_owners,
        "pc_relative_lea_pea_reference_count": sum(
            len(references) for references in pc_relative.values()
        ),
        "candidates": detailed_rows,
    }


def is_word_stream_byte_lane(data: bytes, start: int, end: int) -> bool:
    if start % 2 != 1 or (end - 1) % 2 != 0:
        return False
    containing_word = int.from_bytes(data[start - 1 : start + 1], "big")
    following_control = int.from_bytes(data[end - 1 : end + 1], "big")
    return containing_word <= 0x07FF and following_control in WORD_STREAM_CONTROLS


def ending_scenario_owner(address: int) -> str:
    if address < 0x0954E2:
        return "epilogue 16-bit text record"
    if address < 0x096D00:
        return "ending 16-bit text or graphics record"
    if address < 0x096F00:
        return "ending structured layout data"
    if address < 0x098000:
        return "shared UI/name/layout data"
    if address < 0x09A000:
        return "condition/scenario-description resource"
    if address < 0x09B000:
        return "battle-local UI resource"
    if address < 0x09B2FC:
        return "system-local UI resource"
    return "scenario-description glyph/token resource"


def system_graphics_word_owner(address: int) -> str:
    if address < 0x082BFE:
        return "shared system-message 16-bit glyph stream"
    if address < 0x082D5A:
        return "magic-name 16-bit glyph stream"
    return "mercenary-name 16-bit glyph stream"


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    candidates = low_signal_runs(japanese)
    font_bitmap = [
        row
        for row in candidates
        if FONT_BITMAP_BANK_START
        <= int(row["start_int"])
        < FONT_BITMAP_BANK_END
    ]
    class_sprite_graphics = [
        row
        for row in candidates
        if CLASS_SPRITE_GRAPHICS_BANK_START
        <= int(row["start_int"])
        < CLASS_SPRITE_GRAPHICS_BANK_END
    ]
    item_name_graphics = [
        row
        for row in candidates
        if ITEM_NAME_GRAPHICS_BANK_START
        <= int(row["start_int"])
        < ITEM_NAME_GRAPHICS_BANK_END
    ]
    system_graphics_ending = [
        row
        for row in candidates
        if SYSTEM_GRAPHICS_ENDING_BANK_START
        <= int(row["start_int"])
        < SYSTEM_GRAPHICS_ENDING_BANK_END
    ]
    ending_scenario = [
        row
        for row in candidates
        if ENDING_SCENARIO_BANK_START
        <= int(row["start_int"])
        < ENDING_SCENARIO_BANK_END
    ]
    text_ui = [
        row
        for row in candidates
        if TEXT_UI_BANK_START <= int(row["start_int"]) < TEXT_UI_BANK_END
    ]
    compressed_resources = [
        row
        for row in candidates
        if COMPRESSED_RESOURCE_BANK_START
        <= int(row["start_int"])
        < COMPRESSED_RESOURCE_BANK_END
    ]
    compressed_resource_bank = compressed_resource_candidate_inventory(
        japanese, compressed_resources
    )
    executable_tail = [
        row
        for row in candidates
        if EXECUTABLE_TAIL_START
        <= int(row["start_int"])
        < EXECUTABLE_TAIL_END
    ]
    executable_tail_bank = executable_tail_candidate_inventory(
        japanese, executable_tail
    )
    executable_renderer = [
        row
        for row in candidates
        if EXECUTABLE_RENDERER_START
        <= int(row["start_int"])
        < EXECUTABLE_RENDERER_END
    ]
    executable_renderer_bank = executable_renderer_candidate_inventory(
        japanese, executable_renderer
    )
    executable_gameplay = [
        row
        for row in candidates
        if any(
            start <= int(row["start_int"]) < end
            for start, end, _, _ in EXECUTABLE_GAMEPLAY_SEGMENTS
        )
    ]
    executable_gameplay_bank = executable_gameplay_candidate_inventory(
        japanese, executable_gameplay
    )
    executable_auxiliary = [
        row
        for row in candidates
        if EXECUTABLE_AUXILIARY_START
        <= int(row["start_int"])
        < EXECUTABLE_AUXILIARY_END
    ]
    executable_auxiliary_bank = executable_auxiliary_candidate_inventory(
        japanese, executable_auxiliary
    )
    executable_startup = [
        row
        for row in candidates
        if EXECUTABLE_STARTUP_START
        <= int(row["start_int"])
        < EXECUTABLE_STARTUP_END
    ]
    executable_startup_bank = executable_startup_candidate_inventory(
        japanese, executable_startup
    )
    executable_core_a = [
        row
        for row in candidates
        if EXECUTABLE_CORE_A_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_A_END
    ]
    executable_core_a_bank = executable_core_a_candidate_inventory(
        japanese, executable_core_a
    )
    executable_core_b = [
        row
        for row in candidates
        if EXECUTABLE_CORE_B_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_B_END
    ]
    executable_core_b_bank = executable_core_b_candidate_inventory(
        japanese, executable_core_b
    )
    executable_core_c = [
        row
        for row in candidates
        if EXECUTABLE_CORE_C_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_C_END
    ]
    executable_core_c_bank = executable_core_c_candidate_inventory(
        japanese, executable_core_c
    )
    executable_core_d = [
        row
        for row in candidates
        if EXECUTABLE_CORE_D_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_D_END
    ]
    executable_core_d_bank = executable_core_d_candidate_inventory(
        japanese, executable_core_d
    )
    executable_core_e = [
        row
        for row in candidates
        if EXECUTABLE_CORE_E_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_E_END
    ]
    executable_core_e_bank = executable_core_e_candidate_inventory(
        japanese, executable_core_e
    )
    executable_core_f = [
        row
        for row in candidates
        if EXECUTABLE_CORE_F_START
        <= int(row["start_int"])
        < EXECUTABLE_CORE_F_END
    ]
    executable_core_f_bank = executable_core_f_candidate_inventory(
        japanese, executable_core_f
    )

    font_bitmap_addresses = {
        int(row["start_int"]) for row in font_bitmap
    }
    font_bitmap_absolute = aligned_absolute_references(
        japanese, font_bitmap_addresses
    )
    font_bitmap_pc_relative = pc_relative_lea_pea_references(
        japanese, font_bitmap_addresses
    )
    font_bitmap_representatives = []
    for row in font_bitmap:
        start = int(row["start_int"])
        if start not in FONT_BITMAP_REPRESENTATIVE_ADDRESSES:
            continue
        end = int(row["end_int"])
        context_start, context = word_context(japanese, start, end)
        font_bitmap_representatives.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": "font_bitmap_false_positive",
                "owner": "packed Japanese 16x16 glyph pixels",
                "glyph_index": (start - FONT_BITMAP_BANK_START)
                // FONT_BITMAP_GLYPH_BYTES,
                "glyph_byte_offset": (start - FONT_BITMAP_BANK_START)
                % FONT_BITMAP_GLYPH_BYTES,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in font_bitmap_absolute.get(start, [])
                ],
            }
        )

    class_sprite_graphics_addresses = {
        int(row["start_int"]) for row in class_sprite_graphics
    }
    class_sprite_graphics_absolute = aligned_absolute_references(
        japanese, class_sprite_graphics_addresses
    )
    class_sprite_graphics_pc_relative = pc_relative_lea_pea_references(
        japanese, class_sprite_graphics_addresses
    )
    class_sprite_graphics_rows = []
    class_sprite_graphics_reference_reviews = []
    for row in class_sprite_graphics:
        start = int(row["start_int"])
        end = int(row["end_int"])
        category, owner = CLASS_SPRITE_GRAPHICS_REVIEWS.get(
            start, ("unclassified", "requires manual ownership review")
        )
        context_start, context = word_context(japanese, start, end)
        class_sprite_graphics_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in class_sprite_graphics_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in class_sprite_graphics_pc_relative.get(
                        start, []
                    )
                ],
            }
        )
        for reference in class_sprite_graphics_absolute.get(start, []):
            review = CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS.get(
                (start, reference)
            )
            if review is None:
                classification = "unclassified"
                evidence = "requires instruction/data-boundary review"
            else:
                classification, evidence = review
            class_sprite_graphics_reference_reviews.append(
                {
                    "target": f"0x{start:06X}",
                    "address": f"0x{reference:06X}",
                    "classification": classification,
                    "evidence": evidence,
                }
            )

    item_name_graphics_addresses = {
        int(row["start_int"]) for row in item_name_graphics
    }
    item_name_graphics_absolute = aligned_absolute_references(
        japanese, item_name_graphics_addresses
    )
    item_name_graphics_pc_relative = pc_relative_lea_pea_references(
        japanese, item_name_graphics_addresses
    )
    item_name_graphics_rows = []
    item_name_graphics_reference_reviews = []
    for row in item_name_graphics:
        start = int(row["start_int"])
        end = int(row["end_int"])
        category, owner = ITEM_NAME_GRAPHICS_REVIEWS.get(
            start, ("unclassified", "requires manual ownership review")
        )
        context_start, context = word_context(japanese, start, end)
        item_name_graphics_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in item_name_graphics_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in item_name_graphics_pc_relative.get(
                        start, []
                    )
                ],
            }
        )
        for reference in item_name_graphics_absolute.get(start, []):
            review = ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS.get(
                (start, reference)
            )
            if review is None:
                classification = "unclassified"
                evidence = "requires instruction/data-boundary review"
            else:
                classification, evidence = review
            item_name_graphics_reference_reviews.append(
                {
                    "target": f"0x{start:06X}",
                    "address": f"0x{reference:06X}",
                    "classification": classification,
                    "evidence": evidence,
                }
            )

    system_graphics_ending_addresses = {
        int(row["start_int"]) for row in system_graphics_ending
    }
    system_graphics_ending_absolute = aligned_absolute_references(
        japanese, system_graphics_ending_addresses
    )
    system_graphics_ending_pc_relative = pc_relative_lea_pea_references(
        japanese, system_graphics_ending_addresses
    )
    system_graphics_ending_rows = []
    for row in system_graphics_ending:
        start = int(row["start_int"])
        end = int(row["end_int"])
        if is_word_stream_byte_lane(japanese, start, end):
            category = "word_stream_byte_false_positive"
            owner = system_graphics_word_owner(start)
        elif start in SYSTEM_GRAPHICS_ENDING_REVIEWS:
            category, owner = SYSTEM_GRAPHICS_ENDING_REVIEWS[start]
        else:
            category = "unclassified"
            owner = "requires manual ownership review"
        context_start, context = word_context(japanese, start, end)
        system_graphics_ending_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in system_graphics_ending_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in system_graphics_ending_pc_relative.get(
                        start, []
                    )
                ],
            }
        )

    addresses = {int(row["start_int"]) for row in text_ui}
    reviewed_addresses = set(TEXT_UI_REVIEWS)
    missing_reviews = sorted(addresses - reviewed_addresses)
    stale_reviews = sorted(reviewed_addresses - addresses)

    absolute = aligned_absolute_references(japanese, addresses)
    pc_relative = pc_relative_lea_pea_references(japanese, addresses)
    detailed_rows = []
    for row in text_ui:
        start = int(row["start_int"])
        end = int(row["end_int"])
        category, owner = TEXT_UI_REVIEWS.get(
            start, ("unclassified", "requires manual ownership review")
        )
        context_start, context = word_context(japanese, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}" for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    ending_scenario_addresses = {
        int(row["start_int"]) for row in ending_scenario
    }
    ending_scenario_absolute = aligned_absolute_references(
        japanese, ending_scenario_addresses
    )
    ending_scenario_pc_relative = pc_relative_lea_pea_references(
        japanese, ending_scenario_addresses
    )
    ending_scenario_rows = []
    for row in ending_scenario:
        start = int(row["start_int"])
        end = int(row["end_int"])
        if start == SCENARIO_LEVEL_PREFIX:
            category = "retained_compact_english_ui"
            owner = "scenario briefing unit-level prefix"
        elif is_word_stream_byte_lane(japanese, start, end):
            category = "word_stream_byte_false_positive"
            owner = ending_scenario_owner(start)
        elif start in ENDING_SCENARIO_STRUCTURED_REVIEWS:
            category = "structured_layout_false_positive"
            owner = ENDING_SCENARIO_STRUCTURED_REVIEWS[start]
        else:
            category = "unclassified"
            owner = "requires manual ownership review"
        context_start, context = word_context(japanese, start, end)
        ending_scenario_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in ending_scenario_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in ending_scenario_pc_relative.get(start, [])
                ],
            }
        )

    kind_counts = Counter(str(row["kind"]) for row in candidates)
    region_counts = {
        kind: dict(
            sorted(
                Counter(
                    str(row["region"])
                    for row in candidates
                    if row["kind"] == kind
                ).items()
            )
        )
        for kind in ("halfwidth", "ascii")
    }
    category_counts = Counter(str(row["category"]) for row in detailed_rows)
    font_bitmap_kind_counts = Counter(
        str(row["kind"]) for row in font_bitmap
    )
    class_sprite_graphics_category_counts = Counter(
        str(row["category"]) for row in class_sprite_graphics_rows
    )
    item_name_graphics_category_counts = Counter(
        str(row["category"]) for row in item_name_graphics_rows
    )
    ending_scenario_category_counts = Counter(
        str(row["category"]) for row in ending_scenario_rows
    )
    system_graphics_ending_category_counts = Counter(
        str(row["category"]) for row in system_graphics_ending_rows
    )
    system_graphics_ending_reviewed_addresses = (
        set(SYSTEM_GRAPHICS_ENDING_REVIEWS)
        | {
            int(row["address"], 16)
            for row in system_graphics_ending_rows
            if row["category"] == "word_stream_byte_false_positive"
        }
    )
    item_name_graphics_reference_pairs = {
        (target, reference)
        for target, references in item_name_graphics_absolute.items()
        for reference in references
    }
    class_sprite_graphics_reference_pairs = {
        (target, reference)
        for target, references in class_sprite_graphics_absolute.items()
        for reference in references
    }
    ending_scenario_reviewed_addresses = (
        set(ENDING_SCENARIO_STRUCTURED_REVIEWS)
        | {SCENARIO_LEVEL_PREFIX}
        | {
            int(row["address"], 16)
            for row in ending_scenario_rows
            if row["category"] == "word_stream_byte_false_positive"
        }
    )
    return {
        "warning": (
            "This scan inventories maximal FF-terminated half-width/uppercase-ASCII "
            "runs with only one or two signal bytes. Most are binary coincidences. "
            "The 0x030000..0x17FFFF executable-tail/font/class/sprite/item/name/graphics/"
            "system/ending/scenario/text/UI/compressed-resource-bank "
            "candidates are classified here. Exact aligned 32-bit and LEA/PEA "
            "PC-relative references do not exclude base-relative, indexed, or "
            "dynamic access."
        ),
        "source_sha256": hashlib.sha256(japanese).hexdigest(),
        "scan_end": f"0x{SCAN_END:06X}",
        "candidate_count": len(candidates),
        "kind_counts": dict(sorted(kind_counts.items())),
        "region_counts": region_counts,
        "font_bitmap_bank": {
            "range": "0x040000..0x050000",
            "glyph_bytes": FONT_BITMAP_GLYPH_BYTES,
            "glyph_count": (
                FONT_BITMAP_BANK_END - FONT_BITMAP_BANK_START
            )
            // FONT_BITMAP_GLYPH_BYTES,
            "source_sha256": hashlib.sha256(
                japanese[FONT_BITMAP_BANK_START:FONT_BITMAP_BANK_END]
            ).hexdigest(),
            "expected_source_sha256": FONT_BITMAP_SOURCE_SHA256,
            "source_layout_valid": (
                hashlib.sha256(
                    japanese[FONT_BITMAP_BANK_START:FONT_BITMAP_BANK_END]
                ).hexdigest()
                == FONT_BITMAP_SOURCE_SHA256
            ),
            "candidate_count": len(font_bitmap),
            "kind_counts": dict(sorted(font_bitmap_kind_counts.items())),
            "category_counts": {
                "font_bitmap_false_positive": len(font_bitmap)
            },
            "unclassified_count": 0,
            "candidate_manifest_sha256": candidate_manifest_sha256(
                font_bitmap
            ),
            "missing_representative_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    FONT_BITMAP_REPRESENTATIVE_ADDRESSES
                    - font_bitmap_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(references)
                for references in font_bitmap_absolute.values()
            ),
            "aligned_absolute_32_references": [
                {
                    "target": f"0x{target:06X}",
                    "addresses": [
                        f"0x{address:06X}" for address in addresses
                    ],
                }
                for target, addresses in sorted(font_bitmap_absolute.items())
            ],
            "pc_relative_lea_pea_reference_count": sum(
                len(references)
                for references in font_bitmap_pc_relative.values()
            ),
            "pc_relative_lea_pea_references": [
                {
                    "target": f"0x{target:06X}",
                    "references": [
                        {
                            "instruction": reference["instruction"],
                            "address": (
                                f"0x{int(reference['address']):06X}"
                            ),
                            "displacement": reference["displacement"],
                        }
                        for reference in references
                    ],
                }
                for target, references in sorted(
                    font_bitmap_pc_relative.items()
                )
            ],
            "representative_candidates": font_bitmap_representatives,
        },
        "class_sprite_graphics_bank": {
            "range": "0x050000..0x060000",
            "candidate_count": len(class_sprite_graphics_rows),
            "category_counts": dict(
                sorted(class_sprite_graphics_category_counts.items())
            ),
            "unclassified_count": class_sprite_graphics_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    class_sprite_graphics_addresses
                    - set(CLASS_SPRITE_GRAPHICS_REVIEWS)
                )
            ],
            "stale_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(CLASS_SPRITE_GRAPHICS_REVIEWS)
                    - class_sprite_graphics_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in class_sprite_graphics_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in class_sprite_graphics_rows
            ),
            "aligned_reference_reviews": class_sprite_graphics_reference_reviews,
            "missing_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    class_sprite_graphics_reference_pairs
                    - set(CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                )
            ],
            "stale_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    set(CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                    - class_sprite_graphics_reference_pairs
                )
            ],
            "candidates": class_sprite_graphics_rows,
        },
        "item_name_graphics_bank": {
            "range": "0x060000..0x080000",
            "candidate_count": len(item_name_graphics_rows),
            "category_counts": dict(
                sorted(item_name_graphics_category_counts.items())
            ),
            "unclassified_count": item_name_graphics_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    item_name_graphics_addresses
                    - set(ITEM_NAME_GRAPHICS_REVIEWS)
                )
            ],
            "stale_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(ITEM_NAME_GRAPHICS_REVIEWS)
                    - item_name_graphics_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in item_name_graphics_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in item_name_graphics_rows
            ),
            "aligned_reference_reviews": item_name_graphics_reference_reviews,
            "missing_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    item_name_graphics_reference_pairs
                    - set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                )
            ],
            "stale_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                    - item_name_graphics_reference_pairs
                )
            ],
            "candidates": item_name_graphics_rows,
        },
        "system_graphics_ending_bank": {
            "range": "0x080000..0x090000",
            "candidate_count": len(system_graphics_ending_rows),
            "category_counts": dict(
                sorted(system_graphics_ending_category_counts.items())
            ),
            "unclassified_count": system_graphics_ending_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    system_graphics_ending_addresses
                    - system_graphics_ending_reviewed_addresses
                )
            ],
            "stale_structured_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(SYSTEM_GRAPHICS_ENDING_REVIEWS)
                    - system_graphics_ending_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in system_graphics_ending_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in system_graphics_ending_rows
            ),
            "candidates": system_graphics_ending_rows,
        },
        "ending_scenario_bank": {
            "range": "0x090000..0x0A0000",
            "candidate_count": len(ending_scenario_rows),
            "category_counts": dict(
                sorted(ending_scenario_category_counts.items())
            ),
            "unclassified_count": ending_scenario_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    ending_scenario_addresses
                    - ending_scenario_reviewed_addresses
                )
            ],
            "stale_structured_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(ENDING_SCENARIO_STRUCTURED_REVIEWS)
                    - ending_scenario_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in ending_scenario_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in ending_scenario_rows
            ),
            "retained_level_prefix": {
                "address": f"0x{SCENARIO_LEVEL_PREFIX:06X}",
                "source_bytes": japanese[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ].hex(" ").upper(),
                "current_bytes": korean[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ].hex(" ").upper(),
                "text": "L-",
                "hook": f"0x{SCENARIO_LEVEL_PREFIX_HOOK:06X}",
                "hook_bytes": japanese[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ].hex(" ").upper(),
                "source_hook_valid": japanese[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ]
                == SCENARIO_LEVEL_PREFIX_HOOK_BYTES,
                "current_hook_preserved": korean[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ]
                == SCENARIO_LEVEL_PREFIX_HOOK_BYTES,
                "current_record_preserved": korean[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ]
                == b"L-\xFF",
                "live_verified": True,
                "evidence": SCENARIO_LEVEL_PREFIX_EVIDENCE,
            },
            "candidates": ending_scenario_rows,
        },
        "text_ui_bank": {
            "range": "0x0A0000..0x0B0000",
            "candidate_count": len(detailed_rows),
            "category_counts": dict(sorted(category_counts.items())),
            "unclassified_count": category_counts.get("unclassified", 0),
            "missing_review_addresses": [
                f"0x{address:06X}" for address in missing_reviews
            ],
            "stale_review_addresses": [
                f"0x{address:06X}" for address in stale_reviews
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in detailed_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in detailed_rows
            ),
            "candidates": detailed_rows,
        },
        "compressed_resource_bank": compressed_resource_bank,
        "executable_tail_bank": executable_tail_bank,
        "executable_renderer_bank": executable_renderer_bank,
        "executable_gameplay_bank": executable_gameplay_bank,
        "executable_auxiliary_bank": executable_auxiliary_bank,
        "executable_startup_bank": executable_startup_bank,
        "executable_core_a_bank": executable_core_a_bank,
        "executable_core_b_bank": executable_core_b_bank,
        "executable_core_c_bank": executable_core_c_bank,
        "executable_core_d_bank": executable_core_d_bank,
        "executable_core_e_bank": executable_core_e_bank,
        "executable_core_f_bank": executable_core_f_bank,
    }


def markdown_report(result: dict[str, object]) -> str:
    font_bank = result["font_bitmap_bank"]
    class_bank = result["class_sprite_graphics_bank"]
    item_bank = result["item_name_graphics_bank"]
    system_bank = result["system_graphics_ending_bank"]
    ending_bank = result["ending_scenario_bank"]
    level_prefix = ending_bank["retained_level_prefix"]
    bank = result["text_ui_bank"]
    compressed_bank = result["compressed_resource_bank"]
    executable_tail_bank = result["executable_tail_bank"]
    executable_renderer_bank = result["executable_renderer_bank"]
    executable_gameplay_bank = result["executable_gameplay_bank"]
    executable_auxiliary_bank = result["executable_auxiliary_bank"]
    executable_startup_bank = result["executable_startup_bank"]
    executable_core_a_bank = result["executable_core_a_bank"]
    executable_core_b_bank = result["executable_core_b_bank"]
    executable_core_c_bank = result["executable_core_c_bank"]
    executable_core_d_bank = result["executable_core_d_bank"]
    executable_core_e_bank = result["executable_core_e_bank"]
    executable_core_f_bank = result["executable_core_f_bank"]
    lines = [
        "# Short Inline Byte Candidate Inventory",
        "",
        "Generated by `python3 tools/jp_short_inline_byte_inventory.py`.",
        "",
        str(result["warning"]),
        "",
        f"- Low-signal candidates: {result['candidate_count']}",
        f"- Half-width candidates: {result['kind_counts']['halfwidth']}",
        f"- Uppercase ASCII candidates: {result['kind_counts']['ascii']}",
        f"- Font-bitmap-bank candidates: {font_bank['candidate_count']}",
        (
            "- Font-bitmap-bank unclassified: "
            f"{font_bank['unclassified_count']}"
        ),
        (
            "- Class/sprite/graphics-bank candidates: "
            f"{class_bank['candidate_count']}"
        ),
        (
            "- Class/sprite/graphics-bank unclassified: "
            f"{class_bank['unclassified_count']}"
        ),
        (
            "- Item/name/graphics-bank candidates: "
            f"{item_bank['candidate_count']}"
        ),
        (
            "- Item/name/graphics-bank unclassified: "
            f"{item_bank['unclassified_count']}"
        ),
        (
            "- System/graphics/ending-bank candidates: "
            f"{system_bank['candidate_count']}"
        ),
        (
            "- System/graphics/ending-bank unclassified: "
            f"{system_bank['unclassified_count']}"
        ),
        (
            "- Ending/scenario-bank candidates: "
            f"{ending_bank['candidate_count']}"
        ),
        (
            "- Ending/scenario-bank unclassified: "
            f"{ending_bank['unclassified_count']}"
        ),
        f"- Text/UI-bank candidates: {bank['candidate_count']}",
        f"- Text/UI-bank unclassified: {bank['unclassified_count']}",
        (
            "- Compressed-resource-bank candidates: "
            f"{compressed_bank['candidate_count']}"
        ),
        (
            "- Compressed-resource-bank unclassified: "
            f"{compressed_bank['unclassified_count']}"
        ),
        (
            "- Executable-tail candidates: "
            f"{executable_tail_bank['candidate_count']}"
        ),
        (
            "- Executable-tail unclassified: "
            f"{executable_tail_bank['unclassified_count']}"
        ),
        (
            "- Executable-renderer candidates: "
            f"{executable_renderer_bank['candidate_count']}"
        ),
        (
            "- Executable-renderer unclassified: "
            f"{executable_renderer_bank['unclassified_count']}"
        ),
        (
            "- Executable-gameplay candidates: "
            f"{executable_gameplay_bank['candidate_count']}"
        ),
        (
            "- Executable-gameplay unclassified: "
            f"{executable_gameplay_bank['unclassified_count']}"
        ),
        (
            "- Executable-auxiliary candidates: "
            f"{executable_auxiliary_bank['candidate_count']}"
        ),
        (
            "- Executable-auxiliary unclassified: "
            f"{executable_auxiliary_bank['unclassified_count']}"
        ),
        (
            "- Executable-startup candidates: "
            f"{executable_startup_bank['candidate_count']}"
        ),
        (
            "- Executable-startup unclassified: "
            f"{executable_startup_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-A candidates: "
            f"{executable_core_a_bank['candidate_count']}"
        ),
        (
            "- Executable-core-A unclassified: "
            f"{executable_core_a_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-B candidates: "
            f"{executable_core_b_bank['candidate_count']}"
        ),
        (
            "- Executable-core-B unclassified: "
            f"{executable_core_b_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-C candidates: "
            f"{executable_core_c_bank['candidate_count']}"
        ),
        (
            "- Executable-core-C unclassified: "
            f"{executable_core_c_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-D candidates: "
            f"{executable_core_d_bank['candidate_count']}"
        ),
        (
            "- Executable-core-D unclassified: "
            f"{executable_core_d_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-E candidates: "
            f"{executable_core_e_bank['candidate_count']}"
        ),
        (
            "- Executable-core-E unclassified: "
            f"{executable_core_e_bank['unclassified_count']}"
        ),
        (
            "- Executable-core-F candidates: "
            f"{executable_core_f_bank['candidate_count']}"
        ),
        (
            "- Executable-core-F unclassified: "
            f"{executable_core_f_bank['unclassified_count']}"
        ),
        (
            "- Exact aligned 32-bit references to text/UI-bank candidates: "
            f"{bank['aligned_absolute_32_reference_count']}"
        ),
        (
            "- Exact `LEA d16(PC)`/`PEA d16(PC)` references to text/UI-bank "
            f"candidates: {bank['pc_relative_lea_pea_reference_count']}"
        ),
        "",
        "## Region Counts",
        "",
        "| Region | Half-width | ASCII |",
        "| --- | ---: | ---: |",
    ]
    regions = sorted(
        set(result["region_counts"]["halfwidth"])
        | set(result["region_counts"]["ascii"])
    )
    for region in regions:
        lines.append(
            f"| `{region}` | "
            f"{result['region_counts']['halfwidth'].get(region, 0)} | "
            f"{result['region_counts']['ascii'].get(region, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Reviewed Executable-Core-F Candidates",
            "",
            (
                f"- The source-locked `{executable_core_f_bank['range']}` "
                "region contains one exact 68000 code stream followed by "
                "one directly referenced candidate-free pattern table."
            ),
            (
                f"- Source SHA-256: `{executable_core_f_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_f_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_f_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_f_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Code instructions: "
                f"{executable_core_f_bank['code_segment']['linear_instruction_count']}; "
                f"`RTS`: "
                f"{executable_core_f_bank['code_segment']['rts_instruction_count']}."
            ),
            (
                "- Pattern values: "
                + ", ".join(
                    f"`0x{value:04X}`"
                    for value in executable_core_f_bank[
                        "pattern_table"
                    ]["values"]
                )
                + "; reference operand at "
                + ", ".join(
                    f"`{address}`"
                    for address in executable_core_f_bank[
                        "pattern_table"
                    ]["aligned_absolute_32_references"]
                )
                + "."
            ),
            (
                "- Candidate-target aligned four-byte windows: "
                f"{executable_core_f_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_f_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "## Reviewed Executable-Core-E Candidates",
            "",
            (
                f"- The source-locked `{executable_core_e_bank['range']}` "
                "region is one exact contiguous 68000 instruction stream."
            ),
            (
                f"- Source SHA-256: `{executable_core_e_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_e_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_e_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_e_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Instructions: "
                f"{executable_core_e_bank['linear_instruction_count']}; "
                f"`RTS`: {executable_core_e_bank['rts_instruction_count']}."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_core_e_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_e_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "## Reviewed Executable-Core-D Candidates",
            "",
            (
                f"- The source-locked `{executable_core_d_bank['range']}` "
                "region contains five exact 68000 instruction streams and "
                "five explicit candidate-free data tables."
            ),
            (
                f"- Source SHA-256: `{executable_core_d_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_d_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_d_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_d_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_core_d_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_d_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Code segment | Bytes | Instructions | Candidates | Source SHA-256 |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for segment in executable_core_d_bank["code_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['source_bytes']} | "
            f"{segment['linear_instruction_count']} | "
            f"{segment['candidate_count']} | "
            f"`{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "| Data segment | Owner | Bytes | Candidates | Source SHA-256 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for segment in executable_core_d_bank["data_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['owner']} | "
            f"{segment['source_bytes']} | {segment['candidate_count']} | "
            f"`{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "The 35 aligned four-byte windows target four odd candidate",
            "addresses. Each target is source-locked inside a `DBRA` or",
            "`MOVE` instruction rather than at an executable entry boundary.",
            "",
            "## Reviewed Executable-Core-C Candidates",
            "",
            (
                f"- The source-locked `{executable_core_c_bank['range']}` "
                "region contains two exact 68000 instruction streams and two "
                "explicit candidate-free data tables."
            ),
            (
                f"- Source SHA-256: `{executable_core_c_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_c_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_c_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_c_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_core_c_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_c_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Code segment | Bytes | Instructions | Candidates | Source SHA-256 |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for segment in executable_core_c_bank["code_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['source_bytes']} | "
            f"{segment['linear_instruction_count']} | "
            f"{segment['candidate_count']} | "
            f"`{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "| Data segment | Owner | Bytes | Candidates | Source SHA-256 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for segment in executable_core_c_bank["data_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['owner']} | "
            f"{segment['source_bytes']} | {segment['candidate_count']} | "
            f"`{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "The first code byte at `0x00D49E` is also the final ASCII `!`",
            "of the preceding source marker. Independent Capstone tests require",
            "both code streams to end exactly at their declared boundaries.",
            "",
            "## Reviewed Executable-Core-B Candidates",
            "",
            (
                f"- The source-locked `{executable_core_b_bank['range']}` "
                "region is one exact contiguous 68000 instruction stream."
            ),
            (
                f"- Source SHA-256: `{executable_core_b_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_b_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_b_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_b_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- The code segment contains "
                f"{executable_core_b_bank['linear_instruction_count']} "
                "instructions and "
                f"{executable_core_b_bank['candidate_count']} candidates."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_core_b_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_b_bank['pc_relative_lea_pea_reference_count']}."
            ),
            (
                "- The following source-locked ASCII boundary marker is "
                f"`{executable_core_b_bank['following_ascii_marker']['raw_ascii']}` "
                "at "
                f"`{executable_core_b_bank['following_ascii_marker']['range']}`."
            ),
            "",
            "Independent Capstone tests require the stream to cover every byte,",
            "end on its final `RTS`, and contain every candidate span. The",
            "indexed jump block at `0x00B69A` resolves through valid `BRA`",
            "instructions rather than an embedded byte-string table.",
            "",
            "## Reviewed Executable-Core-A Candidates",
            "",
            (
                f"- The source-locked `{executable_core_a_bank['range']}` "
                "region contains one exact 68000 instruction stream followed "
                "by its PC-indexed dispatch offset table."
            ),
            (
                f"- Source SHA-256: `{executable_core_a_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_core_a_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_core_a_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_core_a_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- The code segment contains "
                f"{executable_core_a_bank['code_segment']['linear_instruction_count']} "
                "instructions and "
                f"{executable_core_a_bank['code_segment']['candidate_count']} "
                "candidates. The following dispatch table contains "
                f"{executable_core_a_bank['dispatch_table']['candidate_count']}."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_core_a_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_core_a_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Segment | Bytes | Instructions | Candidates | Source SHA-256 |",
            "| --- | ---: | ---: | ---: | --- |",
            (
                f"| `{executable_core_a_bank['code_segment']['range']}` | "
                f"{executable_core_a_bank['code_segment']['source_bytes']} | "
                f"{executable_core_a_bank['code_segment']['linear_instruction_count']} | "
                f"{executable_core_a_bank['code_segment']['candidate_count']} | "
                f"`{executable_core_a_bank['code_segment']['source_sha256']}` |"
            ),
            (
                f"| `{executable_core_a_bank['dispatch_table']['range']}` | "
                f"{executable_core_a_bank['dispatch_table']['source_bytes']} | "
                "0 | "
                f"{executable_core_a_bank['dispatch_table']['candidate_count']} | "
                f"`{executable_core_a_bank['dispatch_table']['source_sha256']}` |"
            ),
            "",
            "Independent Capstone tests require the code segment to end on its",
            "final `RTS`. The next ten bytes are the exact five-word table",
            "read by the following PC-indexed dispatch routine.",
            "",
            "## Reviewed Executable-Startup Candidates",
            "",
            (
                f"- The source-locked `{executable_startup_bank['range']}` "
                "startup/interrupt region is split into five exact 68000 "
                "instruction segments and four explicit data tables."
            ),
            (
                f"- Source SHA-256: `{executable_startup_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_startup_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_startup_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_startup_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- The preceding "
                f"`{executable_startup_bank['preceding_ff_padding']['range']}` "
                "gap contains "
                f"{executable_startup_bank['preceding_ff_padding']['source_bytes']} "
                "bytes of `0xFF` padding and no candidate."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_startup_bank['aligned_absolute_32_reference_count']} "
                f"across "
                f"{len(executable_startup_bank['aligned_absolute_32_references'])} "
                "candidate starts; exact `LEA d16(PC)`/`PEA d16(PC)` "
                f"references: "
                f"{executable_startup_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Code segment | Bytes | Instructions | Candidates | Source SHA-256 |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for segment in executable_startup_bank["code_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['source_bytes']} | "
            f"{segment['linear_instruction_count']} | "
            f"{segment['candidate_count']} | `{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "| Data segment | Owner | Candidates | Source SHA-256 |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for segment in executable_startup_bank["data_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['owner']} | "
            f"{segment['candidate_count']} | `{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "Independent Capstone tests require each code segment to end exactly",
            "at its declared boundary and cover all 40 code-candidate spans.",
            "Candidate `0x008101` remains owned by the source-locked startup",
            "configuration table rather than an executable byte string.",
            "",
            "## Reviewed Executable-Auxiliary Candidates",
            "",
            (
                f"- The source-locked `{executable_auxiliary_bank['range']}` "
                "region is split into five contiguous 68000 instruction "
                "segments and four explicit lookup/pointer data segments."
            ),
            (
                f"- Source SHA-256: `{executable_auxiliary_bank['source_sha256']}`; "
                "candidate manifest SHA-256: "
                f"`{executable_auxiliary_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_auxiliary_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_auxiliary_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- The 38-entry long-pointer table resolves into 36 unique "
                "16-bit word records. Four candidates are low bytes of word "
                "`0x004A` immediately before a `0xFFFF` record terminator."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_auxiliary_bank['aligned_absolute_32_reference_count']} "
                f"across "
                f"{len(executable_auxiliary_bank['aligned_absolute_32_references'])} "
                "candidate starts; exact `LEA d16(PC)`/`PEA d16(PC)` "
                f"references: "
                f"{executable_auxiliary_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Code segment | Bytes | Instructions | Candidates | Source SHA-256 |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for segment in executable_auxiliary_bank["code_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['source_bytes']} | "
            f"{segment['linear_instruction_count']} | "
            f"{segment['candidate_count']} | `{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "| Data segment | Owner | Candidates | Source SHA-256 |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for segment in executable_auxiliary_bank["data_segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['owner']} | "
            f"{segment['candidate_count']} | `{segment['source_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "Independent Capstone tests require each code segment to end exactly",
            "at its declared boundary and cover all 123 code-candidate spans.",
            "The other four rows retain their containing word, following",
            "terminator, record start, and pointer-table entries in the JSON report.",
            "",
            "## Reviewed Executable-Gameplay Candidates",
            "",
            (
                "- Two source-locked contiguous 68000 instruction segments cover "
                f"{executable_gameplay_bank['candidate_count']} candidates around "
                "one explicitly separated 20-byte numeric lookup table."
            ),
            (
                "- Combined candidate manifest SHA-256: "
                f"`{executable_gameplay_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_gameplay_bank['source_layout_valid']}`)."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{executable_gameplay_bank['aligned_absolute_32_reference_count']} "
                f"across "
                f"{len(executable_gameplay_bank['aligned_absolute_32_references'])} "
                "odd candidate addresses; exact `LEA d16(PC)`/`PEA d16(PC)` "
                "references: "
                f"{executable_gameplay_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Instruction segment | Bytes | Instructions | Candidates | Source SHA-256 | Candidate manifest |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for segment in executable_gameplay_bank["segments"]:
        lines.append(
            f"| `{segment['range']}` | {segment['source_bytes']} | "
            f"{segment['linear_instruction_count']} | "
            f"{segment['candidate_count']} | `{segment['source_sha256']}` | "
            f"`{segment['candidate_manifest_sha256']}` |"
        )
    lines.extend(
        [
            "",
            (
                f"The gap `{executable_gameplay_bank['numeric_table_gap']['range']}` "
                "contains decimal place values and bit/index masks, has no "
                "low-signal candidate, and is deliberately not classified as code."
            ),
            "Every candidate span in the two surrounding segments is independently",
            "covered by a contiguous Capstone 68000 instruction stream. All six",
            "apparent aligned target values are odd addresses, so they cannot be",
            "valid 68000 instruction entry points; they remain instruction bytes.",
            "",
            "## Reviewed Executable-Renderer Candidates",
            "",
            (
                f"- The source-locked `{executable_renderer_bank['range']}` "
                f"block contains {executable_renderer_bank['source_bytes']} "
                f"bytes and "
                f"{executable_renderer_bank['linear_instruction_count']} "
                "contiguous 68000 instructions."
            ),
            (
                f"- Source SHA-256: "
                f"`{executable_renderer_bank['source_sha256']}`; candidate "
                f"manifest SHA-256: "
                f"`{executable_renderer_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_renderer_bank['source_layout_valid']}`)."
            ),
            (
                "- Category total: "
                "`contiguous_instruction_stream_false_positive` "
                f"{executable_renderer_bank['candidate_count']}."
            ),
            (
                "- Exact aligned four-byte references: "
                f"{executable_renderer_bank['aligned_absolute_32_reference_count']} "
                f"across "
                f"{len(executable_renderer_bank['aligned_absolute_32_references'])} "
                "code targets; exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_renderer_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Code target | Exact aligned references |",
            "| --- | --- |",
        ]
    )
    for row in executable_renderer_bank[
        "aligned_absolute_32_references"
    ]:
        lines.append(
            f"| `{row['target']}` | "
            + ", ".join(
                f"`{address}`" for address in row["addresses"]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "All 108 candidate spans are covered by the contiguous instruction",
            "stream in an independent Capstone regression test. The 37 exact",
            "aligned references resolve to four instruction entry points, which",
            "further confirms executable ownership rather than text ownership.",
            "Per-candidate word contexts and references remain in the JSON report.",
            "",
            "## Reviewed Executable-Tail Candidates",
            "",
            (
                f"- The source-locked `{executable_tail_bank['range']}` block "
                f"contains {executable_tail_bank['source_bytes']} bytes and "
                f"{executable_tail_bank['linear_instruction_count']} contiguous "
                "68000 instructions."
            ),
            (
                f"- Source SHA-256: "
                f"`{executable_tail_bank['source_sha256']}`; candidate manifest "
                f"SHA-256: "
                f"`{executable_tail_bank['candidate_manifest_sha256']}` "
                f"(layout valid: "
                f"`{executable_tail_bank['source_layout_valid']}`)."
            ),
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in executable_tail_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte references: "
                f"{executable_tail_bank['aligned_absolute_32_reference_count']}; "
                "exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{executable_tail_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Candidate | Raw | Instruction | Instruction bytes | Classification |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in executable_tail_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['raw_hex']}` | "
            f"`{row['instruction_address']}` | `{row['instruction_bytes']}` | "
            f"`{row['category']}` |"
        )
    lines.extend(
        [
            "",
            "Seventeen rows begin in immediate operands and four begin in opcode",
            "bytes. In every case the scanner treats the following `FF` byte of",
            "an absolute `FFFFFxxx` destination operand as a string terminator.",
            "The full instruction boundary proves these are code bytes, not",
            "standalone Japanese or ASCII strings.",
            "",
            "## Reviewed Compressed-Resource-Bank Candidates",
            "",
            (
                f"- The source-locked `{compressed_bank['range']}` bank "
                f"contains {compressed_bank['resource_count']} resources; "
                f"{compressed_bank['resource_count_with_candidates']} contain "
                "one or more low-signal candidates."
            ),
            (
                f"- Resource pointers run from "
                f"`{compressed_bank['first_resource_pointer']}` to "
                f"`{compressed_bank['last_resource_pointer']}`; the final "
                f"encoded stream ends at "
                f"`{compressed_bank['last_resource_encoded_end']}`."
            ),
            (
                f"- Bank SHA-256: `{compressed_bank['source_sha256']}`; "
                f"pointer-table SHA-256: "
                f"`{compressed_bank['pointer_table_sha256']}` "
                f"(layout valid: `{compressed_bank['source_layout_valid']}`)."
            ),
            (
                f"- Candidate manifest SHA-256: "
                f"`{compressed_bank['candidate_manifest_sha256']}`."
            ),
            (
                "- Category total: "
                "`compressed_resource_payload_false_positive` "
                f"{compressed_bank['candidate_count']}."
            ),
            (
                "- Exact encoded payload bytes: "
                f"{compressed_bank['encoded_payload_bytes']}; alignment/tail "
                f"padding bytes: {compressed_bank['padding_bytes']} "
                f"({compressed_bank['padding_value_counts']})."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{compressed_bank['aligned_absolute_32_reference_count']} "
                f"across "
                f"{len(compressed_bank['aligned_absolute_32_references'])} "
                "targets."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{compressed_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Asset family | Candidate count |",
            "| --- | ---: |",
        ]
    )
    for family, count in compressed_bank[
        "asset_family_candidate_counts"
    ].items():
        lines.append(f"| `{family}` | {count} |")
    lines.extend(
        [
            "",
            "| Representative | Raw | Resource | Asset family | Encoded offset |",
            "| --- | --- | ---: | --- | ---: |",
        ]
    )
    for row in compressed_bank["representative_candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['raw_hex']}` | "
            f"{row['resource_index']} | `{row['asset_family']}` | "
            f"{row['encoded_byte_offset']} |"
        )
    lines.extend(
        [
            "",
            "The pointer table, every type 1/2/3 encoded-stream boundary, the",
            "inter-resource alignment bytes, and the final `FF` tail padding are",
            "parsed independently. All 3,254 candidates lie inside actual encoded",
            "payload bytes; none begins in the pointer table, alignment padding,",
            "or unowned space. Their half-width/ASCII appearance is therefore a",
            "compression-byte coincidence, not untranslated standalone text.",
            "",
            "## Reviewed Font-Bitmap-Bank Candidates",
            "",
            (
                f"- The fixed `{font_bank['range']}` bank contains "
                f"{font_bank['glyph_count']} Japanese 16x16 glyphs at "
                f"{font_bank['glyph_bytes']} bytes each."
            ),
            (
                f"- Source SHA-256: `{font_bank['source_sha256']}` "
                f"(layout valid: `{font_bank['source_layout_valid']}`)."
            ),
            (
                f"- Candidate manifest SHA-256: "
                f"`{font_bank['candidate_manifest_sha256']}`."
            ),
            (
                "- Category total: `font_bitmap_false_positive` "
                f"{font_bank['category_counts']['font_bitmap_false_positive']}."
            ),
            (
                "- Kind totals: "
                + ", ".join(
                    f"`{kind}` {count}"
                    for kind, count in font_bank["kind_counts"].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{font_bank['aligned_absolute_32_reference_count']} across "
                f"{len(font_bank['aligned_absolute_32_references'])} targets."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{font_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Representative | Raw | Glyph index | Byte offset | Word context |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in font_bank["representative_candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['raw_hex']}` | "
            f"{row['glyph_index']} | {row['glyph_byte_offset']} | "
            f"`{row['context_words']}` |"
        )
    lines.extend(
        [
            "",
            "| Bitmap target | Aligned four-byte windows |",
            "| --- | --- |",
        ]
    )
    for row in font_bank["aligned_absolute_32_references"]:
        lines.append(
            f"| `{row['target']}` | "
            + ", ".join(f"`{address}`" for address in row["addresses"])
            + " |"
        )
    lines.extend(
        [
            "",
            "Every byte in this source-locked bank is one of the 64 pixel bytes",
            "for a Japanese 16x16 glyph. The short half-width/ASCII-looking runs",
            "are therefore bitmap coincidences, regardless of whether an aligned",
            "four-byte window is a real glyph/pixel address or a numeric/code",
            "coincidence. They are not standalone byte strings.",
            "",
            "## Reviewed Class/Sprite/Graphics-Bank Candidates",
            "",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in class_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{class_bank['aligned_absolute_32_reference_count']}; all are "
                "reviewed below as non-pointer coincidences."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{class_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in class_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The 57 rows before the commander sprite-map table are packed 4bpp",
            "pixel data. Four rows are byte lanes of class-to-sprite mapping",
            "records. `0x05E949` is the low byte of final class-name pointer",
            "`0x0005E94A` followed by eight padding spaces.",
            "",
            "| Apparent target | Four-byte window | Classification | Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in class_bank["aligned_reference_reviews"]:
        lines.append(
            f"| `{row['target']}` | `{row['address']}` | "
            f"`{row['classification']}` | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "The executable `0x050019` match spans the source and destination",
            "displacements of one `MOVE.B` instruction. The second is a sliding",
            "window in a 16-bit numeric/index row. Neither is an absolute pointer.",
            "",
            "## Reviewed Item/Name/Graphics-Bank Candidates",
            "",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in item_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{item_bank['aligned_absolute_32_reference_count']}; all are "
                "reviewed below as non-pointer coincidences."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{item_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in item_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The seven early rows are packed 4bpp item/system graphics. "
            "`0x061ABB` is the low byte of the final name-table pointer "
            "`0x00061ABC` followed by eight padding spaces. The remaining "
            "75 rows repeat inside packed 4bpp tile/sprite blocks; they are "
            "pixel nibbles, not half-width or ASCII text.",
            "",
            "| Apparent target | Four-byte window | Classification | Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in item_bank["aligned_reference_reviews"]:
        lines.append(
            f"| `{row['target']}` | `{row['address']}` | "
            f"`{row['classification']}` | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "The `0x06121F` match is a sliding four-byte window inside a numeric/",
            "graphics index row. Both `0x070C2A` matches cross a 68000 instruction",
            "boundary: immediate value `0007` is followed by opcode `0C2A`.",
            "They are not absolute pointers.",
            "",
            "## Reviewed System/Graphics/Ending-Bank Candidates",
            "",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in system_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned 32-bit references: "
                f"{system_bank['aligned_absolute_32_reference_count']}."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{system_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in system_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The 13 word-stream rows are low-byte lanes of shared system, magic,",
            "or mercenary-name glyph words. The other 67 addresses are pinned",
            "tilemap/render scripts, sprite frame/coordinate/animation records,",
            "or character-epilogue pointer/selector fields. None is a standalone",
            "user-facing Japanese byte string.",
            "",
            "## Reviewed Ending/Scenario-Bank Candidates",
            "",
            f"- `{level_prefix['address']}` is the byte record `{level_prefix['text']}`.",
            f"  The stock code at `{level_prefix['hook']}` loads it directly before",
            "  drawing each unit's numeric level in the scrolling scenario briefing.",
            "  It is an intentional compact level abbreviation, not untranslated",
            "  Japanese. The current ROM preserves both record and hook, and",
            f"  `{level_prefix['evidence']}` visibly shows `L-5`, `L-4`, and other",
            "  unit levels.",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in ending_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned 32-bit references: "
                f"{ending_bank['aligned_absolute_32_reference_count']}; "
                "the sole reference is the retained `L-` load."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{ending_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Structured address | Raw | Owner |",
            "| --- | --- | --- |",
        ]
    )
    for row in ending_bank["candidates"]:
        if row["category"] != "structured_layout_false_positive":
            continue
        lines.append(
            f"| `{row['address']}` | `{row['raw_hex']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "## Reviewed Text/UI-Bank Candidates",
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The 28 word-stream rows begin on one byte lane of an existing 16-bit glyph",
            "or token word. The remaining 10 rows end at a structured layout boundary.",
            "They are not standalone user-facing Japanese strings and must not be patched",
            "as byte strings. Full word contexts and reference lists are in",
            "`localization/short_inline_byte_candidates.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory one/two-signal FF-terminated inline byte candidates"
    )
    parser.add_argument(
        "--jp-rom",
        type=Path,
        default=Path("roms/original/Langrisser II (Japan).md"),
    )
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean).md"),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("localization/short_inline_byte_candidates.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/short_inline_byte_candidate_inventory.md"),
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    font_bank = result["font_bitmap_bank"]
    class_bank = result["class_sprite_graphics_bank"]
    item_bank = result["item_name_graphics_bank"]
    system_bank = result["system_graphics_ending_bank"]
    ending_bank = result["ending_scenario_bank"]
    bank = result["text_ui_bank"]
    compressed_bank = result["compressed_resource_bank"]
    executable_tail_bank = result["executable_tail_bank"]
    executable_renderer_bank = result["executable_renderer_bank"]
    executable_gameplay_bank = result["executable_gameplay_bank"]
    executable_auxiliary_bank = result["executable_auxiliary_bank"]
    executable_startup_bank = result["executable_startup_bank"]
    executable_core_a_bank = result["executable_core_a_bank"]
    executable_core_b_bank = result["executable_core_b_bank"]
    executable_core_c_bank = result["executable_core_c_bank"]
    executable_core_d_bank = result["executable_core_d_bank"]
    executable_core_e_bank = result["executable_core_e_bank"]
    executable_core_f_bank = result["executable_core_f_bank"]
    print(
        f"{result['candidate_count']} low-signal candidates; "
        f"{font_bank['candidate_count']} font-bitmap-bank, "
        f"{class_bank['candidate_count']} class/sprite/graphics-bank, "
        f"{item_bank['candidate_count']} item/name/graphics-bank, "
        f"{system_bank['candidate_count']} system/graphics/ending-bank, "
        f"{ending_bank['candidate_count']} ending/scenario-bank, and "
        f"{bank['candidate_count']} text/UI-bank, and "
        f"{compressed_bank['candidate_count']} compressed-resource-bank, and "
        f"{executable_tail_bank['candidate_count']} executable-tail, and "
        f"{executable_renderer_bank['candidate_count']} executable-renderer candidates, "
        f"{executable_gameplay_bank['candidate_count']} executable-gameplay candidates, "
        f"{executable_auxiliary_bank['candidate_count']} executable-auxiliary candidates, "
        f"{executable_startup_bank['candidate_count']} executable-startup candidates, "
        f"{executable_core_a_bank['candidate_count']} executable-core-A candidates, "
        f"{executable_core_b_bank['candidate_count']} executable-core-B candidates, "
        f"{executable_core_c_bank['candidate_count']} executable-core-C candidates, "
        f"{executable_core_d_bank['candidate_count']} executable-core-D candidates, "
        f"{executable_core_e_bank['candidate_count']} executable-core-E candidates, "
        f"{executable_core_f_bank['candidate_count']} executable-core-F candidates, "
        f"{font_bank['unclassified_count'] + class_bank['unclassified_count'] + item_bank['unclassified_count'] + system_bank['unclassified_count'] + ending_bank['unclassified_count'] + bank['unclassified_count'] + compressed_bank['unclassified_count'] + executable_tail_bank['unclassified_count'] + executable_renderer_bank['unclassified_count'] + executable_gameplay_bank['unclassified_count'] + executable_auxiliary_bank['unclassified_count'] + executable_startup_bank['unclassified_count'] + executable_core_a_bank['unclassified_count'] + executable_core_b_bank['unclassified_count'] + executable_core_c_bank['unclassified_count'] + executable_core_d_bank['unclassified_count'] + executable_core_e_bank['unclassified_count'] + executable_core_f_bank['unclassified_count']} "
        "unclassified"
    )


if __name__ == "__main__":
    main()
