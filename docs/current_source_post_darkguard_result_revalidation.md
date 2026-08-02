# Current-source post-DarkGuard result revalidation

Date: 2026-08-02

This report records non-release runtime evidence for the current dirty-source
candidate after the Scenario 13 enemy mercenary cache fix. It does not promote a
release, change the displayed version, or replace any Desktop ROM.

## Candidate identity

| Profile | Candidate | Mega Drive checksum | SHA-256 |
| --- | --- | --- | --- |
| normal | `tmp/current-source-post-darkguard-normal.md` | `1E83` | `58fdd97aba3d768bf3729052ba6fe211f4b23c35b63e65a941bf96ba01541592` |
| hard | `tmp/current-source-post-darkguard-hard.md` | `348E` | `2b21c81ddaaf565b4ceb3dbc24ae9eb721cede23f8f7c1ec8d660a742825b648` |

The 34 normal/hard diagnostic ROMs for Scenarios 10, 12-27 were generated in
`tmp/current-source-post-darkguard-result-probes/manifest.json`. The manifest
records `release_promoted: false` and `version_bumped: false`.

## Scenario 13 Dark Guard

The first exact-current run failed before rendering because the stock Vargus
Dark Guard group is event-hidden at the initial deployment state. That failure
does not test the renderer. A diagnostic-only ROM therefore changed one already
visible Dragonia subordinate into Dark Guard; production scenario data was not
changed.

The visible diagnostic run passed:

- evidence: `captures/run/enemy_dynamic_mercenary_status_probe/post-darkguard-current-s13-visible-darkguard-20260802-01/evidence.json`
- target class: `0x7C`, `다크가드`
- ROM sprite: `0x006D`
- cache owner/index: dynamic row 8
- base tile: `0x03A8`
- both animation frames matched the ROM sprite bytes before and after cursor
  hover

## Battle-result runtime matrix

All runs used isolated BlastEm instances and retained PNG/GST/JSON evidence.
Normal and hard profiles were tested separately.

