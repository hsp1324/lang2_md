# Hard Mode First-Turn Verification

This document records no-action first-turn playback on the separate Standard Hard ROM. It is generated from `localization/hard_mode_first_turn_smoke.json`.

## Method

- Revalidate the source GST as Turn 1 and confirm every planned hard enemy runtime group before input.
- Copy the source GST into an isolated `hard-first-turn-sXX` runtime; never advance the loader evidence in place.
- Advance completed dialogue one page at a time, choose the stock `턴 종료` command, and wait through event, AI, movement, and battle animation frames.
- Accept only a real Turn 2 command menu or the scenario's normal GAME OVER path. The Turn 2 endpoint is also checked against work-RAM counter `$FFFFA5F1`.
- Store endpoint screenshots, GST paths, and SHA-256 values in the JSON manifest. Runtime captures are local evidence and are not release ROM inputs.

BlastEm rewrites its mutable runtime `quicksave.gst` when a process closes. Loader-smoke entry files are therefore revalidated from RAM content and the live digest is recorded instead of trusting an older manifest digest alone. Retained deep-evidence GST files remain strictly hash-locked.

## Coverage

- Status: `in_progress`
- Verified: 3/31
- Verified scenarios: 28, 29, 30
- Missing scenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 31

## Results

| Scenario | Endpoint | Opening confirmations | Phase confirmations | Elapsed |
|---:|---|---:|---:|---:|
| 28 | `turn_2_command` | 13 | 3 | 194.6s |
| 29 | `turn_2_command` | 5 | 4 | 239.1s |
| 30 | `game_over_turn_1` | 12 | 1 | 126.0s |

`turn_2_command` proves that the stock first-turn event and faction phases returned to a playable command state. `game_over_turn_1` is accepted only where the no-action route naturally defeats the party; it does not claim a successful scenario clear.
