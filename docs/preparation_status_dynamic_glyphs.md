# Preparation/status dynamic glyph ownership

## Current Pike/Monk-safe full candidate (2026-08-01)

The current non-release candidates are normal checksum `CB53`, SHA-256
`00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371`,
and hard checksum `E15E`, SHA-256
`f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad`.
They keep the old visible title/version and are not release artifacts.

The user-reported B1.0.2 Monk fragment has an exact collision: released
battle slots 6 and 7 were `0x0370` and `0x0371`, the upper two cells of
Monk active frame 0 (`0x0370..0x0373`). The current battle pool is entirely
outside every ordinary mercenary active frame 0 (`0x0348..0x0387`), active
frame 1 (`0x0448..0x0487`), and acted-gray frame (`0x03B0..0x03EF`).

`tools/run_pike_acted_surface_probe.py` now verifies both colored animation
frames and the acted-gray frame for any ordinary mercenary. A diagnostic ROM
whose only non-checksum delta changes Fighter's hire unlock at `0x05EE12`
from Soldier to Monk exposes a real Monk without touching sprite, glyph,
cache, scenario, or battle code. Normal and hard both match the original ROM
sources for Monk tiles `0x0370..0x0373`, `0x0470..0x0473`, and
`0x03D8..0x03DB`, then perform a real move and change acted flag `0 -> 1`.
The exact report is `localization/monk_sprite_cache_regression.json`.

The full `pike-safe-full01` matrix passes all 54 Scenario 1..27 normal/hard
preparation runs, all 54 scenario identities, all 54 real gray movements,
both battle animation frames in 27/27 scenarios per profile, all 16 hireable
mercenaries on six pages, and pixel-exact `크로스`/`넥클리스`. Every new
preparation source and same-run pre/post-shop pair is SHA-256 identical to its
prior passed manual review. The current H-scroll gate passes 162/162 states.
Fresh debugger pairs around `0x2BEBC0..0x2BEC30` change only normal tile
`0x03CA` (`론`) or hard tile `0x07DB` (`쉐`), with zero H-scroll,
mercenary-cache, or other VRAM changes. The combined report is
`localization/current_candidate_surface_regression.json`.

The separate cumulative release gate remains pending for complete battle
results in Scenario 10 and Scenarios 12 through 27. No release/version
promotion is implied.

## Actual Pike acted-gray correction (2026-08-01)

The latest user correction identifies the affected unit precisely as the
hireable mercenary class `파이크` (`0x62`), not a generic spearman label. The
reported top-left Hangul fragment has an exact ownership explanation: Pike is
the first ordinary mercenary gray silhouette and owns tiles
`0x03B0..0x03B3` (VRAM `0x7600..0x767F`), while the prior battle dynamic
class/name pool also assigned slot 10 to `0x03B0`.

The non-release candidate now keeps all 16 battle name/class destinations out
of all three ordinary mercenary caches: active frame 0
`0x0348..0x0387`, active frame 1 `0x0448..0x0487`, and acted-gray
`0x03B0..0x03EF`. The destinations also avoid H-scroll
`0x07A0..0x07BF`. Preparation-only coloring cells may be used before sortie,
but the stock battle loader restores the complete gray cache before the map
is accepted.

`tools/run_pike_acted_surface_probe.py` reproduces the exact lifetime. It
enters Scenario 12, makes Sherry hire six real Pikes, automatically deploys,
moves member 1 from `(9,27)` to `(8,27)`, and verifies its acted flag changes
from 0 to 1. Normal checksum `CB53` and hard checksum `E15E` both produce the
same intact acted frame. Pike VRAM matches the original expanded silhouette
at SHA-256
`0fe0987d6d93be4842ad899ae0dedbf85f1342b86efc6957e53fde7f76aee0a8`,
and all four Pike tiles have live Plane A references.

The same two runtime states verify all 16 ordinary hireable gray silhouettes,
not only Pike. Every class in `0x62..0x71` matches its original source across
the full `0x03B0..0x03EF` cache both immediately after sortie and after the
Pike action. Hashes and exact state paths are recorded in
`localization/pike_acted_surface_regression.json`. These are candidates only;
no release/version promotion is made.

## Previous pre-Pike full-matrix and first-draw proof (2026-08-01)

The earlier non-release normal checksum `6693` / SHA-256
`3028bc7ab75240fdab35d7a09e5c147684173a04c6f9377f2496d72a796a7c05`
and hard checksum `19BD` / SHA-256
`16f496f887d0abfa2866081224d14870801532f283280aab303ff3a5a002fc14`
replaced still older probe hashes for that verification pass. The later Pike
cache correction above changes the dynamic destination table again, so these
hashes and first-draw tile positions are retained historical evidence rather
than acceptance for checksums `CB53`/`E15E`. They do not change the visible
release version and are not promoted release ROMs.

