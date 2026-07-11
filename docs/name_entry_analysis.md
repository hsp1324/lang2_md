# Japanese Name-Entry Resource Analysis

This is a static ownership map for the Japanese-ROM name-entry screen. It does
not claim that the selectable Japanese grid is Korean or live-verified.

## Confirmed Code References

| Code | Instruction target | Role |
| --- | --- | --- |
| `0x02ABF8` | `0x0A38E0` | name-entry layout resource |
| `0x02AC0E` | `0x0A37BE` | `名前を決めて下さい...` prompt |
| `0x02AC22` | `0x0A38A6` | initial local-token layout |
| `0x02AC3E` | `0x0A3B0C` | default-name buffer copied to RAM `0xD1A8` |
| `0x02B4BE` | `0x0A3BB0` | confirmation glyph/control comparison |
| `0x02B67A` | `0x0A3BB0` | confirmation glyph list load |
| `0x02B68E` | `0x0A3BC0` | confirmation local-token layout |

The loop at `0x02AC48..0x02AC4E` copies eight words from `0x0A3B0C`. The
editable name itself uses five cells; the remaining three copied words are
padding. The builder now validates all eight original words and writes `엘윈`
followed by six spaces, rather than relying on the original trailing padding.

## Selectable Character Resources

- `0x0A3864`: 32 English/number glyph entries.
- `0x0A3C5A`: 32 Japanese selectable glyph entries.
- `0x0A38A6`, `0x0A38C2`, `0x0A3CC0`, `0x0A3CE2`: screen-local token/layout rows.
- `0x0A3BB0`: seven confirmation glyph/control entries, visibly including
  conventional `YES`/`NO` labels.

The existing default-name patch only changes the initial buffer and reused
glyph pixels. It does not convert the complete selectable Japanese grid into a
usable Korean input method. Do not replace `0x0A3C5A` blindly: its page/control
ownership and cursor-to-buffer behavior still require live verification.
