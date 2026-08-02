# Map Sprite Inactive-State Remap

## Symptom

Expansion-backed commander sprites render correctly while active, but can turn
into Hangul-like fragments when they become gray after moving or acting. They
return to normal at the start of the next player turn. The confirmed examples
were Shaman, Hein High Lord, and Elwin Lord.

The field report gives a precise state boundary: changing Hein to Shaman is
not enough to corrupt the sprite, and the next player turn restores the active
sprite. The corruption starts only after movement commits and the commander is
drawn as the gray acted unit. That active -> gray -> active sequence identifies
the separate 1bpp inactive-frame loader below; it is not a class-change record,
palette, save-data, or ordinary two-frame animation failure.

## Root Cause

The map loader at `0x0110A8` loads normal frames from:

- frame 0: `0x052980 + sprite_id * 0x80`
- frame 1: `0x058280 + sprite_id * 0x80`

It also calls `0x011DD8` with base `0x0510C0` to expand a separate
`0x40`-byte 2bpp silhouette into the gray `0x80`-byte inactive frame. Stock
code executes `LSL.W #6,D0`, so expansion sprite IDs `0x53AD..0x53E1` wrap in
16 bits and address unrelated ROM bytes.

## Fix

`scripts/build_korean_jp_probe.py` replaces the entry at `0x011DD8` with a
jump to `0x2B8D40`. Stock IDs pass through. All 53 dense custom IDs
`0x53AD..0x53E1` index private `0x40`-byte gray masks at `0x2F8000`, then
execution resumes at the stock expansion loop at `0x011DE2`.

The first implementation translated each custom ID back to the silhouette ID
from the original class record. That prevented ROM-address wrap and Hangul
fragments, but it was only correct while the redesigned active sprite retained
the stock silhouette. Scenario 13 exposed the remaining error: acted Elwin and
Hein Archmage loaded their obsolete stock infantry/cavalry shapes, which could
look like the enemy Armor Soldier successor or Royal Horse even though their
VRAM slots had not collided with those enemies.

The current implementation therefore treats recolors and redesigns
differently:

- a pure recolor whose active occupancy still matches the stock active and
  gray masks retains the hand-authored stock gray mask;
- a redesigned sprite derives a deterministic three-tone gray mask from its
  accepted custom active frame, preserving every occupied pixel of the new
  silhouette.

The mapping covers:

- Bald and Loren
- generic and commander-specific Shamans
- paired NPC sprites
- all 40 redesigned commander/class sprites

Normal custom animation frames are unchanged. Ordinary mercenary active,
second-frame, and gray caches are also unchanged; the separate fixed-cache
reuse test remains responsible for Pike, Monk, Phalanx, and the other ordinary
mercenaries when Scenario 13 fills all ten dynamic enemy slots through Royal
Horse.

### Scenario 13 redesign regression (2026-08-02)

The user's real 64 KiB Genesis Plus GX save was imported without changing its
roster, loaded into Scenario 13, and Elwin Archmage was moved through the real
in-game command. The acted runtime record is class `0x14`, commander `0x01`,
acted `0x01`, position `(16,3)`. Plane A references all four tiles
`0x04B0..0x04B3`, and VRAM `0x9600..0x967F` is byte-identical to custom sprite
`0x53BD`'s new private gray mask expansion.

- ROM: `tmp/s13-custom-gray-fix-20260802-01/candidate-hard.md`
- ROM checksum: `EC96`
- ROM SHA-256:
  `fff955d9c2549a8ac06ae2182e1aee93aed6296861aa309109d8074ae77417e2`
- capture:
  `captures/run/scenario13_royalhorse_regression/custom-gray-fix-20260802-01/elwin-acted-map.png`
- GST:
  `captures/run/scenario13_royalhorse_regression/custom-gray-fix-20260802-01/states/elwin-acted.gst`
- acted gray VRAM SHA-256:
  `0f7f922b9191785b112b3f8dd955f2c79c4538b5c39ea0531d6994f7ae3c398a`

The candidate is diagnostic only. It does not bump or replace a release ROM.

## Verification

