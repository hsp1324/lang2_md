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

## Scenario 4 acceptance on the class-change-fixed candidate

The renderer dispatch fix for the class-change mercenary rows changes one
non-checksum ROM byte at `0x2B7121`. Because that produces new normal and hard
candidate checksums, Scenario 4 was replayed on normal `76D1` and hard-profile
`D9B2`.

Both `classfix04` runs completed the real preparation -> shop item list ->
preparation sequence with 20/20 byte-identical full-screen pairs. They cover
three allied commander/status pages, three hiring pages, the allied roster,
arrangement and minimap screens, and all ten visible fixed-record detail
pages. All accepted preparation/shop frames match the already reviewed
pre-fix Scenario 4 pixels, and the normal/hard accepted frames match each
other. The hidden masked-knight record remains explicitly not applicable at
source coordinates `(255,255)`.

The battle-side gate also passes:

- actual movement sets Elwin/Fighter runtime group 0 to acted flag 1 at
  `(8,38)`;
- gray VRAM `0x9600..0x967F` exactly expands the stock Fighter silhouette
  `0x001E` and is referenced from Plane A;
- a stock Attack against Morgan reaches the same full-screen `전과보고`
  pixels in both profiles;
- result-header VRAM `0xA000..0xA1FF` has the expected hash and all 16 Plane A
  cells reference tiles `0x0500..0x050F`;
- the clear diagnostic changes only checksum, Elwin placement, and Morgan
  AT/DF/mercenaries while preserving the other deployments, all non-Morgan
  records, Morgan identity/coordinates, every Scenario 4 event byte, and the
  Korean result header.

The accepted report is
`localization/preparation_surface_scenario_04.json`. Its rejected-attempt
section records the missed scenario-selector window, the overshot result
capture, the resumable 60-second dialogue command limit, the incomplete
foreground `classfix01` run, and the two background-launch setup failures.
The cumulative gate now accepts Scenarios 1, 2, 3, 4, and 9 in both profiles;
Scenarios 5–8 and 10–27 remain pending. This is candidate validation only:
no release ROM or version was promoted.

Focused Scenario 4, preparation, shop, and class-change checks pass. Full
discovery runs 1,486 tests and retains exactly the preceding 44 failures plus
3 errors; the sorted failing/error test names are unchanged. They remain the
pre-existing experimental-sprite, hard-runtime/plan/generated-document,
item-inventory-current-ROM, and release-promotion gates rather than new
Scenario 4 regressions.

## Scenario 5 current-candidate closure

Normal `76D1` and hard-profile `D9B2` were replayed through Scenario 5 on the
class-change-fixed candidates. The accepted runs cover all five allied
commander/status pages, all five hiring pages, the allied roster, arrangement
and minimap, and every preparation-visible fixed record before and after one
real same-run shop item-list visit. Both profiles pass 19/19 exact full-screen
pairs. Every important preparation and shop frame is byte-identical between
the two profiles.

The source has nine fixed records. Records 0 through 4 are visible and were
each captured; records 5 through 8 are hidden at source coordinates
`(255,255)` and are individually recorded as not applicable. The accepted
frames keep Elwin, Hein, Scott, Liana, `쉐리`, every class and hired
mercenary, `웨어울프`, `울프맨`, Morgan, all imperial commanders, every
sprite, minimap row, border, and number intact before and after shop.

The battle-side gate also passes. Actual movement sets Elwin/Fighter to acted
flag 1 at `(14,51)`, and gray VRAM `0x9600..0x967F` exactly expands the stock
Fighter silhouette `0x001E` with all four tiles referenced from Plane A. For
the result path, the diagnostic changes only the checksum and Elwin's first
deployment Y from 50 to 1. A real Move Up crosses the stock north-escape
threshold; all nine fixed records, the other four player deployments, every
Scenario 5 event byte, and the Korean result header remain unchanged.

