from pathlib import Path
import unittest

from editor.model import (
    class_change_editor_model,
    class_progression_editor_model,
)
from tools.class_ability_data import (
    learned_runtime_mask,
    read_ability_definitions,
)
from tools.class_hire_data import class_record_offset
from tools.class_progression_data import (
    CLASS_AT_GROWTH_OFFSET,
    CLASS_DF_GROWTH_OFFSET,
    CLASS_MP_GROWTH_OFFSET,
    GROWTH_HELPER_HOOK,
    GROWTH_HELPER_ORIGINAL,
    GROWTH_OVERRIDE_AT_TABLE,
    GROWTH_OVERRIDE_MP_TABLE,
    GROWTH_OVERRIDE_ROUTINE,
    GROWTH_OVERRIDE_ROUTINE_LIMIT,
    commander_starting_record_offset,
    patch_ability_requirements,
    patch_class_progressions,
    patch_commander_starting_classes,
    read_commander_starting_records,
    read_playable_class_progressions,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ClassProgressionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def progression_rows(self) -> list[dict[str, object]]:
        return class_progression_editor_model(
            self.korean,
            self.japanese,
        )["classes"]

    def test_model_exposes_real_starts_and_semantic_keith_lester_roots(self):
        model = class_change_editor_model(self.korean, self.japanese)
        keith = model["commanders"][6]
        lester = model["commanders"][8]
        self.assertEqual(
            (keith["starting_class_id"], keith["starting_level"]),
            (0x06, 10),
        )
        self.assertEqual(
            (lester["starting_class_id"], lester["starting_level"]),
            (0x07, 10),
        )
        self.assertEqual(
            next(
                row["source_tier"]
                for row in keith["transitions"]
                if row["current_class"] == 0x06
            ),
            1,
        )
        self.assertEqual(
            next(
                row["source_tier"]
                for row in keith["transitions"]
                if row["current_class"] == 0x2B
            ),
            2,
        )
        self.assertEqual(
            next(
                row["source_tier"]
                for row in lester["transitions"]
                if row["current_class"] == 0x07
            ),
            1,
        )
        self.assertEqual(
            next(
                row["source_tier"]
                for row in lester["transitions"]
                if row["current_class"] == 0x2C
            ),
            2,
        )

    def test_starting_class_patch_changes_only_ten_roster_class_bytes(self):
        data = bytearray(self.korean)
        before = bytes(data)
        rows = [
            {
                "commander_id": record.commander_id,
                "starting_class_id": (
                    0x04 if record.commander_id == 1 else record.class_id
                ),
            }
            for record in read_commander_starting_records(data)
        ]
        patch_commander_starting_classes(data, rows)
        changed = [
            offset
            for offset, (old, new) in enumerate(zip(before, data))
            if old != new
        ]
        self.assertEqual(changed, [commander_starting_record_offset(1)])
        self.assertEqual(read_commander_starting_records(data)[0].class_id, 0x04)

    def test_progression_model_has_all_playable_classes_and_global_abilities(self):
        model = class_progression_editor_model(self.korean, self.japanese)
        self.assertEqual(len(model["classes"]), 0x2C)
        self.assertEqual(len(model["abilities"]), 23)
        fighter = model["classes"][0]
        self.assertEqual(fighter["class_id"], 0x01)
        self.assertEqual(fighter["movement"], 5)
        self.assertEqual(fighter["soldier_at_correction"], 0)
        self.assertEqual(fighter["soldier_df_correction"], 2)
        self.assertEqual(len(fighter["growth"]["mp"]), 10)
        self.assertEqual(fighter["ability_ids"], [0xFF] * 4)
        self.assertEqual(model["abilities"][22]["name"], "소환")
        self.assertEqual(model["abilities"][22]["kind"], "summon")

    def test_unchanged_progression_round_trip_is_byte_exact(self):
        data = bytearray(self.korean)
        before = bytes(data)
        patch_class_progressions(data, self.progression_rows())
        self.assertEqual(bytes(data), before)
        self.assertEqual(
            data[GROWTH_HELPER_HOOK : GROWTH_HELPER_HOOK + 6],
            GROWTH_HELPER_ORIGINAL,
        )

    def test_unchanged_japanese_progression_round_trip_is_byte_exact(self):
        model = class_progression_editor_model(
            self.japanese,
            self.japanese,
        )
        data = bytearray(self.japanese)
        before = bytes(data)
        patch_class_progressions(data, model["classes"])
        patch_ability_requirements(data, model["abilities"])
        self.assertEqual(bytes(data), before)

    def test_growth_override_is_per_class_and_preserves_stock_stat_bytes(self):
        data = bytearray(self.korean)
        rows = self.progression_rows()
        fighter = rows[0]
        fighter["growth"]["at"][4] = 3
        fighter["growth"]["mp"][7] = 2
        fighter_base = class_record_offset(0x01)
        stock_codes = bytes(
            data[
                fighter_base + CLASS_MP_GROWTH_OFFSET:
                fighter_base + CLASS_DF_GROWTH_OFFSET + 1
            ]
        )

        patch_class_progressions(data, rows)

        self.assertEqual(
            data[
                fighter_base + CLASS_MP_GROWTH_OFFSET:
                fighter_base + CLASS_DF_GROWTH_OFFSET + 1
            ],
            stock_codes,
        )
        self.assertEqual(
            data[GROWTH_HELPER_HOOK : GROWTH_HELPER_HOOK + 6],
            bytes.fromhex("4E F9") + GROWTH_OVERRIDE_ROUTINE.to_bytes(4, "big"),
        )
        self.assertNotEqual(
            data[GROWTH_OVERRIDE_ROUTINE:GROWTH_OVERRIDE_ROUTINE_LIMIT],
            b"\xFF" * (GROWTH_OVERRIDE_ROUTINE_LIMIT - GROWTH_OVERRIDE_ROUTINE),
        )
        relative = 0x01 * 0x1C
        self.assertEqual(data[GROWTH_OVERRIDE_AT_TABLE + relative + 4], 3)
        self.assertEqual(data[GROWTH_OVERRIDE_MP_TABLE + relative + 7], 2)
        reread = read_playable_class_progressions(data)[0]
        self.assertEqual(reread.at_growth[4], 3)
        self.assertEqual(reread.mp_growth[7], 2)

    def test_second_growth_edit_preserves_an_existing_class_override(self):
        data = bytearray(self.korean)
        first_rows = self.progression_rows()
        first_rows[0]["growth"]["at"][4] = 3
        patch_class_progressions(data, first_rows)

        second_model = class_progression_editor_model(data, self.japanese)
        second_model["classes"][1]["growth"]["df"][2] = 4
        patch_class_progressions(data, second_model["classes"])

        fighter = read_playable_class_progressions(data)[0]
        cleric = read_playable_class_progressions(data)[1]
        self.assertEqual(fighter.at_growth[4], 3)
        self.assertEqual(cleric.df_growth[2], 4)

    def test_growth_edit_rejects_unexpanded_japanese_rom(self):
        model = class_progression_editor_model(
            self.japanese,
            self.japanese,
        )
        model["classes"][0]["growth"]["at"][4] = 3
        with self.assertRaisesRegex(ValueError, "expanded Korean ROM"):
            patch_class_progressions(
                bytearray(self.japanese),
                model["classes"],
            )

    def test_ability_slots_and_global_required_levels_patch_independently(self):
        progression_model = class_progression_editor_model(
            self.korean,
            self.japanese,
        )
        data = bytearray(self.korean)
        progression_model["classes"][0]["ability_ids"] = [
            0x00,
            0x16,
            0xFF,
            0xFF,
        ]
        progression_model["abilities"][0]["required_level"] = 10
        patch_class_progressions(data, progression_model["classes"])
        patch_ability_requirements(data, progression_model["abilities"])
        fighter = read_playable_class_progressions(data)[0]
        self.assertEqual(fighter.ability_ids, (0x00, 0x16))
        self.assertEqual(read_ability_definitions(data)[0].required_level, 10)
        self.assertEqual(read_ability_definitions(data)[22].required_level, 1)
        self.assertEqual(learned_runtime_mask(data, 0x01, 9), 1 << 23 | 1)
        self.assertEqual(
            learned_runtime_mask(data, 0x01, 10),
            (1 << 1) | (1 << 23) | 1,
        )


if __name__ == "__main__":
    unittest.main()
