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

Validation after the replacement:

- focused preparation/ownership/inventory checks: 46/46 pass;
- diagnostic ROM checksum locks affected by the common builder delta: 422/422
  pass after the uniform `+0x18A7` rebase;
- full suite: 1,440 tests, 44 failures and 3 errors remain. The first run had
  92 failures and 3 errors. The eliminated 48 failures were the checksum
  cascade from this builder change. Remaining failures belong to concurrent
  hard-runtime/plan state, experimental sprites, intentionally unchanged
  release artifacts/inventories, and generated runtime documentation.
