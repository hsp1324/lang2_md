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
- `0x0A37E6` contains 95 word glyph IDs. Indexes 0..69, 71..83, and 85 expose
  84 Korean syllables. Index 70 is a Japanese composite-character special
  case, index `0x54` is the engine's blank/delete command, and 86..94 remain
  blank.
- `0x0A3B3E` contains the corresponding 95 saved byte values. It is validated
  against SHA-256
  `50d1a1959f5d98185873049d2b4555315a1433f35ee960b87d6e3902beb9fb9a`.
- The small byte-font allocator now has 100 protected codes. Uppercase
  `LV/AT/DF/ITEM`, digits, status graphics `0x80..0xA4`, and gauge/icon graphics
  `0xE0..0xFF` are not reused.
- Japanese dakuten helper cells are cleared. The action labels are `진행`,
  `뒤로`, and the conventional `END` label.

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

- Build checksum `0E8A`: default `엘윈` renders in the grid, preparation UI,
  battle status, and dialogue speaker label.
- A non-default high custom glyph was selected as `폴`, confirmed through the
  route screen, and verified in preparation and dialogue without a reset:
  `captures/run/0e8a_name_selected_pol.png`,
  `captures/run/0e8a_pol_prep.png`, and
  `captures/run/0e8a_pol_dialogue_3.png`.
- Build checksum `8A01` keeps the hook and removes two blank Scenario 1 event
  pages caused by translated line controls. The verified sequence is in
  `captures/analysis/8a01_event_00_23.png`.

This is a practical 84-syllable palette for game names, not arbitrary Hangul
composition. Expanding it requires a new page/composition design; do not reuse
the reserved indexes or status/icon byte codes.
