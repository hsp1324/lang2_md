#!/usr/bin/env python3
"""Prove the exact-release Scenario 27 stock battle and every ending page.

Each profile starts its exact S31-output/S27-input save on an isolated virtual
display.  One BlastEm PID drives stock Move, End Turn, stock Attack, ordinary
combat, the ordered ending ledger, and stable ``Fin`` without loading an
external emulator state or writing tactical work RAM.  Expected ending records
and token digests come from the exact release ROM, the observed post-battle
roster, and source-locked stock selectors rather than accepted screenshots.

The ten fixed closing-montage captions are matched through the stock
ROM-glyph-to-VRAM conversion.  Dialogue pages are accepted only after stable
text observations and exact runtime semantic assignment.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.capture_magic_application import (  # noqa: E402
    portrait_dialogue_visible,
)
from tools import run_blastem_sequence as sequence  # noqa: E402
from tools import run_gray_acted_surface_matrix as gray  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_preparation_surface_parallel as parallel  # noqa: E402
from tools import run_scenario21_result_surface as shared  # noqa: E402
from tools import run_scenario27_stock_route as stock_route  # noqa: E402
from tools import run_sequential_campaign_revalidation as campaign  # noqa: E402
from tools import v137_release_identity as release_identity  # noqa: E402


PROFILES = ("pure", "normal", "hard")
SCENARIO_NUMBER = 27
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/v137-s27-ending-page-supplement"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/v137-s27-ending-page-runtime"
DEFAULT_DISPLAY_BASE = 960
DEFAULT_MAX_ENDING_FRAMES = 7200
STABLE_TEXT_CONFIRMATIONS = 3
STABLE_CAPTION_CONFIRMATIONS = 3
GST_VRAM_FILE_OFFSET = 0x12478
GST_VRAM_BYTES = 0x10000
ENDING_SLOT_RAM_OFFSET = 0xAE90
ENDING_SEQUENCE_CURSOR_RAM_OFFSET = 0xAE9E
ENDING_VISIT_BUFFER_RAM_OFFSET = 0xAA34
ENDING_VISIT_BUFFER_MAX_WORDS = 0x800
ENDING_DIALOGUE_STREAM_POINTER_RAM_OFFSET = 0xD1CA
PERSISTENT_ROSTER_RAM_OFFSET = 0xA4CC
ENDING_STATUS_TABLE = 0x088E10
ENDING_STATUS_ENTRY_BYTES = 0x12
ENDING_STATUS_SLOT_COUNT = 16
ENDING_SEQUENCE_POINTER_TABLE = 0x0953AE
ENDING_SEQUENCE_COUNT = 14
ENDING_SEQUENCE_ENTRY_BYTES = 8
ENDING_SEQUENCE_TERMINATOR = 0x18
EPILOGUE_GROUP_POINTER_TABLE = 0x08916E
EPILOGUE_NORMAL_SLOT_COUNT = 14
EPILOGUE_LIANA_POINTER_TABLE = 0x089572
EPILOGUE_WORLD_POINTER_TABLE = 0x089592
TEXT_OBJECT_CALLBACK = 0x37E4
TEXT_OBJECT_POINTER_OFFSET = 0x02
TEXT_OBJECT_PAGE_STATE_OFFSET = 0x0A
TEXT_OBJECT_PORTRAIT_OFFSET = 0x0C
TEXT_OBJECT_SCAN_START = 0x8000
TEXT_OBJECT_SCAN_END = 0xC000
CLOSING_MONTAGE_RECORDS = (
    (0x0A6BA8, 0x02FB5A),
    (0x0A6BEA, 0x02FEE2),
    (0x0A6C2A, 0x03006E),
    (0x0A6CA6, 0x030200),
    (0x0A6CEC, 0x03037C),
    (0x0A6D5E, 0x0304F0),
    (0x0A6DB8, 0x030618),
    (0x0A6DFE, 0x0306D4),
    (0x0A6E80, 0x0308A2),
    (0x0A6F02, 0x0309EC),
)
CLOSING_MONTAGE_TERMINATOR_INDICES = {
    0x0A6BA8: 32,
    0x0A6BEA: 31,
    0x0A6C2A: 61,
    0x0A6CA6: 34,
    0x0A6CEC: 56,
    0x0A6D5E: 44,
    0x0A6DB8: 34,
    0x0A6DFE: 64,
    0x0A6E80: 64,
    0x0A6F02: 19,
}
CLOSING_MONTAGE_RENDER_COUNT = 0x40
CLOSING_MONTAGE_VRAM_START = 0xA000
CLOSING_MONTAGE_GLYPH_ROM_BASE = 0x040000
CLOSING_MONTAGE_GLYPH_SOURCE_BYTES = 0x40
CLOSING_MONTAGE_GLYPH_VRAM_BYTES = 0x80
CLOSING_MONTAGE_LOADER_SNIPPET_BYTES = 20
CLOSING_MONTAGE_LOADER_SHA256 = (
    "1cb91ed90fbed4599afbf27578231718fe7eb25d9b9ba4d853874ad1a5d6e476"
)
CLOSING_MONTAGE_RENDERER_RANGE = (
    0x02C2C4,
    0x02C31C,
    "e40f9769818d598173c11158cca7805f38bee2eea2e8952dab9627029f8c8bd0",
)
CLOSING_MONTAGE_GLYPH_CONVERTER_RANGE = (
    0x02C390,
    0x02C3DC,
    "b15d0e851175e6d2f2670ca860ce2d61180f3104946bb6f391d187ed897a9c4e",
)
RUNTIME_GROUP_BASE = matrix.RUNTIME_GROUP_BASE
RUNTIME_GROUP_SIZE = matrix.RUNTIME_GROUP_SIZE
RUNTIME_MEMBER_SIZE = matrix.RUNTIME_MEMBER_SIZE
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_Y_OFFSET = 0x07
RUNTIME_PERSISTENCE_SKIP_FLAGS_OFFSET = 0x08
RUNTIME_SCENARIO_KILLS_OFFSET = 0x5E
RUNTIME_SYNC_GROUP_COUNT = 20
ELWIN_RUNTIME_GROUP = 0
FIN_SHA256 = (
    "4cb7db62c30ace38e0d8b2fa1a34fc7b"
    "a31586104f5b59c9663b6ad9564a46b0"
)
ENDING_DIALOGUE_TRANSLATIONS = Path("localization/ending_dialogue_ko.json")
ENDING_DIALOGUE_RELOC_LIMIT = 0x2D8000
EPILOGUE_RELOC_LIMIT = 0x2D0000
HISTORICAL_SURFACE_SHA256 = {
    "montage": "0e9e02c2636667098be11c3dd48cf7ea6f9b542081bff69fe6fc5b3eb3e50265",
    "scott": "2fcfb72fc90c5f4ec040362c95245de0c53fff70055eacbce98997d3fc13f1ce",
    "lana": "78d4c84d076cf6e4bba5e794c26ea59145af4df7342ec86c695615df4adc92ae",
    "bozel": "ad013a95bcd1d258e2dca78982d34ab7d7437be6a3ec1124faebb64efba5e307",
    "leon": "612a042329ce427419896bf736bd04a106824510f17bfe52d3ee47bdbb86ba90",
    "liana": "e14bc69eeb74e34be38aa740ccc6eafc34002706de84df395dac7165af79e8d2",
    "elwin": "ee69e166d2327f5f218325164cd8bc6ca116763bfe59a3396b48158bf21fc3b2",
    "fin": FIN_SHA256,
}
SELECTOR_SOURCE_RANGES = {
    "ending_slot_initialization": (
        0x01C7A8,
        0x01C7B8,
        "9254a16d47be029bfbb63325a924f074b6d666c5ff31992e54b94b2a8830fd2f",
    ),
    "ending_visit_branch": (
        0x01C854,
        0x01C96E,
        "c33a929ada6418e05af9f8444be5d17bd3be236b4e6aa6298667c98026ba57d0",
    ),
    "ending_slot_advance": (
        0x01CF96,
        0x01CFBE,
        "169e2a3892eea05ab3681ebafc999497d131580362d0a51f9308c95b6cd53f18",
    ),
    "ending_status_roster_copy": (
        0x01CA80,
        0x01CABC,
        "031d2ee31ba57ca5fd2499271b457ea57d939f87da75ef4b8f165ae5a665ab64",
    ),
    "ending_status_table": (
        0x088E10,
        0x088F30,
        "0d32bacdf80513002ce14cdcdc8a260c6ec1c91c3467ccbaa56041648a52773f",
    ),
    "runtime_to_persistent_roster": (
        0x011C78,
        0x011D78,
        "86ea07a4d04d66430bc8c342296ec947b5145b82231638cb4a67790baab7eba1",
    ),
    "epilogue_selector": (
        0x01DC64,
        0x01DD6A,
        "bfbcf72f9f673ea6006b83a5ea4cc5d0b91e1e7e181a662043a5db0be9c5c740",
    ),
    "ending_visit_dialogue_init": (
        0x02B32A,
        0x02B35E,
        "78812dd5d7fc05e82234c9b691061039687db5eaead705468cbb631aefa00b32",
    ),
    "ending_visit_dialogue_loop": (
        0x02B448,
        0x02B5C0,
        "5fa32db93f1737339379f0b67e44d38da1cfee4dd49520beee83e653378b51e7",
    ),
    "ending_visit_page_handlers": (
        0x02B908,
        0x02B9A8,
        "b85dbcb5b5a7a52b22a79879d68180720f6e677144f965cd829a1855708706fb",
    ),
    "epilogue_page_buffer": (
        0x0037E4,
        0x00388C,
        "df32cc6e2cb879b82d8c8fc4c8eb90f49cb90f5cf51b2d76835f34c0869610be",
    ),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fin_visible(path: Path) -> bool:
    """Recognize only the reviewed terminal Fin frame."""
    return path.is_file() and sha256_path(path) == FIN_SHA256


def ending_caption_visible(path: Path) -> bool:
    """Detect white closing captions drawn directly over a black field."""
    with Image.open(path) as opened:
        source = opened.convert("RGB")
    if source.size != (320, 240):
        return False
    band = source.crop((0, 175, 320, 235))
    pixels = list(band.getdata())
    white = sum(
        red > 160 and green > 160 and blue > 160
        for red, green, blue in pixels
    ) / len(pixels)
    black = sum(
        red < 25 and green < 25 and blue < 25
        for red, green, blue in pixels
    ) / len(pixels)
    return white > 0.01 and black > 0.85


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def be16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def record_words(
    data: bytes,
    start: int,
    *,
    limit: int,
) -> list[int]:
    words = []
    cursor = start
    while cursor + 2 <= limit:
        word = be16(data, cursor)
        words.append(word)
        cursor += 2
        if word == 0xFFFF:
            return words
    raise ValueError(f"unterminated ending record at 0x{start:06X}")


def split_record_pages(words: list[int]) -> list[list[int]]:
    if not words or words[-1] != 0xFFFF:
        raise ValueError("ending record has no FFFF terminator")
    pages: list[list[int]] = [[]]
    for word in words[:-1]:
        if word == 0xFFFD:
            pages.append([])
        else:
            pages[-1].append(word)
    return pages


def token_digest(words: list[int]) -> str:
    return sha256_bytes(
        b"".join(word.to_bytes(2, "big") for word in words)
    )


def load_rows(path: Path, expected: int) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records")
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError(f"expected {expected} records in {path}")
    return rows


def validate_selector_source_ranges(rom: bytes) -> dict[str, dict[str, Any]]:
    """Reject a release whose stock ending selectors differ from the source."""
    result = {}
    for label, (start, end, expected) in SELECTOR_SOURCE_RANGES.items():
        actual = sha256_bytes(rom[start:end])
        if actual != expected:
            raise ValueError(
                f"{label} source-locked range changed: {actual} != {expected}"
            )
        result[label] = {
            "range": f"0x{start:06X}..0x{end:06X}",
            "sha256": actual,
            "source_locked": True,
        }
    return result


def validate_closing_montage_renderer(rom: bytes) -> dict[str, Any]:
    """Lock the ten fixed-count caption calls and their stock glyph renderer."""
    snippets = []
    calls = []
    for source_address, operand_address in CLOSING_MONTAGE_RECORDS:
        start = operand_address - 2
        end = start + CLOSING_MONTAGE_LOADER_SNIPPET_BYTES
        snippet = rom[start:end]
        if len(snippet) != CLOSING_MONTAGE_LOADER_SNIPPET_BYTES:
            raise ValueError("closing montage loader snippet is outside the ROM")
        if be32(rom, operand_address) != source_address:
            raise ValueError(
                "closing montage loader source changed at "
                f"0x{operand_address:06X}"
            )
        snippets.append(snippet)
        calls.append(
            {
                "source_address": f"0x{source_address:06X}",
                "loader_range": f"0x{start:06X}..0x{end:06X}",
                "sha256": sha256_bytes(snippet),
            }
        )
    loader_sha = sha256_bytes(b"".join(snippets))
    if loader_sha != CLOSING_MONTAGE_LOADER_SHA256:
        raise ValueError(
            "closing montage fixed-count loader calls changed: "
            f"{loader_sha} != {CLOSING_MONTAGE_LOADER_SHA256}"
        )
    locked_ranges = {}
    for label, (start, end, expected) in {
        "fixed_count_renderer": CLOSING_MONTAGE_RENDERER_RANGE,
        "glyph_converter": CLOSING_MONTAGE_GLYPH_CONVERTER_RANGE,
    }.items():
        actual = sha256_bytes(rom[start:end])
        if actual != expected:
            raise ValueError(
                f"closing montage {label} changed: {actual} != {expected}"
            )
        locked_ranges[label] = {
            "range": f"0x{start:06X}..0x{end:06X}",
            "sha256": actual,
        }
    return {
        "loader_calls_sha256": loader_sha,
        "loader_calls": calls,
        "source_locked_ranges": locked_ranges,
        "renderer_count": CLOSING_MONTAGE_RENDER_COUNT,
        "vram_start": f"0x{CLOSING_MONTAGE_VRAM_START:04X}",
        "source_locked": True,
    }


def closing_montage_glyph_vram(rom: bytes, tokens: list[int]) -> bytes:
    """Reproduce stock 0x02C390 for the fixed-count caption glyphs."""
    rendered = bytearray()
    for token in tokens:
        source = CLOSING_MONTAGE_GLYPH_ROM_BASE + (
            token * CLOSING_MONTAGE_GLYPH_SOURCE_BYTES
        )
        glyph = rom[source : source + CLOSING_MONTAGE_GLYPH_SOURCE_BYTES]
        if len(glyph) != CLOSING_MONTAGE_GLYPH_SOURCE_BYTES:
            raise ValueError(f"closing montage glyph 0x{token:04X} is outside ROM")
        for offset in range(0, len(glyph), 2):
            planes = be16(glyph, offset)
            high_plane = planes >> 8
            low_plane = planes & 0xFF
            row = 0
            for bit in range(7, -1, -1):
                pixel = (
                    ((high_plane >> bit) & 1) << 1
                    | ((low_plane >> bit) & 1)
                )
                row = (row << 4) | pixel
            rendered.extend(row.to_bytes(4, "big"))
    expected_bytes = len(tokens) * CLOSING_MONTAGE_GLYPH_VRAM_BYTES
    if len(rendered) != expected_bytes:
        raise AssertionError("closing montage glyph conversion length changed")
    return bytes(rendered)


def closing_montage_expectations(rom: bytes) -> list[dict[str, Any]]:
    """Derive the ten stock S27 closing captions directly from the release."""
    expectations = []
    for record_index, (source_address, operand_address) in enumerate(
        CLOSING_MONTAGE_RECORDS
    ):
        renderer_count = CLOSING_MONTAGE_RENDER_COUNT
        if renderer_count != CLOSING_MONTAGE_RENDER_COUNT:
            raise ValueError(
                f"closing montage 0x{source_address:06X} renderer count changed"
            )
        terminator_index = CLOSING_MONTAGE_TERMINATOR_INDICES[source_address]
        token_count = (
            renderer_count if terminator_index is None else terminator_index
        )
        tokens = [
            be16(rom, source_address + index * 2)
            for index in range(token_count)
        ]
        if 0xFFFF in tokens:
            raise ValueError(
                f"closing montage 0x{source_address:06X} gained an early terminator"
            )
        if terminator_index is not None and be16(
            rom, source_address + terminator_index * 2
        ) != 0xFFFF:
            raise ValueError(
                f"closing montage 0x{source_address:06X} terminator changed"
            )
        vram = closing_montage_glyph_vram(rom, tokens)
        expectations.append(
            {
                "record_index": record_index,
                "source_address": f"0x{source_address:06X}",
                "loader_operand_address": f"0x{operand_address:06X}",
                "renderer_count": renderer_count,
                "terminator_index": terminator_index,
                "token_count": token_count,
                "token_sha256": token_digest(tokens),
                "vram_start": f"0x{CLOSING_MONTAGE_VRAM_START:04X}",
                "vram_prefix_bytes": len(vram),
                "vram_prefix_sha256": sha256_bytes(vram),
            }
        )
    identities = {
        (row["vram_prefix_bytes"], row["vram_prefix_sha256"])
        for row in expectations
    }
    if len(identities) != len(expectations):
        raise ValueError("closing montage VRAM identities are not unique")
    return expectations


def serialized_roster_stats(
    serialized: bytes,
    slot: int,
) -> tuple[int, int]:
    """Return (kill count, retreat count) used by the stock ending selector."""
    if not 0 <= slot < sequence.MANUAL_SLOT_COMMANDER_COUNT:
        raise ValueError(f"commander slot outside 0..9: {slot}")
    base = (
        sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + slot * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    # Routine 0x01CAAC copies the saved +0x12 word into ending-record +0x1E;
    # 0x01CAA0 copies saved +0x14 into the low byte of +0x20.  The status UI
    # and selector at 0x01DC64 use those as kills and retreats respectively.
    kills = be16(serialized, base + 0x12)
    retreats = serialized[base + 0x14]
    return kills, retreats


def ending_status_roster_index(rom: bytes, slot: int) -> int | None:
    """Map an ending-status slot through the stock commander-ID table."""
    if not 0 <= slot < ENDING_STATUS_SLOT_COUNT:
        raise ValueError(f"ending slot outside 0..15: {slot}")
    entry = ENDING_STATUS_TABLE + slot * ENDING_STATUS_ENTRY_BYTES
    commander_id = be16(rom, entry)
    if 1 <= commander_id <= sequence.MANUAL_SLOT_COMMANDER_COUNT:
        return commander_id - 1
    return None


def selector_record_from_runtime_roster(
    serialized: bytes,
    gst_payload: bytes,
) -> tuple[bytes, dict[str, Any]]:
    """Emulate stock 0x11C78 roster sync before the ending selectors run."""
    if len(serialized) != sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE:
        raise ValueError("serialized campaign record has the wrong size")
    ram = gst_work_ram(gst_payload)
    result = bytearray(serialized)
    persistent_stats = []
    for slot in range(sequence.MANUAL_SLOT_COMMANDER_COUNT):
        saved_kills, saved_retreats = serialized_roster_stats(serialized, slot)
        runtime = PERSISTENT_ROSTER_RAM_OFFSET + (
            slot * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        persistent_kills = be16(ram, runtime + 0x12)
        persistent_retreats = ram[runtime + 0x14]
        saved = sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET + (
            slot * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        result[saved + 0x12 : saved + 0x14] = persistent_kills.to_bytes(2, "big")
        result[saved + 0x14] = persistent_retreats
        persistent_stats.append(
            {
                "slot": slot,
                "saved_kills": saved_kills,
                "persistent_kills": persistent_kills,
                "persistent_kill_delta": persistent_kills - saved_kills,
                "saved_retreats": saved_retreats,
                "persistent_retreats": persistent_retreats,
                "persistent_retreat_delta": (
                    persistent_retreats - saved_retreats
                ),
            }
        )
    group_contributions = []
    for group in range(RUNTIME_SYNC_GROUP_COUNT):
        runtime = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        if ram[runtime + RUNTIME_PERSISTENCE_SKIP_FLAGS_OFFSET] & 0x20:
            continue
        commander_id = ram[runtime + 1]
        if commander_id == 0 or commander_id > 11:
            continue
        if commander_id == 11:
            commander_id = 4
        slot = commander_id - 1
        scenario_kills = ram[runtime + RUNTIME_SCENARIO_KILLS_OFFSET]
        defeated = bool(ram[runtime + RUNTIME_DEFEATED_FLAG_OFFSET] & 0x80)
        hp = ram[runtime + RUNTIME_HP_OFFSET]
        retreat_increment = int(defeated or hp == 0)
        saved = sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET + (
            slot * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        before_kills = be16(result, saved + 0x12)
        after_kills = before_kills + scenario_kills
        if after_kills > 0xFFFF:
            # This odd 0x00FF saturation is the exact BCC/fallback behavior at
            # 0x011CE6..0x011CEE, not a generic clamp invented by the runner.
            after_kills = 0x00FF
        before_retreats = result[saved + 0x14]
        after_retreats = min(0xFF, before_retreats + retreat_increment)
        result[saved + 0x12 : saved + 0x14] = after_kills.to_bytes(2, "big")
        result[saved + 0x14] = after_retreats
        group_contributions.append(
            {
                "runtime_group": group,
                "commander_id": commander_id,
                "slot": slot,
                "scenario_kills": scenario_kills,
                "retreat_increment": retreat_increment,
                "defeated": defeated,
                "hp": hp,
            }
        )
    stats = []
    for row in persistent_stats:
        slot = row["slot"]
        selector_kills, selector_retreats = serialized_roster_stats(result, slot)
        stats.append(
            {
                **row,
                "selector_kills": selector_kills,
                "selector_kill_delta": selector_kills - row["saved_kills"],
                "selector_retreats": selector_retreats,
                "selector_retreat_delta": (
                    selector_retreats - row["saved_retreats"]
                ),
            }
        )
    return bytes(result), {
        "source": (
            "post-Bernhardt persistent roster 0xFFFFA4CC plus source-locked "
            "runtime-to-roster sync 0x011C78..0x011D78"
        ),
        "copied_fields": ["commander +0x12 kills", "commander +0x14 retreats"],
        "seed_record_sha256": sha256_bytes(serialized),
        "selector_record_sha256": sha256_bytes(result),
        "runtime_group_contributions": group_contributions,
        "stats": stats,
    }


def ending_visit_sequence_index(serialized: bytes, slot: int) -> int | None:
    """Emulate the source-locked branch table at 0x01C854..0x01C960."""
    if not 0 <= slot <= 15:
        raise ValueError(f"ending slot outside 0..15: {slot}")
    if slot == 0:
        return 1 if serialized_roster_stats(serialized, 5)[1] >= 2 else 0
    if slot == 1:
        return 3 if serialized_roster_stats(serialized, 3)[1] >= 2 else 2
    if slot == 2:
        return 4
    if slot == 3:
        return 5
    if slot == 4:
        return 6
    if slot == 5:
        kills, retreats = serialized_roster_stats(serialized, 8)
        if retreats == 0:
            return 7 if kills >= 0x62 else 8
        if retreats == 1 and kills >= 0x9B:
            return 8
        return 9
    if slot == 6:
        return 10
    if slot == 7:
        return 11
    if slot == 14:
        elwin_kills, _ = serialized_roster_stats(serialized, 0)
        _, liana_retreats = serialized_roster_stats(serialized, 1)
        return 12 if liana_retreats == 0 and elwin_kills >= 0xC8 else 13
    return None


def parse_ending_visit_sequence(
    rom: bytes,
    index: int,
) -> list[dict[str, int]]:
    if not 0 <= index < ENDING_SEQUENCE_COUNT:
        raise ValueError(f"ending visit sequence outside 0..13: {index}")
    cursor = be32(rom, ENDING_SEQUENCE_POINTER_TABLE + index * 4)
    result = []
    for entry_index in range(64):
        if rom[cursor] == ENDING_SEQUENCE_TERMINATOR:
            return result
        result.append(
            {
                "entry_index": entry_index,
                "entry_address": cursor,
                "name_control": rom[cursor + 1],
                "portrait_id": rom[cursor + 2],
                "record_pointer": be32(rom, cursor + 4),
            }
        )
        cursor += ENDING_SEQUENCE_ENTRY_BYTES
    raise ValueError(f"ending visit sequence {index} has no 0x18 terminator")


def epilogue_special_index(serialized: bytes, slot: int) -> int:
    elwin_kills, _ = serialized_roster_stats(serialized, 0)
    liana_kills, liana_retreats = serialized_roster_stats(serialized, 1)
    if slot == 14:
        if liana_retreats == 0:
            return 0 if elwin_kills <= 0xC8 else 1
        base = 2 if liana_retreats == 1 else 5
        if liana_kills <= 0x28:
            return base
        if liana_kills <= 0x48:
            return base + 1
        return base + 2
    if slot == 15:
        if elwin_kills <= 0x92:
            return 0
        if elwin_kills <= 0xC8:
            return 1
        return 2 if liana_retreats else 3
    raise ValueError("special epilogue selector is only for slots 14 and 15")


def selected_epilogue_pointer(
    rom: bytes,
    serialized: bytes,
    slot: int,
) -> int | None:
    """Emulate the source-locked selector at 0x01DC64..0x01DD66."""
    if not 0 <= slot <= 15:
        raise ValueError(f"ending slot outside 0..15: {slot}")
    group = be32(rom, EPILOGUE_GROUP_POINTER_TABLE + slot * 4)
    if slot == 14:
        if group != EPILOGUE_LIANA_POINTER_TABLE:
            raise ValueError("Liana epilogue pointer table changed")
        return be32(rom, group + epilogue_special_index(serialized, slot) * 4)
    if slot == 15:
        if group != EPILOGUE_WORLD_POINTER_TABLE:
            raise ValueError("world epilogue pointer table changed")
        return be32(rom, group + epilogue_special_index(serialized, slot) * 4)

    if slot < 8:
        roster_index = ending_status_roster_index(rom, slot)
        if roster_index is None:
            raise ValueError(
                f"normal ending slot {slot} has no player-roster commander ID"
            )
        kills, retreats = serialized_roster_stats(serialized, roster_index)
    else:
        # The fixed villain status records clear +0x1E/+0x20 at 0x01CADA.
        kills, retreats = 0, 0
    cursor = group
    for _ in range(32):
        retreat_min = be16(rom, cursor)
        if retreat_min == 0xFFFF:
            return None
        retreat_max = be16(rom, cursor + 2)
        kill_min = be16(rom, cursor + 4)
        kill_max = be16(rom, cursor + 6)
        if (
            retreat_min <= retreats <= retreat_max
            and kill_min <= kills <= kill_max
        ):
            return be32(rom, cursor + 8)
        cursor += 12
    raise ValueError(f"epilogue descriptor list for slot {slot} is unterminated")


def runtime_visit_buffer(words: list[int], name_control: int) -> bytes:
    """Reproduce the stock 0x01C978 visit buffer independently of runtime."""
    output = [0xFFF7, name_control, 0xFFF7, 0]
    line_width = 0
    for word in words:
        line_width += 8
        if word == 0xFFFF:
            output.extend((0xFFFA, line_width, 0xFFFC))
            break
        if word == 0xFFFD:
            output.extend((0xFFFA, line_width, 0xFFFB))
            line_width = 0
            continue
        output.append(word)
    else:
        raise ValueError("visit record is unterminated")
    return b"".join(word.to_bytes(2, "big") for word in output)


def runtime_visit_page_end_offsets(buffer: bytes) -> list[int]:
    """Return D1CA offsets while each constructed visit page is stable."""
    if len(buffer) % 2:
        raise ValueError("ending visit runtime buffer has an odd byte length")
    words = [be16(buffer, offset) for offset in range(0, len(buffer), 2)]
    offsets = []
    for index in range(len(words) - 2):
        if (
            words[index] == 0xFFFA
            and words[index + 2] in {0xFFFB, 0xFFFC}
        ):
            # 0x02B970 consumes the width argument after FFFA. While the page
            # remains visible, D1CA therefore points at the following
            # FFFB/FFFC page/end control.
            offsets.append((index + 2) * 2)
    if not offsets or words[-1] != 0xFFFC:
        raise ValueError("ending visit runtime buffer lacks its final FFFC")
    return offsets


def current_pointer_map(
    rom: bytes,
    rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    result = {}
    for index, row in enumerate(rows):
        reference = int(str(row["pointer_reference"]), 16)
        pointer = be32(rom, reference)
        if pointer in result:
            raise ValueError(f"duplicate relocated ending pointer 0x{pointer:06X}")
        result[pointer] = {**row, "record_index": index}
    return result


def record_expectation(
    rom: bytes,
    pointer: int,
    row: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    words = record_words(rom, pointer, limit=limit)
    pages = split_record_pages(words)
    declared_text = str(row.get("text", row.get("target_korean", "")))
    declared_pages = declared_text.split("\f") if declared_text else []
    if declared_pages and len(declared_pages) != len(pages):
        raise ValueError(
            f"declared/runtime page count differs at 0x{pointer:06X}: "
            f"{len(declared_pages)} != {len(pages)}"
        )
    return {
        "record_index": int(row["record_index"]),
        "source_address": str(row["address"]),
        "english_record": int(row["english_record"]),
        "pointer": f"0x{pointer:06X}",
        "page_count": len(pages),
        "record_token_sha256": token_digest(words),
        "pages": [
            {
                "page_index": page_index,
                "token_count": len(page),
                "token_sha256": token_digest(page),
                "dynamic_name_word_offsets": [
                    index + 1
                    for index in range(len(page) - 1)
                    if page[index] == 0xFFF7 and page[index + 1] == 0
                ],
            }
            for page_index, page in enumerate(pages)
        ],
    }


def build_expected_page_model(
    rom: bytes,
    serialized: bytes,
) -> dict[str, Any]:
    """Build independent montage and selected page expectations for S27."""
    if len(serialized) != sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE:
        raise ValueError("serialized campaign record has the wrong size")
    if be16(serialized, sequence.MANUAL_SLOT_SCENARIO_OFFSET) != SCENARIO_NUMBER:
        raise ValueError("campaign record is not Scenario 27")
    selector_ranges = validate_selector_source_ranges(rom)
    montage_renderer = validate_closing_montage_renderer(rom)
    montage_records = closing_montage_expectations(rom)
    visit_rows = load_rows(ROOT / ENDING_DIALOGUE_TRANSLATIONS, 23)
    epilogue_rows = load_rows(ROOT / "localization/epilogue_records.json", 90)
    visit_map = current_pointer_map(rom, visit_rows)
    epilogue_map = current_pointer_map(rom, epilogue_rows)

    slots = []
    montage_pages = [
        {
            "slot": None,
            "kind": "closing_montage",
            "source_address": record["source_address"],
            "record_index": record["record_index"],
            "page_index": 0,
            "token_count": record["token_count"],
            "token_sha256": record["token_sha256"],
        }
        for record in montage_records
    ]
    dialogue_pages = []
    for slot in range(16):
        visit_index = ending_visit_sequence_index(serialized, slot)
        visits = []
        if visit_index is not None:
            for entry in parse_ending_visit_sequence(rom, visit_index):
                pointer = entry["record_pointer"]
                row = visit_map.get(pointer)
                if row is None:
                    raise ValueError(
                        f"slot {slot} visit pointer is not inventoried: 0x{pointer:06X}"
                    )
                expectation = record_expectation(
                    rom,
                    pointer,
                    row,
                    limit=ENDING_DIALOGUE_RELOC_LIMIT,
                )
                words = record_words(
                    rom,
                    pointer,
                    limit=ENDING_DIALOGUE_RELOC_LIMIT,
                )
                buffer = runtime_visit_buffer(words, entry["name_control"])
                page_end_offsets = runtime_visit_page_end_offsets(buffer)
                if len(page_end_offsets) != expectation["page_count"]:
                    raise ValueError(
                        "ending visit source/runtime page geometry differs at "
                        f"{expectation['source_address']}"
                    )
                for page, end_offset in zip(
                    expectation["pages"],
                    page_end_offsets,
                    strict=True,
                ):
                    page["runtime_end_pointer"] = (
                        f"0xFFFF{ENDING_VISIT_BUFFER_RAM_OFFSET + end_offset:04X}"
                    )
                expectation.update(
                    {
                        "sequence_index": visit_index,
                        "sequence_entry_index": entry["entry_index"],
                        "sequence_entry_address": (
                            f"0x{entry['entry_address']:06X}"
                        ),
                        "name_control": entry["name_control"],
                        "portrait_id": entry["portrait_id"],
                        "runtime_buffer_sha256": sha256_bytes(buffer),
                    }
                )
                visits.append(expectation)
                for page in expectation["pages"]:
                    dialogue_pages.append(
                        {
                            "slot": slot,
                            "kind": "ending_visit",
                            "source_address": expectation["source_address"],
                            "record_index": expectation["record_index"],
                            **page,
                        }
                    )

        epilogue_pointer = selected_epilogue_pointer(rom, serialized, slot)
        epilogue = None
        if epilogue_pointer is not None:
            row = epilogue_map.get(epilogue_pointer)
            if row is None:
                raise ValueError(
                    f"slot {slot} epilogue pointer is not inventoried: "
                    f"0x{epilogue_pointer:06X}"
                )
            epilogue = record_expectation(
                rom,
                epilogue_pointer,
                row,
                limit=EPILOGUE_RELOC_LIMIT,
            )
            for page in epilogue["pages"]:
                dialogue_pages.append(
                    {
                        "slot": slot,
                        "kind": "epilogue",
                        "source_address": epilogue["source_address"],
                        "record_index": epilogue["record_index"],
                        **page,
                    }
                )
        kills = retreats = None
        selector_roster_index = ending_status_roster_index(rom, slot)
        if slot < sequence.MANUAL_SLOT_COMMANDER_COUNT:
            if slot < 8:
                if selector_roster_index is None:
                    raise ValueError(
                        f"normal ending slot {slot} has no roster mapping"
                    )
                kills, retreats = serialized_roster_stats(
                    serialized,
                    selector_roster_index,
                )
            else:
                kills, retreats = 0, 0
        slots.append(
            {
                "slot": slot,
                "status_commander_id": (
                    selector_roster_index + 1
                    if selector_roster_index is not None
                    else None
                ),
                "selector_roster_index": selector_roster_index,
                "selector_kills": kills,
                "selector_retreats": retreats,
                "visit_sequence_index": visit_index,
                "ending_visits": visits,
                "epilogue": epilogue,
            }
        )
    flat_pages = montage_pages + dialogue_pages
    return {
        "schema_version": 1,
        "selector_anchors": {
            "closing_montage": (
                "Japanese fixed-count calls into routines "
                "0x02C2C4 and 0x02C390"
            ),
            "ending_visit_branch": "Japanese routine 0x01C854..0x01C960",
            "epilogue_selector": "Japanese routine 0x01DC64..0x01DD66",
            "saved_kills_offset": "commander +0x12 word",
            "saved_retreats_offset": "commander +0x14 byte",
            "runtime_selector_roster": "post-battle persistent RAM 0xFFFFA4CC",
            "source_locked_ranges": selector_ranges,
        },
        "closing_montage_renderer": montage_renderer,
        "closing_montage": montage_records,
        "slots": slots,
        "expected_montage_pages": montage_pages,
        "expected_dialogue_pages": dialogue_pages,
        "expected_pages": flat_pages,
        "expected_closing_montage_pages": len(montage_pages),
        "expected_visit_pages": sum(
            row["kind"] == "ending_visit" for row in dialogue_pages
        ),
        "expected_epilogue_pages": sum(
            row["kind"] == "epilogue" for row in dialogue_pages
        ),
        "expected_page_count": len(flat_pages),
        "expected_semantic_digest": sha256_bytes(
            json.dumps(flat_pages, sort_keys=True).encode()
        ),
    }


def gst_work_ram(payload: bytes) -> bytes:
    start = sequence.GST_WORK_RAM_FILE_OFFSET
    end = start + 0x10000
    ram = payload[start:end]
    if len(ram) != 0x10000:
        raise ValueError("GST is missing the complete 64 KiB work RAM")
    return ram


def gst_vram(payload: bytes) -> bytes:
    start = GST_VRAM_FILE_OFFSET
    end = start + GST_VRAM_BYTES
    vram = payload[start:end]
    if len(vram) != GST_VRAM_BYTES:
        raise ValueError("GST is missing the complete 64 KiB VDP VRAM")
    return vram


def active_closing_montage(
    vram: bytes,
    expected_model: dict[str, Any],
) -> list[dict[str, Any]]:
    """Identify a rendered fixed-count caption by its release-derived VRAM."""
    matches = []
    for record in expected_model["closing_montage"]:
        length = int(record["vram_prefix_bytes"])
        start = CLOSING_MONTAGE_VRAM_START
        actual = sha256_bytes(vram[start : start + length])
        if actual == record["vram_prefix_sha256"]:
            matches.append(
                {
                    "record_index": record["record_index"],
                    "source_address": record["source_address"],
                    "token_count": record["token_count"],
                    "vram_start": record["vram_start"],
                    "vram_prefix_bytes": length,
                    "vram_prefix_sha256": actual,
                }
            )
    return matches


def runtime_visit_buffer_bytes(ram: bytes) -> bytes | None:
    cursor = ENDING_VISIT_BUFFER_RAM_OFFSET
    output = bytearray()
    for _ in range(ENDING_VISIT_BUFFER_MAX_WORDS):
        if cursor + 2 > len(ram):
            break
        output.extend(ram[cursor : cursor + 2])
        if be16(ram, cursor) == 0xFFFC:
            return bytes(output)
        cursor += 2
    return None


def runtime_epilogue_page_words(ram: bytes) -> list[int] | None:
    cursor = ENDING_VISIT_BUFFER_RAM_OFFSET
    words = []
    for _ in range(ENDING_VISIT_BUFFER_MAX_WORDS):
        if cursor + 2 > len(ram):
            break
        word = be16(ram, cursor)
        if word == 0xFFFF:
            return words
        words.append(word)
        cursor += 2
    return None


def epilogue_runtime_page_matches(
    observed_words: list[int] | None,
    record: dict[str, Any],
    portrait: int,
) -> list[dict[str, Any]]:
    """Normalize the stock FFF7/0 portrait substitution and identify a page."""
    if observed_words is None:
        return []
    matches = []
    for page in record["pages"]:
        if len(observed_words) != page["token_count"]:
            continue
        normalized = list(observed_words)
        valid = True
        for offset in page["dynamic_name_word_offsets"]:
            if normalized[offset] != portrait:
                valid = False
                break
            normalized[offset] = 0
        if valid and token_digest(normalized) == page["token_sha256"]:
            matches.append(
                {
                    "page_index": page["page_index"],
                    "token_count": page["token_count"],
                    "token_sha256": page["token_sha256"],
                    "dynamic_name_word_offsets": page[
                        "dynamic_name_word_offsets"
                    ],
                }
            )
    return matches


def active_epilogue_objects(
    ram: bytes,
    expected_model: dict[str, Any],
) -> list[dict[str, Any]]:
    page_words = runtime_epilogue_page_words(ram)
    records = []
    for slot in expected_model["slots"]:
        epilogue = slot["epilogue"]
        if epilogue is not None:
            records.append(
                (
                    int(epilogue["pointer"], 16),
                    int(epilogue["pointer"], 16)
                    + sum(page["token_count"] for page in epilogue["pages"]) * 2
                    + max(0, epilogue["page_count"] - 1) * 2
                    + 2,
                    int(slot["slot"]),
                    epilogue,
                )
            )
    objects = []
    for offset in range(
        TEXT_OBJECT_SCAN_START,
        TEXT_OBJECT_SCAN_END - 14 + 1,
        2,
    ):
        if be16(ram, offset) != TEXT_OBJECT_CALLBACK:
            continue
        pointer = be32(ram, offset + TEXT_OBJECT_POINTER_OFFSET)
        matches = [row for row in records if row[0] <= pointer < row[1]]
        for start, end, slot, record in matches:
            portrait = be16(ram, offset + TEXT_OBJECT_PORTRAIT_OFFSET)
            objects.append(
                {
                    "ram_address": f"0xFFFF{offset:04X}",
                    "pointer": f"0x{pointer:06X}",
                    "record_start": f"0x{start:06X}",
                    "record_end": f"0x{end:06X}",
                    "slot": slot,
                    "source_address": record["source_address"],
                    "record_index": record["record_index"],
                    "display_countdown": be16(
                        ram,
                        offset + TEXT_OBJECT_PAGE_STATE_OFFSET,
                    ),
                    "portrait": portrait,
                    "runtime_page_token_sha256": (
                        token_digest(page_words)
                        if page_words is not None
                        else None
                    ),
                    "runtime_page_matches": epilogue_runtime_page_matches(
                        page_words,
                        record,
                        portrait,
                    ),
                }
            )
    return objects


def runtime_semantics(
    gst_path: Path,
    expected_model: dict[str, Any],
) -> dict[str, Any]:
    payload = gst_path.read_bytes()
    ram = gst_work_ram(payload)
    vram = gst_vram(payload)
    slot = be16(ram, ENDING_SLOT_RAM_OFFSET)
    visit_buffer = runtime_visit_buffer_bytes(ram)
    return {
        "slot": slot,
        "slot_in_range": 0 <= slot <= 15,
        "ending_sequence_cursor": (
            f"0x{be32(ram, ENDING_SEQUENCE_CURSOR_RAM_OFFSET):06X}"
        ),
        "dialogue_stream_pointer": (
            f"0x{be32(ram, ENDING_DIALOGUE_STREAM_POINTER_RAM_OFFSET):08X}"
        ),
        "visit_buffer_sha256": (
            sha256_bytes(visit_buffer) if visit_buffer is not None else None
        ),
        "visit_buffer_bytes": len(visit_buffer) if visit_buffer is not None else 0,
        "closing_montage_matches": active_closing_montage(
            vram,
            expected_model,
        ),
        "epilogue_objects": active_epilogue_objects(ram, expected_model),
    }


def runtime_group_member(
    gst: bytes,
    group: int,
    member: int,
) -> dict[str, int]:
    if not 0 <= group < 40 or not 0 <= member < 8:
        raise ValueError("runtime group/member is outside the loaded table")
    start = (
        sequence.GST_WORK_RAM_FILE_OFFSET
        + RUNTIME_GROUP_BASE
        + group * RUNTIME_GROUP_SIZE
        + member * RUNTIME_MEMBER_SIZE
    )
    if start + RUNTIME_MEMBER_SIZE > len(gst):
        raise ValueError("GST is too short for the requested runtime member")
    return {
        "class_id": gst[start],
        "name_id": gst[start + 1],
        "defeated_flag": gst[start + RUNTIME_DEFEATED_FLAG_OFFSET],
        "hp": gst[start + RUNTIME_HP_OFFSET],
        "x": gst[start + RUNTIME_X_OFFSET],
        "y": gst[start + RUNTIME_Y_OFFSET],
    }



def text_fingerprint(path: Path) -> tuple[str, int]:
    fingerprint = sequence.dialogue_text_fingerprint(path)
    return sha256_bytes(fingerprint), sum(fingerprint)


def stable_page_report(
    recorder: matrix.RuntimeRecorder,
    path: Path,
    *,
    page_number: int,
    frame_number: int,
    fingerprint_sha256: str,
    white_pixels: int,
    expected_model: dict[str, Any],
) -> dict[str, Any]:
    gst = recorder.save_gst(
        f"states/pages/page_{page_number:03d}.gst"
    )
    return {
        "ordinal": page_number,
        "ending_frame": frame_number,
        "surface_type": "portrait_dialogue",
        "capture": shared.image_report(path),
        "text_fingerprint_sha256": fingerprint_sha256,
        "text_fingerprint_white_pixels": white_pixels,
        "stable_observations": STABLE_TEXT_CONFIRMATIONS,
        "gst": relative(gst),
        "gst_sha256": sha256_path(gst),
        "runtime": runtime_semantics(gst, expected_model),
    }


def stable_caption_report(
    recorder: matrix.RuntimeRecorder,
    path: Path,
    *,
    caption_number: int,
    frame_number: int,
    stable_observations: int,
    expected_model: dict[str, Any],
) -> dict[str, Any]:
    gst = recorder.save_gst(
        f"states/captions/caption_{caption_number:03d}.gst"
    )
    return {
        "ordinal": caption_number,
        "ending_frame": frame_number,
        "surface_type": "closing_caption",
        "capture": shared.image_report(path),
        "stable_observations": stable_observations,
        "gst": relative(gst),
        "gst_sha256": sha256_path(gst),
        "runtime": runtime_semantics(gst, expected_model),
    }


def dialogue_text_surfaces_nonblank(
    observed_dialogue_pages: list[dict[str, Any]],
) -> bool:
    """Require at least one rendered white text pixel on every accepted page."""
    return all(
        int(row.get("text_fingerprint_white_pixels", 0)) > 0
        for row in observed_dialogue_pages
    )


def assign_semantic_pages(
    stable_surfaces: list[dict[str, Any]],
    expected_model: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match runtime-stable pages to the independently selected page model."""
    expected = list(
        expected_model.get(
            "expected_dialogue_pages",
            [
                row
                for row in expected_model["expected_pages"]
                if row["kind"] in {"ending_visit", "epilogue"}
            ],
        )
    )
    observed: list[dict[str, Any]] = []
    extras: list[dict[str, Any]] = []
    cursor = 0
    pending: tuple[dict[str, Any], str, str, int] | None = None
    visit_buffers = {
        (
            int(slot["slot"]),
            str(record["runtime_buffer_sha256"]),
        )
        for slot in expected_model["slots"]
        for record in slot["ending_visits"]
    }

    def matches_expected(
        wanted: dict[str, Any],
        classification: tuple[str | None, int, str | None, int | None],
    ) -> bool:
        kind, slot, source_address, page_index = classification
        return (
            kind == wanted["kind"]
            and slot == wanted["slot"]
            and source_address == wanted["source_address"]
            and page_index == wanted["page_index"]
        )

    def accept_pending() -> None:
        nonlocal cursor, pending
        if pending is None:
            return
        surface, _, _, _ = pending
        observed.append(
            {
                **surface,
                "semantic": expected[cursor],
                "semantic_index": cursor,
                "semantic_match": True,
                "completion_rule": (
                    "last stable surface before the next exact runtime page "
                    "identity"
                ),
            }
        )
        cursor += 1
        pending = None

    for surface in stable_surfaces:
        runtime = surface["runtime"]
        slot = runtime["slot"]
        objects = runtime["epilogue_objects"]
        visit_key = (slot, runtime["visit_buffer_sha256"])
        kind = None
        source_address = None
        page_index = None
        matching = [
            row
            for row in objects
            if row["slot"] == slot
        ]
        if len(matching) == 1:
            kind = "epilogue"
            source_address = matching[0]["source_address"]
            page_matches = matching[0]["runtime_page_matches"]
            if len(page_matches) == 1:
                page_index = page_matches[0]["page_index"]
        elif matching:
            kind = "epilogue"
        elif visit_key in visit_buffers:
            kind = "ending_visit"
            for slot_row in expected_model["slots"]:
                if slot_row["slot"] != slot:
                    continue
                matches = [
                    row
                    for row in slot_row["ending_visits"]
                    if row["runtime_buffer_sha256"] == visit_key[1]
                ]
                if len(matches) == 1:
                    source_address = matches[0]["source_address"]
                    end_pointers = {
                        page["runtime_end_pointer"]: page["page_index"]
                        for page in matches[0]["pages"]
                    }
                    page_index = end_pointers.get(
                        runtime["dialogue_stream_pointer"]
                    )
        classification = (kind, slot, source_address, page_index)
        wanted = expected[cursor] if cursor < len(expected) else None
        if wanted is not None and matches_expected(wanted, classification):
            if pending is not None:
                previous, _, old_source, old_page = pending
                extras.append(
                    {
                        **previous,
                        "classification": (
                            "partial_or_intermediate_exact_page_surface"
                        ),
                        "fatal_semantic_extra": False,
                        "source_address": old_source,
                        "page_index": old_page,
                        "next_expected": wanted,
                    }
                )
            pending = (surface, str(kind), str(source_address), int(page_index))
        elif (
            pending is not None
            and cursor + 1 < len(expected)
            and matches_expected(expected[cursor + 1], classification)
        ):
            accept_pending()
            pending = (surface, str(kind), str(source_address), int(page_index))
        else:
            fatal_semantic_extra = kind in {"ending_visit", "epilogue"}
            if fatal_semantic_extra:
                classification_label = (
                    "unexpected_exact_page_surface"
                    if source_address is not None and page_index is not None
                    else "invalid_exact_page_surface"
                )
            else:
                classification_label = "non_page_dialogue_surface"
            extras.append(
                {
                    **surface,
                    "classification": classification_label,
                    "fatal_semantic_extra": fatal_semantic_extra,
                    "source_address": source_address,
                    "page_index": page_index,
                    "next_expected": wanted,
                }
            )
    accept_pending()
    return observed, extras