`tools/verify_preparation_hscroll_matrix.py` now validates all current
Scenario 1 through 27 preparation runs in both profiles. It checks the
hash-bound `pre_shop`, real `shop_item_list`, and `post_shop` GST for each
profile/scenario: 54 runs and 162 states total. Every state decodes VDP
register 11 as `0x00`, register 13 as `0x3D`, full-screen H-scroll base
`0xF400`, and zero nonzero bytes in `0xF400..0xF7FF`. All 26 current dynamic
tile addresses are outside that allocation. The checked report is
`localization/preparation_hscroll_current_candidate.json`.

The exact first preparation dynamic draw is also retained in normal and hard
GST pairs under `captures/analysis/preparation_first_draw_current`. Debugger
breakpoints bracket the preparation renderer entry `0x2BEBC0` and its final
`RTS` at `0x2BEC30`. BlastEm queues a requested GST until its next 68K
synchronization boundary, so the stored before PC is `0x2BEBF4`; its full
VRAM still contains the complete pre-draw tile. Across each before/after pair,
the complete 64KiB VRAM differs in exactly one aligned 32-byte tile:

- normal renders `쉐` only into owned tile `0x03C9` (`0x7920..0x793F`);
- hard renders `록` only into owned tile `0x07D1` (`0xFA20..0xFA3F`).

All other VRAM bytes and all VDP registers are identical. H-scroll remains
zero and byte-identical, and the fixed mercenary icon cache
`0x6900..0x70FF` is unchanged. The exact state hashes and reproducible checks
are in `localization/preparation_first_draw_current_candidate.json`, generated
by `tools/verify_preparation_first_draw.py`.

These results close the former preparation-glyph/H-scroll ownership question.
The overall release acceptance file intentionally remains pending only for its
separate battle-result coverage gaps; no release/version promotion is implied.

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

The B1.0.2 correction keeps 22 proven cache cells and relocates the four map
slots that a supplied Scenario 11 Genesis Plus GX state showed were also used
by visible unit graphics:

`0359 035B 0795 079C 036C 036D 0370 0371`

`079D 07E0 03B0 03BD 03C0 03C1 03C4 03C9`

`03CA 03D0 03D1 03D4 03D5 03D7 03D8 03DA 03DF 03E0`

Tiles `0x0795`, `0x079C`, and `0x079D` are in the physical gap between the SAT
and H-scroll tables; `0x07E0` is above H-scroll. None is inside live H-scroll
VRAM `0xF400..0xF7FF`. A recursive scan of 1,146 retained GST states found no
Plane A/B, Window, SAT, or VDP-table reference to those four replacements, and
the 31 pre-assignment preparation-like states retained one stable payload for
each. The stock full-screen H-scroll initializer at `0x0090A6` keeps its
original `MOVE.W #$00B7,D1`; the rejected `#$0007` shortening is not emitted.

The supplied B1.0.1 state reproduces the failure only after a cursor or menu
update. Its Plane A contains unit cells that reference `0x0360`, `0x0361`,
`0x037D`, and `0x037F`; the dynamic Hangul upload therefore replaced their
graphics with gray syllable blocks. The same state and twelve independent
controller-input probes remain intact after relocating only the four
corresponding cache slots. B1.0.2 deliberately leaves every other text,
design, and balance byte unchanged apart from its ROM header and checksum.

The B1.0.2 playtest then exposed the same ownership error on hiring screens:
dynamic slot 5 uploaded `가` to `0x036D`, which is also the left pattern of the
Ballista mercenary icon. B1.0.3 relocates that one slot to `0x07F0`. A recursive
scan of 1,151 retained GST states found no Plane A/B, Window, SAT, or VDP-table
reference to `0x07F0`; all 51 preparation-like states also retained one stable
pre-assignment payload there. B1.0.3 additionally corrects the independently
stored visible hard-build title from `1.0.1` to `1.0.3` while leaving the
translation version at `1.0.1`.

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

## Scenario 7 current-candidate closure

Normal `76D1` and hard-profile `D9B2` were replayed through the complete
Scenario 7 preparation surface. Each profile passes 27/27 exact full-screen
before/after pairs around one uninterrupted real shop item-list visit. The
matrix covers all six allied commander status and hiring pages, both allied
roster pages, arrangement/minimap, and every preparation-visible fixed
record. Every corresponding preparation and shop PNG is also byte-identical
between normal and hard.

