# Preparation/status dynamic glyph ownership

> **2026-07-31 correction:** the ownership claim below is no longer accepted.
> User captures from Scenario 9 show both gray Hangul-like blocks and severe
> right-side minimap row shifts on the preparation/deployment surface. These
> symptoms are consistent with `0x07A1..0x07BC` overlapping a live H-scroll
> table. The earlier Plane/Window/SAT scans did not cover VDP consumption of
> H-scroll entries. Do not extend this allocation or treat the FBE2/B2A4
> captures as complete runtime acceptance. The replacement investigation and
> exact stop point are recorded in
> `docs/session_handoff_2026-07-31.md`.

## Replacement pattern pool probe (2026-07-31)

The collision is now proven from the retained GST format rather than inferred
from screenshots. BlastEm stores VDP registers at file offset `0xFA` and VRAM
at `0x12478`. In
`captures/analysis/hard_fbe2_s06_after_shop_enemy_detail.gst`, register 11 is
`0x00`, register 13 is `0x3D`, and therefore the live H-scroll allocation is
VRAM `0xF400..0xF7FF`. Every former dynamic tile `0x07A1..0x07BC` resolves
inside that exact byte range. Five populated ranges contain 192 nonzero bytes
of Hangul patterns. The old cache was not an unused pattern bank.

The builder probe replaces all 26 cache cells with noncontiguous ordinary
pattern tiles:

`0359 035B 0360 0361 036C 036D 0370 0371`

`037D 037F 03B0 03BD 03C0 03C1 03C4 03C9`

`03CA 03D0 03D1 03D4 03D5 03D7 03D8 03DA 03DF 03E0`

Their byte addresses are below `0xC000`. A read-only ownership scan of the 384
pre-replacement GST files found no Plane A, Plane B, Window, SAT, or VDP-table
ownership for any selected tile. Across the 31 preparation-like retained
states, every selected cell had one stable pre-assignment payload. The stock
full-screen H-scroll initializer at `0x0090A6` again keeps its original
`MOVE.W #$00B7,D1`; the rejected `#$0007` shortening is no longer emitted.

`tools/analyze_preparation_vram_ownership.py` reproduces the register decode,
historical collision, ownership scan, and runtime comparison. Its checked
report is `localization/preparation_vram_ownership.json`.

The first full normal Scenario 1 run against the 24-cell probe found one real
missed glyph: `로얄호스` used static `얄` tile `0x03AC`, and only that 8x8
pattern changed after the shop. `얄` is now preparation slot 24 at audited
ordinary pattern tile `0x03DF`. The original 3203/7B41 probes are superseded.

The later all-scenario surface inventory showed that every static Hangul
extension range can also be occupied by commander or mercenary graphics.
Preparation therefore loads only the stock byte font and routes 121 unsafe
characters through 26 conflict-colored slots. Characters share a slot only
when the Scenario 1–27 commander, hiring, fixed-detail, and class-change
inventory proves that they never appear on the same surface.

Current combined non-release probes only:

- normal checksum `7621`, SHA-256
  `4abcfaaab868739f60d8c2ff13f9c462169e6c318285fecb7889688d22c7f03c`;
- hard checksum `D902`, SHA-256
  `fe6c710cfc671c0fc08badb7a1a486e5b33a93fe9c55632f3ebda3c2f6912e78`.

### Class-change mercenary tile-renderer correction

A later user capture showed `팔랑크스` and `발리스타` losing their shared
`스` on the Arch Mage class-change detail. The conflict-colored slot plan
already included `스`; the missed path was the tile renderer used by
class-change mercenary calls `0x02C004` and `0x02C040`. It still used the
ordinary static local-tile lookup after candidate graphics had reused those
patterns.

`_build_byte_ui_tile_renderer()` now calls the preparation local-tile lookup.
Fresh normal and hard `메이지 -> 그랑나이트 / 실버나이트 / 아크메이지`
probes render all three choices and both Arch Mage mercenary rows intact. The
six passing frames are byte-identical across profiles and are recorded in
`localization/class_change_mercenary_glyph_regression.json`. The replacement
normal and hard-profile probes are checksums `76D1` and `D9B2`. Neither is a
release promotion.

Scenario 9 now has complete acceptance evidence in both profiles. Each run
passes 32/32 same-run pre/post shop full-screen pairs: seven allied commanders
over two roster pages, all hiring pages, both arrangement pages, and all 13
visible fixed details. Normal and hard also have intact gray acted-sprite
captures and actual Elwin/Hein attacks that invoke the stock death/victory
path and reach intact result screens. The checked evidence is
`localization/preparation_surface_scenario_09.json`.

Scenario 1 has a reviewed preparation pass in both current probes. Normal run
`normal/s01/yal02` and hard run `hard/s01/yal01` under
`captures/run/preparation_surface_matrix` each produce 14/14 byte-identical
full-screen pairs across every allied status/hiring page, the arrangement
roster/minimap, all six visible fixed records, and a real shop item-list round
trip. Commander, class, mercenary, sprite, minimap, border, and numeric fields
were visually reviewed.

