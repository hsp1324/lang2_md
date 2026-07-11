# Japanese Class-Change Resource Analysis

The Japanese class-change screen uses a shared 15-slot global glyph list rather
than an FF-terminated byte string.

## Confirmed Ownership

- Code `0x02BB60` loads 15 glyphs from `0x0A3C9C` into VRAM `0xD080`.
- Layout `0x0A3CBA` references slots 0..10 and displays
  `クラスチェンジできます`.
- Code `0x02BC0C` opens layout `0x0A3CDC`, which references slots 0..6 and
  displays the shorter title `クラスチェンジ`.
- Original slots 11..14 are `傭兵` and `魔法` and are shared by the detail UI.

## Korean Slot Plan

The builder preserves all 15 indexes:

```text
0..5   클래스체인지
6      space
7..8   가능
9..10  space
11..12 용병
13..14 마법
```

This makes the existing 0..10 layout read `클래스체인지 가능`, the 0..6
layout read `클래스체인지`, and preserves the two detail labels without
changing layout tokens or code. The original 15-word tuple is validated before
patching. Runtime navigation and every candidate class still require emulator
verification.
