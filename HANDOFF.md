# Langrisser II Korean Patch Handoff

This project is currently a Japanese-ROM-based Korean localization prototype for
Mega Drive Langrisser II. The active builder is:

```bash
python3 scripts/build_korean_jp_probe.py
```

It writes:

```text
roms/builds/Langrisser II (Korean JP Probe).md
```

## Why The Work Moved From English ROM To Japanese ROM

The project originally started on the English ROM because the first visible
English fixed-width font was easy to replace. That approach produced early wins:
the opening `후후후...` text and some Scenario 1 prep/menu text appeared in
Korean.

However, the English-ROM approach caused repeated slot collisions:

- title screen letters such as `Press Start Button`, `Start`, `Load` broke when
  shared English font tiles were reused for Korean;
- `LV`, `MV`, `DF`, `P/F/V`-like status letters broke because some UI letters
  used alternate/shared glyph slots;
- command icons and order markers started showing Korean syllables because icon
  tiles and text tiles overlapped;
- the name entry screen and some dialogue paths used different fixed-font
  renderers, so fixing one screen often broke another;
- expanding the ROM alone did not solve the problem, because the game still
  referenced original indexed glyph/tile windows and sometimes restarted or
  crashed when code/data references pointed outside the expected range.

The Japanese ROM was chosen as the new base because it already has a 16x16
glyph-list text system that is closer to Korean text layout. Each text record
loads a local glyph list and the body uses local indexes. This makes it possible
to insert Korean glyphs into controlled high slots while preserving the original
screen code paths.

Important: the Japanese ROM is not one single text system. It still has multiple
paths:

- 16x16 Japanese glyph-list text for scenario/condition/large menus;
- small 8x8 byte UI font for prep/shop names and labels;
- one-byte 16x16 item/class/name paths in some shop/prep screens;
- sprite/tile resource paths for some route menu rows and popups.

So the current direction is not "replace every Japanese character globally".
Instead, identify the exact renderer/path for each screen, then patch only that
path.

## Files Not In Git

The repository intentionally ignores ROMs, generated builds, emulator binaries,
and captures:

- `roms/**/*.md`
- `tools/blastem/`
- `tools/blastem64-*.tar.gz`
- `captures/`

On a new machine, prepare these locally:

```text
roms/original/Langrisser II (Japan).md
```

For testing with BlastEm, either copy the existing `tools/blastem/` directory
from this machine or install/extract BlastEm locally. The current command line is:

```bash
env LD_LIBRARY_PATH=tools/blastem/lib \
  tools/blastem/blastem "roms/builds/Langrisser II (Korean JP Probe).md"
```

Python tools need Pillow and python-xlib:

```bash
python3 -c "import PIL, Xlib"
```

Do not assume system packages are installed on the next PC.

## Current Build Status

Last live-verified build during this handoff:

```text
checksum: 988E
```

The current source builds checksum `988E` and passes all 152 tests. It
includes all 31 scenarios' static event translations, the complete direct-name,
ending-visit, credits, and 90-record epilogue resources, plus the extended 8x8
commander-name font bank. Live regressions include Scenario 1 core UI, the
Scenario 27 ending/epilogue paths, Scenario 19 and 20 openings, and Scenario 25
through its complete unconditional opening. Static translation does not prove
all conditional event branches; the scenario sections below state the exact
remaining runtime gaps.

Build command:

```bash
python3 scripts/build_korean_jp_probe.py
```

Important recent local commits:

```text
1e9401c Add stock epilogue playback probe
72de5e9 Translate Lana character epilogues
efb6083 Translate Keith character epilogues
f21e0c3 Translate Sherry epilogues and restore battle UI
e1e2931 Translate Scott character epilogues
b4276bb Stabilize JP probe input and early UI patches
```

This document may have later commits after `d89ff79`; always start with
`git log --oneline -5` and inspect the latest `HANDOFF.md`.

## Durable Localization Direction

These requirements come from the user's running localization review and remain
in force across goal resumes:

- The Japanese ROM is the active base. Keep the old English-ROM path intact,
  but do not require an English ROM to build or verify the JP probe.
- Finish the current verifiable milestone first: the complete Scenario 1 play
  path and every prep/shop/arrangement/battle-command screen reachable from it.
  Continue toward full-game Korean localization after that milestone instead of
  treating Scenario 1 as the final project boundary.
- Preserve familiar compact game abbreviations such as `LV`, `AT`, and `DF`.
  They do not need Korean replacements when the original notation is clearer.
- Use `발드` consistently. Do not reintroduce `볼도` or `불도`. Scenario 1's
  escape condition must read `발드가 우하단 도주`.
- Match the Japanese condition-screen layout: victory/defeat headings and their
  entries must align cleanly, with no isolated dynamic `엘윈` name pages or
  unrelated oversized names before the conditions.
- Purchase and sale flows must be checked after the action, not only at menu
  entry. Expected messages include `단검을 구입함` and `단검을 판매함`, with
  no trailing corrupt glyphs.
- Scenario 1 verification must continue through the first completed player
  turn. Use the in-game end-turn command/input, advance the event that follows,
  and verify every resulting dialogue page. Localize any Japanese or corrupt
  text found there before considering the active goal complete.
- The in-battle `Start` menu is part of the same milestone. Its visible rows
  must read `저장`, `불러오기`, `승리조건`, `게임설정`, and `턴 종료` without
  Japanese remnants or broken glyphs. Verify `턴 종료` by using it to complete
  the first player turn, not only by inspecting the menu text.
- Treat the mixed Japanese/Korean name-entry grid as a mapping aid. Capture it
  when useful and compare visible glyphs with byte/tile codes rather than
  globally replacing shared font slots.
- The current WSLg environment is the only required runtime target. Emulator
  keyboard input and screenshots must work here; separate Ubuntu/Windows
  implementations are not required.
- Commit and push coherent verified checkpoints. Do not commit experimental ROM
  probes or broken intermediate builds.

## Active Scenario 1 Regression Checklist

The July 11 user playtest found that the Scenario 1 milestone is not complete.
Keep every item below in scope when the Codex goal is resumed:

- Localize the Japanese `Prologue` banner at the top of the Scenario 1 briefing.
- Fix the dagger description so no stray `4` appears below `AT+1`, and explain
  only real item statistics.
- Localize all four choices below Elwin's `명령` command, not only `이동`.
- Repair the broken `방어` label in the commander status window.
- Finish every Start-menu child screen: save confirmation and choices, load
  prompt and slot statuses, victory/defeat conditions, and game settings.
- Replace the opening Japanese dialogue quote mark after speaker names with a
  natural Korean separator such as `:` on every dialogue page.
- Localize Scenario 1's commander, NPC, enemy, class, and adjacent mercenary
  names. Verify Elwin, Hein, Liana, Leon, Laird, Bald, villagers, militia, enemy
  commanders, and every visible hired/default troop through cursor inspection.
- Repair the stray/corrupt `머서버` text shown below `레벨 1` in the upper-right
  area of Elwin's full commander status panel. Compare the same location with
  the original Japanese ROM before changing the owning byte-font/class slot.
- Keep the shared `레` glyph intact in both `레벨` and the cleric-class label;
  the A1/A2 status-icon slots must not be used for `레` or `온`.
- Advance the first player turn one page at a time and translate all remaining
  Japanese dialogue, including Leon, Laird, and Liana pages and job labels.
- Reproduce and fix the reset that occurs after advancing Laird's post-turn
  dialogue. A reset, freeze, black screen, or skipped page is a release blocker.
- Rebuild the ROM and verify every path above in BlastEm with screenshots before
  marking the active goal complete; then commit and push the verified checkpoint.

### July 11 Verified Result

Build `ABF6` completed this checklist in the WSLg BlastEm runtime. Its compact
money label was `소지G`; the later live-verified build `686D` restores it to
`소지금`:

- The Scenario 1 banner is `프롤로그`; the dagger shows `호신용 단검`, `AT+1`,
  and its real `50P` price without the stray `4`.
- Elwin's command panel and `명령` submenu render `이동/공격/치료/명령` and
  `이동/공격/방어/자동`; the full status panel renders `공격`, `방어`, `레벨`,
  and `지휘범위` without the former corrupt `머서버` text.
- Exact Scenario 1 class names are `클레릭` for Liana, `매직나이트` for Laird,
  and `나이트마스터` for Leon. `레` remains intact in both `클레릭` and
  `레벨`; live captures are `final_0228_elwin_status.png`,
  `final_0228_laird.png`, and `final_0228_leon.png`.
- The Start-menu save, load, condition, and config child screens are localized.
  Dialogue speaker names use `:` instead of the Japanese quote glyph.
- Commander and adjacent troop inspection confirms Elwin, Hein, Liana, Leon,
  Laird, Bald, militia/NPC labels, `솔저`, `가드맨`, `헤비호스맨`, and
  `로얄호스` on the Scenario 1 path. At that historical verification point the
  shop still used compact `ITEM`, `WPN`, `ARMOR`, and `소지G`; the later
  live-verified state replaces them with `장신구/무기/방어구` and `소지금`.
- The complete first-turn event was advanced page by page. The formerly mixed
  imperial-command line now reads `지금부터 발드님의 퇴로를
  확보하겠습니다!` (`final_924a_event_52.png`). The game reaches `TURN 2`
  (`final_924a_event_64.png`) and displays the following Hein and Elwin dialogue
  (`final_924a_event_65.png`, `final_924a_event_66.png`) without a reset, freeze,
  or black-screen failure.
- The class pointer table at `0x05E6D6` is now the source of truth. The builder
  validates each active class's original CP932 string before writing Korean, so
  an inferred label cannot silently replace a different Japanese class. Live
  verification confirms Laird's troop is original `ﾍﾋﾞｰﾎｰｽﾏﾝ` ->
  `헤비호스맨` (`class_exact_abf6_laird_merc2.png`) and Leon's blue troop is
  class 123, original `ﾛｲﾔﾙﾎｰｽ` -> `로얄호스`
  (`class_exact_abf6_leon_merc.png`). Leon himself remains `나이트마스터`.
- Scenario 1 prep hiring was also checked: Elwin offers original `ｿﾙｼﾞｬｰ` ->
  `솔저` (`class_exact_abf6_hire_list.png`), and Hein offers original
  `ｶﾞｰﾄﾞﾏﾝ` -> `가드맨` (`class_exact_abf6_hain_hire_list.png`). A resident
  renders `시민`, and an imperial foot unit renders `솔저` on the map.

## Emulator Input

BlastEm default keyboard mapping in this repo:

```text
Return = Start
d      = C / confirm
s      = B / cancel / fast-forward
arrows = D-pad
`      = save state
```

Automation scripts:

```bash
python3 tools/run_blastem_sequence.py prep
python3 tools/run_blastem_sequence.py shop
python3 tools/run_blastem_sequence.py shop-buy-list
python3 tools/run_blastem_sequence.py shop-buy
python3 tools/run_blastem_sequence.py shop-buy-sell
python3 tools/run_blastem_sequence.py shop-sell-list
python3 tools/run_blastem_sequence.py arrange
python3 tools/run_blastem_sequence.py deploy-dialogue
python3 tools/run_blastem_sequence.py battle-command
python3 tools/run_blastem_sequence.py first-turn-dialogue
python3 tools/run_blastem_sequence.py name-entry
python3 tools/run_blastem_sequence.py load-screen --reuse-runtime-state
python3 tools/capture_blastem_window.py captures/run/example.png
python3 tools/send_blastem_keys.py c:0.8
python3 tools/send_blastem_keys.py left:0.2 right:0.2 start+c@0.2:0.8
```

`tools/run_blastem_sequence.py` launches BlastEm with `320 240` width/height
arguments by default so automated tests do not occupy the full desktop after the
monitor-layout change. Use `--window-width 640 --window-height 480` when a
larger window is useful.

The reliable startup timing found on this PC is encoded in
`tools/run_blastem_sequence.py`: after launching, wait around 12 seconds, then
send `Start`, wait, `Start`, then `C` inputs. The user observed that sending the
first Start too early or too late can land in the attract/cutscene loop.

When using global XTest input, keyboard focus can be stolen by Barrier or another
window. If inputs do not affect BlastEm, first verify the emulator window has
focus.

## Verified Working Areas

- Opening intro shows Korean text including:
  - `후후후...`
  - `알하자드... 전설의 마검...`
  - `바라던 무한한 힘...`
- Scenario 1 description preserves the original dynamic hero-name controls, but
  aligns all four insertions with natural Korean sentences. There are no blank
  or isolated `엘윈` pages.
- Scenario condition labels show Korean:
  - `※승리조건`, `·발드 격파`
  - `※패배조건`, `·엘윈 사망`, `·발드가 우하단 도주`
- Force labels on condition screens were localized:
  - `아군`
  - `적군`
  - `중립`
- Prep screen main labels are mostly Korean:
  - `엘윈`, `헤인`
  - `전사`
  - `용병고용`, `장비착용`, `상점`, `지휘관배치`
- One-byte UI Korean glyph codes are stabilized in
  `BYTE_UI_STABLE_CODE_BY_CHAR`. This prevents a new byte UI patch from shifting
  existing labels such as `엘윈` into unrelated glyphs such as `아이`.
- Prep status panel bottom labels are fixed:
  - original `シキハイ` / 指揮範囲 -> `지휘범위`
  - original `シュウセイ` / 修正 -> `수정`
  - stats use the conventional compact labels `AT`, `DF`, `LV`, `MV`, `MP`
- Shop item purchase path has working item text:
  - first item `단검`
  - description `호신용 단검` and `AT+1`
- Shop purchase/sale paths are verified:
  - titles `아이템 구입`, `아이템 판매`
  - completion messages `단검을 구입함`, `단검을 판매함`
  - no corrupt tile after the dagger name
- Commander arrangement shows all five Korean rows: `지휘관배치`,
  `이동순변경`, `자동배치`, `적군보기`, `출격`.
- The in-battle Start menu shows `저장`, `불러오기`, `승리조건`, `게임설정`,
  `턴 종료`.
- Battle commands are live-verified for both commanders: Elwin shows
  `이동/공격/치료/명령`, and Hein shows `이동/공격/마법/치료/명령`. `소환` is
  patched in the same contiguous command stream but is unavailable to their
  current Scenario 1 classes.
- `first-turn-dialogue` reaches the Scenario 1 post-turn event. Its five pages
  show Korean speaker names/body text (`주민`, `제국군지휘관`, `레온`,
  `레아드`) and continue into `ENEMY PHASE`.
- Name entry screen currently defaults to `엘윈`, and it is a useful probe for
  seeing which Japanese byte/glyph slots now render as Korean.

### Byte UI Graphic Collision Regression (2026-07-13)

- User testing found Korean-looking fragments cycling in the blue, red, and
  green unit overlays (`키/코/론`, `젤/름`, `보/카/면`, and `손`) plus an
  apparent `박` near the terrain percentage and another preparation-screen
  fragment. This was not dialogue corruption. The expanded name-entry grid had
  assigned Hangul to ASCII byte-font codes `0x3B`, `0x5B..0x7E`, even though
  the live game also uses those font-resource tiles for animated faction,
  terrain, and panel graphics.
- Rejected assumption: lowercase Latin was unused because localized UI strings
  do not print it. ROM text searches are insufficient for this resource; the
  renderer addresses the same tile numbers as graphics.
- Fix: `BYTE_UI_GLYPH_CODES` uses the verified half-width-kana window
  `0xA5..0xDF`. Prep stats use `AT/DF/LV/MV/MP`, which the user explicitly
  accepts, and the Korean name-entry grid is temporarily limited to 57 unique
  syllables with unused cells blank. Its navigation labels use ASCII `OK/NO`.
  The equipment categories are now `무기/방어구/장신구`; their five overflow
  glyphs use only original uppercase letter tiles `J/Q/W/Y/Z`. `B/K/U` remain
  original for `BGM`, `OK`, and the small in-map `TURN` label. Do not extend
  this exception to `X` (`EXP`) or to lowercase/punctuation graphics.
  A future full Hangul name grid needs a screen-specific font-resource swap;
  it must not expand into shared ASCII/status tiles again.
- Automated regression: `test_byte_ui_patch_preserves_ascii_and_status_graphics`
  decompresses the original and patched byte-font resources and asserts every
  tile in `0x00..0xA4` except the five declared uppercase extensions, and every
  tile in `0xE0..0xFF`, is byte-identical. All byte UI Hangul mappings must
  remain within `0xA5..0xDF` or the explicit `J/Q/W/Y/Z` set.
- Fresh-boot live verification used the rebuilt ROM, not a GST carrying old
  VRAM. Captures under `captures/analysis/safe_byte_font_s1/` cover the allied
  animation (`fresh_blue_00.png` through `_15.png`), enemy
  (`fresh_enemy_00.png` through `_11.png`), NPC (`fresh_npc_00.png` through
  `_11.png`), preparation (`fresh_prep.png`), and equipment
  (`fresh_equipment_open.png`). No reported Hangul fragments remain, terrain
  `%` graphics are intact, and the prep/equipment panels show no extra glyph.
- Korean equipment-category verification is under the same directory:
  `korean_categories_equipment.png` live-verifies `무기`, while
  `korean_equipment_categories_offline.png` renders all three owning strings
  (`0x0A18E0`, `0x0A18EC`, `0x0A18F8`) as `무기/방어구/장신구`.
- Build after the fix: checksum `C56C`, 763 custom 16x16 glyphs. The name-entry
  resource test suite passes 6 tests. The full suite has one expected baseline
  failure because the uncommitted Scenario 22 translation raises the modified
  physical-page count from 1,740 to 1,812; do not mistake that for this UI fix.

## Known Remaining Problems

- Some established route/in-map banners remain English, such as `SCENARIO 1`,
  `TURN 1`, and `ENEMY PHASE`. The user explicitly allows familiar compact game
  notation; these are not blockers for the Scenario 1 milestone.
- Only Scenario 1 gameplay path has been heavily tested. The script contains
  broader item/class/scenario patches, but many later screens remain unverified.
- Xlib capture can catch BlastEm's clearing half-frame and produce a mostly
  black PNG even while gameplay is stable. Capture a second frame about one
  second later before treating it as a game black-screen regression.
- Do not overwrite broad font slots casually. Previous attempts broke title
  screen text, name entry, command icons, and status labels.

## Tried And Rejected / Do Not Repeat Blindly

This section records dead ends and partially disproven assumptions. Use it before
trying a "simple" patch.

### English ROM Fixed-Font Patch

Tried: replace English fixed font tiles with Korean syllables and patch English
strings directly.

Result: worked for some early visible text, but broke too many shared tiles.
Typical regressions were:

- title screen `Press Start Button`, `Start`, `Load` became mixed Korean/garbage;
- name entry screen lost most letters or showed Korean syllables in the alphabet
  grid;
- `LV`, `MV`, `DF`, `P/F/V`-style status letters changed shape or disappeared;
- order icons/command markers became Korean syllables;
- dialogue and menu fonts did not share one renderer, so fixing one screen often
  damaged another.

Conclusion: do not continue broad English fixed-font replacement as the main
path. The Japanese ROM path is the active path.

### "Just Double The ROM Size"

Tried/considered: expand the ROM and place every Korean asset after the original
data.

Result: expansion is useful for relocated glyph lists and resources, but not
sufficient by itself. Many game routines still load only an original local
glyph/tile window or expect indexes within a fixed range. In earlier tests,
references outside expected windows could produce black screens, resets, or
unmapped address fatal errors.

Conclusion: use expansion only when the code path has been verified to follow a
relocated pointer. Do not assume any renderer can see new high-offset data.

### Global Japanese Glyph Replacement

Tried/considered: find Japanese font slots and replace them globally with Korean.

Result: unsafe. Japanese glyph slots are shared by unrelated text, UI, and
possibly tile/icon-like uses. It can make one screen readable while corrupting
another. Some "Japanese-looking" text on screen is not read from the main 16x16
glyph table at all.

Conclusion: identify the actual renderer and local glyph list per screen. Patch
specific strings/lists, not the whole Japanese font blindly.

### Scenario 1 Class Names And Byte-Font Slot Limits

Source of truth: the big-endian class pointer table at `0x05E6D6`. Read each
original `0xFF`-terminated byte string as CP932. Do not infer a class from the
sprite or translate every mounted unit generically as `기병`.

Incorrect attempt: class 103/104 and 121/122/123 were initially shortened to
`기병`/`중기병`. This also hid the fact that Leon's blue adjacent troop uses
class 123 (`ﾛｲﾔﾙﾎｰｽ`), not class 103 (`ﾎｰｽﾏﾝ`). The corrected active mappings
are enforced by `SCENARIO1_EXPECTED_JP_CLASS_LABELS`; important examples are:

```text
103  ﾎｰｽﾏﾝ        -> 호스맨
104  ﾍﾋﾞｰﾎｰｽﾏﾝ    -> 헤비호스맨
109  ｶﾞｰﾄﾞﾏﾝ       -> 가드맨
123  ﾛｲﾔﾙﾎｰｽ      -> 로얄호스
```

Failed slot attempt: build `C833` temporarily added byte codes `0x80..0xA0`
to fit more Hangul syllables. The build succeeded offline, but the live full
status panel rendered the first syllable of `공격` as a red icon. Those codes
are not safe text slots in the battle renderer and were removed. Codes
`0xA1`, `0xA2`, and `0xA4` and the `0xE0..0xFF` range are likewise reserved by
live status graphics. Do not re-enable them based only on offline font output.

The byte-font pool is renderer-dependent and must be rechecked after every new
syllable. The equipment labels use `무기/방어구/장신구` through the explicit
safe uppercase-tile exception documented above; `NPC` remains compact where
needed. Later-scenario classes outside
`BYTE_UI_SCENARIO1_CLASS_INDEXES` are not claimed as verified; add them only
after checking their original table entry and live renderer, then rebalance the
safe glyph budget deliberately.

### `0x974xx` Direct Name Candidates

Tried: patch direct strings around `0x97404` because offline rendering looked
like character/monster names.

Result: these candidates are not the visible JP name-entry table and can collide
with data/control paths. Earlier unsafe name patches could break progress after
name confirmation.

Conclusion: keep `UNSAFE_DIRECT_NAME_PATCHES` disabled unless revalidated with a
specific screen and save-state comparison.

### `0x018082` Shop Title Attempt

Tried: add `0x018082` (`ｱｲﾃﾑ ｾﾝﾀｸ`) to `BYTE_UI_STRING_PATCHES` as
`아이템소지` to remove the remaining shop title prefix.

Result: offline byte UI rendering changed, but the live shop title did not
become correct. Worse, adding this string at the front of the byte UI patch set
shifted the generated one-byte Korean glyph-code assignment. In the live game,
`엘윈` then rendered as `아이` in shop/prep UI. This was reverted and the build
returned to checksum `8034`. A second attempt inserted the patch at the end of
the dictionary, preserving `엘윈/헤인`, but the live shop title still stayed
`アイテム소지`, so this address is not the visible title owner for that screen.

Conclusion: do not patch `0x018082` by simply adding it to the shared byte UI
patch dictionary. If revisiting it, keep byte-code allocation stable or give the
title a dedicated code path.

### Shop Title Tile Loader

Found: routine `0x2792E` chooses the direct title token stream at `0xA17A4` or
`0xA17B8`, then writes tile IDs as `0x680 + token*4`. This bypasses the normal
local text renderer.

Tried: shorten `0xA17A4` to tokens `3,4,5` to hide the Japanese `アイテム`
prefix.

Result: it removed the prefix but produced incomplete titles such as `소지`, so
it was removed from the active build.

Tried: patch the purchase-side script at `0xA177E` by treating the words after
the apparent loader header as plain glyph IDs.

Result: unsafe. That script includes an `FFF9`-controlled substream. In a test
build it reached the title normally but could blank/freeze while entering the
shop. Do not use this as the purchase-title fix without disassembling the
substream ownership.

Current: `0xA1716` is a 31-glyph VRAM list, not a short message string. It owns
the purchase title and both completion suffixes. The sale screen initially loads
`0xA16D4`, then reloads `0xA1716`; therefore `0xA17B8` now uses common slots 11
and 12 for `판매`. This is verified as `아이템 판매` in the live sale list and
completion popup.

### Name Entry Default

Tried: patch default hero name to Korean through byte-string/default buffer
paths.

Result: visible behavior was inconsistent. Japanese name entry and later game
state do not use one simple string path. Some attempts showed Korean in one
place but caused black screen/reset after confirming the name.

Current: the default name and prompt are Korean (`엘윈`, `이름을 정해주세요`).
The mixed Japanese/Korean grid is intentionally retained as a glyph/code mapping
probe; do not globally rewrite it at the expense of shared font safety.

### Arrangement Route Menu As Linear Grid

Tried: treat the commander arrangement route menu as five rows of five 16x16
glyph slots and overwrite a continuous range near `0xA2B6E`.

Result: wrong. It scrambled rows into combinations like `관배치순서`, while
`移動順変更` still remained. The menu mixes direct strings, sprite/tile paths,
and reused out-of-order fragments.

Conclusion: do not patch that menu as a simple continuous grid.

2026-07-10 follow-up: on build `BC63`, the remaining visible Japanese came from
VRAM plane C tile IDs:

- `移動順変更`: tile IDs `5A0-5B3`;
- `自動` prefix: tile IDs `5B4-5B7`;
- the menu window nametable starts at VRAM plane C around `0xC000`.

Searching raw ROM bytes and the `0x0B0000` 4-byte graphics resource table did
not find these tile bytes, so the source is likely another compressed/tile path.

Resolved follow-up: both rows ultimately use the screen-local glyph list at
`0xA2BAC`. Patching only that six-glyph list produces `이동순변경` and
`자동배치` without touching global glyph shapes.

### Arrangement Menu Glyph-Shape Substitution

Tried: replace glyph shapes for suspected original glyph IDs in
`ARRANGE_MENU_GLYPH_SHAPE_PATCHES`.

Result: did not remove all visible Japanese, and can affect unrelated text if
those glyphs are shared.

Conclusion: current build leaves `ARRANGE_MENU_GLYPH_SHAPE_PATCHES = {}`. Use a
screen-specific source trace instead.

### Shop Item Name By Arbitrary Byte Codes

Tried: replace `0x060405` (`ナイフ`) with arbitrary Korean byte UI codes for
`단검`.

Result: the item name disappeared from the live shop list. Offline tools could
render some data, but the shop renderer did not display the new arbitrary code
path.

Conclusion: preserve raw bytes `C5 B2 CC` at `0x060405` and change the wide
16x16 glyph shapes for those original byte codes instead.

### Item Name/Description By Appending New Local Glyph Slots

Tried: append Korean glyphs to the relocated item glyph list and point the first
item name/description at the new slots.

Result: offline render tools showed Korean, but the live shop screen did not.
The live shop only loaded the original low local glyph window for the visible
first item/description.

Conclusion: for Scenario 1 shop, reuse original low local slots:

- possession title slots `0..5` for `아이템소지`;
- first item name tokens `6,7,8` for `단검` plus space;
- description slots `0..7` for `호신용 단검`;
- keep original `AT+1` slots available instead of replacing them.

### Item Purchase / Possession Messages

Tried: use `ITEM_TITLE_TEXT` alone to control the shop title.

Result: this did not control every live shop/possession overlay.

Tried: patch `0xA1716` as a fixed title string.

Result: wrong. `0xA1716` is a shop message record with control words
`0000 0001 0012 0020`. Overwriting it as a title caused the post-purchase popup
to show a stray `입` after `단검`.

Conclusion: do not truncate `0xA1716`. Preserve all 31 entries and patch only
the owned slots. The current build shows `단검을 구입함` and `단검을 판매함`
without a trailing corrupt tile.

### Status Panel Labels

Tried: patch only byte layout string `0x0A3D15` for `シキハイ`.

Result: the live prep status panel still showed Japanese. The actual visible
panel also uses 16-bit tile ID sequences.

Conclusion: the working patch includes all of:

- `0x0A3D15` byte layout string -> `지휘범위`;
- `0x09AB36`, `0x09ACA8` word/tile sequences -> `지휘범위`;
- `0x09AB8C`, `0x09ACF0` word/tile sequences -> `수정`.

### VDP/VRAM Rendering Tool Pitfall

Tried: inspect VRAM with the old `tools/render_md_vram_tiles.py` output.

Result: that renderer displayed vertical stripe artifacts for some Mega Drive
tiles because it treated the 4bpp tile bytes like bitplanes. A quick custom
nibble-based renderer showed the screen correctly.

Conclusion: if VRAM images look like vertical bars, do not trust that output for
glyph identification. Use a correct Mega Drive 4bpp nibble renderer or fix
`render_md_vram_tiles.py` before making conclusions.

### BlastEm Input Timing

Tried: send keys step-by-step while inspecting each intermediate screen.

Result: slow inspection lets the attract/cutscene loop start and desynchronizes
the sequence. Also, Barrier or another focused window can steal key input.

Conclusion: for repeatable tests, use `tools/run_blastem_sequence.py` and avoid
mid-sequence screenshots unless debugging timing itself. If input seems ignored,
check focus first.

## Still Unclear / Needs Investigation

- `SCENARIO 1` route/menu title: not yet patched. It may be tied to system menu
  strings and should not be changed blindly.
- `SCENARIO` at ROM `0x0D48E` and `TURN` at `0x05E351` are ASCII strings, but
  patching them through the byte UI fixed-string path did not affect the live
  in-map `SCENARIO 1` / `TURN 1` banners on build `795E`; those banners also
  use a different tile/graphic path.
- Later scenarios/items/classes are not live-tested. The build script contains
  broad data, but Scenario 1 is the only heavily verified path.

## Important Implementation Notes

The Japanese ROM uses several text/font paths. Treat them separately.

### 16x16 Japanese Glyph Path

- Base font starts at `0x40000`.
- One glyph is 64 bytes.
- The conversion matches the ROM routine at `0x2C390`.
- Custom Korean glyphs are currently placed in high slots beginning around
  `0x7000`.

This path is used by scenario text, condition screens, and many large menu
strings.

### Small 8x8 Byte UI Font

- Font resource table: `0x0B0000`
- Resource index: `1`
- Original resource pointer: around `0x0B0A84`
- Builder relocates the decompressed/recompressed font resource to `0x290000`.

This path is used by many prep/shop small labels and commander/class/name text.

### One-Byte 16x16 Shop Item Path

The first shop item name `ナイフ` at `0x060405` is special. It is rendered as
large 16x16 text, but still uses one-byte item-name codes.

The working approach is:

- keep raw bytes `C5 B2 CC` at `0x060405`
- patch the wide 16x16 glyph shapes for those byte codes:
  - `0xC5` -> `단`
  - `0xB2` -> `검`
  - `0xCC` -> blank

Replacing `0x060405` with arbitrary Korean byte UI codes made the item name
disappear in the shop list.

### Item Name/Description Local Slots

The shop only loads a limited original local glyph window for the first item.
For Scenario 1 shop, the first item must reuse original low local slots:

- item name local slots `0,1,2` -> `단`, `검`, blank
- first description local slots `0..7` -> `호신용 단검`
- original local slots `9..12` must remain available for `AT+1`

Appending new Korean glyph slots worked in offline render tools but did not show
on the live shop screen.

## Useful Debug Commands

Render item names from the relocated item glyph list:

```bash
python3 tools/jp_text_font_analyzer.py \
  --rom "roms/builds/Langrisser II (Korean JP Probe).md" \
  render-pointer-text \
  --pointer-table 0xA1902 \
  --low 0xA1990 \
  --high 0xA1B90 \
  --glyph-list 0x282000 \
  --cols 12 \
  --scale 4 \
  --out item_names_current.png
