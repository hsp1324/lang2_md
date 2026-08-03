#!/usr/bin/env python3
"""Verify that preparation scratch glyphs never alias in one surface lifetime.

The preparation renderer keeps tile references alive longer than the five
currently visible commander rows.  In particular, later roster pages may load
their glyphs after the first page has already written its tilemap.  This tool
models that lifetime explicitly instead of relying only on before/after shop
screenshots, which cannot detect a screen that is identically corrupt twice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.class_change_data import hidden_class_routes, read_class_change_chain
from tools.class_hire_data import (
    MERCENARY_CLASS_BASE,
    MERCENARY_CLASS_COUNT,
    read_class_hire_unlocks,
)
from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS
from tools.run_preparation_surface_matrix import player_commander_ids
from tools.scenario_data import (
    DEFAULT_REFERENCE_ROM,
    KOREAN_NAME_BY_ID,
    read_scenario,
)


DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_REFERENCE = ROOT / DEFAULT_REFERENCE_ROM
DEFAULT_HARD_PLAN = ROOT / "localization/hard_mode_plan.json"
DEFAULT_OUTPUT = ROOT / "tmp/preparation-glyph-conflicts.json"
PLAYABLE_CLASS_FIRST = 0x01
PLAYABLE_CLASS_LAST = 0x2A
ROSTER_PAGE_SIZE = 5
HIRE_PAGE_SIZE = 3
REGRESSION_PAIRS = (
    ("쉐", "제"),  # 쉐리 / latent 제시카 page
    ("키", "메"),  # 키스 / 메이지 family
    ("니", "키"),  # 아니키
    ("랜", "쉐"),  # 하이랜더 / 쉐리 roster
    ("랜", "제"),  # 하이랜더 / 제시카 roster
)


@dataclass(frozen=True)
class SurfaceContext:
    name: str
    chars: tuple[str, ...]


def _dynamic_chars(texts: tuple[str, ...], dynamic: set[str]) -> tuple[str, ...]:
    return tuple(sorted(set("".join(texts)) & dynamic))


def _append_context(
    contexts: list[SurfaceContext],
    dynamic: set[str],
    name: str,
    *texts: str,
) -> None:
    chars = _dynamic_chars(texts, dynamic)
    if chars:
        contexts.append(SurfaceContext(name=name, chars=chars))


def _normal_fixed_contexts(
    contexts: list[SurfaceContext],
    dynamic: set[str],
    source: bytes,
    reference: bytes,
) -> None:
    for scenario in range(1, 32):
        model = read_scenario(source, reference, scenario)
        for row in model["records"]:
            if row["hidden"] or row["x"] == 0xFF or row["y"] == 0xFF:
                continue
            mercenaries = tuple(
                KOREAN_CLASS_LABELS[class_id]
                for class_id in row["mercenaries"]
                if class_id != 0xFF
            )
            _append_context(
                contexts,
                dynamic,
                f"normal:s{scenario:02d}:fixed:{int(row['index']):02d}",
                row["name"]["ko"],
                row["class"]["ko"],
                *mercenaries,
            )


def _hard_fixed_contexts(
    contexts: list[SurfaceContext],
    dynamic: set[str],
    hard_plan_path: Path | None,
) -> None:
    if hard_plan_path is None:
        return
    plan = json.loads(hard_plan_path.read_text(encoding="utf-8"))
    for scenario in plan["scenarios"]:
        scenario_number = int(scenario.get("scenario", scenario["number"]))
        for row in scenario["records"]:
            mercenaries = tuple(
                KOREAN_CLASS_LABELS[int(class_id)]
                for class_id in row["mercenaries"]["planned"]
                if int(class_id) != 0xFF
            )
            _append_context(
                contexts,
                dynamic,
                f"hard:s{scenario_number:02d}:fixed:{int(row['index']):02d}",
                str(row["name_korean"]),
                str(row["class_korean"]),
                *mercenaries,
            )


def build_contexts(
    source: bytes,
    reference: bytes,
    hard_plan_path: Path | None = DEFAULT_HARD_PLAN,
) -> list[SurfaceContext]:
    dynamic = set(builder.BYTE_UI_PREP_DYNAMIC_CHARS)
    contexts: list[SurfaceContext] = []

    # Every individual record must first be internally collision-free.
    for name_id, label in sorted(KOREAN_NAME_BY_ID.items()):
        _append_context(contexts, dynamic, f"name:{name_id:02X}", label)
    for class_id, label in enumerate(KOREAN_CLASS_LABELS):
        _append_context(contexts, dynamic, f"class:{class_id:02X}", label)

    mercenary_labels = tuple(
        KOREAN_CLASS_LABELS[MERCENARY_CLASS_BASE + index]
        for index in range(MERCENARY_CLASS_COUNT)
    )
    for scenario in range(1, 32):
        commander_ids = player_commander_ids(source, scenario)
        roster_names = tuple(KOREAN_NAME_BY_ID[row] for row in commander_ids)

        # The game may render names from latent roster pages into the scratch
        # bank, so one scenario roster is one lifetime rather than independent
        # five-row page contexts.
        _append_context(
            contexts,
            dynamic,
            f"scenario:{scenario:02d}:complete_roster",
            *roster_names,
        )
        for commander_id in commander_ids:
            selected_name = KOREAN_NAME_BY_ID[commander_id]
            for class_id in range(PLAYABLE_CLASS_FIRST, PLAYABLE_CLASS_LAST + 1):
                selected_class = KOREAN_CLASS_LABELS[class_id]
                _append_context(
                    contexts,
                    dynamic,
                    f"scenario:{scenario:02d}:root:{commander_id:02d}:"
                    f"class:{class_id:02X}",
                    *roster_names,
                    selected_name,
                    selected_class,
                )
                # Exercise the user's proposed synthetic all-mercenary list in
                # the exact three-row pages used by the game.
                for page_start in range(0, MERCENARY_CLASS_COUNT, HIRE_PAGE_SIZE):
                    page = mercenary_labels[
                        page_start:page_start + HIRE_PAGE_SIZE
                    ]
                    _append_context(
                        contexts,
                        dynamic,
                        f"scenario:{scenario:02d}:hire:{commander_id:02d}:"
                        f"class:{class_id:02X}:page:{page_start // HIRE_PAGE_SIZE + 1}",
                        *roster_names,
                        selected_name,
                        selected_class,
                        *page,
                    )

    _normal_fixed_contexts(contexts, dynamic, source, reference)
    _hard_fixed_contexts(contexts, dynamic, hard_plan_path)

    for commander_id in range(1, 11):
        transitions = (
            read_class_change_chain(source, commander_id)
            + hidden_class_routes(commander_id)
        )
        for transition in transitions:
            candidate_labels = tuple(
                KOREAN_CLASS_LABELS[class_id]
                for class_id in transition.candidates
            )
            for selected_class_id in transition.candidates:
                unlocks = read_class_hire_unlocks(source, selected_class_id)
                hire_labels = tuple(
                    KOREAN_CLASS_LABELS[class_id]
                    for class_id in unlocks.hire_class_ids
                    if class_id != 0xFF
                )
                _append_context(
                    contexts,
                    dynamic,
                    f"class_change:{commander_id:02d}:"
                    f"from:{transition.current_class:02X}:"
                    f"selected:{selected_class_id:02X}",
                    KOREAN_NAME_BY_ID[commander_id],
                    *candidate_labels,
                    *hire_labels,
                )
    return contexts


def slot_by_char(groups: tuple[str, ...]) -> dict[str, int]:
    result: dict[str, int] = {}
    for slot, group in enumerate(groups):
        for char in group:
            if char in result:
                raise ValueError(f"preparation character is repeated: {char}")
            result[char] = slot
    return result


def verify_contexts(
    contexts: list[SurfaceContext],
    groups: tuple[str, ...] = builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS,
) -> dict[str, object]:
    slots = slot_by_char(groups)
    dynamic = set(builder.BYTE_UI_PREP_DYNAMIC_CHARS)
    missing = sorted(dynamic - set(slots))
    extra = sorted(set(slots) - dynamic)
    conflicts: list[dict[str, object]] = []
    for context in contexts:
        by_slot: dict[int, list[str]] = {}
        for char in context.chars:
            if char not in slots:
                continue
            by_slot.setdefault(slots[char], []).append(char)
        for slot, chars in sorted(by_slot.items()):
            if len(chars) > 1:
                conflicts.append(
                    {
                        "context": context.name,
                        "slot": slot,
                        "chars": chars,
                    }
                )

    regression_pairs = []
    for left, right in REGRESSION_PAIRS:
        separated = left in slots and right in slots and slots[left] != slots[right]
        regression_pairs.append(
            {
                "left": left,
                "right": right,
                "left_slot": slots.get(left),
                "right_slot": slots.get(right),
                "separated": separated,
            }
        )

    digest_source = "\n".join(
        f"{context.name}:{''.join(context.chars)}" for context in contexts
    ).encode("utf-8")
    passed = not missing and not extra and not conflicts and all(
        row["separated"] for row in regression_pairs
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "surface_context_count": len(contexts),
        "surface_context_sha256": hashlib.sha256(digest_source).hexdigest(),
        "dynamic_character_count": len(dynamic),
        "slot_count": len(groups),
        "missing_characters": missing,
        "extra_characters": extra,
        "conflict_count": len(conflicts),
        "conflicts": conflicts[:100],
        "regression_pairs": regression_pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--reference-rom", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--hard-plan", type=Path, default=DEFAULT_HARD_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    contexts = build_contexts(
        args.source_rom.read_bytes(),
        args.reference_rom.read_bytes(),
        args.hard_plan,
    )
    report = verify_contexts(contexts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{report['status']}: {report['surface_context_count']} contexts, "
        f"{report['slot_count']} slots, {report['conflict_count']} conflicts"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
