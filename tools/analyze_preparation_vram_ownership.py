#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
GST_VDP_REG_OFFSET = 0xFA
GST_VDP_REG_COUNT = 24
GST_VRAM_OFFSET = 0x12478
VRAM_SIZE = 0x10000
TILE_BYTES = 32
HSCROLL_TABLE_BYTES = 0x400

HISTORICAL_HSCROLL_TILES = (
    0x07A1, 0x07A2, 0x07A3, 0x07A4, 0x07A5, 0x07A6, 0x07A7, 0x07A8,
    0x07A9, 0x07AD, 0x07AF, 0x07B0, 0x07B1, 0x07B3, 0x07B4, 0x07B5,
    0x07AA, 0x07AB, 0x07AC, 0x07B6, 0x07B7, 0x07B9, 0x07BB, 0x07BC,
)

DEFAULT_HISTORICAL_GST = (
    ROOT / "captures/analysis/hard_fbe2_s06_after_shop_enemy_detail.gst"
)
DEFAULT_PRE_GST = (
    ROOT / "captures/analysis/hard_7b41_s09_pre_shop_enemy_detail.gst"
)
DEFAULT_POST_GST = (
    ROOT / "captures/analysis/hard_7b41_s09_post_shop_enemy_detail.gst"
)
DEFAULT_PRE_CAPTURES = (
    ROOT / "captures/run/hard_7b41_s09_pre_shop_prep.png",
    ROOT / "captures/run/hard_7b41_s09_pre_shop_arrangement.png",
    ROOT / "captures/run/hard_7b41_s09_pre_shop_enemy_detail.png",
)
DEFAULT_POST_CAPTURES = (
    ROOT / "captures/run/hard_7b41_s09_post_shop_prep.png",
    ROOT / "captures/run/hard_7b41_s09_post_shop_arrangement.png",
    ROOT / "captures/run/hard_7b41_s09_post_shop_enemy_detail.png",
)
DEFAULT_NORMAL_POST_GST = (
    ROOT / "captures/analysis/normal_3203_s09_post_shop_enemy_detail.gst"
)
DEFAULT_NORMAL_PRE_CAPTURES = (
    ROOT / "captures/run/normal_3203_s09_pre_shop_prep.png",
    ROOT / "captures/run/normal_3203_s09_pre_shop_arrangement.png",
    ROOT / "captures/run/normal_3203_s09_pre_shop_enemy_detail.png",
)
DEFAULT_NORMAL_POST_CAPTURES = (
    ROOT / "captures/run/normal_3203_s09_post_shop_prep.png",
    ROOT / "captures/run/normal_3203_s09_post_shop_arrangement.png",
    ROOT / "captures/run/normal_3203_s09_post_shop_enemy_detail.png",
)
DEFAULT_RETAINED_GST_MANIFEST = (
    ROOT / "localization/preparation_vram_ownership_sources.json"
)
RETAINED_GST_SCOPE = "current_v137_preparation_vram_ownership_source_lock"
RETAINED_GST_FAMILY_IDS = (
    "current_candidate_first_turn_matrix",
    "fresh_s1_preparation",
    "pure_s19_preparation_roundtrip",
    "exact_release_s13_s16_battle_cache",
)


@dataclass(frozen=True)
class GstVdpState:
    path: Path
    registers: bytes
    vram: bytes

    @property
    def hscroll_mode(self) -> int:
        return self.registers[11] & 0x03

    @property
    def hscroll_base(self) -> int:
        return (self.registers[13] & 0x3F) << 10

    @property
    def plane_width(self) -> int:
        return {0: 32, 1: 64, 3: 128}[self.registers[16] & 0x03]

    @property
    def plane_height(self) -> int:
        return {0: 32, 1: 64, 3: 128}[(self.registers[16] >> 4) & 0x03]

    @property
    def plane_bases(self) -> dict[str, int]:
        return {
            "plane_a": (self.registers[2] & 0x38) << 10,
            "plane_b": (self.registers[4] & 0x07) << 13,
            "window": (self.registers[3] & 0x3E) << 10,
        }

    @property
    def sat_base(self) -> int:
        return (self.registers[5] & 0x7F) << 9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gst(path: Path) -> GstVdpState:
    data = path.read_bytes()
    if data[:4] != b"GST@":
        raise ValueError(f"{path} is not a BlastEm GST state")
    registers = data[GST_VDP_REG_OFFSET : GST_VDP_REG_OFFSET + GST_VDP_REG_COUNT]
    vram = data[GST_VRAM_OFFSET : GST_VRAM_OFFSET + VRAM_SIZE]
    if len(registers) != GST_VDP_REG_COUNT or len(vram) != VRAM_SIZE:
        raise ValueError(f"{path} is truncated")
    return GstVdpState(path=path, registers=registers, vram=vram)