The allied rows are 엘윈/파이터/솔저, 헤인/워록/가드맨,
스코트/파이터/솔저, 리아나/클레릭/가드맨, 쉐리/파이터/솔저, and
아론/파이터/솔저. The ten visible fixed records cover three
주민/클레릭/시민 rows, 기남/네크로맨서/좀비, two
제국지휘관/네크로맨서/스켈톤 rows, two
그레이트슬라임/그레이트슬라임/슬라임 rows,
제국지휘관/호크나이트/그리폰, and
제국지휘관/서펜나이트/리자드맨. Every name, class, commander and
mercenary sprite, minimap cell, border, and number is intact. Fixed records 3
and 11 are hidden at source coordinates `(255,255)` and are explicitly
recorded as preparation-time not applicable.

The shop page renders 라지실드, 그레이트소드, 갑옷, 체인메일, and 로브
without any glyph or row corruption. The same-run post-shop scans remain
byte-exact to the pre-shop scans.

Actual movement changes Elwin/Fighter to acted flag 1 at `(8,20)`. Both
profiles retain the exact stock Fighter silhouette expansion in gray VRAM
`0x9600..0x967F`; tiles `0x04B0..0x04B3` are referenced from Plane A at the
expected map cells. The action-menu PNG is byte-identical between profiles,
and the runtime record plus gray VRAM match exactly.

For completion, the existing source-validated Scenario 7 diagnostic moves only
Ginam from `(6,6)` to `(7,19)`, sets his AT/DF to zero, and removes his six
mercenaries. It preserves all player deployments, every non-Ginam fixed
record, resident-death events, the scheduled-turn table and handlers, and the
Korean result header. A real Elwin Attack then enters the unchanged
civilian-safe stock aftermath.

That aftermath naturally levels Sherry and exposes all three choices.
Normal and hard frames are byte-identical for `로드` with `파이크 / 솔저`
and `힐 / 프로텍션`, `호크나이트` with `그리폰` and `토네이도`, and
`세인트` with `가드맨 / 파이크` and `썬더 / 일루전`. Normal continued
with Saint and hard with Lord; both reach intact `전과보고 / POINT 1650P`
screens whose result-header VRAM and all 16 Plane A cells match.

The first normal command detector omitted its map-aware option and stopped on
the Scenario 7 banner without sending input. A later first attack attempt left
the target cursor on Elwin and returned to the command menu. Both attempts are
excluded. The accepted route uses the screen-detected selector, automatic
placement, map-aware command detection, and an explicit Up target movement to
Ginam. All input was sent directly to the isolated Xvfb `:104` window.

The checked report is
`localization/preparation_surface_scenario_07.json`. The cumulative gate now
accepts Scenarios 1, 2, 3, 4, 5, 6, 7, 9, and 11 in both profiles. Scenarios
8, 10, and 12 through 27 remain pending. No release ROM or version was
promoted.

Focused Scenario 7 diagnostic-builder, complete-surface, and cumulative
acceptance checks pass 38/38. Full discovery runs 1,514 tests with 50 failures
and 3 errors; no Scenario 7 test appears in that set. After normalizing test
module names against the prior 1,508-test baseline (44 failures and 3 errors),
the only name-set change is seven new failures and one resolved failure in the
concurrently modified `test_experimental_class_sprite_assets` module. The
Scenario 7 candidate/probe hashes remain byte-exact after the full run.

## Scenario 8 current-candidate closure

Normal `76D1` and hard-profile `D9B2` were replayed through the complete
Scenario 8 preparation surface. Each profile passes 28/28 exact full-screen
before/after pairs around one uninterrupted real shop item-list visit. The
matrix covers all seven allied status and hiring pages, both allied roster
pages, arrangement/minimap, and all nine preparation-visible enemy records.
Every corresponding normal/hard preparation and shop PNG is byte-identical.

The allied rows are 엘윈/파이터/솔저, 헤인/워록/가드맨,
스코트/파이터/솔저, 리아나/클레릭/가드맨, 쉐리/파이터/솔저,
아론/파이터/솔저, and 키스/호크나이트/솔저/그리폰. The visible enemy
rows cover 호크나이트/그리폰, 메이지/다크엘프/솔저,
매직나이트/호스맨, 크레이머/하이로드/솔저/파이크, and every repeated
제국지휘관 row. The shop keeps 대거 and 로브 intact. Every name, class,
commander and mercenary sprite, minimap cell, border, and numerical field
remains intact before and after shop.