```

Render item descriptions:

```bash
python3 tools/jp_text_font_analyzer.py \
  --rom "roms/builds/Langrisser II (Korean JP Probe).md" \
  render-pointer-text \
  --pointer-table 0xA1D7C \
  --low 0xA1E10 \
  --high 0xA2C00 \
  --glyph-list 0x286000 \
  --cols 15 \
  --scale 3 \
  --out item_desc_current.png
```

Render direct strings around the prep/menu region:

```bash
python3 tools/jp_text_font_analyzer.py \
  --rom "roms/builds/Langrisser II (Korean JP Probe).md" \
  render-direct-strings \
  --start 0x97000 \
  --end 0x97800 \
  --base 0x40000 \
  --format jp2bpp16 \
  --scale 3
```

Capture current BlastEm window:

```bash
python3 tools/capture_blastem_window.py captures/run/current.png
```

Save BlastEm state with the mapped backtick key:

```bash
python3 tools/send_blastem_keys.py save:0.8
cp ~/.local/share/blastem/'Langrisser II (Korean JP Probe)'/quicksave.gst \
  captures/analysis/current.gst
```

GST VRAM starts at `0x12478` for these BlastEm save states.

## Suggested Next Step

After the verified Scenario 1 milestone, continue later-scenario live testing
in order. Keep `SCENARIO 1`/`TURN 1` banner work separate from normal text: the
known ASCII tables do not own those live graphics. Use the existing per-screen
glyph/list approach and add a reproducible sequence before enabling any broad
name/font table patch.

## July 11 Continued Regression And Scenario Editor

This section is the newest source of truth. It records work after build `ABF6`.

### Naming Policy

- The MD Japanese ROM determines the class/mercenary ID, original name, and
  three-tier MD composition. Do not copy a PC/remake composition onto MD data.
- Use Namu Wiki's Langrisser 2, mercenary, class, and class-change pages for
  established Korean spelling after the ROM identity is known. The URLs are
  recorded in `README.md`.
- The MD source confirms Scenario 1 Leon as class `0x45` (`나이트마스터`)
  with mercenary `0x7B` (`로얄호스`), and Laird as class `0x37`
  (`매직나이트`) with two `0x7A` (`헤비호스맨`) slots.

### Money And `제` Glyph Regression

- `POINT` fields at `0x09ABC2` and `0x0A1896` now render `소지금`; the leading
  currency icon is not overwritten. Live build `686D` verified this in prep
  and shop.
- Byte-font code `0xA3` is unsafe for dynamically assigned glyphs in the full
  battle renderer. It caused broken `제` in `제국지휘관`/`사제`, just as
  `0xA1`, `0xA2`, and `0xA4` caused status icon collisions. `제` is pinned to
  the live-stable `0xC0` slot. Existing screen-specific `구`/`템` assignments
  remain fixed until their shop paths are deliberately reworked.
- Do not expand the apparently free byte-code pool based only on offline font
  output. Verify every new slot in the complete commander/status panel.

### First-Turn Support Event

- Event page `0x185664..0x18568A` is patched to
  `기다려!\n이 마을에서 멋대로 못해!`. A 21-character draft exceeded the
  20-character record and failed the build; the current 19-character text fits.
- Build `686D` was advanced through the support event. The militia commander
  displayed `민병대 / 로드`; the priest commander displayed a clean Korean
  class label; the support dialogue no longer contained Japanese.
- Reverse engineering later proved the priest source record is class `0x9C`,
  whose original class pointer is `ﾌﾟﾘｰｽﾄ`. The current source therefore maps
  it explicitly to `프리스트`, not `하이프리스트`. This correction produces
  build `7C92` and still needs one live check when emulator work is allowed.
- Dialogue speaker `자경단` is the original `自警団` speaker label. The map
  unit name `민병대` is a separate compact unit label; keeping both is
  intentional.

### Class Pointer Table Correction

- Runtime code loads normal big-endian pointers from `0x05E6D6`. The former
  analyzer started at `0x05E6D8` and reconstructed each pointer from adjacent
  16-bit words. That happened to work through class 155 but read garbage for
  final class 156 because no following pointer supplied the high word.
- `scripts/build_korean_jp_probe.py` and `tools/jp_byte_table_analyzer.py` now
  use `0x05E6D6`, 157 entries (`0..156`), and direct big-endian reads.

### Scenario Fixed-Placement Format

The scenario header pointer table is `0x18005E` and has 31 valid entries. For
each header, the long pointer at `header + 0x0C` leads to a two-byte record count
followed by fixed-placement records of `0x24` bytes each.

Verified record fields:

```text
+0x0E  level
+0x12  AT
+0x13  DF
+0x18  initial X (FF when waiting for an event)
+0x19  initial Y (FF when waiting for an event)
+0x1A  name ID
+0x1B  class ID
+0x1E  mercenary class ID slot 1
...
+0x23  mercenary class ID slot 6
```

Scenario 1's list is at `0x1801B6`, count 12, records at `0x1801B8`. Known
enemy records are:

```text
index  ROM       name          class  LV  AT  DF  mercenaries
8      0x1802D8  발드          0x2E    4  21  18  0x72 x6
9      0x1802FC  레온          0x45    4  40  31  0x7B
10     0x180320  레아드        0x37    6  33  25  0x7A x2
11     0x180344  제국지휘관    0x2D    1  19  18  0x72 x6
```

The first-turn support records are hidden initially (`X=Y=0xFF`): militia at
`0x180200`, class `0x99` (`로드`), and priest at `0x180224`, class `0x9C`
(`프리스트`). These values come from ROM records, not sprite inference.

### Scenario Editor

- `tools/scenario_data.py` parses all 31 fixed-placement lists and only writes
  verified fields. Unknown flags and coordinates remain read-only.
- `editor/server.py` plus `editor/static/` provides a local UI for scenario
  selection and class/LV/AT/DF/six-mercenary editing.
- It reads either the latest Korean build or Japanese source and writes
  `roms/builds/Langrisser II (Korean Scenario Edit).md`; it never overwrites the
  input ROM. The Mega Drive checksum is recalculated.
- `tests/test_scenario_data.py` validates all 31 list pointers, exact Scenario 1
  Leon/Laird data, field patching, and checksum output.
- A no-change editor build was byte-identical to Korean build `7C92`. Desktop
  and mobile screenshots were checked before the user asked to stop GUI work.
- This is deliberately a data editor, not yet a map/event editor. Do not expose
  unknown record bytes until their runtime ownership is proven.

### Automation Attempt And Final Live Check

- `battle_command_menu_visible` previously mistook blue portrait/cutscene
  frames for the command menu. Bottom status-bar and dark-panel checks plus a
  delayed second capture were added. The delayed check was increased from 0.7
  to 2.0 seconds; this is detector confirmation time, not game input delay.
- The improved detector still encountered transient cutscene candidates during
  the last attempt. Do not treat that interrupted run as a ROM reset result.
- Build `7C92` captured every post-turn confirmation as
  `captures/run/regression_7c92_postturn_01.png` through `_75.png`. It reached
  `TURN 2` at `_67.png`, then displayed the Hein/Elwin dialogue without a reset.
  Empty dialogue boxes at `_17.png` and `_23.png` are transition frames before
  full-screen narration, not missing text pages.
- Final build `5B8A` independently reached `TURN 2` in
  `regression_5b8a_turn2_banner.png`. The final support status is
  `regression_5b8a_support_priest_status2.png`: `사제 / 프리스트` and
  `NPC 유닛입니다` are intact. The enemy notice is verified in
  `regression_5b8a_enemy_notice2.png` as `적군 유닛입니다`, with the leading
  `제` in `제국지휘관` intact.
- The active localization goal's runtime checks are complete. The command-menu
  detector can still be improved later using saved-frame classification, but
  it is no longer a release blocker for Scenario 1.

### Shared Unit-Type Notices

- The battle UI glyph list at `0x9706A` is shared by commands and unit notices.
  Its original slots 39..42, 16, and 17 spell `ユニットです`.
- Notice token streams are enemy `0x09AEE4`, NPC `0x09AF04`, and already-acted
  `0x09AF26`. Their original prefixes are `敵の`, `NPC`, and `行動済み`.
- The builder validates every original token sequence before writing
  `적군 유닛입니다`, `NPC 유닛입니다`, and `행동완료 유닛입니다`. Slot 17
  is explicitly changed to the global space glyph so other notices cannot end
  in a stray Japanese `す`.
- Intermediate build `3079` proved the NPC suffix but left the enemy prefix
  Japanese. Build `3024` fixed the enemy prefix but did not yet blank the
  shared trailing `す`. Final build `5B8A` contains both corrections.

## Full Localization Goal And Stage 1 Inventory

The Scenario 1 goal was completed at build `5B8A`. The active follow-up Goal is
full-game Korean localization, split into six stages in
`docs/full_localization_plan.md`: inventory, shared UI/global names, Scenarios
2-10, Scenarios 11-20, Scenarios 21-31/endings, and final regression/release.

- The 31-entry event-block pointer table is `0x18011A`. Scenario 1 begins at
  `0x18416A`; Scenario 31 begins at `0x1B8378`. The current conservative end of
  event data is `0x1B9000`.
- `tools/jp_event_inventory.py` finds in-block 32-bit references whose targets
  parse as at least three glyph IDs (`0x0000..0x07FF`) plus `FFF7`/`FFFE`
  controls and an `FFFD`/`FFFF` terminator.
- The baseline inventory contains 2,968 candidate records and 3,567 physical
  pages. Build `1DD0` modifies 431 candidate records and 532 physical pages:
  Scenario 1 is 107/121 records, Scenario 2 is 110/110, Scenario 3 is 89/89,
  and Scenario 14 is 125/125. Scenarios 4-13 and 15-31 are unstarted.
- A modified page is not automatically complete Korean. Scenarios 2, 3, and 14
  now have reviewed full-page data; Scenario 1 still contains older partial
  work and must be reviewed for complete natural text and control safety.
- Machine-readable page addresses, source references, terminators, and glyph
  token streams are in `localization/event_pages.json`; the coverage table is
  `docs/full_localization_inventory.md`.
- English extraction JSON remains legacy reference material. Its addresses and
  control layout are not authoritative for Japanese-ROM writes.

### Global Byte-String Inventory Checkpoint

- `tools/jp_global_inventory.py` inventories three genuine FF-terminated
  pointer tables: 157 classes at `0x05E6D6`, 38 item entries at `0x060364`,
  and 117 actor/NPC/monster names at `0x0618E8`.
- `tools/scenario_data.py` previously stopped the name table at 105 entries.
  The verified count is 117 (`0x75`); the editor/parser limit was corrected.
- Current direct byte-string changes are classes 28/157, items 0/38, and names
  25/117. These are coverage signals, not verified translation counts.
- The inventory separately compares the original byte codes' 16x16 global
  font pixels. The knife keeps original codes `C5 B2 CC` while those glyphs
  render `단`, `검`, and blank. Twelve other item strings reuse at least one of
  those codes, so their alternate byte-font render paths are collision risks,
  not localized entries.
- Detailed original hex/text, pointers, capacities, known Korean targets, and
  affected font codes are in `localization/global_strings.json`; the summary is
  `docs/global_localization_inventory.md`.
- All 117 name IDs now have explicit Korean targets in `tools/scenario_data.py`.
  Repeated Japanese pointers retain one consistent label: monster runs cover
  Werewolf through Demon Lord, IDs 104-109 map the custom `qyu` bytes to the
  separately rendered Japanese `アニキ` (`형님`), and IDs 110-115 cover
  witch, priest, imperial soldier, and Faias. ID 116 is the repeated blank.
  This completes metadata identification, not live ROM patching of every path.
- The user-provided Namu Wiki pages were retried during this checkpoint but
  were inaccessible to the web tool and returned no searchable results. No
  names were changed from unreliable snippets; Japanese ROM IDs remained
  authoritative.

### Shared 16-bit Word Resources

- `tools/jp_resource_inventory.py` records the other known global text paths
  without treating byte changes as proof of completion. Every entry has
  explicit `reviewed` and `live_verified` flags, initially false.
- Current modified baselines are: conditions 31/32 (the final record is shared
  preparation UI and intentionally preserved), scenario descriptions
  31/31, item names 38/38, item descriptions 37/37, magic names 23/23,
  mercenary battle names 15/15, and battle status messages 3/3.
- Scenario descriptions 2-31 came from legacy machine-translated material.
  Their 31/31 byte-change count is not a translation-quality result.
- All 31 scenario conditions are statically patched; later scenarios still
  need real-index live verification. Summoned creature labels are class-table IDs and stay tracked in
  `localization/global_strings.json` rather than a fabricated summon table.
- Machine-readable details are in `localization/shared_word_resources.json`;
  the summary is `docs/shared_word_resource_inventory.md`.

### Declared UI Patch Surfaces And Gaps

- `tools/jp_ui_surface_inventory.py` inventories 75 UI patch declarations
  already present in the builder. 74 change bytes in the current build; the
  unchanged declaration is the intentionally retained `NPC` abbreviation.
- The compressed 8x8 byte-UI font is resource table `0x0B0000`, index 1. Its
  table entry at `0x0B0004` moves from `0x0B0A84` to `0x290000`.
- This is a declared-patch inventory, not a whole-ROM proof. The report keeps
  explicit gaps for class-change UI, save/load variants, ending/credits UI,
  magic/summon prompts, non-Scenario-1 equipment/shop variants, ownership of
  other compressed resources, and undeclared executable-embedded strings.
- Details are in `localization/ui_patch_surfaces.json`; the summary and gap
  list are in `docs/ui_patch_surface_inventory.md`.

### Complete Compressed Resource Table

- `tools/jp_compressed_resource_inventory.py` derives the resource count from
  the first pointer in table `0x0B0000`. The first block begins at `0x0B06B4`,
  so the table contains exactly 429 strictly increasing pointers; its last
  original pointer is `0x13807E`.
- The type-byte distribution is type 1: 2, type 2: 248, and type 3: 179.
  Dispatcher `0x0099FA`
  routes type 1 to `0x009A38`, type 2 to `0x009C10`, and only type 3 to the
  builder-equivalent `0x009DFE` decoder. Type 1 is verified 4-bit RLE; its two
  blocks decode to 384 and 224 bytes. All 179 type 3 blocks also decode and hash.
  Type 2 reconstructs 32-byte work tiles from a width-1/2/4 mask stream, then
  performs the game's four-plane bit transpose and optional 16-nibble palette
  remap. All 248 type 2 blocks decode and hash. The 429 resources produce
  903,296 bytes in total. Do not repeat the earlier incorrect assumption that
  every table entry uses `0x009DFE`.
- Only index 1 differs in the current build. It is the independently confirmed
  8,192-byte small UI font, relocated from `0x0B0A84` to `0x290000` with its
  decompressed glyph content changed. The other 428 owners remain deliberately
  unknown; successful decompression is not evidence that a resource is UI or text.
- Full pointers, types, output sizes and decoded SHA-256 values are in
  `localization/compressed_resources.json`; the summary is
  `docs/compressed_resource_inventory.md`. Tests enforce the table boundary,
  type counts, all three decoders, a fixed type 2 sample hash, and the single
  known relocation.
- Loader wrapper `0x0099B2` calls lookup `0x009A0E`, which masks the high flag
  bit, multiplies the resource ID by four, and reads `0x0B0000[index]`; the
  type 3 decompressor is `0x009DFE`. There are 75 direct calls to the wrapper:
  64 use an immediate ID and map 50 distinct resources, while 11 choose their
  ID dynamically. The inventory records all call addresses, immediate IDs,
  high-bit flags, and destinations without inventing IDs for dynamic calls.
- No emulator or desktop input was used for this checkpoint.

### Direct Word-String Candidate Scan

- `tools/jp_direct_string_inventory.py` scans `0x000000..0x180000` for at
  least three glyph IDs (`0000..07FF`), known controls, and `FFFF` termination.
  Scenario event blocks are covered separately by `jp_event_inventory.py`.
- Baseline remains 783 candidates. After offline rendering and pointer-interval
  ownership analysis, all 783 are classified and zero remain unclassified.
  The current build differs at 256 candidate starts.
- The old 14/97 counts were conservative scanner suffix matches, not complete
  dialogue-record counts. Pointer tracing proved that the 14 ending visit
  records begin at `0x0954E2`; their long `FFFF`-terminated bodies continue
  through `0x096C58`, with nine shorter Liana-branch records linked from the
  same script table at `0x09540C..0x0954DF`. The remaining 90 matches below
  `0x0954E2` are still-untranslated character-epilogue fragments. The inventory
  now classifies all 22 ending suffix matches under their 23 complete translated
  records instead of calling them untranslated pages.
- Other candidates are assigned to exact pointer records/interiors, declared
  patches, unsafe name records, credits, name-entry resources, local UI token
  streams, item/shop resources, or render-confirmed code/structured-data false
  positives. The combined unclassified render sheet is
  `captures/analysis/jpfont_probe/direct_unclassified_jp2bpp16.png`.
- New matches still require rendering or code-reference proof before patching;
  never bulk-write a scanner result merely because it matches the byte pattern.
- Detailed tokens and ownership are in
  `localization/direct_word_candidates.json`; the summary is
  `docs/direct_word_candidate_inventory.md`.

### Static System And Word-Item Localization Checkpoint

- Offline rendering identified shared system fragments at `0x082ACE..0x082B90`:
  level/AT/DF/MP increase, one/two-point increase, spell learned/usable, item
  obtained, Treasure-kun label, and item equipped. The builder verifies every
  original token tuple before writing Korean.
- `GAME OVER` at `0x082B3C` intentionally remains conventional English. The
  Japanese secret/debug-style message at `0x082B78` rendered as
  `面をしないだすー`; web searches did not establish its runtime context, so
  it remains untouched rather than guessed.
- A separate word-swapped 37-entry item-name pointer table starts at `0x001068`.
  Its strings span `0x0010FE..0x0012E8`; two Langrisser IDs share `0x00115E`,
  leaving 36 unique strings. The builder validates source block SHA-256
  `16d62e68434c815650971ceb5a0a4d87d354698a653952888ce8861611ff5da4`
  and the complete pointer tuple before patching all 37 IDs.
- Build checksum after these static patches is `9B03`. Offline captures are
  `captures/analysis/jpfont_probe/direct_082ACE_082B9F_jp2bpp16.png`,
  `direct_0010F0_0012F6_jp2bpp16.png`, and the exact knife capture
  `direct_0010FE_001106_jp2bpp16.png`.
- No emulator was launched for this checkpoint at the user's request. These
  entries are statically rendered but not `live_verified`; stop before any GUI
  or input automation until the user is ready.
- Candidate classification recognizes pointer-record starts/interiors, credits,
  name-entry resources, ending/epilogue pages, screen-local battle tokens, and
  structured-data false positives. The current unclassified count is zero.

### Name-Entry Static Ownership

The earlier default-name-only conclusion was superseded by a live-verified
confirmation hook. The former 84-syllable experiment is historical: it reused
shared byte-font status/icon codes and was retired. The current production grid
contains 57 safe syllables as documented below and in
`docs/name_entry_analysis.md`.

### Class-Change Static Patch

- Code `0x02BB60` loads the 15-slot glyph list at `0x0A3C9C`. Layout
  `0x0A3CBA` uses slots 0..10 for `クラスチェンジできます`; layout
  `0x0A3CDC` uses 0..6 for the title, and slots 11..14 are `傭兵/魔法`.
- The Korean slot plan is `클래스체인지`, space, `가능`, two spaces,
  `용병마법`. It preserves every existing token index and renders the long
  prompt, short title, and detail labels without code/layout changes.
- The builder validates the complete original 15-word tuple. Static build
  checksum is `DBE1`; offline output is
  `captures/analysis/jpfont_probe/class_change_a3c9c_korean.png`.
- Tests cover the three direct code references, shared-index plan, source
  rejection, and patched word layout. Emulator navigation and dynamic class
  candidate rendering remain not `live_verified` at the user's request.

### Korean Name Grid And Scenario 1 Turn-Event Regression (2026-07-12; superseded grid size)

- The name-entry layout is the byte-tilemap at `0x0A38E0..0x0A3B0A`; its
  decoded size is 40x28. The selectable glyph list is `0x0A37E6` (95 words)
  and the selection-to-byte table is `0x0A3B3E` (95 bytes).
- This section originally verified an 84-syllable grid. That allocation is no
  longer active because later whole-UI testing proved that it overwrote shared
  status, faction, and icon byte-font tiles. The production grid now exposes
  57 unique Korean syllables at indexes 0..53 and 55..57; all other cells stay
  blank. Keep index 70 reserved for the original `ヴ` composite path and index
  `0x54` as blank/delete.
- Failed approach: storing `0x7000`-series glyph IDs directly in the editable
  name buffer. Code `0x02B070` treats that word as an index into `0x0A3B3E`,
  so high values blanked or destabilized the screen. Low fallback glyph IDs
  avoided that lookup failure but corrupted shared glyphs such as shop digits.
- Correct approach: keep selection indexes in RAM `0xD1A8`. Hook the original
  18-byte confirmation copy at `0x02B046` and call the relocated routine at
  `0x2A0000`, which writes `0x0A37E6[index]` into dialogue glyph RAM `0xA5DE`.
  The following original conversion still writes stable byte values to
  `0xA5CC`.
- Before the hook, the default speaker rendered as Japanese `ハヘ` even though
  prep/status showed `엘윈`. Checksum `0E8A` verifies `엘윈` in dialogue and
  a manually selected high custom name `폴` through route, prep, and dialogue:
  `captures/run/0e8a_dynamic_name_fixed.png`,
  `captures/run/0e8a_name_selected_pol.png`,
  `captures/run/0e8a_pol_prep.png`, and
  `captures/run/0e8a_pol_dialogue_3.png`.
- The first-turn event was advanced one input at a time through residents,
  imperial officers, Leon/Laird/Bald/Liana, militia support, enemy movement,
  and Elwin/Hein response. No reset occurred after Laird. The initial capture
  sequence is `captures/analysis/0e8a_turn1_events_sheet.png` and later event
  sheets use the same checksum prefix.
- Two blank pages followed long Leon records because explicit translated
  newlines plus fixed-length padding pushed blank cells onto another screen.
  Removing those forced newlines, and shortening the militia response, fixes
  the layout. Checksum `8A01` is reverified in
  `captures/analysis/8a01_event_00_23.png`; the previously blank positions now
  contain the next dialogue immediately.
- `tools/send_blastem_keys.py` now accepts `load` for BlastEm's `L` state-load
  binding. Automated command-menu detection is still timing-sensitive; a
  failed detector can select Move even when the game itself is healthy.

### Condition-Table Relocation Probe Warning (2026-07-12)

- Do not test a later condition by replacing condition/glyph pointer table
  entry 0 with a later entry. Scenario 1 preparation also depends on entry 0;
  the pointer-only probe made its large menu blank and eventually restarted.
- Later condition screens must be reached through the game's real scenario
  index (normal save progression or the built-in scenario-select command).
  Static pointer/token rendering does not justify marking them live verified.
- Live subset testing isolated the real boundary: condition entries 1-31 can
  all be patched in place and keep preparation intact; changing entry 32 alone
  blanks the large preparation-menu labels. The game has 31 scenarios, so the
  final table entry is a shared preparation resource rather than another
  scenario condition. The corrected patch leaves entry 32 byte-for-byte
  original and translates entries 1-31 at their original pointers. Failed
  relocation variants were never committed.
- Final ROM checksum `8AAD` is byte-identical to the successful 1-31 subset
  probe. `captures/run/condition_first_31_prep2.png` verifies that names,
  numbers, and all four large preparation labels remain visible. Automated
  tests also assert that entry 32's pointer, glyph list, and 113-word stream
  remain byte-for-byte Japanese-original data.
- A fresh Scenario 1 in-game save was created from the live `8AAD` Start menu.
  It did not persist because the 4 MiB ROM overlapped the original 2 MiB SRAM
  base. Checksum `8C4D` relocates SRAM and all verified absolute save addresses
  to `0x400001..0x403FFF`; Japanese saves now load and Korean saves persist.
  The earlier confirmation had overlapping/mixed choice glyphs; checksum
  `F639` fixes that UI independently from the SRAM mapping.

### SRAM And Real-Index Condition Verification (2026-07-12)

- Root cause and all patched addresses are in `docs/sram_relocation.md`.
  `tests/test_sram_relocation.py` guards the expanded-ROM/SRAM boundary and all
  13 verified long-address operands/table entries.
- A Japanese valid autosave appears as `CONTINUE 1` on checksum `8C4D`.
  A subsequent Korean save changed the runtime SRAM hash and increased its
  nonzero byte count, verifying both load and store paths.
- Scenario select requires a manual slot, not `CONTINUE`. Highlight slot 1-4,
  enter Left, Right, Start, C, choose the scenario with Up/Down, and confirm.
  `tools/send_blastem_keys.py` now also supports chord syntax such as
  `start+c@0.2`, although the working code was the documented sequential input.
- Scenario 14's seven-row conditions are live-verified in
  `captures/run/8c4d_scenario14_conditions_live.png`. Scenario 23's long
  rod-carrier/escape conditions are live-verified in
  `captures/run/8c4d_scenario23_conditions_live.png`.
- The same run exposes remaining full-localization work: Scenario 14 event
  dialogue is still Japanese, the title-screen Load path is Japanese, and the
  scenario-selector suffix is Japanese.

### Start Save/Load Record Boundaries (2026-07-12)

- The Load prompt at `0x09B066` has 14 cells and a mandatory `FFFF` at
  `0x09B082`. The previous 17-cell patch crossed that terminator and the next
  record. Checksum `F639` limits the prompt to 14 cells and preserves every
  following fixed record boundary.
- The save-choice record has `FFFD` at `0x09AE56`, then its `0003 0002`
  layout header at `0x09AE58`. Writing from `0x09AE56` had erased the control
  word. The corrected patch writes after it and uses compact original Latin
  glyphs for clear `YES/NO`, which the user permits for familiar game UI.
- `captures/run/40db_save_prompt_live.png` verifies the clean confirmation.
  `captures/run/f639_ingame_load.png` verifies `불러올 데이터를 선택하세요`,
  dynamic `23장`, `턴 1`, and `손상된 데이터` in the in-battle Load screen.
- `tests/test_start_submenus.py` guards the control words, terminators, record
  widths, and Latin glyph IDs. The separate title-screen Load display remains
  Japanese and must not be marked complete from this in-battle capture.

### Legacy English Dialogue Ownership Map (2026-07-12)

- `script_extract/english_records.json` contains 3,082 records. The first three
  bytes preserved in each record are an event continuation value, not the
  address of its Japanese text page. Never write to the Japanese ROM by treating
  `prefix` as a string pointer.
- `tools/english_dialogue_inventory.py` classifies those continuation values
  against the 31 Japanese event blocks. It assigns 2,978 records to scenarios
  and 104 records to ending/epilogue data outside the event blocks. Exact rows
  are in `localization/english_dialogue_mapping.json`; the summary is
  `docs/english_dialogue_mapping.md`.
- Scenario 14 owns one contiguous English reference run, indexes `383..510`
  (128 records), while its conservative Japanese pointer scan finds 125 text
  pages. Other scenarios also differ by a few records. Aligning lists solely by
  ordinal position is therefore unsafe; controls and visible Japanese text must
  be checked at each insertion/deletion point.
- `machine_korean_reference` is the old Google output and is explicitly marked
  `reference_only`. It is useful for rough meaning only and must never be shipped
  without natural Korean review and Japanese control preservation.

### Scenario 14 Reviewed Dialogue (2026-07-12)

- A candidate pointer target is not always one visible dialogue page. Long
  records contain consecutive `FFFD`-terminated physical pages before the final
  `FFFF`. The original inventory counted 2,968 candidate records but hid these
  continuations. `tools/jp_event_inventory.py` now expands only spans that parse
  exactly up to the next candidate target. The final candidate in each block is
  followed only through its first `FFFF`, not blindly to the block boundary:
  3,567 physical pages are exposed. Scenario 14 has 125 candidate records and
  162 physical pages.
- `localization/event_dialogue_ko.json` stores reviewed text and `{NNNN}` dynamic
  name placeholders. The builder verifies every original address, capacity,
  terminator, and `FFF7` actor ID before writing. Scenario 14 now covers all 125
  pointer records plus 37 continuation pages, 162 physical pages total. The
  aligned English references are records `385..395` and `397..510`; record 396
  is the verified insertion/deletion boundary and is intentionally skipped.
- The first attempt patched only pointer targets. Build `F5BF` showed Japanese
  continuation pages after the first Korean Jessica page. This was not a reset;
  it proved the physical-page omission. Build `6EDC` translated the continuations
  and reached Aaron/Hein and the battle map without a reset, but one blank page
  remained because forced Korean newlines pushed fixed padding to another screen.
- Build `92CB` removes those forced newlines. The production build also promotes
  only four isolated Scenario 14 speaker names into the safe direct patch set:
  `쉐리` (`0x97420`), `아론` (`0x97444`), `레스터` (`0x9744E`), and `제시카`
  (`0x97458`). `captures/analysis/921f_s14_speakers.png` verifies 쉐리, 레스터,
  제시카, 엘윈, and 헤인 labels before the final newline adjustment.
- `captures/analysis/92cb_s14_intro_verified.png` is the final consecutive live
  sequence. The first Jessica lore page proceeds directly to `그래서 왕은…`
  with no blank box; the sequence reaches Korean Aaron/Hein and the interior
  event without a reset. The interior capture shows Japanese `エルウィン`
  because the scenario-selector manual slot was created from an old Japanese
  save and that event inserts the saved custom protagonist name. A fresh Korean
  name-entry/default-name confirmation is independently verified by the `92CB`
  name-entry captures; do not mistake the diagnostic SRAM payload for a fixed
  speaker-table regression.
- Do not enable the entire `UNSAFE_DIRECT_NAME_PATCHES` map. Probe `1E28` entered
  a black screen during Scenario 14. A two-name probe `4212` proved `제시카`
  alone rendered correctly; the four-name production subset then passed the
  name-entry grid and default-name confirmation at checksum `92CB` in
  `captures/run/92cb_name_entry.png` and `captures/run/92cb_name_confirmed.png`.
  Continue isolating later names in scenario-sized batches.
- `tools/render_event_pages.py --scenario 14` renders address-labelled physical
  pages from the ROM passed with `--rom`, rather than echoing inventory-source
  tokens. Checksum `F9AC` renders all 162 Korean pages under
  `captures/analysis/event_pages_ko/` and the 14 contact sheets cover the entire
  scenario. Automated tests prove that the declared address set exactly equals
  the modified physical-page set and that all controls, dynamic actor IDs, page
  terminators, and fixed capacities are preserved. Build, both inventories,
  and all 65 tests pass.
- Live verification currently covers the opening Jessica/Aaron/Hein sequence,
  transition into the map, and absence of the former blank page/reset. Later
  battle branches (Runestone, Langrisser attempts/competition, retreat/death
  quotes, and the scenario ending) are translated and statically rendered but
  are not yet all reached by live play. Keep them open in the scenario checklist
  until each reachable path is captured without a reset or freeze.
- A local `/tmp` Tesseract Japanese package was used only as an OCR aid; rendered
  source images remain the authority because OCR frequently misreads the Mega
  Drive font.

### Scenario 2 Reviewed Dialogue (2026-07-12)

- `localization/event_dialogue_ko.json` now covers all 110 Scenario 2 pointer
  records and 27 continuation pages, 137 physical pages total. Primary pages
  align one-to-one with English reference records `1991..2100`; Japanese ROM
  pages and controls remain authoritative. All declared page addresses exactly
  equal the modified physical-page set in automated tests.
- The old suffix-only direct patches did more than leave mixed Japanese/Korean
  lines: patch `0x18698E` overwrote the actor ID following `FFF7` at
  `0x186976`. `patch_reviewed_event_pages` now validates capacities,
  terminators, and actor IDs against the untouched Japanese ROM rather than the
  already-mutated build buffer, then rewrites the complete page. This restores
  every Scenario 2 dynamic-name control to the original value.
- The first live pass at checksum `7637` exposed blank padding boxes between
  continuation pages. Scenario 2's reviewed physical pages are at most 58
  words, so explicit Korean newlines were unnecessary; fixed-length space
  padding after those newlines crossed a display boundary. Removing all forced
  newlines produced checksum `99D3` and eliminated the blank boxes throughout
  the consecutive night sequence. Captures are
  `captures/analysis/99d3_s02_intro_00_29.png` and the two morning sheets
  `captures/analysis/99d3_s02_intro_30_49.png` / `_50_69.png`.
- Scenario-sized safe speaker-name promotion adds `스코트` (`0x97432`),
  `발가스` (`0x97482`), `졸름` (`0x974AA`), `지휘관` (`0x97504`), and
  `로렌` (`0x97526`). Checksum `2DBE` live-verifies 로렌, 스코트, 지휘관 and
  the dynamic 발가스/졸름 names in `captures/analysis/2dbe_s02_morning_00_24.png`
  and `captures/analysis/2dbe_s02_names.png`. The same build opens the Korean
  name-entry grid normally in `captures/run/2dbe_name_entry.png`; do not promote
  the remaining unsafe-name map as one batch.
- The scenario-select manual slot was created by the Japanese ROM, so saved
  custom protagonist insertions still render `エルウィン` during this diagnostic
  run. Fixed speaker names and a fresh Korean default-name path are independent;
  the latter remains verified by the name-entry capture. Do not record the old
  SRAM payload as a current name-table failure.
- Live verification reaches the entire night conversation, morning meeting,
  imperial ambush, and the first playable command without reset or freeze.
  Optional combat, defeat, item, rescue, and ending branches are translated and
  statically rendered but remain open for route-specific live capture.

### Scenario 3 Reviewed Dialogue (2026-07-12)

- All 89 pointer records plus 17 continuations are reviewed, for 106 physical
  pages total. Primary pages align with English references `2223..2311`, while
  Japanese page images determine wording and control placement. The build keeps
  all original `FFF7` IDs and `FFFD`/`FFFF` terminators and uses no forced
  newlines, preventing the Scenario 2 blank-padding regression.
- Checksum `1DD0` renders the complete Korean scenario under
  `captures/analysis/event_pages_ko/scenario_03/` and nine contact sheets. The
  address-set test proves that all 89 candidates and all 106 physical pages are
  declared and modified; all 67 tests pass.
- Live Scenario 3 selection, Korean briefing, deployment, opening mountain-pass
  conversation, default `YES` escort choice, Korean `졸름` speaker label, and
  first playable command are captured in
  `captures/analysis/1dd0_s03_intro_00_19.png`. The repeated command-menu frames
  in `_20_39.png` are automation continuing to press C after dialogue ended,
  not a game loop or freeze.
- The default escort branch reaches play without a blank page or reset. Other
  escort choices, combat deaths/retreats, Attack-magic hint, ambush, and ending
  conversations are translated and statically rendered but still need their
  own live route captures. The diagnostic scenario-select SRAM continues to
  insert its old Japanese custom protagonist name; fresh Korean name entry was
  independently verified at checksum `2DBE`.

### Scenario 1 Complete Reviewed Dialogue (2026-07-12)

- Scenario 1 now owns all 121 Japanese pointer records and all 145 physical
  pages in `localization/event_dialogue_ko.json`. The English reference has 122
  records because it split Japanese record `0x1849B4` and its second physical
  page `0x1849DA` into records 2107 and 2108. Address-based alignment therefore
  uses primary references `2101..2107, 2109..2222`, with 2108 attached only to
  continuation page `0x1849DA`; ordinal alignment after that point is invalid.
- Every reviewed page preserves its Japanese-ROM `FFF7` actor IDs and
  `FFFD`/`FFFF` terminator, contains no forced newline, and fits the original
  word capacity. The complete Korean render is under
  `captures/analysis/event_pages_ko/scenario_01/`, with 13 contact sheets named
  `scenario_01_pages_00.png` through `_12.png`.
- Checksum `A964` was live-tested from the diagnostic scenario-select SRAM
  through the opening dialogue, first command, Start > turn end, NPC/enemy
  phases, Leon/Liana abduction dialogue, and Laird's reinforcement arrival.
  It did not reset at the former post-Laird failure. Captures are in
  `captures/analysis/a964_s01_intro/`, `a964_s01_intro_sheet.png`,
  `a964_s01_turn1/`, and `a964_s01_turn1_sheet.png`.
- The diagnostic SRAM still supplies Japanese cached names to `FFF7` for the
  saved protagonist and Bernhardt. The ROM byte-name entry for name ID 14 at
  `0x061B00` is now patched to `베른하르트`; checksum `3647` passes all 69
  tests. Re-entering through the same diagnostic save still showed the cached
  Japanese name, so that run cannot validate the new ROM entry. A clean
  `first-turn-dialogue` macro attempt ended on a black frame before reaching
  the command detector. Do not treat either result as proof that the fresh-game
  dynamic insertion is broken or fixed; repeat this check from a freshly made
  Korean save.
- Current event inventory is 2,968 candidate records / 3,567 physical pages,
  with 445 candidate records / 550 physical pages modified. Complete reviewed
  scenarios are now 1, 2, 3, and 14. Optional Scenario 1 combat/death/item and
  victory branches are statically translated but still need route-specific
  live captures.

### Scenario 31 Complete Reviewed Dialogue (2026-07-12)

- Scenario 31 / X4 Death Tower now owns all 44 Japanese pointer records and 46
  physical pages. The English map contains a stray cross-scenario record 1434;
  Japanese screenshots show that the real contiguous mapping is English
  records `1572..1615`. Do not align this scenario from the first English row.
- All pages preserve their original controls and terminators, fit the Japanese
  capacity, and use no forced newlines. The full Korean render and four contact
  sheets are in `captures/analysis/event_pages_ko/scenario_31/` and
  `scenario_31_pages_00.png` through `_03.png`.
- Checksum `F3B0` was entered through the scenario selector and reached the
  Death Tower map and first Korean Egbert dialogue without a blank page or
  reset. That run exposed the still-Japanese Egbert speaker label. The fixed
  16-bit speaker entry `0x974B2` and byte-name ID 20 at `0x061B28` are now
  patched to `에그베르트`; checksum `E96D` passes all 71 tests. A follow-up
  navigation attempt stopped in commander preparation before re-reaching the
  dialogue, so the new speaker label still needs one direct live capture.
- Inventory is now 489/2,968 candidate records and 596/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 14, and 31. Scenario 4 has
  129 Japanese records / 155 physical pages, but its English-ROM order diverges
  from Japanese after several branches; translate it from Japanese renders and
  use English only as a semantic reference.

### Scenario 29 Complete Reviewed Dialogue (2026-07-12)

- All 49 Japanese pointer records and 55 physical pages are reviewed. English
  records 198/199 are unrelated rows incorrectly grouped into this scenario;
  Japanese records 0..46 align with English `1170..1216`. The final two
  Japanese-only lines at `0x1B761C` and `0x1B764C` describe the strange defeated
  squad and the completed ship preparations for Velzeria, and are translated
  directly from the Japanese render with `english_record: null`.
- Checksum `A434` preserves every control/terminator and passes all 72 tests.
  Complete Korean renders and five sheets are under
  `captures/analysis/event_pages_ko/scenario_29/` and
  `scenario_29_pages_00.png` through `_04.png`.
- The diagnostic selector invoked with `--scenario-number 29` entered an ending
  montage instead of Japanese event block 29. The selector's late-row ordering
  is not the event-block numbering, so this is not a dialogue crash. Scenario
  29 remains statically verified and needs a valid route save or corrected
  selector-row map for live entry.
- Inventory is now 538/2,968 candidate records and 651/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 14, 29, and 31.

### Scenario 30 Complete Reviewed Dialogue (2026-07-12)

- Scenario 30 / X3 now covers all 65 Japanese pointer records and 70 physical
  pages. English records 1217/1218 are the two Japanese-only Scenario 29 ending
  lines grouped on the wrong side of the English extraction; Japanese records
  0..63 align with English `1370..1433`. The last Japanese record at `0x1B832A`
  has no English equivalent and tells the party to leave the transformed girl
  alone and escape the dangerous cave.
- Checksum `2D3A` passes all 73 tests. Six complete Korean contact sheets are in
  `captures/analysis/event_pages_ko/scenario_30/`.
- Live scenario-selector row 30 correctly enters X3. The run passed briefing,
  deployment, cave discovery, the girl encounter, dragon encirclement, and the
  first playable command without a blank page or reset. Captures are under
  `captures/analysis/2d3a_s30_intro/`, with the command menu at frame 22. Fixed
  speakers such as Lester and Liana render in Korean; the diagnostic SRAM's
  saved protagonist name remains Japanese as previously documented.
- Inventory is now 603/2,968 candidate records and 721/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 14, 29, 30, and 31.

### Scenario 24 Complete Reviewed Dialogue (2026-07-12)

- Scenario 24 now covers all 53 Japanese pointer records and 65 physical
  pages. The English project splits Japanese physical pages 6 and 7 into
  different records and merges several later continuations, so the mapping is
  stored per physical address rather than by ordinal. English records
  `1569..1571` are stray rows that do not occur in this Japanese block.
- Japanese pages `0x1B037A` and `0x1B03A8` have no English equivalents. They
  preserve the closing resolve not to let the peaceful world end and to set
  out to restore it, with `english_record: null` and `japanese_only: true`.
- All 65 pages preserve their Japanese `FFF7` controls and `FFFD`/`FFFF`
  terminators, fit their original capacities, and contain no forced newline.
  The complete static render and six sheets are in
  `captures/analysis/event_pages_ko/scenario_24/` and
  `scenario_24_pages_00.png` through `_05.png`.
- Checksum `DC6D` was entered through selector row 24, commander preparation,
  automatic deployment, and the live `SCENARIO 24 / TURN 1` map without a
  reset or blank screen. Captures are under
  `captures/analysis/dc6d_s24_intro/`. The translated event pages are mostly
  conditional combat/seal events, so their individual live routes remain to
  be exercised even though every physical page is statically verified.
- That run exposed the mixed warning `지휘관배치가終了していません`. Its
  local stream is `0x0A2C2E`; unused local glyph slots 32..39 at `0x0A2B9C`
  now hold `가끝나않았습니다`, and the stream renders
  `지휘관배치가끝나지않았습니다`. The patch validates both original arrays
  before writing. Checksum `58DB` was live-captured at
  `captures/analysis/58db_arrange_warning_live.png` and passes 75 tests.
- Inventory is now 656/2,968 candidate records and 786/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 14, 24, 29, 30, and 31.

### Scenario 21 Complete Reviewed Dialogue (2026-07-12)

- Scenario 21 now covers all 71 Japanese pointer records and all 80 physical
  pages. The primary records align in order with English `912..980` followed
  by `1168/1169`; nine Japanese records continue onto additional physical
  pages. Every `{0002}`, `{0010}`, `{0014}`, and `{0060}` dynamic-name control
  is retained at its original address.
- Checksum `A813` preserves every `FFF7` control and `FFFD`/`FFFF` terminator,
  fits every original page capacity, and uses no forced newline. Seven Korean
  sheets are in `captures/analysis/event_pages_ko/scenario_21/` and
  `scenario_21_pages_00.png` through `_06.png`.
- Selector row 21 entered the correct `SCENARIO 21` ship map. Automatic
  deployment reached `TURN 1`, and the live opening displayed Aaron's
  `호오… 여기가 벨제리아인가.` followed by Scott's `서둘러 상륙하자.` before
  returning to player control. Captures are under
  `captures/analysis/a813_s21_intro/`.
- The first live run exposed a `battle_command_menu_visible()` false positive:
  the broad blue sea in `advance_02.png` was mistaken for a command panel.
  The detector now rejects crops over 85% blue and accepts the ornate status
  bar at a 45% blue threshold. Synthetic tests and the real captures classify
  Scenario 30's `22.png` as a command menu and Scenario 21's water cursor as
  plain control. The run stopped before issuing another confirmation.
- Inventory is now 727/2,968 candidate records and 866/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 14, 21, 24, 29, 30,
  and 31.

### Scenario 5 Complete Reviewed Dialogue (2026-07-12)

- Scenario 5 now covers all 79 Japanese pointer records and all 87 physical
  pages. English `2442/2443` are previous-scenario residue; Japanese primaries
  0..75 align with `2444..2519`. English has only one final village pursuit
  row (`2520`), while Japanese primaries 76..78 are three route-specific
  variants, so all three deliberately reference `2520`.
- Every `{0001}` and `{0016}` name control and every `FFFD`/`FFFF` terminator
  is preserved, all pages fit their original capacity, and no forced newline
  is used. Eight Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_05/`.
