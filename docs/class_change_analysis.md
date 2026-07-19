# Japanese Class-Change Resource Analysis

The Japanese class-change screen uses a shared 15-slot global glyph list rather
than an FF-terminated byte string. The static resource and Fighter Elwin's
first candidate branch are now structurally and live verified.

## Confirmed Ownership

- Code `0x02BB60` loads 15 glyphs from `0x0A3C9C` into VRAM `0xD080`.
- Layout `0x0A3CBA` references slots 0..10 and displays
  `クラスチェンジできます`.
- Code `0x02BC0C` opens layout `0x0A3CDC`, which references slots 0..6 and
  displays the shorter title `クラスチェンジ`.
- Original slots 11..14 are `傭兵` and `魔法` and are shared by the detail UI.

## Korean Slot Plan

The builder preserves all 15 indexes:

```text
0..5   클래스체인지
6      space
7..8   가능
9..10  space
11..12 용병
13..14 마법
```

This makes the existing 0..10 layout read `클래스체인지 가능`, the 0..6
layout read `클래스체인지`, and preserves the two detail labels without
changing layout tokens or code. The original 15-word tuple is validated before
patching.

## Persistent And Runtime Progress

- The persistent player roster starts at work RAM `0xFFA4CC`. It contains ten
  records of `0x18` bytes. Within each record, class is `+0x00`, level is
  `+0x02`, and experience is `+0x03`.
- Manual save slot 1 starts at SRAM `0x194E`; the roster begins at slot offset
  `+0x30` and uses the same `0x18`-byte records.
- Runtime units start at `0xFF603C` and use `0x60`-byte records. Elwin's class
  is `0xFF603C`, level is `0xFF606A`, and experience is `0xFF606B`.
- Routine `0x011C78` copies runtime progress back to the persistent roster.
  Routine `0x0177D8` copies persistent progress into runtime units. Patching
  only the save-slot level/experience is therefore not stable across all
  preparation/deployment synchronization points.
- The level-up handler is `0x01480C`. Fighter class ID `0x01` needs 16 EXP at
  level 9 to reach the first class-change branch.

`tools/run_blastem_sequence.py` can patch a recovered manual slot with
`--manual-slot-commander-id`, `--manual-slot-level`,
`--manual-slot-experience`, and optional `--manual-slot-expected-class`. It
validates the slot marker, valid flag, scenario, checksum, and source class,
then updates the checksum. This is useful for structure experiments, but it
does not replace runtime synchronization verification.

## Fighter Elwin Candidate Proof

The original Fighter progression list at `0x082562` yields class IDs
`0x04`, `0x05`, and `0x0A`: `ロード`, `ナイト`, and `シャーマン`. The Korean
targets are `로드`, `나이트`, and `샤먼`.

`tools/build_class_change_probe_rom.py` builds an ignored diagnostic ROM. Its
Start-key wrapper constructs the same source-derived candidate array and jumps
to the stock UI at `0x02BB48`. A separate guarded end-turn wrapper gives only
Fighter Elwin the exact LV9/EXP16 trigger and then jumps to the stock level-up
handler. Neither wrapper is part of the production ROM.

BlastEm checksum `D1D7` verifies:

- long prompt `클래스체인지 가능`;
- short title `클래스체인지`;
- candidates `로드`, `나이트`, `샤먼` and their Korean `용병`/`마법` detail;
- Down navigation through all three rows and wrap from `샤먼` to `로드`;
- confirmation returns from the diagnostic UI to the map.

Accepted captures are
`captures/run/d1d7_class_change_start_trigger.png`,
`captures/run/d1d7_class_change_candidate1.png`,
`captures/run/d1d7_class_change_candidate2.png`,
`captures/run/d1d7_class_change_candidate3.png`,
`captures/run/d1d7_class_change_candidate_wrap.png`, and
`captures/run/d1d7_class_change_confirm.png`. Its retained state
`captures/analysis/d1d7_class_change_confirm.gst` is screen/navigation evidence,
not a controlled before/after application proof. The normal end-turn route is
retained in `captures/analysis/eb00_class_change_turn2.gst` and proves the
runtime change from class `0x01` to `0x04`, LV1, EXP0.

Candidate sets beyond Fighter Elwin's and Hein's first branches still require
runtime coverage. Do not describe the entire class-change matrix as complete
until those commander and branch combinations have been sampled.

## Full Chain Inventory

`python3 tools/class_change_inventory.py` reads all ten source pointers at
`0x08253A` and generates `localization/class_change_chains.json` plus
`docs/class_change_chain_inventory.md`. The source contains 100 transitions
and 76 unique current/candidate combinations after duplicates are merged.
Each row keeps the original address, class IDs, Japanese name, Korean display
target, screen-verification state, and application-verification state.

The generalized probe also displayed Lester's source transition
`서펜나이트(0x10) -> 실버나이트(0x1D) / 서펜로드(0x1F) / 팔라딘(0x19)` on
checksum `D221`. All three rows and their `용병/마법` details are intact in
`captures/run/d221_c9_s10_candidate1.png` through `candidate3.png`.

That diagnostic used Elwin's active runtime record because Lester was not
present in Scenario 2. Its retained state did not establish a Lester
before/after transition. Treat `D221` as screen/navigation evidence only.

## Non-Elwin Runtime Application Proof

The probe now treats source-chain ownership and the active runtime record as
independent inputs. Runtime record index 1 starts at `0xFF609C`; this is Hein's
active record in the Scenario 1 test path. Two separate probes establish the
boundary between display and application:

- Start-display checksum `8EF4` uses commander ID 5, current class `0x03`, and
  candidates `0x0A/0x09/0x04` (`샤먼/소서러/로드`). All three rows and their
  `용병/마법` details are visible in
  `captures/run/8ef4_c5_s03_candidate1.png` through `candidate3.png`.
- GSTs `captures/analysis/8ef4_c5_s03_preconfirm.gst` and
  `8ef4_c5_s03_confirm.gst` have identical player runtime and persistent roster
  class fields. Direct Start confirmation therefore proves navigation only; it
  is not an application path.
- End-turn-only checksum `A8D7` preserves the normal Start menu. Selecting
  `턴 종료` enters the stock level-up handler and changes runtime record 1 from
  class `0x03` to `0x0A`, resetting level to 1. The result is retained in
  `captures/analysis/a8d7_c5_s03_after_turn.gst` and visibly rendered as
  `헤인 / 샤먼 / LV 1` in
  `captures/run/a8d7_c5_s03_hein_shaman_applied.png`.

An in-battle `저장` confirmation in the isolated `A8D7` runtime did not set a
manual-slot valid flag or write a roster record to `save.sram`. It is not
accepted as persistent-save synchronization evidence. Runtime application is
proven; persistence across a normal scenario-clear save remains a separate
verification task.
