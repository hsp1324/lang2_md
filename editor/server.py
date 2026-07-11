#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.scenario_data import SCENARIO_COUNT, patch_scenario, read_scenario


STATIC = Path(__file__).resolve().parent / "static"
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
ROM_CHOICES = {
    "korean": ROOT / "roms/builds/Langrisser II (Korean JP Probe).md",
    "japanese": REFERENCE_ROM,
}
OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Korean Scenario Edit).md"


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
        if self.path != "/api/build":
            return self.send_json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            rom_key = request.get("rom", "korean")
            source = ROM_CHOICES[rom_key]
            data = bytearray(source.read_bytes())
            checksum = patch_scenario(data, int(request["number"]), request["records"])
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
    parser = argparse.ArgumentParser(description="Langrisser II MD scenario editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Scenario editor: http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