Fixed records 9 and 10 begin hidden at source coordinates `(255,255)`, so
preparation alone is not treated as sufficient coverage. A second
source-validated diagnostic changes only Kramer's AT/DF, six mercenary bytes,
and coordinates, using DF 14. A real Elwin attack leaves Kramer at HP 1 and
enters the unchanged stock reinforcement event. It places unchanged source
record 9 as runtime group 16, `발가스/제너럴`, at `(2,11)`, and unchanged
source record 10 as runtime group 17, `조름/로드`, at `(3,8)`. Both profiles
show intact dialogue, portraits, names, classes, map sprites, status values,
and borders. Their runtime records are byte-identical across profiles.

Actual movement separately changes Elwin/Fighter to acted flag 1 at `(3,7)`.
Both profiles retain the exact stock Fighter silhouette expansion in gray
VRAM `0x9600..0x967F`; tiles `0x04B0..0x04B3` are referenced from Plane A at
`(18,13),(18,14),(19,13),(19,14)`.

For completion, the clear diagnostic uses the same isolated Kramer record with
DF 0. Normal checksum/hash are `CA44` /
`37b6fb0dd9051d79570698af656d0e015490106bafab7bb51fc86a48c04f8ec8`;
hard are `2D25` /
`9a73fd3d15c8a8c92fd3a4ae15d97e66dafebb7c6c21a2f26fff9f910f1609f6`.
The survival variants are `CA52` /
`ec033cabd835f9f384394aa812f207dd4804658e58ab36124dd7798e6bb934ea`
and `2D33` /
`e90a6d1306fa49eb1c1ee6845bcde872be28caee9d9bbbb39ad9927b0d9b6481`.
Both modes preserve every player deployment, every non-Kramer fixed record,
both hidden reinforcement records, the scheduled-turn table/handlers, and the
Korean result header.

The stock victory aftermath naturally exposes Sherry's three choices. Normal
and hard frames are pairwise byte-identical for
`로드 / 파이크 / 솔저 / 힐 / 프로텍션`,
`호크나이트 / 그리폰 / 토네이도`, and
`세인트 / 가드맨 / 파이크 / 썬더 / 일루전`. Normal continued with
Saint and hard with Lord; both reach intact `전과보고 / POINT 1760P` whose
header VRAM and all 16 Plane A cells match.

Normal `result01` is rejected because no accepted result GST survived before
a quicksave load reset to title. Hard `result01` missed the selector and
entered name entry. Normal `reinforcement01` used the DF-0 clear probe, killed
Kramer, and could not open the reinforcement branch. Accepted evidence uses
normal/hard `gray01`, `result02`, and `reinforcement02`.

The checked report is
`localization/preparation_surface_scenario_08.json`. The cumulative gate now
accepts Scenarios 1 through 9 and Scenario 11 in both profiles. Scenario 10
and Scenarios 12 through 27 remain pending. No release ROM or version was
promoted.

Focused Scenario 8 builder, status-probe, complete-surface, and cumulative
acceptance checks pass 50/50. Full discovery runs 1,523 tests with 51 failures
and 3 errors; no Scenario 8 test is in that set. The failures remain in
concurrently modified experimental sprite, hard-mode/runtime inventory, and
unchanged release-gate modules. Both accepted candidate hashes and the checked
Scenario 8 report remain byte-exact after the full run.

## 2026-08-01 glyph-lifetime candidate: complete preparation review

The released 1.0.2 build still reproduces the later user reports: `쉐리` can
initially appear as `제리`, `키스` can initially appear as `메스`, and the
`몽크` / `발리스타` hire rows can display Hangul-shaped blocks until another
selection redraws the surface. Those observations are release evidence, not a
failure of the replacement candidate described here.

The common cause was scratch-glyph lifetime, not incorrect commander or class
data. Tile references written by an earlier preparation page can remain live
while a later page uploads another glyph to the same pattern. The replacement
allocation colors 121 preparation-visible characters into 26 slots over
64,890 modeled surface contexts. It gives `쉐/제` and `키/메` distinct slots
and moves preparation scratch patterns away from the fixed mercenary icon
cache at tiles `0x0348..0x0387`. The checked static report has zero missing
characters and zero conflicts.

The current non-release candidates are:

- normal checksum `6693`, SHA-256
  `3028bc7ab75240fdab35d7a09e5c147684173a04c6f9377f2496d72a796a7c05`;
- hard checksum `19BD`, SHA-256
  `16f496f887d0abfa2866081224d14870801532f283280aab303ff3a5a002fc14`.

