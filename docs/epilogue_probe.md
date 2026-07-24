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

The production build validates all 90 Japanese records against the full source
SHA-256 values in `localization/epilogue_records.json`. It also checks each
individual selector pointer, control sequence, and page count. The Korean
records are variable length so natural word spacing is possible; they are
written consecutively from `0x2C0000` and each original selector pointer is
updated to the corresponding relocated record. The original compact records
are retained but are no longer reachable.

`tools/build_epilogue_probe_rom.py` copies the current Korean build, validates
the selected Japanese source record, follows its pointer reference to the
relocated Korean record, and writes two descriptors into the otherwise-unused
expanded-ROM range at `0x3FF000`:

- a skip descriptor beginning with `FFFF`, which makes the stock routine return
  without creating a text object;
- an all-inclusive descriptor that points at the requested record.

All other normal character groups are temporarily redirected to the skip
descriptor. Liana and world records retain their special stock paths and have
their small direct-pointer table redirected to the relocated requested record.
The Mega Drive checksum is recalculated.

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

## All-Record Renderer Pass

`--all-records` concatenates the current build's 90 relocated Korean records
into one probe-only stream at `0x3E0000`. Every record keeps its encoded words,
dynamic-name controls, line breaks, and existing page breaks; only each
intermediate `FFFF` terminator becomes one `FFFD` page break. The final record
retains its `FFFF` terminator. This produces exactly 515 pages, the sum of the
90 individual page counts, without modifying the production ROM.

```bash
python3 tools/build_epilogue_probe_rom.py --all-records
```

The command writes two ignored artifacts beside one another:

```text
roms/builds/Langrisser II (Epilogue Probe All).md
roms/builds/Langrisser II (Epilogue Probe All).manifest.json
```

The manifest maps every original address and English cross-reference to a
zero-based `start_page`, `page_count`, relocated address, and combined-stream
word range. The builder validates all 90 Japanese source hashes and pointer
owners before following the 90 current Korean relocation pointers. It also
rejects an occupied stream reservation, a page-count change, an unterminated
relocated record, or overflow into the descriptor reservation at `0x3FF000`.

Combine it with the Scenario 27 placement probe for one stock ending entry:

```bash
python3 tools/build_scenario27_ending_probe_rom.py \
  --input-rom 'roms/builds/Langrisser II (Epilogue Probe All).md' \
  --output-rom 'roms/builds/Langrisser II (Scenario 27 All Epilogues Probe).md'
```

This path is intended to prove that all authored pages survive the real text
renderer with natural spacing and dynamic names. It does not prove the normal
stat-selection condition for each outcome, nor does it replace the normal
per-character portrait/stat transition checks. The single-record normal,
Liana, and world probes below remain authoritative for those selector classes.

The combined checksum `DD8F` was played through Scenario 27 on 2026-07-18.
Bernhardt was defeated on the first adjacent attack and the stock ending path
consumed the combined stream through stable `Fin` without a reset or freeze.
The continuous evidence sets are:

```text
captures/run/dd8f_closing_watch/
captures/run/dd8f_all_epilogues_watch/
```

`dd8f_all_epilogues_watch/0750.png` is `Fin`, which remains stable through
`1200.png`. Reaching the final terminator proves that the real renderer can
consume the 90-record/515-page stream, but it is not a substitute for normal
outcome selection or manual acceptance of every individual page.

This pass also exposed an ending-status font-bank regression. Stable frames
`0340.png` and `0545.png` show broken extension glyphs in
`보젤/다크마스터` and `베른하르트/엠퍼러`. A GST from the broken screen
proved that the ending background had overwritten extension ranges beginning
at tiles `0x398`, `0x440`, `0x498`, and `0x4D8`, while the live Plane A/B and
sprite table did not reference those ranges. The context-specific call at
`0x01CBA6` now reloads compressed resources `0x1AF..0x1B2` through wrapper
`0x2B7D00` before invoking the existing direct renderer. The other two callers
of the shared renderer remain unchanged.

