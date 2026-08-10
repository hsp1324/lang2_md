# Scenario 6 Rune Stone And All-Factions Cheat

## Result

Scenario 6's hidden Rune Stone is at the one-based map coordinate `(5,4)`,
the well in the upper-left area. This is not a hard-mode addition. The
Japanese event table contains the exact coordinate pair in
`0x18D768..0x18D778`, dispatches handler `0x18D8D8`, and renders the localized
record at `0x18E1C8`:

`룬스톤을 찾았다!`

In v1.3.2 the handler and dialogue remain source-identical, while the trigger's
horizontal end coordinate is extended from `5` to `7`. The accepted rectangle
is therefore `(5,4)..(7,4)`.

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
Earlier builds preserved that source behaviour, which could make the item
unobtainable during ordinary play. v1.3.2 keeps every NPC record unchanged and
adds the reachable right approach `(7,4)` to the same hidden-item trigger.

The first adjacent experiment stopped at `(6,4)`, but live play proved that
cell cannot be entered through the ordinary movement UI. The accepted build
therefore uses `(7,4)`, not the unverified adjacent-cell shortcut.

The live probe changed only Elwin's Scenario 6 deployment from `(4,26)` to
`(6,4)`. An ordinary rightward move to `(7,4)` rendered:

`룬스톤을 찾았다!`

The original accepted screen is
`captures/run/v132_s06_runestone_reachable.png`; the matching GST is recorded
in `localization/scenario6_runestone_runtime.json`.

v1.3.4 was replayed independently on an isolated Xvfb display.  The normal
release was wrapped only to place Elwin at `(6,4)`; an ordinary move to
`(7,4)` again rendered `룬스톤을 찾았다!`.  The reviewed screen and GST are
`captures/run/v134_release_regression/s06_runestone_retry/battle/runestone_found.png`
and `captures/run/v134_release_regression/s06_runestone_retry/states/runestone_found.gst`.
Their hashes are locked by `localization/v134_release_regression.json`.

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