The stock completion naturally levels Sherry and opens all three class
choices. Both profiles have byte-identical frames for `로드` with
`파이크 / 솔저`, `호크나이트` with `그리폰`, and `세인트` with
`가드맨 / 파이크`; the corresponding magic rows, sprites, statistics, map,
and borders are intact. Both profiles then reach the same byte-identical
full-screen `전과보고`. The hard run has one additional Hein level-up page
before the same Sherry choices.

Rejected evidence is retained in the generated report. `current01` exposed a
detector bug where the five-row arrangement menu matched the broad
fixed-detail shape; the detector now distinguishes the panels by their right
edge and has a Scenario 5 regression test. `current02` and three gray launches
missed selector/title timing. One normal rightward move targeted a red-X tile
and left acted flag 0, so only the later southeast-move state is accepted. The
hard file named `class_candidate_01` is the extra Hein level-up page and is
explicitly rejected; `class_choice_01..03` are the accepted Sherry frames.

The checked report is
`localization/preparation_surface_scenario_05.json`. The cumulative gate now
accepts Scenarios 1, 2, 3, 4, 5, and 9 in both profiles. Scenarios 6–8 and
10–27 remain pending, including fresh complete verification of the
user-reported Scenario 11 corruption. No release ROM or version was promoted.

Focused Scenario 5, preparation, shop, class-change, and cumulative checks
pass 37/37. Full discovery runs 1,493 tests and retains exactly 44 failures
plus 3 errors. The sorted set of all 47 failing/error test names is identical
to the Scenario 4 baseline; no Scenario 5 test is in that set.

## Scenario 11 current-candidate closure

Normal `76D1` and hard-profile `D9B2` were replayed through the complete
Scenario 11 preparation surface. Each profile passes 27/27 exact full-screen
before/after pairs in one uninterrupted shop round trip. The matrix covers all
six allied commanders and hiring pages, both allied roster pages,
arrangement/minimap, and all ten preparation-visible fixed records. Fixed
record 10 is the only preparation-time exception and is source-locked at
`(255,255)`; it is recorded as not applicable in preparation and later appears
as the stock final reinforcement.

This is a complete allied/NPC/enemy enumeration, not a sample of the reported
screens. The visible fixed records are 제시카/소서러/솔저,
에그베르트/자베라/아머솔저, 호크나이트/그리폰,
어새신/버서커/파이크, both 메이지/다크엘프/파이크 rows,
소드맨/버서커, both 매직나이트/호스맨 rows, and
서펜나이트/리자드맨. Every commander and mercenary sprite, name/class row,
minimap cell, border, and numerical field remains intact before and after
shop in both profiles. This closes all three user-reported Scenario 11
gray-block screenshots on the current candidates.

Actual Move Down changes Elwin/Fighter to acted flag 1 at `(14,11)`. Gray
VRAM `0x9600..0x967F` exactly expands stock Fighter silhouette `0x001E`, and
all four gray tiles are referenced from Plane A in both profiles.

For result evidence, freshly rebuilt current-candidate safe-clear derivatives
retain the source scenario events and fixed side/name identities. The
unchanged D091 pre-final-battle GST from the previously verified stock
turn-event route was loaded without mutation under each derivative. A real
Sherry normal attack defeated source runtime group 16, rendered its
`제국군지휘관: 어째서…` line, all 18 captured victory transitions/dialogues,
and `전과보고 / POINT 3770P`. The final report is byte-identical between
normal and hard. Attempts that directly altered defeated flags, HP, position,
or GST battle bookkeeping reset and were rejected; no such experimental code
remains.

No class-choice selection occurs in the retained pre-final-battle state
because its six allied commanders have already passed the relevant class
boundary. Status/class rows are covered by the preparation matrix, while live
class-choice glyphs remain covered by Scenario 5 and the dedicated 팔랑크스 /
발리스타 regression.

The checked report is
`localization/preparation_surface_scenario_11.json`. The cumulative gate now
accepts Scenarios 1, 2, 3, 4, 5, 9, and 11 in both profiles. Scenarios 6–8,
10, and 12–27 remain pending. No release ROM or version was promoted.

