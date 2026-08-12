# v1.3.1-v1.3.6 historical-save acceptance matrix

Status: **artifact/route contract complete; controller runtime pending**.

`tools/run_historical_save_version_matrix.py` defines the supplemental
`historical_save_version_matrix_v1` acceptance surface required by the v1.3.7
final gate. It covers all 17 public patch targets from v1.3.1 through v1.3.6
and Keith, Lester, and Jessica on every target: 51 rows. The non-public v1.3.0
development tag is deliberately excluded.

The planning command reads the Japanese source ROM, verifies every manifest
and BPS hash, applies each BPS in memory, and rejects the target unless the
reconstructed 4 MiB ROM has the published output SHA-256. It also verifies the
three frozen v1.3.7 ROMs:

| Profile | Frozen v1.3.7 ROM SHA-256 |
| --- | --- |
| Original | `2d475a96f5f5ee26352bef6c3c392a77aafa283a2c0f260a6d1cb8603b3610ac` |
| Normal | `92e90c0e00df03c1c3264bc6ff7702c5356c2ba2b65d5f2281177066f329c7d8` |
| Hard | `ca7750c207382023636acb37901242437861a8b83f4b39477c1405c8dd1ee6eb` |

The runtime contract is intentionally stricter than the older diagnostic
matrices:

- Each lineage begins at the real title screen and uses controller input only.
- Every historical target must perform the stock in-game SAVE itself and then
  exit, producing an exact 8 KiB cartridge SRAM.
- The ROM behind one stable media path changes only after the emulator exits,
  so the naturally created SRAM remains the same cartridge save. It is never
  imported, copied into a slot, or externally repaired.
- The current ROM starts in a fresh process, uses the stock title LOAD UI,
  proceeds and re-saves in game, exits, then starts a second fresh process and
  uses title LOAD again.
- No emulator state input, scenario selector, marker injection, direct RAM
  write, direct SRAM write, or manual-slot mutation is allowed.
- The verifier parses the flushed 8 KiB payload, validates the format marker,
  valid bit and stock checksum, and compares the selected commander's
  class/LV/EXP with the controller-visible status evidence.

The v1.3.2 and v1.3.3 Keith/Lester Fighter LV11+ rows have a mandatory
v1.3.1 predecessor. Original and Normal use the public v1.3.1 Normal parent;
Hard uses the public v1.3.1 Hard parent. Fighter LV11+ must be reached through
ordinary historical gameplay, saved in game, exited, title-loaded by the exact
v1.3.2/v1.3.3 target, and re-saved there. The acceptance source has no path for
constructing that state from a marker or edited slot.

Recovery rows must consume exactly one live-join grant on the first v1.3.7
progression and none on the second LOAD. Keith's fixed raw amount is `0x00`;
Lester's is `0x90`. A first-choice Keith recovery settles at Lord LV1/EXP0,
and a first-choice Lester recovery settles at Knight LV5/EXP16. Historical
states that already selected a class must remain unchanged. The fresh
v1.3.4-v1.3.6 Lester rows separately cover the missed Crocoknight LV10 join
boundary and its one-time recovery.

Generate the hash-locked pending plan with:

```sh
python tools/run_historical_save_version_matrix.py plan \
  --run-id v137-historical-save-final-01 \
  --artifact-root /absolute/path/to/isolated-artifacts \
  --output /absolute/path/to/historical-save-plan.json
```

The plan explicitly sets `acceptance_claimed` to false. Only a complete
51-row controller-run evidence file accepted by the `verify` command may emit
a release-eligible pass report. Planning or static tests alone are not runtime
acceptance.