Every Scenario 1 through 27 preparation run was freshly bound to its runtime
scenario identity and reviewed in both profiles. The aggregate report
`localization/preparation_manual_review_current_candidate.json` passes 27/27
normal and 27/27 hard runs. It verifies every available allied status/hiring
page, arrangement roster/minimap, and preparation-visible allied, NPC, and
enemy fixed-detail page. All same-run pre/post-shop pairs are byte-identical;
the contact sheets, source captures, evidence files, and accepted gray-sprite
captures are SHA-256 bound. Scenario 3 uses the corrected run
`glyph-lifetime-s03-corrected01`; the verifier rejects the earlier run that
actually entered Scenario 1.

Direct inspection confirms that Scenario 5 first displays `쉐리` and Scenario
8 first displays `키스` without a corrective cursor move. A synthetic isolated
commander separately exposes every one of the 16 mercenary hire rows across
six pages. Both profiles pass, their pages are byte-identical, and no fixed
mercenary icon tile contains a dynamic Hangul payload. In particular,
`팔랑크스`, `발리스타`, and `몽크` plus their sprites are intact.

Fresh shop probes are pixel-exact to the accepted `크로스` / `넥클리스`
frames in normal and hard. Fresh class-change captures cover all three
`메이지 -> 그랑나이트 / 실버나이트 / 아크메이지` candidates and retain
both `팔랑크스` and `발리스타`; corresponding normal/hard frames are
byte-identical. The updated evidence is hash-locked in
`localization/class_change_mercenary_glyph_regression.json`.

Actual movement in all 54 Scenario 1..27 profile runs changes the unit
coordinate and acted flag, then produces the stock gray silhouette rather
than a Hangul block. The independent battle-cache check covers Scenarios
1..31 in both profiles and matches both animation frames of every cached
mercenary against the candidate ROM source.

This closes the currently reported preparation/name/mercenary/shop/gray-sprite
corruption on the candidate. It does not promote a release or version. The
formal cumulative release gate remains pending because complete battle-result
acceptance for Scenario 10 and Scenarios 12 through 27 is separate from this
complete preparation-surface review. The expanded related focused suite,
including the 162-state H-scroll matrix and first-draw GST delta gates, passes
114/114. The five added cache-reuse checks lock the ordinary enemy mercenary
path used by the all-scenario gray/battle-sprite regression.

## 2026-08-02 current-source revalidation

The late-ally tier-1/LV10 progression change and the battle target-cursor tile
separation landed after the prior preparation candidate was captured. Separate
non-release audit ROMs were therefore rebuilt from the current working source:

- normal checksum `015C`, SHA-256
  `eaee0b0443140776a6ad7ae4542a9b41a132ac7c19c4b4b127a61de8b8d74c27`;
- hard checksum `1767`, SHA-256
  `5b391ad132553427d2ededf01651d6215a71ce60dc8e1f0cacb1e45419a17f8a`.

`tools/run_full_surface_regression.py` used six isolated workers per profile,
up to twelve simultaneous BlastEm instances, for Scenarios 1 through 27. All
54 preparation runs and all 54 real-movement gray-acted runs passed. The
preparation runs contain 733 same-run pre/post-shop pairs per profile; every
one of the 1,466 new pairs is byte-identical and every source surface is
SHA-256 identical to its previously reviewed counterpart. The hash-exact
review transfer therefore passed all 27 scenarios in both profiles and is
recorded in `localization/preparation_manual_review_current_candidate.json`.

The same current-source run passes all 16 mercenary hire rows, both Pike
profiles with six hired Pikes and a real move, both isolated Monk active/acted
profiles, Cross/Necklace shop rows, both mercenary animation frames in all
27 scenarios per profile, the 64,890-context zero-conflict allocation, and all
162 H-scroll GST states with zero nonzero bytes. The consolidated evidence is
`localization/current_candidate_surface_regression.json` and the orchestrator
summary is
`tmp/full_surface_regression/current-source-20260802-01/summary.json`.

The retained first-draw debugger GSTs are not relabeled as fresh current-ROM
captures. Instead,
`localization/preparation_first_draw_current_applicability.json` verifies the
recorded source ROM/GST hashes and proves that the dynamic glyph payloads,
preparation slot table, preparation VDP commands, preparation tile IDs, and
preparation renderer are byte-identical in both current audit ROMs. The
battle-only cursor-table change is outside that preparation lifetime contract.
No release ROM, save, version, or desktop artifact was changed. Full
battle-result acceptance for Scenario 10 and Scenarios 12 through 27 remains
the separate pending release gate.
