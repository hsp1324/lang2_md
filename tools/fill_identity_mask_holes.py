#!/usr/bin/env python3
"""Fill enclosed pinholes in editable AI-class identity masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    IDENTITY_MASK_OVERRIDES,
    enclosed_empty_points,
)


def fill_identity_mask_holes(path: Path) -> dict[str, list[list[int]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("unsupported AI identity-mask file version")
    masks = document.get("masks")
    if not isinstance(masks, dict):
        raise ValueError("AI identity-mask masks must be an object")

    changed: dict[str, list[list[int]]] = {}
    for key, raw_points in masks.items():
        points = {tuple(point) for point in raw_points}
        additions = enclosed_empty_points(points)
        if not additions:
            continue
        points |= additions
        masks[key] = [
            [x, y]
            for x, y in sorted(points, key=lambda point: (point[0], point[1]))
        ]
        changed[key] = [
            [x, y]
            for x, y in sorted(additions, key=lambda point: (point[1], point[0]))
        ]

    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--masks",
        type=Path,
        default=IDENTITY_MASK_OVERRIDES,
        help="identity-mask JSON to update",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    changed = fill_identity_mask_holes(args.masks)
    added = sum(len(points) for points in changed.values())
    print(
        f"filled {added} enclosed mask pixels across {len(changed)} classes"
    )
    for key, points in changed.items():
        print(f"  {key}: +{len(points)} {points}")


if __name__ == "__main__":
    main()
