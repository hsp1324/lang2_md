import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile
import zlib

from tools.archive_rom_release import archive_current_release
from tools.build_rom_update_package import SourceRom, build_package
from tools import rom_update


ROOT = Path(__file__).resolve().parents[1]
RELEASE_REGISTRY = ROOT / "localization/rom_update_releases.json"
PRODUCTION_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


def make_md_rom(seed: int, edits: dict[int, int] | None = None) -> bytes:
    size = 0x2000
    data = bytearray((index * 17 + seed) & 0xFF for index in range(size))
    data[0x100:0x110] = b"SEGA MEGA DRIVE "
    data[0x1A4:0x1A8] = (size - 1).to_bytes(4, "big")
    data[0x1B0:0x1BC] = bytes.fromhex(
        "52 41 F8 20 00 40 00 01 00 40 3F FF"
    )
    for offset, value in (edits or {}).items():
        data[offset] = value
    checksum = rom_update.md_checksum(data)
    data[0x18E:0x190] = checksum.to_bytes(2, "big")
    return bytes(data)


def make_manual_bps(
    source: bytes,
    target: bytes,
    commands: bytes,
) -> bytes:
    patch = bytearray(rom_update.BPS_MAGIC)
    patch.extend(rom_update._encode_bps_number(len(source)))
    patch.extend(rom_update._encode_bps_number(len(target)))
    patch.extend(rom_update._encode_bps_number(0))
    patch.extend(commands)
    patch.extend((zlib.crc32(source) & 0xFFFFFFFF).to_bytes(4, "little"))
    patch.extend((zlib.crc32(target) & 0xFFFFFFFF).to_bytes(4, "little"))
    patch.extend((zlib.crc32(patch) & 0xFFFFFFFF).to_bytes(4, "little"))
    return bytes(patch)


class BpsTests(unittest.TestCase):
    def test_round_trip_equal_size_and_length_change(self):
        pairs = [
            (b"", b""),
            (b"same bytes", b"same bytes"),
            (b"abcdefghij", b"abcXefghYj"),
            (b"short", b"a much longer target"),
            (bytes(range(128)), bytes(range(64))),
        ]
        for source, target in pairs:
            with self.subTest(source=source, target=target):
                patch = rom_update.bps_create(
                    source, target, metadata=b'{"test":true}'
                )
                self.assertEqual(
                    rom_update.bps_apply(patch, source), target
                )

    def test_rejects_wrong_source_and_corrupt_patch(self):
        source = b"source payload"
        patch = rom_update.bps_create(source, b"target payload")
        with self.assertRaisesRegex(
            rom_update.UpdateError, "source checksum mismatch"
        ):
            rom_update.bps_apply(patch, b"wrong payload!")

        damaged = bytearray(patch)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(
            rom_update.UpdateError, "patch checksum mismatch"
        ):
            rom_update.bps_apply(bytes(damaged), source)

    def test_applies_standard_sourcecopy_and_targetcopy_actions(self):
        source = b"abc"
        source_copy_commands = bytearray()
        source_copy_commands.extend(
            rom_update._encode_bps_number(((1 - 1) << 2) | 2)
        )
        source_copy_commands.extend(rom_update._encode_bps_number(4))
        source_copy_commands.extend(
            rom_update._encode_bps_number(((2 - 1) << 2) | 2)
        )
        source_copy_commands.extend(rom_update._encode_bps_number(7))
        source_copy_patch = make_manual_bps(
            source, b"cab", bytes(source_copy_commands)
        )
        self.assertEqual(
            rom_update.bps_apply(source_copy_patch, source), b"cab"
        )

        target_copy_commands = bytearray()
        target_copy_commands.extend(
            rom_update._encode_bps_number(((3 - 1) << 2) | 0)
        )
        target_copy_commands.extend(
            rom_update._encode_bps_number(((3 - 1) << 2) | 3)
        )
        target_copy_commands.extend(rom_update._encode_bps_number(0))
        target_copy_patch = make_manual_bps(
            source, b"abcabc", bytes(target_copy_commands)
        )
        self.assertEqual(
            rom_update.bps_apply(target_copy_patch, source), b"abcabc"
        )


