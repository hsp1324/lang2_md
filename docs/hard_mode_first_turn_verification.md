# Hard Mode First-Turn Verification

This document records no-action first-turn playback on the separate Standard Hard ROM. It is generated from `localization/hard_mode_first_turn_smoke.json`.

## Method

- Revalidate the source GST as Turn 1 and confirm every planned hard enemy runtime group before input.
- Preserve scenario-selector Turn 1 states as hash-locked snapshots. Continue the live process when a scenario entry is not safely resumable after a BlastEm relaunch; otherwise copy the source into an isolated `hard-first-turn-sXX` runtime.
- Advance completed dialogue one page at a time, choose the stock `턴 종료` command, and wait through event, AI, movement, and battle animation frames.
- Accept only a real Turn 2 command menu or the scenario's normal defeat path. A title return is accepted only when the immutable normal ROM reproduces the same route and the scenario is listed in `localization/hard_mode_first_turn_expected_endpoints.json`. The Turn 2 endpoint is also checked against work-RAM counter `$FFFFA5F1`.
- Store endpoint screenshots, GST paths, and SHA-256 values in the JSON manifest. Runtime captures are local evidence and are not release ROM inputs.

BlastEm rewrites its mutable runtime `quicksave.gst` when a process closes. Newly retained entry and endpoint snapshots are therefore stored under `captures/analysis` and strictly hash-locked. Older loader-smoke runtime files are revalidated from RAM content instead of trusting an older manifest digest alone.

## Coverage

- Status: `in_progress`
- Verified: 24/31
- Verified scenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 28, 29, 30, 31
- Missing scenarios: 21, 22, 23, 24, 25, 26, 27

## Results

| Scenario | Endpoint | Opening confirmations | Phase confirmations | Speed | Elapsed |
|---:|---|---:|---:|---:|---:|
| 1 | `turn_2_command` | 4 | 30 | 100% | 145.4s |
| 2 | `turn_2_command` | 33 | 4 | 100% | 196.3s |
| 3 | `turn_2_command` | 12 | 3 | 100% | 108.1s |
| 4 | `turn_2_command` | 14 | 15 | 100% | 198.7s |
| 5 | `turn_2_command` | 5 | 8 | 100% | 113.9s |
| 6 | `defeat_return_title_turn_1` | 11 | 10 | 100% | 187.3s |
| 7 | `turn_2_command` | 8 | 27 | 100% | 274.1s |
| 8 | `turn_2_command` | 8 | 8 | 100% | 138.4s |
| 9 | `turn_2_command` | 16 | 19 | 100% | 243.7s |
| 10 | `turn_2_command` | 6 | 1 | 100% | 73.7s |
| 11 | `turn_2_command` | 25 | 22 | 100% | 285.3s |
| 12 | `turn_2_command` | 8 | 1 | 100% | 153.7s |
| 13 | `defeat_return_title_turn_1` | 8 | 4 | 100% | 89.3s |
| 14 | `turn_2_command` | 22 | 8 | 100% | 200.5s |
| 15 | `turn_2_command` | 6 | 4 | 100% | 122.1s |
| 16 | `turn_2_command` | 5 | 3 | 100% | 122.0s |
| 17 | `turn_2_command` | 16 | 8 | 100% | 202.7s |
| 18 | `turn_2_command` | 10 | 3 | 100% | 189.2s |
| 19 | `turn_2_command` | 8 | 3 | 100% | 135.8s |
| 20 | `turn_2_command` | 5 | 10 | 100% | 131.9s |
| 28 | `turn_2_command` | 13 | 3 | 100% | 194.6s |
| 29 | `turn_2_command` | 5 | 4 | 100% | 239.1s |
| 30 | `game_over_turn_1` | 12 | 1 | 100% | 126.0s |
| 31 | `game_over_turn_1` | 4 | 1 | 150% | 65.5s |

`turn_2_command` proves that the stock first-turn event and faction phases returned to a playable command state. `game_over_turn_1` is accepted only where the no-action route naturally defeats the party. `defeat_return_title_turn_1` requires a matching immutable-normal-ROM defeat trace. Neither defeat endpoint claims a successful scenario clear.
