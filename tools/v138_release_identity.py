#!/usr/bin/env python3
"""Central, immutable identity for the v1.3.8 crimson-Loren release."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAPANESE_SOURCE_ROM_BYTES = 0x200000
JAPANESE_SOURCE_ROM_SHA256 = (
    "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"
)
RELEASE_ROM_PATHS = {
    "pure": ROOT / "roms/builds/Langrisser II (Korean Original v1.3.8).md",
    "normal": ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.8).md",
    "hard": ROOT / "roms/builds/Langrisser II (Korean Hard v1.3.8).md",
}
RELEASE_ROM_SHA256 = {
    "pure": "e25a8c19e3116c1dbdcc726eecd099db3186349869df4cc6a601c486a207aaf3",
    "normal": "104231bcc391178454dadb4d7609a761c55a550266e271267ced3a696685c55c",
    "hard": "eebc790c6068832708c2f1d13de5bd009066e1d49f8692fd3fe9272b19974f9c",
}
RELEASE_IDENTITY_FINALIZED = True
RELEASE_IDENTITY_GENERATION = "loren-crimson-gradient-20260813"
INVALIDATED_RELEASE_SHA256 = frozenset()

# These records carry the current v1.3.8 identity. v1.3.7 records remain
# historical and continue to describe the earlier lavender package exactly.
DERIVED_IDENTITY_FILES = (
    "patches/v1.3.8.json",
    "localization/hard_mode_build.json",
    "localization/hard_mode_update_releases.json",
    "docs/player_patch_distribution_v1.3.8.md",
    "docs/release_notes_v1.3.8.md",
    "docs/v1.3.8_validation.md",
)


def require_final_release_identity(
    observed: dict[str, str] | None = None,
) -> None:
    if not RELEASE_IDENTITY_FINALIZED:
        raise ValueError("v1.3.8 release identity is not finalized")
    if set(RELEASE_ROM_SHA256.values()) & INVALIDATED_RELEASE_SHA256:
        raise ValueError("v1.3.8 release identity contains invalidated SHA-256")
    if observed is not None and observed != RELEASE_ROM_SHA256:
        raise ValueError(
            "v1.3.8 observed release SHA-256 values differ from the central identity"
        )


def identity_snapshot() -> dict[str, object]:
    return {
        "generation": RELEASE_IDENTITY_GENERATION,
        "finalized": RELEASE_IDENTITY_FINALIZED,
        "sha256": dict(RELEASE_ROM_SHA256),
        "invalidated_sha256": sorted(INVALIDATED_RELEASE_SHA256),
        "derived_identity_files": list(DERIVED_IDENTITY_FILES),
    }