| Scenarios | Run ID | Profiles passed | Summary |
| --- | --- | ---: | --- |
| 12 | `post-darkguard-20260802-08` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s12-safe-summary.json` |
| 13 | `post-darkguard-20260802-15` normal; `post-darkguard-20260802-14` hard | 2/2 | profile `evidence.json` files under `captures/run/current_source_result_revalidation/s13` |
| 14, 15, 17, 21-26 | `post-darkguard-20260802-02` | 18/18 | `tmp/current-source-post-darkguard-result-probes/supported-summary.json` |
| 10 | `post-darkguard-20260802-04` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s10-summary.json` |
| 16 | `post-darkguard-20260802-05` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s16-summary.json` |
| 18, 19 | `post-darkguard-20260802-16` | 4/4 | `tmp/current-source-post-darkguard-result-probes/s18-20-summary.json` plus profile `evidence.json` files |
| 20 | `post-darkguard-20260802-17` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s20-corrected-summary.json` |
| 27 | `post-darkguard-20260802-06` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s27-safe-summary.json` |

The Scenario 10 runner marks only the ten runtime monster groups defeated,
checks those group records, then completes the ordinary End Turn path. Both
profiles reached the battle-result screen at frame 32 and the save menu at
frame 1. Reaching the save menu does not overwrite a save slot.

Scenario 12 resumes the byte-exact historical final-battle GST without editing
the file or its work RAM. The normal candidate defeated the final Living Armor
in one ordinary attack. The hard candidate reduced it to HP 2, used the stock
End Turn path, and defeated it with Sherry's second ordinary attack. Both
profiles reached the battle-result surface at aftermath frame 26 and the save
menu at frame 1. Their result captures differ only inside the bottom-left
16x16 animated fire-icon cell; all text, portraits, roster rows, and points are
visibly clean. The first hard attempt
`post-darkguard-20260802-07` rejected HP 2 because the new runner initially
allowed only the formerly observed HP 1 continuation. That was a harness
assumption failure, not ROM evidence.

Scenario 13 also resumes its byte-exact historical final-Vargas GST. The
diagnostic-only current-candidate ROM checks Vargas's runtime identity and
changes only his live HP from 8 to 1 through the retained stock Start entry.
Ordinary Attack can miss, so every retry terminates the emulator and launches
the untouched continuation again; no mid-turn GST is restored and no later
turn is synthesized. Normal hit on fresh launch 4 and hard on fresh launch 5.
Both profiles reached the battle-result surface at aftermath frame 46 and the
save menu at frame 1. Their result PNGs are byte-identical with SHA-256
`f5ed2f149611f260eb808dd732d3ef108cdaa2e15a84d89b3a265e6ab933008a`;
their save-menu PNGs are also byte-identical with SHA-256
`cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a`.

The rejected `post-darkguard-20260802-13` runner tried to continue after a
miss by ending the turn. Scenario events reinitialized Vargas and the command
focus selected Elwin instead of Keith, so that route is harness-invalid. The
normal half of `post-darkguard-20260802-14` failed before any game input when
BlastEm exited during window creation with a JIT address-displacement error;
the clean normal rerun above distinguishes that emulator failure from ROM
evidence.

Scenario 16 now uses the same one-tile stock completion runner as Scenarios 14
and 15. Elwin moves from `(13, 6)` to the stock completion gate `(13, 5)`.
Both profiles reached a clean battle-result screen; the normal result capture is
`captures/run/current_source_result_revalidation/normal/s16/post-darkguard-20260802-05/battle/battle_result.png`.

Scenarios 18-20 resume SHA-256-locked historical final-boss continuations and
verify the requested scenario identity plus the boss class, name, position, and
initial HP before accepting any input. Scenario 18 defeated Great Dragon from
HP 9, Scenario 19 defeated Imelda from HP 10 normal/HP 1 hard, and Scenario 20
defeated Fias from HP 10. Every resulting GST records boss HP 0. Normal and hard
produced byte-identical result PNGs for each scenario:

- Scenario 18: frame 40 normal/frame 41 hard, SHA-256
  `36a961e6c48ff7b6b041e4f9aa43e358e7cbae6d0172a795a4bea61eb9d8b688`
- Scenario 19: frame 23, SHA-256
  `911bfe3d5abf6b7a8beba9d66721d5c3c70a457f320bb18acec005f413e89c98`
- Scenario 20: frame 36, SHA-256
  `08c028f063b438093474ab002bdd7ef6678f2186918d1f836bcbed8fb13eb350`

All six runs reached the same clean save-menu PNG, SHA-256
`cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a`.
The retained dialogue, level-up, and class-change frames include clean names
for Scott, Elwin, Aaron, Fias, Jessica, and Keith and clean class labels and
sprites. Key completed frames either byte-match the previously manually
reviewed Scenario 18-20 evidence or were manually rechecked in this run.

The first Scenario 20 run in `post-darkguard-20260802-16` pressed C as though
the historical continuation already held an Attack target. It actually held an
enemy-inspection cursor, so the run opened Fias's status page and stalled. The
corrected runner explicitly returns to Elwin, opens Attack, selects Fias, and
then confirms battle. This was an input-harness failure and is not ROM evidence.

The Scenario 27 runner stopped battle confirmations at the first retained GST
where Bernhardt had HP 0 (attempt 1, battle frame 6 in both profiles). It then
traversed the untouched result, ending, history, and character epilogue path.
Normal reached `Fin` at frame 3301 and hard at frame 3312. Both `Fin` captures
have SHA-256
`4cb7db62c30ace38e0d8b2fa1a34fc7ba31586104f5b59c9663b6ad9564a46b0`.
The profile-specific evidence files are under
`captures/run/current_source_result_revalidation/s27/{profile}/post-darkguard-20260802-06/evidence.json`.

An earlier retry experiment continued a fixed confirmation loop after HP 0 and
eventually entered the title/attract loop. That rejected run was a probe-input
failure; the passing run proves the current-source ROM's ordinary ending path.

## Coverage boundary

This current-source post-DarkGuard runtime matrix now covers Scenarios 10 and
12-27 in both profiles. The older accepted Scenario 1-9 and 11 result evidence
still needs a consolidated applicability audit against the present source
candidate before the cumulative Scenario 1-27 release gate can be marked
complete. No release ROM or displayed version was changed by this work.

## Exact-current cumulative closure

The preceding coverage boundary describes the earlier post-DarkGuard candidate
and is superseded by this exact-current rebuild. The final audit candidates are
normal checksum `015C`, SHA-256
`eaee0b0443140776a6ad7ae4542a9b41a132ac7c19c4b4b127a61de8b8d74c27`,
and hard checksum `1767`, SHA-256
`5b391ad132553427d2ededf01651d6215a71ce60dc8e1f0cacb1e45419a17f8a`.
The accepted manifests
`tmp/current-source-result-probes-full01/manifest.json`,
`tmp/current-source-result-probes-retry02/manifest.json`, and the complete
rebuild `tmp/current-source-result-probes-full02/manifest.json` are all bound
to that same candidate pair.

| Exact-current scenarios | Run ID | Passed profiles |
| --- | --- | ---: |
| 1, 2, 3, 5, 6, 7, 9 | `post-darkguard-20260802-18` | 14/14 |
| 4, 8, 11 | `post-darkguard-20260802-19` | 6/6 |
| 10, 12-16, 18, 20 | `current-source-20260802-20` | 16/16 |
| 19 | `current-source-20260802-21` | 2/2 |
| 17, 21-26 | `current-source-20260802-22` | 14/14 |
| 27 | `current-source-20260802-23` normal; `current-source-20260802-24` hard | 2/2 |

Fresh exact-current runtime evidence now covers all 27 scenarios in both
profiles, 54/54 profile-scenario runs. Scenarios 1-9 and 11 were rebuilt and
replayed instead of inheriting historical acceptance. Scenarios 4 and 8 use a
deterministic Start-entry runtime-group clear so their result proof does not
depend on combat RNG; this changes only ignored diagnostic probes. Scenario 11
loads the SHA-256-locked stock pre-final-battle continuation, validates both
reinforcement groups, performs a real Sherry attack, and reaches the stock
result and save surfaces. Scenario 19 uses the same one-HP continuation in both
profiles to remove the last profile-specific retry assumption.

All retained normal/hard result frames were visually inspected for Korean
commander names, portraits, result sprites, `POINT`, borders, rows, and numeric
fields. Scenario 27 additionally starts fresh from the selector, verifies
Bernhardt HP reaches zero through ordinary battle, and traverses the complete
stock ending through `Fin`. The aggregate hash-bound report is
`localization/current_result_surface_regression.json`.

The first exact-current hard Scenario 27 playback is rejected: the broad
caption heuristic matched a bright scanline in the moving terminal cinematic,
sent an extra confirmation, and returned to the title without retaining
`Fin`. The corrected runner confirms caption-only surfaces only after three
byte-identical captures, while dialogue panels still advance immediately. The
normal run remains `current-source-20260802-23`; the corrected hard run is
`current-source-20260802-24`.

This completes the exact-current cumulative Scenario 1-27 result/ending gate.
It does not authorize a release promotion: no release ROM, save, displayed
version, or Desktop artifact was changed by this verification.
