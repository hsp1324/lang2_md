# Preparation/status dynamic glyph ownership

The preparation, hiring, shop, commander-status, and result paths do not keep
the same static 8x8 font tiles alive as the map-bottom status renderer. Their
graphics loads overwrite the final static font segment. A Hangul string can
therefore render correctly on the map and still lose individual syllables in
the preparation or status screen.

## Runtime symptom and scope

The Android RetroArch captures from 2026-07-29 establish three separate
preparation/status failures:

- Elwin's `샤먼` class label lost both class syllables in the commander-status
  panel.
- Scenario 4's deployment list lost `록` in `워록`.
- The same list lost the final `안` in `바바리안`.
- The class-change screen rendered the three middle syllables of
  `수수께끼의 기사` as one red graphics block.
- Scenario 5's deployment list lost `울` in both `웨어울프` and `울프맨`.
- The same deployment surface also showed the already tracked `쉐` corruption
  in `쉐리` on the released 1.0.0 build.

The user confirmed that `워록` and `바바리안` remain intact in the map-bottom
information panel. The class/name table records are therefore correct; the
failure belongs to the preparation/status tile lifetime.

## Scratch ownership

The first 16 entries of `BYTE_UI_DYNAMIC_TILE_IDS` remain the two established
eight-cell map fields. They are not reordered:

- slots 0..7: selected unit name
- slots 8..15: selected unit class

Preparation/status rendering also uses fixed slots because several rows can
remain visible simultaneously. The existing 16 slots cover:

`라 론 쉐 카 코 키 록 적 가 스 럴 슬 임 비 크 제`

Seven additional preparation-only slots cover:

`샤 먼 안 께 울 끼 의`

They use VRAM tile IDs `0x07AA`, `0x07AB`, `0x07AC`, `0x07B6`, `0x07B7`,
`0x07B9`, and `0x07BB`. These patterns are in the unused tail of the
full-screen H-scroll table, like the established map cache. The first three
passed the earlier 286-state ownership scan. A broader read-only scan of 696
retained GST runtime states found zero Plane A, Plane B, window, or map-SAT
references to all seven IDs before assignment. Tile `0x07A0` remains reserved
for the active H-scroll word, and cursor-owned `0x07BE..0x07BF` remain
excluded.

The expansion tables now reserve capacity for 32 scratch slots:

- VDP commands: `0x2BE800..0x2BE87F`
- tile IDs: `0x2BE880..0x2BE8BF`
- legacy byte-to-local index: `0x2BE8C0..0x2BE9BF`
- preparation local-index-to-slot: `0x2BE9C0..0x2BEABF`

The checked-in byte UI inventory is the authoritative character-to-slot
record.

## Current-candidate runtime acceptance

The hard candidate with MD checksum `5BE8` and SHA-256
`227e7a25818860ebd674d62bda3ca748901aaa45f0919c3eb1ae4340157742bd`
was launched on isolated display `:116`:

- `captures/run/hard_5be8_s03_shaman_hein_command.png`: Hein's commander
  panel shows `헤인 / 샤먼` intact.
- `captures/run/hard_5be8_s05_prep_detect_16.png`: the Scenario 5 commander
  arrangement list shows `쉐리` intact.
- `captures/run/hard_5be8_s05_enemy_roster.png`: the Scenario 5 enemy
  deployment list shows `웨어울프` and six simultaneous `울프맨` rows intact.
- `captures/run/hard_5be8_s03_guardman_status.png`: the map status bar shows
  `리아나 / 가드맨`, retaining the established `가` slot.
- `captures/run/hard_5be8_s03_pike_status.png`: the map status bar shows
  `제국지휘관 / 파이크`, retaining the established `제` and `크` slots.

The earlier checksum-`21B9` candidate established the retained Scenario 4
regressions:

- `captures/run/hard_21b9_s04_warlock_roster.png`: the Scenario 4 deployment
  list shows `샤먼` and four simultaneous `바바리안` rows intact.
- `captures/run/hard_21b9_s04_warlock_attempt5.png`: the same deployment list
  shows `워록` and six simultaneous `바바리안` rows intact.
- `captures/run/hard_21b9_s04_warlock_roster2.png`: the nearby `파이크` rows
  remain intact, covering the existing `크` slot while the new slots are
  active.

The hard-candidate delta verifier classifies all 578 changed bytes against the
released hard predecessor. It reports zero balance, event, or AI changes and
zero bytes outside the owned UI, sprite, checksum, and Loren-frame ranges.
The first 16 map cache slots retain their original order, so this preparation
expansion does not alter the independent map-bottom name/class fields.
The focused unit test separately locks the `적군` result record to its
dedicated dynamic result tile, covering the remaining reported `적` glyph.
