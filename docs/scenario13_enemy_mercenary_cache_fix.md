# Scenario 13/16 enemy mercenary cache validation

## Failure model

The battle renderer has ten dynamic enemy-mercenary cache rows at WRAM
`0xFFFFA88E..0xFFFFA8B5`.  If an unsupported roster requests more distinct
advanced mercenary sprites than fit in those rows, stock lookup code can read
the following owner's word as a tile number and display unrelated tiles such
as Korean font fragments.

An in-game SRAM save does **not** serialize the hostile runtime groups that
would be needed to retain a twelve-class enemy roster.  The previously used
"legacy save retains twelve classes" description was therefore incorrect.
Cross-ROM savestates and an artificially expanded twelve-class Pure roster are
also outside the supported release state domain.

## Repair and release scope

Normal and Hard use the guarded loader built by
`scripts/build_korean_jp_probe.py`.  It treats fixed and dynamic rows as one
lookup domain, never writes an eleventh dynamic row, recognizes sprites already
present in either table, and uses a source-locked fallback only after proving a
compatible fixed row is unused by the twenty runtime groups.

Original keeps the original design and loader.  Its exact v1.3.7 Scenario 13
and 16 rosters use at most all ten supported dynamic rows; consequently no
overflow patch is needed or applied to Original.  The synthetic twelve-class
Original stress case is recorded as `unsupported_out_of_domain_synthetic_stress`
and is not counted as a release pass.

## v1.3.7 runtime evidence

`tmp/v137-s13-cache-formal/summary.json` is the fail-closed verification
manifest (`SHA-256
7d7638966454b8134770571cf9b6cd534572467f5d5a61576b7c9a978f20a2cf`).
It locks each case to an exact ROM hash, scenario, target runtime group/member,
expected cache owner/index/tile, and seed hash.

- Exact Original/Normal/Hard Scenario 13 and 16 boundary cases all pass on
  isolated virtual displays.  Both animation frames match the exact sprite
  source in each tested release ROM.
- Hard's ordinary class `0x63` correctly reuses fixed row 1 at tile `0x034C`;
  advanced classes remain within the ten dynamic rows.
- Normal and Hard source-locked overflow diagnostics confirm the guarded
  behavior without being presented as exact release gameplay.
- Cursor movement, target identity, Plane A sprite linkage, before/after cache
  ownership, ROM hash, and seed immutability are mandatory checks.  Missing or
  mismatched expectations fail instead of being inferred from the observed
  result.

The diagnostic ROMs are not releases and do not change the checked-in version
registry.
