# Scenario 6 Rune Stone And All-Factions Cheat

## Result

Scenario 6's hidden Rune Stone is at the one-based map coordinate `(5,4)`,
the well in the upper-left area. This is not a hard-mode addition. The
Japanese event table contains the exact coordinate pair in
`0x18D768..0x18D778`, dispatches handler `0x18D8D8`, and renders the localized
record at `0x18E1C8`:

`룬스톤을 찾았다!`

The trigger and handler bytes are identical in the Japanese ROM, current normal
candidate, and current hard candidate.

## NPC Occupancy

Scenario 6 fixed records `0..3` are Aaron and the three residents. Their initial
coordinates remain source-identical:

| Record | Unit | Coordinate |
| --- | --- | --- |
| 0 | 아론 | `(14,10)` |
| 1 | 주민 | `(5,5)` |
| 2 | 주민 | `(14,4)` |
| 3 | 주민 | `(22,5)` |

The stock resident AI can move onto or obstruct access to the nearby well.
Contemporary Japanese and English Mega Drive guides explicitly warn that the
NPC can block this Rune Stone and recommend Teleport, the all-factions cheat,
or waiting for the NPC to be defeated. Moving the NPC's fixed record in the
hard build would change source gameplay and is therefore rejected.

## Hard-Mode Cheat Check

The original all-factions command was entered on the current hard candidate
with 50 ms key holds and 50 ms gaps:

`UP LEFT UP RIGHT A LEFT DOWN B DOWN RIGHT A B DOWN RIGHT A`

Afterward, selecting an enemy commander opened its ordinary `이동 / 공격`
command menu:

- `captures/run/hard_fbe2_s06_all_factions_enemy_command.png`
- `captures/analysis/hard_fbe2_s06_all_factions_enemy_command.gst`

This proves that hard mode does not disable the cheat. A missed attempt is an
input timing/focus problem, not a ROM rule difference.

Machine-readable evidence and locked hashes are in
`localization/scenario6_runestone_runtime.json`.
