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

Last verified build during this handoff:

```text
checksum: B572
```

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
python3 tools/run_blastem_sequence.py shop-buy-sell
python3 tools/run_blastem_sequence.py arrange
python3 tools/run_blastem_sequence.py deploy-dialogue
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
- Scenario 1 description and the first dialogue are readable in Korean.
- Scenario condition labels show Korean:
  - `승리조건`
  - `패배조건`
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
- Shop sell-title tile loader `0xA181C` has identified title slots for the
  direct token stream at `0xA17B8`; the current build writes the visible slots as
  `아이템판매` without changing the token stream.
- Name entry screen currently defaults to `엘윈`, and it is a useful probe for
  seeing which Japanese byte/glyph slots now render as Korean.

## Known Remaining Problems

- Commander arrangement route menu still has Japanese on two rows:
  - `移動順変更`
  - `自動배치`
  - Rows already working: `지휘관배치`, `적군보기`, `출격`.
- Shop purchase/possession title is not fully solved. Do not restore the old
  `0xA17A4` token-shortening hack: it only hid the Japanese prefix and produced
  incomplete titles such as `소지`. The purchase script near `0xA177E` contains
  an `FFF9`-controlled substream; treating the following words as plain glyph IDs
  can blank/freeze the shop entry path. The sell path is safer: `0xA17B8` maps
  tokens directly to tile blocks and `0xA181C` supplies the glyph slots.
- Some route/menu titles still show English/Japanese, such as `SCENARIO 1`.
- Only Scenario 1 gameplay path has been heavily tested. The script contains
  broader item/class/scenario patches, but many later screens remain unverified.
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

Current: the sell-side script at `0xA181C` is safer and has been patched only at
the slots referenced by `0xA17B8` to prepare `아이템판매`. The purchase title
still needs its correct tile/glyph source isolated.

### Name Entry Default

Tried: patch default hero name to Korean through byte-string/default buffer
paths.

Result: visible behavior was inconsistent. Japanese name entry and later game
state do not use one simple string path. Some attempts showed Korean in one
place but caused black screen/reset after confirming the name.

Conclusion: do not spend time on the name-entry grid unless it becomes a real
gameplay blocker. Current test flow can start the game without solving the whole
name-entry alphabet screen.

### Arrangement Route Menu As Linear Grid

Tried: treat the commander arrangement route menu as five rows of five 16x16
glyph slots and overwrite a continuous range near `0xA2B6E`.

Result: wrong. It scrambled rows into combinations like `관배치순서`, while
`移動順変更` still remained. The menu mixes direct strings, sprite/tile paths,
and reused out-of-order fragments.

Conclusion: do not patch that menu as a simple continuous grid. The remaining
`移動順変更` and `自動...` rows need VRAM/sprite/tile-resource tracing.

2026-07-10 follow-up: on build `BC63`, the remaining visible Japanese came from
VRAM plane C tile IDs:

- `移動順変更`: tile IDs `5A0-5B3`;
- `自動` prefix: tile IDs `5B4-5B7`;
- the menu window nametable starts at VRAM plane C around `0xC000`.

Searching raw ROM bytes and the `0x0B0000` 4-byte graphics resource table did
not find these tile bytes, so the source is likely another compressed/tile path.

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

Conclusion: preserve `0xA1716` through `DIRECT_PREFIX_STRING_PATCHES` as
`소지불가`. In build checksum `8034`, the first-item purchase popup shows
`단검 소지` instead of `단검  입`.

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

- Commander arrangement rows `移動順変更` and `自動...`: remaining Japanese likely
  comes from sprite/tile-resource paths or a different direct-string ownership
  than the rows already patched.
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

Continue with the remaining route/arrangement menu labels. Reproduce the
commander arrangement screen:

```bash
python3 tools/run_blastem_sequence.py arrange
python3 tools/capture_blastem_window.py captures/run/arrange_current.png
```

Known remaining Japanese/English in this path includes `SCENARIO 1` and some
arrangement rows such as `移動順変更` / `自動配置`. Do not patch these as one
continuous grid; earlier attempts scrambled the menu because rows are sourced
from mixed string/tile paths.
