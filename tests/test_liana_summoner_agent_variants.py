from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/shared-liana-summoner-agent-v1"
)
LIVE = ROOT / "editor/static/ai-class-sprites"
KEYS = (
    (2, 0x28), (2, 0x25), (2, 0x26),
    (3, 0x28), (3, 0x25), (3, 0x26),
)


class LianaSummonerAgentVariantTests(unittest.TestCase):
    def test_full_geometry_and_neutral_pixels_match_master(self) -> None:
        report = json.loads(
            (SOURCE / "validation-report.json").read_text(encoding="utf-8")
        )
        self.assertTrue(report["all_accepted"])
        masters = {
            0x28: Image.open(
                SOURCE / "master/02-28-liana-user-edited.png"
            ).convert("RGBA"),
            0x25: Image.open(
                SOURCE / "class-masters/25.png"
            ).convert("RGBA"),
            0x26: Image.open(
                SOURCE / "class-masters/26.png"
            ).convert("RGBA"),
        }
        palettes = []
        for commander_id, class_id in KEYS:
            source = SOURCE / f"logical16/{commander_id:02d}-{class_id:02X}.png"
            live = LIVE / str(commander_id) / f"{class_id:02X}.png"
            image = Image.open(source).convert("RGBA")
            live_image = Image.open(live).convert("RGBA")
            self.assertEqual(
                list(image.get_flattened_data()),
                list(live_image.get_flattened_data()),
            )
            self.assertEqual(
                [bool(color[3]) for color in image.get_flattened_data()],
                [
                    bool(color[3])
                    for color in masters[class_id].get_flattened_data()
                ],
            )
            colors = {color for color in image.get_flattened_data() if color[3]}
            self.assertLessEqual(len(colors), 15)
            self.assertNotIn((0, 0, 0, 255), colors)
            self.assertNotIn((255, 0, 255, 255), colors)
            palettes.append(colors)
        self.assertEqual(len({frozenset(colors) for colors in palettes}), 6)
        self.assertGreaterEqual(min(report["class_alpha_differences"].values()), 5)

    def test_manifest_uses_latest_liana_master(self) -> None:
        manifest = json.loads((LIVE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["asset_version"], "liana-lana-healer-shared-v106"
        )
        for commander_id, class_id in KEYS:
            row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
            self.assertIn("쌍둥이 마법 클래스", row["ai_source_kind"])

    def test_agents_keep_gold_hair_and_do_not_share_summoner_colors(self) -> None:
        agent_master = Image.open(
            SOURCE / "class-masters/25.png"
        ).convert("RGBA")
        gold = (255, 182, 0, 255)
        hair_points = {
            (x, y)
            for y in range(8)
            for x in range(3, 13)
            if agent_master.getpixel((x, y)) == gold
        }
        self.assertEqual(len(hair_points), 18)
        for commander_id in (2, 3):
            agent = Image.open(
                LIVE / str(commander_id) / "25.png"
            ).convert("RGBA")
            for point in hair_points:
                self.assertEqual(agent.getpixel(point), gold)

        liana_agent = {
            color
            for color in Image.open(LIVE / "2/25.png").convert("RGBA").get_flattened_data()
            if color[3]
        }
        liana_summoner = {
            color
            for color in Image.open(LIVE / "2/28.png").convert("RGBA").get_flattened_data()
            if color[3]
        }
        lana_agent = {
            color
            for color in Image.open(LIVE / "3/25.png").convert("RGBA").get_flattened_data()
            if color[3]
        }
        lana_summoner = {
            color
            for color in Image.open(LIVE / "3/28.png").convert("RGBA").get_flattened_data()
            if color[3]
        }
        self.assertIn((146, 0, 73, 255), liana_agent)
        self.assertNotIn((146, 0, 73, 255), liana_summoner)
        self.assertIn((0, 146, 146, 255), lana_agent)
        self.assertNotIn((0, 146, 146, 255), lana_summoner)
        lana_zarvera = {
            color
            for color in Image.open(LIVE / "3/26.png").convert("RGBA").get_flattened_data()
            if color[3]
        }
        self.assertIn((73, 109, 255, 255), lana_zarvera)
        self.assertIn((109, 219, 255, 255), lana_zarvera)
        self.assertNotIn((0, 146, 146, 255), lana_zarvera)


if __name__ == "__main__":
    unittest.main()