- Checksum `7E02` entered selector row 5, commander preparation, automatic
  deployment, `SCENARIO 5 / TURN 1`, and the first translated pursuit line.
  This exposed the Japanese fixed speaker `モーガン` even though the dialogue
  body was Korean. Live evidence promoted only the isolated candidate
  `0x0974C8` to `모건`; the rest of the formerly unsafe name-table batch stays
  untouched.
- Checksum `5D62` was then re-entered through the same path and shows `모건:
  서둘러! 빨리 달아나지 않으면 놈들이 따라잡을 거야.` correctly. Captures
  are in `captures/analysis/7e02_s05_intro/` and the final fixed frame is
  `captures/analysis/5d62_s05_morgan_live.png`.
- Inventory is now 806/2,968 candidate records and 953/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 21, 24, 29, 30,
  and 31.

### Scenario 23 Complete Reviewed Dialogue (2026-07-12)

- Scenario 23 now covers all 83 Japanese pointer records and 92 physical
  pages. English record `1369` is previous-scenario residue. Japanese
  primaries 0..79 align with `1489..1568`; the three final Langrisser seal
  lines were incorrectly grouped under English Scenario 24 as `1569..1571`,
  but physically complete this block. The real mapping is therefore the
  contiguous range `1489..1571`.
- All `{0001}`, `{0003}`, `{000D}`, `{0010}`, and `{0011}` controls and all
  `FFFD`/`FFFF` terminators are preserved, every page fits its source capacity,
  and no forced newline is used. Eight complete sheets are under
  `captures/analysis/event_pages_ko/scenario_23/`.
