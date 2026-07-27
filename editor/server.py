#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from editor.model import class_change_editor_model, item_editor_model
from tools.class_change_data import patch_class_change_chains
from tools.class_hire_data import patch_class_hire_unlocks
from tools.item_data import patch_items
from tools.scenario_data import (
    SCENARIO_COUNT,
    patch_scenario,
    read_scenario,
    update_checksum,
)


STATIC = Path(__file__).resolve().parent / "static"
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
ROM_CHOICES = {
    "korean": ROOT / "roms/builds/Langrisser II (Korean).md",
    "japanese": REFERENCE_ROM,
}
OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Korean Editor Edit).md"
AI_MASK_FILE = ROOT / "editor/ai_identity_masks.json"
AI_MOUNT_MASK_FILE = ROOT / "editor/ai_mount_masks.json"
AI_DESIGN_FILE = ROOT / "editor/ai_class_design_overrides.json"
AI_SPRITE_MANIFEST = STATIC / "ai-class-sprites/manifest.json"
AI_MASK_BUILD_LOCK = threading.Lock()
MEGA_DRIVE_CHANNEL_LEVELS = (0, 36, 73, 109, 146, 182, 219, 255)


def normalize_identity_mask_points(
    raw_points: object,
) -> list[list[int]]:
    if not isinstance(raw_points, list):
        raise ValueError("mask points must be a list")
    points: set[tuple[int, int]] = set()
    for raw_point in raw_points:
        if (
            not isinstance(raw_point, list)
            or len(raw_point) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in raw_point
            )
        ):
            raise ValueError("mask point must contain two integers")
        x, y = raw_point
        if not (0 <= x < 16 and 0 <= y < 16):
            raise ValueError("mask point must be inside the 16x16 grid")
        points.add((x, y))
    return [list(point) for point in sorted(points)]


def write_identity_mask_document(document: dict[str, object]) -> None:
    write_mask_document(AI_MASK_FILE, document)


def write_mask_document(
    path: Path,
    document: dict[str, object],
) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def update_identity_mask_override(
    commander_id: int,
    class_id: int,
    points: object,
    *,
    reset: bool = False,
) -> list[list[int]]:
    from tools.build_ai_class_sprite_assets import identity_mask_key

    normalized = normalize_identity_mask_points(points)
    document = json.loads(AI_MASK_FILE.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("unsupported AI identity-mask file version")
    masks = document.get("masks")
    if not isinstance(masks, dict):
        raise ValueError("AI identity-mask masks must be an object")
    key = identity_mask_key(commander_id, class_id)
    if reset:
        masks.pop(key, None)
    else:
        masks[key] = normalized
    write_identity_mask_document(document)
    return normalized


def update_identity_mask_manifest(
    commander_id: int,
    class_id: int,
    points: list[list[int]],
    *,
    reset: bool = False,
) -> dict[str, object]:
    manifest = json.loads(
        AI_SPRITE_MANIFEST.read_text(encoding="utf-8")
    )
    row = manifest["commanders"][str(commander_id)]["classes"][
        str(class_id)
    ]
    effective_points = (
        row["identity_lock_default_points"]
        if reset
        else points
    )
    row["identity_lock_points"] = effective_points
    row["identity_lock_pixel_count"] = len(effective_points)
    row["identity_lock_mode"] = "automatic" if reset else "custom"
    row["identity_mask_pending_rebuild"] = True
    temporary = AI_SPRITE_MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(AI_SPRITE_MANIFEST)
    return manifest


def update_mount_mask_override(
    commander_id: int,
    class_id: int,
    points: object,
) -> list[list[int]]:
    from tools.build_ai_class_sprite_assets import identity_mask_key

    normalized = normalize_identity_mask_points(points)
    document = (
        json.loads(AI_MOUNT_MASK_FILE.read_text(encoding="utf-8"))
        if AI_MOUNT_MASK_FILE.is_file()
        else {"version": 1, "masks": {}}
    )
    if document.get("version") != 1:
        raise ValueError("unsupported AI mount-mask file version")
    masks = document.get("masks")
    if not isinstance(masks, dict):
        raise ValueError("AI mount-mask masks must be an object")
    masks[identity_mask_key(commander_id, class_id)] = normalized
    write_mask_document(AI_MOUNT_MASK_FILE, document)
    return normalized


def update_mount_mask_manifest(
    commander_id: int,
    class_id: int,
    points: list[list[int]],
) -> dict[str, object]:
    manifest = json.loads(
        AI_SPRITE_MANIFEST.read_text(encoding="utf-8")
    )
    row = manifest["commanders"][str(commander_id)]["classes"][
        str(class_id)
    ]
    row["mount_lock_points"] = points
    row["mount_lock_pixel_count"] = len(points)
    row["mount_lock_mode"] = "custom"
    row["mount_mask_pending_rebuild"] = True
    temporary = AI_SPRITE_MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(AI_SPRITE_MANIFEST)
    return manifest


def normalize_ai_design_pixels(
    raw_pixels: object,
) -> list[list[int]]:
    if not isinstance(raw_pixels, list) or len(raw_pixels) != 256:
        raise ValueError("design must contain exactly 256 RGBA pixels")
    pixels: list[list[int]] = []
    for raw_pixel in raw_pixels:
        if (
            not isinstance(raw_pixel, list)
            or len(raw_pixel) != 4
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 255
                for value in raw_pixel
            )
        ):
            raise ValueError(
                "each design pixel must contain four byte values"
            )
        red, green, blue, alpha = raw_pixel
        if alpha < 128:
            pixels.append([0, 0, 0, 0])
            continue
        pixels.append([
            min(
                MEGA_DRIVE_CHANNEL_LEVELS,
                key=lambda level: abs(level - red),
            ),
            min(
                MEGA_DRIVE_CHANNEL_LEVELS,
                key=lambda level: abs(level - green),
            ),
            min(
                MEGA_DRIVE_CHANNEL_LEVELS,
                key=lambda level: abs(level - blue),
            ),
            255,
        ])
    return pixels


