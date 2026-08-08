import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "editor/static/app.js"
HTML_PATH = ROOT / "editor/static/index.html"


class EditorClassRouteUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = APP_PATH.read_text(encoding="utf-8")
        start = cls.script.index("function replaceNextClassInRoute(")
        end = cls.script.index(
            "\nfunction changeTransitionCurrentClass(",
            start,
        )
        cls.helper = cls.script[start:end]

    def run_helper(self, commander: dict, slot: int, class_id: int) -> dict:
        if shutil.which("node") is None:
            self.skipTest("Node.js is required for the editor JavaScript test")
        program = f"""
{self.helper}
const commander = {json.dumps(commander)};
replaceNextClassInRoute(commander, commander.transitions[0], {slot}, {class_id});
process.stdout.write(JSON.stringify(commander));
"""
        result = subprocess.run(
            ["node", "-e", program],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_replacing_next_class_keeps_its_existing_outgoing_choices(self) -> None:
        commander = {
            "starting_class_id": 1,
            "transitions": [
                {"current_class": 1, "candidates": [4, 5, 10]},
                {"current_class": 4, "candidates": [18, 11, 12]},
                {"current_class": 5, "candidates": [11, 12, 13]},
            ],
        }
        changed = self.run_helper(commander, 0, 42)
        self.assertEqual(changed["transitions"][0]["candidates"], [42, 5, 10])
        self.assertEqual(changed["transitions"][1]["current_class"], 42)
        self.assertEqual(changed["transitions"][1]["candidates"], [18, 11, 12])

    def test_existing_class_is_swapped_instead_of_duplicated(self) -> None:
        commander = {
            "starting_class_id": 1,
            "transitions": [
                {"current_class": 1, "candidates": [4, 5, 10]},
                {"current_class": 4, "candidates": [18, 11, 12]},
                {"current_class": 5, "candidates": [11, 12, 13]},
            ],
        }
        changed = self.run_helper(commander, 0, 5)
        self.assertEqual(changed["transitions"][0]["candidates"], [5, 4, 10])
        self.assertEqual(changed["transitions"][1]["current_class"], 5)
        self.assertEqual(changed["transitions"][1]["candidates"], [18, 11, 12])
        self.assertEqual(changed["transitions"][2]["current_class"], 4)
        self.assertEqual(changed["transitions"][2]["candidates"], [11, 12, 13])

    def test_picker_uses_route_replacement_helper(self) -> None:
        self.assertIn(
            "replaceNextClassInRoute(\n          commander,\n          transition,",
            self.script,
        )

    def test_original_and_new_design_share_class_change_tab(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        self.assertNotIn('data-tab="aiClasses"', html)
        self.assertIn('data-class-mode="original"', html)
        self.assertIn('data-class-mode="new"', html)
        self.assertIn('id="originalClassesMode"', html)
        self.assertIn('id="newClassesMode"', html)


if __name__ == "__main__":
    unittest.main()
