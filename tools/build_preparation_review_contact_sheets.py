#!/usr/bin/env python3
"""Build labeled contact sheets for manual preparation-surface review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix


DEFAULT_CAPTURE_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/preparation_review_contact_sheets"
GROUPS = ("overview", "allied", "arrangement", "shop", "fixed")
REVIEW_REQUIREMENTS = (
    {
        "id": "korean_labels",
        "description": (
            "every Korean commander, class, and mercenary label is intact"
        ),
    },
    {
        "id": "commander_mercenary_sprites",
        "description": (
            "commander and mercenary sprites contain no corrupted glyph blocks"
        ),
    },
    {
        "id": "fixed_map_records",
        "description": (
            "the fixed-unit map entry and every visible fixed record are intact"
        ),
    },
    {
        "id": "arrangement_shop_ui",
        "description": (
            "root, arrangement, shop-return, and roster surfaces are intact"
        ),
    },
    {
        "id": "numeric_tiles_borders",
        "description": "numeric fields, tile rows, minimap rows, and borders are intact",
    },
)
SHEET_COLUMNS = 2
SHEET_ROWS = 2
LABEL_HEIGHT = 20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def sources_for(pre_root: Path, group: str) -> list[Path]:
    if group == "overview":
        root = pre_root / "root.png"
        return [root] if root.is_file() else []
    if group == "allied":
        return sorted((pre_root / "allied").glob("*.png"))
    if group == "arrangement":
        return sorted((pre_root / "arrangement").glob("*.png"))
    if group == "shop":
        return sorted((pre_root.parent / "shop").glob("*.png"))
    if group == "fixed":
        return sorted((pre_root / "fixed").glob("*.png"))
    raise ValueError(f"unknown review group: {group}")


def compose_sheet(paths: list[Path]) -> Image.Image:
    if not paths:
        raise ValueError("contact sheet needs at least one source")
    with Image.open(paths[0]) as first:
        width, height = first.size
    canvas = Image.new(
        "RGB",
        (
            SHEET_COLUMNS * width,
            SHEET_ROWS * (height + LABEL_HEIGHT),
        ),
        "black",
    )
    draw = ImageDraw.Draw(canvas)
    for index, path in enumerate(paths):
        column = index % SHEET_COLUMNS
        row = index // SHEET_COLUMNS
        x = column * width
        y = row * (height + LABEL_HEIGHT)
        with Image.open(path) as source:
            frame = source.convert("RGB")
        if frame.size != (width, height):
            raise ValueError(f"capture dimensions changed: {path}")
        canvas.paste(frame, (x, y + LABEL_HEIGHT))
        draw.text((x + 4, y + 4), path.stem, fill="white")
    return canvas


def build_sheet(paths: list[Path], destination: Path) -> None:
    canvas = compose_sheet(paths)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def sheet_matches_sources(sheet: Path, sources: list[Path]) -> bool:
    expected = compose_sheet(sources)
    with Image.open(sheet) as opened:
        observed = opened.convert("RGB")
    return observed.size == expected.size and observed.tobytes() == expected.tobytes()


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    pre_root = (
        args.capture_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "pre"
    )
    if not pre_root.is_dir():
        raise FileNotFoundError(f"preparation capture root does not exist: {pre_root}")
    output = (
        args.output_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
    )
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"review output already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    groups = []
    for group in GROUPS:
        sources = sources_for(pre_root, group)
        sheets = []
        per_sheet = SHEET_COLUMNS * SHEET_ROWS
        for sheet_index, start in enumerate(range(0, len(sources), per_sheet), 1):
            selected = sources[start:start + per_sheet]
            destination = output / f"{group}_{sheet_index:02d}.png"
            build_sheet(selected, destination)
            sheets.append({
                "path": relative(destination),
                "sha256": sha256(destination),
                "sources": [
                    {
                        "path": relative(path),
                        "sha256": sha256(path),
                    }
                    for path in selected
                ],
            })
        groups.append({
            "group": group,
            "source_count": len(sources),
            "sheet_count": len(sheets),
            "sheets": sheets,
        })
    manifest = {
        "schema_version": 1,
        "status": "pending_manual_review",
        "profile": args.profile,
        "scenario": args.scenario,
        "run_id": args.run_id,
        "capture_root": relative(pre_root),
        "groups": groups,
        "review_requirements": list(REVIEW_REQUIREMENTS),
        "review_decision": None,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=("pure", "normal", "hard"), required=True
    )
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.capture_root = args.capture_root.resolve()
    args.output_root = args.output_root.resolve()
    manifest = build_manifest(args)
    print(
        f"{args.profile} Scenario {args.scenario}: "
        f"{sum(row['sheet_count'] for row in manifest['groups'])} sheets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
