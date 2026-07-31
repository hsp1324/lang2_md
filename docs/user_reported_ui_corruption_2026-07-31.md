# User-reported preparation and shop corruption — 2026-07-31

## Outcome

Two independent VRAM ownership bugs explain the reported failures:

1. Preparation, deployment, hiring, and class/status surfaces reused the static
   Hangul extension ranges as commander and mercenary graphics. Reloading a
   full static font could therefore turn sprites into gray Hangul blocks, or
   turn commander/class/mercenary text into sprite fragments. The current
   candidate keeps the stock font on those surfaces and renders all 121 unsafe
   characters through 26 conflict-colored, ownership-audited scratch slots.
2. The item-name overflow bank put `넥클리스` token 68 (`클`) at VRAM
   `0xB600`, exactly where the shop stores a green page-arrow graphic. The
   compact 166-glyph description bank now ends at `0xA700`; name overflow uses
   `0xA700..0xB3FF`, so `클` is rendered at `0xA900`.

The Scenario 9 normal and hard candidates each pass 32/32 same-run pre/post
shop full-screen pairs, including seven allied commanders over two pages,
every offered hiring page, both roster pages, and all 13 fixed details. Both
profiles also pass the gray acted-sprite and real stock-victory result checks.
The `크로스`/`넥클리스` shop page was separately reviewed with each item
selected and both rows intact.

This is candidate evidence, not a release promotion. Scenarios 4–8 and 10–27
still require the same complete normal/hard runtime matrix before the overall
release gate can pass.

## Reported captures

The following desktop captures were supplied as historical manifestations of
the preparation/deployment corruption family:

- `화면 캡처 2026-07-29 003444.png`
- `화면 캡처 2026-07-29 015645.png`
- `화면 캡처 2026-07-29 015958.png`
- `화면 캡처 2026-07-29 025653.png`
- `화면 캡처 2026-07-29 110654.png`
- `화면 캡처 2026-07-29 111002.png`
- `화면 캡처 2026-07-29 114439.png`
- `화면 캡처 2026-07-29 133442.png`
- `화면 캡처 2026-07-29 133748.png`
- `화면 캡처 2026-07-29 134056.png`
- `화면 캡처 2026-07-30 003256.png`
- `화면 캡처 2026-07-30 003431.png`
- `화면 캡처 2026-07-30 003540.png`
- `화면 캡처 2026-07-30 003705.png`
- `화면 캡처 2026-07-30 003842.png`
- `화면 캡처 2026-07-30 014727.png`
- `화면 캡처 2026-07-30 183035.png`
- `화면 캡처 2026-07-30 183145.png`
- `화면 캡처 2026-07-30 183637.png`
- `화면 캡처 2026-07-30 183753.png`
- `화면 캡처 2026-07-31 022045.png`
- `화면 캡처 2026-07-31 022141.png`

The last two are Scenario 9 failure references. They are now covered by the
complete Scenario 9 normal/hard evidence in
`localization/preparation_surface_scenario_09.json`.

The shop-specific report is:

- `화면 캡처 2026-07-31 111759.png` — `크로스` is intact, while only the
  `클` in `넥클리스` is replaced by a green graphic.

Its root cause and accepted runtime captures are recorded in
`localization/item_shop_overflow_regression.json`.