- Checksum `8C6B` entered selector row 23, automatic deployment, the Holy Rod
  temple map, and `TURN 1`. Laird's opening line and the following imperial
  commander line render in Korean, followed by the room-search camera motion
  without a reset or blank screen. The command-menu detector did not fire
  during 15 confirmations; the final frames are plain map control, so input
  stopped there. Captures are under `captures/analysis/8c6b_s23_intro/`.
- Inventory is now 889/2,968 candidate records and 1,045/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 21, 23, 24, 29,
  30, and 31.

### Scenario 16 Complete Reviewed Dialogue (2026-07-12)

- Scenario 16 now covers all 87 Japanese pointer records and all 98 physical
  pages. Japanese primaries 0..85 align with English records `511..596`.
  English `705/706` physically complete Scenario 15; the final Japanese record
  at `0x1A1F78` is a source-only two-page resolve to defeat the Emperor and
  rescue the controlled ally.
- Every dynamic-name control and every `FFFD`/`FFFF` terminator remains on its
  original physical page. All text fits the original capacity and uses no
  forced newline. Nine complete Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_16/`.
- Build `7183` first reached the Scenario 16 route map, preparation screen,
  automatic deployment, `TURN 1`, and four opening dialogue steps without a
  reset. That live pass exposed the particle-sensitive form `エルウィン와`.
  The reviewed text now avoids dynamic-name particle errors throughout this
  scenario, including `과`, `만`, `따윈`, and `폐하` phrasing.
- Final checksum `0E2D` was re-entered one input step at a time and verifies
  the first line plus `하지만 덕분에 エルウィン과 다시 맞설 기회가 왔다!`.
  The Japanese names in these diagnostic frames come from the old Japanese
  manual-save roster used by the built-in scenario selector, not the fixed
  speaker table. Fresh Korean name entry was independently verified earlier,
  so do not enable the unsafe whole `0x974xx` patch set for this symptom.
  Captures are under `captures/analysis/0e2d_s16_intro/`.
- A fast combined input attempt on `0E2D` ran ahead of screen transitions and
  returned to the opening sequence. Re-entering with staged inputs succeeded;
  treat this as automation timing, not a ROM reset regression.
- Inventory is now 976/2,968 candidate records and 1,143/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 16, 21, 23, 24,
  29, 30, and 31.

### Scenario 15 Complete Reviewed Dialogue (2026-07-12)

- Scenario 15 now covers all 110 Japanese pointer records and all 118 physical
  pages. English `598..704` are grouped under Scenario 15, while `705/706`
  were grouped under Scenario 16 even though their Rayguard-castle advance
  lines physically close this Japanese block. Repeated short Japanese battle
  reactions deliberately reuse their closest semantic English reference.
- All dynamic-name controls and every `FFFD`/`FFFF` terminator remain on their
  source physical page. Every page fits its original capacity and uses no
  forced newline. Ten complete Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_15/`.
- Checksum `7596` entered Scenario 15 preparation, automatic deployment,
  `TURN 1`, Jessica's opening line, the river camera movement, and Imelda's
  first response without a reset. This exposed fixed speaker `イメルダ` at
  `0x0974BE`; checksum `C5C3` verifies the isolated `이멜다` promotion live in
  `captures/analysis/c5c3_s15_intro/imelda_fixed.png`.
- The next live pass exposed fixed speaker `キース` at `0x09743C`. Final build
  `A64F` promotes only that isolated slot to `키스` and passes the full test
  suite. Live re-entry was stopped before the final Keith frame when the user
  needed the machine; do not claim that one final frame as captured yet.
- Inventory is now 1,086/2,968 candidate records and 1,261/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 15, 16, 21, 23,
  24, 29, 30, and 31.

### Diagnostic SRAM Default-Name Migration (2026-07-12)

- The Scenario 15 preparation screen showed `엘윈리아나`, but the ROM name
  table at `0x061AC5` was correctly terminated. A Japanese-ROM comparison
  proved the source screen displays only `エルウィン`. The diagnostic manual
  save cached the original five byte codes `B4 D9 B3 A8 DD FF`; after the byte
  UI font replacement those codes render as `엘윈리아나`.
- Directly changing the six name bytes made the manual slot fail its checksum,
  so that attempt was restored. Manual slots are 0x1A8 bytes; the checksum at
  `slot+0x1A6` is the big-endian 16-bit-word sum of `slot[0:0x1A4]`.
- `tools/run_blastem_sequence.py` now migrates only valid manual slots whose
  name exactly matches the Japanese default, and only when launching the
  Korean production ROM through `scenario-select`. It writes
  `B4 D9 FF FF FF FF`, recalculates the slot checksum, and leaves custom names,
  invalid slots, original-ROM runs, and user SRAM outside the isolated runtime
  untouched. `tests/test_blastem_sram_migration.py` covers success and invalid
  checksum rejection.
- The real diagnostic slot migrated once and remained visible as a valid
  manual Scenario 1 slot on the Load screen. A final preparation-screen visual
  confirmation was not completed before emulator shutdown; resume from the
  migrated runtime when interactive testing is available again.

### Scenario 17 Complete Reviewed Dialogue (2026-07-12)

- Scenario 17 now covers all 108 Japanese pointer records and all 135 physical
  pages. English record 597 is the final Scenario 16 resolve; the Japanese
  Rayguard throne block aligns one-for-one with English `804..911`.
- Every dynamic-name control and `FFFD`/`FFFF` terminator remains on its source
  physical page. All text fits the original capacity and uses no forced
  newline. Twelve complete Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_17/`.
- The first complete build was checksum `6BBC`. Its live pass reached the
  route map, scrolling Korean briefing, preparation screen, automatic
  deployment, `SCENARIO 17`, `TURN 1`, and the opening throne dialogue without
  a reset. It exposed the fixed Japanese speaker labels for Bernhardt and
  Bozel, now isolated at `0x097474` and `0x09748C` and promoted to the safe
  direct patch set.
- An intermediate `7D4E` pass verified `베른하르트` but showed Japanese
  `エルウィン`. Patching direct candidate `0x097404` alone did not affect that
  diagnostic frame: the built-in scenario selector stores a second, 16-bit
  dialogue copy of the hero name at manual-slot offset `+0x142` in addition to
  the byte UI copy at `+0x130`.
- `tools/run_blastem_sequence.py` now migrates both exact Japanese default-name
  representations, derives the current Korean dialogue words from the built
  ROM instead of hard-coding custom glyph IDs, and recalculates the manual-slot
  checksum. It accepts an already migrated half, skips custom names, and still
  rejects invalid checksums. The real diagnostic slot now contains byte name
  `B4 D9 FF FF FF FF`, dialogue name `700B 700C FFFF FFFF FFFF`, and matching
  checksum `2C21`.
- Final checksum `5CC0` live-verifies `베른하르트`, migrated `엘윈`, `쉐리`,
  and `보젤` speaker labels plus their opening Korean lines. Captures are under
  `captures/run/5cc0_s17_*.png`. The full suite passes 87 tests.
- Inventory is now 1,194/2,968 candidate records and 1,396/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 15, 16, 17, 21,
  23, 24, 29, 30, and 31.

### Scenario 18 Complete Reviewed Dialogue (2026-07-12)

- Scenario 18 now covers all 95 Japanese pointer records and all 117 physical
  pages. The primary records align with English `707..801`, but the English
  project split several post-battle pages differently after `0x1A5882`.
  Korean text follows the physical Japanese order for the Mireil departure,
  Dark Princess identity, dispelling chant, failure, and route-variant harbor
  explanations rather than mechanically copying those English page breaks.
- Every original dynamic-name control and `FFFD`/`FFFF` terminator is preserved
  in order. All pages fit their source capacity and use no forced newline. Ten
  complete Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_18/`.
