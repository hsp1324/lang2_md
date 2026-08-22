from pathlib import Path
import re
import unittest

from tools import v140_release_assets as assets


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_WORKFLOW = ROOT / ".github/workflows/build-v1.4.0-patcher.yml"
PLATFORM_WORKFLOW = ROOT / ".github/workflows/build-v1.4.0-patcher-platforms.yml"
DISTRIBUTION_DOC = ROOT / "docs/player_patch_distribution_v1.4.0.md"


class V140ReleaseAssetContractTests(unittest.TestCase):
    def test_release_has_exactly_five_unique_platform_assets(self):
        self.assertEqual(assets.RELEASE_TAG, "v1.4.0")
        self.assertEqual(assets.RELEASE_TITLE, "v1.4.0")
        self.assertEqual(len(assets.PATCHER_ASSET_FILENAMES), 5)
        self.assertEqual(len(set(assets.PATCHER_ASSET_FILENAMES)), 5)

    def test_workflows_target_only_the_v140_release(self):
        for path in (WINDOWS_WORKFLOW, PLATFORM_WORKFLOW):
            workflow = path.read_text(encoding="utf-8")
            with self.subTest(workflow=path.name):
                self.assertIn("release:\n    types: [published]", workflow)
                self.assertIn("permissions:\n  contents: write", workflow)
                self.assertIn("github.event.release.tag_name == 'v1.4.0'", workflow)
                self.assertIn("gh release upload", workflow)
                self.assertIn('--title "v1.4.0"', workflow)
                self.assertIn("--clobber", workflow)
                self.assertIn("--self-test", workflow)

    def test_distribution_and_readme_use_the_v140_contract(self):
        document = DISTRIBUTION_DOC.read_text(encoding="utf-8")
        asset_block = document.split(
            "다음 플랫폼 패처를 정확히 5개만 올립니다.", 1
        )[1].split("```text", 1)[1].split("```", 1)[0]
        self.assertEqual(
            tuple(line for line in asset_block.splitlines() if line),
            assets.PATCHER_ASSET_FILENAMES,
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"/releases/download/(v\d+\.\d+\.\d+)/", readme)
        self.assertEqual(set(links), {"v1.4.0"})
        for phrase in (
            "1단계 LV10",
            "경험치량은 원작과 같습니다",
            "최신 New 클래스 디자인",
        ):
            self.assertIn(phrase, readme)