Focused Scenario 11, Scenario 5, cumulative preparation, matrix, shop-overflow,
class-change, and diagnostic-builder checks pass 57/57. Full discovery runs
1,499 tests and retains exactly 44 failures plus 3 errors. The sorted set of
all 47 failing/error test names is identical to the established baseline; no
Scenario 11 test is in that set.

## Scenario 6 current-candidate closure

Normal `76D1` and hard-profile `D9B2` were replayed through the complete
Scenario 6 preparation surface with the screen-detected scenario selector.
Each profile passes 26/26 exact full-screen before/after pairs in one
uninterrupted shop round trip. The matrix covers all five allied commander
status and hiring pages, the allied roster, arrangement/minimap, and every
preparation-visible fixed record.

This is a complete allied/NPC/enemy enumeration. The allied rows are
엘윈/파이터/솔저, 헤인/워록/가드맨, 스코트/파이터/솔저,
리아나/클레릭/가드맨, and 쉐리/파이터/솔저. Fixed records 0 through 11
cover 아론/파이터/글래디에이터/솔저, three 주민/클레릭/시민 rows,
모건, every visible 제국지휘관, and all visible 소서러/샤먼/나이트/
파이터, 바바리안/파이크/다크엘프/호스맨 rows. Every name, class,
mercenary sprite, commander sprite, minimap cell, border, and numerical field
is intact before and after shop in both profiles. Fixed record 12 is the only
exception: the source 호크나이트 is hidden at `(255,255)` and is explicitly
recorded as not applicable during preparation.

Actual Move Right changes Elwin/Fighter to acted flag 1 at `(5,26)`. Both
profiles retain the stock Fighter gray-silhouette expansion hash at
`0x9600..0x967F`, and all four tiles are referenced from Plane A at the
expected map cells. The action-menu frame is byte-identical between profiles;
the post-action PNG animation phase differs, while the runtime record and gray
VRAM are identical.

The civilian-safe stock victory aftermath naturally levels Sherry and exposes
all three class choices. Both profiles have byte-identical full-screen frames
for `로드` with `파이크 / 솔저` and `힐 / 프로텍션`, `호크나이트` with
`그리폰` and `토네이도`, and `세인트` with `가드맨 / 파이크` and
`썬더 / 일루전`. Every class, mercenary, and magic label, sprite, statistic,
border, and background map pixel is intact.

The result diagnostic preserves every player deployment, all thirteen fixed
records, the scheduled-turn table and handlers, and the Korean result header.
Opening Start marks only runtime enemy groups 9 through 17 defeated; the stock
turn-end victory checks, complete civilian-safe aftermath, class change, and
`전과보고` renderer remain in control. Normal continued with Lord and hard
with Saint, so their final unit grids legitimately differ, but both retain the
same intact result-header VRAM and Plane A cells.

The legacy `battle-command` preset was discovered to ignore
`--scenario-number` and enter Scenario 1. The resulting `gray01` and
normal `result01` files are explicitly rejected and are not used by the
checked report. A normal selector miss that entered name entry (`result03`),
an overshot default class selection (`result04`), and later hard quicksave
reload attempts that reset are also retained as rejected attempts. Accepted
evidence uses `gray02`, normal `result02` plus `result05`, and hard
`result02`.

The checked report is
`localization/preparation_surface_scenario_06.json`. The cumulative gate now
accepts Scenarios 1, 2, 3, 4, 5, 6, 9, and 11 in both profiles. Scenarios 7,
8, 10, and 12 through 27 remain pending. No release ROM or version was
promoted.

Focused Scenario 6 diagnostic-builder and complete-surface checks pass 33/33;
the cumulative Scenario 6 plus acceptance set passes 39/39. Split full
discovery runs 1,508 tests and retains exactly the established 44 failures
plus 3 errors. The nine newly added Scenario 6 tests account for the increase
from 1,499, and no Scenario 6 test appears in the failure/error set.