- Checksum `B333` entered the Korean Scenario 18 briefing, preparation screen,
  automatic deployment, the first resident line, and Lana's opening line
  without a reset. That pass exposed fixed speaker `ラーナ` at `0x097418`.
- Final checksum `932F` promotes only that live-reached slot to `라나` and
  verifies `라나: 아하하하! 도망쳐라! 안 그러면 죽는다!` live. The
  direct-string inventory now classifies Lana as a declared patch while keeping
  unpromoted candidates such as `0x097462` explicitly unsafe. Captures are under
  `captures/run/932f_s18_*.png`; the full suite passes 89 tests.
- Inventory is now 1,289/2,968 candidate records and 1,513/3,567 physical pages
  modified. Complete reviewed scenarios are 1, 2, 3, 5, 14, 15, 16, 17, 18,
  21, 23, 24, 29, 30, and 31.

### Scenario 19 Static Review And Opening Live Verification (2026-07-14)

- Scenario 19 statically covers all 98 Japanese pointer records and all 116
  physical pages. English `802/803` are Scenario 18 residue; Japanese primaries
  0..94 align with English `983..1077`. The final three Japanese sortie-delay
  lines at `0x1A781A`, `0x1A783C`, and `0x1A7868` have no English counterparts
  and are deliberately marked `japanese_only`.
- Static comparison against all ten Japanese contact sheets corrected several
  misleading English-reference translations. Notable fixes include the
  Imelda departure line whose meaning had been reversed, the approaching
  reinforcements, Lana's reinforcement offer, mast/anchor orders expressed as
  natural Korean departure commands, and the final garrison status reports.
  Item messages now match the established direct-name table as `갸라르혼` and
  `아우로라` rather than the inconsistent `갸라르의 뿔` and `아우라`.
- Every original dynamic-name control and `FFFD`/`FFFF` terminator remains in
  order, every page fits its source capacity, and no forced newline or new
  custom glyph was required. Final static build checksum is `5300`, with 765
  custom glyphs and 90 passing tests. Ten Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_19/` and
  `scenario_19_pages_00.png` through `_09.png`.
- Inventory at the static-review point was 1,387/2,968 candidate records and
  1,629/3,567 physical pages modified. Checksum `524D` subsequently entered
  selector row 19, the Korean briefing and preparation screens, automatic
  deployment, the ship map, and the complete opening sequence. Imelda, the
  Imperial commander, Hein, Keith, and Lester all displayed Korean names and
  dialogue, `SCENARIO 19`/`TURN 1` appeared, and 15 paced confirmations returned
  to the playable command menu without a reset, freeze, blank page, or visible
  Japanese residue. Evidence is
  `captures/analysis/524d_s19_opening_sheet.png` and
  `captures/run/524d_s19_opening/01.png` through `15.png`.
- Scenario 19 is not fully live-complete yet. Conditional reinforcements, item
  pickups, departure paths, and victory/defeat variants still need runtime
  traversal; do not infer their runtime safety from the verified opening.

### Scenario 20 Static Review And Opening Live Verification (2026-07-14)

- Scenario 20 statically covers all 88 Japanese pointer records and all 111
  physical pages. English `1078..1080` are the three final Scenario 19
  garrison reports. The Japanese ship-battle block then covers English
  `1081..1167`; physical grouping differs around monster cries, Faias's
  multi-page battle dialogue, and the post-battle route variants. All three
  final Japanese approach warnings deliberately reference English `1167`.
- All ten Japanese sheets were compared address by address rather than using
  English page breaks mechanically. The Korean pass covers the boarding
  attack, golem tactics, kraken tactics, Faias/Doren confrontation, every
  battle reaction, Bozel warning, Doren aftermath, Elwin's crisis, landing
  calls, and the three Velzeria approach variants. Every `{0001}`, `{0002}`,
  `{0004}`, `{0006}`, `{0007}`, `{0010}`, `{0060}`, and `{0073}` control and
  every `FFFD`/`FFFF` terminator is preserved in its original physical page.
- The full font was already at 765/766 slots. Scenario 20 keeps the canonical
  `골렘` spelling without exceeding the table by changing Scenario 21's unique
  `무릎 꿇어라` wording to the equivalent `굴복해라`; all other new one-off
  syllables were avoided through natural synonyms. Every page fits its source
  capacity, no forced newline is used, and final static checksum `C1BA` still
  uses 765 custom glyphs. Ten Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_20/` and
  `scenario_20_pages_00.png` through `_09.png`.
- Inventory at the static-review point was 1,475/2,968 candidate records and
  1,740/3,567 physical pages modified, with 91 passing tests. Checksum `524D`
  subsequently entered selector row 20, the Korean briefing and preparation
  screens, automatic deployment, the ship map, and every opening page. A slow
  capture pass verified Scott, Sherry, Faias, and Elwin names/dialogue and a
  clean return to the playable map; evidence is
  `captures/analysis/524d_s20_opening_slow_sheet.png` and
  `captures/run/524d_s20_opening_slow/01.png` through `08.png`.
- That live pass exposed a semantic error at `0x1A7EC2`. Japanese
  `{0010}様の邪魔だけは、俺がゆるさん` means Faias will not forgive anyone
  interfering with Bozel, but the first Korean wording incorrectly made Bozel
  the interfering subject. The corrected capacity-safe text is
  `하지만 벨제리아엔 못 간다. {0010}님을 방해하면 내가 용서 못 해!`.
  Rebuilt checksum `53AD` live-verifies the corrected page in
  `captures/run/53ad_s20_dialogue_04.png`, the remaining Elwin/Faias pages in
  `53ad_s20_dialogue_05.png` and `53ad_s20_dialogue_06.png`, and the playable
  Korean `엘윈` command panel in `53ad_s20_command_menu.png`. No reset, freeze,
  blank page, or visible Japanese residue occurred in the full opening.
- Scenario 20 is not fully live-complete yet. The conditional golem/kraken
  events, later Faias/Doren confrontations, victory dialogue, and route
  variants still require runtime traversal.

### Scenario 22 Complete Reviewed Dialogue (2026-07-13)

- Scenario 22 now covers all 151 Japanese pointer records and all 191 physical
  pages. The English mapping begins with two Scenario 21 residue records
  (`981/982`); the actual aligned run is `1219..1368`. The final Japanese
  resolution record at `0x1AD326`/`0x1AD35C` has no English counterpart and is
  explicitly marked `japanese_only`.
- All Japanese contact sheets were checked address by address. The translation
  covers the Dark Temple approach, Alhazard ritual variants, Bozel/Egbert
  betrayal branches, both transport-spell explanations, Lana/Liana reunion,
  Alhazard tracking, Langrisser's sealed power, Holy Rod objective, and the
  Dragon's Lair branch. Every original dynamic-name control and `FFFD`/`FFFF`
  terminator is preserved; no forced newline is used.
- The 765/766 custom-glyph budget remains unchanged. New one-off syllables were
  avoided with equivalent wording, and every physical page fits its original
  word capacity. Sixteen Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_22_pages_00.png` through `_15.png`.
- Final build checksum `3B53` passes all 93 tests. Live verification entered
  Scenario 22 through the built-in selector, displayed both Korean briefing
  pages, entered preparation and automatic deployment, reached `TURN 1`, and
  advanced the first nine event pages without a reset, blank page, or corrupt
  control. Captures include `captures/run/3b53_s22_briefing.png`,
  `3b53_s22_after_confirm.png`, `3b53_s22_prep.png`,
  `3b53_s22_first_dialogue.png`, and the sequence under
  `captures/run/3b53_s22_opening_pages/`.
- Inventory is now 1,626/2,968 candidate records and 1,931/3,567 physical pages
  modified. Scenario 22 is static-complete with its opening path live-verified;
  conditional mid-map branches remain part of the later whole-game route
  regression pass.

### Scenario 4 Complete Reviewed Dialogue (2026-07-13)

- Scenario 4 now covers all 129 Japanese pointer records and all 155 physical
  pages. English `2312..2440` align with the 129 primary Japanese records;
  English `2441` is outside this block. The later escape, Sherry, and controlled
  Liana branches diverge substantially in physical order, so translations from
  `0x18B7E8` onward follow the Japanese sheets rather than English sequencing.
- The Japanese original also differs in meaning at several points. Morgan says
  that surrendering the tablet would only have earned a painless death, not
  survival as the English reference implies. This and the sanctuary, tablet,
  Alhazard seal, Dark Elf tactics, mind-control spell, rescue, pursuit, Sherry
  recruitment, Cross reward, and branch aftermath were translated from source.
- Every dynamic-name control and `FFFD`/`FFFF` terminator remains in its original
  physical page. No forced newline or new custom glyph was needed; the build
  remains at 765/766 glyphs. Thirteen Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_04_pages_00.png` through `_12.png`.
- Live verification exposed fixed speaker `神官` at `0x97648`. Only that
  live-reached slot was promoted to `신관`; the unsafe full direct-name map stays
  disabled. Final checksum `4793` passes all 94 tests and live-verifies the
  Korean briefing, preparation, automatic deployment, `TURN 1`, Morgan's
  opening pages, and the corrected `신관` label. Relevant captures are
  `captures/run/693e_s04_*.png`, `captures/run/693e_s04_opening_pages/`, and
  `captures/run/4793_s04_priest_speaker_final.png`.
- Inventory is now 1,755/2,968 candidate records and 2,086/3,567 physical pages
  modified. Scenario 4 is static-complete with its opening path live-verified;
  conditional combat and ending branches remain in the whole-game regression
  pass.

### Scenario 6 Complete Reviewed Dialogue (2026-07-13)

- Scenario 6 now covers all 102 Japanese pointer records and all 122 physical
  pages at `0x18DCC0..0x18F24C`. English `2521..2622` supply a complete
  one-to-one record reference, but the Japanese order diverges around the
  Runestone, village-defense deaths, sword-master reunion, and post-battle
  holy/demon sword explanation. Those sections follow the Japanese contact
  sheets rather than the English page order.
- The translation covers Morgan's parchment search, the village elder and
  Aaron, every civilian/cultist death reaction, the Shika-speaking troops,
  Morgan and Zold battle branches, Aaron's recruitment, Langrisser and
  Alhazard history, both village-damage outcomes, and the Amulet reward. All
  dynamic-name controls and `FFFD`/`FFFF` terminators remain on their original
  physical pages; no forced newline is used.
- Eight one-off syllables initially exceeded the shared font budget. Equivalent
  Korean wording removed all eight rather than consuming byte-UI graphics.
  Final checksum `7044` uses 765/766 custom glyphs. Eleven Korean sheets are in
  `captures/analysis/event_pages_ko/scenario_06_pages_00.png` through `_10.png`.
- The full static suite passes 95 tests. Inventory is now 1,857/2,968 candidate
  records and 2,208/3,567 physical pages modified. Live verification entered
  the real `SCENARIO 6`, completed automatic deployment, reached `TURN 1`, and
  advanced the opening Morgan/village-elder sequence without a blank page,
  reset, or bad dynamic-name substitution. Captures include
  `captures/run/7044_s06_arrange_live.png`, `7044_s06_deploy_start.png`, and
  `7044_s06_dialogue_1.png` through `_12.png`.
- A failed first selector attempt exposed that `scenario-select` deleted its
  own manual-slot runtime unless `--reuse-runtime-state` was passed. A valid
  slot was recreated through the documented diagnostic save branch, and
  `tools/run_blastem_sequence.py` now preserves `captures/runtime/load-screen`
  by default. Do not remove that runtime before selector-based live checks.

### Scenario 7 Complete Reviewed Dialogue (2026-07-13)

- Scenario 7 contains 101 pointer candidates and 118 physical candidates, but
  `0x18F610` is not text: it is a 12-word structured record beginning
  `0202 0601 0019 0200` and reached from `0x18F358`. It remains byte-identical
  and has an explicit regression test. The 100 real Japanese records at
  `0x18F88A..0x190CEC` cover 117 physical pages.
- English `2623/2624` are Scenario 6 aftermath residue. The 98 reference rows
  `2625..2722` are retained in positional order because English splits and
  merges the princess arrival, civilian deaths, and Kalzath aerial-unit lines
  differently. Japanese-only `0x190CDE` and `0x190CEC` provide the final thanks
  and Runestone acquisition message.
- The Japanese sheets are authoritative for the Kalzath warning, cemetery
  necromancy, Zolm's attack, undead/slime tactics tutorial, all civilian and
  unit death branches, Keith's arrival variants, post-battle Blue Dragon
  Knight report, Kalzath strategy explanation, and Runestone reward. Every
  original dynamic-name control and terminator is preserved without forced
  newlines.
- The only new glyph retained is `켈` for the canonical class name
  `스켈레톤`; equivalent wording removed sixteen other one-off syllables.
  Checksum `AC20` therefore uses the complete 766/766 glyph budget. Ten Korean
  sheets are under `captures/analysis/event_pages_ko/scenario_07_pages_00.png`
  through `_09.png`. Inventory is now 1,957/2,968 candidate records and
  2,325/3,567 physical pages modified, with 97 passing tests.
- Live verification entered the real `SCENARIO 7`, completed automatic
  deployment, reached `TURN 1`, displayed the elder/Sherry/Zolm opening, and
  reached the first playable Elwin command without a reset or corrupt name.
  The first pass captured Elwin's short page during its empty transition
  frame; a clean replay captured `시키겠나!` at the same point in
  `captures/run/ac20_s07_repro_late_3.png`, proving it is not a blank ROM page.
  Other evidence includes `ac20_s07_arrange.png`, `ac20_s07_deploy.png`, and
  `ac20_s07_dialogue_1.png` through `_18.png`.

### Scenario 8 Complete Reviewed Dialogue (2026-07-13)

- Scenario 8 covers all 103 Japanese pointer records and all 128 physical
  pages at `0x191416..0x192B3E`. English `2723/2724` are Scenario 7 residue;
  the first 102 Japanese records align positionally with English
  `2725..2826`. The final record at `0x192B14`, continued at `0x192B3E`, is a
  Japanese-only report that the enemy has also lost many soldiers.
- The Japanese sheets are authoritative for the bridge-demolition countdown,
  flying/cavalry two-wave attack, bridge-collapse branches, flying and elf
  tactics, Imperial knight assistance, commander deaths and retreats,
  Kalzath aftermath, and Blue Dragon Knight branches. Every dynamic-name
  control and `FFFD`/`FFFF` terminator remains on its original physical page.
- Initial Korean wording exceeded 32 physical-page capacities and requested
  ten new syllables after the shared 16x16 font had reached 766/766 slots.
  Equivalent shorter wording removed every overflow and every new glyph.
  Eleven reviewed sheets are under
  `captures/analysis/event_pages_ko/scenario_08/scenario_08_pages_00.png`
  through `_10.png`.
- Live verification entered the real `SCENARIO 8`, showed the Korean
  `프롤로그`, preparation and arrangement screens, automatically deployed,
  reached `TURN 1`, and advanced the bridge opening without a reset. The first
  fixed speaker was still `クレイマー`; its live-reached direct-name record
  `0x974DA` is now safely promoted as `크레이머`. The final proof is
  `captures/run/305d_s08_opening_kramer_final.png`; subsequent Korean pages are
  in `captures/run/305d_s08_opening_pages/`.
- A broader attempt to add map-status names `스코트`, `키스`, and `크레이머`
  at `0x061ADC`, `0x061AE1`, and `0x061B41` was rejected and reverted. It needs
  33 extra byte-font glyph codes while only 29 collision-free codes remain.
  Reusing more ASCII/status tiles would reintroduce the already fixed faction
  animation and terrain corruption. These later-scenario map names require a
  screen-specific font swap or a larger safe byte-font design; the direct
  dialogue names are already Korean.
- Final checksum `305D` uses 766/766 custom glyphs and passes all 98 tests.
  Inventory is now 2,060/2,968 candidate records and 2,453/3,567 physical
  pages modified. Scenario 8 is static-complete with its opening live-verified;
  conditional battle routes remain in the whole-game regression pass.

### Scenario 9 Complete Reviewed Dialogue (2026-07-13)

- The Japanese Scenario 9 block contains 147 logical pointer records and 169
  physical pages at `0x1934B0..0x19546A`. Fifteen source contact sheets are in
  `captures/analysis/event_pages_jp/scenario_09/scenario_09_pages_00.png`
  through `_14.png`; all were visually reviewed before translation.
- English record `2827` is the final Scenario 8 bridge report and does not
  belong to this block. Japanese primary records 0..145 align positionally
  with English `2828..2973`. The final Japanese primary record at `0x195426`,
  continued at `0x19546A`, is source-only: even if some casualties are caused,
  the commander orders a direct assault and concentration on the castle.
- The block covers the Kalzath siege, monster diversion, Sherry's relief
  force, siege-unit tactics and deaths, multiple castle-defense outcomes,
  Liana and Jessica's Alhazard/Dark Rod explanation, and renewed Imperial
  assaults. All 169 physical pages are translated from the Japanese ordering;
  dynamic-name controls and `FFFD`/`FFFF` terminators stay on their source
  pages without forced newlines.
- The first draft produced multiple capacity overflows and fourteen one-off
  glyph requests across its two editing passes. Equivalent concise wording
  removed every overflow and every new glyph, preserving the full 766/766
  shared-font budget. Fifteen reviewed Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_09/scenario_09_pages_00.png`
  through `_14.png`.
- Live verification entered the real Scenario 9, showed its Korean briefing
  and preparation screens, automatically deployed, reached `TURN 1`, and
  advanced the opening Leon/Reard/Imperial-commander sequence without a reset.
  The first live pass exposed an orphaned `?` after automatic wrapping; the
  source page at `0x1934B0` was shortened to `공성 부대 상황은? 보고하라.`.
  `captures/run/3fa7_s09_opening_final.png` verifies the corrected wrapping on
  the final ROM.
  Captures include `captures/run/91a2_s09_briefing_end.png`,
  `91a2_s09_prep.png`, `91a2_s09_deployed.png`, `91a2_s09_turn.png`, and the
  sequence under `captures/run/91a2_s09_opening_pages/`.
- Final checksum `3FA7` uses 766/766 custom glyphs and passes all 99 tests.
  Inventory is now 2,207/2,968 candidate records and 2,622/3,567 physical
  pages modified. Conditional mid-map and ending branches remain part of the
  later whole-game route regression pass.

### Scenario 10 Complete Reviewed Dialogue (2026-07-13)

- The Japanese Scenario 10 block contains 108 logical records and 112 physical
  pages at `0x195CB6..0x197046`. Ten visually reviewed source sheets are under
  `captures/analysis/event_pages_jp/scenario_10/scenario_10_pages_00.png`
  through `_09.png`.
- English record `2974` is Scenario 9's final risky-assault order and is not
  part of this block. Japanese primary records 0..103 align positionally with
  English `2975..3078`.
- Japanese primary records 104..107 are source-only: a subordinate acknowledges
  the order, offers a necklace at `0x196FFC`, receives thanks at `0x197028`,
  and the final record `0x197046` awards the Necklace. All four are translated
  in their original order.
- The block covers the river crossing, monster ambush, water/land tactics,
  many ally and monster death branches, Dark Rod intelligence, the magician's
  location, several temporary-party departure variants, and the Japanese-only
  Necklace reward. All original dynamic-name controls and terminators remain
  on their source pages without forced newlines.
- Initial wording exceeded several physical-page capacities and requested six
  new syllables. Equivalent concise wording removed every overflow and every
  new glyph, preserving the full 766/766 shared-font budget. Ten reviewed
  Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_10/scenario_10_pages_00.png`
  through `_09.png`.
- Live verification entered the real Scenario 10, showed the Korean briefing,
  deployed, reached its opening event, and advanced nine dialogue/event pages.
  Dynamic Keith substitution renders correctly in Sherry's first line; no
  Japanese dialogue, blank page, reset, or freeze appeared. Captures include
  `captures/run/2c48_s10_briefing_end.png`, `2c48_s10_deployed.png`,
  `2c48_s10_opening_00.png`, and the sequence under
  `captures/run/2c48_s10_opening_pages/`.
- Final checksum `2C48` uses 766/766 custom glyphs and passes all 100 tests.
  Inventory is now 2,315/2,968 candidate records and 2,734/3,567 physical
  pages modified. Conditional battle and ending branches remain in the later
  whole-game route regression pass.

### Scenario 11 Complete Reviewed Dialogue (2026-07-13)

- The Japanese Scenario 11 block contains 96 logical records and 117 physical
  pages at `0x197680..0x198D98`. Ten visually reviewed source sheets are under
  `captures/analysis/event_pages_jp/scenario_11/scenario_11_pages_00.png`
  through `_09.png`.
- English records `3079..3081`, whose source prefixes are
  `0x197068..0x1970A2`, are Scenario 10's acknowledgement and Necklace reward;
  they are not part of Scenario 11. The English extractor then wraps to record
  zero because its numbering follows ROM-bank order rather than scenario order.
- Japanese primary records 0..94 align positionally with English `0..94`.
  The final Japanese primary record at `0x198D98` is source-only: the fire will
  not follow the river current, so the party must hurry to the opposite bank.
- The block covers Jessica's Dark Rod explanation, Egbert's raid, Runestone
  reward, oil and fire trap, unit-death branches, Hein's request to study under
  Jessica, Sherry's tiara and royal lineage, escape variants, and the route to
  Reitel. All original dynamic-name controls and `FFFD`/`FFFF` terminators stay
  on their source pages without forced newlines.
