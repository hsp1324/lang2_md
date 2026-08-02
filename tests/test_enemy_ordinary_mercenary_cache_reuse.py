from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]


class EnemyOrdinaryMercenaryCacheReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = builder.IN_ROM.read_bytes()
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_enemy_ordinary_mercenary_cache_reuse(cls.patched)
        cls.loader = (
            builder._build_enemy_ordinary_mercenary_cache_loader_routine()
        )
        cls.lookup = (
            builder._build_enemy_ordinary_mercenary_cache_lookup_routine()
        )
        cls.lookup_start = (
            builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE
            + len(cls.loader)
        )

    def test_stock_dynamic_cache_and_lookup_are_both_hooked(self) -> None:
        for hook, target in (
            (
                builder.ENEMY_ORDINARY_MERCENARY_CACHE_LOADER_HOOK,
                builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE,
            ),
            (
                builder.ENEMY_ORDINARY_MERCENARY_CACHE_LOOKUP_HOOK,
                self.lookup_start,
            ),
        ):
            with self.subTest(hook=f"0x{hook:06X}"):
                self.assertEqual(
                    self.original[
                        hook:
                        hook
                        + len(
                            builder.ENEMY_ORDINARY_MERCENARY_CACHE_HOOK_ORIGINAL
                        )
                    ],
                    builder.ENEMY_ORDINARY_MERCENARY_CACHE_HOOK_ORIGINAL,
                )
                self.assertEqual(
                    self.patched[hook:hook + 6],
                    bytes.fromhex("4E F9") + target.to_bytes(4, "big"),
                )

    def test_generated_routines_fit_the_owned_gap(self) -> None:
        start = builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE
        self.assertEqual(
            self.patched[start:start + len(self.loader)],
            self.loader,
        )
        self.assertEqual(
            self.patched[
                self.lookup_start:self.lookup_start + len(self.lookup)
            ],
            self.lookup,
        )
        self.assertLessEqual(
            self.lookup_start + len(self.lookup),
            builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE_LIMIT,
        )

    def test_lookup_scans_fixed_dynamic_and_overflow_entries(self) -> None:
        self.assertIn(
            bytes.fromhex("41 F9")
            + builder.ENEMY_ORDINARY_MERCENARY_FIXED_TABLE.to_bytes(4, "big"),
            self.lookup,
        )
        self.assertIn(bytes.fromhex("70 0F"), self.lookup)
        self.assertIn(
            bytes.fromhex("41 F9")
            + builder.ENEMY_DYNAMIC_MERCENARY_TABLE.to_bytes(4, "big"),
            self.lookup,
        )
        self.assertIn(bytes.fromhex("70 09"), self.lookup)
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_MERCENARY_LOOKUP_RETURN.to_bytes(4, "big"),
            self.lookup,
        )

    def test_loader_borrows_only_a_runtime_unused_fixed_row(self) -> None:
        for class_id in (
            builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS,
            builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS,
        ):
            self.assertIn(
                bytes.fromhex("0C 41") + class_id.to_bytes(2, "big"),
                self.loader,
            )
        self.assertIn(
            builder.ENEMY_DYNAMIC_MERCENARY_TABLE_END.to_bytes(4, "big"),
            self.loader,
        )
        self.assertIn(
            builder.ENEMY_ORDINARY_MERCENARY_FIXED_LAST_ROW.to_bytes(4, "big"),
            self.loader,
        )
        self.assertIn(
            builder.ENEMY_MERCENARY_RUNTIME_BASE.to_bytes(4, "big"),
            self.loader,
        )
        self.assertIn(
            bytes.fromhex("78 13 0C 13 00 FF"),
            self.loader,
        )
        self.assertIn(bytes.fromhex("7A 06"), self.loader)
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_ORDINARY_MERCENARY_LOADER_SKIP.to_bytes(4, "big"),
            self.loader,
        )
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_ORDINARY_MERCENARY_LOADER_RESUME.to_bytes(
                4, "big"
            ),
            self.loader,
        )
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_ORDINARY_MERCENARY_LOADER_LOAD.to_bytes(4, "big"),
            self.loader,
        )

    def test_corruption_proof_fallback_table_is_installed(self) -> None:
        table = builder.ENEMY_MERCENARY_FALLBACK_CLASS_TABLE
        expected = builder.ENEMY_ADVANCED_MERCENARY_FALLBACK_CLASSES
        self.assertEqual(self.patched[table:table + len(expected)], expected)
        self.assertIn(table.to_bytes(4, "big"), self.lookup)
        self.assertEqual(len(expected), 0x0E)
        self.assertEqual(expected[0x72 - 0x72], 0x64)  # Soldier
        self.assertEqual(expected[0x7C - 0x72], 0x6D)  # Dark Guard -> Guardman
        self.assertEqual(expected[0x7F - 0x72], 0x63)  # Phalanx

    def test_patch_rejects_an_occupied_routine_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE] = 0
        with self.assertRaisesRegex(ValueError, "routine area is not blank"):
            builder.patch_enemy_ordinary_mercenary_cache_reuse(data)

    def test_patch_rejects_an_occupied_fallback_table(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.ENEMY_MERCENARY_FALLBACK_CLASS_TABLE] = 0
        with self.assertRaisesRegex(ValueError, "fallback table area is not blank"):
            builder.patch_enemy_ordinary_mercenary_cache_reuse(data)


if __name__ == "__main__":
    unittest.main()
