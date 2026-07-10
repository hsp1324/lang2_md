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
checksum: A5DC
```

Build command:

```bash
python3 scripts/build_korean_jp_probe.py
```

Important recent local commits:

```text
c857911 Localize prep status labels
989ad65 Localize condition force labels
20ee84f Improve route menu and battle command patches
b4276bb Stabilize JP probe input and early UI patches
```

This handoff commit adds the current shop item fixes after `c857911`.

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
python3 tools/run_blastem_sequence.py arrange
python3 tools/run_blastem_sequence.py deploy-dialogue
python3 tools/capture_blastem_window.py captures/run/example.png
python3 tools/send_blastem_keys.py c:0.8
```

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
- Prep status panel bottom labels are fixed:
  - original `シキハイ` / 指揮範囲 -> `지휘범위`
  - original `シュウセイ` / 修正 -> `수정`
- Shop item purchase screen currently shows:
  - title `아이템구입`
  - first item `단검`
  - description `호신용 단검` and `AT+1`

## Known Remaining Problems

- Purchase popup after buying the first item still has bad text layout:
  - observed as `단검  입` with the item icon and a stray `입`.
  - This likely uses a separate fixed/prefix message path, not the same item
    list/description path.
- Commander arrangement route menu still has Japanese on two rows:
  - `移動順変更`
  - `自動배치`
  - Rows already working: `지휘관배치`, `적군보기`, `출격`.
- Some route/menu titles still show English/Japanese, such as `SCENARIO 1`.
- Only Scenario 1 gameplay path has been heavily tested. The script contains
  broader item/class/scenario patches, but many later screens remain unverified.
- Do not overwrite broad font slots casually. Previous attempts broke title
  screen text, name entry, command icons, and status labels.

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

Fix the purchase popup. Reproduce from the shop screen:

```bash
python3 tools/run_blastem_sequence.py shop
python3 tools/send_blastem_keys.py c:0.8
python3 tools/capture_blastem_window.py captures/run/purchase_popup.png
```

The popup currently appears after buying the first item and shows the item name
plus a stray `입`. Search for the original Japanese purchase message path and
patch it separately, preserving any prefix/control words.