Production checksum `5F82` plus the all-record and Scenario 27 probes produced
checksum `1BE7`. Its numbered stock playback is
`captures/run/1be7_full_ending_watch/0000.png` through `1288.png`.
`0799.png` shows intact `보젤/다크마스터`, and `1052.png` shows intact
`베른하르트/엠퍼러`; named copies are
`1be7_bozel_darkmaster_fixed.png` and
`1be7_bernhardt_emperor_fixed.png`. The stream reaches `Fin` at frame `1241`
and remains byte-identical through `1288`, without reset or freeze.

This historical run retained the then-unreviewed line
`제국군이 마을로 오고 있어! 리아나가 위험해!` at frames `0104.png`
through `0107.png`. Do not cite that wording as accepted translation evidence.
The later Japanese-source review below proved that it was an invented Scenario
1 recap and replaced the complete montage conversation.

## All Ending Visit Dialogue Pass

The 23 ending-visit records at Japanese addresses `0x0954E2..0x096A84` are
separate from the 90 outcome epilogues. Each record has one verified pointer
owner in the stock descriptor block at `0x095412..0x0954DC`. Production now
keeps every Japanese source record intact, relocates naturally spaced Korean
records consecutively from `0x2D0000`, and updates those 23 owners. Ordered
dynamic-name controls, source hashes, page counts, three-line pages, and
24-cell lines remain build gates.

`tools/build_ending_dialogue_probe_rom.py` constructs an ignored diagnostic
stream at `0x3D0000`. It copies all 23 current relocated records and replaces
only the first 22 terminators with page breaks. All 23 visit pointers then
target the combined stream, so whichever visit condition the stock ending
chooses first renders all 83 authored pages. The generated manifest maps each
record to its exact page range. This proves renderer coverage, not all natural
condition selections.

```bash
python3 scripts/build_korean_jp_probe.py
python3 tools/build_ending_dialogue_probe_rom.py
python3 tools/build_scenario27_ending_probe_rom.py \
  --input-rom 'roms/builds/Langrisser II (Ending Dialogue Probe All).md' \
  --output-rom 'roms/builds/Langrisser II (Scenario 27 All Ending Dialogues Probe).md'
```

Production checksum `E38B` generates standalone probe `ACE4` and combined
Scenario 27 probe `F852`. The complete playback is retained in
`captures/run/f852_ending_dialogue_watch/`. The combined stream starts before
frame `240`; representative spaced pages are `240`, `320`, `400`, and `420`.
Frame `470` renders the final Liana request, `475` renders the final
`넌 혼자가 아니야, 리아나` page, and `477` reaches the normal forest ending.
Frame `479` begins the expected SEGA restart. No Japanese residue, clipping,
blank authored page, premature terminator, unintended reset, or freeze occurred.

## Scenario 27 Ending Probe

`tools/build_scenario27_ending_probe_rom.py` can be applied after the selected
epilogue probe. It validates the complete Scenario 27 layout and exact Japanese
Bernhardt record, then moves an unguarded Bernhardt directly above the first
automatic Elwin position. Scenario AT/DF bytes are signed modifiers rather than
final values, so the probe writes `-12/-4` to cancel Emperor's `AT 12/DF 4`
class bases. Live status is therefore `AT 0/DF 0`.

AT/DF 0 alone does not guarantee a one-attack defeat: combat variance can leave
Bernhardt at HP 1 even when a diagnostic save raises Elwin from AT 23 to AT 64.
Save a BlastEm state at the command menu immediately before selecting Attack.
If the result is HP 1, load that state, wait a different number of frames to
advance the battle RNG, and retry. Do not change the production ROM or a normal
user SRAM to force the result.

```bash
python3 tools/build_epilogue_probe_rom.py --record-index 78 --start-slot 14
python3 tools/build_scenario27_ending_probe_rom.py \
  --input-rom 'roms/builds/Langrisser II (Epilogue Probe 78).md'
```

Both outputs are ignored non-distribution ROMs.

The final credit group can be checked by applying the two probes in the other
order so the world ending loop starts at slot 15:

