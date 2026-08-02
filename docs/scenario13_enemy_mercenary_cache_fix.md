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

The post-fix current-source normal candidate (`SHA-256
58fdd97aba3d768bf3729052ba6fe211f4b23c35b63e65a941bf96ba01541592`,
MD checksum `1E83`) was also rebuilt with the legacy Scenario 13 mercenary
roster and one immediately visible diagnostic Dark Guard.  Before and after
status hover, Dark Guard occupied dynamic row 8 at tile `0x03A8`; both
animation frames exactly matched ROM sprite `0x006D`.  The fresh evidence is
`captures/run/enemy_dynamic_mercenary_status_probe/post-darkguard-current-s13-visible-darkguard-20260802-01/evidence.json`.

The first current-source rerun at
`post-darkguard-current-s13-darkguard-20260802-01` intentionally retained the
stock event visibility and stopped with `no visible enemy subordinate class
0x7C`; it is a documented setup failure, not a cache or rendering failure.  The
diagnostic builder's `--make-darkguard-visible` option changes only one
otherwise visible Dragonia subordinate in the ignored probe ROM.

The diagnostic ROM is not a release and does not change the checked-in version
registry.
