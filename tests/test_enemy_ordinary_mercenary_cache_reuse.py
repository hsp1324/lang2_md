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
        cls.prep_restore = (
            builder._build_preparation_mercenary_cache_restore_routine()
        )
        cls.shop_finalizer = (
            builder._build_preparation_mercenary_cache_restore_shop_finalizer()
        )
        cls.shop_completion = (
            builder._build_preparation_mercenary_cache_restore_shop_completion()
        )
        cls.direct_restore = (
            builder._build_preparation_mercenary_cache_direct_restore_routine()
        )
        cls.entry_restore = (
            builder._build_preparation_entry_cache_restore_routine()
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

    def test_preparation_restore_requeues_both_frames_for_both_tables(
        self,
    ) -> None:
        for table in (
            builder.ENEMY_ORDINARY_MERCENARY_FIXED_TABLE,
            builder.ENEMY_DYNAMIC_MERCENARY_TABLE,
        ):
            self.assertIn(table.to_bytes(4, "big"), self.prep_restore)
        for frame_base in builder.MAP_SPRITE_FRAME_BASES:
            self.assertIn(frame_base.to_bytes(4, "big"), self.prep_restore)
        self.assertEqual(
            self.prep_restore.count(bytes.fromhex("4E B9 00 01 14 90")),
            2,
        )
        self.assertEqual(
            self.prep_restore.count(bytes.fromhex("38 FC FF F9")),
            4,
        )
        self.assertEqual(
            self.prep_restore.count(bytes.fromhex("38 FC 00 40")),
            4,
        )
        self.assertTrue(
            self.prep_restore.endswith(
                bytes.fromhex("4C DF 7F FF 4E 75")
            )
        )

    def test_preparation_restore_routine_uses_owned_gap(self) -> None:
        start = builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_ROUTINE
        self.assertEqual(
            self.patched[start:start + len(self.prep_restore)],
            self.prep_restore,
        )
        self.assertLessEqual(
            start + len(self.prep_restore),
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_ROUTINE_LIMIT,
        )

    def test_shop_return_rebuilds_static_icons_and_all_unit_caches(self) -> None:
        hook = builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_HOOK
        original = builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_HOOK_ORIGINAL
        self.assertEqual(self.original[hook:hook + len(original)], original)
        self.assertEqual(
            self.patched[hook:hook + len(original)],
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_FINALIZER.to_bytes(
                4, "big"
            )
            + bytes.fromhex("4E 71"),
        )
        finalizer = builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_FINALIZER
        self.assertEqual(
            self.patched[finalizer:finalizer + len(self.shop_finalizer)],
            self.shop_finalizer,
        )
        self.assertTrue(
            self.shop_finalizer.startswith(bytes.fromhex("48 E7 FF FE"))
        )
        self.assertTrue(
            self.shop_finalizer.endswith(bytes.fromhex("4C DF 7F FF 4E 75"))
        )
        for target in (
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_GRAPHICS_1,
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_GRAPHICS_2,
            builder.BYTE_UI_PREP_MERCENARY_CACHE_DIRECT_RESTORE_ROUTINE,
        ):
            self.assertIn(
                bytes.fromhex("4E B9") + target.to_bytes(4, "big"),
                self.shop_finalizer,
            )
        self.assertIn(
            bytes.fromhex("26 BC 54 00 00 01"),
            self.shop_finalizer,
        )
        self.assertLess(
            self.shop_finalizer.index(bytes.fromhex("4E B9 00 00 8A 6C")),
            self.shop_finalizer.index(
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_PREP_MERCENARY_CACHE_DIRECT_RESTORE_ROUTINE.to_bytes(
                    4, "big"
                )
            ),
        )

        completion_hook = (
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_COMPLETION_HOOK
        )
        completion_original = (
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_COMPLETION_HOOK_ORIGINAL
        )
        self.assertEqual(
            self.original[
                completion_hook:completion_hook + len(completion_original)
            ],
            completion_original,
        )
        self.assertEqual(
            self.patched[
                completion_hook:completion_hook + len(completion_original)
            ],
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_COMPLETION.to_bytes(
                4, "big"
            )
            + bytes.fromhex("4E 71 4E 71"),
        )
        completion = builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_COMPLETION
        self.assertEqual(
            self.patched[completion:completion + len(self.shop_completion)],
            self.shop_completion,
        )
        self.assertTrue(self.shop_completion.startswith(bytes.fromhex("48 E7 FF FE")))
        self.assertTrue(
            self.shop_completion.endswith(completion_original + bytes.fromhex("4E 75"))
        )
        self.assertNotIn(
            bytes.fromhex("0C 39 00 FE FF FF A6 DA"),
            self.shop_completion,
        )
        self.assertNotIn(
            bytes.fromhex("0C 39 00 FD FF FF A6 DA"),
            self.shop_completion,
        )
        stable_cache_rebuild = (
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_MERCENARY_CACHE_DIRECT_RESTORE_ROUTINE.to_bytes(
                4, "big"
            )
        )
        self.assertIn(stable_cache_rebuild, self.shop_completion)
        direct_icon_copy = (
            bytes.fromhex(
                "47 F9 00 C0 00 04 49 F9 00 C0 00 00 "
                "36 BC 8F 02 26 BC 54 00 00 01 41 F9"
            )
            + (builder.BYTE_UI_PREP_STATIC_ICON_RAW + 0x1400).to_bytes(
                4, "big"
            )
            + bytes.fromhex("30 3C 05 FF 38 98 51 C8")
        )
        self.assertIn(direct_icon_copy, self.shop_completion)
        self.assertEqual(
            self.shop_completion.count(
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_MAP_SPRITE_CACHE_REBUILD_ROUTINE.to_bytes(
                    4, "big"
                )
            ),
            1,
        )
        clear_dynamic = (
            bytes.fromhex("41 F9")
            + builder.ENEMY_DYNAMIC_MERCENARY_TABLE.to_bytes(4, "big")
            + bytes((0x70, builder.ENEMY_DYNAMIC_MERCENARY_COUNT - 1))
        )
        self.assertIn(clear_dynamic, self.shop_completion)
        rebuild = (
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_MAP_SPRITE_CACHE_REBUILD_ROUTINE.to_bytes(4, "big")
        )
        resource = stable_cache_rebuild
        self.assertLess(
            self.shop_completion.index(clear_dynamic),
            self.shop_completion.index(rebuild),
        )
        self.assertLess(
            self.shop_completion.index(rebuild),
            self.shop_completion.index(resource),
        )
        self.assertLess(
            self.shop_completion.index(resource),
            self.shop_completion.index(direct_icon_copy),
        )
        self.assertLessEqual(
            completion + len(self.shop_completion),
            builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_SHOP_COMPLETION_LIMIT,
        )
        direct = builder.BYTE_UI_PREP_MERCENARY_CACHE_DIRECT_RESTORE_ROUTINE
        self.assertEqual(
            self.patched[direct:direct + len(self.direct_restore)],
            self.direct_restore,
        )
        self.assertLessEqual(
            direct + len(self.direct_restore),
            builder.BYTE_UI_PREP_MERCENARY_CACHE_DIRECT_RESTORE_ROUTINE_LIMIT,
        )
        self.assertIn(bytes.fromhex("36 BC 8F 02"), self.direct_restore)
        self.assertIn(bytes.fromhex("26 84 7A 3F 38 99"), self.direct_restore)
        entry = builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_ROUTINE
        self.assertEqual(
            self.patched[entry:entry + len(self.entry_restore)],
            self.entry_restore,
        )
        self.assertLessEqual(
            entry + len(self.entry_restore),
            builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_ROUTINE_LIMIT,
        )
        for hook, original, wrapper in (
            (
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_HOOK_A,
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_HOOK_A_ORIGINAL,
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_WRAPPER_A,
            ),
            (
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_HOOK_B,
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_HOOK_B_ORIGINAL,
                builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_WRAPPER_B,
            ),
        ):
            self.assertEqual(self.original[hook:hook + len(original)], original)
            self.assertEqual(
                self.patched[hook:hook + len(original)],
                bytes.fromhex("4E B9") + wrapper.to_bytes(4, "big"),
            )
            wrapper_code = (
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_PREP_ENTRY_CACHE_RESTORE_ROUTINE.to_bytes(
                    4, "big"
                )
                + original
                + bytes.fromhex("4E 75")
            )
            self.assertEqual(
                self.patched[wrapper:wrapper + len(wrapper_code)],
                wrapper_code,
            )

        resource_index = builder.BYTE_UI_PREP_STATIC_ICON_RESOURCE & 0x7FFF
        resource_pointer = builder.be32(
            self.original,
            builder.BYTE_UI_FONT_RESOURCE_TABLE + resource_index * 4,
        ) & 0x00FFFFFF
        expected_raw = builder.decompress_9dfe(
            self.original,
            resource_pointer + 1,
        )
        self.assertEqual(
            self.patched[
                builder.BYTE_UI_PREP_STATIC_ICON_RAW:
                builder.BYTE_UI_PREP_STATIC_ICON_RAW_LIMIT
            ],
            expected_raw,
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

    def test_patch_rejects_an_occupied_preparation_restore_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.BYTE_UI_PREP_MERCENARY_CACHE_RESTORE_ROUTINE] = 0
        with self.assertRaisesRegex(ValueError, "restore area is not blank"):
            builder.patch_enemy_ordinary_mercenary_cache_reuse(data)


if __name__ == "__main__":
    unittest.main()