```bash
python3 tools/build_scenario27_ending_probe_rom.py
python3 tools/build_epilogue_probe_rom.py \
  --input-rom 'roms/builds/Langrisser II (Scenario 27 Ending Probe).md' \
  --record-index 86 --start-slot 15 \
  --output-rom 'roms/builds/Langrisser II (Scenario 27 Final Credit Probe).md'
python3 tools/run_blastem_sequence.py scenario-select \
  --rom 'roms/builds/Langrisser II (Scenario 27 Final Credit Probe).md' \
  --scenario-number 27 --send-event
```

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
- Production checksum `743F`, Scenario 27 probe checksum `BFAD`, and the slot
  15 combined checksum `F2FC` replayed the complete final route. Bernhardt's
  live status was `AT 0/DF 0`, the stock world epilogue completed, and the
  final two-record credit group displayed `COPYRIGHT 1994 NCS` together with
  `한국어화 hsp1324`. Evidence is
  `captures/run/f2fc_credit_final_watch/324.png`. That run proved the ending
  route, but did not prove AT/DF 0 makes the first combat deterministic.

GST saves are ROM-content-specific in BlastEm. Loading the pre-epilogue GST
after swapping to another probe ROM was rejected, and changing `AE90` inside an
already-running GST altered the active callback flow and ended the sequence
early. Rebuild the combined probe and replay Scenario 27 instead.

This proves the normal, Liana, and world selector/renderer classes. It does not
prove every one of the 90 records live; all 90 retain separate static hash,
capacity, page-boundary, and rendered-sheet checks.

## Relocated Spaced Records

The earlier no-space Korean epilogues were a conservative response to each
original record's fixed capacity, not a renderer requirement. On 2026-07-15 all
90 records were reflowed with normal Korean word spacing and relocated into the
reserved `0x2C0000..0x2D0000` range. The current set starts at `0x2C0000`; its
last record starts at `0x2CA54E`. Unit tests require all 90 relocated pointers
to be unique and increasing, preserve source controls and page breaks, and keep
every authored page within three lines of 24 visible cells.

Production checksum `E6F4` and combined Scenario 27/slot 15 checksum `BE4C`
completed the stock closing event, world epilogue, credits, and `Fin` without a
reset. The 340-step evidence set is
`captures/run/be4c_epilogue_watch/001.png` through `340.png`; frame 300 visibly
confirms ordinary spaces. Frame 270 exposed one remaining authored adjacency,
`{0001}일행`, which rendered as `엘윈일행`. All eight occurrences were changed
to `{0001} 일행`, guarded by a regression test, and the corrected production
checksum is `EA22`.

The first corrected-checksum attempt used production `EA22`, Scenario probe
`3590`, and combined checksum `C176` without boosting the diagnostic save.
Bernhardt displayed AT/DF 0 but survived at HP 1; evidence is
`captures/run/c176_probe_failure_current.png`. The 133 frames under
`captures/run/c176_epilogue_watch/` are an aborted battle attempt, not epilogue
verification evidence. A second diagnostic attempt raised Elwin to AT 64 but
the same damage cap still left Bernhardt at HP 1, captured at
`captures/run/c176_at64_second_failure_current.png`. The 150 frames under
`captures/run/c176_at64_epilogue_watch/` are also aborted battle evidence. The
next runtime attempt must use a pre-attack save-state and varied-delay retries.

The final corrected-checksum run used the same production `EA22`, Scenario probe
`3590`, and combined checksum `C176`. A quicksave was created at Elwin's command
menu before Attack. This run rolled the full ten damage on its first attempt,
defeated Bernhardt, and completed the stock closing route without loading the
state. The continuous evidence set is
`captures/run/c176_corrected_epilogue_watch/001.png` through `359.png`:

- frame 216 renders `어둠의 대결은 엘윈 일행의` with the required space;
- frames 216-244 cover every page of relocated world record 86 with natural
  Korean spacing and intact page transitions;
- frame 280 renders `COPYRIGHT 1994 NCS` and `한국어화 hsp1324`;
- frame 288 reaches `Fin`, which remains stable through frame 359.

