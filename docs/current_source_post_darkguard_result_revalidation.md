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
| 14, 15, 17, 21-26 | `post-darkguard-20260802-02` | 18/18 | `tmp/current-source-post-darkguard-result-probes/supported-summary.json` |
| 10 | `post-darkguard-20260802-04` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s10-summary.json` |
| 16 | `post-darkguard-20260802-05` | 2/2 | `tmp/current-source-post-darkguard-result-probes/s16-summary.json` |
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

Scenario 16 now uses the same one-tile stock completion runner as Scenarios 14
and 15. Elwin moves from `(13, 6)` to the stock completion gate `(13, 5)`.
Both profiles reached a clean battle-result screen; the normal result capture is
`captures/run/current_source_result_revalidation/normal/s16/post-darkguard-20260802-05/battle/battle_result.png`.

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

## Pending coverage

Current-source battle-result runners are still missing for Scenarios 13 and
18-20. Consequently this report is evidence for the rows above, not full
release acceptance.