- The first draft requested eight new syllables after the shared font had
  reached 766/766 slots. Equivalent wording removed all eight rather than
  consuming shared byte-UI graphics. Four over-capacity pages were shortened
  without changing their meaning. Ten reviewed Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_11/scenario_11_pages_00.png`
  through `_09.png`.
- Live verification entered the real Scenario 11, showed its Korean briefing
  and preparation screens, automatically deployed, reached `TURN 1`, and
  advanced the Jessica meeting. The first pass exposed an orphaned final
  syllable in Lester's opening and a split `다크/로드`; both lines were
  shortened. `captures/run/da67_s11_opening_final.png` and
  `da67_s11_dark_rod_wrap.png` verify the corrected wrapping. Other evidence
  includes `da67_s11_prep_arrange_selected.png`, `da67_s11_auto_selected.png`,
  and `da67_s11_deployed.png`.
- Final checksum `DA67` uses 766/766 custom glyphs and passes all 101 tests.
  Inventory is now 2,411/2,968 candidate records and 2,851/3,567 physical
  pages modified. Conditional battle, fire-trap, and ending branches remain in
  the later whole-game route regression pass.

### Scenario 12 Complete Reviewed Dialogue (2026-07-13)

- The Japanese Scenario 12 block contains 88 logical records and 113 physical
  pages at `0x199344..0x19A93E`. Ten visually reviewed source sheets are under
  `captures/analysis/event_pages_jp/scenario_12/scenario_12_pages_00.png`
  through `_09.png`.
- English record `95`, whose source prefix is `0x198E12`, is Scenario 11's
  final instruction to escape across the river and is not part of Scenario 12.
  Japanese primary records 0..27 align with English `200..227`; after that,
  battle deaths, guardian cries, Dark Rod theft, and conditional return routes
  split and merge differently. The Japanese address order is authoritative.
- Source-only material includes a chronic-illness death at `0x199BC8` and the
  repeated Liana-abduction return variant at `0x19A87E..0x19A8F4`. English-only
  short reactions are not inserted into unrelated Japanese pages.
- The block covers the Reitel guardians, Egbert's Alhazard plans and
  reincarnation history, Dark Rod acquisition and theft branches, guardian and
  Imperial battle reactions, the hidden shrine, Liana's kidnapping aftermath,
  Jessica's regret, Hein's view of magic, and Jessica's promise to accept him
  as an apprentice. All 113 physical pages are translated; every dynamic-name
  control and `FFFD`/`FFFF` terminator remains on its source page without
  forced newlines.
- The first draft requested ten new syllables after the shared font had reached
  766/766 slots. Equivalent wording removed every new glyph rather than
  consuming shared byte-UI graphics. Ten reviewed Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_12/scenario_12_pages_00.png`
  through `_09.png`.
- Live verification entered the real Scenario 12, showed its Korean briefing
  and preparation screens, automatically deployed, reached `TURN 1`, and
  advanced the Elwin/Reitel-guardian opening. The first pass exposed fixed
  speaker `リッチ` and an orphaned punctuation line. Direct-name slot
  `0x97594` is now safely promoted as `리치`, and the warning was shortened.
  `captures/run/9543_s12_lich_final.png` verifies both fixes; other evidence
  includes `e737_s12_briefing.png`, `e737_s12_prep.png`,
  `e737_s12_deployed.png`, and `9543_s12_after_turn.png`.
- Final checksum `9543` uses 766/766 custom glyphs and passes all 102 tests.
  Inventory is now 2,499/2,968 candidate records and 2,964/3,567 physical
  pages modified. Conditional battle, shrine, and return branches remain in
  the later whole-game route regression pass.

### Scenario 13 Complete Reviewed Dialogue (2026-07-13)

- The Japanese Scenario 13 block contains 96 logical records and 126 physical
  pages at `0x19AEE0..0x19C6F4`. Eleven visually reviewed source sheets are
  under `captures/analysis/event_pages_jp/scenario_13/`, ending at
  `scenario_13_pages_10.png`.
- English record `288`, whose source prefix is `0x19A9B8`, is Scenario 12's
  final departure line and is not part of Scenario 13. Japanese primary
  records 0..93 align positionally with English `289..382`.
- The final Japanese primaries at `0x19C6EC` and `0x19C6F4` are source-only:
  the first is the unit's affirmative response, and the second vows not to die
  but to win and return to Eliza and the speaker's child.
- The block covers the Fire Dragon corps blockade, ballista/griphon/flying
  tactics, Keith and Sherry branches, Kalzath rescue, Dark Rod/Liana ritual,
  Langrisser discovery, and the Imperial commander's family and honor speech.
  All 126 physical pages are translated in Japanese ROM order. Original
  dynamic-name controls and `FFFD`/`FFFF` terminators remain on their source
  pages without forced newlines.
- The first draft requested eight new syllables after the shared font had
  reached 766/766 slots. Equivalent wording removed all eight instead of
  consuming byte-UI/status graphics. One dynamic-name control was moved back
  to its original physical page, and two over-capacity pages were shortened
  without changing their meaning. Eleven reviewed Korean sheets are under
  `captures/analysis/event_pages_ko/scenario_13/`, ending at
  `scenario_13_pages_10.png`.
- Live verification entered the real Scenario 13, displayed its Korean
  briefing and preparation screens, automatically deployed, reached `TURN 1`,
  and completed the opening event. Keith, Elwin, Lester, Hein, Aaron, and
  Sherry all render with Korean speaker names; dialogue wrapping, unit
  movement, and return to player control are normal, with no Japanese text,
  blank page, reset, or freeze. Evidence includes
  `captures/run/bd7f_s13_briefing2.png`, `bd7f_s13_arrange.png`,
  and `bd7f_s13_opening_02.png` through `_09.png`.
- Final checksum `BD7F` uses 766/766 custom glyphs and passes all 103 tests.
  Inventory is now 2,595/2,968 candidate records and 3,090/3,567 physical
  pages modified. Conditional battle, family, Langrisser, and ending branches
  remain in the later whole-game route regression pass.

### Scenario 25 Static Dialogue Complete (2026-07-13)

- Scenario 25 has 100 pointer candidates and 132 physical candidates in the
  event block `0x1B03D6..0x1B2012`. Candidate `0x1B0518` is not text: it is a
  17-word structured record beginning `0001 0001 001B 0544`; keep it
  byte-identical. The 99 real Japanese dialogue records begin at `0x1B0982`
  and cover 131 physical pages.
- English records `1487/1488` are Scenario 24 aftermath residue. The actual
  Scenario 25 reference run is `1799..1898`. Japanese logical record 1 splits
  across English `1799/1800`, logical record 16 ends with a separate English
  `1816` exclamation, and logical record 91 ends with separate English `1892`.
  All other shared records retain positional order after accounting for those
  three splits.
- Japanese logical records 98 and 99 at `0x1B1FAA` and `0x1B1FE6` are
  source-only. They identify Alhazard beneath the castle, probably in the
  underground shrine, and order the party to advance and end the battle as
  quickly as possible.
- Eleven reviewed Japanese source sheets are under
  `captures/analysis/event_pages_jp/scenario_25/`, ending at
  `scenario_25_pages_10.png`. They cover Bosel's hostage scene, the Alhazard
  faction, Leon and the Blue Dragon Knights' final battle and conditional
  deaths/retreats, Imperial unity ideology, and the route toward the
  underground shrine.
- All 131 real physical dialogue pages are translated in Japanese ROM order.
  Original dynamic-name controls and `FFFD`/`FFFF` terminators remain on their
  source pages without forced newlines. The structured candidate remains
  byte-identical and has an explicit regression test. Eleven reviewed Korean
  sheets are under `captures/analysis/event_pages_ko/scenario_25/`, ending at
  `scenario_25_pages_10.png`.
- The first draft requested six new shared-font syllables. Equivalent wording
  removed all six rather than consuming byte-UI/status graphics. Checksum
  `7361` keeps the shared font at 766/766 slots and passes all 105 tests.
  Inventory is now 2,694/2,968 candidate records and 3,221/3,567 physical
  pages modified; Scenario 25 intentionally reports 99/100 and 131/132
  because its first candidate is structured data.
- Live verification entered the real Scenario 25 and displayed both Korean
  briefing pages and the Korean preparation/arrangement screens. The earlier
  pass stopped there because concurrent AVNC focus/input caused arrangement
  selections to diverge from sent keys; this was an automation failure, not a
  ROM failure. Evidence from that pass includes
  `captures/run/7361_s25_briefing1.png`, `7361_s25_briefing2.png`, and
  `7361_s25_arrange2.png`.
- Checksum `53AD` subsequently repeated the route and briefing, displayed the
  preparation roster as `엘윈/헤인/쉐리/아론/키스`, performed automatic
  deployment, and reached `SCENARIO 25` / `TURN 1`. Twenty-five paced event
  advances covered the complete unconditional Egbert, Elwin, Liana, Leon,
  Jessica, and Imperial commander exchange and returned to Elwin's Korean
  `이동/공격/치료/명령` menu. No Japanese text, joined commander name, blank
  page, reset, or freeze appeared. Evidence is
  `captures/analysis/53ad_s25_opening_sheet.png` and
  `captures/run/53ad_s25_opening_03.png` through `_27.png`.
- Scenario 25 is not fully live-complete. Conditional hostage, Leon/Blue Dragon
  battle and death/retreat paths, item events, victory/defeat outcomes, and the
  underground-shrine transition still require runtime traversal.

### Scenario 26 Static Dialogue Complete (2026-07-13)

- Scenario 26 contains 71 logical Japanese records and 102 physical pages in
  `0x1B2494..0x1B3832`, inside event block `0x1B2012..0x1B3872`. All 71
  candidates are dialogue; unlike Scenario 25, this set has no structured
  non-text candidate that must be excluded.
- Japanese logical records 0..68 align positionally with English records
  `1616..1684`. They cover Egbert's trap and confrontation with Jessica,
  their history, the Runestone reward, unit-death branches, the optional Death
  Tower rematch, Egbert's death, and Jessica's aftermath.
- Japanese logical records 69 and 70 at `0x1B380A` and `0x1B3832` are
  source-only. The former orders the party to end the age of Darkness; the
  latter is an enemy battle taunt asking for a more entertaining fight.
- English records `1899/1900` describe Alhazard below the castle and finishing
  the battle. They correspond to Scenario 25's source-only final records and
  are cross-scenario residue in the English Scenario 26 mapping; do not apply
  them to the two Japanese-only Scenario 26 records.
- All 102 physical dialogue pages are translated in Japanese ROM order.
  Original dynamic-name controls and `FFFD`/`FFFF` terminators remain on their
  source pages without forced newlines. Nine reviewed Japanese source sheets
  are under `captures/analysis/event_pages_jp/scenario_26/`, ending at
  `scenario_26_pages_08.png`; the corresponding reviewed Korean sheets are
  under `captures/analysis/event_pages_ko/scenario_26/`.
- The first draft requested seven new shared-font syllables. Equivalent wording
  removed all seven rather than consuming byte-UI/status graphics. Static
  sheet review also shortened lines that split words or left punctuation alone
  at the 32-glyph display edge.
- The first live pass exposed two periods wrapping onto a line by themselves in
  the narrower portrait dialogue box. The affected death offer and magic-circle
  challenge were shortened, then re-entered through the selector and verified
  in the final ROM.
- Live verification displayed the Korean route/briefing and preparation
  screens, completed automatic deployment, reached `SCENARIO 26` and `TURN 1`,
  and advanced the complete opening Egbert/Elwin/Lester exchange back to player
  control. Dynamic Jessica and Egbert names render correctly; no Japanese text,
  blank page, reset, or freeze appeared. Evidence includes
  `captures/run/76ca_s26_prep2.png`, `76ca_s26_arrange.png`,
  `76ca_s26_dialogue1.png`, `76ca_s26_dialogue3.png`,
  `76ca_s26_dialogue_magic_circle.png`, and
  `76ca_s26_player_control.png`.
- Final checksum `76CA` keeps the shared font at 766/766 slots and passes all
  106 tests. Inventory is now 2,765/2,968 candidate records and 3,323/3,567
  physical pages modified. Conditional battle, death, Runestone, rematch, and
  ending branches remain part of the later whole-game route regression pass.

### Scenario 27 Dialogue Alignment (2026-07-13)

- Scenario 27 contains 97 logical Japanese records and 126 physical pages in
  `0x1B3DF2..0x1B54D4`, inside event block `0x1B3872..0x1B5506`. All 97
  candidates are dialogue.
- English records `1685/1686` are Scenario 26's two source-only final battle
  lines and are cross-scenario residue here. Japanese logical records 0..81
  align with English `1687..1768`; the short continuation at `0x1B51F0`
  corresponds to English `1769`; logical records 82..94 align with English
  `1770..1782`. This content-based boundary supersedes the earlier impossible
  shorthand `0..94 -> 1687..1782`, which had overlooked that one English
  record belongs to a Japanese physical continuation.
- Japanese logical records 95 and 96 at `0x1B54A4` and `0x1B54D4` are
  source-only. They call for ending the age of war and state that this will be
  Langrisser's final duty.
- Eleven reviewed Japanese source sheets are under
  `captures/analysis/event_pages_jp/scenario_27/`, ending at
  `scenario_27_pages_10.png`. They cover the final confrontation with
  Bernhardt, Imperial officer and monster battle/death branches, Bernhardt's
  ideology and death, Leon/Imelda route variants, and the Alhazard aftermath.
  All 126 translated physical pages were reviewed in the matching Korean
  sheets under `captures/analysis/event_pages_ko/scenario_27/`; none are blank,
  over capacity, or missing their original dynamic-name controls.
- The static Scenario 27 build has checksum `16A0`, keeps the shared Hangul
  font at 766/766 slots, and passes all 107 tests. Inventory is now
  2,862/2,968 logical candidates and 3,449/3,567 physical pages modified.
  Conditional route regression remains pending.
- Live selector row 27 displayed the Korean route screen and `전설의 끝`
  prologue, entered preparation, completed automatic deployment, and reached
  `SCENARIO 27` / `TURN 1`. The complete unconditional opening event advanced
  through Lana, Liana, Sherry, Elwin, and Bernhardt and returned to Elwin's
  `이동/공격/치료/명령` command menu. The dynamic Bernhardt insertion rendered
  correctly, and no Japanese text, blank dialogue, reset, or freeze appeared.
  Evidence includes `captures/run/16a0_s27_briefing.png`,
  `16a0_s27_arrange.png`, `16a0_s27_dialogue1.png`,
  `16a0_s27_opening_step04.png`, `16a0_s27_opening_step10.png`,
  `16a0_s27_opening_step20.png`, and `16a0_s27_opening_step22.png`.

### Scenario 28 Dialogue Alignment (2026-07-13)

- Scenario 28 contains 104 logical Japanese dialogue records and 116 physical
  pages in `0x1B5B7A..0x1B6B4C`, inside event block
  `0x1B5506..0x1B6B70`.
- English records `1783/1784` repeat Scenario 27's two Japanese-only closing
  lines and are cross-scenario residue. Japanese logical records 0..101 align
  positionally with English `96..197`. Japanese logical records 102 and 103 at
  `0x1B6B04` and `0x1B6B4C` are source-only closing jokes about slime/bug
  muscles and keeping up the mood while departing.
- Ten reviewed Japanese source sheets are under
  `captures/analysis/event_pages_jp/scenario_28/`, ending at
  `scenario_28_pages_09.png`. They cover the bodybuilding-brother opening,
  Brotherly Love conversion branches, Man Beam countdown, combat/death and
  item branches, Samson/Adon lines, and the post-battle exchange. All 116
  translated physical pages were reviewed in the matching Korean sheets under
  `captures/analysis/event_pages_ko/scenario_28/`; none are blank, over
  capacity, or missing their original dynamic-name and continuation controls.
- The translation uses `형님교단`, `이다텐과 변재천`, `남자광선`,
  `모히모히푸`, `보디빌드`, `삼손/아돈`, `당가드`, and `철아령`. These
  choices fit the original record capacities without adding glyphs to the
  already-full shared font. In particular, `남자광선` is the capacity-safe
  rendering of `メンズビーム`; the more literal loanword needs unavailable
  `빔/즈` glyph slots.
- The static Scenario 28 build has checksum `14C8`, keeps the shared Hangul
  font at 766/766 slots, and passes all 108 tests. Inventory is now
  2,966/2,968 logical candidates and 3,565/3,567 physical pages modified. The
  only two untouched candidates are the known structured non-dialogue records
  in Scenarios 7 and 25.
- The first live pass exposed two distinct name renderers: byte-name records
  `0x061B7E/0x061B83/0x061B88` own the map status labels, while direct-word
  records `0x97530/0x97538/0x97542` own the 16x16 dialogue speaker labels.
  Patching only the byte records produced Korean `바란` in the status bar but
  Japanese `バラン` in dialogue. All six records are now patched and covered
  by inventory tests.
- Adding the five new byte-name syllables initially exceeded the verified safe
  byte-font pool. Expanding into shared graphics was rejected. Status-only
  class labels were compacted to `마전사`, `기사장`, `무장기병`, `수호병`,
  `주민`, and `R기병`, preserving class IDs while keeping the byte font inside
  64/64 safe slots. A first allocation reused uppercase `U` and visibly broke
  the small in-map `TURN`; a second allocation reused `K` and rendered the
  name-entry action as `O프`. The final `J/Q/W/Y/Z` allocation preserves
  `B/K/U` and fixes both regressions.
- Fresh-boot live selector row 28 displayed `근육의 신전`, entered preparation,
  completed automatic deployment, and reached the original secret-stage label
  `SCENARIO ?1` / `TURN 1`. The unconditional opening advanced through Baran,
  Adon, Samson, Lester, Sherry, and Jessica and returned to Elwin's command
  menu. No Japanese text, blank dialogue, reset, or freeze remained. A supposed
  one-character Baran page was reproduced with a ten-second wait and proved to
  be a capture taken during portrait/typewriter animation; the complete line
  rendered normally. Evidence includes `captures/run/6782_s28_turn1.png`,
  `6782_s28_baran.png`, `6782_s28_row8_wait10.png`, and the per-input sequence
  under `captures/run/6782_s28_slow/`. A final fresh boot after the terminology
  adjustment reconfirmed the Korean speaker/status label in
  `captures/run/452c_s28_baran.png` and retained the intact small `TURN` label.
- Final checksum `0267` uses 765/766 shared custom glyph slots and passes all
  109 tests. A fresh Scenario 1 boot also preserved name-entry `OK/NO`, reached
  the route screen, and rendered the Start-menu save prompt with intact
  `YES/NO`; see `captures/run/0267_name_entry.png`,
  `0267_name_confirm_route.png`, and `0267_save_confirm.png`. Conditional
  combat, conversion, item, death, and post-battle branches remain part of the
  whole-game route regression pass.

### Complete Direct Speaker And Monster Name Table (2026-07-13)

- The original direct 16x16 name table at `0x097404..0x09765E` was rendered
  from the Japanese ROM and checked address by address. It contains 57 records
  covering named characters, generic speakers, and monster names. Evidence is
  `captures/analysis/jpfont_probe/direct_097400_097660_jp_original.png`.
- The 26 previously deferred records are now default patches. They include
  `가면기사`, `기잠`, `세이갈`, `폴거`, `일반병`, `사제`, `해적`, every
  monster record from `웨어울프` through `데몬로드`, and
  `형님/마녀/제국병/파이어스`. `グレートドラゴン` is rendered without the
  old abbreviation as `그레이트드래곤`. The complete Korean sheet is
  `captures/analysis/jpfont_probe/direct_097400_097660_ko_4dc7.png`.
- Five new syllables were required: `폴/큐/뱀/켄/몬`. Four single-use dialogue
  syllables were removed with meaning-preserving edits at
  `0x186B2C`, `0x189868`, `0x1A039C`, and `0x1AF90E`. The resulting pages were
  rebuilt and inspected under `captures/analysis/event_pages_ko/` for
  Scenarios 2, 3, 15, and 24; none are blank or clipped.
- Failed allocation order: putting the new direct-name strings before the
  established name-entry consumers kept the total at 766 but shifted `릭` to
  glyph `0x7267`, beyond the verified name-entry ceiling `0x7262`. The builder
  rejected that ROM. `LATE_DIRECT_NAME_GLYPH_OFFSETS` now allocates the 26
  promoted records after the name-entry set, preserving all established UI
  IDs while still patching the same direct records.
- Current checksum `4DC7` uses exactly 766/766 custom 16x16 glyph slots. The
  legacy `--include-unsafe-direct-names` build is now idempotent and produces
  the same checksum. All 110 tests pass, the direct candidate inventory has
  zero unclassified and zero unsafe name records, and a fresh boot confirmed
  intact `엘윈`, `OK/NO`, and route entry in
  `captures/run/4dc7_name_entry.png` and `4dc7_name_confirm.png`.

### Complete Ending Visit Dialogue Records (2026-07-13)

- The ending visit script at `0x09540C..0x0954DF` points to 14 main Japanese
  records corresponding to English reference records 1785-1798. The Liana
  travel ending additionally chains nine short response records. All 23 source
  records are now translated in `localization/ending_dialogue_ko.json`.
- Japanese ROM text and pointers remain authoritative. The English extraction
  was used only to cross-check long-record continuity. Each translation records
  the complete source SHA-256 and preserves the original ordered `FFF7` actor
  IDs and exact `FFFD` page-break count. The builder rejects a changed source,
  missing name control, altered page count, or record overflow.
