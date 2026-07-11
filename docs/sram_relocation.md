# SRAM Relocation After ROM Expansion

The Japanese ROM is 2 MiB and declares odd-byte SRAM immediately after it:

- ROM end: `0x1FFFFF`
- SRAM: `0x200001..0x203FFF`

The Korean build expands the cartridge image to 4 MiB (`0x3FFFFF`). Leaving
the original SRAM declaration in place makes BlastEm map ROM over the save
range. The visible symptoms were deterministic:

- Start > Save returned normally but left an all-zero 8192-byte SRAM file.
- Load treated an original Japanese valid save as corrupt/no data.
- The scenario-select code could not be tested because it requires a valid
  manual scenario slot.

The builder now moves SRAM to `0x400001..0x403FFF`, the first range after the
expanded ROM. It patches the header and the verified absolute addresses in the
save subsystem at `0x01DDD4..0x01E06D`. The five slot bases remain the same
distance apart; only `0x200000` is added. The game accesses odd-byte SRAM with
68K `MOVEP`, so the logical size and the 8192-byte emulator file stay unchanged.

`tests/test_sram_relocation.py` verifies the header, every known long address,
and the unchanged SRAM size. Checksum `8C4D` was live-tested both ways:

- A Japanese-ROM save loads as `CONTINUE 1` in the Korean ROM.
- Saving Scenario 23 changed the SRAM SHA-256 from `92f8202e...` to
  `9de54cde...`; nonzero bytes increased from 2562 to 4714.

## Scenario Select

The Mega Drive scenario-select code only works on manual slots 1-4, not the
`CONTINUE` autosave. Highlight a valid manual slot and enter Left, Right,
Start, C. The Load title then shows the selected scenario number. Up decrements
(Scenario 1 wraps to 24), Down increments, and C loads the selected scenario.

For diagnosis only, `0x022FC8` was changed in a temporary ROM from the long
branch `66 00 00 08` to `66 08 70 01`: a confirmed Start-menu save was sent to
manual slot 1 instead of `CONTINUE`. This produced the manual slot used for
scenario-select verification. That probe is not part of the production build.

Live condition captures made through the real scenario index:

- `captures/run/8c4d_scenario14_conditions_live.png`
- `captures/run/8c4d_scenario23_conditions_live.png`

The title-screen Load path and scenario-select suffix are still Japanese. The
in-battle Start > Load path and save confirmation were fixed separately at
checksum `F639`; those UI issues are independent from SRAM mapping.
