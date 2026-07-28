# Map Sprite Inactive-State Remap

## Symptom

Expansion-backed commander sprites render correctly while active, but can turn
into Hangul-like fragments when they become gray after moving or acting. They
return to normal at the start of the next player turn. The confirmed examples
were Shaman, Hein High Lord, and Elwin Lord.

## Root Cause

The map loader at `0x0110A8` loads normal frames from:

- frame 0: `0x052980 + sprite_id * 0x80`
- frame 1: `0x058280 + sprite_id * 0x80`

It also calls `0x011DD8` with base `0x0510C0` to expand a separate
`0x40`-byte 1bpp silhouette into the gray `0x80`-byte inactive frame. Stock
code executes `LSL.W #6,D0`, so expansion sprite IDs `0x53AD..0x53E1` wrap in
16 bits and address unrelated ROM bytes.

## Fix

`scripts/build_korean_jp_probe.py` replaces the entry at `0x011DD8` with a
jump to `0x2B8D40`. Stock IDs pass through. All 53 dense custom IDs
`0x53AD..0x53E1` are translated through the word table at `0x2B8E00` to the
silhouette ID from the original class record, then execution resumes at
`0x011DDE`.

The mapping covers:

- Bald and Loren
- generic and commander-specific Shamans
- paired NPC sprites
- all 40 redesigned commander/class sprites

Normal custom animation frames are unchanged.

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
- current build checksum `8674`, SHA-256
  `142580f8ff9021f011ae5da186c7685f9ed7f7bd01d1ebdb9959148f9691cd27`
  contains the jump `4E F9 00 2B 8D 40`;
- the current build's complete hook, routine, and 53-entry table are
  byte-identical to the live-verified gray-remap candidate.

`tests/test_hard_candidate_delta.py` now validates the current hard ROM's
semantic hook, generated routine, and generated table directly, in addition
to locking its hash. The release file remains unchanged until the user
explicitly approves a new release.

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
active sequence; the still-published checksum-`1011` release does not contain
this fix.

Do not load a GST captured from another ROM hash as live proof, and do not
change an acted flag inside a paused GST and treat its cached frame as proof.
Both diagnostics can display a cached map and then reset on the next input.
Emulator proof must start or recover a manual save under the exact candidate
ROM and reach the acted state through the real movement command, as the
checksum-`8674` verification above did.
