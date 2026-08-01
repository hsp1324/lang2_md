# Scenarios 18-20 Current Result Surface Verification

Date: 2026-08-01

This check covers the current normal and hard candidates for Scenarios 18,
19, and 20 from the final boss interaction through their stock aftermath,
level/class-change pages, battle-result roster, sprites, and save menu. It does
not promote a release or close the cumulative Scenario 1-27 acceptance gate.

## Candidate and probe lineage

- The current normal candidate is checksum `CB53`; the current hard candidate
  is checksum `E15E`.
- Each normal result probe is an exact replay of the corresponding guarded
  completion-layout builder over the current normal candidate.
- Each hard probe applies exactly the normal diagnostic byte envelope over the
  current hard candidate and recalculates only the Mega Drive checksum.
- Scenario 18 probes are checksums `04CD/EEBE`, Scenario 19 probes are
  `1504/C6BF`, and Scenario 20 probes are `C6B0/A89B` for normal/hard.
- These are diagnostic ROMs only. They are neither release builds nor hard-mode
  balance evidence.

## Runtime result

- Scenario 18 normal and hard both defeat the stock Great Dragon, preserve
  Scott, resident, Elwin, and class-change text, and reach pixel-identical
  `전과보고 / POINT 12500P` screens.
- Scenario 19 normal reaches `POINT 14600P`. Hard uses the same current hard
  ROM with a diagnostic GST whose only difference from the historical fixture
  is Imelda's runtime current HP byte at GST offset `0x8877`, changed from
  `10` to `1`. It deterministically reaches Imelda HP0, the stock aftermath,
  level pages, `전과보고 / POINT 15500P`, and save menu. The one-byte state
  edit is not distributable player state and proves no battle balance.
- Scenario 20 normal and hard retain Fias's restored portrait-font path,
  dynamic names for Elwin, Jessica, and Keith, Scott's class-change page,
  complete result rosters, and the save menu. Their diagnostic point totals
  differ (`0P` and `18050P`) because the historical continuations carry
  different accumulated runtime rewards; this is recorded rather than hidden.
- All 43 reviewed images are 320x240, SHA-256 locked, and show clean sprites
  without Japanese residue, broken dynamic glyphs, or stale text over icons.
- All six save-menu images are pixel-identical.

## Rejected Scenario 19 hard attempts

- With Imelda at HP10, an ordinary attack could deal 9 damage and leave HP1.
  Short repeated confirms then selected Laird's status panel; this was an
  incomplete battle/input-timing path, not a renderer failure.
- Ending that incomplete branch's turn reached `GAME OVER`, so it was rejected
  as completion evidence.
- HP9 was also insufficient because one attempt dealt 8 and again left HP1.
- A temporary Start-menu MP guard, checksum `A2BC`, was unnecessary for the
  accepted path and was removed from source. It is retained only as a rejected
  attempt in the machine-readable report.

## Save-state policy

Player migration must launch the current ROM, use the game's `START → 불러오기`
path to load SRM, and create a fresh savestate afterward. Old player
savestates are not release or validation inputs. The historical GST fixtures
used here are isolated renderer continuations with explicit scope limits.

The machine-readable evidence is
`localization/scenario18_20_current_result_surface_regression.json`; the
verifier is `tools/verify_scenario18_20_current_result_surface.py`.
