import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from patcher import langrisser_ii_korean_patcher as patcher
from tools.build_v132_release_patches import (
    SOURCE_PATH,
    TARGETS,
    build,
)


ROOT = Path(__file__).resolve().parents[1]


class V133ReleasePatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_file():
            raise unittest.SkipTest("local Japanese verification ROM is absent")

    def test_committed_bps_assets_are_reproducible(self):
        manifest = build(check=True)
        self.assertEqual(manifest["release"], "v1.3.3")
        self.assertEqual(
            {record["id"] for record in manifest["targets"]},
            {"pure", "normal", "hard"},
        )

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
                    "Langrisser II (Korean Original v1.3.3).md",
                    "Langrisser II (Korean Normal v1.3.3).md",
                    "Langrisser II (Korean Hard v1.3.3).md",
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


if __name__ == "__main__":
    unittest.main()