Fresh Scenario 3 playback on isolated Xvfb display `:115` moved each commander
one tile and observed the gray state:

| Commander/class | Custom ID | Source ID | Gray VRAM | Capture |
| --- | ---: | ---: | ---: | --- |
| Hein Shaman | `0x53B4` | `0x37` | `0x9680` | `captures/run/gray_remap_s03_move_confirmed.png` |
| Hein High Lord | `0x53CC` | `0x3A` | `0x9680` | `captures/run/gray_remap_lord_s03_after_move.png` |
| Elwin Lord | `0x53BA` | `0x1E` | `0x9600` | `captures/run/gray_remap_elwin_lord_s03_after_move.png` |

The matching states are under `captures/analysis`:

- `regression_s03_shaman_gray_remap_after_move.gst`
- `regression_s03_high_lord_gray_remap_after_move.gst`
- `regression_s03_elwin_lord_gray_remap_after_move.gst`

Each complete 128-byte gray VRAM payload is byte-identical to a software
expansion of the remapped stock silhouette.

`captures/run/gray_remap_elwin_lord_s03_inactive_closed.png` is the final
acted state after closing the post-move command panel, not only the transient
post-move state. Its matching
`captures/analysis/regression_s03_elwin_lord_gray_remap_inactive_final.gst`
has class `0x04`, acted flag `0x01`, position `(16,15)`, and the same coherent
gray silhouette.

The same candidate was then started fresh and re-entered through normal
Scenario 3 preparation, automatic deployment, and opening dialogue. The
following status rows verify the UI fixes that share the candidate:

- `captures/run/current_s03_enemy_soldier_status_final.png`: `적군 / 솔저`
  remains intact when the Soldier is selected; it does not change to `파이`.
- `captures/run/current_s03_enemy_commander_status_final.png`: the adjacent
  generic enemy commander renders `적군 / 로드`, including the formerly
  damaged `적`.
- `captures/run/gray_remap_s03_scott_soldier_status.png`: the selected allied
  subordinate renders `리아나 / 가드맨`, including `가`, instead of inheriting
  the commander's class name.
- `captures/run/gray_remap_s03_enemy_pike_status.png`: the enemy subordinate
  renders `적군 / 파이크`, including `크`.

The previously retained real Scenario 1 result capture
`captures/run/candidate_regression_s01_clear_result_jeok_direct_fixed.png`
also renders `적군` intact in `전과보고`. The gray-source hook does not touch
the result renderer or its font slots.

Candidate:

- path: `tmp/current-regression-fix/Langrisser II (Korean regression-fix gray-remap).md`
- size: 4 MiB
- Mega Drive checksum: `A9FE`
- SHA-256: `4ff67d01332a46145b7f5dc26ff65202781618e5ee0210abc9ab01a57fa12a80`
- release version: unchanged; the candidate has not replaced either 1.0.0 ROM

Focused tests pass 68/68. `tests/test_map_sprite_gray_source_remap.py` locks
the mapping, hook, table, source IDs, blank-space ownership, and old word-wrap
failure.

## Current Hard Candidate

The same symptom was reported again while playing the unchanged `1.0.0/1.0.0`
release ROM. This does not indicate that the remap regressed:

- released predecessor checksum `1011`, SHA-256
  `c46249fdc50db4010115e5509c173de007761f5a42562345eca747506b43227b`
  still contains the stock bytes `02 80 00 00 FF FF` at `0x011DD8`;
- current build checksum `5BE8`, SHA-256
  `227e7a25818860ebd674d62bda3ca748901aaa45f0919c3eb1ae4340157742bd`
  contains the jump `4E F9 00 2B 8D 40`;
- the current build's complete hook, routine, and 53-entry table are
  byte-identical to the live-verified gray-remap candidate.

`tests/test_hard_candidate_delta.py` now validates the current hard ROM's
semantic hook, generated routine, and generated table directly, in addition
to locking its hash. After full 31-scenario runtime and first-turn validation,
this exact checksum-`5BE8` candidate replaced the same-version playtest file;
the checksum-`1011` predecessor remains in `roms/releases/archive`.

