#!/usr/bin/env python3
"""Audit the Empire localization script without mutating a ROM.

The report is intentionally address-oriented: it keeps the thousands of
dialogue records out of terminal output while making every remaining review
problem reproducible from the checked-in JSON.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = ROOT / "localization/empire/reviewed/script_ko.json"
DEFAULT_REPORT = ROOT / "localization/empire/reviewed/audit.json"

CONTROL_RE = re.compile(r"\{([0-9A-Fa-f]{4})\}")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
ASCII_WORD_RE = re.compile(r"[A-Za-z]")
BROKEN_RE = re.compile(r"\[(?:GLYPH|INDEX):|\{BROKEN_NAME_CONTROL\}")

EVENT_LINE_CELLS = 24
EVENT_PAGE_LINES = 3


def controls(text: str) -> list[int]:
    return [int(value, 16) for value in CONTROL_RE.findall(text)]


def visible_line(text: str) -> str:
    # Six cells is the longest current Empire actor label (베른하르트).
    return CONTROL_RE.sub("이름이름이름", text)


def record_key(kind: str, row: dict[str, object]) -> str:
    if kind == "event":
        return str(row["address"])
    return f"{kind}:{int(row['id']):02d}"


def audit_script(script: dict[str, object]) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    record_counts: Counter[str] = Counter()

    def issue(kind: str, row: dict[str, object], code: str, detail: str) -> None:
        issues.append(
            {
                "record": record_key(kind, row),
                "kind": kind,
                "code": code,
                "detail": detail,
            }
        )

    collections: list[tuple[str, list[dict[str, object]]]] = [
        ("condition", list(script["condition_records"])),
        ("scenario_description", list(script["scenario_description_records"])),
    ]
    for scenario, rows in dict(script["event_scenarios"]).items():
        for row in rows:
            row.setdefault("scenario", int(scenario))
        collections.append(("event", list(rows)))

    for kind, rows in collections:
        for row in rows:
            record_counts[kind] += 1
            review_status = str(row.get("review_status", "missing"))
            status_counts[review_status] += 1
            text = str(row["draft_korean"])
            source = str(row["source_chinese"])
            plain_text = CONTROL_RE.sub("", text)

            if controls(text) != controls(source):
                issue(
                    kind,
                    row,
                    "actor_control_mismatch",
                    f"source={controls(source)!r}, korean={controls(text)!r}",
                )
            if CJK_RE.search(plain_text):
                issue(kind, row, "chinese_remaining", "CJK ideograph remains")
            if JAPANESE_RE.search(plain_text):
                issue(kind, row, "japanese_remaining", "Japanese glyph remains")
            if ASCII_WORD_RE.search(plain_text):
                issue(kind, row, "ascii_word_remaining", "ASCII letter remains")
            if BROKEN_RE.search(plain_text):
                issue(kind, row, "broken_placeholder", "OCR placeholder remains")

            if kind == "condition":
                if len(text) != 7 * 16:
                    issue(
                        kind,
                        row,
                        "condition_layout",
                        f"{len(text)} cells; expected 112",
                    )
            elif kind == "event":
                for page_number, page in enumerate(text.split("\f"), 1):
                    lines = page.split("\n") or [""]
                    if len(lines) > EVENT_PAGE_LINES:
                        issue(
                            kind,
                            row,
                            "event_page_too_tall",
                            f"page {page_number}: {len(lines)} lines; maximum {EVENT_PAGE_LINES}",
                        )
                    for number, line in enumerate(lines, 1):
                        width = len(visible_line(line))
                        if width > EVENT_LINE_CELLS:
                            issue(
                                kind,
                                row,
                                "event_line_too_wide",
                                f"page {page_number}, line {number}: {width} cells; maximum {EVENT_LINE_CELLS}",
                            )

    issue_counts = Counter(str(row["code"]) for row in issues)
    expected_counts = {
        "condition": 32,
        "scenario_description": 31,
        "event": 3214,
    }
    counts_match = dict(record_counts) == expected_counts
    fully_reviewed = status_counts == Counter({"human reviewed": 3277})
    release_ready = counts_match and fully_reviewed and not issues
    return {
        "release_ready": release_ready,
        "record_counts": dict(record_counts),
        "expected_record_counts": expected_counts,
        "review_status_counts": dict(status_counts),
        "issue_counts": dict(issue_counts),
        "issue_count": len(issues),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    script = json.loads(args.script.read_text(encoding="utf-8"))
    report = audit_script(script)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Empire review audit: ready={report['release_ready']}, "
        f"issues={report['issue_count']}, "
        f"statuses={report['review_status_counts']}"
    )
    return 0 if report["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