Both runs automatically save pre/post `로얄호스` GST checkpoints. In all four
states, tile `0x03DF` exactly matches the candidate-ROM `얄` bitmap, Plane A
cell `(7,8)` contains tile word `0x83DF`, and H-scroll
`0xF400..0xF7FF` contains zero nonzero bytes. The checked report is
`localization/preparation_surface_matrix.json`; it is reproduced by
`tools/verify_preparation_surface_evidence.py`.

Separate normal/hard battle runs under
`captures/run/preparation_battle_surface` complete Scenario 1. After an actual
Move command, runtime group 0 is Elwin/Fighter with acted flag 1 at `(12,17)`.
VRAM `0x9600..0x967F` has SHA-256
`74e404c1c9dad9a31578fcdf25c61158ade1fdb43221941c7b2c3f6e19313b22`
and exactly matches the stock Fighter silhouette ID `0x001E` expanded by the
original two-bit renderer. Plane A references its four tiles at
`(20,11)..(21,12)`.

Both profiles also traverse the stock victory event into the full
`전과보고` surface. The two result PNGs are byte-identical, retain the Korean
header, `아론/엘윈/헤인/리아나`, all result sprites, POINT, borders, rows,
and numerical fields. The normal/hard result diagnostics change only Bald's
AT/DF, coordinate, mercenary setup, and the checksum; the result header and
event code remain candidate-identical. The preserved seed exposes no live
class-change choice, so that surface is explicitly not applicable with a
written reason. Scenarios 1, 2, 3, and 9 are now fully accepted; Scenarios
4–8 and 10–27 remain mandatory.

Failed attempts retained for future work:

- the hard-mode builder rejected an output directly under `/tmp`, then rejected
  a relative `tmp/...` path because its manifest requires an absolute path
  below the repository root; the third absolute repository-local probe path
  succeeded without replacing a release;
- a debugger breakpoint at `0x2B7300` did stop immediately before the first
  dynamic write, but the direct debugger used the default native state format
  and produced `quicksave.state`, not the required GST. It is not acceptance
  evidence;
- normal Scenario 1 attempts `canonical01..canonical10` were rejected for
  incomplete pairs, focus/arrangement navigation failures, one accidental
  Soldier hire, repeated fixed records, or mismatched screens. `canonical10`
  is the useful failure that exposed the missing `얄` ownership;
- a later attempt to load `pre_shop.gst` and manually recreate the Leon
  checkpoint unexpectedly deployed. It produced no accepted pre-checkpoint.
  The clean normal `yal02` and hard `yal01` runs replace that attempt by
  saving both checkpoints inline without loading state.

Validation for the original 24-cell stable unit:

- the focused preparation/ownership/inventory suite passes 46/46, including
  the Scenario 6 evidence hash lock;
- 422 diagnostic-ROM checksum tests pass after rebasing their expected MD
  checksums by the uniform `+0x18A7` caused by the common builder change;
- the full suite runs 1,440 tests and ends at 44 failures plus 3 errors. The
  original run had 92 failures plus 3 errors, so every one of the 48
  preparation-induced checksum failures is resolved. The remaining failures
  are in the concurrently dirty hard-runtime/plan manifests, experimental
  sprite assets, unchanged release-ROM/report gates, item/shop inventory, and
  generated runtime documentation. They are not promoted to passes here.

No release ROM or version was changed to silence those remaining gates.

Validation for the 25-cell Scenario 1 evidence unit currently passes 61/61
focused tests covering the builder allocation, byte inventory, ownership
report, matrix plan/navigation, candidate hashes, exact screenshot pairs,
human-review state, all four preparation GST checkpoints, the acted runtime
record and gray-payload expansion, and the battle-result header/delta proof.
Full discovery runs 1,455 tests in four time-bounded groups and remains at the
same 44 failures plus 3 errors as the preceding stable unit. No new checksum
cascade was introduced; the remaining failures are the existing
experimental-sprite, hard-runtime/plan/generated-document, release-promotion,
and inventory gates.

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
- Entering the shop and returning to Scenario 6 deployment overwrote the first
  syllable of every visible `글래디에이터` row. The same current-candidate
  round trip retained `쉐리`, proving that `글` was the remaining unprotected
  static-extension glyph rather than a corrupted name or class record.

The user confirmed that `워록` and `바바리안` remain intact in the map-bottom
information panel. The class/name table records are therefore correct; the
failure belongs to the preparation/status tile lifetime.

The shop-round-trip reproduction also exposed a missed renderer path. The
shared word renderer used by deployment, hiring, and class-change rows still
called the ordinary static local-tile lookup, even though every other
preparation renderer called the preparation lookup. It now uses the same
preparation lookup, and the focused regression test enumerates that renderer
alongside the roster, panel, status, selected-name, selected-panel, and
hire-class renderers.

## Historical H-scroll scratch ownership (rejected)

The first 16 entries of `BYTE_UI_DYNAMIC_TILE_IDS` remain the two established
eight-cell map fields. They are not reordered:

- slots 0..7: selected unit name
- slots 8..15: selected unit class