Fresh exact-current playback then recovered a valid manual slot under checksum
`8674`, entered Scenario 3 normally, and set only Hein's class to Shaman before
entry. The live runtime sequence was:

| State | Class/commander | Acted | Position | Capture |
| --- | --- | ---: | --- | --- |
| active on turn 1 | `0A/05` | `00` | `(0F,14)` | `captures/run/hard_8674_s03_shaman_fresh5_hein_command.png` |
| actual one-tile move complete | `0A/05` | `01` | `(0E,14)` | `captures/run/hard_8674_s03_shaman_inactive_actual.png` |
| active again on turn 2 | `0A/05` | `00` | `(0E,14)` | `captures/run/hard_8674_s03_shaman_turn2_active_actual.png` |

The complete gray payload at VRAM `0x9680` in
`captures/analysis/hard_8674_s03_shaman_inactive_actual.gst` is byte-identical
to the stock 68000 routine's software expansion of original Shaman silhouette
ID `0x37`. The current build therefore fixes the reported active -> gray ->
active sequence. The superseded checksum-`1011` candidate did not contain this
fix.

The checksum-`8674` predecessor was also re-entered from a valid Scenario 2 save,
then taken through the Scenario 3 preparation shop, item purchase list, return
to preparation, automatic deployment, and opening dialogue. The post-shop map
status rows remain intact:

- `captures/run/hard_8674_s03_scott_after_shop_status.png`:
  `스코트 / 파이터`;
- `captures/run/hard_8674_s03_guardman_after_shop_status.png`:
  `리아나 / 가드맨`;
- `captures/run/hard_8674_s03_pike_after_shop_status.png`:
  `적군 / 파이크`.

The current checksum-`5BE8` candidate was then started from a valid manual
slot, entered Scenario 3, and set Hein's class to Shaman before entry. Hein
was selected normally, moved one tile left through the in-game movement
command, and committed the post-move standby state:

| State | Class/commander | Acted | Capture |
| --- | --- | ---: | --- |
| active command panel | `0A/05` | `00` | `captures/run/hard_5be8_s03_shaman_hein_command.png` |
| actual movement complete | `0A/05` | `01` | `captures/run/hard_5be8_s03_shaman_inactive_actual.png` |

The matching
`captures/analysis/hard_5be8_s03_shaman_inactive_actual.gst` has a complete
gray payload at VRAM `0x9680`. Its 128-byte SHA-256 is
`10f15f0c4b9860e2b19cbe717c142b57be31d7bd5fe7bae5dca1e9741b51ea55`,
byte-identical to the previously verified Shaman silhouette. The remap table
also covers every commander-specific Shaman ID, including Sherry's; the
focused test enumerates all of them rather than checking only Hein.

The user also reported the same failure for Sherry specifically. A second
exact-current Scenario 5 run selected Sherry as Shaman and committed a normal
one-tile move:

| State | Class/commander | Acted | Position | Capture |
| --- | --- | ---: | --- | --- |
| active command panel | `0A/04` | `00` | `(15,53)` | `captures/run/hard_5be8_s05_sherry_shaman_command.png` |
| actual movement complete | `0A/04` | `01` | `(16,53)` | `captures/run/hard_5be8_s05_sherry_shaman_inactive_actual.png` |

The inactive sprite remains a coherent gray Shaman. The matching
`captures/analysis/hard_5be8_s05_sherry_shaman_inactive_actual.gst` locks
class `0x0A`, name ID `0x04`, acted flag `0x01`, and the final position.

This separates two previously conflated reports. The checksum-`1011` release
really lacks the inactive-frame remap. The checksum-`8674` predecessor
retained both the remap and the map-status glyphs after the shop renderer ran,
and the current checksum-`5BE8` candidate retains the same semantic hook,
generated routine, complete 53-entry table, and newly replayed Shaman gray
state.

Do not load a GST captured from another ROM hash as live proof, and do not
change an acted flag inside a paused GST and treat its cached frame as proof.
Both diagnostics can display a cached map and then reset on the next input.
Emulator proof must start or recover a manual save under the exact candidate
ROM and reach the acted state through the real movement command, as the
checksum-`8674` verification above did.
