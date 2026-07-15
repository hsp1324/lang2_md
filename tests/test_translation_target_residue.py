import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCALIZATION = ROOT / "localization"
JAPANESE_OR_REPLACEMENT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\ufffd]")
OUTPUT_FIELDS = {
    "credits_ko.json": ("target_korean", 61),
    "ending_dialogue_ko.json": ("text", 23),
    "epilogue_dialogue_ko.json": ("text", 90),
    "event_dialogue_ko.json": ("text", 3565),
    "global_strings.json": ("target_korean", 312),
    "shared_word_resources.json": ("target_korean", 366),
    "ui_patch_surfaces.json": ("target_korean", 94),
}


def collect_strings(value, path):
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        return [
            row
            for index, child in enumerate(value)
            for row in collect_strings(child, f"{path}[{index}]")
        ]
    return []


def collect_field_values(value, field, path=""):
    rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key == field:
                rows.extend(collect_strings(child, child_path))
            else:
                rows.extend(collect_field_values(child, field, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(collect_field_values(child, field, f"{path}[{index}]"))
    return rows


class TranslationTargetResidueTests(unittest.TestCase):
    def test_output_targets_have_no_japanese_or_replacement_characters(self):
        for filename, (field, expected_count) in OUTPUT_FIELDS.items():
            with self.subTest(filename=filename):
                data = json.loads((LOCALIZATION / filename).read_text(encoding="utf-8"))
                rows = collect_field_values(data, field)
                self.assertEqual(len(rows), expected_count)
                residue = [
                    f"{path}: {text!r}"
                    for path, text in rows
                    if JAPANESE_OR_REPLACEMENT.search(text)
                ]
                self.assertEqual(residue, [])


if __name__ == "__main__":
    unittest.main()
