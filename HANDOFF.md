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
  `로얄호스` on the Scenario 1 path. The shop uses compact `ITEM`, `WPN`,
  `ARMOR`, and the then-current `소지G` label to stay within the safe one-byte
  font slots.
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
python3 tools/capture_blastem_window.py captures/run/example.png
python3 tools/send_blastem_keys.py c:0.8
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
syllable. To preserve the exact Scenario 1 class names, compact familiar UI
labels use `WPN`, `ARMOR`, and `NPC`. Later-scenario classes outside
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
- The baseline inventory contains 2,968 candidate pages. The current build
  differs from the Japanese ROM at 272: Scenario 1 is 107/121, Scenario 2 is
  91/110, Scenario 3 is 74/89, and Scenarios 4-31 are 0 modified pages.
- A modified page is not automatically complete Korean. Existing Scenario 2/3
  patches came from older partial work and must be reviewed for full-page text,
  natural translation, terminator safety, and live behavior.
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
- Current modified baselines are: conditions 1/32, scenario descriptions
  31/31, item names 38/38, item descriptions 37/37, magic names 23/23,
  mercenary battle names 15/15, and battle status messages 3/3.
- Scenario descriptions 2-31 came from legacy machine-translated material.
  Their 31/31 byte-change count is not a translation-quality result.
- Conditions remain the clearest missing shared resource: only Scenario 1 is
  patched. Summoned creature labels are class-table IDs and stay tracked in
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
- All 429 blocks decompress successfully with the builder's `0x9DFE` decoder.
  Their type-byte distribution is type 1: 2, type 2: 248, and type 3: 179;
  together they expand to 8,099,366 bytes.
- Only index 1 differs in the current build. It is the independently confirmed
  8,192-byte small UI font, relocated from `0x0B0A84` to `0x290000` with its
  decompressed glyph content changed. The other 428 owners remain deliberately
  unknown; successful decompression is not evidence that a resource is UI or text.
- Full pointers, types, decompressed sizes and SHA-256 values are in
  `localization/compressed_resources.json`; the summary is
  `docs/compressed_resource_inventory.md`. Tests enforce the table boundary,
  type counts, full decompression, and the single known relocation.
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

- `docs/name_entry_analysis.md` records direct 68000 references from the
  initialization and confirmation routines. Important targets are layout
  `0x0A38E0`, prompt `0x0A37BE`, initial tokens `0x0A38A6`, default buffer
  `0x0A3B0C`, confirmation glyphs `0x0A3BB0`, and confirmation layout
  `0x0A3BC0`.
- Code `0x02AC48..0x02AC4E` copies eight words from the default buffer. Five
  are editable name cells and three are padding. The builder now validates all
  eight source words and writes `엘윈` plus six spaces deterministically.
- `0x0A3864` and `0x0A3C5A` contain 32-entry English/number and Japanese
  selectable glyph resources. The existing patch changes only the default
  name; it is not a complete Korean input grid.
- Do not replace the Japanese selectable grid until cursor/page behavior is
  live-verified. No emulator was launched during this analysis.

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
