# Hard-Mode Intermittent Movement Regression

## Reported Symptom

In Standard Hard Scenario 1, an individual Soldier can sometimes appear to
have only two tiles of movement after some combat. Canceling Move and selecting
it again can restore the expected range. Bald was also reported to move at an
unexpected speed in one run.

This issue is not yet reproduced on the current candidate. Do not change class
movement data without a matching before/after runtime capture.

## Static Audit

`tools/build_hard_mode_rom.py` changes only fixed-placement commander AT/DF,
the hard-only Soldier A+/D+ correction tag, and occupied mercenary slots. It
does not patch class movement.

The complete 157-record class table is byte-identical between the current
localized base and hard candidate. Relevant movement bytes at class record
offset `+0x0D` are:

| Class | ID | Movement |
| --- | ---: | ---: |
| Soldier | `64` | `5` |
| Guardman | `65` | `6` |
| Horseman | `72` | `6` |
| Heavy Horseman | `73` | `5` |
| Royal Horseman | `7B` | `13` |

The stock loader at `0x010E84` copies class movement to runtime group offset
`+0x44`. The Standard Hard hook at `0x010E90` replaces only the following
class A+/D+ writes to runtime offsets `+0x46/+0x47`; it does not overlap
movement.

## Current Runtime Evidence

The latest hard candidate was entered from an in-game Scenario 1 save, hired
six Soldiers, used automatic deployment, and completed the first NPC/enemy
turn. The same Soldier's Move range was opened repeatedly before turn end and
again on Turn 2:

- `captures/run/hard_current_soldier_range_repeat1.png`
- `captures/run/hard_current_soldier_range_repeat5.png`
- `captures/run/hard_current_turn2_soldier_range.png`

All observed ranges remained normal. The retained Turn 2 state is:

- `captures/analysis/hard_current_s01_turn2_soldier_range.gst`

Elwin's runtime group begins at work RAM `0xFFFF603C`. Its six hired member
records all contain class `64`, and group movement at `+0x44` is `05`. This
rules out a persistent ROM table overwrite and a persistent hard-loader write
as the cause of the reported two-tile display.

An old-release quicksave visually restored under another diagnostic process
then reset when execution resumed. It is rejected evidence. Movement
reproduction must enter through disk SRAM and must not load a state created by
another ROM build.

## Next Reproduction

1. Continue the current hard candidate until a hired Soldier has participated
   in combat.
2. Save a GST without loading it when the short range first appears.
3. Cancel Move, reopen it, save a second GST, and compare group `+0x44`, member
   coordinates/flags, occupied tiles, terrain, and the generated reach map.
4. Patch only after the changing runtime field or pathfinding input is
   identified.

