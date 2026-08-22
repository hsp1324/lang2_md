from pathlib import Path
import re
import unittest

from tools import v139_release_assets as assets


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_WORKFLOW = ROOT / ".github/workflows/build-v1.3.9-patcher.yml"
PLATFORM_WORKFLOW = ROOT / ".github/workflows/build-v1.3.9-patcher-platforms.yml"
DISTRIBUTION_DOC = ROOT / "docs/player_patch_distribution_v1.3.9.md"


class V139ReleaseAssetContractTests(unittest.TestCase):
    def test_release_has_exactly_five_unique_platform_assets(self):
        self.assertEqual(assets.RELEASE_TAG, "v1.3.9")
        self.assertEqual(assets.RELEASE_TITLE, "v1.3.9")
        self.assertEqual(len(assets.PATCHER_ASSET_FILENAMES), 5)
        self.assertEqual(len(set(assets.PATCHER_ASSET_FILENAMES)), 5)

    def test_workflows_target_only_the_v139_published_release(self):
        for path in (WINDOWS_WORKFLOW, PLATFORM_WORKFLOW):
            workflow = path.read_text(encoding="utf-8")
            with self.subTest(workflow=path.name):
                self.assertIn("release:\n    types: [published]", workflow)
                self.assertIn("permissions:\n  contents: write", workflow)
                self.assertIn("github.event.release.tag_name == 'v1.3.9'", workflow)
                self.assertIn("gh release upload", workflow)
                self.assertIn(
                    'gh release edit "${{ github.event.release.tag_name }}"',
                    workflow,
                )
                self.assertIn('--title "v1.3.9"', workflow)
                self.assertIn("--clobber", workflow)
                self.assertIn("--self-test", workflow)

    def test_distribution_and_readme_keep_a_non_404_contract(self):
        document = DISTRIBUTION_DOC.read_text(encoding="utf-8")
        release_section = document.split(
            "v1.3.9 Release에는 다음 플랫폼 패처를 정확히 5개만 올립니다.",
            1,
        )[1]
        asset_block = release_section.split("```text", 1)[1].split("```", 1)[0]
        self.assertEqual(
            tuple(line for line in asset_block.splitlines() if line),
            assets.PATCHER_ASSET_FILENAMES,
        )
        self.assertIn("상태: **v1.3.9 공개 배포 완료**", document)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"/releases/download/(v\d+\.\d+\.\d+)/", readme)
        self.assertEqual(set(links), {"v1.3.9"})
        self.assertNotIn("아직 공개하지 않았으므로", readme)
