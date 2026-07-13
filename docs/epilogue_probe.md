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

## Remaining Runtime Step

The selector patch is statically tested, but live playback is not yet proven.
A valid Scenario 27 end-state or quicksave immediately before the character
epilogues is still required. After the user permits emulator use:

1. enter Scenario 27 (`전설의 끝`) through the existing scenario selector;
2. create a non-distribution easy-clear patch or save immediately before the
   ending epilogue loop;
3. load that state with a generated probe ROM;
4. advance every page of the requested record and confirm layout, punctuation,
   termination, and transition to the next ending state;
5. retain screenshots and record the exact probe index/checksum in
   `HANDOFF.md`.

Until this pass is done, offline record sheets remain static evidence only and
must not be described as live ending verification.