class RomUpdatePackageTests(unittest.TestCase):
    def build_fixture(
        self, directory: Path
    ) -> tuple[Path, Path, bytes, bytes, dict[str, object]]:
        source = make_md_rom(3)
        target = make_md_rom(
            3,
            {
                0x320: 0x7A,
                0x321: 0x55,
                0x1200: 0xA5,
            },
        )
        source_path = directory / "old-release.md"
        target_path = directory / "new-release.md"
        package_path = directory / "ko-update.zip"
        source_path.write_bytes(source)
        target_path.write_bytes(target)
        manifest = build_package(
            target_path=target_path,
            target_release="ko-new",
            sources=[SourceRom("ko-old", source_path)],
            output_path=package_path,
        )
        return package_path, source_path, source, target, manifest

    def test_package_has_patch_and_tools_but_no_rom(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            package, _, _, _, manifest = self.build_fixture(directory)
            with zipfile.ZipFile(package) as archive:
                names = set(archive.namelist())
                self.assertIn("update.json", names)
                self.assertIn("apply_update.py", names)
                self.assertIn("apply_update.bat", names)
                self.assertIn("apply_update.sh", names)
                self.assertIn("README_KO.txt", names)
                self.assertNotIn("old-release.md", names)
                self.assertNotIn("new-release.md", names)
                patch_name = manifest["patches"][0]["patch_file"]
                self.assertIn(patch_name, names)

    def test_in_place_update_preserves_filename_and_all_save_files(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            package, source_path, source, target, _ = self.build_fixture(
                directory
            )
            rom_path = directory / "Langrisser II (Korean).md"
            source_path.replace(rom_path)
            save_payloads = {
                "Langrisser II (Korean).srm": b"SRAM" * 2048,
                "Langrisser II (Korean).sav": b"SAVE",
                "Langrisser II (Korean).state": b"STATE0",
                "Langrisser II (Korean).state7": b"STATE7",
                "Langrisser II (Korean).gst": b"BLASTEM",
            }
            for name, payload in save_payloads.items():
                (directory / name).write_bytes(payload)
            before = {
                name: hashlib.sha256(
                    (directory / name).read_bytes()
                ).hexdigest()
                for name in save_payloads
            }

            result = rom_update.apply_update(package, rom_path)

            self.assertEqual(result.status, "updated")
            self.assertEqual(result.rom_path.name, "Langrisser II (Korean).md")
            self.assertEqual(rom_path.read_bytes(), target)
            self.assertIsNotNone(result.backup_path)
            self.assertEqual(result.backup_path.read_bytes(), source)
            self.assertEqual(
                before,
                {
                    name: hashlib.sha256(
                        (directory / name).read_bytes()
                    ).hexdigest()
                    for name in save_payloads
                },
            )

    def test_dry_run_and_unsupported_rom_never_write(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            package, source_path, source, _, _ = self.build_fixture(
                directory
            )
            dry_result = rom_update.apply_update(
                package, source_path, dry_run=True
            )
            self.assertEqual(dry_result.status, "verified")
            self.assertEqual(source_path.read_bytes(), source)
            self.assertEqual(list(directory.glob("*.bak")), [])

            unsupported = directory / "unsupported.md"
            unsupported_payload = make_md_rom(9)
            unsupported.write_bytes(unsupported_payload)
            with self.assertRaisesRegex(
                rom_update.UpdateError, "unsupported or modified ROM"
            ):
                rom_update.apply_update(package, unsupported)
            self.assertEqual(
                unsupported.read_bytes(), unsupported_payload
            )
            self.assertEqual(list(directory.glob("*.bak")), [])

    def test_corrupt_patch_is_rejected_before_rom_or_save_changes(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            package, source_path, source, _, manifest = self.build_fixture(
                directory
            )
            extracted = directory / "package"
            with zipfile.ZipFile(package) as archive:
                archive.extractall(extracted)
            patch_path = extracted / manifest["patches"][0]["patch_file"]
            damaged = bytearray(patch_path.read_bytes())
            damaged[10] ^= 1
            patch_path.write_bytes(damaged)
            save_path = directory / "old-release.srm"
            save_path.write_bytes(b"persistent save")

            with self.assertRaisesRegex(
                rom_update.UpdateError, "patch SHA-256 mismatch"
            ):
                rom_update.apply_update(extracted, source_path)
            self.assertEqual(source_path.read_bytes(), source)
            self.assertEqual(save_path.read_bytes(), b"persistent save")
            self.assertEqual(list(directory.glob("*.bak")), [])

    def test_already_current_is_idempotent(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            package, source_path, _, target, _ = self.build_fixture(
                directory
            )
            source_path.write_bytes(target)
            result = rom_update.apply_update(package, source_path)
            self.assertEqual(result.status, "already_current")
            self.assertIsNone(result.backup_path)
            self.assertEqual(source_path.read_bytes(), target)

    def test_builder_rejects_changed_sram_layout(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            source_path = directory / "source.md"
            target_path = directory / "target.md"
            source_path.write_bytes(make_md_rom(1))
            changed = bytearray(make_md_rom(1, {0x300: 0x44}))
            changed[0x1B8] ^= 1
            changed[0x18E:0x190] = rom_update.md_checksum(
                changed
            ).to_bytes(2, "big")
            target_path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "SRAM layout differs"):
                build_package(
                    target_path=target_path,
                    target_release="target",
                    sources=[SourceRom("source", source_path)],
                    output_path=directory / "update.zip",
                )


class ReleaseRegistryTests(unittest.TestCase):
    def test_current_release_registry_matches_production_rom(self):
        registry = json.loads(
            RELEASE_REGISTRY.read_text(encoding="utf-8")
        )
        self.assertEqual(registry["current_release"], "ko-99fd")
        record = next(
            row
            for row in registry["releases"]
            if row["release_id"] == registry["current_release"]
        )
        payload = PRODUCTION_ROM.read_bytes()
        self.assertEqual(record["size"], len(payload))
        self.assertEqual(record["sha256"], rom_update.sha256_bytes(payload))
        self.assertEqual(
            record["md_checksum"],
            f"{rom_update.md_header_checksum(payload):04X}",
        )
        self.assertEqual(
            record["sram_descriptor"],
            rom_update.md_sram_descriptor(payload).hex().upper(),
        )
        self.assertEqual(
            record["save_format"], rom_update.DEFAULT_SAVE_FORMAT
        )

    def test_archive_current_release_is_verified_and_idempotent(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            builds = root / "roms/builds"
            builds.mkdir(parents=True)
            payload = make_md_rom(12)
            rom_path = builds / "Langrisser II (Korean).md"
            rom_path.write_bytes(payload)
            registry_path = root / "registry.json"
            record = {
                "release_id": "ko-test",
                "rom_path": "roms/builds/Langrisser II (Korean).md",
                "size": len(payload),
                "md_checksum": (
                    f"{rom_update.md_header_checksum(payload):04X}"
                ),
                "sha256": rom_update.sha256_bytes(payload),
                "sram_descriptor": (
                    rom_update.md_sram_descriptor(payload).hex().upper()
                ),
                "save_format": rom_update.DEFAULT_SAVE_FORMAT,
            }
            registry_path.write_text(
                json.dumps(
                    {
                        "current_release": "ko-test",
                        "releases": [record],
                    }
                ),
                encoding="utf-8",
            )
            archive_dir = root / "roms/releases"
            first = archive_current_release(
                registry_path=registry_path,
                root=root,
                archive_dir=archive_dir,
            )
            second = archive_current_release(
                registry_path=registry_path,
                root=root,
                archive_dir=archive_dir,
            )
            self.assertEqual(first, second)
            self.assertEqual(first.read_bytes(), payload)
            self.assertEqual(len(list(archive_dir.glob("*.md"))), 1)

    def test_archive_rejects_rom_not_matching_registry(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            builds = root / "roms/builds"
            builds.mkdir(parents=True)
            payload = make_md_rom(13)
            rom_path = builds / "Langrisser II (Korean).md"
            rom_path.write_bytes(payload)
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "current_release": "ko-test",
                        "releases": [
                            {
                                "release_id": "ko-test",
                                "rom_path": (
                                    "roms/builds/"
                                    "Langrisser II (Korean).md"
                                ),
                                "size": len(payload),
                                "md_checksum": (
                                    f"{rom_update.md_header_checksum(payload):04X}"
                                ),
                                "sha256": "0" * 64,
                                "sram_descriptor": (
                                    rom_update.md_sram_descriptor(
                                        payload
                                    ).hex().upper()
                                ),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError, "does not match registry"
            ):
                archive_current_release(
                    registry_path=registry_path,
                    root=root,
                    archive_dir=root / "roms/releases",
                )
            self.assertFalse((root / "roms/releases").exists())


if __name__ == "__main__":
    unittest.main()
