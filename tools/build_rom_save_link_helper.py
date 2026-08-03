#!/usr/bin/env python3
"""Build the cross-platform ROM/save-link helper ZIP."""

from __future__ import annotations

import argparse
from pathlib import Path
import stat
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rom-save-link-helper"
DEFAULT_OUTPUT = (
    ROOT / "dist/Langrisser-II-ROM-Save-Link-Helper-v1.0.0.zip"
)
MEMBERS = (
    "index.html",
    "core.js",
    "app.js",
    "styles.css",
    "open_windows.bat",
    "open_linux.sh",
    "README_KO.txt",
)
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build(output: Path, *, force: bool = False) -> Path:
    if output.exists() and not force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for name in MEMBERS:
                path = SOURCE / name
                if not path.is_file():
                    raise FileNotFoundError(path)
                mode = 0o755 if name == "open_linux.sh" else 0o644
                info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | mode) << 16
                archive.writestr(info, path.read_bytes())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(build(args.output, force=args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
