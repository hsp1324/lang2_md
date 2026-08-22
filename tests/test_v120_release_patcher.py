import hashlib
import io
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
import zipfile

from patcher import langrisser_ii_korean_patcher as patcher
from tools.build_v142_release_patches import (
    SOURCE_PATH,
    TARGETS,
    build,
)


ROOT = Path(__file__).resolve().parents[1]


class CurrentReleasePatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")

    def test_committed_bps_assets_are_reproducible(self):
        manifest = build(check=True)
        self.assertEqual(manifest["release"], "v1.4.2")
        self.assertEqual(
            {record["id"] for record in manifest["targets"]},
            {"pure", "normal", "hard"},
        )

    def test_embedded_self_test_hashes_and_applies_every_bps(self):
        structural = patcher.verify_embedded_assets()
        self.assertTrue(structural["embedded_manifest_verified"])
        self.assertTrue(structural["all_patches_hashed"])
        self.assertFalse(structural["all_patches_applied"])
        applied = patcher.verify_embedded_assets(SOURCE_PATH.read_bytes())
        self.assertTrue(applied["all_patches_applied"])
        self.assertEqual(len(applied["targets"]), 3)
        self.assertTrue(
            all(row["application_verified"] for row in applied["targets"])
        )

    def test_embedded_self_test_rejects_a_corrupted_packaged_patch(self):
        with TemporaryDirectory() as temporary:
            asset_dir = Path(temporary)
            manifest = patcher.load_release_manifest()
            shutil.copy2(
                ROOT / "patches" / patcher.MANIFEST_FILENAME,
                asset_dir / patcher.MANIFEST_FILENAME,
            )
            for row in manifest["targets"]:
                name = str(row["patch_filename"])
                shutil.copy2(ROOT / "patches" / name, asset_dir / name)
            corrupt = asset_dir / str(manifest["targets"][0]["patch_filename"])
            payload = bytearray(corrupt.read_bytes())
            payload[len(payload) // 2] ^= 0x01
            corrupt.write_bytes(payload)
            with (
                mock.patch.object(patcher, "_asset_dir", return_value=asset_dir),
                self.assertRaisesRegex(patcher.UpdateError, "내장 패치 해시"),
            ):
                patcher.verify_embedded_assets()

    def test_patcher_builds_all_three_verified_roms_without_source_overwrite(self):
        source_before = hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
        with TemporaryDirectory() as temp:
            output_dir = Path(temp)
            results = patcher.apply_release(
                SOURCE_PATH,
                output_dir=output_dir,
            )
            self.assertEqual(
                {result.target_id for result in results},
                {"pure", "normal", "hard"},
            )
            self.assertEqual(
                {result.output_path.name for result in results},
                {
                    "Langrisser II (Korean Original v1.4.2).md",
                    "Langrisser II (Korean Normal v1.4.2).md",
                    "Langrisser II (Korean Hard v1.4.2).md",
                },
            )
            for spec in TARGETS:
                output = output_dir / str(spec["output_filename"])
                self.assertEqual(output.stat().st_size, 4_194_304)
                self.assertEqual(
                    hashlib.sha256(output.read_bytes()).hexdigest(),
                    hashlib.sha256(Path(spec["rom_path"]).read_bytes()).hexdigest(),
                )
            repeated = patcher.apply_release(
                SOURCE_PATH,
                output_dir=output_dir,
            )
            self.assertTrue(
                all(result.status == "already_current" for result in repeated)
            )
        self.assertEqual(
            hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(), source_before
        )

    def test_zip_source_and_existing_srm_work_together(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            archive_path = directory / "Langrisser II (Japan).zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "Langrisser II (Japan).md", SOURCE_PATH.read_bytes()
                )
            source = patcher.read_source_rom(archive_path)
            self.assertIn("Langrisser II (Japan).md", source.display_name)

            save_path = directory / "old-hard.srm"
            save_payload = bytes(range(256)) * 256
            save_path.write_bytes(save_payload)
            results = patcher.apply_release(archive_path)
            hard = next(
                result for result in results if result.target_id == "hard"
            )
            from tools.rom_update import migrate_save

            migrated = migrate_save(save_path, hard.output_path)
            self.assertEqual(migrated.destination_path.read_bytes(), save_payload)
            self.assertEqual(save_path.read_bytes(), save_payload)

    def test_wrong_rom_and_modified_existing_output_are_rejected(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            wrong_rom = directory / "wrong.md"
            wrong_rom.write_bytes(b"not a supported ROM")
            with self.assertRaisesRegex(
                patcher.UpdateError, "지원하는 일본판 ROM이 아닙니다"
            ):
                patcher.read_source_rom(wrong_rom)

            output_name = str(TARGETS[0]["output_filename"])
            (directory / output_name).write_bytes(b"keep this file")
            with self.assertRaisesRegex(
                patcher.UpdateError, "다른 내용의 결과 ROM"
            ):
                patcher.apply_release(SOURCE_PATH, output_dir=directory)
            self.assertEqual(
                (directory / output_name).read_bytes(), b"keep this file"
            )

    def test_source_output_collision_is_rejected_before_any_write(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / str(TARGETS[0]["output_filename"])
            source.write_bytes(SOURCE_PATH.read_bytes())
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaisesRegex(patcher.UpdateError, "원본 ROM과 결과 ROM"):
                patcher.apply_release(source, output_dir=directory)
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), source_hash
            )
            for target in TARGETS[1:]:
                self.assertFalse(
                    (directory / str(target["output_filename"])).exists()
                )

    def test_three_output_commit_rolls_back_create_and_replace_together(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            pure = directory / str(TARGETS[0]["output_filename"])
            normal = directory / str(TARGETS[1]["output_filename"])
            hard = directory / str(TARGETS[2]["output_filename"])
            original = b"preexisting normal output"
            normal.write_bytes(original)
            real_replace = patcher.os.replace
            injected = False

            def flaky_replace(source, destination):
                nonlocal injected
                source_path = Path(source)
                destination_path = Path(destination)
                if (
                    not injected
                    and source_path.suffix == ".tmp"
                    and destination_path == normal
                ):
                    injected = True
                    raise OSError("injected second-output commit failure")
                return real_replace(source, destination)

            with (
                mock.patch.object(
                    patcher.os,
                    "replace",
                    side_effect=flaky_replace,
                ),
                self.assertRaisesRegex(patcher.UpdateError, "모두 되돌렸습니다"),
            ):
                patcher.apply_release(
                    SOURCE_PATH,
                    output_dir=directory,
                    confirm_overwrite=lambda _path: True,
                )

            self.assertTrue(injected)
            self.assertFalse(pure.exists())
            self.assertEqual(normal.read_bytes(), original)
            self.assertFalse(hard.exists())
            self.assertEqual(list(directory.glob("*.bak")), [])
            self.assertEqual(list(directory.glob(".*.tmp")), [])

    def test_frozen_macos_defaults_next_to_app_bundle(self):
        executable = Path(
            "/Users/player/Downloads/Langrisser II Korean Patcher v1.4.2.app/"
            "Contents/MacOS/Langrisser II Korean Patcher v1.4.2"
        )
        with (
            mock.patch.object(patcher.sys, "frozen", True, create=True),
            mock.patch.object(patcher.sys, "executable", str(executable)),
            mock.patch.object(patcher.sys, "platform", "darwin"),
        ):
            self.assertEqual(
                patcher._application_dir(),
                Path("/Users/player/Downloads"),
            )

    def test_self_test_cli_does_not_launch_gui(self):
        with mock.patch.object(patcher, "run_gui") as gui:
            self.assertEqual(patcher.main(["--self-test"]), 0)
        gui.assert_not_called()

    def test_self_test_reconfigures_legacy_windows_console_to_utf8(self):
        stdout_bytes = io.BytesIO()
        stderr_bytes = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_bytes, encoding="cp1252")
        stderr = io.TextIOWrapper(stderr_bytes, encoding="cp1252")
        with (
            mock.patch.object(patcher.sys, "stdout", stdout),
            mock.patch.object(patcher.sys, "stderr", stderr),
        ):
            self.assertEqual(patcher.main(["--self-test"]), 0)
            stdout.flush()
            self.assertEqual(stdout.encoding.lower(), "utf-8")
            self.assertIn("self-test 통과", stdout_bytes.getvalue().decode("utf-8"))
        stdout.detach()
        stderr.detach()


if __name__ == "__main__":
    unittest.main()
