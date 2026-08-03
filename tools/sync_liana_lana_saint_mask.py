#!/usr/bin/env python3
"""Copy Lana's user-painted Saint identity mask to matching Liana geometry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
DONOR = "3:17"
TARGET = "2:17"


def main() -> None:
    document = json.loads(MASK_PATH.read_text(encoding="utf-8"))
    masks = document["masks"]
    donor = masks.get(DONOR)
    if not donor:
        raise ValueError("Lana Saint mask 3:17 is missing")
    masks[TARGET] = [list(point) for point in donor]
    MASK_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{DONOR} -> {TARGET}: {len(donor)} pixels")


if __name__ == "__main__":
    main()
