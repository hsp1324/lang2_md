# Hard Mode First-Turn Verification

This document records no-action first-turn playback on the separate Standard Hard ROM. It is generated from `localization/hard_mode_current_candidate_first_turn.json`.

## Method

- Revalidate the source GST as Turn 1 and confirm every planned hard enemy runtime group before input.
- Preserve scenario-selector Turn 1 states as hash-locked snapshots. Continue the live process when a scenario entry is not safely resumable after a BlastEm relaunch; otherwise copy the source into an isolated `hard-first-turn-sXX` runtime.
- Advance completed dialogue one page at a time. Confirm the battle map after closing the unit panel, confirm the Start menu after opening it, choose the stock `턴 종료` command, and wait through event, AI, movement, and battle animation frames.
- Accept only a real Turn 2 command menu or the scenario's normal defeat path. A title return is accepted only when the immutable normal ROM reproduces the same route and the scenario is listed in `localization/hard_mode_first_turn_expected_endpoints.json`. The Turn 2 endpoint is also checked against work-RAM counter `$FFFFA5F1`.
- Store endpoint screenshots, GST paths, and SHA-256 values in the JSON manifest. Runtime captures are local evidence and are not release ROM inputs.

BlastEm rewrites its mutable runtime `quicksave.gst` when a process closes. Newly retained entry and endpoint snapshots are therefore stored under `captures/analysis` and strictly hash-locked. Older loader-smoke runtime files are revalidated from RAM content instead of trusting an older manifest digest alone.

## Coverage

- Status: `in_progress`
- Verified: 9/31
- Verified scenarios: 2, 3, 4, 5, 6, 7, 8, 9, 10
- Missing scenarios: 1, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31

## Results

| Scenario | Endpoint | Opening confirmations | Phase confirmations | Speed | Elapsed |
|---:|---|---:|---:|---:|---:|
| 2 | `turn_2_command` | 36 | 4 | 100% | 201.6s |
| 3 | `turn_2_command` | 12 | 3 | 100% | 108.7s |
| 4 | `turn_2_command` | 16 | 16 | 100% | 215.7s |
| 5 | `turn_2_command` | 5 | 9 | 100% | 115.9s |
| 6 | `defeat_return_title_turn_1` | 11 | 10 | 100% | 184.3s |
| 7 | `turn_2_command` | 6 | 28 | 100% | 278.3s |
| 8 | `turn_2_command` | 8 | 10 | 100% | 142.9s |
| 9 | `turn_2_command` | 15 | 20 | 100% | 244.9s |
| 10 | `turn_2_command` | 0 | 0 | 100% | 49.5s |

`turn_2_command` proves that the stock first-turn event and faction phases returned to a playable command state. `game_over_turn_1` is accepted only where the no-action route naturally defeats the party. `defeat_return_title_turn_1` requires a matching immutable-normal-ROM defeat trace. Neither defeat endpoint claims a successful scenario clear.
