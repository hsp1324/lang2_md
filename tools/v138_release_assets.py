#!/usr/bin/env python3
"""Single filename contract for the five v1.3.8 platform patchers."""

from __future__ import annotations


RELEASE_TAG = "v1.3.8"
WINDOWS_PATCHER_ASSET = "Langrisser-II-Korean-Patcher-v1.3.8.exe"
LINUX_PATCHER_ASSETS = {
    "x86_64": "Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64.tar.gz",
    "arm64": "Langrisser-II-Korean-Patcher-v1.3.8-linux-arm64.tar.gz",
}
MACOS_PATCHER_ASSETS = {
    "arm64": "Langrisser-II-Korean-Patcher-v1.3.8-macos-arm64.app.zip",
    "x86_64": "Langrisser-II-Korean-Patcher-v1.3.8-macos-x86_64.app.zip",
}
PATCHER_ASSET_FILENAMES = (
    WINDOWS_PATCHER_ASSET,
    LINUX_PATCHER_ASSETS["x86_64"],
    LINUX_PATCHER_ASSETS["arm64"],
    MACOS_PATCHER_ASSETS["arm64"],
    MACOS_PATCHER_ASSETS["x86_64"],
)


def filenames_for_release(release_tag: str) -> tuple[str, ...]:
    """Apply the stable platform filename contract to another release tag."""
    if not release_tag.startswith("v") or "/" in release_tag:
        raise ValueError(f"unsafe release tag: {release_tag!r}")
    return tuple(
        filename.replace(RELEASE_TAG, release_tag)
        for filename in PATCHER_ASSET_FILENAMES
    )