Preparation/status rendering also uses fixed slots because several rows can
remain visible simultaneously. The existing 16 slots cover:

`라 론 쉐 카 코 키 록 적 가 스 럴 슬 임 비 크 제`

Eight additional preparation-only slots cover:

`샤 먼 안 께 울 끼 의 글`

They use VRAM tile IDs `0x07AA`, `0x07AB`, `0x07AC`, `0x07B6`, `0x07B7`,
`0x07B9`, `0x07BB`, and `0x07BC`. These patterns are in the unused tail of the
full-screen H-scroll table, like the established map cache. The first three
passed the earlier 286-state ownership scan. A broader read-only scan of 696
retained GST runtime states found zero Plane A, Plane B, window, or map-SAT
references to all seven IDs before assignment. Tile `0x07A0` remains reserved
for the active H-scroll word, and cursor-owned `0x07BE..0x07BF` remain
excluded.

Before assigning `0x07BC`, a new conservative scan covered all 750 retained
GST states and every 16-bit entry in the conventional Plane/Window/SAT VRAM
tail (`0xC000..0xFFFF`). It found zero references to tile `0x07BC`; nearby
unassigned candidates `0x07AE`, `0x07B2`, `0x07B8`, `0x07BA`, and `0x07BD`
all had retained references and were rejected.

The expansion tables now reserve capacity for 32 scratch slots:

- VDP commands: `0x2BE800..0x2BE87F`
- tile IDs: `0x2BE880..0x2BE8BF`
- legacy byte-to-local index: `0x2BE8C0..0x2BE9BF`
- preparation local-index-to-slot: `0x2BE9C0..0x2BEABF`

The checked-in byte UI inventory is the authoritative character-to-slot
record.

## Historical FBE2/B2A4 text evidence (invalidated for full-screen acceptance)

The hard candidate with MD checksum `FBE2` and SHA-256
`99a518338269e971bcdbf65b354be5d0109556967afe87b4161dfbd6448800a9`
was launched on isolated display `:104`. The normal candidate has MD checksum
`B2A4` and SHA-256
`78d6ee610b44eb2b657998d112b45c7bebbe91ba11e20a1976dea18bcb384776`.

Both candidates completed the exact Scenario 6 preparation -> shop -> item
list -> preparation -> enemy deployment round trip:

- `captures/run/normal_b2a4_s06_enemy_detail_after_shop.png`
- `captures/analysis/normal_b2a4_s06_after_shop_enemy_detail.gst`
- `captures/run/hard_fbe2_s06_enemy_detail_after_shop.png`
- `captures/analysis/hard_fbe2_s06_after_shop_enemy_detail.gst`

The shop still overwrites the old static `글` tile `0x04AE`, which proves the
original destructive transition occurred. In both retained GST states, the
three visible `글래디에이터` rows instead reference dynamic tile `0x07BC` at
Plane A offsets `0xC40C`, `0xC50C`, and `0xC60C`. Tile `0x07BC` is an exact
match for the Galmuri7 `글` pattern.

The same-run gate now also covers the preparation roster and class-change
surface in both builds:

- `captures/run/normal_b2a4_class_probe_after_shop_return.png` retains `쉐리`;
- `captures/run/normal_b2a4_class_change_candidate1_after_shop.png` retains
  `쉐리`, `메이지`, `엘프`, and `글래디에이터`;
- `captures/run/hard_fbe2_class_probe_sherry_after_shop.png` retains `쉐리`;
- `captures/run/hard_fbe2_class_probe_candidate1_after_shop.png` retains
  `쉐리`, `메이지`, `엘프`, and `글래디에이터`.

The corresponding class-change states are
`captures/analysis/normal_b2a4_class_change_after_shop.gst` and
`captures/analysis/hard_fbe2_class_change_after_shop.gst`. Only the dedicated
mercenary-hiring `글래디에이터` row remains
`pending_same_run_before_after_capture` for each build. A class-change capture
that happens to contain the same word does not substitute for that surface.

Scenario 7 was then entered on the same hard candidate, the real shop item
list was opened, and enemy deployment was inspected after returning:

- `captures/run/hard_fbe2_s07_ginam_after_shop.png` retains
  `기남 / 네크로맨서 / 좀비`;
- `captures/run/hard_fbe2_s07_imperial_necromancer_after_shop.png` retains
  `제국지휘관 / 네크로맨서 / 좀비`;
- `captures/analysis/hard_fbe2_s07_after_shop_enemy_detail.gst` retains the
  post-shop state.

The distant `그레이트슬라임` and `서펜나이트 / 리자드맨` records still
need fresh coordinate captures. Directional input became unreliable while
button input continued working, so repeated captures of the same record were
rejected rather than mislabelled as evidence.

Scenario 7 mercenaries that are listed during deployment but are absent on the
opening player turn appear during the first enemy turn. The user confirmed
this is the original event timing. It is explicitly excluded from defect
scope in `localization/preparation_status_dynamic_glyphs.json`.

The current hard candidate also retains the earlier acceptance captures:

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