- The earlier direct inventory mistook suffixes such as `0x09600E` for complete
  pages because its conservative scanner stops after 64 words. Full-record
  tracing found actual starts including `0x0954E2`, `0x096090`, `0x0963A4`,
  `0x096518`, `0x0967A4`, and `0x096A84`. Sixteen old suffix probes were retired
  as write targets. Their text remains allocation-only compatibility input so
  established UI and name-entry glyph IDs do not move.
- The 68000 converter at `0x02C390` masks the glyph ID to all 16 bits and shifts
  it by 64 bytes from font base `0x040000`. Static relocation analysis proves
  that glyph `0x7300` begins at ROM `0x20C000`, before the next relocated data
  at `0x270000`. `CUSTOM_GLYPH_RANGES` therefore extends through `0x73FE`, with
  an overlap guard and `tests/test_custom_glyph_storage.py`. The translated
  ending needs only eight new syllables and ends at glyph `0x7306`.
- Checksum `69D4` uses 774/1021 available custom glyph slots and passes all 120
  tests. Complete original and Korean record sheets are under
  `captures/analysis/ending_records_jp_original/` and
  `captures/analysis/ending_records_ko_69d4/`; all 23 records render Korean,
  fit at most 24 visible cells per authored line, and contain no Japanese glyph
  IDs outside preserved dynamic-name arguments. A fresh `69D4` boot preserved
  the `엘윈` default, `OK/NO`, the 57-character name grid, route entry, and the
  `시나리오 1 / 서장` screen without a reset; see
  `captures/run/69d4_name_entry.png`, `69d4_name_confirm.png`, and
  `69d4_scenario1.png`. Live ending-route verification remains required before
  the ending translation itself can be promoted beyond static review.

### Character Epilogue Inventory And Scott Outcomes (2026-07-13)

- The character epilogue resource is 90 complete Japanese records in
  `0x0895A2..0x0954E2`, not the short suffix fragments previously reported by
  the conservative direct-string scan. `tools/jp_epilogue_inventory.py`
  accepts an English-map address only after the Japanese ROM proves exactly
  one pointer owner and a complete `FFFF`-terminated record. The resulting
  source hashes, capacities, controls, and pointer owners are in
  `localization/epilogue_records.json` and `docs/epilogue_inventory.md`.
- Pointer order groups the records as Scott 0-8, Sherry 9-17, Keith 18-26,
  Lana 27-35, Aaron 36-44, Lester 45-53, Hein 54-62, Jessica 63-71,
  Imperial/villain outcomes 72-77, Liana 78-85, and world outcomes 86-89.
  The original sheets are under
  `captures/analysis/epilogue_records_jp_original/`.
- Scott's nine outcome records at `0x0895A2..0x08A566` are translated in
  `localization/epilogue_dialogue_ko.json`. They cover his different growth,
  survival, family, Salrath, and monster-attack outcomes. The builder validates
  each full Japanese source SHA-256, ordered dynamic controls, exact page-break
  count, and in-place capacity before writing it.
- The direct inventory now classifies the nine translated Scott suffixes as
  `declared_epilogue_translation` and leaves the remaining 81 explicitly
  `confirmed_untranslated_epilogue_fragment`; it has zero unclassified
  candidates. `tools/render_direct_inventory_pages.py --record-inventory`
  supports complete-record sheets rather than only conservative suffixes.
- Checksum `052E` uses 782 custom glyphs through `0x730E` and passes all 127
  tests. All nine Korean Scott records were rendered in
  `captures/analysis/epilogue_records_ko_052e_scott/` with no Japanese text in
  authored content. A live final-route epilogue check is still pending; do not
  treat static rendering alone as complete end-to-end verification.

### Sherry Epilogues, Baseline Punctuation, And Battle Font Recovery (2026-07-13)

- Sherry's nine outcome records at `0x08A73A..0x08B6D8` are translated in
  `localization/epilogue_dialogue_ko.json`. The source records are refs
  `E1910..E1918`; each entry records the full Japanese SHA-256 and preserves
  ordered actor controls, page breaks, terminators, and in-place capacity.
  Original sheets are under
  `captures/analysis/epilogue_records_jp_sherry/`, and the Korean render is
  `captures/analysis/epilogue_records_ko_80e6_sherry/`. This brings the
  epilogue inventory to 18 translated records out of 90.
- Custom 16x16 `.` and `,` glyphs previously inherited centered font metrics,
  so dialogue punctuation floated at mid-cell height. `render_hangul_glyph()`
  now draws them explicitly on rows 12-13 and 11-14 respectively, matching the
  existing bottom-aligned ellipsis. `test_period_and_comma_use_dialogue_baseline`
  prevents this regression.
- Japanese class table `0x05E6D6` proves Scenario 1 Laird uses class IDs
  13/55/56 `ﾏｼﾞｯｸﾅｲﾄ` and Leon uses class 69 `ﾅｲﾄﾏｽﾀｰ`. Their byte-status
  labels are therefore the exact `매직나이트` and `나이트마스터`, not the
  earlier abbreviations `마전사` and `기사장`. Fresh live evidence is
  `captures/run/80e6_laird_map_status.png` and
  `captures/run/80e6_leon_map_status.png`. Class 113 `シビリアン` is `시민`;
  only the narrow map-status record for `민병대` is compacted to `민병` to fit
  the verified 64-slot byte-font budget. The direct 16x16 name remains
  `민병대`.
- Failed attempt and root cause: byte-font code `0xB0` had been assigned to
  Korean `록`. That tile is live decoration in the battle result renderer, so
  the center rows became `록AT록`, `록DF록`, and a similarly corrupted
  formation row. `0xB0` is now excluded from the Korean byte-font pool and
  `록` uses the verified private ASCII tile `I`. The builder test compares the
  patched `0xB0` tile byte-for-byte with the original ROM.
- Live verification used an ignored temporary ROM that moved the Scenario 1
  imperial commander adjacent to Elwin without changing the committed game
  data. The resulting battle screen displays the original `-AT-`, `-DF-`, and
  formation decorations with no Korean intrusion; evidence is
  `captures/run/80e6_battle_result_decoration_fixed.png`. The temporary ROM
  `/tmp/lang2_battle_ui_probe.md` is not a distributable artifact and must not
  be committed.
- Checksum `80E6` uses 790 custom glyphs through `0x7316`. Both inventories
  regenerate cleanly (`90` epilogue records, `783` direct candidates, zero
  unclassified), and the complete test suite passes all 129 tests. A live
  final-route Sherry epilogue check is still pending alongside the other
  ending-route checks.

### Keith Epilogue Outcomes (2026-07-13)

- Keith's nine outcome records at `0x08B8C4..0x08C9AA` are translated in
  `localization/epilogue_dialogue_ko.json`. They are English cross-reference
  records `E1901..E1909`; the Japanese ROM records and pointer owners remain
  authoritative. Source SHA-256, capacity, and exact page-break counts are
  enforced for every entry.
- The outcomes preserve the original condition differences: Keith's reputation
  as a surviving warrior or Kalzath's greatest knight, protection and rebuilding
  of Kalzath, domestic or continental monster eradication, marriage, unit
  disbandment and solitary wandering, failure to save a woman, and Keith's own
  death. The low-performance branches do not borrow the success text.
- Checksum `4CAF` uses 794 custom glyphs through `0x731A`. The complete Korean
  record render is under
  `captures/analysis/epilogue_records_ko_4caf_keith/`; records 18-26 on sheets
  01 and 02 contain Korean authored text with all original page markers and no
  visible clipping or Japanese residue. The inventories report 27 translated
  epilogues out of 90, 63 confirmed untranslated epilogue fragments, and zero
  unclassified direct candidates. All 129 tests pass.
- This is still static record verification. A temporary ending/epilogue selector
  or natural final-route playthrough must verify these pages in the actual
  ending renderer before full-game completion can be claimed.

### Lana Epilogue Outcomes (2026-07-13)

- Lana's nine outcome records at `0x08CBCE..0x08DD68` are translated in
  `localization/epilogue_dialogue_ko.json` from Japanese ROM source records,
  with English records `E1943..E1951` used only as continuity references.
  Every source hash, in-place capacity, and original 4-6 page-break count is
  enforced before the builder writes the record.
- The translations keep the original outcome distinctions: medicine versus
  healing magic, partial or complete plague recovery, blindness as a serious
  side effect, appointment as archbishop or pope, failure to find a cure,
  infection and death without results, completing a preventative medicine at
  the cost of Lana's life, and the modest result that earns her recognition as
  a model sister.
- Checksum `8A46` uses 799 custom glyphs through `0x731F`. The rendered record
  sheets are under `captures/analysis/epilogue_records_ko_8a46_lana/`;
  records 27-35 on sheets 02 and 03 contain Korean text through Lana's final
  outcome, while record 36 correctly begins the still-untranslated Aaron
  group. No blank page, clipping, or authored Japanese residue was visible.
- Inventories now report 36 translated epilogues out of 90, 54 confirmed
  untranslated epilogue fragments, 783 classified direct candidates, and zero
  unclassified candidates. All 129 tests pass. Actual playback through the
  ending renderer is not yet proven; the next development task is an ignored,
  non-distribution epilogue selector/harness for BlastEm verification.

### Stock Ending Epilogue Probe (2026-07-13)

- Static disassembly found the actual normal-character epilogue selector at
  `0x01DC64`. It reads character index RAM `0xFFFFAE90`, indexes the group table
  at `0x08916E`, evaluates two inclusive statistic ranges, and passes the
  selected record pointer to the stock text object created by `0x0094DC` with
  callback `0x37E4`.
- `tools/build_epilogue_probe_rom.py` builds an ignored ROM that keeps this
  original renderer but redirects the selected character slot to one requested
  record. Other normal slots use a synthetic `FFFF` skip descriptor. Liana's
  eight-pointer table at `0x089572` and the four world outcomes at `0x089592`
  are handled separately, matching the original branches.
- The two synthetic descriptors occupy verified `FF` space at `0x3FF000` in
  the expanded probe copy only. The tool validates the Japanese record hash,
  original selector tables, record presence, reserved free space, and updates
  the Mega Drive checksum. Record 18 produced an ignored checksum `4D2F` ROM
  without launching BlastEm.
- `tests/test_epilogue_probe_rom.py` covers all 90 record-to-character-slot
  mappings, normal and special pointer rewrites, Japanese source rejection,
  and checksum regeneration. Detailed usage and the remaining Scenario 27
  end-state step are in `docs/epilogue_probe.md`.
- Live playback remains pending. The user explicitly requested no emulator,
  mouse, or keyboard activity while doing other work, so no BlastEm process was
  started during this analysis.

### Aaron Epilogue Outcomes (2026-07-13)

- Aaron's nine outcome records at `0x08DF62..0x08EED6` are translated in
  `localization/epilogue_dialogue_ko.json`. The Japanese record sheets
  `captures/analysis/epilogue_records_jp_original/direct_record_03.png` and
  `direct_record_04.png` were read directly; English records `E1961..E1969`
  were used only to resolve continuity. Each translation is bound to the full
  Japanese source SHA-256 and preserves its original 4-5 page breaks and
  in-place capacity.
- The distinct branches remain separate: a peaceful retirement teaching
  children, a nationally famous school influenced by Sherry, victory over
  challengers despite Aaron's age, accidental death during live-blade
  training, returning to battle to seek a place to die, mutual death against
  an evil dragon, poverty without pupils, death before gathered disciples, and
  retirement from swordsmanship while warmly watching the children train.
- Checksum `5696` uses 805 custom glyphs through `0x7325`. Complete static
  sheets are under `captures/analysis/epilogue_records_ko_5696_aaron/`;
  records 36-44 on sheets 03 and 04 show Korean authored text with no visible
  blank page, clipping, or Japanese residue.
- Inventories now report 45 translated epilogues, 45 confirmed untranslated
  epilogue fragments, 783 classified direct candidates, and zero unclassified
  candidates. All 134 tests pass.
- No emulator, mouse, or keyboard automation was used for this group because
  the user requested background-only work. Actual playback through the stock
  ending renderer remains pending and must use the ignored probe after emulator
  use is explicitly permitted.

### Lester Epilogue Outcomes (2026-07-13)

- Lester's nine outcome records at `0x08F0B0..0x090104` are translated in
  `localization/epilogue_dialogue_ko.json`. Japanese sheets 04 and 05 in
  `captures/analysis/epilogue_records_jp_original/` were the translation
  authority; English records `E1952..E1960` were continuity references only.
  Every full source SHA-256, capacity, and original 3-6 page-break count is
  checked before the builder writes a record.
- The translations keep the original branches distinct: returning to piracy
  and becoming the Pirate King, choosing an honest life before defeating a sea
  monster or pirate fleet, disappearing after a reckless solo attack, mutual
  financial ruin between pirate groups, dying after defeating the enemy
  leader, being cut down after turning to robbery, returning to Jessica and
  guarding the Rahl River, and dying in that river while protecting her.
- Checksum `64BF` uses 810 custom glyphs through `0x732A`. Static sheets are in
  `captures/analysis/epilogue_records_ko_64bf_lester/`; records 45-53 span
  sheets 03-05 and show Korean authored text without visible blank pages,
  clipping, or Japanese residue.
- Inventories now report 54 translated epilogues, 36 confirmed untranslated
  epilogue fragments, 783 classified direct candidates, and zero unclassified
  candidates. All 134 tests pass. This is static evidence only; no emulator or
  input automation was used, and stock ending playback is still pending.

### Hein Epilogue Outcomes (2026-07-13)

- Hein's nine outcome records at `0x090300..0x09135E` are translated in
  `localization/epilogue_dialogue_ko.json`. The Japanese source sheets 05 and
  06 in `captures/analysis/epilogue_records_jp_original/` were read directly;
  English records `E1978..E1986` served only as continuity references. Full
  source hashes, capacities, and the original 4-5 page-break counts are
  enforced for all nine records.
- The branches retain their separate outcomes: practical magic and helping
  people, discovering ancient spells and becoming a Great Wizard, founding a
  continental wizard guild, producing useless novelty magic, fortune-telling
  and finding royal treasure, weather control that enriches the continent,
  failed reincarnation, being dragged into the demon realm by a forbidden
  summon, and death caused by greed over weather-magic fees.
- Checksum `5361` uses 819 custom glyphs through `0x7333`. Static sheets are in
  `captures/analysis/epilogue_records_ko_5361_hein/`; records 54-62 on sheets
  04 and 05 contain Korean authored text without visible blank pages,
  clipping, or Japanese residue.
- Inventories now report 63 translated epilogues, 27 confirmed untranslated
  epilogue fragments, 783 classified direct candidates, and zero unclassified
  candidates. All 134 tests pass. No emulator or input automation was used;
  live playback through the stock ending renderer remains pending.

### Jessica Epilogue Outcomes (2026-07-13)

- Jessica's nine outcome records at `0x09158C..0x092612` are translated in
  `localization/epilogue_dialogue_ko.json`. Japanese source sheets 06 and 07
  in `captures/analysis/epilogue_records_jp_original/` were the translation
  authority, with English records `E1925..E1933` used only to cross-check
  continuity. Full source hashes, capacities, and original 4-5 page-break
  counts are enforced for every record.
- The branches preserve whether Hein becomes Jessica's apprentice, whether
  she writes an advanced or beginner-friendly grimoire, establishes the Rahl
  River School or history's first university of magic, fades from history,
  leaves the world temporarily through reincarnation, or departs on a journey
  for knowledge and spiritual discipline.
- Checksum `9599` uses 821 custom glyphs through `0x7335`. Static sheets are in
  `captures/analysis/epilogue_records_ko_9599_jessica/`; records 63-71 on
  sheet 05 contain Korean authored text without visible blank pages, clipping,
  or Japanese residue.
- Inventories now report 72 translated epilogues, 18 confirmed untranslated
  epilogue fragments, 783 classified direct candidates, and zero unclassified
  candidates. All 134 tests pass. No emulator or input automation was used;
  stock ending playback remains pending.

### Imperial And Villain Epilogue Outcomes (2026-07-13)

- The six normal-selector villain records at `0x092820..0x093370` are
  translated in `localization/epilogue_dialogue_ko.json`: Bozel, Vargas,
  Imelda, Leon, Egbert, and Bernhardt. Japanese source sheet 07 in
  `captures/analysis/epilogue_records_jp_original/` was the translation
  authority; English records `E1919..E1924` were continuity references only.
- Full Japanese hashes, capacities, original 4-10 page-break counts, and the
  ordered `FFF7` protagonist-name controls are enforced. The Korean records
  preserve all controls for Vargas (three), Imelda (two), Leon (three), Egbert
  (three), and Bernhardt (one); Bozel has no dynamic-name control.
- The outcomes retain the original causes and relationships: Bozel absorbed by
  Alhazard, Vargas dying while rescuing his men, Imelda's Ice Dragon Navy
  collapsing, Leon sharing Bernhardt's fate, Egbert's Black Dragon magic and
  death, and Bernhardt's final battle and deliberate Alhazard runaway.
- Checksum `3E98` uses 831 custom glyphs through `0x733F`. Static sheets are in
  `captures/analysis/epilogue_records_ko_3e98_villains/`; records 72-77 on
  sheet 06 contain Korean authored text without visible blank pages, clipping,
  or Japanese residue. The visible `CTL` markers are intentional renderings of
  preserved dynamic-name controls, not text corruption.
- Inventories now report 78 translated epilogues, 12 confirmed untranslated
  epilogue fragments, 783 classified direct candidates, and zero unclassified
  candidates. All 134 tests pass. No emulator or input automation was used;
  stock ending playback remains pending.

### Liana Epilogue Outcomes (2026-07-13)

- Liana's eight special-selector records at `0x0937B2..0x09458C` are
  translated in `localization/epilogue_dialogue_ko.json`. Japanese source
  sheets 07 and 08 in `captures/analysis/epilogue_records_jp_original/` were
  the translation authority; English records `E1970..E1977` were continuity
  references only. Full hashes, capacities, original 4-5 page-break counts,
  and record 79's single dynamic protagonist-name control are enforced.
- The branches distinguish royal or noble support and marriage, working with
  the returning protagonist to end war, accepting a political marriage to fund
  the orphanage, becoming revered as a saint, death from starvation and
  overwork, abandonment after a fraudulent marriage, and independent orphanage
  management ending in death from exhaustion.
- These records use the original direct eight-pointer table at `0x089572`, not
  the normal statistic descriptor groups. `tools/build_epilogue_probe_rom.py`
  and its tests retain this separate selector path.
- Checksum `7E98` uses 833 custom glyphs through `0x7341`. Static sheets are in
  `captures/analysis/epilogue_records_ko_7e98_liana/`; records 78-85 on sheets
  06 and 07 contain Korean authored text without visible blank pages, clipping,
  or Japanese residue.
- Inventories now report 86 translated epilogues, four confirmed untranslated
  world-epilogue fragments, 783 classified direct candidates, and zero
  unclassified candidates. All 134 tests pass. No emulator or input automation
  was used; stock ending playback remains pending.

### World Epilogue Outcomes And Static Completion (2026-07-13)

- The four world-outcome records at `0x0947E0..0x094F1A` are translated in
  `localization/epilogue_dialogue_ko.json`. Japanese source sheet 08 in
  `captures/analysis/epilogue_records_jp_original/` was the translation
  authority; English records `E1987..E1990` were continuity references only.
  Full hashes, capacities, original six or ten page-break counts, and all
  ordered protagonist-name controls are enforced.
- The four branches distinguish recognizing inexperience and leaving on a new
  adventure, becoming a silver-wing-tiara hero in later legends, ending a war
  on another continent after substantial growth, and the long final reflection
  on wartime losses, trust, false peace through force, and traveling with Liana
  to build a world without war.
- These records use the original four-pointer world table at `0x089592`.
  `tools/build_epilogue_probe_rom.py` retains and tests this path separately
  from both normal character descriptors and Liana's eight-pointer table.
- Checksum `D39F` uses 834 custom glyphs through `0x7342`. Complete static
  sheets are under `captures/analysis/epilogue_records_ko_d39f_complete/`;
  records 86-89 on sheet 07 contain Korean authored text without visible blank
  pages, clipping, or Japanese residue. Visible `CTL` markers are intentional
  representations of dynamic-name controls.
- The character-epilogue inventory now reports all 90 records translated. The
  direct inventory reports zero untranslated epilogue fragments, 90 declared
  epilogue translation fragments, 783 classified candidates, and zero
  unclassified candidates. All 134 tests pass.
- This completes static translation of the 90-record epilogue resource only.
  It does not complete the full-game Goal: no emulator or input automation was
  used, stock ending playback is still pending, and all routes still require
  runtime regression checks before the localization can be called complete.

### Scenario 27 Ending And Live Epilogue Paths (2026-07-14)

- `tools/build_scenario27_ending_probe_rom.py` validates Scenario 27 header
  `0x1830CC`, deployment table `0x1830F2`, Elwin's automatic position `(15,16)`,
  and the exact Bernhardt record at `0x18323E`. Its ignored output moves an
  unguarded AT/DF 0 Bernhardt to `(15,15)`. Tests reject changed layout/records
  and verify the checksum. AT/DF 0 does not by itself guarantee a one-attack
  defeat; save immediately before Attack and retry from that state as documented
  below.
