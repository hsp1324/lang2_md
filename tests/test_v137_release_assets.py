from pathlib import Path
import re
import unittest

from tools import v138_release_assets as assets


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_WORKFLOW = ROOT / ".github/workflows/build-v1.3-patcher.yml"
PLATFORM_WORKFLOW = (
    ROOT / ".github/workflows/build-v1.3-patcher-platforms.yml"
)
DISTRIBUTION_DOC = ROOT / "docs/player_patch_distribution_v1.3.8.md"


class V138ReleaseAssetContractTests(unittest.TestCase):
    def test_candidate_has_exactly_five_unique_platform_assets(self):
        self.assertEqual(assets.RELEASE_TAG, "v1.3.8")
        self.assertEqual(len(assets.PATCHER_ASSET_FILENAMES), 5)
        self.assertEqual(len(set(assets.PATCHER_ASSET_FILENAMES)), 5)

    def test_workflows_have_published_release_trigger_and_write_permission(self):
        for path in (WINDOWS_WORKFLOW, PLATFORM_WORKFLOW):
            workflow = path.read_text(encoding="utf-8")
            with self.subTest(workflow=path.name):
                self.assertIn("release:\n    types: [published]", workflow)
                self.assertIn("permissions:\n  contents: write", workflow)
                self.assertIn("github.event.release.tag_name == 'v1.3.8'", workflow)
                self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
                self.assertIn("if: github.event_name == 'release'", workflow)
                self.assertIn("gh release upload", workflow)
                self.assertIn("--clobber", workflow)
                self.assertIn("--self-test", workflow)

    def test_release_uploads_are_the_five_constant_assets_only(self):
        windows = WINDOWS_WORKFLOW.read_text(encoding="utf-8")
        platforms = PLATFORM_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            f'"dist/{assets.WINDOWS_PATCHER_ASSET}" --clobber',
            windows,
        )
        archive_values = tuple(
            re.findall(r"^\s+archive: (\S+)$", platforms, flags=re.MULTILINE)
        )
        self.assertEqual(
            set(archive_values),
            set(assets.PATCHER_ASSET_FILENAMES[1:]),
        )
        self.assertIn('"dist/${{ matrix.archive }}" --clobber', platforms)
        for workflow in (windows, platforms):
            publish_blocks = re.findall(
                r"gh release upload.*?--clobber",
                workflow,
                flags=re.DOTALL,
            )
            self.assertTrue(publish_blocks)
            self.assertTrue(
                all("SHA256SUMS" not in block for block in publish_blocks)
            )

    def test_windows_workflow_requires_amd64_pe32_plus(self):
        workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pe.FILE_HEADER.Machine != 0x8664", workflow)
        self.assertIn("pe.OPTIONAL_HEADER.Magic != 0x020B", workflow)

    def test_distribution_draft_has_the_exact_five_asset_contract(self):
        document = DISTRIBUTION_DOC.read_text(encoding="utf-8")
        release_section = document.split(
            "v1.3.8 Release에는 다음 플랫폼 패처를 정확히 5개만 올립니다.",
            1,
        )[1]
        asset_block = release_section.split("```text", 1)[1].split("```", 1)[0]
        self.assertEqual(
            tuple(line for line in asset_block.splitlines() if line),
            assets.PATCHER_ASSET_FILENAMES,
        )
        self.assertIn("정확히 5개", document)
        self.assertIn("Release 자산으로 별도 업로드하지", document)
        self.assertIn(
            "Langrisser II (Korean Hard v1.3.8).md",
            document,
        )
        self.assertIn("상태: **v1.3.8 배포 준비 완료**", document)
        self.assertIn("BPS", document)

    def test_readme_downloads_follow_the_same_filename_contract(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(
            r"/releases/download/(v\d+\.\d+\.\d+)/"
            r"(Langrisser-II-Korean-Patcher-[^)]+)",
            readme,
        )
        self.assertEqual(len(links), 5)
        tags = {tag for tag, _ in links}
        self.assertEqual(len(tags), 1)
        public_tag = tags.pop()
        self.assertEqual(
            {filename for _, filename in links},
            set(assets.filenames_for_release(public_tag)),
        )


if __name__ == "__main__":
    unittest.main()
