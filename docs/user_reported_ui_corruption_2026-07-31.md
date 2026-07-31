# User-reported preparation and shop corruption — 2026-07-31

## Outcome

Two independent VRAM ownership bugs explain the reported failures:

1. Preparation, deployment, hiring, and class/status surfaces reused the static
   Hangul extension ranges as commander and mercenary graphics. Reloading a
   full static font could therefore turn sprites into gray Hangul blocks, or
   turn commander/class/mercenary text into sprite fragments. The current
   candidate keeps the stock font on those surfaces and renders all 121 unsafe
   characters through 26 conflict-colored, ownership-audited scratch slots.
2. The item-name overflow bank put `넥클리스` token 68 (`클`) at VRAM
   `0xB600`, exactly where the shop stores a green page-arrow graphic. The
   compact 166-glyph description bank now ends at `0xA700`; name overflow uses
   `0xA700..0xB3FF`, so `클` is rendered at `0xA900`.

The Scenario 9 normal and hard candidates each pass 32/32 same-run pre/post
shop full-screen pairs, including seven allied commanders over two pages,
every offered hiring page, both roster pages, and all 13 fixed details. Both
profiles also pass the gray acted-sprite and real stock-victory result checks.
The `크로스`/`넥클리스` shop page was separately reviewed with each item
selected and both rows intact.

This is candidate evidence, not a release promotion. Scenarios 1–5 and 9 now
pass the complete normal/hard surface gate. Scenarios 6–8 and 10–27 still
require the same runtime matrix before the overall release gate can pass.

## Reported captures

The following desktop captures were supplied as historical manifestations of
the preparation/deployment corruption family:

- `화면 캡처 2026-07-29 003444.png`
- `화면 캡처 2026-07-29 015645.png`
- `화면 캡처 2026-07-29 015958.png`
- `화면 캡처 2026-07-29 025653.png`
- `화면 캡처 2026-07-29 110654.png`
- `화면 캡처 2026-07-29 111002.png`
- `화면 캡처 2026-07-29 114439.png`
- `화면 캡처 2026-07-29 133442.png`
- `화면 캡처 2026-07-29 133748.png`
- `화면 캡처 2026-07-29 134056.png`
- `화면 캡처 2026-07-30 003256.png`
- `화면 캡처 2026-07-30 003431.png`
- `화면 캡처 2026-07-30 003540.png`
- `화면 캡처 2026-07-30 003705.png`
- `화면 캡처 2026-07-30 003842.png`
- `화면 캡처 2026-07-30 014727.png`
- `화면 캡처 2026-07-30 183035.png`
- `화면 캡처 2026-07-30 183145.png`
- `화면 캡처 2026-07-30 183637.png`
- `화면 캡처 2026-07-30 183753.png`
- `화면 캡처 2026-07-31 022045.png`
- `화면 캡처 2026-07-31 022141.png`

The last two are Scenario 9 failure references. They are now covered by the
complete Scenario 9 normal/hard evidence in
`localization/preparation_surface_scenario_09.json`.

The shop-specific report is:

- `화면 캡처 2026-07-31 111759.png` — `크로스` is intact, while only the
  `클` in `넥클리스` is replaced by a green graphic.

Its root cause and accepted runtime captures are recorded in
`localization/item_shop_overflow_regression.json`.
The later class-change-fixed candidates differ from those two accepted shop
builds only at one checksum byte and the isolated class-change renderer
dispatch byte `0x2B7121`; all item glyphs, shop renderer code, and shop
graphics remain byte-identical. Thus both `크로스` and `넥클리스` evidence
applies unchanged to current normal `76D1` and hard-profile `D9B2`.

## Class-change mercenary-row `스`

The later capture `화면 캡처 2026-07-31 132324.png` exposed one more member of
the same static-extension lifetime family. On Elwin's
`메이지 -> 그랑나이트 / 실버나이트 / 아크메이지` class-change screen, the
two Arch Mage mercenary rows lost the shared final/third syllable in
`팔랑크스` and `발리스타`.

The class and mercenary records were correct. Class-change calls `0x02C004`
and `0x02C040` used the shared tile renderer, but that renderer still resolved
localized pair records through the ordinary static tile table. Candidate
graphics had already reused those static patterns. The tile renderer now uses
`BYTE_UI_PREP_LOCAL_TILE_LOOKUP_ROUTINE`, matching the other preparation and
class-change paths.

Fresh non-release normal and hard probes captured all three candidate rows.
The corresponding pairs are byte-identical, and the Arch Mage detail renders
both `팔랑크스` and `발리스타` intact along with the class sprite, statistics,
and magic rows. The failure and six passing frames are hash-locked by
`localization/class_change_mercenary_glyph_regression.json`. This remains a
candidate-only fix; no release ROM or version was promoted.

## Scenario 4 current-candidate closure

The class-change renderer change produced normal checksum `76D1` and hard
profile checksum `D9B2`. Both current candidates were therefore replayed
through the complete Scenario 4 preparation -> real shop item list ->
preparation sequence instead of relying only on the earlier candidate:

- normal `classfix04`: 20/20 byte-identical pre/post full-screen pairs;
- hard `classfix04`: 20/20 byte-identical pre/post full-screen pairs;
- all 40 accepted surfaces in each profile are also byte-identical to the
  previously reviewed Scenario 4 frames;