- The production checksum after the ending-label fix is `451C`. Its Scenario 27
  probe checksum `9B8E` ran through the Korean route, prologue, preparation,
  22-screen opening, Bernhardt battle, complete closing event, ending art,
  history pages, and multiple normal character epilogues without reset.
- Live playback exposed the stock Japanese epilogue labels `敵撃破数` and
  `撤退回数`. The dedicated eight-word glyph list at `0x089146` is now validated
  before the builder writes `격파횟수퇴각횟수`. The corrected screen is
  `captures/run/9b8e_epilogue_labels_live2.png`.
- `tools/build_epilogue_probe_rom.py --start-slot` replaces the six-byte
  `CLR.W $FFFFAE90` at `0x01C7A8` with an equal-length absolute-short
  initializer. Slot 14 starts Liana and slot 15 starts the world record while
  retaining the stock callbacks. Tests cover valid and rejected initializers.
- Liana record 78 used start slot 14 and combined checksum `94FE`. Its direct
  eight-pointer path, portrait/background, Korean `격파횟수/퇴각횟수`, and Korean
  record text were confirmed in `captures/run/94fe_liana78_transition1.png`.
- World record 86 used start slot 15 and combined checksum `CEDD`. Its direct
  four-pointer path and final Korean `그리고 모든 것은 전설이 됐다...` page were
  confirmed in `captures/run/cedd_world86_transition1.png`.
- BlastEm GST files are ROM-content-specific, so swapping probe ROMs under a
  pre-epilogue GST failed. Editing RAM index `0xAE90` in an active GST also
  changed the already-installed callback flow and ended early. Do not repeat
  either approach; rebuild the combined probe and replay Scenario 27.
- The same run exposed Japanese credit overlays between ending scenes. Credits
  remain a full-localization task even though all 90 epilogue records are
  statically translated and all three selector classes now have live evidence.

### Korean Credits And Three-Line Ending Windows (2026-07-14)

- The credits pointer table is `0x0A333A`, with 60 ordered big-endian pointers
  to records at `0x0A342A..0x0A3752`. The table SHA-256 is
  `b2081d5421643bcce3dccf67ec6dc241177addd81184e85a7a945abc95141ebf`;
  concatenated source records hash to
  `3f01aa3cb7858ef4e62efb88e490552313310430cff4d0b93ca00f76d6404ac8`.
- `localization/credits_ko.json` owns all 60 records. The builder validates both
  hashes and every source address, relocates the records to
  `0x2B0000..0x2B2000`, updates the pointer table, and preserves the final
  `COPYRIGHT 1994 NCS` record plus the unrelated digit helper at `0x0A3788`.
  Offline evidence is under `captures/analysis/credits_ko_relocated/`.
- Live Scenario 27 playback exposed a real soft-lock at ending record
  `0x0954E2`: a Korean page contained four explicit lines, but the stock visit
  window only accepts three lines per form-feed page. Eleven ending pages and
  two epilogue pages had the same risk. All were reflowed to at most three
  lines, and both test modules now enforce the renderer limit in addition to
  the existing 24-character line limit and control preservation.
- The rebuilt production checksum is `E551`; the Scenario 27 ending probe is
  `3BC3`. The full 145-test suite passes. A final live replay of the corrected
  page and relocated credits remains required before committing this unit.
- `tools/send_blastem_keys.py` now names BlastEm's right-Control keyboard
  capture toggle as `capture`, Escape as `menu`, and Tab as `tab`. XTest input
  can be lost after remote-desktop focus changes while direct game-key events
  still work. BlastEm also supports `-s FILE` for startup GST loading, but GST
  files are ROM-content-specific; do not use a state from another checksum as
  proof of a current build.

### Later-Scenario Commander Name Regression (2026-07-14)

- Live checksum `3BC3` Scenario 27 preparation displayed correct `엘윈/헤인`
  but corrupt-looking remaining roster rows. The source roster is
  `엘윈, 헤인, 셰리, 아론, 키스`; the bad rows are the original Japanese
  byte-name records being drawn through the partially replaced Korean 8x8
  font. This is not an SRAM checksum failure or a 16x16 credits-glyph collision.
- The actual byte-name pointer table is `0x0618E8`. Relevant unpatched records
  are `0x061AD3=シェリー`, `0x061AE5=アーロン`, and
  `0x061AE1=キース`. With the current global mapping those bytes render as
  strings resembling `맨립헤-`, `인-랑나`, and a corrupt `키스`; capture evidence is
  `captures/run/3bc3_current_commander_names.png`.
- The production byte-font pool is already 64/64. Exact playable-name coverage
  needs six additional syllables (`라/론/셰/카/코/키`) beyond the currently
  allocated set. Blindly appending them would displace verified glyphs used by
  `소지금`, equipment categories, `클레릭`, `나이트마스터`, and secret-stage
  names. Do not fix this by re-enabling `0x80..0xA4`, `0xB0`, lowercase, or
  `0xE0..0xFF`; those ranges previously corrupted faction, terrain, status,
  battle-result, and gauge graphics.
- The safe fix is an engine-level/context-specific byte-font bank or renderer
  extension, followed by patching every byte-name and class pointer from the
  Japanese source tables. A probe-only glyph swap or abbreviation is not a
  production fix.
- The production fix relocates the 429-entry compressed-resource table to
  `0x2B2000`, appends resource `429` at `0x2B2800`, and loads its 15 tiles at
  VRAM `0x3F0..0x3FE`. Localized FF-terminated byte strings use `F0..FE` only
  as escape values; the original `F0..FE` tiles remain untouched because they
  contain live status graphics. The six currently used extension syllables
  are `라/론/셰/카/코/키`.
- Two approaches were rejected by live testing. Loading extension tiles into
  `F0..FE` only for preparation was overwritten by later common font loads at
  `CC80`, `C920`, and `CA70`. Mapping the roster path at `0x295B0` also did not
  affect the visible five-name list because that is a different UI builder.
  BlastEm `-l` writes unique executed block addresses to
  `tools/blastem/address.log`; it identified the actual preparation list
  builder at `0x22496`.
- The left roster reads the name pointer table at `0x618E8` and writes ordinary
  characters through `0x2251A`. Hook `0x22502` now preserves the DE/DF mark
  path and maps `F0..FE` to `3F0..3FE` before the store. Other byte-name paths
  are covered by the common word/tile/plane and status-panel render hooks in
  `install_byte_ui_extension()`.
- Checksum `524D` live-verifies Scenario 27 preparation as
  `엘윈/헤인/셰리/아론/키스`; the plane rows contain `3F2`, `3F1`, and `3F5`
  rather than raw `F2`, `F1`, and `F5`. Capture:
  `captures/run/524d_s27_prep_names2.png`. Scenario 1 still shows
  `엘윈/헤인` with the LV/status graphics intact in
  `captures/run/524d_s01_prep2.png`. All 148 tests pass.

### Remaining Playable-Name And Automation Verification (2026-07-14)

- A non-distribution renderer probe copied the production ROM and replaced
  only the five Scenario 27 preparation name records. It live-rendered
  `제시카/스코트/레스터/라나` through the same `0x22502` roster hook without
  changing the production ROM or diagnostic SRAM. Evidence is
  `captures/run/5a88_s27_step9.png`; the earlier variant with `라나/스코트/
  레스터/리아나` is `captures/run/345a_s27_step3.png`.
- `레스터` is encoded as `D1 AF AB`; decompressed production tile `D1`
  byte-for-byte matches a fresh Galmuri7 `레` render. At native 8x8 size it can
  resemble `리`, but this is not a font collision. Offline comparison is
  `captures/analysis/524d_re_ri_tiles.png`.
- A stale address-trace process launched as `./blastem -l` remained alive while
  later commands searched only for the absolute executable path. The capture
  helper therefore selected the old pre-extension window and appeared to show
  a regression. Use process name `blastem`, not a command-line path substring,
  when checking or terminating test instances.
- The Scenario Select cheat is timing-sensitive: 0.8-second waits between
  Left, Right, Start, C perform an ordinary load, while 0.12-second holds and
  0.05-second gaps reliably expose the `로드01` suffix. The automation now
  uses that timing, refuses to launch beside an existing BlastEm by default,
  supports `--replace-existing`, and enables keyboard capture once on a fresh
  `--click-window` launch. This specifically addresses remote-desktop focus
  loss without silently choosing the wrong emulator window.

### Full Byte Name And Class Tables (2026-07-15)

- The six-tile `F0..FE` extension was not sufficient for the complete game.
  All 157 class records and 117 name records together require 171 distinct
  glyph entries including space. The production builder now validates the
  original pointer tables and concatenated source records by SHA-256, relocates
  every Korean record to `0x2B9000..0x2BB000`, and encodes each glyph as
  `00,index` followed by the original `FF` terminator. Original JP strings do
  not use `00`, so untouched strings remain distinguishable.
- A 16-bit index-to-VRAM table at `0x2B8000` reuses verified base glyphs and
  allocates the remaining glyphs across six map/preparation VRAM segments:
  `340..347`, `398..3AF`, `440..447`, `498..4AF`, `4D8..4EF`, and
  `5D8..5F3`. Resources 430 through 435 are appended to the relocated compressed
  resource table and loaded with the normal byte font. Resource 429 and the
  `F0..FE -> 3F0..3FE` name-entry compatibility path remain intact.
- Every known byte-string renderer now recognizes the pair encoding. The map
  commander popup needed its separate `0x2115E` path redirected from calls
  `0x20EDA/0x20F08`. The bottom map status bar also reaches `0x105BC` through
  relative `BSR` calls at `0x1042E/0x10444`, so patching only three absolute
  callers was insufficient; the `0x105BC` entry itself now jumps to the
  localized renderer. Do not repeat the partial-call-site approach.
- Checksum `988E` live-verifies Scenario 1 preparation `엘윈/파이터` and the
  map popup plus bottom status bar for `제국지휘관/파이터`, `주민/클레릭`,
  `레아드/매직나이트`, and `레온/나이트마스터`. It also verifies the
  source-ID mercenary labels `로얄호스` for Leon and `헤비호스맨` for Laird.
  Captures are `captures/run/c228_prep.png`,
  `captures/run/988e_enemy_bottom.png`, `988e_npc_status.png`,
  `988e_leard_status.png`, `988e_leon_status.png`,
  `988e_leon_merc_status3.png`, and `988e_leard_merc.png`.
- Earlier checksum `C228` proved the relocated preparation roster but exposed
  raw local indexes in the map popup; `9A7B` fixed that popup but still exposed
  raw indexes in the bottom bar. These are failed intermediate builds, not
  release candidates. The current full test suite has 152 passing tests.
- Korean spelling is intentionally `쉐리` per project direction. Scenario 1's
  JP class IDs confirm Laird as `ﾏｼﾞｯｸﾅｲﾄ`, Leon as `ﾅｲﾄﾏｽﾀｰ`, Leon's
  mercenary as `ﾛｲﾔﾙﾎｰｽ`, and Laird's as `ﾍﾋﾞｰﾎｰｽﾏﾝ`; these labels are not
  inferred from sprite appearance.

### Preparation Selected Names And Hire Classes (2026-07-15)

- Full-table checksum `988E` exposed two more direct byte readers in Scenario
  27 preparation. The selected commander summary at the lower left rendered
  pair indexes as `Z !`, `6 T`, `P 7`, and `3 D`; the hire list rendered a
  class as a lone `E`. These were not magic or equipment names.
- The lower-left refresh routine is `0x229F4`, called after the selected unit
  pointer is resolved at `0x22978`. It now jumps to the pair-aware command
  stream builder at `0x2B7A00`. The separate preparation/deployment name copy
  at `0x27A64` also jumps to `0x2B7900` so later arrangement rows do not expose
  the same indexes.
- The hire-list builder reads the class pointer table directly at `0x22AF2`
  and formerly copied bytes from `0x22AFC`. That loop now jumps to `0x2B7B00`,
  preserving its eight-cell padding and dakuten control behavior while mapping
  localized pairs.
- Checksum `F153` live-verifies `키스`, `헤인`, `쉐리`, and `아론` in both the
  roster/status panel and lower-left selected-name panel. It also verifies
  Keith's original-source hire classes as `솔저` and `그리폰`. Scenario 1 was
  re-entered on the same build and still displays `엘윈/파이터` plus the
  lower-left `엘윈` without corrupting `소지금`. Evidence:
  `captures/run/f153_s27_direct_down.png`, `f153_s27_sherry.png`,
  `f153_s27_hein.png`, `f153_s27_aaron_verified.png`, and
  `f153_s27_hire_class2.png`, plus `f153_s01_prep.png`.
- Global XTest input was ignored after a WSLg/remote-focus transition even
  though the window was raised. `tools/send_blastem_keys.py --send-event`
  delivered the same D-pad/C inputs directly to the BlastEm window and allowed
  deterministic verification. Treat unchanged frames as an input-delivery
  issue before changing game logic.
### Project Credit

- Project developer ID: `hsp1324`.
- The repository README and the localized in-game staff roll both credit this
  ID. The in-game implementation adds synthetic record 60, `한국어화 hsp1324`,
  without replacing any of the 60 original records or `COPYRIGHT 1994 NCS`.
- The original 16-sequence placement table at `0x0A3172` and 60-record pointer
  table at `0x0A333A` are hash-validated. They are expanded at `0x2BB000` and
  `0x2BB800`; the final sequence retains copyright record 59 at `(0x10,0x5A)`
  and adds developer record 60 at `(0x40,0x78)`. Renderer `LEA` operands at
  `0x02A634` and `0x02A65A` point to the relocated tables.
- Checksum `743F` renders the new record correctly offline at
  `captures/analysis/credits_ko_hsp1324/direct_record/060_2B03AA.png`.
  The combined Scenario 27 ending/world-slot probe checksum is `F2FC`.
  Stock playback reached the final group after the world epilogue and rendered
  both `COPYRIGHT 1994 NCS` and `한국어화 hsp1324` without reset or overlap in
  `captures/run/f2fc_credit_final_watch/324.png`.

### Final Credit Playback And Automation Notes (2026-07-15)

- Scenario 27 stat bytes are signed class modifiers, not final AT/DF values.
  Writing zero left Emperor's `AT 12/DF 4`, allowed Bernhardt to survive at
  one HP, and could trigger healing. The ending probe now writes `-12/-4` and
  checksum `BFAD` live-verifies actual `AT 0/DF 0`. Do not restore literal zero
  bytes, but do not treat the displayed zeroes as deterministic damage either.
- Applying `tools/build_epilogue_probe_rom.py --record-index 86 --start-slot 15`
  to `BFAD` produces ignored checksum `F2FC`. The complete route was replayed
  through the closing event, ending art, all scenario-history pages, world
  epilogue, final credit group, and `Fin` screen. The full sampled run is under
  `captures/run/f2fc_credit_final_watch/`.
- `tools/send_blastem_keys.py --send-event` previously built both direct events
  as `KeyPress` objects and only changed the numeric type for release. It now
  emits the real Xlib `KeyRelease` class, avoiding stuck direction/confirm
  input after remote-focus changes. The helper also names the BlastEm `F7`
  binding as `pause` for diagnosis.
- The battle-command detector falsely accepted preparation/hire panels because
  both have a broad blue lower area. Real battle status bars measured about
  48% blue in the stable crop, while the observed hire panel measured about
  52%; the detector now accepts `45%..50.5%` and has a regression test for the
  preparation shape. Scenario 27 still requires three confirmations after the
  scenario map before navigating the preparation menu; a fixed two-confirm
  batch enters soldier hire and must not be used.

### Battle Magic And Summon List Font (2026-07-15)

- The `FFFF`-terminated records at `0x082BFE..0x082D1E` are used by shared
  acquisition/system-message paths, but they do not draw the in-battle magic
  selection list. Blank-record probes left that list Japanese, so do not repeat
  the direct-string-only approach.
- Renderer `0x021686` reads 31 per-entry glyph counts from `0x09B0F4`, sums
  them to find each entry, and draws a dedicated contiguous font run beginning
  at glyph `0x03C0` (ROM `0x04F000`). The first 23 entries are magic and the
  last eight are summons. Each row can show at most six glyphs; the original
  run reserves 130 glyphs through `0x0441`.
- `patch_magic_list_names()` hash-validates both the original 31-byte length
  table and all 130 source glyphs, rewrites the length table, renders the
  localized names, and clears the unused tail. Tests enforce the six-glyph row
  limit and total capacity.
- Magic terminology follows the referenced Langrisser 2 magic page, with
  spaces removed where the fixed-width game list requires it: `매직애로우`,
  `블래스트`, `파이어볼`, `블리져드`, `턴언데드`, `포스힐1`, `슬립`,
  `뮤트`, `프로텍션`, `어택`, `텔레포트`, `일루전`, `레지스트`, and `참`.
  The direct acquisition strings use the same names.
- Production checksum `8AD6` live-verifies `매직애로우` in Hein's battle
  magic list and preserves the bottom status labels `헤인/워록` in
  `captures/run/8ad6_s01_magic_namu_names.png`.

### Relocated Epilogues With Word Spacing (2026-07-15)

- The former no-space epilogue text was a conservative fixed-capacity choice,
  not a proven text-window restriction. All 90 Korean character and world
  records now use normal word spacing and are relocated consecutively from
  `0x2C0000`; the last record starts at `0x2CA54E`.
- `patch_relocated_epilogue_dialogue_records()` validates each Japanese source
  SHA-256, original capacity, name controls, page-break count, and individual
  pointer before writing. It rejects occupied relocation storage and changed
  working pointers. Tests also enforce unique increasing pointers and the
  three-line/24-cell window limit.
- The probe builder and static inventory/render tools now follow each record's
  pointer reference. This keeps Japanese rendering on the original addresses
  and Korean rendering on the relocated records. The direct inventory remains
  at 783 classified candidates with zero unclassified entries.
- Automated Korean spacing was manually reviewed. Corrections include compound
  nouns such as `근위기사`, `기사단장`, `제국군`, `마왕`, `마검`, and broken
  phrase/page boundaries. Production checksum `E6F4` plus the Scenario 27
  ending/slot 15 probe produced checksum `BE4C` and completed the entire route
  through `Fin`; evidence is `captures/run/be4c_epilogue_watch/001.png` through
  `340.png`.
- Live frame 270 showed that `{0001}일행` becomes `엘윈일행`. All eight dynamic
  name occurrences were changed to `{0001} 일행` and a regression assertion
  now rejects the joined form. Corrected production checksum is `EA22`; repeat
  the final combined-probe playback before treating this exact wording as live
  verified.
- Global XTest was unreliable in the current remote/focus state, while direct
  window events via `tools/send_blastem_keys.py --send-event` worked. Unchanged
  frames during automation should be diagnosed as input delivery first.
- The corrected production checksum `EA22`, Scenario probe `3590`, and combined
  checksum `C176` exposed a false probe assumption: the first Elwin combat left
  AT/DF 0 Bernhardt at HP 1. `captures/run/c176_probe_failure_current.png` is
  the evidence; `captures/run/c176_epilogue_watch/` was aborted after 133 frames
  and is not epilogue evidence. A second isolated-save experiment raised Elwin
  from AT 23 to AT 64, but the combat cap still left Bernhardt at HP 1 in
  `captures/run/c176_at64_second_failure_current.png`; its 150-frame watch
  directory is also invalid as epilogue evidence. Do not repeat AT boosting.
  Save state at the command menu, then load and retry with different pre-attack
  delays until the damage roll reaches 10.
- Automated BlastEm configs remove host gamepad bindings but retain keyboard
  mappings used by direct X events. This prevents an Xbox controller used in
  another game from steering the localization test emulator.
- A final `EA22` / `3590` / `C176` retry saved state at Elwin's command menu,
  then rolled ten damage and defeated Bernhardt on the first attack without a
  reload. The stock route completed through credits and `Fin`. Frame 216 in
  `captures/run/c176_corrected_epilogue_watch/` renders
  `어둠의 대결은 엘윈 일행의` with the corrected space; frames 216-244 cover
  all pages of relocated world record 86, frame 280 shows
  `한국어화 hsp1324`, and frame 288 reaches `Fin`. The stable `Fin` screen was
  captured through frame 359. This supersedes the two failed HP-1 attempts as
  the authoritative corrected-spacing live run.

### Event Inventory Text Classification (2026-07-16)

- The event inventory's only two byte-identical candidates were already proven
  non-dialogue structures: Scenario 7 `0x18F610` (13 words including `FFFF`)
  and Scenario 25 `0x1B0518` (17 words including `FFFF`). Their source refs are
  `0x18F358` and `0x1B03E6`. Do not translate or overwrite either record.
- `tools/jp_event_inventory.py` now recognizes those records only when their
  complete original token streams match. A changed stream raises an error
  instead of silently reusing the exclusion.
- Raw pointer-candidate counts remain available for ROM-analysis stability,
  while the report separately counts real text. The current result is 2,966 of
  2,966 logical text records and 3,565 of 3,565 physical text pages modified;
  Scenarios 7 and 25 each list one structured non-text exclusion and now report
  `all modified` instead of the misleading partial status.
- Production build checksum remains `EA22`. The full 163-test suite and direct
  inventory (`783 candidates; 0 unclassified`) pass without launching BlastEm.
- `tests/test_translation_target_residue.py` scans 4,511 output strings across
  event/ending/epilogue dialogue, shared resources, global names, UI patches,
  and credits. It rejects Japanese kana/kanji and the Unicode replacement
  character while deliberately excluding analysis-only source quotations.