def assign_semantic_montage(
    stable_captions: list[dict[str, Any]],
    expected_model: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match stable caption surfaces through release-derived VRAM prefixes."""
    expected = list(expected_model["expected_montage_pages"])
    observed = []
    extras = []
    cursor = 0
    pending: dict[str, Any] | None = None

    def accept_pending() -> None:
        nonlocal cursor, pending
        if pending is None:
            return
        wanted = expected[cursor]
        match = pending["runtime"]["closing_montage_matches"][0]
        observed.append(
            {
                **pending,
                "semantic": wanted,
                "semantic_index": cursor,
                "semantic_match": True,
                "vram_match": match,
                "completion_rule": (
                    "last stable surface before the next release-derived "
                    "montage VRAM identity"
                ),
            }
        )
        cursor += 1
        pending = None

    for surface in stable_captions:
        matches = surface["runtime"]["closing_montage_matches"]
        match = matches[0] if len(matches) == 1 else None
        wanted = expected[cursor] if cursor < len(expected) else None
        if (
            wanted is not None
            and match is not None
            and match["source_address"] == wanted["source_address"]
            and match["record_index"] == wanted["record_index"]
        ):
            if pending is not None:
                extras.append(
                    {
                        **pending,
                        "classification": "partial_or_intermediate_montage_surface",
                        "fatal_semantic_extra": False,
                        "next_expected": wanted,
                    }
                )
            pending = surface
        elif (
            pending is not None
            and cursor + 1 < len(expected)
            and match is not None
            and match["source_address"] == expected[cursor + 1]["source_address"]
            and match["record_index"] == expected[cursor + 1]["record_index"]
        ):
            accept_pending()
            pending = surface
        else:
            fatal_semantic_extra = match is not None or len(matches) > 1
            extras.append(
                {
                    **surface,
                    "classification": (
                        "ambiguous_closing_montage"
                        if len(matches) > 1
                        else (
                            "unexpected_exact_montage_surface"
                            if match is not None
                            else "non_montage_caption_surface"
                        )
                    ),
                    "fatal_semantic_extra": fatal_semantic_extra,
                    "next_expected": wanted,
                }
            )
    accept_pending()
    return observed, extras


def exact_campaign_seed(
    campaign_summary: dict[str, Any],
    profile: str,
) -> tuple[Path, dict[str, Any]]:
    reports = [
        row
        for row in campaign_summary.get("results", [])
        if row.get("profile") == profile
    ]
    if len(reports) != 1:
        raise ValueError(f"campaign summary has no unique {profile} report")
    rows = reports[0].get("results", [])
    s31 = [row for row in rows if row.get("scenario") == 31]
    s27 = [row for row in rows if row.get("scenario") == 27]
    if len(s31) != 1 or len(s27) != 1:
        raise ValueError(f"campaign summary lacks unique {profile} S31/S27 rows")
    predecessor = s31[0].get("output_state")
    input_state = s27[0].get("input_state")
    if not isinstance(predecessor, dict) or not isinstance(input_state, dict):
        raise ValueError(f"campaign summary lacks {profile} S31/S27 state lineage")
    keys = ("path", "gst_sha256", "record_sha256", "scenario")
    if any(predecessor.get(key) != input_state.get(key) for key in keys):
        raise ValueError(f"{profile} S31 output is not the exact S27 input")
    if input_state.get("scenario") != 27:
        raise ValueError(f"{profile} terminal campaign input is not S27")
    path = (ROOT / str(input_state["path"])).resolve()
    if not path.is_file() or sha256_path(path) != input_state["gst_sha256"]:
        raise ValueError(f"{profile} S27 input GST/hash proof broke")
    serialized = campaign.serialized_record_from_gst(path)
    if sha256_bytes(serialized) != input_state["record_sha256"]:
        raise ValueError(f"{profile} S27 serialized record hash proof broke")
    return path, {
        "s31_output": predecessor,
        "s27_input": input_state,
        "exact_transition": True,
    }



def run_profile(
    args: argparse.Namespace,
    profile: str,
    display: str,
    campaign_summary: dict[str, Any],
) -> dict[str, Any]:
    release_path = release_identity.RELEASE_ROM_PATHS[profile]
    expected_release_sha = release_identity.RELEASE_ROM_SHA256[profile]
    if sha256_path(release_path) != expected_release_sha:
        raise ValueError(f"{profile} exact release ROM hash changed")
    seed_path, seed_lineage = exact_campaign_seed(campaign_summary, profile)
    launch_rom = release_path
    serialized = campaign.serialized_record_from_gst(seed_path)
    seed_expected_model = build_expected_page_model(
        release_path.read_bytes(),
        serialized,
    )
    expected_model = seed_expected_model
    output = args.output_root / profile / args.run_id
    if output.exists():
        raise FileExistsError(f"ending page output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s27-pages-{profile}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    stable_surfaces: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    captions: list[dict[str, Any]] = []
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            launch_rom,
            seed_path,
            SCENARIO_NUMBER,
            runtime_name,
            output,
            manual_slot_args=stock_route.manual_slot_args(),
        )
        preparation = recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, launch_rom, output)
        command = recorder.capture("battle/turn1_command.png")
        initial_command = recorder.save_gst("states/initial_command.gst")
        stock_setup = stock_route.drive_to_bernhardt_target(
            recorder,
            rom=release_path,
            seed_gst=seed_path,
            initial_command_gst=initial_command,
        )
        ordinary_combat, post_battle = (
            stock_route.confirm_target_and_advance_battle(
                recorder,
                rom=release_path,
                baseline_process=stock_setup["initial_process"],
                max_frames=args.battle_frames,
                battle_delay=args.battle_delay,
            )
        )
        bernhardt = ordinary_combat["bernhardt"]

        selector_record, selector_stats = selector_record_from_runtime_roster(
            serialized,
            post_battle.read_bytes(),
        )
        post_battle_elwin = runtime_group_member(
            post_battle.read_bytes(),
            ELWIN_RUNTIME_GROUP,
            0,
        )
        if (
            post_battle_elwin["hp"] == 0
            or post_battle_elwin["defeated_flag"] & 0x80
        ):
            raise RuntimeError(
                "ordinary Bernhardt attack also defeated Elwin: "
                f"{post_battle_elwin}"
            )
        nonzero_deltas = [
            (
                row["slot"],
                row["selector_kill_delta"],
                row["selector_retreat_delta"],
            )
            for row in selector_stats["stats"]
            if row["selector_kill_delta"] or row["selector_retreat_delta"]
        ]
        persistent_deltas = [
            (
                row["slot"],
                row["persistent_kill_delta"],
                row["persistent_retreat_delta"],
            )
            for row in selector_stats["stats"]
            if row["persistent_kill_delta"]
            or row["persistent_retreat_delta"]
        ]
        if persistent_deltas:
            raise RuntimeError(
                "persistent roster changed before the source-locked result "
                f"sync: {persistent_deltas}"
            )
        if nonzero_deltas != [(0, 1, 0)]:
            raise RuntimeError(
                "ordinary stock Bernhardt kill changed unexpected persistent "
                f"selector stats after stock sync: {nonzero_deltas}"
            )
        expected_model = build_expected_page_model(
            release_path.read_bytes(),
            selector_record,
        )
        selector_stats.update(
            {
                "expected_battle_delta": [[0, 1, 0]],
                "seed_expected_semantic_digest": seed_expected_model[
                    "expected_semantic_digest"
                ],
                "post_battle_expected_semantic_digest": expected_model[
                    "expected_semantic_digest"
                ],
                "model_changed_after_battle": (
                    seed_expected_model["expected_semantic_digest"]
                    != expected_model["expected_semantic_digest"]
                ),
            }
        )

        previous_text = None
        stable_text = 0
        last_confirmed_text = None
        previous_full = None
        stable_caption = 0
        confirmed_caption = None
        fin = None
        fin_frame = None
        for frame in range(1, args.max_ending_frames + 1):
            time.sleep(args.settle_delay)
            capture = recorder.capture(f"ending/advance_{frame:04d}.png")
            full_sha = sha256_path(capture)
            is_fin = fin_visible(capture)
            dialogue = portrait_dialogue_visible(capture)
            caption = ending_caption_visible(capture)
            text_sha = None
            white_pixels = 0
            if dialogue:
                text_sha, white_pixels = text_fingerprint(capture)
                if text_sha == previous_text:
                    stable_text += 1
                else:
                    stable_text = 1
                previous_text = text_sha
            else:
                previous_text = None
                stable_text = 0
                last_confirmed_text = None
            if caption and full_sha == previous_full:
                stable_caption += 1
            elif caption:
                stable_caption = 1
            else:
                stable_caption = 0
            anchors = sorted(
                label
                for label, expected in HISTORICAL_SURFACE_SHA256.items()
                if expected == full_sha
            )
            observations.append(
                {
                    "frame": frame,
                    "capture": relative(capture),
                    "sha256": full_sha,
                    "dialogue": dialogue,
                    "caption": caption,
                    "fin": is_fin,
                    "text_fingerprint_sha256": text_sha,
                    "stable_text_observations": stable_text,
                    "stable_caption_observations": stable_caption,
                    "historical_anchors": anchors,
                }
            )
            if is_fin:
                fin = capture
                fin_frame = frame
                break
            if (
                dialogue
                and stable_text >= STABLE_TEXT_CONFIRMATIONS
                and text_sha != last_confirmed_text
            ):
                stable_surfaces.append(
                    stable_page_report(
                        recorder,
                        capture,
                        page_number=len(stable_surfaces) + 1,
                        frame_number=frame,
                        fingerprint_sha256=str(text_sha),
                        white_pixels=white_pixels,
                        expected_model=expected_model,
                    )
                )
                recorder.send(["c"], delay=args.confirmation_delay)
                last_confirmed_text = text_sha
                stable_text = 0
                previous_text = None
                continue
            caption_ready = (
                caption
                and stable_caption >= STABLE_CAPTION_CONFIRMATIONS
                and full_sha != confirmed_caption
            )
            if caption_ready:
                captions.append(
                    stable_caption_report(
                        recorder,
                        capture,
                        caption_number=len(captions) + 1,
                        frame_number=frame,
                        stable_observations=stable_caption,
                        expected_model=expected_model,
                    )
                )
                recorder.send(["c"], delay=args.confirmation_delay)
                confirmed_caption = full_sha
                stable_caption = 0
            previous_full = full_sha
        if fin is None or fin_frame is None:
            raise RuntimeError("Scenario 27 stable-page run did not reach Fin")
        fin_process = stock_route.same_process_checkpoint(
            recorder,
            rom=release_path,
            baseline_process=stock_setup["initial_process"],
            phase="stable_fin",
        )

        observed_dialogue_pages, extra_surfaces = assign_semantic_pages(
            stable_surfaces,
            expected_model,
        )
        observed_montage_pages, extra_caption_surfaces = assign_semantic_montage(
            captions,
            expected_model,
        )
        observed_pages = sorted(
            observed_montage_pages + observed_dialogue_pages,
            key=lambda row: int(row["ending_frame"]),
        )
        observed_semantics = [row["semantic"] for row in observed_pages]
        ordered_ledger_sha256 = sha256_bytes(
            json.dumps(
                observed_semantics,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        fatal_extra_surfaces = [
            row
            for row in (*extra_caption_surfaces, *extra_surfaces)
            if row.get("fatal_semantic_extra")
        ]
        accepted_dialogue_text_nonblank = dialogue_text_surfaces_nonblank(
            observed_dialogue_pages
        )
        semantic_complete = (
            observed_semantics == expected_model["expected_pages"]
            and not fatal_extra_surfaces
            and accepted_dialogue_text_nonblank
        )
        seed_unchanged = (
            sha256_path(seed_path)
            == seed_lineage["s27_input"]["gst_sha256"]
        )
        release_unchanged = sha256_path(release_path) == expected_release_sha
        exact_release_acceptance = (
            launch_rom == release_path
            and sha256_path(launch_rom) == expected_release_sha
            and stock_setup["status"] == "pass"
            and stock_setup["external_runtime_state_load_count"] == 0
            and stock_setup["tactical_runtime_bytes_written"] is False
            and stock_setup["runtime_hp_coordinate_setup_used"] is False
            and ordinary_combat["status"] == "pass"
            and ordinary_combat["same_process"] is True
            and fin_process["pid"] == stock_setup["initial_process"]["pid"]
        )
        evidence_complete = (
            semantic_complete
            and seed_unchanged
            and release_unchanged
            and exact_release_acceptance
        )
        report_status = "pass" if evidence_complete else "fail"
        report = {
            "schema_version": 1,
            "status": report_status,
            "profile": profile,
            "scenario": SCENARIO_NUMBER,
            "run_id": args.run_id,
            "display": display,
            "runtime_isolation": {
                "runtime_home": relative(recorder.runtime_home),
                "host_wayland_removed": True,
                "sdl_video_driver": "x11",
            },
            "release_rom": {
                "path": relative(release_path),
                "sha256": expected_release_sha,
                "unchanged": release_unchanged,
            },
            "execution_mode": "exact-release-same-process-stock-ui",
            "exact_release_acceptance": exact_release_acceptance,
            "execution_rom": {
                "path": relative(launch_rom),
                "sha256": sha256_path(launch_rom),
                "is_exact_release_rom": launch_rom == release_path,
            },
            "campaign_lineage": seed_lineage,
            "seed_unchanged": seed_unchanged,
            "scenario_identity": identity,
            "preparation": shared.image_report(preparation),
            "turn1_command": shared.image_report(command),
            "initial_command_gst": relative(initial_command),
            "initial_command_gst_sha256": sha256_path(initial_command),
            "stock_route": stock_setup,
            "ordinary_combat": ordinary_combat,
            "fin_process": fin_process,
            "post_battle_gst": relative(post_battle),
            "post_battle_gst_sha256": sha256_path(post_battle),
            "bernhardt_runtime_state": bernhardt,
            "post_battle_elwin_runtime_state": post_battle_elwin,
            "ending_selector_stats": selector_stats,
            "expected_page_model": expected_model,
            "stable_caption_surfaces": captions,
            "stable_dialogue_surfaces": stable_surfaces,
            "observed_semantic_pages": observed_pages,
            "ordered_semantic_ledger_sha256": ordered_ledger_sha256,
            "first_semantic_page": observed_pages[0] if observed_pages else None,
            "last_semantic_page": observed_pages[-1] if observed_pages else None,
            "observed_montage_pages": observed_montage_pages,
            "observed_dialogue_pages": observed_dialogue_pages,
            "extra_stable_caption_surfaces": extra_caption_surfaces,
            "extra_stable_dialogue_surfaces": extra_surfaces,
            "fatal_extra_surfaces": fatal_extra_surfaces,
            "accepted_dialogue_text_nonblank": accepted_dialogue_text_nonblank,
            "semantic_page_count": len(observed_pages),
            "semantic_pages_complete": semantic_complete,
            "fin": shared.image_report(fin),
            "fin_frame": fin_frame,
            "historical_anchor_matches": {
                label: [
                    row["frame"]
                    for row in observations
                    if label in row["historical_anchors"]
                ]
                for label in HISTORICAL_SURFACE_SHA256
            },
            "ending_observations": observations,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
            "acceptance_updated": False,
        }
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if report["status"] == "fail":
            raise RuntimeError(
                f"{profile} ending semantic coverage incomplete: "
                f"{len(observed_pages)}/{expected_model['expected_page_count']}"
            )
        return report
    finally:
        matrix.terminate_blastem_processes(display=display)


def cross_profile_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    expected_profiles = set(PROFILES)
    observed_profiles = {
        str(report.get("profile"))
        for report in reports
        if report.get("profile") in PROFILES
    }
    by_semantic: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        for page in report.get("observed_semantic_pages", []):
            semantic = page["semantic"]
            logical_identity = {
                "kind": semantic.get("kind"),
                "slot": semantic.get("slot"),
                "source_address": semantic.get("source_address"),
                "record_index": semantic.get("record_index"),
                "page_index": semantic.get("page_index"),
            }
            key = json.dumps(logical_identity, sort_keys=True)
            if semantic["kind"] == "closing_montage":
                text_fingerprint_sha256 = page["vram_match"][
                    "vram_prefix_sha256"
                ]
                fingerprint_kind = "release_derived_runtime_vram_prefix"
            else:
                text_fingerprint_sha256 = page["text_fingerprint_sha256"]
                fingerprint_kind = "stable_dialogue_text_crop"
            by_semantic.setdefault(key, []).append(
                {
                    "profile": report["profile"],
                    "text_fingerprint_sha256": text_fingerprint_sha256,
                    "fingerprint_kind": fingerprint_kind,
                    "capture_sha256": page["capture"]["sha256"],
                    "token_sha256": semantic.get("token_sha256"),
                    "token_count": semantic.get("token_count"),
                    "runtime_end_pointer": semantic.get(
                        "runtime_end_pointer"
                    ),
                }
            )
    shared = []
    fingerprint_mismatches = []
    token_mismatches = []
    coverage_mismatches = []
    duplicate_profile_pages = []
    for key, rows in by_semantic.items():
        profiles = {row["profile"] for row in rows}
        duplicate_profiles = sorted(
            profile
            for profile in profiles
            if sum(row["profile"] == profile for row in rows) != 1
        )
        item = {
            "semantic": json.loads(key),
            "profiles": sorted(profiles),
            "missing_profiles": sorted(expected_profiles - profiles),
            "duplicate_profiles": duplicate_profiles,
            "text_fingerprints": {
                row["profile"]: row["text_fingerprint_sha256"] for row in rows
            },
            "fingerprint_kinds": {
                row["profile"]: row["fingerprint_kind"] for row in rows
            },
            "pixel_fingerprints": {
                row["profile"]: row["capture_sha256"] for row in rows
            },
            "token_sha256": {
                row["profile"]: row["token_sha256"] for row in rows
            },
            "token_counts": {
                row["profile"]: row["token_count"] for row in rows
            },
            "runtime_end_pointers": {
                row["profile"]: row["runtime_end_pointer"] for row in rows
            },
        }
        item["text_fingerprint_identical"] = len(
            set(item["text_fingerprints"].values())
        ) == 1
        item["release_tokens_identical"] = (
            len(set(item["token_sha256"].values())) == 1
            and len(set(item["token_counts"].values())) == 1
            and len(set(item["runtime_end_pointers"].values())) == 1
        )
        item["all_profiles_present_once"] = (
            profiles == expected_profiles and not duplicate_profiles
        )
        shared.append(item)
        if not item["text_fingerprint_identical"]:
            fingerprint_mismatches.append(item)
        if not item["release_tokens_identical"]:
            token_mismatches.append(item)
        if not item["all_profiles_present_once"]:
            coverage_mismatches.append(item)
        if duplicate_profiles:
            duplicate_profile_pages.append(item)
    return {
        "shared_semantic_pages": shared,
        "shared_semantic_page_count": len(shared),
        "all_profile_semantic_page_count": sum(
            row["all_profiles_present_once"] for row in shared
        ),
        "text_fingerprint_mismatches": fingerprint_mismatches,
        "release_token_mismatches": token_mismatches,
        "profile_coverage_mismatches": coverage_mismatches,
        "duplicate_profile_pages": duplicate_profile_pages,
        "observed_profiles": sorted(observed_profiles),
        "all_expected_profiles_reported": observed_profiles == expected_profiles,
        "semantic_pages_nonempty": bool(shared),
        "all_logical_pages_present_once_per_profile": (
            bool(shared)
            and observed_profiles == expected_profiles
            and not coverage_mismatches
        ),
        "release_tokens_match_for_logical_pages": (
            bool(shared) and not token_mismatches
        ),
        "stable_text_fingerprints_match_where_semantics_match": (
            bool(shared) and not fingerprint_mismatches
        ),
        "note": (
            "Cross-profile equality is corroboration only. Expected record and "
            "page token digests are independently derived from the release ROM "
            "and exact post-battle roster via source-locked stock sync and "
            "selectors."
        ),
    }



def validate_campaign_summary_for_supplement(
    campaign_summary: dict[str, Any],
) -> dict[str, Any]:
    """Accept only an exact complete pre-S27 campaign save chain.

    Scenario 27's retained outcome is intentionally irrelevant: this runner
    starts from the exact Scenario 31 output/S27 input and independently proves
    the complete final battle/ending route in a new emulator process.
    """
    route = list(campaign.FULL_ROUTE_ORDER)
    if campaign_summary.get("route_order") != route:
        raise ValueError("campaign summary route order is not the full route")
    for key in (
        "continuous_save_chain",
        "automation_only",
        "release_roms_unchanged",
    ):
        if campaign_summary.get(key) is not True:
            raise ValueError(f"campaign summary does not prove {key}")
    if campaign_summary.get("manual_intervention") is not False:
        raise ValueError("campaign summary used manual intervention")
    reports = campaign_summary.get("results")
    if not isinstance(reports, list) or len(reports) != len(PROFILES):
        raise ValueError("campaign summary lacks three profile reports")
    by_profile = {
        row.get("profile"): row
        for row in reports
        if isinstance(row, dict) and row.get("profile") in PROFILES
    }
    if set(by_profile) != set(PROFILES):
        raise ValueError("campaign summary profile reports are not unique")
    terminal_rows = []
    for profile in PROFILES:
        rows = by_profile[profile].get("results")
        if not isinstance(rows, list) or [
            row.get("scenario") for row in rows if isinstance(row, dict)
        ] != route:
            raise ValueError(f"campaign summary {profile} route is incomplete")
        if any(
            row.get("route_index") != index
            for index, row in enumerate(rows)
        ):
            raise ValueError(f"campaign summary {profile} route indices changed")
        failures = [row for row in rows[:-1] if row.get("status") != "pass"]
        if failures:
            raise ValueError(
                f"campaign summary {profile} has a pre-S27 failure"
            )
        terminal = rows[-1]
        if terminal.get("status") not in {"pass", "failed_attempt"}:
            raise ValueError(
                f"campaign summary {profile} S27 input row is unsupported"
            )
        seed_path, lineage = exact_campaign_seed(campaign_summary, profile)
        terminal_rows.append(
            {
                "profile": profile,
                "retained_s27_status_not_used": terminal.get("status"),
                "seed_path": relative(seed_path),
                "seed_sha256": sha256_path(seed_path),
                "lineage": lineage,
            }
        )
    return {
        "accepted": True,
        "run_id": campaign_summary.get("run_id"),
        "full_route_order": route,
        "pre_s27_steps_passed_per_profile": len(route) - 1,
        "terminal_s27_results_used_as_evidence": False,
        "retained_exact_s27_inputs": terminal_rows,
    }


def run_all(args: argparse.Namespace) -> dict[str, Any]:
    release_identity.require_final_release_identity()
    campaign_summary = json.loads(args.campaign_summary.read_text(encoding="utf-8"))
    if campaign_summary.get("run_id") != args.expected_campaign_run_id:
        raise ValueError("campaign summary run_id differs from its explicit lock")
    campaign_acceptance = validate_campaign_summary_for_supplement(
        campaign_summary
    )
    displays = {
        profile: f":{args.display_base + index}"
        for index, profile in enumerate(PROFILES)
    }
    xvfb = {}
    reports = []
    errors = []
    started = time.monotonic()
    try:
        for profile, display in displays.items():
            xvfb[profile] = parallel.start_xvfb(
                args.xvfb,
                args.xvfb_library_path,
                display,
            )
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    run_profile,
                    args,
                    profile,
                    displays[profile],
                    campaign_summary,
                ): profile
                for profile in PROFILES
            }
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    reports.append(future.result())
                    print(f"{profile} Scenario 27 ending pages: pass", flush=True)
                except Exception as exc:
                    errors.append(
                        {
                            "profile": profile,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
                    print(
                        f"{profile} Scenario 27 ending pages: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
    finally:
        for process in xvfb.values():
            parallel.stop_process(process)
    reports.sort(key=lambda row: PROFILES.index(str(row["profile"])))
    cross = cross_profile_report(reports)
    evidence_complete = (
        len(reports) == 3
        and not errors
        and all(report.get("status") == "pass" for report in reports)
        and cross["all_logical_pages_present_once_per_profile"]
        and cross["release_tokens_match_for_logical_pages"]
        and cross["stable_text_fingerprints_match_where_semantics_match"]
    )
    exact_release_acceptance = (
        len(reports) == len(PROFILES)
        and not errors
        and all(report.get("exact_release_acceptance") for report in reports)
    )
    status = "pass" if evidence_complete and exact_release_acceptance else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "run_id": args.run_id,
        "scope": (
            "exact S31 output/S27 input through same-process stock Move, "
            "stock Attack, ordinary Bernhardt combat, all ten fixed closing "
            "montage captions, all selected ending-visit and epilogue pages, "
            "then uninterrupted traversal through credits to stable Fin"
        ),
        "execution_mode": "exact-release-same-process-stock-ui",
        "exact_release_acceptance": exact_release_acceptance,
        "campaign_summary": {
            "path": relative(args.campaign_summary),
            "sha256": sha256_path(args.campaign_summary),
            "source_run_id": args.expected_campaign_run_id,
            "acceptance": campaign_acceptance,
        },
        "displays": displays,
        "isolated_xvfb_only": True,
        "reports": reports,
        "errors": errors,
        "cross_profile": cross,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "acceptance_updated": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("run",),
        help="run all three exact-release lineages on isolated Xvfb displays",
    )
    run = parser
    run.add_argument("--campaign-summary", type=Path, required=True)
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    run.add_argument("--summary", type=Path, required=True)
    run.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    run.add_argument(
        "--expected-campaign-run-id",
        type=matrix.validate_run_id,
        required=True,
        help="explicit run-id lock for the retained campaign summary",
    )
    run.add_argument("--display-base", type=int, default=DEFAULT_DISPLAY_BASE)
    run.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    run.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    run.add_argument("--battle-frames", type=int, default=36)
    run.add_argument("--battle-delay", type=float, default=0.2)
    run.add_argument("--max-ending-frames", type=int, default=DEFAULT_MAX_ENDING_FRAMES)
    # Three equal observations now span at least half a second, matching the
    # proven dialogue-stability helper and avoiding punctuation pauses being
    # mistaken for a complete page.
    run.add_argument("--settle-delay", type=float, default=0.25)
    run.add_argument("--confirmation-delay", type=float, default=0.28)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 100 <= args.display_base <= 988:
        raise ValueError("--display-base must reserve three isolated displays >= :100")
    for name in (
        "battle_frames",
        "max_ending_frames",
    ):
        if getattr(args, name) < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be at least 1")
    for name in (
        "battle_delay",
        "settle_delay",
        "confirmation_delay",
    ):
        if getattr(args, name) < 0:
            raise ValueError(f"--{name.replace('_', '-')} must not be negative")
    args.campaign_summary = args.campaign_summary.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    args.summary = args.summary.resolve()
    result = run_all(args)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.summary)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
