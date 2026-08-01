# Session handoff: preparation/deployment VRAM corruption

Date: 2026-07-31

## Stop point

The active Goal is intentionally left paused. Do not mark it complete or
blocked. Resume the same Goal in the next Codex session, then read this file
and the final section of `HANDOFF.md` before changing ROM bytes.

The current branch is `main` at `eea9a936c7ae10596d158f6d69572c02bb18604b`.
The worktree is heavily dirty and is shared with concurrent hard-mode and
sprite-design work. Do not reset, revert, or broadly stage it.

No release ROM was replaced and no version was bumped in this session.

## New accepted user evidence

Scenario 9 reproduces the same preparation/deployment corruption already seen
in Scenarios 3 through 7:

- `/mnt/c/Users/hsp13/Desktop/화면 캡처 2026-07-31 022045.png`
  shows gray Hangul-like blocks over the result/summary unit sprites.
- `/mnt/c/Users/hsp13/Desktop/화면 캡처 2026-07-31 022141.png`
  shows vertical gray Hangul-like blocks over commander and mercenary labels.
  The right-side minimap is also split and shifted into unrelated rows.

This is systemic and not a bad Scenario 9 name record. The minimap damage is
strong evidence that the preparation-only dynamic glyph patterns at VRAM tile
IDs `0x07A1..0x07BC` overlap a live H-scroll table or another live preparation
graphics region. Static Plane A/B/window/SAT reference scans did not prove
these cells safe because H-scroll entries are consumed by the VDP without
appearing as ordinary tile references.

Scenario 7 mercenaries appearing during the first enemy turn are confirmed
stock event timing. Do not investigate or change that behavior.

## Invalidated assumption

`docs/preparation_status_dynamic_glyphs.md` previously described
`0x07A1..0x07BC` as an unused full-screen H-scroll tail and treated the FBE2
and B2A4 preparation captures as runtime acceptance. The Scenario 9 evidence
invalidates that ownership assumption. Those captures only proved that the
requested glyphs appeared at the sampled moment; they did not prove that the
scroll/minimap state remained intact.

Do not add another `0x07xx` scratch slot and do not extend the H-scroll-tail
scheme. Downgrade the old acceptance evidence until a replacement allocation
passes complete-screen comparison.

## Current implementation under investigation

Relevant code is in `scripts/build_korean_jp_probe.py`:

- `BYTE_UI_DYNAMIC_MAP_TILE_IDS`
- `BYTE_UI_PREP_EXTRA_TILE_IDS`
- `BYTE_UI_PREP_DYNAMIC_CHARS`
- `_build_byte_ui_dynamic_glyph_renderer()`
- `_build_byte_ui_prep_local_tile_lookup()`
- `_build_byte_ui_word_renderer()`
- `BYTE_UI_FULL_SCROLL_HSCROLL_FILL`

The current preparation slots are:

`라 론 쉐 카 코 키 록 적 가 스 럴 슬 임 비 크 제 샤 먼 안 께 울 끼 의 글`

The most recent dirty change also routes the shared word renderer through the
preparation lookup and adds `글` at tile `0x07BC`. This change may expose the
collision more often but the unsafe ownership predates it.

## Required next steps

1. Reproduce on an isolated virtual display and save GST immediately before
   and after the first preparation dynamic-glyph draw.
2. Decode the GST VDP registers, especially H-scroll mode and H-scroll table
   base, and compare the complete `0x10000` VRAM image before/after.
3. Prove which writes generate the minimap row shifts. Do not infer safety
   only from plane/SAT scans.
4. Allocate preparation glyphs in a genuine pattern/font region or use a
   surface-local pool whose lifetime is proven. Do not move them to a nearby
   H-scroll address.
5. Build non-release normal and hard probes.
6. Verify complete-screen integrity before/after a real shop round trip in
   preparation, hiring, class change, enemy deployment, and result screens.
   Include the minimap and unit sprites, not only text crops.
7. Re-run focused tests, update the ownership inventory and documentation,
   then commit and push only the verified localization unit.

The dedicated mercenary-hiring `글래디에이터` row is still not validly
accepted. It must be checked again after the allocation is replaced.

After the replacement is stable, complete the mandatory Scenario 1 through 27
matrix in `localization/preparation_surface_acceptance.json`. Every scenario
must verify commander names, class names, and all offered mercenary names both
before and after a same-run shop visit. Full-screen sprite and minimap
integrity is part of the gate; text-only crops are insufficient.

## Runtime cleanup

This session used BlastEm PID `658741` on Xvfb display `:116` with the
non-release ROM
`roms/builds/Langrisser II (Korean Hard Shop Class Change Probe).md`.
The next session should start a fresh isolated runtime rather than relying on
that process or its in-memory state.

