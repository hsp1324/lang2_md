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
checksum: 5B8A
```

The current source also builds checksum `5B8A`. It includes the Scenario 1
class-156 `ﾌﾟﾘｰｽﾄ` -> `프리스트` correction and localizes the shared unit-type
notices. A clean BlastEm run reached `TURN 2` and verified the support priest as
`사제 / 프리스트` with `NPC 유닛입니다`.

Build command:

```bash
python3 scripts/build_korean_jp_probe.py
```

Important recent local commits:

```text
d89ff79 Document English ROM attempt and JP pivot
3b06e43 Document handoff and stabilize shop knife text
c857911 Localize prep status labels
989ad65 Localize condition force labels
20ee84f Improve route menu and battle command patches
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
  glyphs use only original uppercase letter tiles `J/K/Q/U/Z`, visually
  confirmed as ordinary alphabet shapes. Do not extend this exception to `X`
  (`EXP`) or to lowercase/punctuation graphics.
  A future full Hangul name grid needs a screen-specific font-resource swap;
  it must not expand into shared ASCII/status tiles again.
- Automated regression: `test_byte_ui_patch_preserves_ascii_and_status_graphics`
  decompresses the original and patched byte-font resources and asserts every
  tile in `0x00..0xA4` except the five declared uppercase extensions, and every
  tile in `0xE0..0xFF`, is byte-identical. All byte UI Hangul mappings must
  remain within `0xA5..0xDF` or the explicit `J/K/Q/U/Z` set.
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
- Classification exposed 14 mostly untranslated full ending-dialogue pages at
  `0x09600E..0x096BD8` and 97 untranslated character-epilogue page chunks at
  `0x0896DE..0x095E52`. Short suffix patches inside an ending page do not make
  the full page translated.
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

The earlier default-name-only conclusion is superseded by the live-verified
84-syllable grid and confirmation hook documented below and in
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

### Korean Name Grid And Scenario 1 Turn-Event Regression (2026-07-12)

- The name-entry layout is the byte-tilemap at `0x0A38E0..0x0A3B0A`; its
  decoded size is 40x28. The selectable glyph list is `0x0A37E6` (95 words)
  and the selection-to-byte table is `0x0A3B3E` (95 bytes).
- The active grid exposes 84 unique Korean syllables at indexes 0..69,
  71..83, and 85. Keep index 70 reserved: the original `ヴ` handling is a
  special composite path. Keep index `0x54` as blank/delete and 86..94 blank.
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

### Scenario 19 Static Reviewed Dialogue (Live Verification Pending, 2026-07-12)

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
- Inventory is now 1,387/2,968 candidate records and 1,629/3,567 physical pages
  modified. Scenario 19 is intentionally not added to the live-complete list:
  the user requested background-only work, so BlastEm was not launched and no
  keyboard, mouse, or foreground window was touched. Resume with selector row
  19 and verify the briefing, preparation, automatic deployment, opening
  dialogue, conditional reinforcements, item pickups, departure paths, and
  first playable turn before promoting it to live complete.

### Scenario 20 Static Reviewed Dialogue (Live Verification Pending, 2026-07-12)

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
- Inventory is now 1,475/2,968 candidate records and 1,740/3,567 physical pages
  modified, with 91 passing tests. Scenario 20 remains live-pending because
  the user requested background-only work; BlastEm and all foreground input
  were left untouched. Resume with selector row 20 and verify the briefing,
  preparation, automatic deployment, golem/kraken event branches, Faias
  confrontations, victory dialogue, and the first controllable turn before
  marking this scenario live complete.

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
