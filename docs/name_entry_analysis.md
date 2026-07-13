# Japanese Name-Entry Resource Analysis

This is the ownership and live-verification map for the Korean name-entry
screen built on the Japanese ROM.

## Confirmed Code References

| Code | Instruction target | Role |
| --- | --- | --- |
| `0x02ABF8` | `0x0A38E0` | name-entry layout resource |
| `0x02AC0E` | `0x0A37BE` | `名前を決めて下さい...` prompt |
| `0x02AC22` | `0x0A38A6` | initial local-token layout |
| `0x02AC3E` | `0x0A3B0C` | default-name buffer copied to RAM `0xD1A8` |
| `0x02AC52` | `0x0A37E6` | 95-entry selectable glyph list loaded at VRAM `0x2000` |
| `0x02B060` | `0x0A3B3E` | selection-index to saved-byte table |
| `0x02B4BE` | `0x0A3BB0` | confirmation glyph/control comparison |
| `0x02B67A` | `0x0A3BB0` | confirmation glyph list load |
| `0x02B68E` | `0x0A3BC0` | confirmation local-token layout |

The loop at `0x02AC48..0x02AC4E` copies eight words from `0x0A3B0C`. The
editable name uses selection indexes, not final glyph IDs. The builder writes
the indexes for `엘`, `윈`, then six `0x0054` blank/delete values.

## Korean Grid

- `0x0A38E0..0x0A3B0A` is a compressed byte-tilemap with decoded dimensions
  40x28. The builder validates SHA-256
  `bd71d36d26f9866d92b272c15c54fefb3253810c94d3f6565b0725e118eb403d`
  before patching its independently encoded cells.
- `0x0A37E6` contains 95 word glyph IDs. The production grid exposes 57 Korean
  syllables at indexes 0..53 and 55..57. Every other selectable cell is blank.
  Index 70 is a Japanese composite-character special case and index `0x54` is
  the engine's blank/delete command, so neither may be repurposed.
- `0x0A3B3E` contains the corresponding 95 saved byte values. It is validated
  against SHA-256
  `50d1a1959f5d98185873049d2b4555315a1433f35ee960b87d6e3902beb9fb9a`.
- The small byte-font allocator is limited to the verified 64-code pool:
  half-width-kana codes `0xA5..0xDF` plus original uppercase tiles
  `J/Q/W/Y/Z`. `B/K/U` remain original for `BGM`, name-entry `OK`, and the
  in-map `TURN` label. Digits, status/faction graphics, and gauge/icon graphics
  `0xE0..0xFF` are not reused.
- Japanese dakuten helper cells are cleared. The action labels are the
  conventional ASCII `OK`, `NO`, and `END` labels.

## Index-To-Glyph Confirmation Hook

The original ROM relies on selectable indexes and glyph IDs both being 0..94.
That stops being true once Korean glyphs live at `0x7000..0x7262`.

The editable RAM buffer must retain indexes because `0x02B070` indexes the
saved-byte table with each value. Conversely, dialogue RAM `0xA5DE` must
receive the actual glyph ID or the hero speaker name renders as Japanese
`ハヘ`. The builder replaces the 18-byte copy loop at `0x02B046` with a call to
`0x2A0000`. The trampoline looks up `0x0A37E6[index]`, writes that glyph ID to
`0xA5DE`, preserves the following byte conversion, and terminates the glyph
list with `FFFF`.

## Live Verification

- Build checksum `0267` renders the default `엘윈`, intact `OK/NO`,
  and confirms through the route screen without a reset. Evidence is
  `captures/run/0267_name_entry.png`,
  `captures/run/0267_name_confirm.png`, and
  `captures/run/0267_name_confirm_route.png`.
- The same fresh boot reached Scenario 1 and preserved the Start-menu save
  prompt and its `YES/NO` labels in `captures/run/0267_save_confirm.png`.
- Checksum `4DC7` filled the original `0x7000..0x72FE` 16x16 pool to 766/766
  after the full direct name-table promotion. A fresh boot preserved `엘윈`,
  `OK/NO`, and confirmation through the route screen in
  `captures/run/4dc7_name_entry.png` and
  `captures/run/4dc7_name_confirm.png`.
- Static build `69D4` extends only the word-text font storage through `0x73FE`
  for ending/epilogue work while preserving every established name-entry glyph
  ID. `tests/test_custom_glyph_storage.py` proves the full-16-bit converter and
  non-overlap with relocated resources. A fresh live boot preserved `엘윈`,
  `OK/NO`, the full grid, route entry, and Scenario 1 in
  `captures/run/69d4_name_entry.png`, `69d4_name_confirm.png`, and
  `69d4_scenario1.png`.
- Earlier checksum `0E8A` proved the confirmation hook with a manually selected
  high custom name `폴` through route, preparation, and dialogue. Its former
  84-syllable grid was later retired because it consumed byte-font codes owned
  by live status, faction, and icon graphics. The historical captures remain
  under `captures/run/0e8a_*`.

The production screen is a practical 57-syllable palette for game names, not
arbitrary Hangul composition. Expanding it requires a screen-specific font
resource or a new page/composition design; do not reuse reserved indexes or
shared status/icon byte codes.
