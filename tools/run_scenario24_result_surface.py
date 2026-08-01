#!/usr/bin/env python3
"""Capture current Scenario 24 result and save surfaces from a fresh entry."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario24_clear_probe_rom as probe_builder
from tools import run_scenario23_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s24_result"


def runtime_clear_state(path: Path, before_path: Path) -> dict[str, object]:
    previous = shared.probe_builder
    shared.probe_builder = probe_builder
    try:
        return shared.runtime_clear_state(path, before_path)
    finally:
        shared.probe_builder = previous


def main() -> int:
    previous_builder = shared.probe_builder
    previous_output_root = shared.DEFAULT_OUTPUT_ROOT
    shared.probe_builder = probe_builder
    shared.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    try:
        return shared.main()
    finally:
        shared.probe_builder = previous_builder
        shared.DEFAULT_OUTPUT_ROOT = previous_output_root


if __name__ == "__main__":
    raise SystemExit(main())