## Continuation update: replacement probe

The old ownership hypothesis is now disproven from the GST layout itself.
BlastEm stores VDP registers at GST offset `0xFA` and VRAM at `0x12478`.
Retained FBE2 reports register 11 `0x00`, register 13 `0x3D`, and therefore a
live H-scroll allocation at VRAM `0xF400..0xF7FF`. Every former dynamic tile
`0x07A1..0x07BC` falls inside it; 192 nonzero bytes in the retained table are
Hangul patterns.

The builder moves all 24 cells to audited noncontiguous ordinary
pattern tiles `0x0359..0x03DA` and restores the source `#$00B7` full-scroll
fill count. The exact list and reproducible proof are in
`localization/preparation_vram_ownership.json` and
`tools/analyze_preparation_vram_ownership.py`.

Non-release probes:

- normal `3203`,
  `01cb379c494bf1bcf3324ddd5b11505d7e3648c2817a6a3802bf113802b223cd`;
- hard `7B41`,
  `059900b4b95a023bb95d4cd75197a0aabd7f7244cb4db2fc782fda3557a4cdf7`.

Scenario 9 normal/hard preparation, arrangement/minimap, and enemy-detail
full-screen PNGs are byte-identical before and after a real shop item-list
round trip. The new H-scroll table remains entirely zero in retained evidence.
Hard Scenario 6 passed the same targeted route. These are partial probes only:
the full Scenario 1..27 all-page commander/class/hiring and sprite/result
matrix is still pending, so do not mark either scenario or the Goal complete.

The first-draw debugger breakpoint was reached at `0x2B7300`, but that direct
debugger saved native `quicksave.state` rather than GST. Do not treat it as
acceptance evidence; an exact first-draw before/after GST pair remains pending.
No release ROM was replaced and no version was changed.

This paragraph is historical and is superseded by the 2026-08-01 continuation
below. The current preparation-specific renderer is `0x2BEBC0`, not the old
map renderer at `0x2B7300`.

Validation after the replacement:

- focused preparation/ownership/inventory checks: 46/46 pass;
- diagnostic ROM checksum locks affected by the common builder delta: 422/422
  pass after the uniform `+0x18A7` rebase;
- full suite: 1,440 tests, 44 failures and 3 errors remain. The first run had
  92 failures and 3 errors. The eliminated 48 failures were the checksum
  cascade from this builder change. Remaining failures belong to concurrent
  hard-runtime/plan state, experimental sprites, intentionally unchanged
  release artifacts/inventories, and generated runtime documentation.

## Continuation update: Scenario 1 matrix and `얄` slot

The preparation matrix is now automated by
`tools/run_preparation_surface_matrix.py`. It uses an isolated runtime and
the preserved Scenario 27 manual-slot GST, enters Scenario 1 through the real
selector, visits both allied status and actual hiring pages, the arrangement
roster, every visible fixed record in source order, a real shop item list, and
then repeats every page in the same process.

Normal attempts `canonical01..canonical10` were retained as rejected
diagnostics. They exposed missed input/focus transitions, one accidental
Soldier hire, repeated fixed-record captures, and finally a real rendering
regression: `canonical10` was 13/14 exact because the static `얄` pattern in
`로얄호스` changed after the shop.

The builder now adds `얄` as preparation slot 24 at ordinary pattern tile
`0x03DF`, bringing the pool to 25 tiles. A read-only scan over 384 retained
GSTs found no Plane/Window/SAT reference or VDP-table ownership for the cell;
31 preparation-like states kept one stable pre-assignment payload. Current
non-release probes are:

- normal B0DF,
  `f141cc13efbf14a421876c520cca7d788b843bd382e52801ad0c989de5d7ce9a`;
- hard FA1D,
  `1d0ffd02e90dcf3b704934aa09d2336bdc65b8968ae0ed49db89bc400a35df32`.

Clean accepted preparation runs are
`captures/run/preparation_surface_matrix/normal/s01/yal02` and
`captures/run/preparation_surface_matrix/hard/s01/yal01`. Each has 14/14
byte-identical full-screen pairs and passed visual review for all Korean
commander/class/mercenary labels, sprites, minimap rows, borders, and numeric
fields. Both automatically retain pre/post Leon GST states. All four states
match the candidate-ROM `얄` payload at `0x03DF`, reference `0x83DF` from
Plane A `(7,8)`, and keep H-scroll `0xF400..0xF7FF` entirely zero.

`localization/preparation_surface_matrix.json` is the checked evidence report
and `localization/preparation_surface_review.json` records the human review.
The acceptance file marks only check-level preparation progress. Scenario 1
normal/hard remain pending because gray acted sprites and battle-result
screens need a separate battle run; the seed has no live class-change choice.
No release ROM/version was changed.

