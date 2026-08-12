# Scenario 6 Rune Stone Reproducible Probe

## Current v1.3.6 Result

Scenario 6's hidden Rune Stone is associated with the one-based map coordinate
`(5,4)`, the well in the upper-left area. This is not a hard-mode addition.
The Japanese event table stores its trigger at `0x18D768..0x18D778`, dispatches
handler `0x18D8D8`, and renders the localized record at `0x18E1C8`:

`룬스톤을 찾았다!`

The current v1.3.6 Original, Normal, and Hard outputs intentionally do **not**
keep the trigger byte-identical to the Japanese ROM. Relative byte `+8`, the
horizontal end coordinate, changes from `0x05` to `0x07`. The accepted trigger
rectangle is therefore `(5,4)..(7,4)`. The handler, dialogue, and NPC records
retain their existing behavior: the handler and NPC records remain
source-identical, while the dialogue remains the current localized Korean
record. The accessibility change was introduced earlier and is carried by all
three current release profiles.

## NPC Occupancy

Scenario 6 fixed records `0..3` are Aaron and the three residents. Their
initial coordinates remain source-identical in all v1.3.6 profiles:

| Record | Unit | Coordinate |
| --- | --- | --- |
| 0 | 아론 | `(14,10)` |
| 1 | 주민 | `(5,5)` |
| 2 | 주민 | `(14,4)` |
| 3 | 주민 | `(22,5)` |

The stock resident AI can move onto or obstruct access to the nearby well.
The release therefore keeps every NPC record unchanged and adds the reachable
right approach `(7,4)` to the same hidden-item trigger.

## Reproducing the v1.3.6 Probe

The probe is generated from the versioned Normal v1.3.6 output. Run:

```sh
python3 tools/build_scenario6_runestone_probe_rom.py
```

If the ignored build ROM is absent, the builder automatically reconstructs it
from the Japanese ROM and tracked `patches/normal-v1.3.6.bps`. The release
manifest is `patches/v1.3.6.json`; no archived Korean ROM is needed.

The default output is `tmp/scenario6-runestone-v1.3.6-probe.md`. It has Mega
Drive checksum `1F70` and SHA-256
`daa4b170ab26d84ed46fee9486774c972d1b05410bd89058e733c9bdc8281fc4`.
The builder changes only Elwin's deployment `(4,26) -> (6,4)` plus the
resulting ROM checksum. It does not change the trigger, handler, dialogue, or
NPC records.

Run the generated ROM with BlastEm on an isolated Xvfb display and make one
ordinary move from `(6,4)` to `(7,4)`. The expected screen is
`룬스톤을 찾았다!`. Generated ROMs, screenshots, and emulator states are
temporary evidence and are not committed. The automated test rebuilds the
Normal v1.3.6 ROM from BPS, regenerates this probe in memory, checks its hash,
and proves that the trigger has only the `5 -> 7` X-end delta while the handler
and all four NPC records remain source-identical.

Machine-readable values are in
`localization/scenario6_runestone_runtime.json`.

## All-Factions Command

The historical input sequence is retained for manual diagnostics:

`UP LEFT UP RIGHT A LEFT DOWN B DOWN RIGHT A B DOWN RIGHT A`

Use 50 ms key holds and 50 ms gaps. Old untracked screenshot and GST paths are
not part of the v1.3.6 reproducible Rune Stone test, so the manifest no longer
requires those deleted files.
