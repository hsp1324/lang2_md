#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "localization/class_change_chains.json"
DEFAULT_OUTPUT = ROOT / "editor/static/class-previews"
SPRITE_CROP = (192, 72, 224, 112)


def candidate_capture_map(
    inventory: dict[str, object],
    root: Path = ROOT,
) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for commander in inventory["commanders"]:
        for transition in commander["transitions"]:
            for index, candidate in enumerate(transition["candidates"], 1):
                class_id = int(candidate["id"])
                if class_id in result:
                    continue
                suffix = f"_candidate{index}.png"
                evidence = next(
                    (
                        root / path
                        for path in transition.get("evidence", [])
                        if path.endswith(suffix) and (root / path).is_file()
                    ),
                    None,
                )
                if evidence is not None:
                    result[class_id] = evidence
    return result


def build_assets(inventory_path: Path, output_dir: Path) -> dict[str, object]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    captures = candidate_capture_map(inventory)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = {}
    for class_id, capture in sorted(captures.items()):
        image = Image.open(capture).convert("RGB")
        if image.size != (320, 240):
            raise ValueError(f"unexpected capture size for {capture}: {image.size}")
        target = output_dir / f"{class_id:02X}.png"
        image.crop(SPRITE_CROP).save(target, optimize=True)
        assets[str(class_id)] = {
            "file": target.name,
            "source": str(capture.relative_to(ROOT)),
            "crop": list(SPRITE_CROP),
        }

    manifest = {
        "generated_from": str(inventory_path.relative_to(ROOT)),
        "asset_count": len(assets),
        "assets": assets,
        "pending_class_ids": sorted(
            (
                {
                    int(transition["current"]["id"])
                    for commander in inventory["commanders"]
                    for transition in commander["transitions"]
                }
                | {
                    int(candidate["id"])
                    for commander in inventory["commanders"]
                    for transition in commander["transitions"]
                    for candidate in transition["candidates"]
                }
            )
            - {int(class_id) for class_id in assets}
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop class-change candidate sprites for the local editor"
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.inventory, args.output)
    print(
        f"{args.output}: {manifest['asset_count']} previews, "
        f"pending {manifest['pending_class_ids']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