- the 44 current-candidate preparation/shop frames are byte-identical between
  normal and hard profiles.

The reviewed matrix includes all three allied commander/status pages, all
three offered hiring pages, the complete allied roster, the arrangement
minimap, and all ten preparation-visible fixed records. It keeps `워록`,
`바바리안`, `샤먼`, `파이크`, `다크엘프`, `호스맨`, every commander name,
all sprites, and every minimap row intact before and after the same-run shop
visit. The hidden masked-knight source record is explicitly not applicable
because its preparation coordinates are `(255,255)`.

Actual movement in both profiles produces the stock gray Elwin/Fighter
silhouette with runtime acted flag 1. A real stock Attack against Morgan then
reaches byte-identical `전과보고` frames with intact names, sprites, POINT,
borders, and numerical fields. The result probe changes only Elwin's
deployment coordinate and Morgan's AT/DF/mercenary fields; every Scenario 4
event byte is preserved.

Rejected attempts are retained in the generated Scenario 4 report: the first
normal gray run missed the scenario-selector timing and entered name entry;
the first result capture advanced to the save menu without a result GST; one
dialogue batch hit the 60-second host limit but resumed in the same emulator;
and the incomplete `classfix01` matrix hit the foreground 120-second host
limit. The accepted `classfix04` runs use an isolated background session and
completed normally. No release ROM or version was changed.

## Scenario 5 full current-candidate verification

The normal `76D1` and hard-profile `D9B2` candidates each pass 19/19 exact
same-run preparation/shop pairs in Scenario 5. The matrix covers all five
allied commanders and hiring pages, roster and arrangement/minimap surfaces,
and all five visible fixed records. The other four source records are hidden
at `(255,255)` and are explicitly accounted for as not applicable.

This closes the earlier `쉐리`, `웨어울프`, and `울프맨` symptoms on the
current candidates rather than on an older build. Actual movement also
produces the correct gray Fighter sprite. A narrowly scoped deployment-only
escape diagnostic reaches the stock north-escape completion and naturally
opens Sherry's three class choices. `로드`, `호크나이트`, `세인트`, their
mercenaries and magic rows, all sprites and statistics, and the final
`전과보고` are intact in both profiles. The diagnostic preserves every fixed
record and Scenario 5 event byte.

## Scenario 11 user-reported recurrence

Three later captures show that the user's currently running build still
reproduces the same preparation graphics/text ownership family in Scenario
11:

- `화면 캡처 2026-07-31 154702.png` — the Soldier and Armor Soldier
  mercenary rows are overwritten by sprite fragments and gray blocks;
- `화면 캡처 2026-07-31 154737.png` — the Mage detail has repeated gray
  blocks over Dark Elf and other mercenary rows;
- `화면 캡처 2026-07-31 154915.png` — the Crusader commander/class area and
  all repeated mercenary sprite/name rows are overwritten.

These are registered as failure evidence, not as the set of records to sample.
Scenario 11 will pass only after the latest candidates enumerate every allied
commander and hiring page plus every preparation-visible allied, NPC, and
enemy fixed record before and after a same-run shop visit. Hidden source
records may be marked not applicable only with their source coordinates.
Gray acted sprites, minimap, characters, borders, numerical fields, live
class changes where present, and the result surface remain mandatory.

The Scenario 5 focused gate passes 37/37. Full discovery runs 1,493 tests with
the same 44 failures plus 3 errors and the exact same sorted failing/error
test-name set as the Scenario 4 baseline. No release ROM or version was
promoted.

## Scenario 11 current-candidate verification result

The Scenario 11 recurrence is closed on the current normal `76D1` and
hard-profile `D9B2` candidates. Both profiles pass 27/27 exact full-screen
same-run shop pairs.

Coverage includes all six allied commanders, every hiring page, both roster
pages, arrangement/minimap, the 제시카 NPC record, all nine
preparation-visible enemy records, and the one source-hidden reinforcement
record explicitly accounted for at `(255,255)`. In particular:

- the reported 솔저 and 아머솔저 rows and sprites are intact;
- both 메이지 records retain 다크엘프 / 파이크 without gray blocks;
- every repeated 제국지휘관 row, class, mercenary name, and sprite is intact;
- all allied names/classes/hiring rows remain intact after the same-run shop
  visit.

The battle-side checks also pass. A real move produces the correct gray
Elwin/Fighter sprite. An unchanged stock pre-final-battle state was resumed
under freshly rebuilt current-candidate diagnostics, and a real Sherry attack
defeated the final reinforcement. Both profiles render the complete victory
dialogue and the same intact `전과보고 / POINT 3770P`.

The detailed checked report is
`localization/preparation_surface_scenario_11.json`. The three screenshots
remain retained as historical failure evidence; they no longer describe the
current candidates. The overall release gate is still pending because
Scenarios 6–8, 10, and 12–27 have not yet completed the same full matrix.

Focused Scenario 11 and related preparation regressions pass 57/57. Full
discovery runs 1,499 tests with the same 44 failures plus 3 errors and the
exact same sorted failing/error test-name set as the established baseline. No
release ROM or version was promoted.
