#!/usr/bin/env python3
"""Apply human-reviewed Empire overrides without promoting the draft."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "localization/empire/draft/script_ko.json"
DEFAULT_OVERRIDES = (
    ROOT / "localization/empire/reviewed/scenario_overrides.json"
)
DEFAULT_EVENT_OVERRIDES = (
    ROOT / "localization/empire/reviewed/event_overrides.json"
)
DEFAULT_OUTPUT = ROOT / "localization/empire/reviewed/script_ko.json"

CONTROL_RE = re.compile(r"\{[0-9A-Fa-f]{4}\}")
EVENT_LINE_CELLS = 24
EVENT_PAGE_LINES = 3


def condition_layout(lines: list[str]) -> str:
    if len(lines) > 7:
        raise ValueError("condition layout exceeds seven rows")
    rows = [[" "] * 16 for _ in range(7)]
    for row, line in enumerate(lines):
        column = 0 if not line or line in ("승리조건", "패배조건") else 1
        if column + len(line) > 16:
            raise ValueError(f"condition line exceeds 16 cells: {line!r}")
        rows[row][column : column + len(line)] = line
    return "".join("".join(row) for row in rows)


def _visible_units(text: str) -> list[tuple[str, int]]:
    """Keep actor controls atomic while measuring the widest actor label."""

    units: list[tuple[str, int]] = []
    cursor = 0
    for match in CONTROL_RE.finditer(text):
        units.extend((char, 1) for char in text[cursor : match.start()])
        units.append((match.group(0), 6))  # 베른하르트
        cursor = match.end()
    units.extend((char, 1) for char in text[cursor:])
    return units


def _wrap_event_line(text: str) -> list[str]:
    units = _visible_units(text.strip())
    rows: list[str] = []
    while units:
        width = 0
        end = 0
        while end < len(units) and width + units[end][1] <= EVENT_LINE_CELLS:
            width += units[end][1]
            end += 1
        if end == len(units):
            rows.append("".join(value for value, _ in units).strip())
            break
        split = next(
            (
                index
                for index in range(end - 1, 0, -1)
                if units[index][0].isspace()
            ),
            end,
        )
        rows.append("".join(value for value, _ in units[:split]).strip())
        units = units[split:]
        while units and units[0][0].isspace():
            units.pop(0)
    return rows or [""]


def layout_event_text(text: str) -> str:
    """Fit translated dialogue into 24x3-cell boxes losslessly."""

    pages: list[str] = []
    for authored_page in text.split("\f"):
        rows: list[str] = []
        for line in authored_page.split("\n"):
            rows.extend(_wrap_event_line(line))
        pages.extend(
            "\n".join(rows[index : index + EVENT_PAGE_LINES])
            for index in range(0, len(rows), EVENT_PAGE_LINES)
        )
    return "\f".join(pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument(
        "--event-overrides", type=Path, default=DEFAULT_EVENT_OVERRIDES
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    draft = json.loads(args.draft.read_text(encoding="utf-8"))
    overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
    event_overrides_payload = json.loads(
        args.event_overrides.read_text(encoding="utf-8")
    )
    event_overrides = dict(event_overrides_payload.get("events", {}))
    output = deepcopy(draft)

    condition_lines = overrides["condition_lines"]
    if set(map(int, condition_lines)) != set(range(32)):
        raise ValueError("human-reviewed Empire conditions must cover IDs 0..31")
    for row in output["condition_records"]:
        row["draft_korean"] = condition_layout(
            list(condition_lines[str(row["id"])])
        )
        row["review_status"] = "human reviewed"

    description_overrides = overrides.get("scenario_descriptions", {})
    for row in output["scenario_description_records"]:
        key = str(row["id"])
        row["draft_korean"] = str(
            description_overrides.get(key, row["draft_korean"])
        )
        row["review_status"] = (
            "human reviewed" if key in description_overrides else "machine draft"
        )

    seen_event_addresses: set[str] = set()
    reviewed_event_count = 0
    for rows in output["event_scenarios"].values():
        for row in rows:
            address = str(row["address"])
            seen_event_addresses.add(address)
            if address in event_overrides:
                row["draft_korean"] = str(event_overrides[address])
                row["review_status"] = "human reviewed"
                reviewed_event_count += 1
            else:
                row["review_status"] = "machine draft; layout validated"
            row["draft_korean"] = layout_event_text(str(row["draft_korean"]))

    unknown_overrides = set(event_overrides) - seen_event_addresses
    if unknown_overrides:
        raise ValueError(
            f"unknown Empire event override {min(unknown_overrides)}"
        )

    release_ready = (
        len(description_overrides) == 31 and reviewed_event_count == 3214
    )
    output["status"] = (
        "human reviewed; release ready"
        if release_ready
        else (
            "human review in progress; machine-assisted event dialogue remains; "
            "not release ready"
        )
    )
    output["review_summary"] = {
        "condition_records": 32,
        "scenario_description_records": len(description_overrides),
        "event_records": reviewed_event_count,
        "release_ready": release_ready,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}: 32 conditions reviewed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
