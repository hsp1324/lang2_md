# Scenario 13 Current Result Surface Verification

Date: 2026-08-01

This verification covers the current normal and hard candidates' Scenario 13
Vargas aftermath, dynamic dialogue names, battle-result roster, Scenario 14
save row, route screen, and next-scenario title. It does not promote a release
or close the cumulative Scenario 1-27 acceptance gate.

## Accepted continuation method

- The source continuation is the historical `0CE6` BlastEm GST with SHA-256
  `11af030d8cf45a61502a60c1fde7811a3c256e92fcfd751944da739feacad658`.
  It was loaded without editing RAM, coordinates, event flags, or defeat bits.
- A savestate can retain the stock Start-menu callback address in work RAM.
  Redirecting only the callback initializer at `0x00F2E0` therefore did not
  invoke the diagnostic after this state was loaded.
- The accepted diagnostic mode hooks the retained stock entry at `0x022C1E`
  with a six-byte absolute jump. The wrapper at `0x3FEF00` checks that runtime
  group 17 still has Vargas name ID `0x0F`, writes only his live HP byte to
  `1`, replays the displaced stock instruction, and returns to `0x022C24`.
- The complete Scenario 13 event block `0x19A964..0x19C735` remains byte-exact.
  The wrapper is diagnostic-only and is not part of a release ROM.

The normal continuation probe is checksum `A46A`, SHA-256
`e181b1a3b3519b0a54ae80484ac7ef3da9158c4c2f5b48e7f4d69241e6f4435d`.
The hard probe is the exact same diagnostic delta over the hard candidate,
checksum `9065`, SHA-256
`ed95b5eda14a92c605dc76351cdf91aee3dde85385be6036037244c54bff06fa`.

## Runtime result

Both profiles used Keith's ordinary Attack command against the displayed
`발가스 / 파이터 / HP1`. The attack reached HP 0, displayed
`데빌액스 획득!`, and traversed 45 reviewed aftermath/level frames before the
battle result.

- Normal result: `전과보고`, the complete seven-commander roster, and
  `POINT 6450P`; capture SHA-256
  `56832449d94e48f93a193e16771b9afee0af861f566eca658528f644dad4c9dd`.
- Hard result: the same clean roster and `POINT 6420P`; capture SHA-256
  `17780c1aea7dab2e9fd49f895fe8e7e4c8db3682dcd26cea61c9a63628584ab2`.
- The only cross-profile result difference is the differing points digit at
  pixel bounding box `(272,97)..(278,104)`. The result header and roster are
  pixel-identical.
- Both paths wrote a real `시나리오 14` row, selected `다음 시나리오`,
  displayed `진군루트`, and entered `시나리오 14 / 성검 랑그릿사`.
- Reviewed dynamic speakers include 발가스, 레온, 아론, 엘윈, 제국지휘관,
  키스, and 제시카. No accepted aftermath/result/save/route/title frame shows
  Japanese residue, a broken name/class glyph, a damaged sprite, reset, or
  freeze.

The machine-readable evidence is
`localization/scenario13_current_result_surface_regression.json`; the verifier
is `tools/verify_scenario13_current_result_surface.py`.

## Rejected attempts

- The fresh southern completion layout placed players in Vargas's arrival
  lane before Zorum's event completed. Attacking Zorum followed the invalid
  event order and reset to the title. The title capture SHA-256 is
  `5a3c802520f96d737b7a16bc74f7eaa75e35807063fcb08b8e77b9f3aedc7aaa`.
- Loading the continuation under the initializer-only wrapper left Vargas at
  HP 8 because the callback address had already been cached. That capture's
  SHA-256 is
  `31981832d52bb19920326e00db7a7e99b215fd75f244af04375cbbca2e6b109f`.
- An older `0AD7` cross-checksum state terminated BlastEm before a stable
  capture and is not accepted as current evidence.
- Pre-result map tiles inherited from the historical cross-checksum state are
  not used to claim current sprite integrity. Current preparation, minimap,
  battle-cache, and gray acted-sprite evidence remains owned by the separate
  current-candidate matrices.
