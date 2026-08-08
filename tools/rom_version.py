#!/usr/bin/env python3
"""Read and validate per-edition ROM versions shown on the title screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "localization/rom_versions.json"
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TITLE_TEXT_MAX_CELLS = 28
ROM_HEADER_TITLE_MAX_BYTES = 48


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != 1:
        raise ValueError("unsupported ROM version registry schema")
    profiles = model.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("ROM version registry has no profiles")
    current = model.get("current_profile")
    if current not in profiles:
        raise ValueError("current ROM version profile does not exist")
    creator = model.get("creator")
    if not isinstance(creator, str) or not creator:
        raise ValueError("ROM version registry has no creator")
    try:
        creator.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("ROM version creator must be ASCII") from exc
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            raise ValueError(f"ROM version profile {name!r} is not an object")
        _validate_profile(name, profile, allow_pending=True)
    return model


def _validate_profile(
    name: str,
    profile: dict[str, Any],
    *,
    allow_pending: bool,
) -> None:
    translation_version = profile.get("translation_version")
    if (
        not isinstance(translation_version, str)
        or not VERSION_PATTERN.fullmatch(translation_version)
    ):
        raise ValueError(
            f"ROM version profile {name!r} needs a MAJOR.MINOR.PATCH "
            "translation version"
        )
    balance_version = profile.get("balance_version")
    status = profile.get("status")
    if status == "pending_balance_approval" and allow_pending:
        if profile.get("release_id") is not None or balance_version is not None:
            raise ValueError(f"pending profile {name!r} must not claim a release")
        return
    if status not in {"release_candidate", "released"}:
        raise ValueError(f"ROM version profile {name!r} has invalid status")
    release_id = profile.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise ValueError(f"ROM version profile {name!r} has no release ID")
    if name in {"pure", "normal"}:
        if balance_version is not None:
            raise ValueError(
                f"{name} ROM profile must not have a balance version"
            )
    elif (
        not isinstance(balance_version, str)
        or not VERSION_PATTERN.fullmatch(balance_version)
    ):
        raise ValueError(
            f"ROM version profile {name!r} needs a MAJOR.MINOR.PATCH "
            "balance version"
        )
    if profile.get("save_format") != "lang2-ko-sram-v1":
        raise ValueError(f"ROM version profile {name!r} changes the save format")
    text = _title_text(name, translation_version, balance_version)
    if len(text) > TITLE_TEXT_MAX_CELLS:
        raise ValueError(
            f"ROM version profile {name!r} title text exceeds "
            f"{TITLE_TEXT_MAX_CELLS} cells"
        )


def _title_text(
    name: str,
    translation_version: str,
    balance_version: str | None,
) -> str:
    if name in {"pure", "normal"}:
        return f"번역:{translation_version}"
    if balance_version is None:
        raise ValueError(f"ROM version profile {name!r} has no balance version")
    return f"번역/밸런스:{translation_version}/{balance_version}"


def _rom_filename(
    name: str,
    translation_version: str,
    balance_version: str | None,
) -> str:
    if name == "pure":
        return f"Langrisser II (Korean Original v{translation_version}).md"
    if name == "normal":
        return f"Langrisser II (Korean Normal v{translation_version}).md"
    if balance_version is None:
        raise ValueError(f"ROM version profile {name!r} has no balance version")
    if balance_version == translation_version:
        return f"Langrisser II (Korean Hard v{translation_version}).md"
    return (
        "Langrisser II (Korean Hard "
        f"T{translation_version} B{balance_version}).md"
    )


def _header_title(
    name: str,
    translation_version: str,
    balance_version: str | None,
    creator: str,
) -> str:
    text = "LANGRISSER II KOREAN"
    if name == "pure":
        text += " PURE"
    text += f" T{translation_version}"
    if name not in {"pure", "normal"}:
        if balance_version is None:
            raise ValueError(
                f"ROM version profile {name!r} has no balance version"
            )
        text += f" B{balance_version}"
    text += f" BY {creator.upper()}"
    if len(text.encode("ascii")) > ROM_HEADER_TITLE_MAX_BYTES:
        raise ValueError(
            f"ROM version profile {name!r} metadata exceeds "
            f"{ROM_HEADER_TITLE_MAX_BYTES} bytes"
        )
    return text


def get_profile(
    name: str | None = None,
    path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    registry = load_registry(path)
    profile_name = name or str(registry["current_profile"])
    profiles = registry["profiles"]
    if profile_name not in profiles:
        raise ValueError(f"unknown ROM version profile: {profile_name}")
    profile = dict(profiles[profile_name])
    _validate_profile(profile_name, profile, allow_pending=False)
    profile["profile"] = profile_name
    profile["creator"] = str(registry["creator"])
    profile["title_text"] = _title_text(
        profile_name,
        str(profile["translation_version"]),
        profile.get("balance_version"),
    )
    profile["rom_filename"] = _rom_filename(
        profile_name,
        str(profile["translation_version"]),
        profile.get("balance_version"),
    )
    profile["header_title"] = _header_title(
        profile_name,
        str(profile["translation_version"]),
        profile.get("balance_version"),
        str(registry["creator"]),
    )
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a validated Langrisser II ROM version profile"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--profile")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = get_profile(args.profile, args.registry)
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(
            f"{profile['release_id']} {profile['title_text']} "
            f"({profile['status']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
