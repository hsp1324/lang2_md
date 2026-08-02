# Scenarios 18-20 Current Result Surface Verification

Date: 2026-08-02

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

## 2026-08-02 current-source rerun

The historical accepted matrix above was rerun after the Scenario 13 Dark
Guard/cache work against current source-derived diagnostic ROMs. No player ROM
was promoted and no displayed version was changed.

| Scenario | Profile | Probe checksum / SHA-256 | Boss HP | Result frame / SHA-256 |
| --- | --- | --- | ---: | --- |
| 18 | normal | `57FD` / `17d18f265f70764a4d3ff30ff4a55ddd742978790389be22a1ae887335bd8093` | 9 -> 0 | 40 / `36a961e6c48ff7b6b041e4f9aa43e358e7cbae6d0172a795a4bea61eb9d8b688` |
| 18 | hard | `41EE` / `6f2e708edf66b395f552ca4e5b560fbcf1cf02b47d05d2ce188654ee3b5edd03` | 9 -> 0 | 41 / `36a961e6c48ff7b6b041e4f9aa43e358e7cbae6d0172a795a4bea61eb9d8b688` |
| 19 | normal | `6834` / `42fcae5cedef70065133d5aceb078510352f26b610029c56dfc51297409a1c6c` | 10 -> 0 | 23 / `911bfe3d5abf6b7a8beba9d66721d5c3c70a457f320bb18acec005f413e89c98` |
| 19 | hard | `19EF` / `5ee48801a4222037c59e89c73c0dc81bd28740ded30369f04c1cd701e0a18d83` | 1 -> 0 | 23 / `911bfe3d5abf6b7a8beba9d66721d5c3c70a457f320bb18acec005f413e89c98` |
| 20 | normal | `19E0` / `bdd1b8623125edfa2c7027a98654b10bf62615bc1df19496f14a032fe535506e` | 10 -> 0 | 36 / `08c028f063b438093474ab002bdd7ef6678f2186918d1f836bcbed8fb13eb350` |
| 20 | hard | `FBCB` / `60fe4add4f1215583dd87fcef4c47501db456d21a11a17080e48c90d0db017d4` | 10 -> 0 | 36 / `08c028f063b438093474ab002bdd7ef6678f2186918d1f836bcbed8fb13eb350` |

All six current-source runs reached the byte-identical clean save menu with
SHA-256
`cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a`.
Scenario 18 and 19 evidence is under run ID
`post-darkguard-20260802-16`; corrected Scenario 20 evidence is under
`post-darkguard-20260802-17` in
`captures/run/current_source_result_revalidation/{normal,hard}/sNN/`.

The first Scenario 20 attempt in run ID `post-darkguard-20260802-16` was
rejected. Its seed retained an enemy-inspection cursor rather than an Attack
target, so the original input sequence opened Fias's status page and stalled.
The runner now returns to Elwin and explicitly selects Attack and Fias. This is
documented as an input-harness failure, not a renderer failure.

The historical machine-readable evidence remains
`localization/scenario18_20_current_result_surface_regression.json`; its
verifier is `tools/verify_scenario18_20_current_result_surface.py`. The reusable
current-source runner is `tools/run_scenario18_20_result_surface.py`, and the
parallel orchestrator now dispatches Scenarios 18-20 through it.