def visible_design_colors(
    pixels: list[list[int]],
) -> set[tuple[int, int, int, int]]:
    return {
        tuple(pixel)
        for pixel in pixels
        if pixel[3]
    }


def design_palette(
    pixels: list[list[int]],
) -> list[str]:
    counts: dict[tuple[int, int, int], int] = {}
    for red, green, blue, alpha in pixels:
        if not alpha:
            continue
        color = (red, green, blue)
        counts[color] = counts.get(color, 0) + 1
    return [
        f"#{red:02x}{green:02x}{blue:02x}"
        for (red, green, blue), _ in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:6]
    ]


def write_ai_design_document(document: dict[str, object]) -> None:
    temporary = AI_DESIGN_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(AI_DESIGN_FILE)


def write_ai_design_manifest(manifest: dict[str, object]) -> None:
    temporary = AI_SPRITE_MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(AI_SPRITE_MANIFEST)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def send_json(self, value: object, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenarios":
            return self.send_json({"scenarios": list(range(1, SCENARIO_COUNT + 1))})
        if parsed.path == "/api/items":
            try:
                rom_key = parse_qs(parsed.query).get("rom", ["korean"])[0]
                rom_path = ROM_CHOICES[rom_key]
                result = item_editor_model(rom_path.read_bytes())
                result["rom"] = rom_key
                result["rom_path"] = str(rom_path.relative_to(ROOT))
                return self.send_json(result)
            except (KeyError, OSError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path == "/api/class-changes":
            try:
                rom_key = parse_qs(parsed.query).get("rom", ["korean"])[0]
                rom_path = ROM_CHOICES[rom_key]
                result = class_change_editor_model(
                    rom_path.read_bytes(),
                    REFERENCE_ROM.read_bytes(),
                )
                result["rom"] = rom_key
                result["rom_path"] = str(rom_path.relative_to(ROOT))
                return self.send_json(result)
            except (KeyError, OSError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/scenarios/"):
            try:
                number = int(parsed.path.rsplit("/", 1)[1])
                rom_key = parse_qs(parsed.query).get("rom", ["korean"])[0]
                rom_path = ROM_CHOICES[rom_key]
                result = read_scenario(rom_path.read_bytes(), REFERENCE_ROM.read_bytes(), number)
                result["rom"] = rom_key
                result["rom_path"] = str(rom_path.relative_to(ROOT))
                return self.send_json(result)
            except (KeyError, OSError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/ai-class-design":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                commander_id = int(request["commander_id"])
                class_id = int(request["class_id"])
                reset = request.get("reset", False)
                if not isinstance(reset, bool):
                    raise ValueError("reset must be boolean")
                with AI_MASK_BUILD_LOCK:
                    manifest = json.loads(
                        AI_SPRITE_MANIFEST.read_text(encoding="utf-8")
                    )
                    row = manifest["commanders"][str(commander_id)][
                        "classes"
                    ][str(class_id)]
                    if not row["redesigned"]:
                        raise ValueError(
                            "AI 상위 클래스만 디자인을 편집할 수 있습니다"
                        )
                    if AI_DESIGN_FILE.is_file():
                        document = json.loads(
                            AI_DESIGN_FILE.read_text(encoding="utf-8")
                        )
                    else:
                        document = {"version": 1, "designs": {}}
                    if document.get("version") != 1:
                        raise ValueError(
                            "unsupported AI class-design override version"
                        )
                    designs = document.get("designs")
                    if not isinstance(designs, dict):
                        raise ValueError(
                            "AI class-design overrides must be an object"
                        )
                    key = f"{commander_id}:{class_id:02X}"
                    target = (
                        STATIC
                        / "ai-class-sprites"
                        / str(commander_id)
                        / f"{class_id:02X}.png"
                    )
                    original_path = (
                        STATIC
                        / "class-sprites/commanders"
                        / str(commander_id)
                        / f"{class_id:02X}-p1.png"
                    )
                    current = Image.open(target).convert("RGBA")
                    current_pixels = [
                        list(pixel) for pixel in current.getdata()
                    ]
                    existing = designs.get(key)
                    if reset:
                        if not isinstance(existing, dict):
                            raise ValueError(
                                "저장된 사용자 디자인이 없습니다"
                            )
                        pixels = normalize_ai_design_pixels(
                            existing.get("base_pixels")
                        )
                        designs.pop(key, None)
                    else:
                        pixels = normalize_ai_design_pixels(
                            request.get("pixels")
                        )
                        base_pixels = (
                            existing.get("base_pixels")
                            if isinstance(existing, dict)
                            else current_pixels
                        )

                    original = Image.open(original_path).convert("RGBA")
                    lock_points = (
                        row.get("identity_lock_points", [])
                        + row.get("mount_lock_points", [])
                    )
                    for raw_point in lock_points:
                        x, y = raw_point
                        pixels[y * 16 + x] = list(
                            original.getpixel((x, y))
                        )
                    colors = visible_design_colors(pixels)
                    if len(colors) > 15:
                        raise ValueError(
                            "메가드라이브 4bpp 제한은 투명색을 제외한 "
                            f"15색입니다. 현재 {len(colors)}색입니다"
                        )
                    revision = time.time_ns()
                    if not reset:
                        designs[key] = {
                            "revision": revision,
                            "pixels": pixels,
                            "base_pixels": base_pixels,
                        }
                    write_ai_design_document(document)

                    image = Image.new("RGBA", (16, 16))
                    image.putdata(
                        [tuple(pixel) for pixel in pixels]
                    )
                    temporary_image = target.with_suffix(".png.tmp")
                    image.save(
                        temporary_image,
                        format="PNG",
                        optimize=True,
                    )
                    temporary_image.replace(target)

                    original_pixels = list(original.getdata())
                    row["changed_pixel_count"] = sum(
                        tuple(pixel) != source_pixel
                        for pixel, source_pixel in zip(
                            pixels,
                            original_pixels,
                        )
                    )
                    row["pixel_palette"] = design_palette(pixels)
                    row["design_override"] = not reset
                    row["design_revision"] = revision
                    row["identity_mask_pending_rebuild"] = False
                    row["mount_mask_pending_rebuild"] = False
                    marker = "·사용자 16×16 디자인 편집 적용"
                    feature = str(row.get("feature", ""))
                    if reset:
                        row["feature"] = feature.replace(marker, "")
                    elif marker not in feature:
                        row["feature"] = feature + marker
                    write_ai_design_manifest(manifest)
                return self.send_json({
                    "ok": True,
                    "asset_version": manifest["asset_version"],
                    "design_override": not reset,
                    "design_revision": revision,
                    "visible_color_count": len(colors),
                    "changed_pixel_count": row["changed_pixel_count"],
                    "pixel_palette": row["pixel_palette"],
                    "pixels": pixels,
                })
            except (
                KeyError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path == "/api/ai-class-mask":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                commander_id = int(request["commander_id"])
                class_id = int(request["class_id"])
                manifest = json.loads(
                    AI_SPRITE_MANIFEST.read_text(encoding="utf-8")
                )
                row = manifest["commanders"][str(commander_id)][
                    "classes"
                ][str(class_id)]
                if not row["redesigned"]:
                    raise ValueError(
                        "ROM 원본 유지 클래스에는 별도 마스크를 적용하지 않습니다"
                    )
                reset = request.get("reset", False)
                if not isinstance(reset, bool):
                    raise ValueError("reset must be boolean")
                points = request.get("points", [])
                normalize_identity_mask_points(points)
                with AI_MASK_BUILD_LOCK:
                    normalized = update_identity_mask_override(
                        commander_id,
                        class_id,
                        points,
                        reset=reset,
                    )
                    rebuilt = update_identity_mask_manifest(
                        commander_id,
                        class_id,
                        normalized,
                        reset=reset,
                    )
                updated_row = rebuilt["commanders"][str(commander_id)][
                    "classes"
                ][str(class_id)]
                return self.send_json({
                    "ok": True,
                    "asset_version": rebuilt["asset_version"],
                    "identity_lock_mode": updated_row[
                        "identity_lock_mode"
                    ],
                    "identity_lock_pixel_count": updated_row[
                        "identity_lock_pixel_count"
                    ],
                })
            except (
                KeyError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path == "/api/ai-class-mount-mask":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                commander_id = int(request["commander_id"])
                class_id = int(request["class_id"])
                manifest = json.loads(
                    AI_SPRITE_MANIFEST.read_text(encoding="utf-8")
                )
                row = manifest["commanders"][str(commander_id)][
                    "classes"
                ][str(class_id)]
                if not row["redesigned"]:
                    raise ValueError(
                        "ROM 원본 유지 클래스에는 별도 탈것 마스크를 "
                        "적용하지 않습니다"
                    )
                points = request.get("points", [])
                normalize_identity_mask_points(points)
                with AI_MASK_BUILD_LOCK:
                    normalized = update_mount_mask_override(
                        commander_id,
                        class_id,
                        points,
                    )
                    updated_manifest = update_mount_mask_manifest(
                        commander_id,
                        class_id,
                        normalized,
                    )
                updated_row = updated_manifest["commanders"][
                    str(commander_id)
                ]["classes"][str(class_id)]
                return self.send_json({
                    "ok": True,
                    "asset_version": updated_manifest["asset_version"],
                    "mount_lock_mode": updated_row["mount_lock_mode"],
                    "mount_lock_pixel_count": updated_row[
                        "mount_lock_pixel_count"
                    ],
                })
            except (
                KeyError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path != "/api/build":
            return self.send_json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            rom_key = request.get("rom", "korean")
            source = ROM_CHOICES[rom_key]
            data = bytearray(source.read_bytes())
            scenarios = request.get("scenarios")
            if scenarios is None and "number" in request:
                scenarios = [{
                    "number": request["number"],
                    "records": request["records"],
                }]
            for scenario in scenarios or []:
                patch_scenario(
                    data,
                    int(scenario["number"]),
                    scenario["records"],
                )
            if "items" in request:
                patch_items(data, request["items"])
            if "class_changes" in request:
                patch_class_change_chains(data, request["class_changes"])
            if "class_hires" in request:
                patch_class_hire_unlocks(data, request["class_hires"])
            if (
                not scenarios
                and "items" not in request
                and "class_changes" not in request
                and "class_hires" not in request
            ):
                raise ValueError("build request contains no editable data")
            checksum = update_checksum(data)
            OUTPUT_ROM.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_ROM.write_bytes(data)
            return self.send_json({
                "ok": True,
                "checksum": f"{checksum:04X}",
                "output": str(OUTPUT_ROM.relative_to(ROOT)),
            })
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="Langrisser II MD data editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Game data editor: http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
