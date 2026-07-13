# Epilogue Playback Probe

This probe is a non-distribution test path for playing one of the 90 character
epilogue records through the stock Mega Drive ending selector and text object.
It does not replace the normal Korean build and its generated ROM must not be
committed.

## Verified Original Path

The Japanese ROM routine at `0x01DC64` reads the current ending character index
from RAM `0xFFFFAE90`. For indices 0-13 it loads a group pointer from the table
at `0x08916E`, compares two character statistics with an inclusive descriptor,
and loads the selected record pointer from descriptor offset `+0x08`.

The descriptor is 12 bytes:

```text
+0x00  statistic 1 minimum, inclusive
+0x02  statistic 1 maximum, inclusive
+0x04  statistic 2 minimum, inclusive
+0x06  statistic 2 maximum, inclusive
+0x08  32-bit epilogue record pointer
```

The routine calls the stock text-object allocator at `0x0094DC`, installs
callback `0x37E4`, and stores the selected record pointer in the object. This is
the actual ending renderer path, not the offline PNG renderer.

Normal group ownership is:

```text
slot 0-7   Scott, Sherry, Keith, Lana, Aaron, Lester, Hein, Jessica
slot 8-13  six imperial/villain outcomes
slot 14    Liana's direct eight-pointer table at 0x089572
slot 15    four world outcomes at 0x089592
```

## Probe ROM

`tools/build_epilogue_probe_rom.py` copies the current Korean build, validates
the selected record against the full Japanese source SHA-256 in
`localization/epilogue_records.json`, and writes two descriptors into the
otherwise-unused expanded-ROM range at `0x3FF000`:

- a skip descriptor beginning with `FFFF`, which makes the stock routine return
  without creating a text object;
- an all-inclusive descriptor that points at the requested record.

All other normal character groups are temporarily redirected to the skip
descriptor. Liana and world records retain their special stock paths and have
their small direct-pointer table redirected to the requested record. The Mega
Drive checksum is recalculated.

`--start-slot` can replace the stock `CLR.W $FFFFAE90` at `0x01C7A8` with an
equal-length `MOVE.W #slot,$AE90.W`. This keeps the original ending loop and
callbacks intact while avoiding unrelated character transitions. Slot 14 is
Liana and slot 15 is the world outcome. This is safer than editing the RAM
index in an active GST state because the currently installed callback may
already belong to the previous character.

Example, without launching an emulator:

```bash
python3 scripts/build_korean_jp_probe.py
python3 tools/build_epilogue_probe_rom.py --record-index 18
```

This writes the ignored file:

```text
roms/builds/Langrisser II (Epilogue Probe 18).md
```

An address may be used instead:

```bash
python3 tools/build_epilogue_probe_rom.py --address 0x08B8C4
```

Special-path examples:

```bash
python3 tools/build_epilogue_probe_rom.py --record-index 78 --start-slot 14
python3 tools/build_epilogue_probe_rom.py --record-index 86 --start-slot 15
```

## Scenario 27 Ending Probe

`tools/build_scenario27_ending_probe_rom.py` can be applied after the selected
epilogue probe. It validates the complete Scenario 27 layout and exact Japanese
Bernhardt record, then moves an unguarded AT/DF 0 Bernhardt directly above the
first automatic Elwin position. This preserves the stock final-battle event and
ending path while making the battle end after one attack.

```bash
python3 tools/build_epilogue_probe_rom.py --record-index 78 --start-slot 14
python3 tools/build_scenario27_ending_probe_rom.py \
  --input-rom 'roms/builds/Langrisser II (Epilogue Probe 78).md'
```

Both outputs are ignored non-distribution ROMs.

## Runtime Verification

The stock path was exercised in BlastEm on 2026-07-14:

- production checksum `451C` plus the Scenario 27 probe produced checksum
  `9B8E`; Scenario 27 opening, Bernhardt's defeat, the complete closing event,
  ending art, history screens, normal character epilogues, and their transition
  all ran without a reset;
- this run exposed Japanese `敵撃破数` / `撤退回数` at glyph list `0x089146`;
  the production builder now writes `격파횟수` / `퇴각횟수`, verified live in
  `captures/run/9b8e_epilogue_labels_live2.png`;
- Liana record 78 used `--start-slot 14` and combined checksum `94FE`; its
  Korean special-selector page is captured in
  `captures/run/94fe_liana78_transition1.png`;
- world record 86 used `--start-slot 15` and combined checksum `CEDD`; its
  Korean final page is captured in
  `captures/run/cedd_world86_transition1.png`.

GST saves are ROM-content-specific in BlastEm. Loading the pre-epilogue GST
after swapping to another probe ROM was rejected, and changing `AE90` inside an
already-running GST altered the active callback flow and ended the sequence
early. Rebuild the combined probe and replay Scenario 27 instead.

This proves the normal, Liana, and world selector/renderer classes. It does not
prove every one of the 90 records live; all 90 retain separate static hash,
capacity, page-boundary, and rendered-sheet checks.