def nonzero_ranges(payload: bytes, base: int) -> list[dict[str, object]]:
    indexes = [index for index, value in enumerate(payload) if value]
    if not indexes:
        return []
    ranges = []
    start = end = indexes[0]
    for index in indexes[1:]:
        if index == end + 1:
            end = index
        else:
            ranges.append(
                {
                    "start": f"0x{base + start:04X}",
                    "end": f"0x{base + end:04X}",
                    "bytes": end - start + 1,
                }
            )
            start = end = index
    ranges.append(
        {
            "start": f"0x{base + start:04X}",
            "end": f"0x{base + end:04X}",
            "bytes": end - start + 1,
        }
    )
    return ranges


def referenced_tiles(state: GstVdpState) -> set[int]:
    tiles: set[int] = set()
    cells = state.plane_width * state.plane_height
    for base in state.plane_bases.values():
        end = base + cells * 2
        if end > VRAM_SIZE:
            continue
        for offset in range(base, end, 2):
            tiles.add(int.from_bytes(state.vram[offset : offset + 2], "big") & 0x07FF)

    tiles.update(sprite_referenced_tiles(state))
    return tiles


def sprite_referenced_tiles(state: GstVdpState) -> set[int]:
    """Return every pattern cell owned by the live linked SAT entries."""
    tiles: set[int] = set()
    index = 0
    seen: set[int] = set()
    while (
        index not in seen
        and index < 80
        and state.sat_base + index * 8 + 8 <= VRAM_SIZE
    ):
        seen.add(index)
        offset = state.sat_base + index * 8
        size_link = int.from_bytes(state.vram[offset + 2 : offset + 4], "big")
        tile = int.from_bytes(state.vram[offset + 4 : offset + 6], "big") & 0x07FF
        width = ((size_link >> 10) & 0x03) + 1
        height = ((size_link >> 8) & 0x03) + 1
        tiles.update((tile + cell) & 0x07FF for cell in range(width * height))
        index = size_link & 0x7F
        if index == 0:
            break
    return tiles


