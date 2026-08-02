# Scenario 13 enemy mercenary cache fix

## Failure

An in-game save created with the B1.0.4 Scenario 13 roster can retain twelve
distinct advanced enemy mercenary classes.  The stock battle cache owns only
ten dynamic rows at WRAM `0xFFFFA88E..0xFFFFA8B5`.  Its renderer nevertheless
assumes every requested class was cached.  A miss therefore reads the next
WRAM owner's word as a tile number, which displays Korean font fragments over
units such as Vargas's `다크가드`.

## Repair

`scripts/build_korean_jp_probe.py` now treats the fixed and dynamic cache as a
single lookup domain, never writes an eleventh dynamic row, and recognizes
classes already loaded into either table.  When the loader encounters a true
overflow class, it borrows a fixed ordinary row only after scanning the twenty
runtime groups and proving that row's ordinary subordinate class is unused.

Some stock group paths omit a class from the preload pass entirely.  The
renderer now handles that case with an explicit same-family ordinary-class
fallback table instead of reading the following WRAM owner.  This last-resort
path changes only the displayed silhouette; class name and combat data remain
the requested advanced class.

## Runtime evidence

- Diagnostic ROM: `tmp/darkguard-overflow-candidate/legacy-b104-s13-mercenaries-v6.md`
  (`SHA-256 c8adebc36ec40568cfb0e6cfbd2d56a6136e6cab02d4fe7e29c9cf44c6aa3cf2`,
  MD checksum `59B3`).
- Legacy `다크가드` (`0x7C`) occupies dynamic row 0 at tile `0x0388`.
  Both active animation frames, VRAM `0x7100..0x717F` and
  `0x9100..0x917F`, exactly match sprite `0x006D` in the ROM.
- A deliberately uncached advanced Soldier (`0x72`) uses the ordinary Soldier
  row at tile `0x0350`.  Before and after status hover, both frames match the
  ROM source and no Korean/font tile is referenced.
- Evidence:
  `captures/run/enemy_dynamic_mercenary_status_probe/overflow-safe-final-s13-legacy-roster-20260802-01/evidence.json`.
- Focused cache, acted-sprite, and dynamic-glyph ownership suite: 24 tests,
  all passing.

The diagnostic ROM is not a release and does not change the checked-in version
registry.
