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