def reserved_table_tiles(state: GstVdpState) -> set[int]:
    reserved: set[int] = set()
    table_bytes = state.plane_width * state.plane_height * 2
    for base in state.plane_bases.values():
        reserved.update(range(base // TILE_BYTES, min(0x800, (base + table_bytes + 31) // 32)))
    reserved.update(
        range(
            state.sat_base // TILE_BYTES,
            min(0x800, (state.sat_base + 80 * 8 + 31) // 32),
        )
    )
    reserved.update(
        range(
            state.hscroll_base // TILE_BYTES,
            min(
                0x800,
                (state.hscroll_base + HSCROLL_TABLE_BYTES + 31) // 32,
            ),
        )
    )
    return reserved


def _source_path(value: object) -> Path:
    if not isinstance(value, str) or not value.endswith(".gst"):
        raise ValueError("retained source path must be a .gst string")
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    return path


def _expand_retained_family(family: dict[str, object]) -> list[Path]:
    family_id = family.get("id")
    if family.get("classification") != "exact_current_release":
        raise ValueError(f"retained family {family_id!r} is not exact-current")

    if family_id == "current_candidate_first_turn_matrix":
        template = (
            "captures/analysis/v137-final-frozen-20260811-02-{profile}-"
            "first-turn-{scenario:02d}-{phase}.gst"
        )
        if family.get("path_template") != template:
            raise ValueError("current first-turn source template changed")
        if family.get("profiles") != ["pure", "normal", "hard"]:
            raise ValueError("current first-turn profiles changed")
        if family.get("scenarios") != "1-31":
            raise ValueError("current first-turn scenario coverage changed")
        phases = [
            "loader_s{scenario:02d}_entry_turn1_entry",
            "first-turn_s{scenario:02d}_endpoint",
        ]
        if family.get("phases") != phases:
            raise ValueError("current first-turn phases changed")
        return [
            _source_path(
                template.format(
                    profile=profile,
                    scenario=scenario,
                    phase=phase.format(scenario=scenario),
                )
            )
            for profile in ("pure", "normal", "hard")
            for scenario in range(1, 32)
            for phase in phases
        ]

    if family_id == "fresh_s1_preparation":
        template = (
            "captures/run/v137-s13-cache-formal/fresh-seeds/{profile}/"
            "v137-s13-cache-current-20260812/fresh_s1_preparation.gst"
        )
        if family.get("path_template") != template:
            raise ValueError("fresh S1 preparation source template changed")
        if family.get("profiles") != ["pure", "normal", "hard"]:
            raise ValueError("fresh S1 preparation profiles changed")
        return [
            _source_path(template.format(profile=profile))
            for profile in ("pure", "normal", "hard")
        ]

    if family_id == "pure_s19_preparation_roundtrip":
        values = family.get("paths")
        if not isinstance(values, list) or not values:
            raise ValueError("pure S19 preparation paths are missing")
        return [_source_path(value) for value in values]

    if family_id == "exact_release_s13_s16_battle_cache":
        template = (
            "captures/run/v137-s13-cache-formal/hover/{case}/states/{phase}.gst"
        )
        cases = [
            "stock-pure-s13-74-current-20260812-01",
            "stock-normal-s13-74-current-20260812-01",
            "stock-hard-s13-74-current-20260812-01",
            "stock-hard-s13-63-current-20260812-01",
            "stock-pure-s16-73-current-20260812-01",
            "stock-normal-s16-73-current-20260812-01",
        ]
        phases = ["before_hover", "command_open", "target_hover"]
        if family.get("path_template") != template:
            raise ValueError("S13/S16 battle-cache source template changed")
        if family.get("cases") != cases or family.get("phases") != phases:
            raise ValueError("S13/S16 battle-cache coverage changed")
        return [
            _source_path(template.format(case=case, phase=phase))
            for case in cases
            for phase in phases
        ]

    raise ValueError(f"unknown retained source family: {family_id!r}")


def _path_hash_aggregate(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.resolve().relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def retained_source_states(
    manifest_path: Path = DEFAULT_RETAINED_GST_MANIFEST,
) -> tuple[list[GstVdpState], list[GstVdpState], dict[str, object]]:
    from tools import v137_release_identity as release_identity

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("retained source manifest schema changed")
    if manifest.get("scope") != RETAINED_GST_SCOPE:
        raise ValueError("retained source manifest scope changed")
    if manifest.get("release_generation") != release_identity.RELEASE_IDENTITY_GENERATION:
        raise ValueError("retained source release generation changed")
    if manifest.get("release_rom_sha256") != release_identity.RELEASE_ROM_SHA256:
        raise ValueError("retained source release hashes changed")
    families = manifest.get("families")
    if not isinstance(families, list):
        raise ValueError("retained source families are missing")
    if tuple(family.get("id") for family in families) != RETAINED_GST_FAMILY_IDS:
        raise ValueError("retained source family order or membership changed")

    paths: list[Path] = []
    preparation_paths: list[Path] = []
    family_reports = []
    for family in families:
        family_paths = _expand_retained_family(family)
        if len(family_paths) != family.get("expected_state_count"):
            raise ValueError(f"retained family {family.get('id')} count changed")
        aggregate = _path_hash_aggregate(family_paths)
        if aggregate != family.get("path_hash_aggregate_sha256"):
            raise ValueError(f"retained family {family.get('id')} hash changed")
        paths.extend(family_paths)
        if family.get("preparation_surface") is True:
            preparation_paths.extend(family_paths)
        elif family.get("preparation_surface") is not False:
            raise ValueError(
                f"retained family {family.get('id')} surface ownership is missing"
            )
        family_reports.append(
            {
                "id": family["id"],
                "state_count": len(family_paths),
                "path_hash_aggregate_sha256": aggregate,
                "preparation_surface": family["preparation_surface"],
            }
        )

    if len(paths) != len(set(paths)):
        raise ValueError("retained source manifest contains duplicate GST paths")
    if len(paths) != manifest.get("expected_state_count"):
        raise ValueError("retained source manifest total count changed")
    aggregate = _path_hash_aggregate(paths)
    if aggregate != manifest.get("path_hash_aggregate_sha256"):
        raise ValueError("retained source manifest aggregate hash changed")
    states_by_path = {path: load_gst(path) for path in paths}
    report = {
        "path": str(manifest_path.resolve().relative_to(ROOT)),
        "sha256": sha256(manifest_path),
        "scope": manifest["scope"],
        "release_generation": manifest["release_generation"],
        "state_count": len(paths),
        "preparation_state_count": len(preparation_paths),
        "path_hash_aggregate_sha256": aggregate,
        "families": family_reports,
        "unrelated_gst_files_are_out_of_scope": True,
    }
    return (
        [states_by_path[path] for path in paths],
        [states_by_path[path] for path in preparation_paths],
        report,
    )


def retained_ownership_scan(
    pool: tuple[int, ...],
    manifest_path: Path = DEFAULT_RETAINED_GST_MANIFEST,
) -> dict[str, object]:
    from scripts import build_korean_jp_probe as builder

    states, prep_states, source_report = retained_source_states(manifest_path)
    reserved: set[int] = set()
    sprite_used: set[int] = set()
    for state in states:
        reserved.update(reserved_table_tiles(state))
        sprite_used.update(sprite_referenced_tiles(state))
    preparation_used: set[int] = set()
    for state in prep_states:
        preparation_used.update(referenced_tiles(state))
    preparation_paths = {state.path for state in prep_states}
    non_preparation_used: set[int] = set()
    for state in states:
        if state.path not in preparation_paths:
            non_preparation_used.update(referenced_tiles(state))
    strictly_preparation_only = (
        set(builder.BYTE_UI_PREP_EXTRA_TILE_IDS)
        - set(builder.BYTE_UI_DYNAMIC_TILE_IDS)
    )
    variants = {
        tile: {
            state.vram[tile * TILE_BYTES : (tile + 1) * TILE_BYTES]
            for state in prep_states
        }
        for tile in pool
    }
    return {
        "retained_source_manifest": source_report,
        "retained_gst_count": len(states),
        "preparation_like_gst_count": len(prep_states),
        "current_preparation_referenced_pool_tiles": [
            f"0x{tile:04X}" for tile in sorted(set(pool) & preparation_used)
        ],
        "current_preparation_renderer_is_exercised": bool(
            set(pool) & preparation_used
        ),
        "pool_has_no_current_sat_reference": set(pool).isdisjoint(sprite_used),
        "strictly_preparation_only_tiles": [
            f"0x{tile:04X}" for tile in sorted(strictly_preparation_only)
        ],
        "strictly_preparation_only_tiles_are_absent_outside_preparation": (
            strictly_preparation_only.isdisjoint(non_preparation_used)
        ),
        "pool_is_outside_all_retained_vdp_tables": all(
            tile not in reserved for tile in pool
        ),
        "preparation_payload_variant_counts_before_assignment": {
            f"0x{tile:04X}": len(variants[tile]) for tile in pool
        },
    }


def build_report(
    historical_gst: Path,
    pre_gst: Path,
    post_gst: Path,
    retained_manifest: Path = DEFAULT_RETAINED_GST_MANIFEST,
) -> dict[str, object]:
    from scripts import build_korean_jp_probe as builder

    pool = tuple(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS)
    historical = load_gst(historical_gst)
    pre = load_gst(pre_gst)
    post = load_gst(post_gst)

    historical_scroll = historical.vram[
        historical.hscroll_base :
        historical.hscroll_base + HSCROLL_TABLE_BYTES
    ]
    pre_scroll = pre.vram[pre.hscroll_base : pre.hscroll_base + HSCROLL_TABLE_BYTES]
    post_scroll = post.vram[
        post.hscroll_base : post.hscroll_base + HSCROLL_TABLE_BYTES
    ]
    pool_payload_identical = all(
        pre.vram[tile * TILE_BYTES : (tile + 1) * TILE_BYTES]
        == post.vram[tile * TILE_BYTES : (tile + 1) * TILE_BYTES]
        for tile in pool
    )

    def capture_pairs(
        before_paths: tuple[Path, ...],
        after_paths: tuple[Path, ...],
    ) -> list[dict[str, object]]:
        pairs = []
        for before, after in zip(before_paths, after_paths):
            pairs.append(
                {
                    "before": str(before.relative_to(ROOT)),
                    "before_sha256": sha256(before),
                    "after": str(after.relative_to(ROOT)),
                    "after_sha256": sha256(after),
                    "byte_identical": before.read_bytes() == after.read_bytes(),
                }
            )
        return pairs

    normal_post = load_gst(DEFAULT_NORMAL_POST_GST)
    normal_post_scroll = normal_post.vram[
        normal_post.hscroll_base :
        normal_post.hscroll_base + HSCROLL_TABLE_BYTES
    ]
    hard_capture_pairs = capture_pairs(DEFAULT_PRE_CAPTURES, DEFAULT_POST_CAPTURES)
    normal_capture_pairs = capture_pairs(
        DEFAULT_NORMAL_PRE_CAPTURES,
        DEFAULT_NORMAL_POST_CAPTURES,
    )

    return {
        "schema_version": 3,
        "historical_collision": {
            "gst": str(historical_gst.relative_to(ROOT)),
            "gst_sha256": sha256(historical_gst),
            "vdp_register_11": f"0x{historical.registers[11]:02X}",
            "vdp_register_13": f"0x{historical.registers[13]:02X}",
            "hscroll_base": f"0x{historical.hscroll_base:04X}",
            "hscroll_end": f"0x{historical.hscroll_base + HSCROLL_TABLE_BYTES - 1:04X}",
            "historical_tiles_inside_hscroll": all(
                historical.hscroll_base
                <= tile * TILE_BYTES
                < historical.hscroll_base + HSCROLL_TABLE_BYTES
                for tile in HISTORICAL_HSCROLL_TILES
            ),
            "nonzero_hscroll_bytes": sum(bool(value) for value in historical_scroll),
            "nonzero_hscroll_ranges": nonzero_ranges(
                historical_scroll, historical.hscroll_base
            ),
        },
        "replacement_pool": {
            "tiles": [f"0x{tile:04X}" for tile in pool],
            "battle_map_tiles": [
                f"0x{tile:04X}"
                for tile in builder.BYTE_UI_DYNAMIC_TILE_IDS
            ],
            "preparation_only_tiles": [
                f"0x{tile:04X}"
                for tile in builder.BYTE_UI_PREP_EXTRA_TILE_IDS
            ],
            "battle_map_avoids_ordinary_mercenary_active_second_and_gray": (
                set(builder.BYTE_UI_DYNAMIC_TILE_IDS).isdisjoint(
                    set(range(0x0348, 0x0388))
                    | set(range(0x0448, 0x0488))
                    | set(range(0x03B0, 0x03F0))
                )
            ),
            "all_pattern_addresses_avoid_live_hscroll": all(
                not 0xF400 <= tile * TILE_BYTES < 0xF800 for tile in pool
            ),
            "stock_full_scroll_fill_restored": (
                builder.BYTE_UI_FULL_SCROLL_HSCROLL_FILL_ORIGINAL
                == bytes.fromhex("32 3C 00 B7")
            ),
            **retained_ownership_scan(pool, retained_manifest),
        },
        "scenario_9_shop_roundtrip": {
            "hard": {
                "pre_gst": str(pre_gst.relative_to(ROOT)),
                "pre_gst_sha256": sha256(pre_gst),
                "post_gst": str(post_gst.relative_to(ROOT)),
                "post_gst_sha256": sha256(post_gst),
                "vdp_register_11": f"0x{post.registers[11]:02X}",
                "vdp_register_13": f"0x{post.registers[13]:02X}",
                "hscroll_base": f"0x{post.hscroll_base:04X}",
                "pre_hscroll_nonzero_bytes": sum(
                    bool(value) for value in pre_scroll
                ),
                "post_hscroll_nonzero_bytes": sum(
                    bool(value) for value in post_scroll
                ),
                "pool_payloads_identical_before_after": pool_payload_identical,
                "capture_pairs": hard_capture_pairs,
            },
            "normal": {
                "post_gst": str(DEFAULT_NORMAL_POST_GST.relative_to(ROOT)),
                "post_gst_sha256": sha256(DEFAULT_NORMAL_POST_GST),
                "vdp_register_11": f"0x{normal_post.registers[11]:02X}",
                "vdp_register_13": f"0x{normal_post.registers[13]:02X}",
                "hscroll_base": f"0x{normal_post.hscroll_base:04X}",
                "post_hscroll_nonzero_bytes": sum(
                    bool(value) for value in normal_post_scroll
                ),
                "capture_pairs": normal_capture_pairs,
            },
        },
    }


def validate_report(report: dict[str, object]) -> None:
    historical = report["historical_collision"]
    replacement = report["replacement_pool"]
    runtime = report["scenario_9_shop_roundtrip"]
    hard_runtime = runtime["hard"]
    normal_runtime = runtime["normal"]
    checks = {
        "historical tiles are inside H-scroll": historical[
            "historical_tiles_inside_hscroll"
        ],
        "historical H-scroll contains glyph bytes": historical[
            "nonzero_hscroll_bytes"
        ] > 0,
        "replacement avoids live H-scroll addresses": replacement[
            "all_pattern_addresses_avoid_live_hscroll"
        ],
        "current preparation renderer exercises the replacement pool": replacement[
            "current_preparation_renderer_is_exercised"
        ],
        "replacement has no current SAT owner": replacement[
            "pool_has_no_current_sat_reference"
        ],
        "preparation-only cells stay absent from non-preparation surfaces": replacement[
            "strictly_preparation_only_tiles_are_absent_outside_preparation"
        ],
        "replacement is outside retained VDP tables": replacement[
            "pool_is_outside_all_retained_vdp_tables"
        ],
        "battle map avoids all ordinary mercenary frames": replacement[
            "battle_map_avoids_ordinary_mercenary_active_second_and_gray"
        ],
        # An unreferenced pattern is free regardless of stale bytes left in
        # VRAM by a prior scene. High-tail cells can legitimately have more
        # than one such payload while still having no Plane/Window/SAT owner.
        "hard pre-shop H-scroll is clean": hard_runtime[
            "pre_hscroll_nonzero_bytes"
        ] == 0,
        "hard post-shop H-scroll is clean": hard_runtime[
            "post_hscroll_nonzero_bytes"
        ] == 0,
        "normal post-shop H-scroll is clean": normal_runtime[
            "post_hscroll_nonzero_bytes"
        ] == 0,
        "replacement pool survives shop": hard_runtime[
            "pool_payloads_identical_before_after"
        ],
        "hard full-screen captures are exact": all(
            row["byte_identical"] for row in hard_runtime["capture_pairs"]
        ),
        "normal full-screen captures are exact": all(
            row["byte_identical"] for row in normal_runtime["capture_pairs"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("preparation VRAM ownership checks failed: " + ", ".join(failed))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode preparation GST VDP ownership and verify the replacement pool"
    )
    parser.add_argument("--historical-gst", type=Path, default=DEFAULT_HISTORICAL_GST)
    parser.add_argument("--pre-gst", type=Path, default=DEFAULT_PRE_GST)
    parser.add_argument("--post-gst", type=Path, default=DEFAULT_POST_GST)
    parser.add_argument(
        "--retained-manifest",
        type=Path,
        default=DEFAULT_RETAINED_GST_MANIFEST,
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.historical_gst,
        args.pre_gst,
        args.post_gst,
        args.retained_manifest,
    )
    if args.check:
        validate_report(report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
