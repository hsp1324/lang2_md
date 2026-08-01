# Scenario 12 Current Result Surface Verification

Date: 2026-08-01

This verification covers the current normal and hard candidates' final
Living Armor battle, stock Dark Rod aftermath, dynamic dialogue names,
battle-result roster, Scenario 13 save row, route screen, and next-scenario
title. It does not promote a release or close the cumulative Scenario 1-27
acceptance gate.

## Accepted continuation method

- The source continuation is the historical Scenario 12 BlastEm GST with
  SHA-256
  `ac2958e056561b4c8345805b351f5b45ac55453c8e89db94ba787317d7588878`.
  It was loaded without editing the state file, RAM, coordinates, event flags,
  HP, or defeat bits.
- The state contains the older compact battle's work RAM with nine of ten
  visible guardians already defeated. It is used only to reach the current
  ROM's post-final-attack renderers. It is not a fresh current
  deployment-to-clear replay and is not hard-mode balance evidence.
- The current normal probe is an exact replay of the source-validating compact
  builder over the current normal candidate. The hard probe applies exactly
  that 108-byte diagnostic envelope over the current hard candidate and then
  recalculates only the Mega Drive checksum.
- The complete Scenario 12 event block `0x198DE0..0x19A963` remains byte-exact
  in both probes. The probes are diagnostic-only and are not release ROMs.

The normal probe is checksum `15CA`, SHA-256
`f8748183072e750d3827e7531477cc2fd1eca55e8a7cc2fb1847d5e6e25ba239`.
The hard probe is checksum `02C2`, SHA-256
`7d51d06a78f438531db880c7f0e8b3a13b48dbe0a632e01250cd447c46bd571d`.

## Runtime result

- Normal: Sherry's ordinary attack visibly reduced the final
  `리빙아머 / HP10` through HP9 to HP0 and rendered its defeat page.
- Hard: the same first ordinary attack left `HP1`; after the ordinary turn
  transition, Sherry's second attack reduced it to HP0. The incomplete
  one-attack state was not mistaken for a clear.
- Both profiles then traversed the same 24 stock aftermath and level frames,
  including reviewed names 엘윈, 제시카, 아론, and 헤인.
- Both final result frames are pixel-identical and visibly render `전과보고`,
  the complete seven-commander roster, and `POINT 4920P`. Their SHA-256 is
  `da64f42f01cf3360813a24e7ed55dff6c166d7f8fdf6af44843921127972cb1b`.
- Both paths opened the real save screen, wrote `시나리오 13` in slot 1,
  selected `다음 시나리오`, displayed `진군루트`, and entered
  `시나리오 13 / 염룡병단과의 결전` without reset or freeze.
- No accepted aftermath/result/save/route/title frame shows Japanese residue,
  a broken name/class glyph, a damaged sprite, or stale text over an icon.

The machine-readable evidence is
`localization/scenario12_current_result_surface_regression.json`; the verifier
is `tools/verify_scenario12_current_result_surface.py`.

## Input pitfall retained from the run

The attack selector initially rests on Sherry's own cell. Pressing confirm
there only returns to the unit menu; it does not damage the adjacent Living
Armor. The accepted sequence moves the target cursor one cell right before
confirming. This was an input-selection mistake, not a ROM renderer failure.
