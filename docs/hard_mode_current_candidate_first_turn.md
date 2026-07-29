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

- Status: `all_scenarios_first_turn_verified`
- Verified: 31/31
- Verified scenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
- Missing scenarios: none

## Results

| Scenario | Endpoint | Opening confirmations | Phase confirmations | Speed | Elapsed |
|---:|---|---:|---:|---:|---:|
| 1 | `turn_2_command` | 4 | 39 | 400% | 103.2s |
| 2 | `turn_2_command` | 36 | 4 | 100% | 201.6s |
| 3 | `turn_2_command` | 12 | 3 | 100% | 108.7s |
| 4 | `turn_2_command` | 16 | 16 | 100% | 215.7s |
| 5 | `turn_2_command` | 5 | 9 | 100% | 115.9s |
| 6 | `defeat_return_title_turn_1` | 11 | 10 | 100% | 184.3s |
| 7 | `turn_2_command` | 6 | 28 | 100% | 278.3s |
| 8 | `turn_2_command` | 8 | 10 | 100% | 142.9s |
| 9 | `turn_2_command` | 15 | 20 | 100% | 244.9s |
| 10 | `turn_2_command` | 0 | 0 | 100% | 49.5s |
| 11 | `turn_2_command` | 25 | 21 | 100% | 279.0s |
| 12 | `turn_2_command` | 8 | 1 | 100% | 148.5s |
| 13 | `defeat_return_title_turn_1` | 8 | 5 | 100% | 122.3s |
| 14 | `turn_2_command` | 22 | 7 | 100% | 203.1s |
| 15 | `turn_2_command` | 5 | 4 | 100% | 121.6s |
| 16 | `turn_2_command` | 5 | 2 | 100% | 115.1s |
| 17 | `turn_2_command` | 13 | 6 | 100% | 199.4s |
| 18 | `turn_2_command` | 13 | 2 | 100% | 186.8s |
| 19 | `turn_2_command` | 7 | 3 | 100% | 134.7s |
| 20 | `turn_2_command` | 5 | 13 | 400% | 73.2s |
| 21 | `turn_2_command` | 9 | 0 | 400% | 70.6s |
| 22 | `turn_2_command` | 10 | 4 | 400% | 77.2s |
| 23 | `turn_2_command` | 11 | 5 | 400% | 97.1s |
| 24 | `turn_2_command` | 9 | 3 | 400% | 92.8s |
| 25 | `game_over_turn_1` | 18 | 13 | 400% | 100.1s |
| 26 | `game_over_turn_1` | 7 | 10 | 400% | 64.2s |
| 27 | `game_over_turn_1` | 14 | 2 | 400% | 58.8s |
| 28 | `turn_2_command` | 15 | 3 | 400% | 92.5s |
| 29 | `turn_2_command` | 5 | 7 | 400% | 91.5s |
| 30 | `game_over_turn_1` | 14 | 1 | 400% | 79.5s |
| 31 | `game_over_turn_1` | 4 | 0 | 400% | 39.1s |

`turn_2_command` proves that the stock first-turn event and faction phases returned to a playable command state. `game_over_turn_1` is accepted only where the no-action route naturally defeats the party. `defeat_return_title_turn_1` requires a matching immutable-normal-ROM defeat trace. Neither defeat endpoint claims a successful scenario clear.
