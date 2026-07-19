#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.class_change_data import (
    ClassTransition,
    COMMANDER_COUNT,
    REGULAR_TRANSITION_COUNT,
    class_change_chain_pointer,
    read_class_change_chain,
)
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


DEFAULT_SOURCE_ROM = Path("roms/original/Langrisser II (Japan).md")
DEFAULT_JSON = Path("localization/class_change_chains.json")
DEFAULT_MARKDOWN = Path("docs/class_change_chain_inventory.md")
LIVE_EVIDENCE = {
    (1, 0x01): [
        "captures/run/d1d7_class_change_candidate1.png",
        "captures/run/d1d7_class_change_candidate2.png",
        "captures/run/d1d7_class_change_candidate3.png",
        "captures/analysis/d1d7_class_change_confirm.gst",
        "captures/analysis/eb00_class_change_turn2.gst",
    ],
    (1, 0x04): ["captures/run/8ea5_c1_s04_trigger.png", "captures/run/8ea5_c1_s04_candidate1.png", "captures/run/8ea5_c1_s04_candidate2.png", "captures/run/8ea5_c1_s04_candidate3.png"],
    (1, 0x05): ["captures/run/8ea1_c1_s05_trigger.png", "captures/run/8ea1_c1_s05_candidate1.png", "captures/run/8ea1_c1_s05_candidate2.png", "captures/run/8ea1_c1_s05_candidate3.png"],
    (1, 0x0A): ["captures/run/8eae_c1_s0a_trigger.png", "captures/run/8eae_c1_s0a_candidate1.png", "captures/run/8eae_c1_s0a_candidate2.png", "captures/run/8eae_c1_s0a_candidate3.png"],
    (1, 0x12): ["captures/run/8edb_c1_s12_trigger.png", "captures/run/8edb_c1_s12_candidate1.png", "captures/run/8edb_c1_s12_candidate2.png", "captures/run/8edb_c1_s12_candidate3.png"],
    (1, 0x0B): ["captures/run/8ed8_c1_s0b_trigger.png", "captures/run/8ed8_c1_s0b_candidate1.png", "captures/run/8ed8_c1_s0b_candidate2.png", "captures/run/8ed8_c1_s0b_candidate3.png"],
    (1, 0x0C): ["captures/run/8ed5_c1_s0c_trigger.png", "captures/run/8ed5_c1_s0c_candidate1.png", "captures/run/8ed5_c1_s0c_candidate2.png", "captures/run/8ed5_c1_s0c_candidate3.png"],
    (1, 0x0D): ["captures/run/8ed9_c1_s0d_trigger.png", "captures/run/8ed9_c1_s0d_candidate1.png", "captures/run/8ed9_c1_s0d_candidate2.png", "captures/run/8ed9_c1_s0d_candidate3.png"],
    (1, 0x13): ["captures/run/8ed8_c1_s13_trigger.png", "captures/run/8ed8_c1_s13_candidate1.png", "captures/run/8ed8_c1_s13_candidate2.png", "captures/run/8ed8_c1_s13_candidate3.png"],
    (1, 0x1A): ["captures/run/8eb2_c1_s1a_trigger.png", "captures/run/8eb2_c1_s1a_candidate1.png"],
    (2, 0x02): [
        "captures/run/8e91_c2_s02_trigger.png",
        "captures/run/8e91_c2_s02_candidate1.png",
        "captures/run/8e91_c2_s02_candidate2.png",
        "captures/run/8e91_c2_s02_candidate3.png",
    ],
    (2, 0x0A): [
        "captures/run/8eb4_c2_s0a_trigger.png",
        "captures/run/8eb4_c2_s0a_candidate1.png",
        "captures/run/8eb4_c2_s0a_candidate2.png",
        "captures/run/8eb4_c2_s0a_candidate3.png",
    ],
    (2, 0x08): [
        "captures/run/8eb1_c2_s08_trigger.png",
        "captures/run/8eb1_c2_s08_candidate1.png",
        "captures/run/8eb1_c2_s08_candidate2.png",
        "captures/run/8eb1_c2_s08_candidate3.png",
    ],
    (2, 0x04): [
        "captures/run/8eab_c2_s04_trigger.png",
        "captures/run/8eab_c2_s04_candidate1.png",
        "captures/run/8eab_c2_s04_candidate2.png",
        "captures/run/8eab_c2_s04_candidate3.png",
    ],
    (2, 0x13): [
        "captures/run/8ed6_c2_s13_trigger.png",
        "captures/run/8ed6_c2_s13_candidate1.png",
        "captures/run/8ed6_c2_s13_candidate2.png",
        "captures/run/8ed6_c2_s13_candidate3.png",
    ],
    (2, 0x0D): [
        "captures/run/8ed2_c2_s0d_trigger.png",
        "captures/run/8ed2_c2_s0d_candidate1.png",
        "captures/run/8ed2_c2_s0d_candidate2.png",
        "captures/run/8ed2_c2_s0d_candidate3.png",
    ],
    (2, 0x11): [
        "captures/run/8ece_c2_s11_trigger.png",
        "captures/run/8ece_c2_s11_candidate1.png",
        "captures/run/8ece_c2_s11_candidate2.png",
        "captures/run/8ece_c2_s11_candidate3.png",
    ],
    (2, 0x12): [
        "captures/run/8ece_c2_s12_trigger.png",
        "captures/run/8ece_c2_s12_candidate1.png",
        "captures/run/8ece_c2_s12_candidate2.png",
        "captures/run/8ece_c2_s12_candidate3.png",
    ],
    (2, 0x0B): [
        "captures/run/8ec8_c2_s0b_trigger.png",
        "captures/run/8ec8_c2_s0b_candidate1.png",
        "captures/run/8ec8_c2_s0b_candidate2.png",
        "captures/run/8ec8_c2_s0b_candidate3.png",
    ],
    (2, 0x19): [
        "captures/run/8eb8_c2_s19_trigger.png",
        "captures/run/8eb8_c2_s19_candidate1.png",
    ],
    (4, 0x01): [
        "captures/run/8e90_c4_s01_trigger.png",
        "captures/run/8e90_c4_s01_candidate1.png",
        "captures/run/8e90_c4_s01_candidate2.png",
        "captures/run/8e90_c4_s01_candidate3.png",
    ],
    (4, 0x04): [
        "captures/run/8ea7_c4_s04_trigger.png",
        "captures/run/8ea7_c4_s04_candidate1.png",
        "captures/run/8ea7_c4_s04_candidate2.png",
        "captures/run/8ea7_c4_s04_candidate3.png",
    ],
    (4, 0x06): [
        "captures/run/8eb0_c4_s06_trigger.png",
        "captures/run/8eb0_c4_s06_candidate1.png",
        "captures/run/8eb0_c4_s06_candidate2.png",
        "captures/run/8eb0_c4_s06_candidate3.png",
    ],
    (4, 0x0A): [
        "captures/run/8eb9_c4_s0a_trigger.png",
        "captures/run/8eb9_c4_s0a_candidate1.png",
        "captures/run/8eb9_c4_s0a_candidate2.png",
        "captures/run/8eb9_c4_s0a_candidate3.png",
    ],
    (4, 0x0B): [
        "captures/run/8ed7_c4_s0b_trigger.png",
        "captures/run/8ed7_c4_s0b_candidate1.png",
        "captures/run/8ed7_c4_s0b_candidate2.png",
        "captures/run/8ed7_c4_s0b_candidate3.png",
    ],
    (4, 0x0E): [
        "captures/run/8ee1_c4_s0e_trigger.png",
        "captures/run/8ee1_c4_s0e_candidate1.png",
        "captures/run/8ee1_c4_s0e_candidate2.png",
        "captures/run/8ee1_c4_s0e_candidate3.png",
    ],
    (4, 0x0F): [
        "captures/run/8ede_c4_s0f_trigger.png",
        "captures/run/8ede_c4_s0f_candidate1.png",
        "captures/run/8ede_c4_s0f_candidate2.png",
        "captures/run/8ede_c4_s0f_candidate3.png",
    ],
    (4, 0x12): [
        "captures/run/8edd_c4_s12_trigger.png",
        "captures/run/8edd_c4_s12_candidate1.png",
        "captures/run/8edd_c4_s12_candidate2.png",
        "captures/run/8edd_c4_s12_candidate3.png",
    ],
    (4, 0x13): [
        "captures/run/8ed4_c4_s13_trigger.png",
        "captures/run/8ed4_c4_s13_candidate1.png",
        "captures/run/8ed4_c4_s13_candidate2.png",
        "captures/run/8ed4_c4_s13_candidate3.png",
    ],
    (4, 0x21): [
        "captures/run/8ebd_c4_s21_trigger.png",
        "captures/run/8ebd_c4_s21_candidate1.png",
    ],
    (5, 0x03): [
        "captures/run/8ef4_c5_s03_candidate1.png",
        "captures/run/8ef4_c5_s03_candidate2.png",
        "captures/run/8ef4_c5_s03_candidate3.png",
        "captures/run/a8d7_c5_s03_hein_shaman_applied.png",
        "captures/analysis/a8d7_c5_s03_after_turn.gst",
    ],
    (5, 0x0A): [
        "captures/analysis/903c_c5_s0a_trigger.png",
        "captures/run/903c_c5_s0a_candidate1.png",
        "captures/run/903c_c5_s0a_candidate2.png",
        "captures/run/903c_c5_s0a_candidate3.png",
    ],
    (5, 0x09): [
        "captures/analysis/9037_c5_s09_trigger.png",
        "captures/run/9037_c5_s09_candidate1.png",
        "captures/run/9037_c5_s09_candidate2.png",
        "captures/run/9037_c5_s09_candidate3.png",
    ],
    (5, 0x04): [
        "captures/analysis/902b_c5_s04_trigger.png",
        "captures/run/902b_c5_s04_candidate1.png",
        "captures/run/902b_c5_s04_candidate2.png",
        "captures/run/902b_c5_s04_candidate3.png",
    ],
    (5, 0x11): [
        "captures/run/904f_c5_s11_trigger.png",
        "captures/run/904f_c5_s11_candidate1.png",
        "captures/run/904f_c5_s11_candidate2.png",
        "captures/run/904f_c5_s11_candidate3.png",
    ],
    (5, 0x12): [
        "captures/run/904e_c5_s12_trigger.png",
        "captures/run/904e_c5_s12_candidate1.png",
        "captures/run/904e_c5_s12_candidate2.png",
        "captures/run/904e_c5_s12_candidate3.png",
    ],
    (5, 0x13): [
        "captures/run/9050_c5_s13_trigger.png",
        "captures/run/9050_c5_s13_candidate1.png",
        "captures/run/9050_c5_s13_candidate2.png",
        "captures/run/9050_c5_s13_candidate3.png",
    ],
    (5, 0x0D): [
        "captures/run/904e_c5_s0d_trigger.png",
        "captures/run/904e_c5_s0d_candidate1.png",
        "captures/run/904e_c5_s0d_candidate2.png",
        "captures/run/904e_c5_s0d_candidate3.png",
    ],
    (5, 0x0B): [
        "captures/run/9052_c5_s0b_trigger.png",
        "captures/run/9052_c5_s0b_candidate1.png",
        "captures/run/9052_c5_s0b_candidate2.png",
        "captures/run/9052_c5_s0b_candidate3.png",
    ],
    (5, 0x15): [
        "captures/run/9037_c5_s15_trigger.png",
        "captures/run/9037_c5_s15_candidate1.png",
    ],
    (6, 0x01): [
        "captures/run/8e8d_c6_s01_trigger.png",
        "captures/run/8e8d_c6_s01_candidate1.png",
        "captures/run/8e8d_c6_s01_candidate2.png",
        "captures/run/8e8d_c6_s01_candidate3.png",
    ],
    (6, 0x06): [
        "captures/run/8eab_c6_s06_trigger.png",
        "captures/run/8eab_c6_s06_candidate1.png",
        "captures/run/8eab_c6_s06_candidate2.png",
        "captures/run/8eab_c6_s06_candidate3.png",
    ],
    (6, 0x05): [
        "captures/run/8eac_c6_s05_trigger.png",
        "captures/run/8eac_c6_s05_candidate1.png",
        "captures/run/8eac_c6_s05_candidate2.png",
        "captures/run/8eac_c6_s05_candidate3.png",
    ],
    (6, 0x04): [
        "captures/run/8ea9_c6_s04_trigger.png",
        "captures/run/8ea9_c6_s04_candidate1.png",
        "captures/run/8ea9_c6_s04_candidate2.png",
        "captures/run/8ea9_c6_s04_candidate3.png",
    ],
    (6, 0x0F): [
        "captures/run/8ee3_c6_s0f_trigger.png",
        "captures/run/8ee3_c6_s0f_candidate1.png",
        "captures/run/8ee3_c6_s0f_candidate2.png",
        "captures/run/8ee3_c6_s0f_candidate3.png",
    ],
    (6, 0x0D): [
        "captures/run/8ede_c6_s0d_trigger.png",
        "captures/run/8ede_c6_s0d_candidate1.png",
        "captures/run/8ede_c6_s0d_candidate2.png",
        "captures/run/8ede_c6_s0d_candidate3.png",
    ],
    (6, 0x0C): [
        "captures/run/8ed9_c6_s0c_trigger.png",
        "captures/run/8ed9_c6_s0c_candidate1.png",
        "captures/run/8ed9_c6_s0c_candidate2.png",
        "captures/run/8ed9_c6_s0c_candidate3.png",
    ],
    (6, 0x11): [
        "captures/run/8eda_c6_s11_trigger.png",
        "captures/run/8eda_c6_s11_candidate1.png",
        "captures/run/8eda_c6_s11_candidate2.png",
        "captures/run/8eda_c6_s11_candidate3.png",
    ],
    (6, 0x0B): [
        "captures/run/8ed0_c6_s0b_trigger.png",
        "captures/run/8ed0_c6_s0b_candidate1.png",
        "captures/run/8ed0_c6_s0b_candidate2.png",
        "captures/run/8ed0_c6_s0b_candidate3.png",
    ],
    (6, 0x1B): [
        "captures/run/8ebf_c6_s1b_trigger.png",
        "captures/run/8ebf_c6_s1b_candidate1.png",
    ],
    (9, 0x10): [
        "captures/run/d221_c9_s10_candidate1.png",
        "captures/run/d221_c9_s10_candidate2.png",
        "captures/run/d221_c9_s10_candidate3.png",
    ],
}
APPLICATION_VERIFIED = {(1, 0x01), (5, 0x03)}


