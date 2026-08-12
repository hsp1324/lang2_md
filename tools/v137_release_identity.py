#!/usr/bin/env python3
"""Single update point for the exact finalized v1.3.7 ROM identities.

The three current hashes identify the reproducibly rebuilt fixed-raw-EXP and
pending-marker candidates used by the fresh final gate.  Superseded hashes
remain in ``INVALIDATED_RELEASE_SHA256`` so an already-generated stale plan is
rejected.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAPANESE_SOURCE_ROM_BYTES = 0x200000
JAPANESE_SOURCE_ROM_SHA256 = (
    "a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b"
)
RELEASE_ROM_PATHS = {
    "pure": ROOT / "roms/builds/Langrisser II (Korean Original v1.3.7).md",
    "normal": ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.7).md",
    "hard": (
        ROOT
        / "roms/builds/Langrisser II (Korean Hard v1.3.7).md"
    ),
}

_INVALIDATED_PRE_PENDING_MARKER_SHA256 = {
    "pure": "b948901816384cf349615bc80d5b35a19be1cb2358b24644112f591d7989c335",
    "normal": "9c38d6eb580eab35c522fea720809cf48e76fadec99389f44d740ecb233b8bd8",
    "hard": "d6c617aae43f42dc6531d7495e83da470f36d37063777c2c676258a965bd6e6b",
}

_INVALIDATED_PRE_COLD_LOAD_SCENARIO_FALLBACK_SHA256 = {
    "pure": "2794ae928902796dda01b1af43f59754afd7dbad3db771a28619cbfa3264dc9e",
    "normal": "124013e06999c0db13478a54123037c211a22f5d83e2030c031267c2bafd3dfc",
    "hard": "4047bac2d45d659ca9a0a7efb3c16d298d75ad68cdac88ed380af15c2c7c34ab",
}

_INVALIDATED_PRE_WARM_LOAD_CONTEXT_GATE_SHA256 = {
    "pure": "8505fa108c65ce6adfcabac12d68b0f759457917992364bf5558eddd64deeac6",
    "normal": "bc12b5400685a0bb9ee98cb6d1b170b2b395b87b5dea722d52e4db791592d53a",
    "hard": "c0b99a2b8da85b9e21042b50dce7da16dc7a586c3ff7c8706300f498ce2558eb",
}

# Final fixed-raw-EXP/pending-marker candidate, rebuilt twice from the same
# Japanese source with byte-identical outputs before this identity was frozen.
RELEASE_ROM_SHA256 = {
    "pure": "604d022080ae701a8b2ff0dd9f6906143e1483a74be5ac4ba9f8a2cffa051bff",
    "normal": "05f8ced0854b78b23eaf2c48b153d000fa56969cc5549a1d01df3dd86a19b32a",
    "hard": "1b5735c1b1b0620f8131c3291208f605d95a7e5293e63de36627b83f3a9001bd",
}
RELEASE_IDENTITY_FINALIZED = True
RELEASE_IDENTITY_GENERATION = "loren-lavender-followup-20260813"
INVALIDATED_RELEASE_SHA256 = frozenset(
    (*_INVALIDATED_PRE_PENDING_MARKER_SHA256.values(),
     *_INVALIDATED_PRE_COLD_LOAD_SCENARIO_FALLBACK_SHA256.values(),
     *_INVALIDATED_PRE_WARM_LOAD_CONTEXT_GATE_SHA256.values(),
     "2d475a96f5f5ee26352bef6c3c392a77aafa283a2c0f260a6d1cb8603b3610ac",
     "92e90c0e00df03c1c3264bc6ff7702c5356c2ba2b65d5f2281177066f329c7d8",
     "ca7750c207382023636acb37901242437861a8b83f4b39477c1405c8dd1ee6eb",
     "3ee7431b5a3d062ce739463e89cdffce9543d0383ba7ccacb29f514e38c32b55",
     "66b4bc9b04e06b7e18f7d7f341d59ad5cfab02e480b3ff0949d277ba04a6f5a9",
     "3f7de8fd1b4695c62e764fef5ed06bf4c96d1974f1296863c46f903ac21d69f5",
     "6646c1ce86e960ea33228f6ef41e7b1b3cd1b39f9fa8779a3172d6c75c65a878",
     "c10ef6a6487c7b6a49ce47cce1792e89521698818cc13ce7590c97794ced4580",
     "7d0c528c10d86367460792d06b95402d92557904ab62aea093ddda9d52081a4a")
)

# These generated/dated records must be refreshed from the same central values.
DERIVED_IDENTITY_FILES = (
    "patches/v1.3.7.json",
    "localization/hard_mode_build.json",
    "localization/hard_mode_update_releases.json",
    "docs/player_patch_distribution.md",
    "docs/release_notes_v1.3.7.md",
    "docs/v1.3.7_validation.md",
)


def require_final_release_identity(
    observed: dict[str, str] | None = None,
) -> None:
    if not RELEASE_IDENTITY_FINALIZED:
        raise ValueError(
            "v1.3.7 release identity is invalidated pending the marker-fix rebuild"
        )
    if set(RELEASE_ROM_SHA256.values()) & INVALIDATED_RELEASE_SHA256:
        raise ValueError("v1.3.7 release identity still contains invalidated SHA-256")
    if observed is not None and observed != RELEASE_ROM_SHA256:
        raise ValueError(
            "v1.3.7 observed release SHA-256 values differ from the central identity"
        )


def identity_snapshot() -> dict[str, object]:
    return {
        "generation": RELEASE_IDENTITY_GENERATION,
        "finalized": RELEASE_IDENTITY_FINALIZED,
        "sha256": dict(RELEASE_ROM_SHA256),
        "invalidated_sha256": sorted(INVALIDATED_RELEASE_SHA256),
        "derived_identity_files": list(DERIVED_IDENTITY_FILES),
    }