Focused validation passes 59/59. Full discovery runs 1,453 tests and ends at
44 failures plus 3 errors, exactly the same failure/error counts as the
preceding 24-cell stable unit. The remaining failures are in concurrently
dirty experimental sprites, hard runtime/plan/generated documentation,
unpromoted release/report gates, and item/shop inventory; the `얄` addition
introduced no new checksum cascade.

## Continuation update: Scenario 1 battle surfaces

Scenario 1 is now complete in both current non-release profiles. Actual Move
commands produced gray Elwin/Fighter captures and GSTs under
`captures/run/preparation_battle_surface/{normal,hard}/s01/gray01`. Runtime
group 0 has class 1, commander 1, acted flag 1, and coordinate `(12,17)`.
VRAM `0x9600..0x967F` exactly matches the software expansion of source
silhouette ID `0x001E`; the four tiles are referenced from Plane A.

Separate adjacent, unguarded Bald diagnostics preserve the result header and
event code and change only the fixed Bald AT/DF, coordinate, mercenary bytes,
and ROM checksum. Normal checksum `4B7D` and hard checksum `92BA` both traverse
the stock victory event to the same full-screen `전과보고` PNG. The Korean
header, `아론/엘윈/헤인/리아나`, all result sprites, POINT, borders, rows,
and numerical fields are visually intact. Result GSTs are retained beside
each capture.

`tools/verify_preparation_surface_evidence.py` now proves the battle-capture
hashes, acted runtime record, exact gray-payload expansion, Plane A tile
references, result header tile cells, and diagnostic ROM delta. Its checked
report marks Scenario 1 as the sole fully accepted scenario in
`localization/preparation_surface_matrix.json`. The overall release gate
remains pending because Scenarios 2 through 27 still require both profiles.
No release ROM or version was changed.

Focused Scenario 1 preparation/battle validation passes 61/61. Full discovery
was split into four groups to stay within the command runtime limit: 277,
413, 395, and 370 tests, or 1,455 total. The result remains exactly 44
failures plus 3 errors. All 44/3 are the pre-existing experimental-sprite,
hard-runtime/plan/generated-document, release-promotion, and inventory gates;
the two new battle-evidence tests pass.

## 2026-08-01 continuation: current first-draw and full H-scroll matrix

The old `0x2B7300` native-state attempt is superseded. Current preparation
dynamic rendering uses `0x2BEBC0..0x2BEC31`. Entry/final-RTS debugger stops
produced normal and hard GST pairs under
`captures/analysis/preparation_first_draw_current`. BlastEm services a queued
save at its next 68K synchronization boundary, so the before GST PC is
`0x2BEBF4`, but its complete VRAM still contains the full pre-draw tile.

Across each before/after pair, exactly one aligned 32-byte tile changes in all
64KiB VRAM: normal writes `쉐` only to tile `0x03C9`; hard writes `록` only to
tile `0x07D1`. All other VRAM, all VDP registers, H-scroll
`0xF400..0xF7FF`, and mercenary icon cache `0x6900..0x70FF` are unchanged.
`localization/preparation_first_draw_current_candidate.json` records the exact
GST hashes and is reproduced by `tools/verify_preparation_first_draw.py`.

The all-scenario gate is now direct rather than inferred from the sampled
Scenario 1/9 states. `tools/verify_preparation_hscroll_matrix.py` checks the
hash-bound pre-shop, real shop item-list, and post-shop GST for all Scenario 1
through 27 normal/hard runs: 54 runs and 162 states. Every state has VDP
register 11 `0x00`, register 13 `0x3D`, H-scroll base `0xF400`, zero nonzero
H-scroll bytes, and no current dynamic tile inside the table. Checked report:
`localization/preparation_hscroll_current_candidate.json`.

The later Pike/Monk cache correction supersedes that checkpoint. The current
candidate is now normal
`CB53` / hard `E15E`; its full `pike-safe-full01` Scenario 1..27 matrix,
162-state H-scroll gate, fresh first-draw debugger pairs, six-Pike probes, and
exact Monk active/acted probe are summarized in
`localization/current_candidate_surface_regression.json`. The current first
draws are normal `론` at `0x03CA` and hard `쉐` at `0x07DB`; the older
`0x03C9` / `0x07D1` pairs are retained under
`captures/analysis/preparation_first_draw_pre_pike` as historical evidence.

This closes the preparation glyph/H-scroll ownership work. It does not close
the separate cumulative release gate: battle-result coverage for Scenario 10
and Scenarios 12 through 27 is still pending. No release ROM or version was
changed.