def transition_signature(
    transition: ClassTransition,
) -> tuple[int, tuple[int, ...]]:
    return transition.current_class, transition.candidates


def live_verified_combinations(source: bytes) -> set[tuple[int, tuple[int, ...]]]:
    combinations = set()
    for commander_id, current_class in LIVE_EVIDENCE:
        transition = next(
            transition
            for transition in read_class_change_chain(source, commander_id)
            if transition.current_class == current_class
        )
        combinations.add(transition_signature(transition))
    return combinations


def inventory(source: bytes) -> dict[str, object]:
    classes = class_names(source)
    commanders = []
    unique_transitions: set[tuple[int, tuple[int, ...]]] = set()
    for commander_id in range(1, COMMANDER_COUNT + 1):
        pointer = class_change_chain_pointer(source, commander_id)
        transitions = []
        for index, transition in enumerate(
            read_class_change_chain(source, commander_id)
        ):
            offset = pointer + (
                index * 8
                if index < REGULAR_TRANSITION_COUNT
                else REGULAR_TRANSITION_COUNT * 8
            )
            candidates = [classes[class_id] for class_id in transition.candidates]
            unique_transitions.add(
                (transition.current_class, transition.candidates)
            )
            key = (commander_id, transition.current_class)
            live_verified = key in LIVE_EVIDENCE
            application_verified = key in APPLICATION_VERIFIED
            transitions.append(
                {
                    "index": index,
                    "offset": f"0x{offset:06X}",
                    "current": classes[transition.current_class],
                    "candidates": candidates,
                    "live_verified": live_verified,
                    "application_verified": application_verified,
                    "evidence": LIVE_EVIDENCE.get(key, []),
                }
            )
        commanders.append(
            {
                "id": commander_id,
                "name": KOREAN_NAME_BY_ID[commander_id],
                "pointer": f"0x{pointer:06X}",
                "transitions": transitions,
            }
        )

    live_verified_unique_transitions = live_verified_combinations(source)
    return {
        "source_pointer_table": "0x08253A",
        "commander_count": len(commanders),
        "transition_count": sum(
            len(commander["transitions"]) for commander in commanders
        ),
        "unique_transition_count": len(unique_transitions),
        "live_verified_transition_count": sum(
            transition["live_verified"]
            for commander in commanders
            for transition in commander["transitions"]
        ),
        "live_verified_unique_transition_count": len(
            live_verified_unique_transitions
        ),
        "application_verified_transition_count": sum(
            transition["application_verified"]
            for commander in commanders
            for transition in commander["transitions"]
        ),
        "commanders": commanders,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Class-Change Chain Inventory",
        "",
        "Generated by `python3 tools/class_change_inventory.py` from the Japanese REV00 ROM.",
        "Class IDs and transitions are source data; Korean labels are display targets.",
        "A translated static name does not imply that its candidate screen was live verified.",
        "",
        f"- Commanders: {result['commander_count']}",
        f"- Source transitions: {result['transition_count']}",
        f"- Unique current/candidate combinations: {result['unique_transition_count']}",
        f"- Live-verified transitions: {result['live_verified_transition_count']}",
        "- Live-verified unique combinations: "
        f"{result['live_verified_unique_transition_count']}",
        f"- Application-verified transitions: {result['application_verified_transition_count']}",
        "",
    ]
    for commander in result["commanders"]:
        lines.extend(
            [
                f"## {commander['id']}. {commander['name']}",
                "",
                f"Source pointer: `{commander['pointer']}`",
                "",
                "| Offset | Current | Candidates | Screen | Apply |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for transition in commander["transitions"]:
            current = transition["current"]
            current_label = f"`{current['id']:02X}` {current['ko']} ({current['jp']})"
            candidate_label = " / ".join(
                f"`{candidate['id']:02X}` {candidate['ko']} ({candidate['jp']})"
                for candidate in transition["candidates"]
            )
            live = "yes" if transition["live_verified"] else "pending"
            applied = "yes" if transition["application_verified"] else "pending"
            lines.append(
                f"| `{transition['offset']}` | {current_label} | "
                f"{candidate_label} | {live} | {applied} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Japanese-ROM class-change chain inventory"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(args.source_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['transition_count']} transitions, "
        f"{result['unique_transition_count']} unique, "
        f"{result['live_verified_transition_count']} screens and "
        f"{result['application_verified_transition_count']} applications verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
