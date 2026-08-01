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

    def test_lookup_uses_the_preloaded_sixteen_entry_table(self) -> None:
        self.assertIn(
            bytes.fromhex("41 F9")
            + builder.ENEMY_ORDINARY_MERCENARY_FIXED_TABLE.to_bytes(4, "big"),
            self.lookup,
        )
        self.assertIn(bytes.fromhex("70 0F"), self.lookup)
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_ORDINARY_MERCENARY_FIXED_LOOKUP_SCAN.to_bytes(
                4, "big"
            ),
            self.lookup,
        )
        self.assertIn(
            bytes.fromhex("4E F9")
            + builder.ENEMY_ORDINARY_MERCENARY_DYNAMIC_LOOKUP_RESUME.to_bytes(
                4, "big"
            ),
            self.lookup,
        )

    def test_loader_skips_only_the_ordinary_hireable_range(self) -> None:
        for class_id in (
            builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS,
            builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS,
        ):
            self.assertIn(
                bytes.fromhex("0C 41") + class_id.to_bytes(2, "big"),
                self.loader,
            )
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

    def test_patch_rejects_an_occupied_routine_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.ENEMY_ORDINARY_MERCENARY_CACHE_ROUTINE] = 0
        with self.assertRaisesRegex(ValueError, "routine area is not blank"):
            builder.patch_enemy_ordinary_mercenary_cache_reuse(data)


if __name__ == "__main__":
    unittest.main()