This closes the live verification gap for the corrected dynamic-name spacing and
the relocated world-epilogue route. It does not replace the separate static
hash, pointer, capacity, and render checks for the other 89 records.

Under the current WSLg/remote-focus state, global XTest input could leave the
frame unchanged even after raising the window. Direct window events through
`tools/send_blastem_keys.py --send-event` were reliable and were used for the
complete `BE4C` playback. Treat an unchanged capture as input-delivery failure
before changing ROM logic.

Automation configs remove the host `pads` binding block while retaining the
keyboard-to-emulated-pad mappings used by direct events. An Xbox controller can
therefore be used by another application without steering the test emulator.

## Source-Reviewed Ending Montage

The fixed-count montage immediately before the result screens is separate from
the 90 outcome epilogues. Japanese-ROM playback is retained in
`captures/run/230d_jp_ending_montage/`. It proves that the old Korean line
`제국군이 마을로 오고 있어! 리아나가 위험해!` was an invented Scenario 1
recap, not the source ending. Addresses `0x0A6BA8..0x0A6F02` now follow the
Japanese conversation about Bernhardt's distrust, mutual understanding, the
allies who stopped the empire, Langrisser uniting hearts, and Elwin continuing
his journey.

The renderer count is a maximum, not each record's storage length. Most source
records end at an earlier `FFFF`; the old writer padded through the maximum and
erased that terminator, causing adjacent records to splice together. The
builder now validates every Japanese source boundary before writing and puts
each terminator back at its exact original word index. Unit tests lock the
layout and reject the invented recap. Production checksum is `D8F6`.

Runtime checksum `1E2A` captured the corrected ten-record sequence under
`captures/run/1e2a_ending_fixed/`. That pass exposed four records where the
game supplies `엘윈` dynamically and the fixed text therefore needs to begin
with `: `; checksum `D8F6` includes that correction. The subsequent `2464`
capture attempt resumed after the conversation and is not accepted as proof of
the final punctuation-only change.

The apparent `엠퍼러` damage in
`captures/run/1e2a_ending_montage/163.png` is specific to the Scenario 27
adjacent-Bernhardt diagnostic layout: Bernhardt's animated flame sprite lies
over the first two class glyphs. The following map frame `164.png` shows the
same sprite at that screen coordinate. The class token stream is byte-identical
to the fixed build, while the ordinary result screen remains fully readable in
`captures/run/1be7_bernhardt_emperor_fixed.png`.

Current production checksum `9DD0` plus the adjacent-Bernhardt diagnostic
produced checksum `E93E`. A fresh selector run first demonstrated a useful
automation failure: reporting a valid saved Scenario 27 does not prove that the
selector cheat was accepted. The missed cheat loaded the slot's Scenario 1 map,
visible as `SCENARIO 1` in the lower panel. The accepted replay stopped on
`captures/run/e93e_s27_selector_live.png`, visibly confirmed selector row
`시나리오 27`, and only then entered the route.

The accepted run used stock automatic deployment and a normal Elwin attack.
`e93e_s27_real_target_bernhardt.png` and `e93e_s27_real_battle_ui.png` retain
intact `베른하르트/엠퍼러`, AT/DF 0 diagnostic stats, and the battle labels.
The complete closing stream is
`captures/run/e93e_s27_ending_watch/000.png` onward. Frames `075..124` traverse
the final punctuation build's ten reviewed montage records; `090..094` contain
the corrected allies/empire line, `100` completes Langrisser uniting everyone's
hearts, and `103` completes Sherry's warning. The invented
`리아나가 위험해` recap never appears.

The same run retained normal result selection rather than the all-record
concatenation probe. Representative status screens include
`225` (`스코트/파이터`), `400` (`라나/클레릭`), `575`
(`보젤/다크마스터`), `650` (`레온/로얄가드`), `725`
(`베른하르트/엠퍼러`), `800` (`리아나/클레릭`), and `825` (Elwin's
conclusion). Credits remain interleaved with the original battle scenes, and
frame `875` reaches `Fin` without a reset or freeze. The ten source-reviewed
montage rows may therefore be `live_verified: true`; the two preceding,
unreviewed villain records remain false.
