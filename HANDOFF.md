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

## Resume Dashboard (2026-07-20)

This section is the first stop after a Goal resume or interrupted session. Do
not restart completed investigations merely because their details also remain
in the chronological log below.

Current reproducible baseline:

```text
current production build checksum: 2CA4
latest targeted live-verified production checksum: 6C85
custom Hangul glyphs: 864 (0x7000..0x7360)
unit tests: 550 passing
direct-word candidates: 783 classified, 0 unclassified
pointer-referenced direct-byte candidates: 348 classified, 0 unclassified
conservative inline-byte candidates: 646 classified, 0 unclassified
declared UI patches: 131/132 byte-modified; NPC is intentionally unchanged
explicit UI verification gaps: 6
```

Completed and closed unless a later edit touches the same renderer, pointer,
glyph bank, or visible screen:

- all 31 scenario event resources are statically translated, and every scenario
  description, conditions, preparation, and opening path has current playback
  evidence recorded in `localization/runtime_verification.json`;
- the 90 outcome epilogues are relocated at `0x2C0000` and the 23 naturally
  spaced ending-visit records are relocated at `0x2D0000`; the combined visit
  renderer completed all 83 pages on checksum `F852`;
- the direct-string inventory has no unclassified candidate, so do not repeat a
  whole-ROM direct-string scan unless the builder changes reachable pointers;
- the Scenario 1 preparation, hire, equipment, shop, arrangement, battle menu,
  first turn, clear result, and save path have accepted evidence;
- complete name/class/mercenary lists, all 22 magic names, all eight summon
  names, representative class-change application, stock Magic Arrow, diagnostic
  Attack, and diagnostic Elemental application have accepted evidence at the
  levels recorded by their inventories. A diagnostic proof is not a natural
  ownership proof.
- the original complete-item secret shop list, all 37 Korean names and
  descriptions, prices, and visible icons are accepted. Current diagnostic
  checksum `C80E` has renderer-aware fingerprint
  `eb1d9aadc20f3a46a8ab3f3b1d7cb757619dbe28551f52d757cce6814027b19c`;
  decoded icon resource 391 remains byte-identical to the Japanese ROM.
- the equipment/shop UI gap is closed by Scenario 1 buy/sell and empty-slot
  equipment paths, Scenario 25's complete nine-commander equipment selector,
  Scenario 27's category and sell variants, and the accepted 37-item matrix.
- a 41st shop purchase with all 40 equipment slots occupied now shows the
  fixed Korean warning `아이템 구입 불가`; the original nine-cell message was
  `これ以上持てません`. The distinct item-award path now shows naturally
  spaced `아이템이 가득 찼습니다` / `하나를 버려주세요`, then renders the
  five-row `버릴 아이템` UI. Diagnostic `94DB` proves pages 1 and 9,
  cursor movement, confirmation, and stable return; a natural treasure/event
  trigger remains to be identified if one exists in normal play.
- compressed resource `391` is now owned as the stock item-icon payload from
  direct load call `0x025E62` (`0x8187` to VRAM `0x4000`), reducing unknown
  original compressed-resource ownership from 428 entries to 427.
- the conservative 32-bit pointer scan now classifies all 348 strict CP932/ASCII
  `FF` byte-string candidates. It found the separate illusion-unit class pointer
  at `0x05E5CA`, selected by the status instruction at `0x010420`; production relocates its
  `ｲﾘｭｰｼﾞｮﾝ` target as `일루전`. The reserved `ﾗﾝｸﾞﾘｯｻｰ/ｱﾙﾊｻﾞｰﾄﾞ` block at
  `0x0A3B9D` is an internal name-entry comparison, not visible UI. Full source
  bytes, references, and reviewed false positives are in
  `localization/direct_byte_string_candidates.json`.
- the independent inline scan classifies 646 conservative `FF`-terminated runs
  with zero unknowns. It proves the fixed 13-cell `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ` prompt at
  `0x01807E` and a separate 77-row hidden sound-test table at
  `0x05E040..0x05E50F`. Production preserves every sound ID, redirects only the
  label renderer, and has live evidence for entry, representative rows, the
  final row, wraparound, and exit.

Active work, in order:

1. Upgrade scenario `completion` and `branches_endings` cells that are still
   `pending` in `docs/runtime_verification_inventory.md`. `progressed` is useful
   continuity evidence but is not a page-by-page visual review.
2. Work only from the six explicit shared-UI gaps in
   `docs/ui_patch_surface_inventory.md`; the item-shop gap is closed.
3. Re-run a completed path only when a new patch shares its glyphs, pointers,
   tokens, compressed resource, or control flow, or when an automated regression
   fails. Record why the regression was necessary.
4. Keep editor work limited to fields with proven ROM/runtime ownership; current
   localization completion remains the priority.

Before new work, run `git status --short`, `git log --oneline -5`, and the focused
tests for the surface being changed. After a coherent unit, regenerate the
inventories, run the full suite, update this dashboard only if its counts or
priorities changed, then commit and push. Generated ROMs and captures remain
ignored; record their checksum and paths here or in the relevant inventory.

Closed all-item shop checkpoint:

- the original shop mode flag at `0xA6DC` selects two secret lists. List 32 has
  28 purchasable items; list 33 at pointer-table index 32 contains exact IDs
  `1..37`, including Langrisser and Alhazard. The diagnostic builder
  `tools/build_item_shop_probe_rom.py` changes only the list selector at
  `0x027B32` plus the checksum and therefore uses the original complete-item
  secret list rather than an invented inventory;
- checksum `3F14` reproduced the defect on page 2: the old relocated name list
  had 140 glyphs while `0x21C72` loaded only 64, and the description list had
  338 glyphs while `0x272C0` loaded only 192;
- production checksum `5993` keeps the compact rewritten name and description
  lists inside their loader windows. All 37 token streams
  are statically proven inside their loaded windows by
  `tests/test_item_shop_resources.py`;
- the previous 37-description list omitted Alhazard at ID 14, shifted the
  following descriptions, and ended with an unrelated Holy Rod line. ID 14 is
  restored, IDs 15..37 are realigned, and Gleipnir/Gjallarhorn/Amulet now match
  the Japanese effects. The runtime panel is 9 columns by four text rows plus
  one price row, not the earlier assumed 15 by three; the corrected layout no
  longer splits `AT+2` across rows;
- diagnostic checksum `D304` was captured as
  `captures/run/d304_item_shop_id01.png` through `id37.png`. All names,
  descriptions, numeric effects, prices, and visible icons were reviewed and
  accepted. Five-digit prices retain their final `0P`; it is present in the raw
  capture pixels even when the 320x240 preview makes it hard to read;
- a later full-shop replay exposed a gap in that checkpoint: tokens `64+` in
  names such as `그레이프니르` were interpreted through the icon bank because
  the stock `0x2000..0x3FFF` name window holds only 64 16x16 glyphs and item
  icons begin at `0x4000`. The old builder loaded all 84 names contiguously,
  so list and purchase-popup suffixes became icons even though static token
  bounds passed;
- production `2282` keeps slots `0..63` at `0x2000`, loads the 20 overflow
  glyphs into `0xB400..0xBDFF` after the 192-slot description bank, and patches
  the two hardcoded list renderers plus the popup stream builder to select the
  matching VRAM base. `0xE000` was rejected after GST inspection proved it is a
  plane/name-table region that gets overwritten with vertical-line data;
- historical free-price derivative `4C04` verifies the full last two shop pages and clean
  messages `그레이프니르를 구입함`, `걀라르호른을 구입함`,
  `아뮬렛을 구입함`, plus the low-slot regression `단검을 구입함` in
  `captures/run/2282_item35_list.png`, `_item35_popup.png`,
  `_item36_37_list.png`, `_item36_popup.png`, `_item37_popup.png`, and
  `_item01_popup_regression.png`;
- current diagnostic checksum `7E0B` has renderer-aware item-surface SHA-256
  `9e3372724e71c96a4dcff082fb9e3f67e843408c93d375f0a0bca16dcdda822b`.
  This fingerprint covers item names, descriptions, glyph lists, direct word
  names, prices, icons, and the glyph-load/list/popup renderer hooks and
  routines, so a later renderer regression now reopens the matrix;
- item icon resource 391 is loaded at `0x025E5A` to VRAM `0x4000`. Its first
  `37 * 0x80` decoded bytes and the ID-to-tile selector at
  `0x027B44..0x027B77` are byte-identical to the Japanese ROM. The exact matrix
  and checksum-bound acceptance are in `localization/item_shop_inventory.json`
  and `docs/item_shop_runtime_matrix.md`;
- `tools/capture_item_shop_inventory.py` derives artifact names from the
  current checksum, checks the real BlastEm 87-level palette, changes page
  before clamping to the first row, and uses one Up on the final two-row page.
  Do not restore the old Up-before-Right/four-Up logic. Attempting the Korean
  title/menu input sequence on original diagnostic checksum `3328` stopped at
  a black screen because the original timing differs; that failed capture is
  not acceptance evidence and need not be repeated for icon proof.
- BlastEm placement selects the widest active RandR output. Direct
  `--send-event` input only places the window and
  never requests `_NET_ACTIVE_WINDOW` or keyboard focus. While the user is
  gaming, do not run an XTest/click-window sequence because that path still
  requires focus by design.
- Windows currently reports the BlastEm outer window at twice the X11 logical
  dimensions because display scaling is 200%. The DWM path now derives that
  scale from both geometries, captures the physical client rectangle, and
  downsamples it to the canonical 320x240 frame without changing focus.
- `PrintWindow` can capture an occluded OpenGL window without focus, but partial
  redraws retain stale pixels from earlier screens, so it remains diagnostic-
  only. However, reliable DWM capture `3c46_s02_prep_verify_09.png` proved that
  the extra `렛` after preparation labels was also a real transition-dependent
  defect. The four rows are six cells wide, and their token stream at
  `0x09AA6C` used unloaded tile `0x05FC` for five trailing cells. That tile
  retained scenario-description VRAM even though `렛` (`0x7235`) is absent
  from the preparation glyph list. Production `38AB` replaces those five
  tokens with loaded blank tile `0x0540`; DWM capture
  `389a_s02_prep_verify_09.png` verifies all four rows without residue.
  `--print-window` is still never an automatic fallback or acceptance path.
- Automatic detector sequences cannot request foreground activation. A single
  manual capture may use `--allow-focus-steal` only after confirming that the
  user is not working in another application. Never add a per-frame activation
  flag back to `run_blastem_sequence.py`; it repeatedly calls Windows
  `SetForegroundWindow` and steals the user's active window.

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
checksum: E38B
```

The current source builds checksum `D8C1` and passes all 394 tests. It includes
all 31 scenarios' static event translations, the complete direct-name, credits,
90-record epilogue, and 23-record naturally spaced ending-visit resources, plus
the extended 8x8 commander-name font bank. Every scenario description,
condition screen, preparation surface, and opening path has current playback
evidence. Static translation and renderer probes do not prove every conditional
event branch; the generated runtime inventory and Resume Dashboard above state
the exact remaining work.

Build command:

```bash
python3 scripts/build_korean_jp_probe.py
```

Important recent local commits:

```text
6195d90 Relocate and verify ending visit dialogue
d7e9ebf Automate summon targeting and runtime probes
da0e8fe Automate magic targeting and result probes
a8ce09d Automate stable class change application probes
d172de2 Complete class change candidate screen matrix
bb3d52d Verify Aaron class change chain
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
  Japanese debug artifact at `0x082B78` renders as `面をしないだすー`; its
  table index and every reachable player growth value are now statically
  proven unable to select it, so it remains byte-identical rather than being
  assigned a guessed Korean sentence.
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
  prevents the renderer regression. The production-build regression
  `test_built_rom_installs_bottom_aligned_period_and_comma` also scans every
  available custom-glyph bank in the completed ROM and proves that both exact
  payloads were installed; it does not depend on their current glyph IDs.
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
  initially allocated the remaining glyphs across six map/preparation VRAM
  segments: `340..347`, `398..3AF`, `440..447`, `498..4AF`, `4D8..4EF`, and
  `5D8..5F3`. The final segment has since moved to `580..59B`; see the current
  Loren regression below. Resources 430 through 435 are appended to the relocated compressed
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

### Current EA22 Scenario 1 UI Regression (2026-07-16)

- A fresh isolated-runtime playback reached Elwin's first command menu after
  12 post-deployment confirmations. `captures/run/ea22_s01_command_magic_fresh.png`
  verifies `엘윈/파이터` and `이동/공격/치료/명령` with intact AT/DF/status
  graphics.
- The Start-menu regression covers `저장`, `불러오기`, `승리조건`, and
  `게임설정`. Evidence is `captures/run/ea22_s01_save_prompt.png`,
  `ea22_s01_load_menu.png`, `ea22_s01_conditions.png`, and
  `ea22_s01_game_settings_final.png`. The load slots consistently render
  `손상된 데이터`; the conditions use `발드`, and all four settings rows are
  Korean. Large `YES/NO` and compact `AT/DF/LV/MP/HP` remain intentional
  conventional English.
- Hein was selected at his initial Scenario 1 position rather than inferred
  from an older checksum. `captures/run/ea22_s01_magic_retry3_hein_menu.png`
  verifies `헤인/워록` and `이동/공격/마법/치료/명령`; selecting the third row
  opens `captures/run/ea22_s01_magic_current.png`, which renders
  `매직애로우` and page `1/12` on production checksum `EA22`.
- Direct X events shorter than one emulated input sample can be ignored, while
  a 0.05-second held direction can repeat across several map cells. For menu
  verification use one `down@0.02` event, wait for a capture, then send the next
  event. This timing issue caused one discarded attack-selection attempt; it
  did not expose a ROM or translation regression.
- The battle-result decoration fix remains guarded in the current source by
  `test_byte_ui_patch_preserves_ascii_and_status_graphics`, including an exact
  byte comparison of tile `0xB0`. The direct live battle-screen evidence is
  checksum `80E6` capture
  `captures/run/80e6_battle_result_decoration_fixed.png`; do not relabel that
  older capture as an `EA22` live battle-screen check. A later
  current-production-derived probe capture is recorded below.

### REV00 Debug Magic Inventory And Revision-Specific Probes (2026-07-16)

- The project Japanese source is REV00: MD5
  `9be7bdb4892eb716ea80bb1de4d660e4`, SHA-1
  `4bbc2502784a61eedf45eca5303dc68062964ff4`, CRC32 `7F891DFC`.
  Public Game Genie pages mix REV00, REV01, and later-revision codes. A code
  decoding to an in-range address does not prove revision compatibility.
- Published REV01 `All Spells` code `AJKA-EA7E` decodes to
  `0x0212A4:6002`. Applying it alone to REV00 checksum `8456`, or together
  with `RGJA-Y6X2` in checksum `21B3`, resets when Hein opens the magic list.
  `RGJA-Y6X2` alone (checksum `3894`) opens only Hein's normal one-spell list.
  `RGJA-Y6ZG` did not add a summon command. These are failed revision probes;
  do not repeat them or promote them to build presets.
- `tools/game_genie.py` retains the verified Genesis decoder, including the
  published Sonic example `SCRA-BJX0 -> 0x009C76:5478`.
  `tools/build_game_genie_probe_rom.py` requires explicit `--code` values,
  validates that localization did not already alter each source word, prints
  the source SHA-1, and writes only an ignored probe ROM. It deliberately has
  no named Langrisser presets because the names implied unsupported REV00
  compatibility.
- On an empty Scenario 1 map cell, the original in-game debug sequence
  `Up, Left, Up, Right, A, Left, Down, B, Down, Right, A, B, Down, Right, A`
  activated on production `EA22`. It permits enemy control and exposes all
  spells only on units that already own a magic command. Hein's list was
  captured without a reset across four pages:
  `ea22_debug_all_magic_page1_retry.png`, `ea22_debug_magic_page2.png`,
  `ea22_debug_magic_page3.png`, and `ea22_debug_magic_page4.png` under
  `captures/run/`. The 22 rows are, in order:
  `매직애로우/블래스트/썬더/파이어볼/메테오/블리져드`,
  `토네이도/턴언데드/어스퀘이크/힐1/힐2/포스힐1`,
  `포스힐2/슬립/뮤트/프로텍션/어택/존`, and
  `텔레포트/일루전/레지스트/참`. All were Korean and fit their rows.
  Right changes list pages; Down only changes the selected row, so
  `ea22_debug_magic_scroll_sheet.png` is a discarded selection-cycle probe.
- The same debug mode proved that class ID is not the magic/summon ability
  owner. Scenario 1 record 11 changed from Fighter to Summoner and displayed
  `서머너`, but still had only `이동/공격/치료/명령`. A second probe changed
  record 10 Laird from Magic Knight to Summoner; live capture
  `captures/run/ea13_laird_command.png` again showed `레아드/서머너` with
  only those four commands. Class-only editing must not be described as
  granting class abilities.
- Command builder `0x020CB0` tests bit 0 of the runtime unit long at `+0x50`
  before adding command ID 2 (magic), then bit 17 of the same long before
  adding command ID 3 (summon). The mapping from Scenario fixed-record bytes
  to this runtime ownership long is not yet proven, so it is not exposed by
  the editor.
- An ignored checksum `D177` probe changed only the conditional branch at
  `0x020DFA` from `671C` to `4E71`, forcing the summon command to be offered
  without changing production `EA22`. After activating the original in-game
  debug sequence, Liana's command menu displayed both `마법` and `소환` in
  `captures/run/d177_debug_liana_command.png`. The debug summon path populates
  all eight IDs. `d177_debug_summon_page1.png` live-verifies
  `엘리멘탈/프레이야/화이트드래곤/발키리/슬레이프니르/펜릴`, and
  `d177_debug_summon_page2.png` verifies `요르문간드/형님`, with no Japanese
  residue, clipping, reset, or freeze. This completes the live name-list
  rendering check but does not justify shipping the forced-command branch.

### Current EA22 Turn 1 And Scenario 27 Preparation Regression (2026-07-16)

- A fresh production `EA22` `first-turn-dialogue` run ended the first player
  turn and was advanced one direct C event at a time. Captures
  `captures/run/ea22_first_turn_step_01.png` through `_73.png` cover the
  resident warning, imperial withdrawal, Leon/Laird orders, Liana/Leon/Bald
  exchange, enemy movement, and the following Hein/Elwin event. The route
  reached `TURN 2` without reset, freeze, Japanese residue, or damaged dynamic
  names; the stable map is `ea22_s01_turn2_map.png`. Some intermediate frames
  were captured while text was still typing and are not authoritative wording
  samples. The first enemy phase did not enter the battle presentation.
- Production `EA22` also entered Scenario 27 through the built-in selector.
  `ea22_s27_roster_sheet.png` verifies the five preparation commanders and
  current classes: `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`,
  `아론/파이터`, and `키스/호크나이트`. It also preserves `소지금` and all
  four main preparation labels.
- The Scenario 27 equipment path cycles through `무기`, `방어구`, and
  `장신구` without the former `WPN` abbreviation or corrupt leading glyph.
  Evidence is `ea22_s27_equipment_current2.png`,
  `ea22_s27_equipment_weapon_list.png`, and
  `ea22_s27_equipment_accessory.png`.
- The same current run bought and sold daggers. `ea22_s27_shop_buy_list.png`
  shows `아이템 구입`, `단검`, `호신용 단검`, `AT+1`, and `50P` with no stray
  `4`; `ea22_s27_shop_buy_message.png` shows `단검을 구입함`.
  `ea22_s27_shop_sell_list.png` and `ea22_s27_shop_sell_message2.png` verify
  `아이템 판매`, the real `40P` sale value, and `단검을 판매함`.
- Preparation navigation has two focus levels. Down while the left commander
  list owns focus changes the selected commander and does not move the main
  command cursor. Press Right once to transfer focus to the right-hand list,
  then use Down. The hire submenu exits through its explicit `END` row; B on
  an empty hire list does not return to the main preparation commands. The
  equipment flow completes after confirming all three slots and then returns
  to the main command list. These observed rules explain the discarded
  unchanged-frame navigation probes and should be reused by automation.
- Rebuilding `tools/build_scenario27_ending_probe_rom.py` directly from
  production `EA22` produced checksum `3590`; its only gameplay changes are
  the documented Scenario 27 Bernhardt placement/stat/mercenary fields. The
  stock battle renderer was entered through the normal Elwin attack path.
  `captures/run/3590_battle_live_078.png` and `_083.png` verify the current
  localization code in the battle presentation: portrait names, numeric stats,
  `-AT-`, `-DF-`, and the original formation/modifier decoration are intact.
  The third center-row mark is original graphic decoration, not untranslated
  Japanese text. It must remain byte-identical rather than be overwritten with
  another Hangul glyph.
- Runtime status is now separated from static translation coverage in
  `localization/runtime_verification.json`. The generated
  `docs/runtime_verification_inventory.md` tracks eight live surfaces for all
  31 scenarios and keeps unreviewed scenarios explicitly pending. Run
  `python3 tools/runtime_verification_inventory.py` after accepting new live
  evidence; `tests/test_runtime_verification_inventory.py` rejects missing,
  reordered, or invalid scenario/status entries and stale generated Markdown.

### Current EA22 Scenario 2 Entry Regression (2026-07-16)

- The built-in selector entered Scenario 2 on production `EA22`.
  `captures/run/ea22_s02_brief_01.png` through `_12.png` show the Korean
  `시나리오 2 / 여행의 시작` briefing pages; accepted stable samples contain
  no Japanese residue or broken dynamic names. `ea22_s02_brief_13.png` reaches
  preparation and displays `엘윈/헤인/스코트` with intact class/status UI.
- Continuing through auto-deployment opened the Korean event at
  `ea22_s02_deploy_banner.png`. The command detector advanced 63 confirmations
  and reached `ea22_s02_command_ready.png` without reset or freeze. This proves
  current-build progression, not individual visual review of all 63
  intermediate pages; record it as `progressed_current`, not
  `verified_current`.
- `captures/run/ea22_s02_conditions.png` verifies the live condition layout:
  victory is `리아나 북쪽 도착` or `적 전멸`; defeat is `리아나 사망` or
  `주인공 사망`. The four rows fit without overlap or Japanese residue.
- A fixed 32-confirm briefing loop continued after the preparation transition
  and hired six Soldiers in the isolated `load-screen` runtime SRAM. No ROM or
  source data changed. Future cross-scenario automation must detect the
  preparation panel and stop confirmations before navigating it; do not use a
  fixed briefing count across scenarios.

### Current EA22 Scenario 3 Entry Regression (2026-07-16)

- `tools/run_blastem_sequence.py detect-prep` now recognizes the stable
  preparation layout from its left roster, right command panel, gold divider,
  and bottom-left money panel. It checks before every C press, so a detected
  preparation frame cannot spill into commander selection or hiring. Synthetic
  tests reject briefing, battle, and condition-like layouts. The optional
  `--capture-prefix` retains every detector frame and works for both
  `detect-prep` and `detect-command`.
- Production `EA22` Scenario 3 stopped at preparation after 13 confirmations.
  `captures/run/ea22_s03_brief_live_01.png` through `_13.png` were individually
  reviewed: `시나리오 3 / 조름의 반격`, the complete Korean description, and
  the `엘윈/파이터` preparation panel are intact with no Japanese residue.
- Automatic deployment reached `ea22_s03_deploy_banner.png`. All 24 opening
  detector frames (`ea22_s03_opening_live_01.png` through `_24.png`) were
  reviewed through the Korean Liana escort choice and the full
  `이동/공격/치료/명령` panel. Names and classes in dialogue, the status bar,
  and the selected commander panel remained intact.
- `ea22_s03_conditions.png` verifies `적 전멸` as the victory condition and
  `리아나 사망` / `주인공 사망` as defeat conditions. Ending the first turn
  entered `ENEMY PHASE`; eight separately captured confirmations showed the
  Liana-position prompt and escort choice and returned to a valid command panel
  (`ea22_s03_turn1_live_01.png` through `_08.png`) without reset or freeze.
  This is current first-turn progression evidence, not a scenario clear or
  complete later-turn review.

### Current F03A Scenario 4 Entry Regression (2026-07-16)

- Live Scenario 4 review exposed inconsistent output terminology. Only actual
  Korean target resources were changed: `레이가드` is now consistently
  `레이갈드`, and `흑룡마도단` is now `흑룡마도사단`. This covers Scenario
  4/15/16/26 descriptions and five later event lines; English/reference data
  was intentionally left unchanged. The resulting production checksum is
  `F03A` with the same 851 custom glyphs.
- The new build re-entered Scenario 4 and `detect-prep` stopped after 14
  confirmations. `f03a_s04_brief_live_01.png` through `_14.png` verify the
  complete `빛의 신전` description, corrected `레이갈드 제국의
  흑룡마도사단`, and intact preparation UI.
- Automatic deployment and all 26 opening captures reached a valid Elwin
  command panel. `f03a_s04_conditions.png` displays victory `모건 격파` and
  defeat `신관 전멸` / `리아나/주인공 사망` without clipping or residue.
- The first turn entered `ENEMY PHASE` and returned to the command panel after
  93 captured confirmations. Text-bearing frames were separately selected and
  reviewed, including Morgan/priest/imperial-commander dialogue and the Korean
  Dark Elf combat tutorial. No reset, freeze, broken name, class, AT, or DF was
  observed. This does not claim later-turn or scenario-clear coverage.

### Current F03A Scenario 5 Entry Regression (2026-07-16)

- `detect-prep` stopped after ten confirmations. The complete `짐승의 포효`
  briefing and preparation transition are in
  `f03a_s05_brief_live_01.png` through `_10.png`; no Japanese residue or broken
  glyph appeared.
- Commander selection was entered explicitly rather than inferred from the
  roster list. `f03a_s05_commander_01.png` through `_05.png` verify
  `엘윈/파이터`, `헤인/워록`, `스코트/나이트`, `리아나/클레릭`, and
  `쉐리/파이터`. Sherry's hire page displays `솔저` at
  `f03a_s05_sherry_hire.png`. Attempts to reuse `B, Up, C` for the other hire
  pages returned to the preparation menu instead; those captures are rejected
  and the remaining hire lists are still pending.
- Automatic deployment and all 16 opening frames reached a valid Elwin command
  panel. `f03a_s05_conditions.png` verifies victory `20턴 내 적 전멸` or
  `20턴 내 북쪽 도착`, with defeat `제한 턴 초과` or `주인공 사망`.
- First-turn progression returned to the command panel after 36 captured
  confirmations. The text-bearing frames, including Morgan and imperial
  commander dialogue, were reviewed against Scenario 5 source records. No
  reset, freeze, broken name, class, AT, or DF was observed; later turns and
  completion remain pending.

### Current F03A Scenario 6 Entry Regression (2026-07-16)

- `detect-prep` stopped after 14 confirmations. All retained frames verify the
  Korean `시나리오 6 / 노병 아론` briefing and the full description through
  preparation. Commander selection separately verifies `엘윈/파이터`,
  `헤인/워록`, `스코트/나이트`, `리아나/클레릭`, and `쉐리/파이터` in
  `f03a_s06_commander_01.png` through `_05.png`.
- Arrangement, automatic deployment, and all 16 opening confirmations were
  reviewed through a valid Elwin command panel. Dialogue names and bottom
  status text for Morgan, Aaron, Sherry, and imperial commanders remained
  intact. `f03a_s06_conditions.png` verifies victory `적 격파` and defeat
  `시민 전멸` / `주인공 사망` without clipping or Japanese residue.
- The first-turn probe deliberately ended the turn without moving any allied
  unit. It reviewed Aaron, resident, Morgan, imperial commander, and Hein
  dialogue around enemy movement. The live battle renderer in
  `f03a_s06_turn1_live_10.png` and `_11.png` displays `바바리안/솔저`,
  `-AT-/-DF-`, and intact formation/status graphics on production F03A.
- Because the civilians were left undefended, they were wiped out and the
  game correctly displayed `GAME OVER` at `f03a_s06_turn1_cont_03.png` before
  returning to the title sequence. This is an expected `시민 전멸` loss, not
  the old dialogue-triggered reset defect. Scenario completion and later-turn
  event coverage remain pending.
- The original command-menu detector falsely accepted a map frame with blue
  roofs and a unit-selection highlight. It now also requires at least 30% of
  the command menu's stable left interior to contain dark-blue panel pixels.
  It also detects the centered `GAME OVER` panel and exits with status 2 before
  confirmations can spill through the title sequence. Synthetic regression
  tests and the exact F03A true/false frames prove the full menu remains
  accepted while the Scenario 6 false positive is rejected.

### Current EF65 Scenario 7 Entry And Ginam Name Fix (2026-07-16)

- The first F03A live pass reviewed all 16 `깨어나는 망자` briefing frames,
  five commander/class rows, the arrangement menu, all 20 opening frames, and
  the condition panel. It exposed a real localization defect: source dialogue
  used the fixed speaker record at `0x0974D2`, whose old capacity-era target
  was intentionally approximated as `기잠`, while the byte name table and
  victory condition correctly used `기남`.
- The expanded glyph banks already contained `남`. Both the stable direct
  patch and its legacy idempotent mirror now use canonical `기남`; custom
  glyph count and IDs remain unchanged at 851 (`0x7000..0x7353`). The rebuilt
  production checksum is `EF65`. Generated direct inventory now reports
  `기남` at `0x0974D2`, with 783 candidates and zero unclassified records.
- A fresh EF65 replay repeated all 16 briefing and 20 opening confirmations.
  `ef65_s07_opening_live_11.png` and `_17.png` show `기남` and `기남님`, and
  `ef65_s07_conditions.png` shows victory `기남 격파` with defeat
  `시민 전멸` / `주인공 사망`. No glyph allocation moved.
- The no-action first-turn path captured 100 confirmations and then completed
  the remaining enemy movement to `TURN 2`. Text-bearing frames cover resident,
  Elwin, Ginam, Scott, Hein, Liana, and imperial-commander dialogue. Current
  battle frames `_62.._65` and `_83.._86` show `슬라임/주민`, `-AT-/-DF-`,
  and intact formation/status graphics. The command detector timed out because
  the Turn 2 cursor did not land on an allied unit; the game itself neither
  reset nor froze. Later turns and scenario completion remain pending.

### Current EF65 Scenario 8 Entry Regression (2026-07-16)

- All 16 `하늘의 다리` briefing confirmations were reviewed through the
  preparation transition. Commander selection cycles five current units and
  verifies `엘윈/파이터`, `헤인/워록`, `스코트/파이터`,
  `리아나/클레릭`, and `쉐리/파이터`. Keith appears in the scenario event
  but is not yet a selectable preparation commander.
- All 17 opening frames were reviewed through a valid Elwin command menu.
  Keith, Sherry, Hein, Kramer, and imperial-commander labels are intact.
  `ef65_s08_conditions.png` verifies victory `12턴 내 크레이머 격파` and
  defeat `제한 턴 초과` / `주인공 사망` without clipping or residue.
- The first detector pass falsely accepted a water-heavy map frame with a unit
  selection rectangle. The command detector now requires more than 6.5% white
  label pixels inside its stable panel crop in addition to the existing blue
  panel/status constraints. Exact captures prove the real Scenario 8 command
  menu remains accepted while `ef65_s08_turn1_live_08.png` and the earlier
  Scenario 6 false frame are rejected.
- Continuing the same no-action path reached `TURN 2`, then reviewed the
  Sherry/Scott/Keith/Aaron anti-air tutorial and returned to Elwin's command
  menu at `ef65_s08_turn1_cont_11.png`. No reset, freeze, Japanese residue, or
  damaged dynamic name/class appeared. This path did not enter the battle
  presentation, so Scenario 8 battle UI remains probe-only; later turns and
  completion remain pending.

### Current D15E Scenario 9 Entry And Dialogue Fix (2026-07-16)

- All 14 `칼자스 성 공방전` briefing confirmations, five commander/class
  rows, arrangement, and all 30 current opening confirmations were reviewed.
  Commander selection shows `엘윈/파이터`, `헤인/워록`, `스코트/파이터`,
  `리아나/클레릭`, and `쉐리/파이터` without damaged dynamic glyphs.
- The first EF65 opening pass exposed a real mistranslation at continuation
  record `0x193834`: `하지만 레온님이 없으면 모른다` inverted the source
  meaning. It now reads `레온님이 없는 지금, 망설일 수 없다.` before the
  Blue Dragon Knights declaration. No glyph was added or reassigned; the
  rebuilt production checksum is `D15E`, still using 851 custom glyphs
  (`0x7000..0x7353`). `d15e_s09_opening_live_28.png` verifies the corrected
  sentence in the emulator.
- `d15e_s09_conditions.png` verifies victory `레아드 격파` and defeat
  `NPC 전멸` / `주인공 사망`. The no-action first-turn path then reviewed 117
  confirmations, reinforcement movement, and the Sherry/Scott/Keith tutorial
  before returning to Elwin's command menu.
- Current battle frames around `_33.._35` and `_77.._80` show the
  `그리폰/파이터` and soldier presentations with intact names, classes,
  `-AT-/-DF-`, counts, and status graphics. The scenario did not reset or
  freeze. Later turns, scenario completion, and branch/ending coverage remain
  pending.

### Current FD90 Scenario 10 Entry And Source Corrections (2026-07-16)

- All 16 `랄강의 수호자` briefing confirmations were reviewed through the
  preparation transition. The visible title and destination previously used
  `랄 강`; the generated resource inventory had been edited first, but live
  replay proved that the production builder reads
  `scripts/legacy/build_korean_complete_wip.py`. Both that authoritative
  source, the Scenario 11 override, and `shared_word_resources.json` now use
  canonical `랄강`. `fd90_s10_brief_live_01.png` and `_14.png` prove the
  corrected no-space form in the final build.
- The five selectable rows show `엘윈/파이터`, `헤인/워록`,
  `쉐리/파이터`, `아론/파이터`, and `키스/호크나이트`. Arrangement and
  automatic deployment were also reviewed. These captures were made before
  the scenario-local dialogue edits, but custom glyph IDs remained unchanged
  at 851 (`0x7000..0x7353`).
- The old 0.9-second detector interval captured partially drawn dialogue.
  `run_blastem_sequence.py` now accepts `--confirmation-delay`; the final
  opening used 2.2 seconds and retained every completed page through the
  command menu. This exposed `0x195DF6` as a real mistranslation: the old
  `겁쟁이인가? 힘으로도 건널 수 있어.` did not match the source's bandit
  encounter. `fd90_s10_opening_slow_10.png` verifies the corrected, naturally
  wrapped `산적인가? 저 정도로는 / 못 막아. 가자!`.
- A pre-fix no-action turn also displayed `0x196162` as
  `불평은 무시해도 좋다!`, unrelated to source `These scum will not get past
  us`. Records `0x19611A..0x196218` were corrected against the source mapping
  and locked by address tests. Those alternate pages did not retrigger in the
  final FD90 path, so their final live reproduction is still pending rather
  than being claimed complete.
- `fd90_s10_conditions.png` verifies victory `레스터 격파` and defeat
  `주인공 사망`. The final first-turn path reviewed the pirate dialogue and
  all enemy movement, reached `TURN 2`, and returned to Elwin's command menu
  without reset or freeze. No battle presentation occurred, so battle UI
  remains covered only by the shared probe. Later turns, completion, and
  branch/ending coverage remain pending. Production checksum is `FD90`.

### Current FD90 Scenario 11 Entry And Editor Records (2026-07-16)

- All ten `불길 속에서` briefing confirmations were reviewed through the
  preparation transition. The original pass incorrectly stopped after the five
  rows visible on the first page. A F0E3 revisit followed the right-side `>>`
  control and also verified `제시카/크루세이더`; all six selectable rows are
  intact. Arrangement and all 37 slow opening confirmations reached a valid
  Elwin command menu without Japanese residue or damaged dynamic names/classes.
- `fd90_s11_conditions.png` verifies victory `적 전멸` and defeat `주인공
  사망` / `제시카 사망`. The no-action first turn reviewed the oil-and-fire
  event, Jessica/Egbert/Lester dialogue, enemy movement, and current battle
  frames. `fd90_s11_turn1_slow_29.png` through `_34.png` show
  `그리폰/호크나이트`, `-AT-/-DF-`, counts, and status graphics intact.
  The path ended at `GAME OVER` after the exposed defenders were defeated;
  this is the expected scenario loss rather than a reset or freeze.
- The original REV00 fixed-placement list at `0x1813C6` contains 11 records.
  `tools/scenario_data.py` reads the complete list for the editor. Confirmed
  examples are Jessica (`소서러`, LV7, AT30, DF17, X18/Y6, mercenary ID 100
  x4), Egbert (`자베라`, LV7, AT43, DF32, X2/Y13, mercenary ID 115 x4), and
  the hidden final imperial commander (`호크나이트`, LV6, AT27, DF22,
  X/Y=`0xFF`, mercenary ID 125 x4). These exact values now have a regression
  test against the Japanese ROM.
- The editor may continue to write only class, LV, AT, DF, and the six
  mercenary slots. Coordinates and hidden/event flags are useful read-only
  context, but their runtime ownership is not proven sufficiently for UI
  editing. Later turns, completion, and branches remain pending.

### Current FD90 Scenario 12 Entry And Editor Records (2026-07-16)

- All 13 `성지 레이텔` briefing confirmations, arrangement, automatic
  deployment, all 12 slow opening confirmations, and the conditions were
  reviewed. The original pass incorrectly stopped after the first five visible
  commander rows. A F0E3 revisit followed `>>` and also verified
  `제시카/크루세이더` and `크루거/소서러`; all seven selectable rows are
  intact.
- Victory is `적 전멸` or `다크로드 획득`; defeat is `주인공 사망`. The
  no-action first turn reviewed monster movement, Jessica's warning, and a
  current `리치/파이터` battle. Names, `-AT-/-DF-`, counts, and status
  graphics remained intact. Elwin was defeated and `GAME OVER` followed as
  expected; this is not a reset or freeze. The Dark Rod acquisition event,
  later turns, completion, and branches remain pending.
- The original fixed-placement list at `0x181592` contains 11 records. Exact
  editor/parser regression samples are the lead Lich (`리치`, LV1, AT32,
  DF27, X15/Y8, mercenary ID 138 x4), the first Living Armor (`리빙아머`,
  LV1, AT31, DF30, X13/Y10, mercenary ID 130 x6), and hidden Egbert
  (`자베라`, LV7, AT43, DF32, X/Y=`0xFF`, no mercenaries). Other records in
  the same list cover `케르베로스`, `그레이트슬라임`, `고스트`, and
  `마스터디노`; they are already returned by `tools/scenario_data.py`.
- Direct X11 events continued to work for directions and C/B. In this in-game
  state, direct-event Start did not open the Start menu, while the existing
  focused XTest fallback (`--click-window start`) did. This is an automation
  transport difference, not a ROM defect.

### Current 85F1 Scenario 13 Entry, Terminology, And Editor Records (2026-07-16)

- Canonical terminology is now consistent across the production scenario
  source, reviewed event dialogue, and generated shared resources: `레이갈드`,
  `흑룡마도사단`, `성지 레이텔`, `다크로드`, `홀리로드`, `염룡병단`, and
  `빙룡병단`. Deprecated spaced or alternate forms are rejected by a resource
  regression test. Scenario 13 now displays `염룡병단과의 싸움` and
  `다크로드` in all 14 reviewed briefing frames.
- Moving `염` into the early scenario-description glyph pass initially shifted
  the stable name-entry allocation and failed the build with glyph ID `0x7263`.
  `scenario_description_glyph_text()` now defers that already-reviewed event
  glyph to its established later allocation point. Changing the source name
  `졸름` to canonical `조름` then removed one allocated glyph and shifted later
  IDs. `RETIRED_ZORUM_GLYPH_COMPATIBILITY_TEXT` deliberately reserves the old
  `졸` slot while every displayed source uses `조름`. The final build therefore
  retains 851 glyphs (`0x7000..0x7353`) and checksum `85F1` without moving the
  name grid or byte-UI graphics.
- The complete preparation roster was reviewed across both pages, not just the
  five visible rows: `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`,
  `아론/파이터`, `키스/호크나이트`, `제시카/크루세이더`, and
  `크루거/소서러`. This pagination rule must be applied to every future
  scenario and caused the explicit Scenario 11/12 revisits above.
- All nine opening dialogue pages, victory `조름 장군 격파`, defeat `주인공
  사망`, and the no-action first turn were reviewed. Zorum and imperial
  commander dialogue use `염룡병단`; current battles show intact names,
  classes, counts, and `-AT-/-DF-`. Elwin's defeat ends in the expected
  `GAME OVER`, not a reset or freeze.
- The original Scenario 13 fixed-placement list contains 13 records. Editor
  regression samples now lock Zorum (`하이로드`, LV9, AT29, DF31), hidden
  Vargas (`제너럴`, LV8, AT48, DF35), hidden Leon (`로얄가드`, LV2, AT45,
  DF34), and hidden Laird (`실버나이트`, LV5, AT39, DF28), including the
  original mercenary IDs where relevant. Later turns, completion, and branches
  remain pending.

### Current F0EE Scenario 14 Entry And Baldea Correction (2026-07-16)

- All 14 `성검 랑그릿사` briefing confirmations were reviewed. The live F0E3
  description exposed `발티아` even though reviewed event records already used
  `발디아`. Official Korean Langrisser I & II material also calls the fallen
  kingdom `발디아`. The production description source, generated shared
  resource, and `Baltia` fallback now consistently use `발디아`; a deprecated
  term regression test rejects `발티아`. The F0EE replay verifies
  `발디아 왕국` in the actual description. Glyph count and IDs remain stable at
  851 (`0x7000..0x7353`).
- The preparation list was reviewed through its second page. All seven rows are
  intact: `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `제시카/크루세이더`, and `크루거/소서러`.
- The complete opening reached Elwin's command menu and displays `발디아 성터`
  in Laird's dialogue. Conditions are one of Elwin/Jessica/Sherry reaching
  Langrisser or defeating Leon; loss is Leon reaching Langrisser or the
  protagonist dying. The no-action first turn reviewed Laird's aquatic, flying,
  and ballista orders plus imperial responses, then returned to a valid Elwin
  command menu without reset or freeze. No battle presentation occurred, so
  Scenario 14 battle UI remains covered by the shared probe.
- The original fixed-placement list has 11 records. Editor regression samples
  now lock an imperial Dragon Knight (LV4, AT31, DF25), Laird
  (`실버나이트`, LV5, AT39, DF28), and hidden Leon (`로얄가드`, LV2,
  AT45, DF34), along with their original coordinates and mercenary IDs. Later
  turns, completion, and branches remain pending.

### Scenario 14 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario14_clear_probe_rom.py` validates the Japanese Scenario
  14 header at `0x181934`, the seven stock player deployments beginning at
  `0x181956`, and all eleven fixed enemy records beginning at `0x181974`.
  It changes only each enemy's AT/DF and six mercenary slots, plus the Mega
  Drive checksum. Names, classes, levels, coordinates, hidden Leon, and all
  event data remain source-identical.
- The verified live conditions allow Elwin, Jessica, or Sherry to reach
  Langrisser, or Leon to be defeated. Leon reaching Langrisser or the
  protagonist dying causes defeat. No guessed Langrisser coordinate or compact
  placement is included: the safe probe is ready for later-turn and completion
  playback once foreground input is available.

### Current 85F1 Scenario 15 Entry And Editor Records (2026-07-16)

- All 13 `빙룡병단` briefing confirmations were reviewed through preparation.
  The preparation roster was not limited to the five rows visible initially:
  the page control was followed to the second page and verified
  `제시카/크루세이더` and `크루거/소서러`. Together with
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`, and
  `키스/호크나이트`, all seven selectable commanders render correctly.
  Future scenario checks must keep paging until the roster wraps to its first
  page; a single visible page is not complete preparation coverage.
- Arrangement, automatic deployment, the complete opening path, and conditions
  were reviewed. Victory is `이멜다 장군 격파` or `주인공 아래 이동`;
  defeat is `주인공 사망`. The first pass used a 2.0-second confirmation delay
  and captured only the first syllable of an Imelda page after the camera moved.
  A 3.2-second replay at `85f1_s15_opening_slow_06.png` proves the complete
  line is `드디어 따라잡았나 보군.`; this was capture timing, not damaged ROM
  text.
- The no-action first turn reviewed Imelda and imperial-commander dialogue,
  enemy movement, and `제시카/크루세이더`, then returned to a valid Elwin
  command menu without reset or freeze. No scenario-specific battle
  presentation occurred, so battle UI remains covered by the shared probe.
  Later turns, completion, and branches remain pending.
- The original fixed-placement list at `0x181B3E` contains 12 records. The
  editor regression locks a visible imperial `서펜나이트` (LV1, AT29, DF23,
  X11/Y13, mercenary ID 120 x4), Imelda (`제너럴`, LV6, AT46, DF32,
  X23/Y21, mercenary IDs 115 x2, 122 x2, 119 x2), and hidden Lana
  (`다크프린세스`, LV1, AT36, DF33, X/Y=`0xFF`, mercenary ID 135 x4).
  The editor must continue exposing coordinates and hidden/event flags as
  read-only context until their runtime ownership is proven.
- Direct-event menu navigation is reliable with short key holds such as
  `down:0.8`. A manual retry used `down@0.7`, which repeated and wrapped the
  selection into the wrong preparation submenu. No ROM change was needed; the
  run was restarted and completed with short direct events. Record this timing
  distinction to avoid repeating the false menu diagnosis.

### Scenario 15 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario15_clear_probe_rom.py` validates the Japanese Scenario
  15 header at `0x181B00`, all seven stock player deployments beginning at
  `0x181B22`, and all twelve fixed records beginning at `0x181B40`. Record 0
  is the hidden allied Scott event and remains byte-identical. Only enemy
  records 1..11 have AT/DF and their six mercenary slots limited.
- Imelda remains `제너럴` at stock `(23,21)`. Hidden Scylla, Lana
  (`다크프린세스`), a second Scylla, and Wyvern retain their original hidden
  flags, identities, classes, levels, and `(255,255)` initial coordinates.
  Player positions and all event handlers remain source-identical, so the
  diagnostic ROM is suitable for later-turn, reinforcement, retreat, and
  completion playback without making an unverified shortcut placement.
- Production `2CA4` source-reviews six awkward Scenario 15 records without
  adding a custom glyph or changing the established glyph order. Addresses
  `0x19FF78`, `0x1A012A`, `0x1A01A0`, `0x1A03F0`, `0x1A0844`, and
  `0x1A087E` now preserve Imelda's treatment of her troops, the mutiny's
  respectful address, Elwin asking whether Liana recognizes him, and Hein's
  explanation that he sensed a spell and recognized the caller's voice.
  All six fit their original physical-page capacities and render cleanly under
  `captures/analysis/s15_render_2ca4/`. This is static renderer evidence;
  Scenario 15 later-turn and completion playback remains pending.

### Current 85F1 Scenario 16 Entry And Editor Records (2026-07-16)

- All eight `레이갈드 제도` briefing confirmations were reviewed through the
  preparation transition. The first preparation page contains
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`, and
  `키스/호크나이트`. Following `>>` reveals a second page with
  `레스터/크로코나이트`, `제시카/소서러`, and `스코트/파이터`.
  `85f1_s16_roster_wrap_page1.png` records the return through `<<`, proving
  both pages and all eight selectable commanders were covered.
- Arrangement, automatic deployment, and all eight opening confirmations were
  reviewed. Dialogue status rows show `쉐리/파이터` and `레온/로얄가드`
  correctly. Conditions are victory by defeating Leon or moving to the castle
  gate, and defeat by the protagonist's death.
- The no-action first turn reviewed `레온/로얄가드` and
  `레아드/실버나이트` dialogue plus all enemy movement, reached `TURN 2`,
  and returned to a valid Elwin command menu without reset or freeze. This path
  did not trigger a battle presentation, so battle UI remains covered by the
  shared probe. Later turns, completion, and branches remain pending.
- The original fixed-placement list at `0x181D34` contains ten records and is
  distinct from the eight selectable preparation commanders. Editor regression
  samples now lock Leon (`로얄가드`, LV4, AT46, DF35, X13/Y10), a visible
  imperial Dragon Lord (`드래곤로드`, LV1, AT35, DF28, X20/Y12), and hidden
  Lana (`다크프린세스`, LV1, AT36, DF33, X/Y=`0xFF`) with their exact
  original mercenary IDs. Coordinates and hidden/event flags remain read-only
  editor context until their ownership is proven.

### Scenario 16 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario16_clear_probe_rom.py` validates the Japanese Scenario
  16 header at `0x181CF0`, all eight stock player deployments beginning at
  `0x181D14`, and all ten fixed enemy records beginning at `0x181D36`.
  It changes only each enemy's AT/DF and six mercenary slots plus the Mega
  Drive checksum. No player coordinate or event byte is changed.
- Leon remains `레온/로얄가드`, LV4, AT46, DF35 at stock `(13,10)`;
  Laird remains `레아드/실버나이트`, LV6, AT40, DF28 at `(6,20)`.
  Hidden records 7..9 retain `(255,255)`, including Lana as
  `라나/다크프린세스`, LV1, AT36, DF33. Both hidden ghosts, all identities,
  classes, levels, initial coordinates, and event handlers are preserved for
  later-turn, gate, reinforcement, and completion playback. Production `2CA4`
  builds the ignored diagnostic ROM as checksum `02C6`.

### Current 12D3 Scenario 17 Entry, Wrapping Fixes, And Editor Records (2026-07-16)

- All eight `황제와 어둠의 왕자` briefing confirmations were reviewed. The
  complete preparation roster has eight selectable commanders across two
  pages: `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `제시카/소서러`, and
  `스코트/파이터`. The run followed `>>` and then `<<` back to page one;
  preparation coverage is not inferred from the first five visible rows.
- The initial 85F1 opening review exposed three renderer-specific wrapping
  defects: `어/디`, `알/하자드`, `주/는`, plus a comma stranded before
  `모두`. Shortening alone did not fix the first two because the dynamic Liana
  name changes the remaining line width. Final event records use explicit
  semantic breaks at `0x1A2852`, `0x1A296C`, and `0x1A2A98`:
  `리아나가 없다! / 어디 간 거지!?`, `당신은 이용당할 뿐이다. /
  알하자드는 생각대로 / 힘을 주는 검이 아니다.`, and
  `원하는 대로 해 주지. / 간다, 모두!`. Production 12D3 captures
  `12d3_s17_opening_09.png`, `_14.png`, and `_18.png` prove all four defects
  are gone. Glyph count and IDs remain stable at 851 (`0x7000..0x7353`).
- Conditions are victory by defeating Bernhardt and defeat by the
  protagonist's death. The no-action first turn ran through 47 retained frames,
  reviewed Bernhardt and imperial dialogue, enemy movement, Scott and Jessica
  reactions, and live `발리스타/파이터/소서러` battles. Names, classes,
  `-AT-/-DF-`, troop counts, and status graphics remained intact, and the path
  returned to a valid Elwin command menu without reset or freeze. Later turns,
  completion, and branches remain pending.
- The original fixed-placement list at `0x181EE2` contains 11 records. Editor
  regressions lock Bernhardt (`엠퍼러`, LV1, AT52, DF37, X15/Y4), Bozel
  (`다크마스터`, LV1, AT38, DF29, X18/Y6), and a hidden imperial Magic Knight
  (`매직나이트`, LV10, AT36, DF27, X/Y=`0xFF`) with exact original
  mercenary IDs. `엠퍼러` follows the Korean class reference for original
  `エンペラー`; no class rename was needed. Coordinates and hidden/event flags
  remain read-only editor context.

### Scenario 17 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario17_clear_probe_rom.py` validates the Japanese Scenario
  17 header at `0x181E9E`, all eight stock player deployments beginning at
  `0x181EC2`, and all eleven fixed enemy records beginning at `0x181EE4`.
  It changes only each enemy's AT/DF and six mercenary slots plus the checksum;
  player coordinates and event data remain byte-identical.
- Bernhardt remains `베른하르트/엠퍼러`, LV1, AT52, DF37 at `(15,4)`,
  and Bozel remains `보젤/다크마스터`, LV1, AT38, DF29 at `(18,6)`.
  Hidden records 9 and 10 retain their two imperial commander IDs,
  `매직나이트`, LV10, AT36, DF27, and `(255,255)` initial coordinates.
  The diagnostic therefore preserves the throne, hidden reinforcement, and
  completion event ownership for later live playback. Production `2CA4`
  builds the ignored diagnostic ROM as checksum `FFB9`.

### Current 1391 Scenario 18 Entry, Dynamic Name Order, And Editor Records (2026-07-16)

- All eight `어둠의 공주` briefing confirmations were reviewed. The complete
  preparation roster again has eight selectable commanders across both pages:
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `제시카/소서러`, and
  `스코트/파이터`. The `>>`/`<<` round trip is retained as evidence that the
  second page was not omitted.
- Live 12D3 exposed an awkward token order at `0x1A497A`: `인간은 마물의
  먹이라고 보젤님이 말했다`. The English reference and Japanese dynamic
  speaker token both mean that Bozel taught her humans are food for monsters.
  The reviewed text is now `정의로운 척하는군! / 보젤님은 인간이 마물의
  / 먹이라고 하셨다.` Production 1391 capture
  `1391_s18_opening_11.png` verifies the inserted `보젤` remains intact and
  the three lines wrap naturally. Glyph count and IDs remain 851
  (`0x7000..0x7353`).
- Conditions are victory by defeating the Great Dragon or Dark Princess, and
  defeat by the protagonist's death or all residents being eliminated. The
  no-action first turn reviewed Liana, Hein, and Jessica dialogue plus enemy
  movement, reached `TURN 2`, and returned to a valid Elwin command menu
  without reset or freeze. No battle presentation occurred, so battle UI
  remains covered by the shared probe. The evacuation choice's alternate path,
  later turns, completion, and other branches remain pending.
- The original fixed-placement list at `0x1820B4` contains 11 records. Editor
  regressions lock a resident (`클레릭`, LV2, AT20, DF17, X15/Y20), the Great
  Dragon (`그레이트드래곤`, LV1, AT39, DF34, X35/Y4), and Lana
  (`다크프린세스`, LV3, AT37, DF34, X37/Y2), including their exact original
  mercenary IDs. The resident's original class mapping confirms `클레릭` is
  intentional here. Coordinates and event ownership remain read-only context.

### Scenario 18 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario18_clear_probe_rom.py` validates the Japanese Scenario
  18 header at `0x182070`, all eight stock player deployments beginning at
  `0x182094`, and all eleven fixed records beginning at `0x1820B6`. Records
  0 and 1 are the two `side_id=3` residents and remain byte-identical,
  including `클레릭`, their four 시민 units, and stock coordinates.
- Only `side_id=4` enemy records 2..10 have AT/DF and six mercenary slots
  limited. The Great Dragon remains `그레이트드래곤`, LV1, AT39, DF34 at
  `(35,4)`, while Lana remains `라나/다크프린세스`, LV3, AT37, DF34 at
  `(37,2)`. All identities, classes, levels, coordinates, resident-loss logic,
  evacuation choice, and completion events remain source-identical for live
  playback. Production `2CA4` builds the ignored diagnostic ROM as checksum
  `660B`.

### Current 1391 Scenario 19 Entry And Canonical Dark Princess Label (2026-07-16)

- All six `미레일 항구 전투` briefing confirmations were reviewed. The
  preparation roster was followed through both pages and back to page one:
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `제시카/소서러`, and
  `스코트/파이터`. This eight-row round trip is retained as evidence; the
  first five visible rows are not treated as complete coverage.
- The opening review exposed `다크 프린세스` at `0x1A6556`, inconsistent
  with the canonical class label `다크프린세스`. All six reviewed event
  occurrences now use the unspaced class label, and the residue test rejects
  the deprecated spaced form. A fresh production replay verifies
  `이런, 다크프린세스!` without a bad wrap. The glyph inventory remains 851
  entries (`0x7000..0x7353`) and the ROM checksum remains `1391`.
- Conditions are victory by defeating Imelda within 23 turns, and defeat by
  exceeding the turn limit or the protagonist's death. The no-action first
  turn retained 32 frames, reviewed ship movement and dialogue from
  `제시카/소서러`, `아론/파이터`, and `엘윈/파이터`, reached `TURN 2`,
  and returned to Elwin's command menu without reset or freeze. No battle
  presentation occurred, so battle UI remains covered by the shared probe.
- The Japanese ROM's fixed-placement list at `0x182286` contains ten records.
  Editor regressions lock an imperial Saint (`세인트`, LV5, AT34, DF30,
  X26/Y17), Imelda (`제너럴`, LV10, AT48, DF33, X37/Y23), and hidden Laird
  (`레아드/실버나이트`, LV9, AT42, DF29, X/Y=`0xFF`) with their exact six
  mercenary slots. Coordinates and hidden/event flags remain read-only editor
  context until runtime ownership is proven. Later turns, completion, and
  branches remain pending.

### Scenario 19 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario19_clear_probe_rom.py` validates the Japanese Scenario
  19 header at `0x182242`, all eight stock player deployments beginning at
  `0x182266`, and all ten fixed enemy records beginning at `0x182288`.
  It changes only each enemy's AT/DF and six mercenary slots plus the checksum;
  player coordinates and event data remain byte-identical.
- Imelda remains `이멜다/제너럴`, LV10, AT48, DF33 at `(37,23)`.
  Hidden records 7..9 retain `(255,255)`, including Laird as
  `레아드/실버나이트`, LV9, AT42, DF29 and the two source imperial
  reinforcement identities/classes. The turn limit, ship movement,
  reinforcement, retreat, and completion event ownership remain intact for
  later live playback. Production `2CA4` builds the ignored diagnostic ROM as
  checksum `7625`.

### Current 138B Scenario 20 Entry And Keith Address Fix (2026-07-16)

- All seven `붉게 물든 바다` briefing confirmations were reviewed. Entering
  the `지휘관배치` submenu exposes the actual paged roster: page one contains
  `엘윈`, `헤인`, `쉐리`, `아론`, and `키스`; page two contains `레스터`,
  `제시카`, and `스코트`. The run returned through `<<` to page one. The
  initial preparation action menu is not the commander pager; pressing Down
  there only cycles `용병고용/장비착용/상점/지휘관배치` and must not be
  mistaken for roster coverage.
- The complete opening and conditions render normally. Victory is `적 전멸`
  and defeat is `주인공 사망`. The no-action first turn retained 41 frames,
  reviewed Faias's orders and enemy movement, reached `TURN 2`, then reviewed
  the golem tactics exchange before returning to Elwin's command menu without
  reset or freeze. The current route did not trigger the later conditional
  kraken event or a battle presentation.
- Live checksum `1391` exposed `키스: 공주` at `0x1A81E6`. The Japanese
  physical page is `姫！`, but it has only two content words. `공주님!` needs
  four words and correctly fails the builder's capacity guard. The final
  capacity-safe translation is the complete royal address `전하`; checksum
  `138B` capture `138b_s20_turn1_38.png` verifies it before Aaron's reply.
  A regression test locks this exact address so the incomplete wording does not
  return. Glyph count and IDs remain 851 (`0x7000..0x7353`).
- The Japanese ROM's fixed-placement list at `0x182434` contains ten records.
  Editor regressions lock a visible Scylla (`스큐라`, LV10, AT36, DF22,
  X18/Y8), Faias (`파이어스/데몬로드`, LV1, AT46, DF32, X22/Y23), and a
  hidden Kraken (`크라켄`, LV4, AT39, DF32, X/Y=`0xFF`) with exact mercenary
  slots. The list also includes Minotaurs, Liches, another Scylla, and hidden
  Wyverns. Coordinates and hidden/event flags remain read-only editor context.

### Scenario 20 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario20_clear_probe_rom.py` validates the Japanese Scenario
  20 header at `0x1823F0`, all eight stock player deployments beginning at
  `0x182414`, and all ten fixed enemy records beginning at `0x182436`.
  It changes only each enemy's AT/DF and six mercenary slots plus the checksum;
  player coordinates and all event data remain byte-identical.
- Fias remains `파이어스/데몬로드`, LV1, AT46, DF32 at `(22,23)`.
  Hidden records 7..9 retain `(255,255)` and their original 와이번/크라켄
  identities, classes, levels, and source mercenary IDs. Keith's player roster
  entry, sea-monster reinforcements, story events, and completion handler are
  untouched for later live playback. Production `2CA4` builds the ignored
  diagnostic ROM as checksum `27E5`.

### Current 138B Scenario 21 Entry And Full Commander/Class Roster (2026-07-16)

- All seven `마리오네트` briefing confirmations render normally. The actual
  `지휘관배치` pager was followed from page one (`엘윈/헤인/쉐리/아론/키스`)
  to page two (`레스터/제시카/스코트`) and back to page one. This explicitly
  verifies Jessica and prevents the five initially visible rows from being
  mistaken for the full roster.
- Names alone are not accepted as class coverage. Opening `장비착용` makes the
  left commander list selectable without changing equipment. Walking that
  list verified `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `제시카/소서러`, and
  `스코트/파이터`. In this selector, horizontal input changes roster pages
  while the left list owns focus. Press Right to transfer focus to the
  equipment choices; skipping all three slots is required before the main
  preparation menu returns. No equipment was changed during this check.
- Automatic deployment and all 16 opening frames were reviewed. The opening
  includes Aaron, Scott, `리아나/세인트`, Lich, Elwin, Sherry, Keith, Lester,
  and Jessica dialogue without Japanese text, damaged names/classes, abnormal
  wrapping, reset, or freeze. Victory is `적 전멸`; defeat is `주인공 사망`.
  Ending the turn retained 18 enemy-movement frames, reached `TURN 2`, and
  returned to a valid Elwin command menu. No scenario-specific battle screen
  occurred, so battle UI remains covered by the shared probe.
- The Japanese ROM fixed-placement list at `0x1825E2` has eleven records.
  Editor regressions lock a visible Lich (`리치`, LV5, AT35, DF29, X31/Y7),
  Lana (`라나/다크프린세스`, LV6, AT39, DF36, X37/Y11), and the stronger
  hidden Kraken (`크라켄`, LV8, AT41, DF35, X/Y=`0xFF`) with exact mercenary
  IDs. The same list also contains Succubi, Living Armors, two other hidden
  Krakens, and a hidden imperial Archmage. Coordinates and hidden/event flags
  remain read-only editor context.

### Scenario 21 Source-Validated Clear Probe (2026-07-21)

- `tools/build_scenario21_clear_probe_rom.py` validates the Japanese Scenario
  21 header at `0x18259E`, all eight stock player deployments beginning at
  `0x1825C2`, and all eleven fixed enemy records beginning at `0x1825E4`.
  It changes only each enemy's AT/DF and six mercenary slots plus the checksum;
  player coordinates and event data remain byte-identical.
- Lana remains `라나/다크프린세스`, LV6, AT39, DF36 at `(37,11)`.
  Hidden records 7..10 retain `(255,255)`, including three original 크라켄
  records and the imperial `아크메이지`, LV6, AT39, DF27. Their identities,
  classes, levels, source mercenaries, reveal events, and completion handler
  remain intact for later live playback. Production `2CA4` builds the ignored
  diagnostic ROM as checksum `AD53`.

### Current 138B Scenario 22 Background Inventory And Partial Preparation (2026-07-16)

- The current-build pass reviewed all six confirmations of `알하자드의 부활`
  through preparation. The `지휘관배치` pager was followed from page one
  (`엘윈/헤인/쉐리/아론/키스`) to page two (`레스터/제시카/스코트`) and
  back to page one, so Jessica is explicitly covered. The equipment commander
  selector then verified the first-page class panels as `엘윈/파이터`,
  `헤인/워록`, `쉐리/파이터`, `아론/파이터`, and `키스/호크나이트`.
- Runtime input stopped at that exact point at the user's request while another
  game uses the machine. Page-two class panels, automatic deployment, the full
  current-build opening, conditions, and the first no-action turn remain
  pending and must not be inferred from the older `3B53` opening probe. BlastEm
  was terminated before background-only work continued.
- Static dialogue remains complete as documented in `Scenario 22 Complete
  Reviewed Dialogue`: 151 Japanese pointer records and 191 physical pages.
  No dialogue text was changed in this background pass.
- The Japanese ROM fixed-placement list at `0x1827B4` contains twelve records.
  Editor regressions lock `리아나/클레릭` (LV2, AT20, DF17, X14/Y4),
  `보젤/다크마스터` (LV6, AT42, DF32, X15/Y5), and hidden
  `베른하르트/엠퍼러` (LV10, AT58, DF41, X/Y=`0xFF`) with their exact
  mercenary bytes. The list also contains Lana, imperial Archmages and a Saint,
  Egbert, Iron Golems, and Liches. Coordinates and hidden/event flags remain
  read-only editor context.

### Scenario 23 Original Editor Records (2026-07-16)

- Background-only inspection of the Japanese ROM found eleven fixed-placement
  records at `0x1829B0`. This does not change Scenario 23's runtime status; a
  fresh production playthrough of briefing, complete preparation pages,
  opening, conditions, and the first turn is still required.
- Editor regressions lock an imperial `드래곤로드` (LV10, AT45, DF31,
  X23/Y13), `레아드/실버나이트` (LV10, AT43, DF30, X23/Y7), and an imperial
  `위저드` (LV10, AT35, DF31, X30/Y3), including exact mercenary slots. The
  remaining records are imperial Paladins, Saints, another Dragon Lord, and
  another Wizard. Scenario 23 has no hidden fixed record in this list.
- As with earlier scenarios, the editor may write only the already verified
  class, LV, AT, DF, and six mercenary fields. Coordinates remain read-only
  context, and the absence of a hidden flag here must not be generalized to
  event-spawned units.

### Scenarios 24-26 Original Editor Records (2026-07-16)

- Background-only Japanese-ROM inspection added representative editor
  regressions without changing any runtime status. Scenario 24 has eleven
  records at `0x182B88`; the locked samples are `베른하르트/엠퍼러`, a
  `데몬로드`, and a `뱀파이어로드`. This list also contains Liches and
  Cerberuses and has no hidden fixed record.
- Scenario 25 has twelve records at `0x182D60`. The locked samples are
  `제시카/워록`, `레온/로얄가드`, and the hidden imperial `드래곤로드`,
  including their exact six mercenary bytes. The list also contains
  `레아드/실버나이트`, Egbert, imperial Wizards, Paladins, and a
  Knight Master.
- Scenario 26 has ten records at `0x182F62`. The locked samples are an imperial
  `아크메이지`, an imperial `나이트마스터`, and `에그베르트/자베라`.
  The other records are imperial Wizards, Saints, and Archmages; none of the
  fixed records is hidden.
- Fresh production playback is still required for all three scenarios before
  briefing, preparation, opening, conditions, or turn-event states can be
  promoted. The editor continues to write only class, LV, AT, DF, and the six
  mercenary slots; coordinates and hidden/event flags remain read-only.

### Scenarios 27-31 Original Editor Records (2026-07-16)

- Background-only extraction now gives every late-game fixed list at least one
  exact editor regression. Scenario 27 (`0x18311C`, ten records) locks a Demon
  Lord, Bernhardt, and hidden `레온/로얄가드`. Scenario 28 (`0x1832C4`, nine
  records) locks `형님/빌더`, `아돈/빌더`, and `바란/빌더`, preserving this
  special scenario's unusual names and mercenary groups.
- Scenario 29 (`0x18344E`, nine records) locks an imperial `서펜로드`,
  `세이갈/드래곤로드`, and `폴거/드래곤로드`. Scenario 30 (`0x1835DE`,
  eleven records) locks a Great Dragon, `마녀/메이지`, and the hidden
  `마녀/세인트`; the two witch classes are deliberately distinct.
- Scenario 31 (`0x1837BC`, ten records) locks the boosted `발가스/제너럴`,
  `보젤/다크마스터`, and final `베른하르트/엠퍼러` records. The large final
  AT/DF values are original data, not editor corruption.
- These regressions do not promote runtime coverage. Scenario 27 retains its
  separately documented production-derived ending probe, while Scenarios
  28-31 still require fresh production traversal. Writable editor fields stay
  limited to class, LV, AT, DF, and mercenary slots.

### Scenarios 2-10 Original Editor Regression Matrix (2026-07-16)

- Background-only Japanese-ROM extraction now gives every Scenario 2-10 fixed
  list three exact representative records. The data-driven regression checks
  record count, Korean name/class mapping, LV/AT/DF, coordinates, hidden flag,
  and all six mercenary bytes for each sample.
- Coverage includes Loren, Liana, the mystery knight, Vargas, priests, Morgan,
  Werewolves, Aaron and residents, Keith, Ginam, Kramer, Zorum, Laird, Leon,
  Lester, Scylla, Great Slime, and ordinary/hidden imperial commanders. This
  protects the same early-game names and classes that previously exposed live
  font and direct-reader bugs.
- Together with the existing Scenario 1 check and explicit Scenario 11-31
  tests, every one of the 31 fixed-placement lists now has a scenario-specific
  editor regression in addition to the generic pointer/count validation.
  Runtime verification states are unchanged; this matrix is original-data and
  editor groundwork only.

### All-Scenario Editor No-Change Regression (2026-07-16)

- `test_no_change_patch_is_byte_identical_for_all_scenarios` now reads and
  reapplies every exposed fixed-placement field for each Scenario 1-31 against
  production `138B`. Every no-change result must remain byte-identical,
  including the stored Mega Drive checksum.
- The checksum path now converts the ROM body to native 16-bit words in one
  block and byte-swaps on little-endian hosts. It produces the same `138B`
  result while reducing this 31-scenario regression from about 18.6 seconds
  to about 1.0 second on the current machine.
- The editor still writes only class, LV, AT, DF, and the six mercenary slots.
  Name ID `+0x1A`, coordinates, and event/hidden flags remain read-only context;
  README wording was corrected so the known name-ID address is not mistaken
  for an exposed writable field.

### Intentional GAME OVER Inventory Classification (2026-07-16)

- Direct record `0x082B3C` is the conventional English `GAME OVER`, already
  accepted by the localization policy and verified in live loss paths. The
  direct-word inventory now classifies it as
  `intentionally_retained_system_label` instead of inflating the unpatched
  system-message count.
- The inventory now reports zero confirmed unpatched system messages, one
  intentionally retained label, one intentionally unreachable debug record at
  `0x082B78`, and zero unclassified candidates. Regeneration also synchronizes
  stored current-token IDs with production checksum `138B`; target text and
  original ownership are unchanged.

### Static Ownership Trace For Direct Record 0x082B78 (2026-07-16)

- The unresolved Japanese record is pointer-table entry 12 in the system
  message table at `0x082A92`; its entry address is `0x082AC2` and its text
  starts at `0x082B78`. The only absolute references to the table base in the
  original ROM are `0x0149D2`, `0x014A64`, and `0x0170E0`.
- `0x0149C6..0x014AE2` builds the level-up message and calls its table-copy
  helper with fixed indexes 0-4 and 7, plus the bounded stat-increase suffix
  index. `0x0170DE` reads entry 0 directly. Separate absolute reads use entry 9
  for `GAME OVER`, entry 10 for item acquisition, and entry 13 for equipment.
  No absolute reference to entry address `0x082AC2` exists in the ROM.
- The stricter value-range proof is now implemented by
  `unreachable_debug_message_proof()`. Across all 40 class IDs reachable from
  the ten playable commanders' complete class-change chains, the three growth
  fields use growth IDs `0..10,12,14`, whose ten-level table values are only
  `0,1,2`. The level-up renderer skips zero and can therefore select only
  suffix entries 5 and 6, never entry 12. Entry address `0x082AC2` and message
  address `0x082B78` also have no executable-region absolute references.
- Entry 12 is now classified `intentionally_unreachable_debug_message` and its
  malformed-looking original text remains unchanged. This is an unreachable
  ROM artifact, not untranslated player-facing UI.
- `test_checked_in_reports_match_current_rom` now compares the computed 783
  candidates with both checked-in JSON and generated Markdown. This prevents
  another production glyph-ID change from leaving the stored direct inventory
  stale while the live calculation tests still pass.

### Generated Inventory Freshness Checks (2026-07-16)

- Regenerating all static inventories against production `138B` found two
  stale metadata-only results: event records `0x19F66A` and `0x1A4822` had old
  modified-word counts, and compressed byte-font resource 1 had an old current
  decoded SHA-256. The current ROM itself was not changed.
- Event and compressed-resource tests now compare their computed models with
  both checked-in JSON and generated Markdown, matching the direct-string
  freshness guard. Future ROM changes must update these reports in the same
  commit instead of silently leaving old hashes or counts behind.

### Scenario 23-31 Description Retranslation And Token Relocation (2026-07-17)

- The Japanese Scenario 23-31 records were rendered directly from
  `roms/original/Langrisser II (Japan).md` with
  `tools/jp_text_font_analyzer.py render-text --table scenarios --mapped`.
  This review found substantive legacy errors, not just awkward wording:
  Scenario 23 incorrectly called Jessica's spell a sacrifice and omitted
  Bernhardt's continental ambition; X2 called a late reinforcement unit
  Imelda's escort; X4 invented `헤인과 남은 엘윈` where the source says the
  outcome depends entirely on Elwin's tactics.
- Scenario 23-31 descriptions now preserve the original events and terminology.
  Restored details include Laird's Elrad battle, Leon and Egbert blocking the
  way to Bernhardt, the Black Dragon Sorcerers' concentrated attack, the
  millennia-long legend ending, Kalzath's care of Liana and the forbidden
  muscle temple, Imelda's delayed support and revenge attack, the Great Dragon
  nest, and the allies captured and brainwashed on each Death Tower floor.
  Offline rendering of the built records showed readable Korean with no
  truncation. Live playback remains pending.
- The first corrected build failed safely because new description vocabulary
  moved name-entry `범` to `0x7266` and `릭` to `0x726D`, past the verified
  `0x7262` ceiling. `DEFERRED_SCENARIO_DESCRIPTION_GLYPH_TEXT` now allocates
  newly promoted description vocabulary after `NAME_ENTRY_GRID_CHARS`, keeping
  established name-entry IDs stable. The related name-entry tests pass.
- Keeping the corrected prose in the original token slots then exposed four
  real capacity overflows: Scenario 24 needed 228 words in a 214-word slot,
  Scenario 27 needed 266/251, X2 needed 247/240, and X3 needed 228/213.
  Shortening them would discard source information, so all 31 description
  token streams are now relocated to `0x274000..0x277475`, with their 32-bit
  table entries updated. Glyph lists remain in `0x270000..0x271C03`; hard
  `0x274000` and `0x280000` bounds plus new pointer/terminator tests prevent
  overlap or unterminated records.
- Production checksum is now `A15B` with 852 custom glyphs ending at `0x7354`.
  The shared resource inventory marks only Scenario 23-31 as statically
  reviewed and keeps all nine live flags false. Because every description
  pointer changed, earlier Scenario 2-22 and 27 description captures were
  conservatively demoted to `historical`; unrelated live surface states were
  retained. No BlastEm process or input automation was used while the user was
  playing Forza Horizon.

### Scenario 2-10 Description Source Review (2026-07-17)

- The same background-only Japanese record renderer was used for Scenario
  2-10. The legacy prose had omitted Loren's request and Zorum's approaching
  unit in Scenario 2, the party's wounds and exhaustion in Scenario 3, and the
  Leon/Laird elite force in Scenario 9. Scenario 8 contained a reversed fact:
  Keith did not join as a guide; his absence left Kalzath Castle thinly
  defended while the Blue Dragon Knights advanced.
- All nine descriptions were rewritten from the Japanese records. Scenario 5
  now correctly leaves Liana out of the pursuit party and identifies Sherry as
  the newly joined companion. Scenario 10 restores the Dark Rod's role in
  fully reviving Alhazard and the Rahl River blocking the party's path.
  Generated `4D39` record sheets show readable Korean, 18-cell wrapping, and
  no truncation or bad glyphs.
- Newly promoted description syllables remain allocation-delayed until after
  the name-entry grid. The build adds only one custom glyph relative to
  `A15B`, uses 853 glyphs through `0x7355`, and keeps all name-entry safety
  tests green. The shared inventory now marks Scenario 2-10 and 23-31 (18
  records total) statically reviewed, with live playback still unclaimed.
  Production checksum is `4D39`; no BlastEm process or input automation was
  used for this review.

### Scenario 11-22 Description Source Review (2026-07-17)

- Scenario 11-22 were rendered from the Japanese ROM with the same mapped
  16x16-font workflow and retranscribed before any live claim was made. The
  middle block contained several factual omissions: Scenario 11 now identifies
  Lester's guidance and Egbert's prepared trap; Scenario 12 restores the hidden
  cave entrance and ancient guardians; Scenario 13 restores the magical theft
  and teleport; Scenario 22 now includes the evil statue, altar sword, two
  lookalike girls, Bozel, and the seal-breaking incantation.
- Two older translations contradicted or invented source events. Scenario 14
  said Jessica helped reveal Baldea Castle, which is not in the Japanese
  description, and Scenario 21 said Chaos lives in Velzeria rather than being
  sealed there. Both are corrected. Scenario 15's Japanese title
  `氷竜兵団将軍イメルダ` is now `빙룡병단장 이멜다`; Scenario 13 is now
  `염룡병단과의 결전`. Historical checksum `85F1` captures still show the
  older `염룡병단과의 싸움`, so the runtime inventory explicitly treats
  that title evidence as historical and requires new playback.
- Offline built-record renders for all twelve descriptions show complete
  Korean glyphs. The focused description, name-entry, pointer, and terminator
  suite passes. The production build is checksum `57D4`, with 859 custom
  glyphs through `0x735B`; name-entry IDs remain within their verified range.
  The shared resource inventory now marks Scenario 2-31 (30 records) as
  statically source-reviewed while Scenario 1 remains separate and every live
  description flag remains false.
- No BlastEm process, keyboard/mouse automation, or gamepad input was used in
  this unit because the user was playing Forza Horizon. Fresh on-screen checks
  for the relocated descriptions and the renamed Scenario 13/15 titles remain
  pending until exclusive emulator input is available.

### Scenario 1 Description Source Review And Live Playback (2026-07-17)

- The final unreviewed description record was compared with the Japanese ROM.
  The previous Korean text invented Bald as the visible enemy commander and a
  future-war narration, while omitting that Elwin spent several days becoming
  acquainted with the villagers, Hein became like an old friend, and Liana is
  Elwin's childhood friend. The current text restores those source facts and
  retains the original `서장` title and victory/defeat conditions.
- Scenario 1 is a fixed 331-word record with four `FFF7 0001` dynamic hero-name
  controls. Its visible body has immutable boundaries of 19, 83, 39, 81, and
  23 characters. The corrected Korean prose fits those exact spans and renders
  the default name naturally as `엘윈이었다`, `엘윈을`, `엘윈이`, and
  `엘윈의`. Tests reject the invented Bald/future-war lines and require the
  restored village, Hein, and Liana facts.
- Changing the first record initially renumbered later custom glyphs. The
  former Scenario 1 character order is now retained by
  `RETIRED_SCENARIO0_DESCRIPTION_GLYPH_COMPATIBILITY_TEXT`; new-only syllables
  are derived from the corrected body, suppressed only for Scenario 1's early
  pass, and collected after every established consumer. A direct comparison
  against commit `c338ef9` proves all 859 glyph IDs remain identical through
  `0x735B`, and generated direct-string tokens no longer churn.
- Production checksum `C7AB` was played in BlastEm with direct window events.
  `c7ab_s01_title.png`, `c7ab_s01_body_name1.png` through `_name4.png`, and
  `c7ab_s01_conditions.png` verify the title, full automatic scroll, four name
  contexts, final `위험에 처한 이는 엘윈의 소꿉친구 리아나였다. 그는 검을
  들었다`, and conditions without broken glyphs or reset. The runtime
  inventory promotes only Scenario 1 description to `verified_current`; the
  other relocated descriptions still require fresh live playback.
- All 31 scenario description records are now marked statically source-reviewed
  and all remain pointer/terminator checked in the shared resource inventory.

### Current C7AB Middle Description Playback (2026-07-17)

- Fresh BlastEm sessions used the built-in scenario selector on production
  checksum `C7AB` after emulator input was available again. Scenario 13 shows
  the corrected title `염룡병단과의 결전` and reaches the rewritten ending
  about Vargas and the Fire Dragon Corps. Scenario 15 shows the Japanese-source
  title `빙룡병단장 이멜다`, reaches its corrected ending, and then opens an
  intact first preparation page with `엘윈/헤인/쉐리/아론/키스`.
- Scenario 22 was followed from the evil statue and altar sword through the two
  lookalike girls, Bozel's incantation, and the imminent broken seal. The title
  and sampled body frames render without broken glyphs or reset on `C7AB`.
- These three descriptions are recorded as `progressed_current`, not fully
  verified, because the live captures sampled their automatic intermediate
  scroll rather than preserving every distinct frame. The inventory cites
  `c7ab_s13_title.png`, `c7ab_s15_title.png`, and
  `c7ab_s22_body_final2.png`; `c7ab_s13_conditions.png` is intentionally not
  cited because that filename contains a preparation-screen frame rather than
  the conditions page.
- The emulator was stopped after the captures. No keyboard or gamepad conflict
  occurred during these sessions. Tests explicitly bind the current
  description state to scenarios 13, 15, and 22 so a future off-by-one
  inventory edit cannot silently promote adjacent scenarios.

### Current C7AB Late Description Playback (2026-07-17)

- Production `C7AB` was freshly entered through selector description records
  23-31. Records 23-27 display the matching on-screen scenario numbers and the
  titles `봉인의 열쇠`, `빛과 어둠`, `대륙 최강의 기사`,
  `흑룡마도사단의 함정`, and `전설의 끝`. Their title, intermediate body,
  and stable final frames render without bad glyphs, reset, or freeze.
- The last four selector records intentionally map to the optional on-screen
  Scenarios X1-X4 rather than numbered Scenarios 28-31: record 28 is
  `근육의 신전`, record 29 is `디레스 해협의 격전`, record 30 is
  `마룡의 둥지`, and record 31 is `죽음의 탑`. Keep this distinction in
  inventory notes and capture filenames; it reflects the existing selector's
  31 description-record ordering, not an input error.
- Every late description was followed to a stable final frame. Because the
  automatic scroll was sampled at two-second intervals rather than capturing
  every distinct frame, records 23-31 are conservatively marked
  `progressed_current`, not `verified_current`. Scenario 23 additionally
  reached an intact first preparation page. Other runtime surfaces for the
  previously bare records remain pending.
- BlastEm was stopped after record 31. Direct window events worked throughout,
  and no user keyboard/gamepad collision was observed. The runtime regression
  now requires current description evidence for records 23-31 and explicitly
  cites both boundary captures so these entries cannot silently fall back to
  bare pending records.

### Current C7AB Early Description Playback (2026-07-17)

- Production `C7AB` was freshly entered through Scenarios 2-12 with direct
  BlastEm window events. Each description has a title capture, one or more
  intermediate body captures, and a stable final-frame capture. No broken
  glyph, reset, freeze, or user-input collision was observed.
- The live frames preserve the Japanese-source corrections made during the
  static review: Scenario 2 includes Loren and Zorum's approaching force;
  Scenario 3 includes the party's wounds and exhaustion; Scenario 5 sends
  Sherry rather than Liana with the pursuit party; Scenario 8 reflects Keith's
  absence from the castle; Scenario 9 names Leon and Laird's elite cavalry;
  Scenario 10 restores the Dark Rod and Rahl River; Scenarios 11-12 retain
  Lester, Egbert's trap, the hidden entrance, and the ancient guardians.
- Scenarios 2-12 are conservatively `progressed_current` because the automatic
  scroll was sampled at two-second intervals rather than recording every
  distinct frame. Existing stronger current evidence for their conditions,
  preparation, opening, battle UI, and turn events remains unchanged.
- Operational rule for future Goal resumes: when Codex reports
  `{"detail":"Bad Request"}`, retry the same bounded action once. If it fails
  again, split combined key, capture, read, or edit calls into smaller requests
  and continue from the last verified artifact. Do not treat this transport
  error as a ROM/emulator failure, and do not abandon a running verification
  sequence solely because it appeared.

### Current C7AB Remaining Description Playback (2026-07-17)

- Production `C7AB` was freshly entered for the seven descriptions that still
  had only historical live evidence: Scenarios 14 and 16-21. Each has a current
  title, intermediate body, and stable final-frame capture without broken
  glyphs, reset, freeze, or input collision.
- The live playback preserves the static Japanese-source corrections: Scenario
  14 identifies Baldea and the holy sword without the invented Jessica action;
  Scenario 16 reaches Leon and the Black Dragon Knights beyond the gate;
  Scenario 17 retains Bernhardt at the throne; Scenario 18 identifies the other
  Liana controlling monsters; Scenario 19 is the ship-seizure operation;
  Scenario 20 starts battle after laying a boarding plank; and Scenario 21 says
  Chaos is sealed in Velzeria rather than living there.
- These seven descriptions are `progressed_current`, matching the conservative
  two-second sampling rule used for the other relocated records. Scenario 1 is
  the only `verified_current` description because every dynamic-name context
  and the complete automatic scroll were captured there. All other Scenarios
  2-31 now have current production playback evidence as
  `progressed_current`; no description remains historical or pending.

### Current C1C9 Scenario 22 Opening And First Turn (2026-07-17)

- The Japanese source for three Scenario 22 opening records was reviewed again.
  `0x1AB208` (`二人は別人だったのか？！`) is now
  `둘은 다른 사람이었나?`; `0x1AB248`
  (`闇の剣を光の巫女が封印した…。納得できる話じゃな。`) is now
  `어둠의 검은 빛의 무녀가 봉인했군… 말이 되는군.`; and
  `0x1AB2A4` (`封印を解き、闇の力をそそぎ込むのが役めでしょう。`) is
  now `봉인을 풀고 어둠의 힘을 불어넣는 역할이겠죠.`. The previous
  wording at `0x1AB248` invented a later unsealing action, while the previous
  `0x1AB2A4` incorrectly described work after the seal rather than breaking it.
- Do not repeat the rejected long variants blindly. The first `0x1AB208`
  revision required 16 words in an original 13-word record, and the first
  `0x1AB248` revision required 31 words in an original 28-word record. The
  final source-faithful forms above fit the original capacities and build
  without relocating these fixed event records.
- The resulting production ROM is checksum `C1C9`, has 859 custom glyphs in
  the unchanged `0x7000..0x735B` range, and rebuilds deterministically to
  SHA-256 `48c1642e06351026b8eea955f8deb0f6607ed8d8b6141c600daed096224dea12`.
  A detached `041b03c` build reproduced `C7AB`. Direct comparison found only
  96 changed bytes: the two checksum-header bytes at `0x18E..0x18F` and the
  three reviewed event-record ranges around `0x1AB208`, `0x1AB248`, and
  `0x1AB2A4`. No description, glyph, UI, class, or preparation bytes changed,
  so the immediately preceding C7AB description and preparation evidence is
  valid for the current source.
- Fresh C1C9 playback reached the preparation screen, deployed, and captured
  all fourteen opening confirmations at a 3.2-second interval. The corrected
  lines render completely in `c1c9_s22_opening_06.png`, `_08.png`, and
  `_10.png`; `_14.png` is a stable Elwin command menu. The slower interval
  avoids treating a partially drawn text frame as a broken glyph.
- The complete selectable preparation roster is 엘윈/파이터, 헤인/워록,
  쉐리/파이터, 아론/파이터, 키스/호크나이트, 레스터/크로코나이트,
  제시카/세이지, and 스코트/파이터. An enlarged nearest-neighbor crop
  resolved the small Keith label as `호크나이트`; it was initially misread as
  `크루세이더`. The later source-table review confirms Lester is
  `크로코나이트`; verify tiny class text against the original class ID and an
  enlarged crop before changing source data.
- `c1c9_s22_conditions.png` shows victory `적 전멸` and defeat
  `주인공 사망`/`제시카 사망`. The no-action first turn captured all four
  Bozel/Egbert dialogue pages, enemy and allied movement, `TURN 2`, and a valid
  Elwin command menu after 30 confirmations. No Japanese text, blank page,
  reset, or freeze appeared. Scenario-specific battle presentation, later
  turns, completion, and conditional branches remain pending.

### Current 544B Scenario 23 Preparation, Opening, And First Turn (2026-07-17)

- Current playback followed both `지휘관배치` pages rather than treating the
  first five visible rows as the full roster. The nine selectable commander
  and class pairs are `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`,
  `아론/파이터`, `키스/호크나이트`, `레스터/크로코나이트`,
  `스코트/파이터`, `리아나/클레릭`, and `라나/클레릭`. Equipment panels
  were inspected without confirming or changing any equipment.
- Attempting to deploy before assigning positions exposed the shared warning
  `지휘관배치가 끝나지않았습니다`. The fixed 16-token record cannot simply
  insert spaces into that sentence. Its screen-local glyph slots and tokens
  now render the shorter, readable `지휘관 배치 미완료입니다` instead.
  `544b_s23_arrange_warning.png` verifies the exact live result, and
  `tests/test_arrange_warning.py` locks the 16-token layout and four blank
  slots.
- Japanese page `0x1AE9F6` is `エルウィン達か？ 急ぐぞ！ヤツらより先に探し
  出すのだ！`. The previous dynamic form `{0001}들인가?` rendered the
  unnatural `엘윈들인가?`. The capacity-safe current form is
  `{0001} 일행인가? 놈들보다 먼저 찾아야 해!`; live frame
  `544b_s23_opening_14.png` confirms `엘윈 일행인가?` with the default name.
  A regression rejects the former suffix.
- The production build is checksum `544B` with the unchanged 859-glyph
  `0x7000..0x735B` bank and deterministically rebuilds to SHA-256
  `e57756fb0c7e7adc0d8bd08686d707fafc129ca872e83a9fcba707f7f39029fd`.
  A detached build of commit `2f0f8cc` reproduced `C1C9`; direct comparison
  found only 60 changed bytes in the checksum header,
  arrangement-warning local glyph/tokens at `0xA2B9C`/`0xA2C2E`, and the
  Scenario 23 event record at `0x1AE9F6`. No global glyph IDs, description
  resources, classes, or other UI records changed.
- Automatic deployment and all eighteen opening confirmations reached a valid
  Elwin command menu. Conditions are victory `로드 소지자 하단 도착` or
  `적 전멸`, and defeat `로드 탈취 후 상단 도주` or `주인공 사망`. The
  no-action first turn reviewed four Laird/imperial-commander dialogue pages,
  all movement, `TURN 2`, and a valid Elwin command menu after 39 confirmations.
  No Japanese text, broken name/class/status glyph, blank page, reset, or freeze
  appeared. Scenario-specific battle presentation, later turns, completion,
  and conditional branches remain pending.

### Current 544B Scenario 24 Preparation, Opening, And First Turn (2026-07-17)

- Both arrangement pages and the complete nine-commander equipment selector
  were inspected. The roster and class pairs are identical to Scenario 23:
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `스코트/파이터`,
  `리아나/클레릭`, and `라나/클레릭`. No equipment was confirmed or
  changed. Small labels were checked from enlarged nearest-neighbor sheets.
- Automatic deployment and all nineteen opening confirmations review the
  Langrisser release sequence and dialogue from Liana, Lana, Keith, Sherry,
  Bernhardt, Scott, Hein, Lester, and Elwin. Bernhardt's two-page challenge
  correctly continues as `놈들을 쓰러뜨리면 벨제리아성으로 오게. 그때는
  내가 직접 상대해 주지!`; it is not a truncated first page. The sequence
  reaches a valid Elwin command menu without reset or a blank page.
- `544b_s24_conditions.png` shows victory `적 전멸` and defeat `주인공
  사망`. The no-action first turn reviews both Vampire Lord dialogue pages,
  all unit movement, `TURN 2`, and a valid Elwin command menu after 38
  confirmations. The portrait status line visibly reads `뱀파이어로드` for
  both name and class and matches the original fixed-placement assertion in
  `tests/test_scenario_data.py`; do not misread the small first syllable as a
  broken `스` glyph.
- No Japanese text, broken commander/class/status glyph, blank page, reset, or
  freeze appeared. Scenario-specific battle presentation, later turns,
  completion, and conditional branches remain pending.

### Current 9C1F Scenario 25 Opening And Battle Class Fix (2026-07-17)

- Six Scenario 25 opening records were corrected against the Japanese source.
  The final meanings are `폐하를 이계로 날려 보낸 어리석은 마술사여.`,
  `알하자드의 힘을 너무 얕봤구나.`, `기다려라, {0014}. 난 비겁하게 인질을
  쓰지 않는다.`, `후후후… 무르군, {000D}. 하지만 그게 네 장점이지.`,
  `놈들을 맞을 준비를 하지. 헛수고로 끝나면 좋겠군.`, and `{000E}가
  알하자드의 힘을 풀어 세상에 큰 이변이 닥치려 해!`. Do not restore the
  rejected `이세계로`, `하지 마라`, `고지식하군`, `헛수고가 아니길`, or
  conditional `힘을 풀면` variants. Build 6F37 captured all 28 opening pages
  in `6f37_s25_opening_01.png` through `_28.png` without clipping, Japanese
  residue, reset, or freeze.
- Runtime RAM in the BlastEm GST starts at file offset `0x2478`. Scenario 25's
  live group 9 is the event-spawned Jessica: class ID 9, original
  `ソーサラー`, Korean `소서러`, LV5, AT29, and DF17. The hidden fixed
  placement record is a different Warlock Jessica and must not be used to name
  the live unit. Preserve this distinction for the scenario editor.
- The broken battle labels were not caused by overwritten extension glyph
  resources. In the exact paused A2A7 GST, tiles `0x3AC` (`얄`), `0x444`
  (`가`), and `0x3AD..0x3AF` (`소서러`) and all six extension resource
  segments were byte-exact. Screenshot matching instead proved that the battle
  plane received `0xAC`, `0x44`, and `0xAD..0xAF`.
- Two failed slot experiments should not be repeated. Putting `소서러` at
  `0x3F6..0x3F8` produced battle graphics because that escape-bank area is not
  stable in battle. Moving it to stable `0x3AD..0x3AF` fixed the map status but
  did not fix the battle label by itself. The latter assignment remains useful
  for stable storage, but it requires the renderer fix below.
- The actual battle path is the localized direct-map renderer at `0x2B7800`,
  called from `0x1B546`, `0x1CBA6`, and `0x1CBBC`. Its post-lookup store at
  `0x2B7862` used `AND.W #$00FF,D1`, truncating every full extension tile ID.
  The builder now keeps the table-index mask but removes the two masks after
  tile lookup. `test_direct_map_renderer_preserves_full_extension_tile_ids`
  prevents the truncation from returning.
- Production 9C1F has SHA-256
  `b88a0150b3a3bae69a31048e2da4de12b054f46419e9a26405be96563b91c51e`.
  Current captures `9c1f_s25_battle_paused.png` through
  `9c1f_s25_battle4_paused.png` verify `파이터`, `워록`, `로얄가드`, and the
  dynamic Jessica's `소서러`; the high-tile syllables are intact. The same
  no-action first turn continued through the defeat ending cinematic without
  reset or freeze. It was over-confirmed rather than preserving every distinct
  dialogue page, so the turn is `progressed_current`, not `verified_current`.
- BlastEm was stopped after verification. A paused GST copied over another
  running session's quicksave caused BlastEm to exit; use a fresh selector run
  for this regression instead of reusing `a2a7_s25_battle_paused.gst`.

### Current ECA0 Scenario 26 Source Review And First Turn (2026-07-17)

- All 102 Japanese physical event pages were rendered and reviewed. Four
  Korean records were corrected against the Japanese source: `0x1B2A48` now
  describes the continent's foremost military state, `0x1B3394` identifies
  Death Tower as Egbert's magic tower that strengthens his forces,
  `0x1B34FC` retains the source's explicit `지옥`, and `0x1B3538` uses the
  natural `스승님과`. Do not restore `대륙 규모 군사국가`, the former vague
  Death Tower wording, softened `저승`, or `스승님께`.
- The first `0x1B3394` rewrite required 38 words in a 36-word physical page.
  The accepted capacity-safe sentence is `싸움은 데스타워에서 한다. 우리
  힘을 키우는 내 마법탑이지.` Never enlarge that record in place; event
  page capacity and continuation controls must remain intact.
- Both preparation pages and all ten class panels were checked. The complete
  roster is `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`,
  `키스/호크나이트`, `레스터/크로코나이트`, `스코트/파이터`,
  `리아나/클레릭`, `라나/클레릭`, and `제시카/소서러`. Representative
  captures include `eca0_s26_arrange_roster1.png`, `_roster2.png`,
  `_equipment_keith2.png`, and `_equipment_jessica.png`.
- Automatic deployment reached the map, and all ten opening dialogue pages
  were captured as `eca0_s26_opening_clean_01.png` through `_10.png` without
  Japanese residue, broken glyphs, clipping, reset, or freeze. Conditions are
  victory `에그베르트 격파` and defeat `주인공 사망`.
- The complete no-action first turn was captured in
  `eca0_s26_turn1_actual_01.png` through `_50.png`. It includes dialogue from
  Jessica, imperial commanders, Hein, Aaron, Egbert, and Elwin, then reaches
  the expected `GAME OVER`; there is no Turn 2 on this losing path. The key
  dialogue frames were reviewed and contain no Japanese or corrupted
  name/class/status glyphs. Scenario-specific battle presentation and a
  successful-clear route remain pending.
- Two input-state mistakes are documented to prevent repetition. Browsing the
  arrangement roster changes the focus, so running the clean deployment key
  sequence afterward can enter equipment instead. Restart or restore the
  initial preparation focus before automatic deployment. Returning from the
  conditions page also does not guarantee the Start-menu cursor is on turn
  end; an assumed cursor position entered save and 70 confirmations stayed in
  its prompt. Reopen Start, identify the selected row, then move explicitly to
  turn end.
- Production ECA0 has SHA-256
  `752622f2c7b424fc8e8ba3a38f316d39a8d30c8575b927040f80c369518b976c`.
  BlastEm was stopped after the current-build verification.

### Current ECA0 Scenario 27 Opening And First Turn (2026-07-17)

- The built-in selector entered Scenario 27 on production ECA0 and the
  detector stopped at preparation after eleven description confirmations.
  The preparation panel retains the verified five-commander roster
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`, and
  `키스/호크나이트`; the later Scenario 26-only Liana/Lana/Jessica rows do
  not belong to this roster.
- Clean automatic deployment and twenty individually retained opening frames
  reached Elwin's `이동/공격/치료/명령` panel. Bernhardt, Lana, Liana,
  Sherry, Elwin, and Aaron dialogue, dynamic names, classes, and status text
  are Korean and intact. Current evidence is
  `eca0_s27_opening_01.png` through `_20.png`.
- `eca0_s27_conditions.png` verifies victory `베른하르트 격파` and defeat
  `주인공 사망`. Closing the conditions screen resets the Start-menu cursor
  to `저장`; move down four rows from that visible state to choose turn end.
  The first attempt assumed the cursor remained on conditions and therefore
  did not leave the page. This was an input-state mistake, not a ROM failure.
- The full no-action first turn retained 55 frames. The only waiting dialogue
  pages are Bernhardt's two arguments for unification by force and Elwin's
  defeat line; all are clean Korean. Enemy movement then defeats the party and
  reaches the expected `GAME OVER` on Turn 1 without reset or freeze.
- One automatic sample caught the all-black battle transition, but no current
  battle-label frame was retained. Do not promote this run to direct battle-UI
  verification; keep the existing production-derived 3590 probe for that
  surface. A successful normal clear and conditional routes are still
  pending. BlastEm was stopped after verification.

### Current ECA0 Secret Scenario X1 Runtime (Selector 28, 2026-07-17)

- Selector record 28 intentionally opens on-screen `시나리오 X1 / 근육의
  신전`; this is original numbering, not a localization offset. Ten detector
  frames include all nine scrolling description states and the preparation
  endpoint. The full description is clean Korean, so this surface is now
  `verified_current` rather than merely sampled.
- The battle status bar says `SCENARIO ?1`, not `SCENARIO X1`. This initially
  looked like a broken Korean tile, but a direct Japanese-ROM run retained
  `jp_s28_after_battle.png` and proves the source uses the same question-mark
  marker. The `?1` pixel rectangle is byte-for-byte identical to ECA0 frame
  `eca0_s28_turn1_61.png`. Secret-stage titles use `X1/X2/X3`, while their
  battle status rows use `?1/?2/?3`; do not overwrite the source marker.
- The preparation screen contains the same five selectable commanders as
  Scenario 27. Automatic deployment was run from the initial preparation
  focus and reached the X1 map without entering equipment or hire menus.
- Eighteen dialogue pages in the twenty retained opening frames verify
  `바란`, `아돈`, `삼손`, 레스터, 아론, 쉐리, and 제시카. Their live
  names, classes, portrait status labels, and all bodybuilding dialogue render
  in Korean without clipping or corrupted high extension tiles. The command
  detector stops at a valid Elwin panel after frame 20.
- Conditions are victory `적 전멸` and defeat `주인공 사망`. The no-action
  first turn contains Baran's two instruction pages, then all enemy/allied
  movement. Frame 62 visibly reaches `TURN 2` and frame 64 reaches Elwin's
  intact command panel. No Japanese text, blank page, reset, or freeze
  appeared.
- No battle-label frame was retained in this run, so X1 battle UI remains
  pending rather than inferred from map movement. Completion and conditional
  conversion/item branches also remain pending. BlastEm was stopped after
  verification.

### Current ECA0 Secret Scenario X2 Runtime (Selector 29, 2026-07-17)

- Selector record 29 intentionally opens `시나리오 X2 / 디레스 해협의
  격전`. All nine scrolling description states were retained and reviewed,
  from the small-ship pursuit through the Rayguard commander's revenge for
  Imelda. The tenth detector frame is the normal five-commander preparation
  screen, so the description is now `verified_current`.
- As in the Japanese source, the battle status row uses `SCENARIO ?2` even
  though the description title uses `X2`. This is not a `록` glyph collision.
- Automatic deployment reaches the naval map. Six opening dialogue pages
  verify `세이갈/드래곤로드`, `폴거/드래곤로드`, `키스/호크나이트`,
  아론, and 엘윈 status labels without Japanese residue or broken extension
  glyphs. The command detector reaches Elwin after nine frames.
- Conditions are victory `적 전멸` and defeat `주인공 사망`. The long
  no-action first turn retains 95 frames. Its six waiting dialogue pages cover
  폴거, 세이갈, 엘윈, 스코트, and 키스; frame 93 is `TURN 2` and frame 95
  is Elwin's valid command menu. No reset, freeze, or blank page appeared.
- The automatic run did not retain a readable battle-label frame, so X2
  battle UI remains pending. Full completion and conditional battle/death
  branches also remain pending. BlastEm was stopped after verification.

### Current ECA0 Secret Scenario X3 Runtime (Selector 30, 2026-07-17)

- Selector record 30 intentionally opens `시나리오 X3 / 마룡의 둥지`.
  Eight scrolling description frames cover the cave discovery and mysterious
  cursed girl through the complete final sentence. Frame 9 is the normal
  five-commander preparation endpoint, so the description is now
  `verified_current`.
- As in the Japanese source, the battle status row uses `SCENARIO ?3` while
  the description title uses `X3`. Preserve the question-mark marker.
- Automatic deployment and 25 retained opening frames reach Elwin's command
  panel. Eighteen dialogue pages verify 엘윈, 쉐리, 아론, 헤인, 키스,
  `미나`, 레스터, and 리아나 names plus the live class/status labels. No
  Japanese text, broken high extension glyph, clipping, reset, or freeze
  appeared.
- Conditions are victory `미나 격파` and defeat `주인공 사망`. On the
  no-action first turn enemy movement defeats Elwin; frame 16 shows the clean
  Korean line `젠장! 왜 이런 곳에…`, and frame 17 reaches the expected
  `GAME OVER` without a reset.
- The user's later keyboard input occurred after frame 17 was retained and
  after BlastEm had been stopped, so it did not affect this evidence. Direct
  battle-label evidence, a successful clear, and conditional branches remain
  pending.

### Current ECA0 Secret Scenario X4 Runtime (Selector 31, 2026-07-17)

- Selector record 31 intentionally opens `시나리오 X4 / 죽음의 탑`. All ten
  scrolling description frames were retained and reviewed through the final
  sentence about breaking through the tower. Frame 11 is the normal
  five-commander preparation endpoint, so the description is now
  `verified_current`.
- The battle status row displays `SCENARIO ?4`, following the source secret-
  stage convention already proved directly for `?1`. The patterned block at
  the far left of the row is the current terrain-tile thumbnail and the
  adjacent `10%` is its terrain modifier. The thumbnail can resemble `록` at
  native resolution, but it is map graphics rather than a Korean text slot;
  do not patch either it or the intentional question-mark stage marker.
- Automatic deployment reaches the Death Tower map. Six opening dialogue
  pages verify `에그베르트`, `나라`, `베른하르트`, and `엘윈`, along with
  live class and status labels, without Japanese residue, broken high
  extension tiles, clipping, reset, or freeze. Evidence is retained in
  `eca0_s31_opening_01.png` through `_12.png`.
- Conditions are victory `적 전멸` and defeat `주인공 사망`. Ending the turn
  without acting immediately reaches the expected `GAME OVER` because the
  protagonist is defeated; `eca0_s31_turn1_01.png` preserves the endpoint.
- A Japanese-ROM comparison session was also opened while investigating the
  status row. The first automatic deployment attempt from its post-description
  focus entered Aaron's equipment screen, so it is not valid X4 battle-row
  evidence and must not be promoted as such. The direct Japanese `?1` proof
  and the source-wide secret-stage convention remain the authoritative marker
  evidence. Scenario-specific battle presentation, a successful clear, and
  conditional branches remain pending. BlastEm was stopped after review.

### Superseded DAC0 Scenario 2 Loren Font-Bank Regression (2026-07-17)

- Production ECA0 exposed a real common byte-UI regression: Scenario 2's fixed
  NPC record is `로렌/하이로드`, but the map status row displayed only `로`.
  The localized pointer at name ID `0x26` was correct (`00 09 00 A2 FF`), and
  compressed resource 435 contained the correct rendered `렌`. The missing
  syllable was therefore a runtime VRAM-load failure, not a name-table error.
- The original final full-extension bank `5D8..5F3` is not retained after the
  preparation transition. Making only the sixth resource request synchronous
  also failed to populate the live tile, and moving it to `348..35B` visibly
  collided with map graphics. These are rejected experiments; do not repeat
  either approach.
- DAC0 kept all six resource requests on the normal queued DMA path and moved
  the final 28-tile bank to `580..59B`. In the early-dialogue state
  `captures/analysis/dac0_s02_first_dialogue.gst`, every used tile in that bank
  exactly matches its rendered resource bytes, including `렌` at tile `590`.
  `captures/run/dac0_s02_loren_cursor.png` and
  `dac0_s02_loren_popup.png` live-verify complete `로렌/하이로드` text in the
  bottom status row and commander popup. The enlarged evidence is
  `captures/analysis/dac0_s02_loren_status_x6.png` and
  `dac0_s02_loren_popup_x6.png`.
- The Scenario 2 run reached the command menu after 70 retained opening
  confirmations without reset or freeze. Save-state RAM comparison identified
  the live cursor at `(5,19)`; moving to the original fixed-record coordinate
  `(19,19)` selected Loren without relying on visual guessing. The relevant
  original editor record remains locked by `tests/test_scenario_data.py`.
- `tests/test_name_entry_resources.py` now locks the stable final segment and
  Loren's `렌 -> 0x590` mapping. The intermediate synchronous-loader builds
  `6CA0`, `E760`, and `5AC0` are not release candidates; production DAC0 is the
  first visually accepted runtime result for this regression. Later fresh
  command-time evidence proved `580..59B` is overwritten by map graphics, so
  this acceptance is superseded by the 489B section below.

### Superseded DAC0 Scenario 2 Status-Banner Recheck (2026-07-18)

- Loren is also still open from the user's visual review. DAC0 fixed the
  missing VRAM tile, and the live bytes now exactly match the generated `렌`
  tile, but the generated 8x8 shape reads too much like a lone corner/`ㄴ` at
  native size. Treat this as a glyph-legibility defect, not as a completed name
  fix. Add a deliberate byte-UI bitmap override for `렌`, rebuild, and require
  both the bottom status row and commander popup to read unambiguously as
  `로렌` before closing the regression.
- The user still reports the phase/status banner as `SCENAR록O`, so this issue
  is open even though the earlier rapid 30-frame crop was byte-identical across
  samples and was initially read as the stylized ASCII `I` in `SCENARIO 2`.
  Do not close it from visual inference alone. Retain the exact current banner,
  capture the same normal Scenario 2 banner from the Japanese ROM, compare the
  `SCENARIO` glyph rectangle pixel-for-pixel, and inspect the live tile ID/VRAM
  bytes before deciding whether it is an ASCII-font shape or a collision with
  the relocated Korean bank.
- A later first-turn attempt is rejected evidence. A manually launched BlastEm
  remained beside the selector-managed process; direct input and capture could
  address different windows, and 99 retained frames were the title demo rather
  than Scenario 2. Never promote `dac0_s02_turn1_*.png`. Before every runtime
  check, require exactly one non-zombie BlastEm process and terminate a process
  that survives normal `SIGTERM` before launching the next window.

### Current 489B Scenario 2 Loren And SCENARIO Resolution (2026-07-18)

- Fresh build FCE0 disproved the earlier DAC0 command-time assumption. It
  entered Scenario 2 normally from a reconstructed manual slot, reached the
  real command menu, and moved from cursor `(5,19)` to Loren at `(19,19)`.
  `captures/analysis/fce0_s02_loren_live.gst` shows tile `0x590` contains map
  graphics rather than the generated `렌`; the early DAC0 GST had only proved
  that the bank existed before the map finished loading.
- Reloading the complete extension font after the stock map loader is rejected.
  Checksum 9ACE produced the visibly corrupted map in
  `captures/run/9ace_s02_deploy_start.png` because it overwrote several live
  map banks. Reloading only the final `5D8..5F3` segment at the same early hook
  preserved graphics but the segment was cleared again before command time.
  Do not repeat either loader placement.
- The accepted implementation keeps `5D8..5F3` and requests only its compressed
  resource from the localized map-info renderer, immediately before the lower
  status row consumes localized name/class tiles. The Scenario 2 GST VDP
  registers resolve Plane A/B, Window, and SAT to `C000/E000/D000/F000`; none
  reference this 28-tile range. Current quicksave bytes exactly match both
  rendered tiles: `록 -> 0x5D8` and manual-bitmap `렌 -> 0x5E9`.
- `captures/run/489b_s02_loren_popup.png` live-verifies `로렌/하이로드`, and
  the same run reached the real command menu after the full opening without
  reset, freeze, or map corruption. The explicit 8x8 `렌` bitmap is locked in
  `tests/test_name_entry_resources.py`; it no longer depends on the ambiguous
  Galmuri7 rasterization.
- The user's `SCENAR록O` report was correct. Exact comparison of
  `captures/run/c805c_s02_arrangement.png` against Japanese
  `captures/run/jp_s02_arrangement.png` found 29 differing pixels only in the
  `I` rectangle. Current code had assigned Korean `록` to base ASCII tile
  `0x49`. Build 489B preserves `0x49`, assigns name-entry `록` to escape code
  `0xF6`, and assigns battle name/class `록` to stable tile `0x5D8`.
  `captures/run/489b_s02_arrangement.png` crop `(18,168,98,226)` is now pixel-
  identical to the Japanese capture. The byte-font regression test also
  requires every non-private ASCII tile, including `I`, to remain unchanged.
- `tools/run_blastem_sequence.py launch-only --manual-slot-gst ...` is the
  reproducible Scenario 2 entry path. GST file offset `0x2478` contains work
  RAM; concatenate RAM `A49C+154`, `BD6E+002`, and `C7F2+050`, write the 1A6
  bytes into SRAM manual slot 1, store the big-endian word sum plus one at
  `+1A6`, and set valid flag bit 1 at SRAM `0x1FF0`. This avoids direct loading
  of cross-build GSTs and the timing-sensitive scenario-select cheat.
- `running_blastem_pids` now reads `/proc`, ignores zombies, and termination
  escalates from SIGTERM to SIGKILL with verification. `launch-only` preserves
  the `load-screen` runtime instead of deleting its recovered save. These paths
  are covered by `tests/test_blastem_sram_migration.py`.
- The same 489B session ended the first player turn without moving units and
  retained `captures/run/489b_s02_turn1_00.png` through `_52.png`. It covers
  Loren, imperial-commander, and commander dialogue, all NPC/enemy movement,
  two battle presentations, and return to a valid Elwin command menu. The
  dialogue is fully Korean, both battle panels retain ordinary `AT/DF` labels
  instead of the old `록AT록` corruption, and no reset or freeze occurs.
  Scenario 2 `battle_ui` and `turn_events` are now `verified_current`.
- A subsequent exhaustive opening review retained 79 frames across
  `489b_s02_opening_01.png` through `_61.png` and
  `489b_s02_opening2_01.png` through `_18.png`. Every text-bearing frame is
  Korean; the sequence covers deployment, Loren and imperial-commander pages,
  map transitions, and the real Elwin command menu with intact names, classes,
  status labels, and graphics. Scenario 2 `opening_events` is therefore also
  `verified_current`.
- Production 489B also retained the complete Scenario 2 description as
  `489b_s02_description_current_00.png` through `_22.png`. The 23 retained
  states comprise the route map, 21 text-bearing scrolling frames, and the
  preparation endpoint. They cover Elwin's party reaching Loren's residence,
  accepting Liana's escort, and Zorum's approaching force. Every line is Korean
  with normal spacing and no clipping, broken glyph, or Japanese residue, so
  Scenario 2 `description` is now `verified_current`.
- This run exposed a scenario-selector automation assumption. The reconstructed
  manual slot starts with word `0x0002`, so the selector initially points to
  Scenario 2; the old helper always sent `scenario_number - 1` Down inputs and
  therefore entered Scenario 3 for a requested Scenario 2. The helper now
  validates the manual-slot flag/checksum, reads the saved scenario word, and
  moves relative to it. Target 2 from saved Scenario 2 sends no movement;
  target 1 sends one Up. Unit tests lock both directions and the SRAM parser.
- The corrected selector then targeted Scenario 3 from saved Scenario 2 with
  exactly one Down input. `489b_s03_description_current_00.png` through
  `_15.png` retain the route map, all 14 text-bearing scrolling frames, and the
  preparation endpoint. The full `조름의 반격` description is natural Korean
  with intact spacing and no clipping, broken glyph, or Japanese residue.
  Scenario 3 `description` is now `verified_current`.
- The same relative selector targeted Scenario 4 with two Down inputs.
  `489b_s04_description_current_00.png` through `_14.png` retain the route map,
  all 13 text-bearing frames of `빛의 신전`, and the preparation endpoint. The
  complete description preserves the mysterious knight, Vargas, the Temple of
  Light, and Rayguard Black Dragon Sorcerer terminology without Japanese text,
  clipping, broken glyphs, or abnormal spacing. Scenario 4 `description` is now
  `verified_current`.
- Scenario 5 followed with three Down inputs from the saved Scenario 2.
  `489b_s05_description_current_00.png` through `_14.png` retain the route map,
  all 13 text-bearing `짐승의 포효` frames, and the preparation endpoint. The
  damaged Temple of Light, Morgan's threat to nearby residents, and Sherry's
  pursuit are complete Korean with no Japanese residue, clipping, broken
  glyph, or abnormal spacing. Scenario 5 `description` is now
  `verified_current`.
- Scenario 6 followed with four Down inputs from the saved Scenario 2.
  `489b_s06_description_current_00.png` through `_17.png` retain the route map,
  all 16 text-bearing `노병 아론` frames, and the preparation endpoint. Morgan
  reaching the village, the fleeing residents, and the lone elderly swordsman
  are complete Korean with no Japanese residue, clipping, broken glyph, or
  abnormal spacing. Scenario 6 `description` is now `verified_current`.
- Scenario 7 followed with five Down inputs from the saved Scenario 2.
  `489b_s07_description_current_00.png` through `_15.png` retain the route map,
  all 14 text-bearing `깨어나는 망자` frames, and the preparation endpoint.
  Aaron's arrival, the quiet night, the cemetery ritual, and the evil presence
  are complete Korean with no Japanese residue, clipping, broken glyph, or
  abnormal spacing. Scenario 7 `description` is now `verified_current`.
- Scenario 8 followed with six Down inputs from the saved Scenario 2.
  `489b_s08_description_current_00.png` through `_26.png` retain the route map,
  all 25 text-bearing `하늘의 다리` frames, and the preparation endpoint. The
  Blue Dragon Knights' advance on Kalxath, Sherry's return, the gorge bridge,
  and the forced breakthrough are complete Korean with no Japanese residue,
  clipping, broken glyph, or abnormal spacing. Scenario 8 `description` is now
  `verified_current`.
- Scenario 9 followed with seven Down inputs from the saved Scenario 2.
  `489b_s09_description_current_00.png` through `_21.png` retain the route map,
  all 20 text-bearing `칼자스 성 공방전` frames, and the preparation endpoint.
  The gorge crossing, Blue Dragon Knights, Leon/Laird elite force, and siege
  opening are complete Korean with no Japanese residue, clipping, broken
  glyph, or abnormal spacing. Scenario 9 `description` is now
  `verified_current`.
- Scenario 10 initially exposed `마법 물건 다크로드`, an awkward literal
  translation. Japanese-ROM playback retained in
  `jp_s10_description_00.png` through `_32.png` shows the exact source
  `ダークロッドとよばれるマジックアイテム`, so the production source now reads
  `다크로드라는 마법 도구가 필요하다는 사실도 알게 되었다.` This avoids
  adding the otherwise new deferred description glyph `템` and preserves all
  existing glyph IDs. The first rebuild also exposed a centered one-character
  `수` line; rewrapping the next
  sentence as `다크로드만 손에 넣으면 / 제국의 야망을 막을 수 있었다.` removes
  it.
- Production D3E8 `d3e8_s10_description_final_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `랄강의 수호자` frames, and the
  preparation endpoint. The corrected item wording and every remaining line
  fit naturally without Japanese residue, clipping, broken glyph, or abnormal
  spacing. Scenario 10 `description` is now `verified_current`.
- Production checksum is `D3E8`, SHA-256
  `f9e60ab0d3aedd160821ff5f810ce367328376f047b8b60fe25847e76e3325b7`.
  All 236 unit tests pass, and the regenerated compressed-resource inventory
  records the unchanged byte-font hash. BlastEm was left on the Scenario 10
  preparation screen for visual review.
- Scenario 11 was compared with the Japanese-ROM render
  `text_scenarios_10_mapped_040000_jp2bpp16.png`. The source explicitly says
  Egbert secretly spread traps while waiting for the opportunity, so the
  awkward `그때를 노리고 함정을 파 두었다` is now
  `그때를 노려 몰래 함정을 파 두었다` in both the production override and
  legacy scenario source. An initial `함정을 쳐 두었다` revision added one
  deferred description glyph and shifted 63 global direct-string token
  records. Reusing `파` removed that shift completely while retaining the
  source meaning; the regenerated direct inventory has no diff.
- Production 466A `466a_s11_description_final_00.png` through `_14.png`
  retain the route map, all 13 text-bearing `불길 속에서` frames, and the
  preparation endpoint. All text is natural Korean without Japanese residue,
  clipping, broken glyphs, or abnormal spacing. Scenario 11 `description` is
  now `verified_current`.
- Production checksum is `466A`, SHA-256
  `d930b01e09093a2b4c0acee5f540cb916100ab585121286684b3d0e80507a391`.
  BlastEm was left on the Scenario 11 preparation screen.
- Scenario 12 was compared with the Japanese-ROM render
  `text_scenarios_11_mapped_040000_jp2bpp16.png`. The Korean description
  preserves the cleverly hidden cave entrance, Dark Rod shrine, unexpectedly
  absent Egbert, and ancient guardians waiting inside. Initial 466A playback
  exposed `입구가` centered on a line by itself. Replacing `교묘하게` with the
  equally accurate shorter `교묘히` makes
  `지나칠 만큼 교묘히 숨겨진 입구가` fit one line. No description glyph was
  added and the regenerated direct-string inventory remains unchanged.
- Production D355 `d355_s12_description_final_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `성지 레이텔` frames, and the
  preparation endpoint. All text is natural Korean without Japanese residue,
  clipping, broken glyphs, or abnormal spacing. Scenario 12 `description` is
  now `verified_current`.
- Production checksum is `D355`, SHA-256
  `334e49ae5ff3f0bbc6526ddba8db5b4488ac03aa1e6f373b1db36e11887f9118`.
  BlastEm was left on the Scenario 12 preparation screen.
- Scenario 13 was compared with the Japanese-ROM render
  `text_scenarios_12_mapped_040000_jp2bpp16.png`. The Korean text preserves
  the ancient guardians' defeat, Egbert stealing the Dark Rod by magic, his
  teleport toward Liana at Kalxath Castle, the party's urgent return, and
  Vargas waiting with the Fire Dragon Corps. No translation or layout change
  was required.
- Production D355 `d355_s13_description_current_00.png` through `_15.png`
  retain the route map, all 14 text-bearing `염룡병단과의 결전` frames, and
  the preparation endpoint. All text is natural Korean without Japanese
  residue, clipping, broken glyphs, or abnormal spacing. Scenario 13
  `description` is now `verified_current`. BlastEm was left on the Scenario 13
  preparation screen.
- Scenario 14 was compared with the Japanese-ROM render
  `text_scenarios_13_mapped_040000_jp2bpp16.png`. It confirms that ancient
  Baldia sleeps at the bottom of a deep lake, Langrisser is enshrined in the
  castle depths, and the Blue Dragon Knights seek the same objective. The
  Korean meaning and canonical `발디아` spelling were already correct, but
  source lines wider than the runtime window left `다스렸던`, `드러낸`, and
  `전설의` isolated. Explicit rewrapping removes all three. A trial wording
  change from `다스렸던` to `다스리던` removed the otherwise unique `렸`
  description glyph and shifted eight global direct-string records, so the
  original wording was retained; the final direct inventory has no diff.
- Production CE27 `ce27_s14_description_final_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `성검 랑그릿사` frames, and the
  preparation endpoint. All text is natural Korean without Japanese residue,
  clipping, broken glyphs, or abnormal spacing. Scenario 14 `description` is
  now `verified_current`.
- Production checksum is `CE27`, SHA-256
  `270ddf0c3346aa46f16dc2830acbc876efb877c6a3123f08aa19a1ef0af7d86c`.
  BlastEm was left on the Scenario 14 preparation screen.
- Scenario 15 was compared with the Japanese-ROM render
  `text_scenarios_14_mapped_040000_jp2bpp16.png`. This exposed a substantive
  omission: the source states that the shortest route requires crossing
  `ローレック河`. The production text now restores the established fallback
  spelling `롤렉 강`. Explicit source rewrapping also removes the isolated
  `불리한` line while retaining every event in the original description.
- Letting `롤렉` enter the early scenario-description pass initially shifted
  121 direct-string records. `TRAILING_SCENARIO_DESCRIPTION_GLYPH_TEXT` now
  excludes both syllables from that pass, preserving their established later
  allocation; retaining the existing `구하려` wording also preserves `려` at
  its original allocation point. The final 783-record direct inventory has no
  token diff and the total custom-glyph count remains 859 (`7000-735B`).
- Production B4C1 `b4c1_s15_description_final_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `빙룡병단장 이멜다` frames, and
  the preparation endpoint. All text is natural Korean without Japanese
  residue, clipping, broken glyphs, or abnormal spacing. Scenario 15
  `description` is now `verified_current`.
- Production checksum is `B4C1`, SHA-256
  `4bd245a30c44e4da9781490e2a7ccef5517922b048fe4b99dd8fe617aa784310`.
  BlastEm was left on the Scenario 15 preparation screen.
- Scenario 16 was compared with the Japanese-ROM render
  `text_scenarios_15_mapped_040000_jp2bpp16.png`. This exposed a substantive
  mistranslation: `大陸の大半` means `대륙 대부분`, not `대륙 절반`.
  The production text now preserves Bernhardt's founding of a nation in one
  generation and conquest of most of the continent. Explicit source
  rewrapping also removes the isolated `황제`, `한`/`세대`, `성에`, and
  `앞에는` lines.
- The changed description length relocates later description pointers inside
  the existing expansion region, which is expected. The regenerated
  783-record direct-string inventory has no token diff, so established global
  glyph IDs for names, classes, and UI remain fixed; the total custom-glyph
  count remains 859 (`7000-735B`).
- Production 3FC0 `3fc0_s16_description_final_00.png` through `_26.png`
  retain the route map, all 25 text-bearing `레이갈드 제도` frames, and the
  preparation endpoint. All text is natural Korean without Japanese residue,
  clipping, broken glyphs, or abnormal spacing. Scenario 16 `description` is
  now `verified_current`.
- Production checksum is `3FC0`, SHA-256
  `9e82439c70338d4f19ff54c25061f96529acea1f58545a3c4902a15b95c4c4d1`.
  BlastEm was left on the Scenario 16 preparation screen.
- Scenario 17 was compared with the Japanese-ROM render
  `text_scenarios_16_mapped_040000_jp2bpp16.png`. The Korean meaning was
  complete, including Bernhardt's warrior-like appearance and the
  evil-smiling man secretly observing the party, but current playback exposed
  `베른하르트.`, `남자가`, and `지켜보았다.` as isolated lines.
- Failed attempt: moving only source newline boundaries produced the identical
  AFD5 ROM. The description encoder normalizes those newlines to spaces and
  performs its own runtime wrapping, so source rewrapping alone cannot control
  this surface. A first sentence rewrite then left `있었다.` isolated and was
  also rejected. The final natural wording uses
  `그가 바로 황제 베른하르트였다.` and
  `그 곁에 남자가 숨어 있었다. 사악한 미소를 띤 그는 일행을 흥미롭게 지켜보았다.`
  to balance the automatic lines without dropping source meaning.
- The visually correct 3564 trial used `곁엔`, but the newly early `엔` glyph
  allocation shifted 62 direct-string token records and was rejected. Reusing
  established glyphs as `그 곁에` restores every prior direct-string ID.
- Production B0E8 `b0e8_s17_description_final_00.png` through `_23.png`
  retain the route map, all 22 text-bearing `황제와 어둠의 왕자` frames, and
  the preparation endpoint. No Japanese residue, clipping, broken glyph, or
  isolated word remains. The regenerated 783-record direct inventory has no
  token diff; later description pointers move only within the existing
  expansion region because the text length changed.
- Production checksum is `B0E8`, SHA-256
  `36402abe18f609a0ff88071129e6d5f482f4837b1e642868d4ab03d86b31d64b`.
  Scenario 17 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.
- Scenario 18 was compared with the Japanese-ROM render
  `text_scenarios_17_mapped_040000_jp2bpp16.png`. The existing Korean covered
  Bozel's pursuit, the monster-attacked village, the laughing girl, and the
  revelation that Liana was controlling the monsters, but current playback
  left `벨제리아로`, `있었다.`, and `마물을` isolated.
- The source now says `마물이 습격한 마을`,
  `한 소녀가 즐겁게 웃었다.`, and
  `마물을 조종하던 이는 리아나였다.` These shorter natural constructions
  preserve every Japanese event while balancing the renderer's automatic
  lines. No new early description glyph is introduced; the regenerated
  783-record direct inventory has no token diff.
- Production 77D0 `77d0_s18_description_final_00.png` through `_15.png`
  retain the route map, all 14 text-bearing `어둠의 공주` frames, and the
  preparation endpoint. No Japanese residue, clipping, broken glyph, or
  isolated word remains. Scenario 18 `description` is now `verified_current`.
- Production checksum is `77D0`, SHA-256
  `485dd695b980382f103c7edea21e8b5770c6ebe4d60990992f7bda157a09c932`.
  BlastEm was left on the Scenario 18 preparation screen.
- Scenario 19 was compared with the Japanese-ROM render
  `text_scenarios_18_mapped_040000_jp2bpp16.png`. The existing Korean fully
  preserves the monster-attacked port, the imperial ship prepared at Mileil
  Harbor, the Dires Strait crossing, the approaching cargo vessel, and Elwin's
  ship-seizure operation. No translation or layout change was required.
- Production 77D0 `77d0_s19_description_current_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `미레일 항구 전투` frames, and
  the preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 19 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.
- Scenario 20 was compared with the Japanese-ROM render
  `text_scenarios_19_mapped_040000_jp2bpp16.png`. The existing Korean fully
  preserves the voyage after Imelda's defeat, the interceptor carrying
  monsters controlled by Bozel, the gangplank between the two ships, and the
  opening of the deck battle. No translation or layout change was required.
- Production 77D0 `77d0_s20_description_current_00.png` through `_17.png`
  retain the route map, all 16 text-bearing `붉게 물든 바다` frames, and the
  preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 20 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.
- Scenario 21 was compared with the Japanese-ROM render
  `text_scenarios_20_mapped_040000_jp2bpp16.png`. The existing Korean fully
  preserves Bozel's ancient defeat, the cursed land where the god of chaos was
  sealed, its appearance beyond the horizon, and the Dark Princess blocking
  the party's landing. No translation or layout change was required.
- Production 77D0 `77d0_s21_description_current_00.png` through `_15.png`
  retain the route map, all 14 text-bearing `마리오네트` frames, and the
  preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 21 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.
- Scenario 22 was compared with the Japanese-ROM render
  `text_scenarios_21_mapped_040000_jp2bpp16.png`. The Korean meaning preserves
  the dark temple, evil idol, sword on the altar, two look-alike maidens,
  Bozel, and the spell announcing Alhazard's imminent release. Initial current
  playback left `제단에는`, `제단`, and `그의` isolated.
- The description builder wraps every source line at 18 characters. The final
  source keeps each intended row within that boundary, restores `어두운 신전`,
  places `검 한 자루` at the altar over two balanced rows, and replaces the
  dangling pronoun with `보젤이 외는 주문은`. The regenerated 783-record
  direct inventory has no token diff.
- Production 42E6 `42e6_s22_description_final_00.png` through `_24.png`
  retain the route map, all 23 text-bearing `알하자드의 부활` frames, and the
  preparation endpoint. No Japanese residue, clipping, broken glyph, isolated
  word, or abnormal spacing remains. Scenario 22 `description` is now
  `verified_current`.
- Production checksum is `42E6`, SHA-256
  `557f48a9461b5e6b40719a42f57257ab37478a3ffba54ec38cef933dc512f41f`.
  BlastEm was left on the Scenario 22 preparation screen.

### Scenario 23 Description Retranslation And Runtime Verification (2026-07-18)

- Scenario 23 was compared directly with Japanese-ROM render
  `text_scenarios_22_mapped_040000_jp2bpp16.png`. Two old Korean statements did
  not match the original: `隙を伺っていたベルンハルト` means Bernhardt was
  watching for an opportunity, not that he was thought dead, and
  `エルフの遺跡` is the elf ruins, not an `엘라드` location.
- The final Korean therefore uses `기회를 노리던 베른하르트` and
  `엘프의 유적`. It still preserves Bozel losing Alhazard, Jessica sending
  Bernhardt to Velzeria, Liana and Lana being freed, and the incomplete power
  of Langrisser that requires the Holy Rod.
- Adding the previously unused `회` glyph at the old `죽` allocation point
  shifted 37 direct-string records. Moving it to a normal deferred string still
  shifted 18 late records. The accepted build allocates `회` in the trailing
  description pool and retains the retired Scenario 23 `죽` glyph before the
  established consumers. The regenerated 783-record direct-string inventory
  has no token diff, preserving all established name, class, unit, and UI IDs.
- Production 212A `212a_s23_description_final_00.png` through `_20.png` retain
  the route map, all 19 text-bearing `봉인의 열쇠` frames, and the preparation
  endpoint. No Japanese residue, clipping, broken glyph, isolated word, or
  abnormal spacing remains. Scenario 23 `description` is now
  `verified_current`.
- Production checksum is `212A`, SHA-256
  `db597ddedddb36751c5b03d09a46fc090c0bf196ec6cb0eb0d293c8aa2dab987`.
  BlastEm was left on the Scenario 23 preparation screen.

### Scenario 24 Description Runtime Verification (2026-07-18)

- Scenario 24 was compared directly with Japanese-ROM render
  `text_scenarios_23_mapped_040000_jp2bpp16.png`. The current Korean accurately
  preserves the Elrad battle against Laird, acquisition of the Holy Rod,
  Liana and Lana starting the ritual to release Langrisser's power, and
  Bernhardt attacking at the moment he had awaited. No translation or layout
  change was required.
- Production 212A `212a_s24_description_current_00.png` through `_17.png`
  retain the route map, all 16 text-bearing `빛과 어둠` frames, and the
  preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 24 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.

### Scenario 25 Description Runtime Verification (2026-07-18)

- Scenario 25 was compared directly with Japanese-ROM render
  `text_scenarios_24_mapped_040000_jp2bpp16.png`. The current Korean accurately
  preserves cursed Velzeria castle, Bernhardt waiting in its depths with
  Alhazard, Leon and Egbert blocking the way, captive Jessica, and the battle
  in which neither side can yield. No translation or layout change was needed.
- Production 212A `212a_s25_description_current_00.png` through `_15.png`
  retain the route map, all 14 text-bearing `대륙 최강의 기사` frames, and the
  preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 25 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.

### Scenario 26 Description Runtime Verification (2026-07-18)

- Scenario 26 was compared directly with Japanese-ROM render
  `text_scenarios_25_mapped_040000_jp2bpp16.png`. The current Korean accurately
  preserves Leon's defeat, entry into Velzeria castle, the passage toward the
  underground temple, Egbert's encirclement trap, and the Black Dragon
  Sorcerers' concentrated magic attack. No translation or layout change was
  required.
- Production 212A `212a_s26_description_current_00.png` through `_15.png`
  retain the route map, all 14 text-bearing `흑룡마도사단의 함정` frames, and
  the preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 26 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.

### Scenario 27 Description Runtime Verification (2026-07-18)

- Scenario 27 was compared directly with Japanese-ROM render
  `text_scenarios_26_mapped_040000_jp2bpp16.png`. The current Korean accurately
  preserves survival of Egbert's magic attack, arrival at Bernhardt's
  innermost temple, the silent dark shrine, Bernhardt holding Alhazard with
  confidence despite being cornered, and the millennia-long legend nearing its
  end. No translation or layout change was required.
- Production 212A `212a_s27_description_current_00.png` through `_20.png`
  retain the route map, all 19 text-bearing `전설의 끝` frames, and the
  preparation endpoint. Every page is natural Korean without Japanese
  residue, clipping, broken glyphs, isolated words, or abnormal spacing.
  Scenario 27 `description` is now `verified_current`, and BlastEm was left on
  its preparation screen.
- With this run, all 31 scenario descriptions have exhaustive current-build
  runtime evidence from their route map through every scrolling text frame and
  the preparation endpoint. This does not promote any separate opening,
  battle, completion, branch, or ending surface that remains pending.

### Current 212A Scenario Banner And Loren Regression Recheck (2026-07-18)

- After the Scenario 23 description added `회`, the regenerated 783-record
  direct-string inventory remained token-identical, but the two user-reported
  regressions were still rechecked in live production rather than inferred
  from that static result.
- `212a_s27_arrange_banner_check_01.png` and
  `212a_s02_arrange_scenario_banner.png` show intact `SCENARIO 27` and
  `SCENARIO 2` arrangement banners. ASCII tile `0x49` still renders `I`; the
  old `SCENAR록O` collision has not returned.
- The Scenario 2 command cursor starts at `(5,19)`, and Loren's original fixed
  record remains `(19,19)`. Closing Elwin's menu and moving right exactly 14
  tiles selected the intended NPC without visual guessing.
  `212a_s02_loren_status.png` and `212a_s02_loren_popup.png` show complete,
  unambiguous `로렌/하이로드` in both the bottom status row and commander
  popup. The final byte-UI mapping still holds `렌 -> 0x5E9`.
- Existing tests continue to require non-private ASCII `I` to remain original,
  `록` to use its private allocation, and `렌` to keep the explicit stable
  tile. These captures prove the constraints survive in the current production
  ROM, not only in the earlier 489B build.

### Current 212A Scenario 1 Preparation Regression (2026-07-18)

- Scenario 1 was re-entered from the built-in selector after all description
  glyph work. `212a_s01_prep_current.png` verifies the main preparation panel,
  `엘윈/파이터`, `용병고용`, `장비착용`, `상점`, `지휘관배치`, and `소지금`.
- The complete hire path was exercised rather than sampled. Elwin's row is
  `솔저`, AT20, DF14, MV5, 40P; Hein's panel is `헤인/워록` and his row is
  `가드맨`, AT18, DF12, MV5, 20P. Buying one soldier changed the balance from
  500P to 460P without a broken name or stat label.
- The no-inventory equipment path advances through all three localized slot
  labels `무기`, `방어구`, and `장신구`, each with `취소`, before returning to
  the main panel. Representative captures are
  `212a_s01_equipment_current.png`, `212a_s01_equipment_exit_b.png`, and
  `212a_s01_equipment_exit_final.png`.
- The shop buy and sell lists show `아이템 구입`, `아이템 판매`, `단검`,
  `호신용 단검`, `AT+1`, 50P purchase and 40P sale values. The completed
  messages read `단검을 구입함` and `단검을 판매함`; the balance changes to
  450P and then 490P. No old possession garbage or lone `4` reappeared.
- `212a_s01_arrangement_current.png` and
  `212a_s01_arrangement_roster.png` verify the intact `SCENARIO 1` banner and
  the complete `엘윈`, `헤인` roster. The preparation surface is now
  `verified_current`.
- Very short direct-window directional events were occasionally ignored in
  the current remote environment. Reliable review used 0.4-second direction
  holds and 0.25-second C/B holds. This is an input-delivery issue, not a game
  reset or localization defect; use those timings for future menu traversal.

### Current 212A Scenario 25 Preparation And Lester Class Correction (2026-07-18)

- The complete Scenario 25 preparation roster was checked again in current
  production, including both horizontal pages. Page one contains
  `엘윈/파이터`, `헤인/워록`, `쉐리/파이터`, `아론/파이터`, and
  `키스/호크나이트`; page two contains `레스터/크로코나이트`,
  `스코트/파이터`, `리아나/클레릭`, and `라나/클레릭`.
- Each of the nine rows was opened through `장비착용` so class coverage is
  based on the live detail panel rather than the name-only arrangement list.
  Evidence is `212a_s25_equipment_commander_01.png` through `_09.png`, plus
  `212a_s25_arrangement_roster1.png` and `_roster2.png`. Names, classes,
  `LV`, `AT`, `DF`, `MV`, `MP`, command range, and correction labels render
  without Japanese residue or damaged glyphs. `SCENARIO 25` is also intact.
- Earlier HANDOFF and inventory entries called Lester a `크루세이더`. That
  was a visual misread, not ROM ground truth. Global class ID 7 has original
  string `ｸﾛｺﾅｲﾄ` in `localization/global_strings.json` and maps to
  `크로코나이트`; `tools/jp_byte_table_analyzer.py` and the Scenario 10
  source-data regression independently agree. All Lester roster notes were
  corrected, while Jessica's separately verified class records were left
  unchanged.
- Horizontal page changes and selection movement were reliable with 0.4-second
  directional holds. Pressing Down on Keith wraps within page one; Right must
  be used to reach Lester and the remaining four rows. Scenario 25
  `preparation` is now `verified_current`.

### Current ECA0 Secret Scenario Battle UI Evidence (2026-07-18)

- Existing first-turn capture sequences for secret Scenarios X1 and X2 were
  re-audited frame by frame. They contain live battle presentations that had
  been omitted from the runtime inventory status; no ROM patch was required.
- Scenario X1 frames `eca0_s28_turn1_34.png` through `_36.png` show a complete
  `바바리안` versus `워록` battle from 10 VS 10 to 0 VS 3. Both class
  labels, portraits, troop counts, AT/DF base and correction values, terrain
  percentages, and the centered `-AT-`/`-DF-` labels are intact.
- Scenario X2 frames `_18.png` through `_20.png`, `_49.png` through `_50.png`,
  and `_72.png` through `_74.png` cover `리자드맨/파이터`,
  `드래곤나이트/파이터`, and `고렘/호크나이트` matchups. All shared
  battle labels and all six class names render without Japanese residue,
  damaged glyphs, clipping, reset, or freeze.
- Scenario 28 and 29 `battle_ui` are therefore `verified_current`. This does
  not promote their still-pending completion or conditional branch surfaces.

### Current 212A Scenario X3 No-Action Battle Audit (2026-07-18)

- Scenario 30 was re-entered through the built-in selector on current 212A.
  `212a_s30_arrangement_current2.png` confirms the source-secret-stage status
  convention `SCENARIO ?3`; the question mark is intentional, not a damaged
  Korean tile. Automatic deployment and the opening reached a valid map.
- The older two-second first-turn run had no retained battle frame, so the new
  run captured 150 frames at roughly 0.3-second intervals from `턴 종료`.
  Enemy movement and effects reduce Elwin to HP0 and lead to the expected
  Korean defeat dialogue without ever entering the side-view battle renderer.
  `212a_s30_after_failed_turn_end.png` is the final HP0 dialogue evidence.
- A first input attempt entered `용병고용` because several directional events
  were sent before checking focus. Its purchases were fully removed in the
  isolated runtime and did not change the ROM or source. Reliable traversal
  used one 0.1-second direction event followed by a screen check; C on the
  hire `END` row, rather than B, returns to the preparation command list.
- Since the actual no-action route cannot prove the scenario-specific battle
  view, Scenario 30 `battle_ui` is conservatively `verified_probe` using the
  production-derived 3590 shared-renderer evidence. It is not
  `verified_current`; successful-clear and branch surfaces remain pending.

### All-Record Epilogue Renderer Probe (2026-07-18)

- The epilogue inventory remains 90/90 translated records and 515 authored
  pages. Static tests already lock every Japanese source hash, unique pointer
  owner, dynamic-name control, page count, relocated Korean pointer, and
  three-line/24-cell page limit, but the old runtime probe forced only one
  outcome per complete Scenario 27 replay.
- `tools/build_epilogue_probe_rom.py --all-records` now constructs one ignored
  renderer stream at `0x3E0000`. It copies every current relocated record
  byte-for-byte except that the first 89 `FFFF` terminators become `FFFD` page
  breaks; the 90th terminator remains unchanged. The resulting stream has
  exactly 515 pages and ends before the existing probe descriptors at
  `0x3FF000`.
- The generated JSON manifest records the zero-based start page, page count,
  source and relocated addresses, English cross-reference, and word range for
  every record. This lets a continuous capture set be attributed back to all
  90 outcomes without guessing from screenshots.
- New tests reconstruct and compare every combined segment against its
  production relocation, assert all 90 page ranges and the total page count,
  verify selector descriptors and checksum, and reject a nonempty reservation.
  The standalone all-record probe is checksum `9221`; applying the Scenario 27
  adjacent-Bernhardt probe produces checksum `DD8F`.
- This is a non-distribution runtime verifier. It proves the real renderer can
  consume every Korean page in one ending entry, but it does not replace
  single-record tests of normal/Liana/world selector ownership or ordinary
  outcome-condition selection.
- Combined checksum `DD8F` was played from the Scenario 27 selector through
  automatic deployment and the adjacent-Bernhardt ending probe. Bernhardt was
  defeated on the first attack, after a pre-attack quicksave, and the complete
  closing path consumed the all-record stream through its final `FFFF` and
  reached stable `Fin` without a reset or freeze. Continuous evidence is
  `captures/run/dd8f_closing_watch/` followed by
  `captures/run/dd8f_all_epilogues_watch/`; frame `0750.png` is `Fin` and it
  remains unchanged through `1200.png`.
- This successful renderer pass does not promote every ending branch. It
  verifies that the combined 90-record/515-page byte stream terminates through
  the stock renderer, while ordinary outcome selection and a page-by-page
  visual acceptance pass remain separate gates.
- The run exposed a production regression outside the authored epilogue text:
  the ending result/status loader does not retain every high-extension glyph.
  `dd8f_all_epilogues_watch/0340.png` holds a stable broken second syllable in
  `보젤` and first syllable in `다크마스터`; `0545.png` through `0560.png`
  hold the same kind of stable corruption in `엠퍼러` below the intact
  `베른하르트`. These are not one-frame fades and must be fixed in the ending
  status-screen glyph loader before this surface is accepted.
- The title-screen LOAD path is also distinct from the already localized
  in-battle Start-menu load child. `captures/run/dd8f_load_slots.png` still
  renders Japanese `ロード` and `データがありません`; keep title LOAD and
  all slot/error variants in the UI gap inventory.

### Ending Result Font-Bank Repair And Full Replay (2026-07-18)

- Broken-run state `captures/analysis/dd8f_ending_status.gst` was inspected
  before changing code. Plane A at `C000`, Plane B at `E000`, and live sprites
  at `F000` did not reference the four damaged extension ranges. The current
  VRAM differed from the ROM resources across tiles `0x398..0x3AF`,
  `0x440..0x447`, `0x498..0x4AF`, and `0x4D8..0x4EF`; the exact user-visible
  failures included `젤`, `다`, `엠`, and `퍼`.
- The ending status name call at `0x01CBA6` is now the only direct-map caller
  routed through wrapper `0x2B7D00`. It preserves all registers, queues
  compressed resources `0x1AF`, `0x1B0`, `0x1B1`, and `0x1B2` for VRAM tile
  starts `0x398`, `0x440`, `0x498`, and `0x4D8`, restores registers, and jumps
  to the existing renderer at `0x2B7800`. Calls at `0x01B546` and `0x01CBBC`
  remain direct, avoiding a global background/resource side effect.
- Production checksum remains `5F82`; the fixed all-record Scenario 27 probe
  is checksum `1BE7`. The adjacent Bernhardt was defeated on the first valid
  attack. A first navigation attempt held Up for 0.4 seconds and moved two
  cells to an out-of-range target; use one short Up event. Loading the same-run
  quicksave later caused BlastEm to exit, so the accepted attempt was replayed
  from the selector instead of treating quickload as reliable evidence.
- `captures/run/1be7_full_ending_watch/0000.png` through `1288.png` retain
  every sampled input frame. Result starts verify `스코트/파이터` at `0257`,
  `쉐리/파이터` at `0322`, `키스/호크나이트` at `0389`, `라나/클레릭`
  at `0467`, `아론/파이터` at `0533`, `레스터/크로코나이트` at `0601`,
  `헤인/워록` at `0668`, and `제시카/소서러` at `0745` before the affected
  imperial/villain groups.
- `0799.png` and `captures/run/1be7_bozel_darkmaster_fixed.png` show complete
  `보젤/다크마스터`. `1052.png` and
  `captures/run/1be7_bernhardt_emperor_fixed.png` show complete
  `베른하르트/엠퍼러`. The combined 90-record/515-page stream reaches `Fin`
  at `1241.png`; hashes stay identical through `1288.png`. No reset, freeze,
  damaged result glyph, or premature terminator was observed.
- The user-reported ending line is now retained at `0104.png` through
  `0107.png`: `제국군이 마을로 오고 있어! 리아나가 위험해!`. It is
  rendered by the fixed-count ending montage list at `0x0A6CEC`, not by the
  Scenario 1 event block. Ownership and playback are proven, but every
  `opening_text_lists` inventory entry remains `reviewed: false`; compare this
  montage against Japanese-ROM playback before accepting its wording.

### Isolated SRAM Recovery Format Marker (2026-07-18)

- A newly created isolated SRAM could contain a checksum-valid manual slot and
  valid flag `0x0002` at `0x1FF0` while the title LOAD screen still reported no
  data. Comparing game-initialized saves proved that the global format marker
  at `0x1FEE` must be `0x07CA`; blank synthetic files contained `0x0000`.
- `recover_manual_slot_from_gst()` now initializes a blank marker, preserves
  the expected marker, and rejects an unknown nonzero marker before writing.
  `manual_slot_scenario_number()` also validates the marker, so automation can
  no longer claim a slot is usable when the game rejects the SRAM container.
  The full suite passes 242 tests, and a fresh `1BE7` runtime entered Scenario
  27 through the title LOAD/selector path using the corrected blank SRAM.

### Ending Montage Source Correction (2026-07-18)

- Japanese replay `captures/run/230d_jp_ending_montage/` proved that
  `리아나가 위험해` in the Korean ending was invented text. The source scene
  instead discusses Bernhardt's distrust, understanding one another, the
  allies who stopped the empire, Langrisser uniting hearts, and Elwin's next
  journey. The ten records at `0x0A6BA8..0x0A6F02` now follow that source.
- The montage renderer count is only a maximum. The previous writer padded to
  that count and overwrote earlier `FFFF` terminators, which spliced adjacent
  records. `OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES` locks and restores the
  exact Japanese layout; `tests/test_opening_text_lists.py` covers the layout,
  written boundaries, reviewed meanings, and dynamic-name separators.
- Runtime `1E2A` under `captures/run/1e2a_ending_fixed/` verified the corrected
  meanings and revealed that four Elwin-owned records receive the name from
  the game. They now begin with `: `. Production checksum is `D8F6`. A later
  `2464` capture began after the conversation, so do not cite it as final
  punctuation playback proof.
- `엠퍼러` remains correct in the ordinary ending result surface, proven by
  `captures/run/1be7_bernhardt_emperor_fixed.png`. The orange/red obstruction
  at `1e2a_ending_montage/163.png` is the adjacent-Bernhardt probe's flame
  sprite overlaying the popup; frame `164.png` places that animated sprite at
  the same coordinates. The relocated class token bytes are unchanged.
- All 245 unit tests pass. The ten Japanese-reviewed montage rows are marked
  `reviewed: true`; the first two villain records remain unreviewed, and the
  final colon-only build remains conservatively `live_verified: false`.

### Title LOAD Slot Localization (2026-07-18)

- The title LOAD path is independent from Start-menu Load. Entry `0x029D76`
  loads 42 local glyphs from `0x0A2F14` into VRAM `0xA000`. Slots 0-10 are the
  cursor and digits and remain byte-identical; only slots 11-41 are reassigned.
- Fixed records are `0x0A30D6` (`이어하기`), `0x0A30E8` (`시나리오`),
  `0x0A30F2` (`손상된 데이터`), `0x0A3106` (`데이터 없음`), and `0x0A311A`
  (`다음 시나리오`). Every original-position `FFFF` terminator and record
  width is validated before writing. The load header's original three cells
  cannot hold four-syllable `불러오기`; the full record is stored in verified
  `FF` space at `0x2B7E00`, and the LEA at `0x029DE6` points there. The original
  header remains a readable `로드` fallback.
- Production checksum is `B65D`. `captures/run/b65d_title_load_live.png`
  proves `불러오기`, a valid manual `1 시나리오 2`, and empty slots. A real
  Scenario 1 Start-menu save created an autosave flag (`0x0001` at SRAM
  `0x1FF0`); its autosave region was merged with the isolated valid manual
  slot for `captures/run/b65d_title_load_autosave_manual1.png`, which proves
  `이어하기` and the valid manual row together.
- In a separate SRAM copy, byte `0x1950` of manual slot 1 was changed without
  updating its checksum. `captures/run/b65d_title_load_corrupt_manual1.png`
  proves `손상된 데이터` while the autosave remains valid. The canonical
  `load-screen` SRAM was restored from
  `captures/analysis/title_load_variants/manual_slot1_original.sram`; the
  corrupt file is diagnostic only. The format marker remains `0x07CA`.
- `다음 시나리오` and the shared title SAVE header are statically patched and
  boundary-tested but not marked live verified. The generated UI inventory now
  declares the glyph bank, five records, fallback/header hook, and relocation
  individually instead of retaining a blanket save/load gap. All 250 unit
  tests pass, and the production build reproduces checksum `B65D` with the
  established 861 custom glyphs still at `0x7000..0x735D`.

### First-Title Credit And Main Menu Localization (2026-07-18)

- The first title screen's byte-font load at `0x02D664` already passes through
  the generic localized font loader. The following source setup at `0x02D66A`
  is hooked to wrapper `0x2B7E20`, which queues new compressed resource 436 at
  VRAM tile `0x3A` and then restores the overwritten resource `0x8189` setup.
  The title-only resource copies the patched base slice `0x3A..0x73`, replaces
  only `:`, `한글화`, menu syllables, and the lowercase `hsp` bitmaps, and is
  reloaded only on this title path. It does not permanently steal gameplay
  mappings or the lowercase terrain/icon slots.
- Copyright renderer entry `0x02D712` jumps to `0x2B7E40`. The wrapper renders
  the untouched source record at `0x0A44F8` to Plane C row 22 and then the new
  record at `0x2B7EC0` to row 24. The centered visible text is
  `한글화: hsp1324`; the requested lowercase ID uses dedicated thick pixel
  bitmaps because the stock lowercase slots are not a coherent Latin font.
- The first menu record is locked at `0x0A3146`. Its five-cell START payload at
  `0x0A3158` is `새 게임` plus padding and keeps `FFFE`; its four-cell LOAD
  payload at `0x0A3164` is `불러오기` and keeps `FFFF`. This renderer consumes
  8x8 byte-font IDs, not global 16x16 glyph IDs. An initial `CECC` experiment
  used global glyph IDs and visibly produced garbage; do not repeat that
  approach. The accepted mapping uses title-only byte slots `0x61..0x67`.
- Production checksum is `F04E`, with the established 861 custom glyphs still
  at `0x7000..0x735D`. `captures/run/f04e_title_credit_live.png` proves the
  centered credit while preserving the original prompt and copyright;
  `captures/run/f04e_title_main_menu_live.png` proves both localized menu rows.
  `captures/run/f04e_title_new_game_entry.png` proves that
  `새 게임` reaches Korean name entry. `captures/run/f04e_title_load_entry.png`
  proves that `불러오기` reaches the localized LOAD screen and preserves the
  right-side scenario number. The preserved valid Scenario 2 manual slot then
  entered the built-in selector and reached target Scenario 14; the route frame
  is `captures/run/f04e_scenario_select_14.png`.
- `tests/test_title_main_screen.py` locks the Japanese menu record, menu
  terminators, title hooks/routines/record boundaries, and every tile in the
  separate compressed font resource. The generated UI inventory declares all
  seven newly owned surfaces as reviewed and live verified. All 257 unit tests
  pass; the direct-word inventory still has 783 classified candidates and no
  unclassified entry.

### Scenario-Selector LOAD Header Number (2026-07-19)

- `tools/run_blastem_sequence.py scenario-select-entry` now reuses the same
  validated manual slot and one-command key timing as `scenario-select`, but
  stops immediately after `Left, Right, Start, C`. Splitting launch and cheat
  input across commands repeatedly left the game on the ordinary LOAD screen;
  do not use that failed method for selector captures.
- `captures/run/jp_scenario_select_entry_reference.png` proves the original
  Japanese behavior: the selector does not replace the header with
  `次のシナリオ`; it draws the saved scenario number in the fourth cell after
  the three-cell `ロード` label. The patched four-cell `불러오기` initially
  occupied that number cell, producing an overlap in
  `captures/run/f04e_scenario_select_entry.png`.
- The relocated header record at `0x2B7E00` now starts at tile X=`0x0F`
  instead of `0x11`. Its four 16-pixel glyphs occupy tile columns 15..22, and
  the unchanged selector number sprite begins at visible X=184/tile column 23.
  This preserves the full normal label without abbreviating it and preserves
  the original dynamic selector number.
- Production checksum is `F04C`; custom glyph count remains 861 at
  `0x7000..0x735D`. `captures/run/f04c_title_load_entry.png` proves the normal
  `불러오기` header, `captures/run/f04c_scenario_select_entry.png` proves the
  non-overlapping `불러오기2` selector header, and
  `captures/run/f04c_scenario_select_14.png` proves the selector still reaches
  Scenario 14.
- The fixed record at `0x0A311A` is translated as `다음 시나리오`, but neither
  the ordinary nor selector-entry LOAD screen exposes it. The following SAVE
  renderer probe establishes its actual visible owner.

### Title SAVE Fixed-Text Renderer Probe (2026-07-19)

- The stock title SAVE renderer is entry `0x029B70`; the normal title LOAD
  renderer is `0x029D76`. `tools/build_title_save_probe_rom.py` validates the
  two LOAD wrapper operands at `0x02A40C` and `0x02A41C`, redirects only those
  operands to SAVE, and updates the ignored diagnostic ROM checksum. Its unit
  test permits changes only in those eight operand bytes and checksum bytes.
- Probe checksum `EC40` reaches the real SAVE renderer through the localized
  title menu. `captures/run/ec40_title_save_renderer_probe.png` visibly proves
  the `저장` header from `0x0A312A` and the lower `다음 시나리오` record from
  `0x0A311A`. These two fixed surfaces are now `live_verified: true` in the UI
  inventory.
- This title redirect does not provide the current scenario-clear work RAM.
  The colored central dynamic sprites in the diagnostic frame are therefore
  invalid test context, not a production patch result. Attempts to set only
  `$A49C=2`, clear D5, and copy a valid manual SRAM did not change them; do not
  repeat those partial initializations. Full dynamic-slot verification remains
  attached to a normal scenario-clear run.
- All 262 unit tests pass. The generated UI inventory still has 111 declared
  surfaces, 110 byte-modified surfaces, and eight explicit remaining gaps.

### Fighter Elwin Class-Change Runtime Proof (2026-07-19)

- The persistent player roster is work RAM `0xFFA4CC`, ten records of `0x18`
  bytes; class/level/experience are record offsets `+0/+2/+3`. Manual slot 1
  starts at SRAM `0x194E`, with this roster at `+0x30`. Runtime units start at
  `0xFF603C`, use `0x60`-byte records, and Elwin's level/experience are
  `0xFF606A/0xFF606B`. Routines `0x011C78` and `0x0177D8` synchronize runtime
  and persistent records in opposite directions.
- A save-only LV9/EXP16 patch reached preparation as intended but deployment
  synchronization restored the older runtime LV1. Do not repeat that method as
  a complete class-change trigger. `tools/run_blastem_sequence.py` nevertheless
  keeps the validated commander-progress patch options because they are useful
  for isolated save-structure experiments and recompute the slot checksum.
- `tools/build_class_change_probe_rom.py` builds an ignored diagnostic ROM. An
  end-turn wrapper at `0x3FF000` modifies only Fighter Elwin, then jumps to the
  stock level-up handler `0x01480C`. The first branch displacement was
  mistakenly `0x0010`, landing inside an instruction; the tested value is
  `0x0012`. Natural end-turn GSTs
  `captures/analysis/eb00_class_change_turn2.gst` and
  `captures/analysis/eb00_class_change_short_turn2.gst` prove stock application
  to class `0x04`, LV1, EXP0, although that route auto-confirms the first row.
- The same probe's Start wrapper at `0x3FF040` fills `0xFFFFAA00` with commander
  ID 1 and source-derived candidates `0x04/0x05/0x0A`, sets A1 to Elwin's
  runtime record, and jumps to stock UI `0x02BB48`. Original progression data at
  `0x082562` identifies these as `로드/나이트/샤먼`.
- Probe checksum `D1D7` visibly verifies `클래스체인지 가능`, the short
  `클래스체인지` title, all three candidates, `용병/마법` details, Down-row
  navigation, and wrap from `샤먼` to `로드`. Accepted captures are
  `captures/run/d1d7_class_change_start_trigger.png`, candidate frames
  `candidate1.png` through `candidate3.png`,
  `d1d7_class_change_candidate_wrap.png`, and
  `d1d7_class_change_confirm.png`.
- `captures/analysis/d1d7_class_change_confirm.gst` has class `0x04`, but lacks
  a controlled pre-confirm state and is retained only as screen/navigation
  evidence. The normal end-turn GSTs above are the accepted application proof:
  they show the runtime change from class `0x01` to `0x04`, LV1, EXP0.
  Production remains checksum `F04C`; no probe wrapper is distributed.
- The broad UI inventory gap is now narrowed to candidate sets beyond Fighter
  Elwin's `로드/나이트/샤먼` branch. Do not mark every commander/branch class
  candidate complete from this representative proof.
- All 269 unit tests pass after the probe builder, save-slot patcher, and
  narrowed generated inventory are included.

### Generalized Class-Change Source Inventory (2026-07-19)

- The ten player-chain pointers start at `0x08253A`. Each chain contains nine
  four-word transitions (`current + three candidates`), one two-word terminal
  transition (`current + one candidate`), and an `FFFF` sentinel. The resulting
  100 source transitions collapse to 76 unique current/candidate combinations.
- `tools/class_change_data.py` validates and parses this structure.
  `tools/class_change_inventory.py` writes
  `localization/class_change_chains.json` and
  `docs/class_change_chain_inventory.md`, keeping Japanese and Korean class
  names plus separate screen/application evidence states. This is the source
  of truth for later class-chain editor work; do not transcribe a PC-version
  chart over these MD records.
- `tools/build_class_change_probe_rom.py --commander-id 9 --current-class 0x10`
  built checksum `D221` from the source transition
  `서펜나이트 -> 실버나이트/서펜로드/팔라딘`. Captures
  `d221_c9_s10_candidate1.png` through `candidate3.png` verify all three names,
  navigation, and their Korean `용병/마법` details without clipping.
- Scenario 2 has no active Lester runtime record, so this diagnostic still set
  A1 to Elwin. Its retained state did not establish a Lester before/after
  transition. This is screen/navigation evidence only; use a scenario with the
  matching commander active before marking `application_verified`.
- The 278-test snapshot recorded here predates the non-Elwin application probe
  below. The generated inventory at this point still had a 74-combination gap.

### Non-Elwin Class-Change Runtime Application (2026-07-19)

- `tools/build_class_change_probe_rom.py` now accepts a source-chain commander
  ID and an independent active runtime-record index. Player runtime records
  start at `0xFF603C`, are `0x60` bytes each, and indexes outside 0..9 are
  rejected. `--end-turn-only` preserves the normal Start menu and installs only
  the guarded stock level-up trigger.
- Start-display checksum `8EF4` uses commander 5, current class `0x03`, runtime
  index 1, and the source candidates `0x0A/0x09/0x04`. Captures
  `captures/run/8ef4_c5_s03_candidate1.png` through `candidate3.png` visibly
  verify `샤먼/소서러/로드`, navigation, and their `용병/마법` details.
- Before/after states `captures/analysis/8ef4_c5_s03_preconfirm.gst` and
  `8ef4_c5_s03_confirm.gst` have identical class bytes in all ten player
  runtime and persistent records. The Start wrapper is a display/navigation
  probe only; confirmation must never be cited as application evidence.
- End-turn-only checksum `A8D7` was booted fresh. The normal Start menu remained
  available, and `턴 종료` entered the stock level-up path. Runtime record 1
  changed from class `0x03` to `0x0A` and reset to LV1. The byte result is in
  `captures/analysis/a8d7_c5_s03_after_turn.gst`; the map status popup visibly
  reads `헤인 / 샤먼 / LV 1` in
  `captures/run/a8d7_c5_s03_hein_shaman_applied.png`.
- An in-battle `저장` confirmation was also attempted in the isolated `A8D7`
  runtime. On clean termination, `save.sram` contained the format marker but no
  manual-slot valid flag or roster payload. This attempt is not persistent-save
  evidence and should not be repeated as such. A normal scenario-clear save is
  still needed to prove persistence; runtime application itself is verified.
- Cross-ROM GST loads that reset after combat were rejected. Only the fresh
  `8EF4` and `A8D7` boots above are accepted evidence. Production ROM content
  was not modified by either ignored diagnostic ROM. Rebuilding production
  retains checksum `AD01`, and all 289 unit tests pass.
- A fresh checksum `903C` Start-display probe covers Hein's next source
  transition, `샤먼(0x0A) -> 프리스트(0x11) / 비숍(0x12) / 메이지(0x13)`.
  `captures/analysis/903c_c5_s0a_trigger.png` and
  `captures/run/903c_c5_s0a_candidate1.png` through `candidate3.png` verify the
  long/short titles, all rows, stats, mercenaries, and Korean magic lists
  without clipping or Japanese residue. This row is `live_verified` but not
  `application_verified`; do not infer application from the Start probe.
- Fresh Start-display checksums `9037` and `902B` extend this to Hein's
  `소서러 -> 비숍/메이지/매직나이트` and
  `로드 -> 메이지/매직나이트/하이로드` rows. The matching
  `captures/run/9037_c5_s09_candidate1.png` and
  `902b_c5_s04_candidate1.png` series through `candidate3.png` verify every
  class, stat, mercenary, and Korean magic list. These are screen-only proofs.
- `tools/jp_ui_surface_inventory.py` now derives the remaining unique
  class-change combination count from the source-chain inventory instead of a
  hand-maintained number. This prevents later live-evidence additions from
  leaving the broad UI gap stale.
- `tools/capture_class_change_transition.py` automates the repeated screen-only
  workflow: build an ignored probe from the selected source transition, boot a
  clean isolated runtime, wait for `battle-command` detection to finish, close
  both command/status panels, enter the Start diagnostic, capture its prompt and
  every candidate row, and terminate BlastEm. It uses direct window events and
  never treats those captures as application evidence.
- End-to-end use of that tool completed Hein's remaining source rows for current
  classes `11/12/13/0D/0B/15`. Accepted capture prefixes are
  `904f_c5_s11`, `904e_c5_s12`, `9050_c5_s13`, `904e_c5_s0d`,
  `9052_c5_s0b`, and `9037_c5_s15`. Visual review found no Japanese residue,
  broken class glyph, clipping, or damaged mercenary/magic label. Hein's full
  ten-transition chain is screen-verified; application remains proven only for
  the initial `03 -> 0A` transition.
- Rebuilding production after the automation changes retains checksum `AD01`.
  All 291 unit tests pass.
- `tools/capture_class_change_chain.py` adds commander-level batching. It derives
  pending work from source transition signatures plus accepted live evidence,
  skips a transition only when its prompt and every candidate capture already
  exist, and supports `--limit`, `--overwrite`, and `--include-verified`.
  Greedy source-set review identifies commander 2 (Liana) as the next best
  chain: ten pending transitions add ten currently uncovered combinations.
- A clean batch run for commander 2 completed all ten selected transitions with
  `completed 10, resumed 0`. Accepted prefixes are `8e91_c2_s02`,
  `8eb4_c2_s0a`, `8eb1_c2_s08`, `8eab_c2_s04`, `8ed6_c2_s13`,
  `8ed2_c2_s0d`, `8ece_c2_s11`, `8ece_c2_s12`, `8ec8_c2_s0b`, and
  `8eb8_c2_s19`. All 28 candidate frames were visually reviewed; names, stats,
  mercenaries, and magic are Korean and intact. These ten rows are screen-only
  evidence. With Liana registered, commander 4 (Sherry) becomes the next
  ten-combination batch target.
- Re-running the first two Liana rows with `--include-verified --limit 2`
  reports `completed 0, resumed 2` without launching BlastEm, proving complete
  capture-set resume behavior. Production remains checksum `AD01`; all 295 unit
  tests pass.
- Commander 4 (Sherry) then completed ten fresh transitions with
  `completed 10, resumed 0`. Accepted prefixes are `8e90_c4_s01`,
  `8ea7_c4_s04`, `8eb0_c4_s06`, `8eb9_c4_s0a`, `8ed7_c4_s0b`,
  `8ee1_c4_s0e`, `8ede_c4_s0f`, `8edd_c4_s12`, `8ed4_c4_s13`, and
  `8ebd_c4_s21`. All 28 candidate frames were reviewed. Flying, unicorn,
  Ranger, Dragon Lord, and terminal High Master branches render Korean names,
  stats, mercenaries, and magic without clipping or residue. Ranger's blank
  mercenary area is source behavior. These are screen-only proofs; commander 6
  (Scott) is the next ten-combination batch target.
- Production rebuild remains checksum `AD01`; all 296 unit tests pass after the
  Sherry evidence and generated inventories are included.
- Commander 6 (Scott) completed all ten source transitions with
  `completed 10, resumed 0`. Accepted prefixes are `8e8d_c6_s01`,
  `8eab_c6_s06`, `8eac_c6_s05`, `8ea9_c6_s04`, `8ee3_c6_s0f`,
  `8ede_c6_s0d`, `8ed9_c6_s0c`, `8eda_c6_s11`, `8ed0_c6_s0b`, and
  `8ebf_c6_s1b`. All 28 candidate frames were visually reviewed. Cavalry,
  flying, holy, and terminal Royal Knight branches show intact Korean class,
  stat, mercenary, and magic text with no Japanese residue or clipping.
  These are screen-only proofs; application evidence remains limited to the
  established Elwin and Hein rows.
- The generated inventory now reports 42/76 unique source combinations
  screen-verified and two transitions application-verified. Duplicate coverage
  also closes Lana's source chain without another emulator run. The remaining
  34 unique combinations begin with nine pending Elwin rows (`04` through
  terminal `1A`). Production remains checksum `AD01` with 861 custom glyphs;
  all 297 unit tests pass.
- Commander 1 (Elwin) completed nine pending transitions with
  `completed 9, resumed 0`: `8ea5_c1_s04`, `8ea1_c1_s05`, `8eae_c1_s0a`,
  `8edb_c1_s12`, `8ed8_c1_s0b`, `8ed5_c1_s0c`, `8ed9_c1_s0d`,
  `8ed8_c1_s13`, and `8eb2_c1_s1a`. All 25 candidate frames were visually
  reviewed through the terminal Hero branch with intact Korean class, stat,
  mercenary, and magic text. They are screen-only evidence.
- Generated coverage is now 51/76 unique combinations, two application proofs,
  and 25 unique combinations remaining. Commander 9 (Lester) is the next
  nine-row batch target. Production remains checksum `AD01` with 861 custom
  glyphs; all 297 unit tests pass.
- Commander 9 (Lester) completed nine pending transitions with
  `completed 9, resumed 0`: `8e97_c9_s01`, `8eae_c9_s05`, `8eb6_c9_s07`,
  `8ebf_c9_s0a`, `8ee0_c9_s0c`, `8ee5_c9_s0d`, `8edf_c9_s12`,
  `8ed5_c9_s13`, and `8ec7_c9_s1f`. All 25 candidate frames were visually
  reviewed, including the MD water chain through terminal Serpent Master.
  Korean class, stat, mercenary, and magic text is intact. These are
  screen-only proofs.
- Generated coverage is now 60/76 unique combinations, two application proofs,
  and 16 unique combinations remaining. Commander 7 (Keith) is the next
  eight-row batch target. Production remains checksum `AD01` with 861 custom
  glyphs; all 299 unit tests pass.
- Commander 7 (Keith) completed eight pending transitions with
  `completed 8, resumed 0`: `8e91_c7_s01`, `8ea9_c7_s04`, `8eb2_c7_s06`,
  `8eb8_c7_s08`, `8ed3_c7_s0b`, `8edc_c7_s0d`, `8ed7_c7_s11`, and
  `8ebe_c7_s1e`. All 22 candidate frames were visually reviewed. `클레릭`,
  the flying chain, and terminal High Master render intact Korean class, stat,
  mercenary, and magic text. These are screen-only proofs.
- Generated coverage is now 68/76 unique combinations, two application proofs,
  and eight unique combinations remaining. Commander 8 (Aaron) supplies five;
  commander 10 (Jessica) supplies the final three. Production remains checksum
  `AD01` with 861 custom glyphs; all 300 unit tests pass.
- Commander 8 (Aaron) completed five pending transitions with
  `completed 5, resumed 0`: `8ed8_c8_s12`, `8ed9_c8_s0c`, `8edc_c8_s0d`,
  `8edd_c8_s13`, and `8eba_c8_s1a`. All 13 candidate frames were visually
  reviewed through terminal High Master. Korean class, stat, mercenary, and
  magic text is intact; the terminal empty mercenary area is source data.
  These are screen-only proofs.
- Generated coverage is now 73/76 unique combinations, two application proofs,
  and three screen combinations remaining. Jessica's current classes
  `03/08/14` are the final screen-only batch. Production remains checksum
  `AD01` with 861 custom glyphs; all 301 unit tests pass.
- Commander 10 (Jessica) completed the final three pending screen transitions
  with `completed 3, resumed 0`: `8e99_c10_s03`, `8ebf_c10_s08`, and
  `8eb9_c10_s14`. All seven candidate frames were visually reviewed through
  terminal Zveler. Korean class, stat, mercenary, and magic text is intact.
- Candidate-screen coverage is now 76/76 unique source combinations; every
  commander returns zero pending unique rows. `jp_ui_surface_inventory.py`
  therefore no longer emits the misleading `remaining 0` wording and instead
  keeps the real gap: application verification beyond the two proven Elwin and
  Hein transitions. A normal scenario-clear save is also still required for
  persistence evidence. Production remains checksum `AD01` with 861 custom
  glyphs; all 302 unit tests pass.

### Scenario 1 Clear, Dynamic SAVE, And Result Header (2026-07-19)

- `tools/build_scenario1_clear_probe_rom.py` builds an ignored diagnostic ROM
  from production. It validates the Japanese Scenario 1 header at `0x180196`,
  the first player deployment slot `(11,17)`, and Bald's fixed record at
  `0x1802D8`. It changes only Bald's AT/DF, position, six mercenary bytes, and
  the Mega Drive checksum. No event, completion, result, or SAVE renderer code
  is patched. The first version called the deployment slot Elwin-specific;
  that ownership was broader than the source evidence, so the accepted names
  say `FIRST_PLAYER_DEPLOYMENT`.
- Probe checksum `8AEA` completed Scenario 1 through the stock event path.
  `captures/run/8aea_s01_clear_post_40.png` reaches the result screen and
  `captures/run/8aea_s01_clear_post_41.png` reaches the real title SAVE screen
  with live work RAM. The latter visibly verifies `저장`, `시나리오 2`, three
  `데이터 없음` rows, `다음 시나리오`, and the unobstructed dynamic number.
  This supersedes the earlier EC40 renderer-only probe's dynamic-data gap.
- The same result frame exposed the Japanese title `戦果報告`. Pixel matching
  against the Japanese global font identifies exact glyph IDs `0149 00A3 0198
  0199`; their unique ROM sequence begins at `0x0A2D88` and is followed by
  `FFFF`. `scripts/build_korean_jp_probe.py` now validates all four source IDs
  before writing `전과보고`. `tests/test_battle_result_screen.py` locks the
  source IDs, terminator, target text, and every rendered 64-byte glyph.
- Production checksum is `AD01`, still with 861 custom glyphs. Its rebuilt
  clear probe checksum is `479F`. Loading the old 8AEA attack GST into 479F
  reproduced the map but reset after combat; that cross-ROM state is rejected
  as evidence. A fresh 479F boot then entered Scenario 1 normally, selected
  Elwin, defeated adjacent Bald, and completed all stock post-battle movement
  and dialogue without reset or freeze.
- `captures/run/479f_s01_clear_result_current.png` visibly proves the centered
  `전과보고` title, party lists, and POINT value without damaged glyphs or
  clipping. The next frame initially showed four `데이터 없음` rows; confirming
  slot 1 wrote the real next-scenario data, and
  `captures/run/479f_s01_clear_save_current.png` proves `시나리오 2`, the
  unobstructed dynamic number, remaining empty rows, and `다음 시나리오`.
  The result-header inventory entry is now `live_verified: true`.

### Scenario 2 North-Escape Completion Probe (2026-07-20, Verified)

- Scenario 2 is not a Zorum-defeat clear. The stock condition resource says
  victory is Liana reaching the north edge or enemy annihilation; defeat is
  Liana or the protagonist dying. Do not reuse the Scenario 1 weak-boss probe.
- `tools/build_scenario2_escape_probe_rom.py` validates the Japanese Scenario 2
  header `0x180368`, deployment table `0x180380`, first-player slot `(5,19)`,
  ten fixed records, and Liana's index-3 record at `0x1803FC` with source
  coordinates `(8,18)`. It changes only that record's Y byte to `1` plus the
  Mega Drive checksum. Current ignored diagnostic checksum is `3C46`.
- Static tests prove the changed-byte subset and reject altered deployment
  pointers or input Liana records. The rebuilt probe based on production `38AB`
  has checksum `389A`. A recovered isolated Scenario 2 save entered the normal
  route, preparation, deployment, and all 62 opening confirmations before
  reaching Elwin's command menu without reset or freeze.
- On the first NPC phase, Liana reached the north edge and the stock completion
  path rendered the complete Korean escape dialogue in
  `389a_s02_escape_12.png` through `_17.png`. Frame `_18.png` is the intact
  `전과보고` screen with `POINT 800P`; `_19.png` is the next-scenario save
  screen. Repeated confirmation wrote real `시나리오 3` data to slot 1, and
  selecting `다음 시나리오` reached the Scenario 3 route map in
  `389a_s02_next_scenario_selected.png`. Scenario 2 completion is therefore
  `verified_probe`; alternative enemy-annihilation victory and both defeat
  branches remain pending.

### Stable Forced Class-Change Application Diagnostics (2026-07-19)

- Stock handler disassembly resolves runtime record `+0x00` as current class
  and `+0x01` as commander ID. The handler reads `+0x01` at `0x01483C`, indexes
  the source pointer table at `0x08253A`, and reads `+0x00` at `0x014B46`.
- The first forced Jessica `03 -> 08` probe, checksum `BDAC`, applied the class
  but reset because runtime record 0 retained Jessica ID 10 in Scenario 1.
  `captures/analysis/bdac_c10_s03_jessica_cleric_applied.gst` is rejected
  failure analysis, not stable evidence. Do not repeat this no-restore design.
- `tools/build_class_change_probe_rom.py --force-runtime-context` now patches
  the post-confirm resume operand at `0x014D0C` to a callback at `0x3FF040`.
  The callback restores the original runtime commander ID and resumes the stock
  handler at `0x01480C`. Forced context is end-turn-only because the callback
  and the screen-only Start probe share the diagnostic expansion slot.
- Checksum `7164` stably applies Jessica's source `워록(03) -> 힐러(08)`
  chain. `captures/analysis/7164_c10_s03_forced_apply_stable.gst` contains class
  08, restored commander 01, LV1, EXP8; the stable map and Korean status screen
  are `7164_c10_s03_post_apply_stable.png` and
  `7164_c10_s03_applied_status.png` under `captures/run`.
- `tools/capture_class_change_application.py` automates the clean Scenario 1
  route, normal `Start > 턴 종료`, first-candidate application, 15-second
  stability wait, GST field assertions, status capture, and BlastEm cleanup.
  Its checksum `715F` Keith proof applies `파이터(01) -> 로드(04)` and retains
  `captures/analysis/715f_c7_s01_forced_apply.gst` with class 04, restored
  commander 01, LV1, EXP0. The corresponding reviewed frames use prefix
  `captures/run/715f_c7_s01_forced_apply_`.
- Forced-context results prove source-chain application through the stock
  handler and stable return after identity restoration. They are not natural
  active-commander or save-persistence proofs. The class-change inventory now
  distinguishes two `natural` proofs from two `forced-context` proofs; the
  remaining gap is natural commander coverage and normal save persistence.
- The production rebuild remains checksum `AD01` with 861 custom glyphs. All
  310 unit tests pass, including the forced wrapper, restore callback, GST
  parser, generated inventory, and explicit evidence-type regressions.

### Magic Targeting And Result Automation (2026-07-19)

- Disassembly confirms the REV00 all-magic debug branch at `0x021228` and the
  diagnostic MP-selection branch at `0x02141E`. The ignored all-magic probe
  validates the Japanese bytes before replacing `67000008` with four NOP bytes
  and `660000D2` with `600000D2`. Production `AD01` retains both stock branches.
- `tools/build_magic_application_probe_rom.py` can independently move unguarded
  Bald beside Hein. With `--stock-magic`, checksum `49A2` changes only the
  already documented Scenario 1 Bald fields and Mega Drive checksum; it leaves
  magic ownership and MP code stock. Without that option, checksum `797C`
  additionally exposes all 22 IDs for renderer diagnostics.
- `tools/capture_magic_application.py` uses the clean `battle-command` route,
  reaches Hein without crossing the moved Bald, sends repeated directions as
  separately reactivated window events, captures selection and both target
  confirmations, and reads Hein's current/max MP from runtime record 1 offsets
  `+0x38/+0x39` in GST. It advances inserted event dialogue one page at a time
  only while MP is unchanged, then closes any post-effect portrait dialogue and
  always terminates BlastEm.
- Production-faithful `49A2` proves `매직애로우`: all three inserted combat
  pages (`헤인`, `리아나`, `발드`) and Bald's post-hit line are Korean, Bald
  falls from HP 10 to 9, Hein spends MP `12 -> 11`, and the stable frame returns
  to the map. Accepted captures use prefix `captures/run/49a2_magic_00_`; the
  authoritative state is `captures/analysis/49a2_magic_00.gst`.
- Diagnostic `797C` proves the separate support spell `어택`, including page-3
  list selection, target confirmation, effect graphics, stable map return, and
  Hein MP `12 -> 10`. Captures use prefix `captures/run/797c_magic_16_`; state
  is `captures/analysis/797c_magic_16.gst`. This proves shared targeting/result
  rendering but not that Hein naturally owns Attack.
- A first `797C` Magic Arrow run appeared to leave a blank blue window after
  the hit. Repeating the path with stock branches in `49A2` rendered Bald's
  final line normally and closed cleanly. Treat the blank forced-branch frame
  as rejected diagnostic divergence, not a production translation defect, and
  do not patch the Scenario 1 dialogue record to compensate for it.
- Remaining coverage is every other magic targeting/result shape and all summon
  application/result paths beyond Elemental. The complete 22-magic and
  eight-summon name lists remain separately verified by the earlier EA22/D177
  inventory captures.
- Rebuilding production after these diagnostic-only additions retains checksum
  `AD01` and 861 custom glyphs. The complete suite passes all 326 tests.

### Summon Targeting And Runtime Application (2026-07-19)

- The REV00 summon path mirrors the magic menu. Command builder branch
  `0x020DFA` controls command ID 3, `0x021724` controls the debug eight-ID list,
  and `0x021938` accepts the selected row. `tools/build_summon_application_probe_rom.py`
  validates the Japanese and production bytes before patching only those three
  branches plus checksum. Production `AD01` remains unchanged; ignored probe
  checksum is `C41E`.
- `tools/capture_summon_application.py` reaches Hein, selects `소환`, captures
  the Korean list and target stages, checks exact MP cost, parses the generated
  member from GST, returns to its runtime coordinate, and opens its unit menu.
  It reuses the key-by-key focus recovery and dialogue handling proven by the
  magic application tool and terminates BlastEm in `finally`.
- Elemental ID 0 consumes source-table cost 5, reducing Hein from MP `12 -> 7`.
  The stable map and GST prove class `0x8D` at `(12,20)`. The resulting bottom
  status renders `엘리멘탈`, and its command menu renders `이동/공격/마법`
  without Japanese residue, broken glyphs, reset, or freeze. Accepted captures
  use prefix `captures/run/c41e_summon_00_`; authoritative state is
  `captures/analysis/c41e_summon_00.gst`.
- Runtime ownership is now concrete: each player commander group at work RAM
  `0xFF603C + index*0x60` consists of eight `0x0C`-byte member records. Hein is
  group 1; Elemental occupies member 7 at group offset `0x54`. Its member class
  is `+0x00`, map X/Y are `+0x06/+0x07`. Do not expose summon members as
  independent commanders in the future editor.
- `C41E` forces a command and list that Hein does not naturally own. It proves
  shared summon list/target/application/status rendering and runtime layout,
  not natural class ownership or persistence. IDs 1..7 and a natural summoner
  route remain pending.
- Rebuilding production after the summon diagnostics retains checksum `AD01`
  and 861 custom glyphs. The complete suite passes all 335 tests.

### Relocated Spaced Ending Visit Dialogue (2026-07-19)

- The 23 ending-visit records are distinct from the 90 outcome epilogues.
  Their Japanese starts are `0x0954E2..0x096A84`; exact unique pointer owners
  are the 23 descriptor fields at `0x095412..0x0954DC`. The earlier fixed-slot
  Korean writer preserved controls and page counts but forced most words
  together. That storage policy is superseded.
- `localization/ending_dialogue_ko.json` now records every pointer owner and
  uses natural Korean spacing. Production validates source SHA-256, pointer
  ownership, ordered `FFF7` dynamic names, `FFFD` page count, at most three
  lines per page, and at most 24 visible cells per line. It leaves the original
  Japanese record bytes intact, writes 23 variable-length Korean records from
  `0x2D0000`, and updates only their verified owners. Current production is
  checksum `E38B` with the established 861 custom glyphs.
- `tools/build_ending_dialogue_probe_rom.py` joins the 23 current records into
  an ignored `0x3D0000` stream. Only intermediate `FFFF` terminators become
  `FFFD`; the final terminator remains. Its manifest proves 23 records and 83
  pages. It redirects every visit descriptor to that stream, so it is renderer
  evidence rather than proof of all natural visit-condition selections.
- Standalone diagnostic checksum is `ACE4`; applying the unchanged adjacent
  Scenario 27 Bernhardt probe produces `F852`. The stock route reached
  preparation after 17 confirmations, command control after 22 opening pages,
  and defeated Bernhardt on the first saved attack attempt.
- `captures/run/f852_ending_dialogue_watch/240.png`, `320.png`, `400.png`, and
  `420.png` visibly verify natural spacing across early and late records.
  `470.png` renders Liana's final request, `475.png` renders
  `넌 혼자가 아니야, 리아나. 그래, 이제 혼자가 아니야…`, `477.png`
  reaches the stock forest ending, and `479.png` begins the expected SEGA
  restart. All 83 pages completed without Japanese residue, clipping, blank
  authored pages, premature termination, freeze, or unintended reset.
- `tools/jp_direct_string_inventory.py` now treats ending visits like relocated
  epilogues and credits: stale source bytes remain unmodified, but the exact
  reachable `0x2Dxxxx` pointer is reported and counts as localized. Do not
  restore the old assumption that the source interval itself must change.
- Because Mega Drive checksums cover the new ending records, rebuilding older
  diagnostics from production `E38B` changes only their identifiers: forced
  class application `A7EE`, class transition `C6C6`, all-magic `B006`, stock
  Magic Arrow `802C`, and summon `FAA8`. Their accepted AD01-derived runtime
  captures remain historical evidence; the probe-byte tests lock the current
  regenerated identifiers and still require each patch to touch only its
  documented fields.
- Final rebuild is production checksum `E38B` with 861 custom glyphs. The
  direct-word inventory classifies all 783 candidates with zero unclassified,
  the UI inventory retains 7 explicit gaps, and all 341 tests pass.

### Inline Byte Inventory, Discard Prompt, And Late Item Names (2026-07-19)

- `tools/jp_inline_byte_string_inventory.py` independently scans conservative
  `FF`-terminated half-width Japanese and ASCII runs outside the pointer-based
  inventories. It classifies 372 half-width and 77 ASCII candidates, 449 total,
  with zero unclassified. Generated outputs are
  `localization/inline_byte_strings.json` and
  `docs/inline_byte_string_inventory.md`.
- The apparent `ｱｲﾃﾑ ｾﾝﾀｸ` fragment is actually the fixed 13-cell record
  `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ` at `0x01807E`. Hook `0x01804C` now renders the relocated
  local-tile record `버릴 아이템 선택` through routine `0x2B7F20`. Static
  source, width, record, hook, and machine-code tests pass. Buying all 37
  distinct items in the complete secret shop did not reach this prompt, so its
  actual equipment/treasure access path remains `reviewed` but not live-verified.
- The 77 fixed 16-byte records at `0x05E040..0x05E50F` are a hidden sound-test
  label table, ending in `ﾌｸﾛｳ`; they are not summon, class, or item names. On
  the battle map, place the cursor at `(2,2)` and hold B for at least 60 frames.
  Flag byte `0xFFFFA6D4` then selects callback `0x00FA28`; Up/Down traverse rows,
  C plays, and B exits. Production `F91E` keeps all 77 first-byte sound IDs
  unchanged, redirects hook `0x00FB14` to renderer `0x2B7F60`, and reads 15
  direct tile words per row from `0x2BC000`. Captures
  `f91e_sound_test_load_state.png`, `_row09.png`, `_row15.png`, `_row22.png`,
  `_row37.png`, `_row60.png`, `_row76.png`, `_wrap_row00.png`, and `_exit.png`
  prove Korean/English labels, tail traversal, wraparound, and clean exit.
- A fresh item-35 purchase reproduced `그레이` followed by icon tiles. Tokens
  `76..78` crossed the stock 64-slot name window into the icon bank. A first
  overflow load at `0xE000` failed because GST VRAM proved that address is the
  plane/name table. The accepted split uses `0xB400`, the 24-slot gap between
  the item-description bank ending at `0xB400` and plane data at `0xC000`.
- Production `2282` and diagnostic `7E0B` use split name loading and bank-aware
  renderers. The renderer-aware item fingerprint is
  `9e3372724e71c96a4dcff082fb9e3f67e843408c93d375f0a0bca16dcdda822b`;
  the subsequent sound-test production build is `F91E`, and all 389 tests pass.
  The current single-display layout is captured reliably
  with direct Xlib rather than the stale-coordinate Windows DWM path.

### Full Inventory Shop Warning (2026-07-19)

- Shop purchase routine `0x02760C` calls item insertion at `0x02826C`. A return
  value of `0xFFFF` branches to `0x0276AC` and opens resource `0x0A177E`, whose
  nine visible cells at `0x0A178C` originally render `これ以上持てません`.
- The word at `0x0A178A` is the argument to the preceding `FFF9` control, not a
  visible glyph. Treating all ten words as text first produced a truncated
  three-glyph popup; this failed interpretation is now covered by the source
  token test and must not be repeated.
- Production `D8C1` keeps the control argument at `1`, assigns shared shop
  glyph-list slots 13/14 to `불/가`, and renders the exact nine-cell warning
  `아이템 구입 불가`. `captures/run/d8c1_shop_inventory_full_message_spaced.png`
  is the accepted live capture.
- `tools/build_item_shop_probe_rom.py --free-prices` changes only the original
  list selector, 37 price words, and checksum. Diagnostic `0243` purchased 40
  free daggers and reached the refusal on purchase 41. The ordinary diagnostic
  remains unchanged when the option is omitted.
- The separate discard initializer at `0x017D5E` enumerates the 40 equipment
  records at work RAM `0xC7F2` plus the newly acquired item and then selects
  callback `0x017E04`. The shop refuses before that initializer; use a treasure
  or event-award path for the remaining live proof of `버릴 아이템 선택`.

### Relocated Full-Inventory Notice And Dormant Discard List (2026-07-20)

- The ordinary shop refusal above and the stock item-award full path are
  distinct. The latter enters at `0x017CE8`, builds the notice at `0x0261AA`,
  reads its glyph pointer at `0x0261B8` and token pointer at `0x0261CC`, and
  originally uses glyph list `0x0A16B0` plus token stream `0x0A17E8`.
  Production relocates them to `0x2B8800` and `0x2B8840` so spaces are retained:
  `아이템이 가득 찼습니다` / `하나를 버려주세요`. Do not remove Korean
  spacing merely to save cells; shorten to another natural Korean phrase only
  if a later surface has a hard width limit.
- `0x0A181C` was initially misidentified as the discard choice. Live tracing
  showed that it is the general shop prompt and it now renders
  `아이템을 선택하세요`. The shared `0x0A16D4` slots still preserve
  `아이템 판매`. Captures that looked like five discardable daggers but also
  contained other shop items were the five-row purchase list, not inventory.
- The actual dormant discard initializer is `0x017D5E`, input callback is
  `0x017E04`, confirmation begins at `0x017EC4`, and its old sprite renderer
  begins at `0x017F08`. The original inline prompt is the full 13-byte record
  `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ` at `0x01807E`; the shorter suffix at `0x018082` is not a
  standalone shop string.
- Production redirects `0x017F08` to `0x2B8600`. The new renderer draws
  `버릴 아이템 선택`, five localized 16x16 item-name rows, cursor, page
  arrows, and a centered page number. The item loader stores each 16x16 glyph
  row-major, while one 2x2 Genesis sprite reads tiles column-major; the first
  implementation scrambled quadrants. The accepted renderer uses two 2x1
  sprites per glyph. `PAGE` was removed because its shared ASCII tiles are
  overwritten after the item bank loads; the stable page number remains.
- The prompt tokens live at `0x2B8880`. Its glyphs are reserved before the
  remaining names in the 64-slot primary item bank because overflow VRAM is
  reused by the shop. The complete item-name bank occupies all supported
  `88/88` slots. Static tests ensure every item and prompt token stays inside
  the loaded primary/overflow windows.
- `tools/build_discard_prompt_probe_rom.py` is diagnostic only. It combines the
  zero-price complete shop with the stock award/full path, then enters the
  otherwise unreachable discard initializer. Calling `0x017D5E` directly
  without clearing Plane A left overlapping shop UI, and loading a Korean GST
  under the Japanese ROM reset; do not repeat either approach. The accepted
  diagnostic clears Plane A, reloads the production item glyph bank, and uses
  RAM markers at `0xAEF0..0xAEFA` to audit entry, initialization, input, and
  confirmation.
- Two diagnostic branch offsets were a real source of intermittent resets:
  `BNE +0x2A` landed in `0xFFFF` padding instead of the initialization `RTS`,
  and `BEQ +0x04` landed inside a `MOVE.B`. They are now `+0x22`, `+0x06`, and
  the confirm branch is `+0x08`; a regression test computes all destinations
  and requires instruction boundaries. Confirmation reaches stock `0x017EC4`,
  records the immediate pop result `callback=0x017D38`, `stack=0xFFFF80FC`,
  clears the diagnostic input latch, and returns to idle shop callback
  `0x0249F8`. The blank blue confirmation capture is intentional because the
  diagnostic cleared Plane A; it proves stable return, not final shop layout.
- Final production checksum is `3C57`; discard diagnostic checksum is `64AD`.
  Live evidence is `captures/run/64ad_discard_selection_page1.png`,
  `_page2.png`, `_page9.png`, `_page1_row2.png`, and
  `_confirm_return.png`. Page 9 contains exactly the 41st pending dagger and
  only the previous-page arrow. No reset or freeze occurred after confirmation.
- Reserving prompt glyphs changed the renderer-aware item fingerprint, so the
  old `7E0B` acceptance was not carried forward blindly. The complete secret
  shop was recaptured as `captures/run/97e0_item_id01.png` through `_id37.png`.
  All names, descriptions, prices, and original icons remained intact. The new
  accepted fingerprint is
  `5be15eded722526f4a630855c24aaaea15bdd4cf1898c0af6acde85ba608af02`
  and diagnostic checksum is `97E0`.
- The first full recapture stalled inside the Windows DWM capture subprocess.
  `tools/capture_item_shop_inventory.py --xlib-only` now selects direct X11
  capture. Its panel detector accepts both the normal white/dark-blue palette
  level `87` and the dim Xlib level `49`; synthetic tests cover both. Use this
  option on the current single-display WSLg setup.
- Because all diagnostics derive from the current production ROM, this resource
  relocation also changes their checksums without changing their probe logic:
  forced class application `00BA`, class transition `1F92`, all-magic `08D2`,
  stock Magic Arrow `D8F8`, and summon `5374`. The probe-builder tests lock
  these regenerated identifiers and their documented patch boundaries.

### Three-Signal Inline Byte Scan (2026-07-20)

- `tools/jp_inline_byte_string_inventory.py` previously required four
  half-width Japanese or uppercase-ASCII signal bytes. It now requires three,
  increasing conservative `FF`-terminated candidates from 449 to 646 while
  retaining zero unclassified rows. This does not claim arbitrary ROM bytes are
  text; compressed payloads, packed glyphs, executable code, and numeric tables
  remain explicitly separated from user-facing strings.
- Four candidates crossed the old boundary without already having exact
  ownership: `0x0096C2` (`BEB9`) disassembles as `CLR.W D5; CLR.B ...`,
  `0x060D0D` (`DUR`) lies in item stat/effect/graphics data, `0x0A4381`
  (`ｸｹｺ`) terminates a character-index table, and `0x0A44F3` (`ｫｵｿ`)
  terminates the numeric title-layout table immediately before the NCS/title
  records. None is patched or promoted as visible Japanese text.
- Tests lock all four raw texts and categories. The remaining explicit gap is
  now byte sequences with fewer than three signal characters; those cannot be
  treated as text without an independent pointer, renderer, or runtime owner.

### Korean Title Logo (2026-07-20)

- The large Japanese `ラングリッサー` logo is compressed resource 393. Its
  original table pointer is `0x120EEE`, type is 3 (`0x009DFE` LZSS), decoded
  size is exactly 5984 bytes/187 tiles, and decoded SHA-256 is
  `58befb34120f5baa2e39868866e47cd043400663429b1db620fbeda69d3193c4`.
  Loader call `0x02D672` requests raw ID `0x8189` at VRAM `0x2000`.
- The matching layout is the 232-byte record `0x0A429E..0x0A4385` with header
  width 28 and height 8. Its source SHA-256 is
  `fdfa8f93b59bec91aa5fed8b2ac478a4cdad8aa657130c4303aab7f363b11cd4`.
  It uses `F8/F9/FA..FE/FF` controls; `0x0A4381` is therefore the tail of a
  numeric tile layout, not an inline Japanese text candidate.
- `build_title_logo_assets()` deterministically renders `랑그릿사` with
  Galmuri9 at 44 pixels, reusing title palette 2. Blank tile 0 plus 172 unique
  nonblank cells fit inside the original 187-tile output. The layout stream is
  214 bytes and fits the original 226-byte payload capacity. The decoded tile
  output remains exactly 5984 bytes.
- The type-3 resource is relocated to `0x2E0000` and both the original and
  active extended table entry 393 are updated. Resources 392, 394, and 395 and
  the 16 bytes after the layout record are locked unchanged, so the stock
  background, large `II`, angels, and adjacent title records remain separate.
- Production checksum `F9C0` is live-verified in
  `captures/run/f9c0_title_logo_live.png` and
  `captures/run/f9c0_title_logo_menu.png`. They show the Korean logo together
  with intact `PUSH START BUTTON`, `새 게임`, `불러오기`, and
  `한글화: hsp1324`. No clipping, bad palette, reset, or damaged adjacent art
  appeared. `tests/test_title_logo_resource.py` locks the source and current
  hashes, layout decoder, tile bounds, and adjacent-resource preservation.
- Diagnostics rebuilt from production now identify as forced class application
  `BAC4`, class transition `D99C`, forced magic capture `C2DC`, stock Magic
  Arrow builder `9302`, summon builder `0D7E`, and item-shop inventory `51EA`.
  These checksum changes come from the shared title resource; the probe-specific
  byte-boundary tests still require their gameplay patches to remain unchanged.

### Scenario 3 Ordinary Clear And Save-Slot Stat Patch (2026-07-20)

- `tools/build_scenario3_clear_probe_rom.py` derives diagnostic `B2BD` from
  production `F9C0`. It validates the Scenario 3 header at `0x1804F8`, the
  deployment table at `0x180510`, all ten 24-byte fixed records against the
  Japanese source, and Elwin's original `(16,16)` deployment before changing
  anything. Only enemy records 2 through 9 are changed: AT `90`, DF `0`, no
  mercenaries, and nearby initial coordinates. Events and completion code are
  untouched, and the generated ROM remains ignored.
- A recovered manual save-slot commander record is 24 bytes. Live-safe fields
  are class `+0`, level `+2`, EXP `+3`, AT `+4`, and DF `+5`.
  `tools/run_blastem_sequence.py` now accepts `--manual-slot-class`,
  `--manual-slot-at`, and `--manual-slot-df`, validates the expected source
  class and `0..99` stat range, and recomputes the slot checksum. The accepted
  run used commander 1, class `0x01`, level 1, EXP 0, AT 99, and DF 96.
- Fixed-record coordinates are not authoritative for scripted reinforcements.
  Vargas's probe record began at `(16,14)` but the stock event overwrote it to
  `(2,11)` on spawn; another hidden group was repositioned similarly. A future
  editor must label fixed deployment separately from event-scripted spawn
  coordinates instead of presenting one field as the final runtime position.
- Direct GST loading from both TURN banners and stable command quicksaves reset
  to the intro/title under this derived ROM. Editing the same live GST fields
  also reset. Do not use state-load retries here. Reconstruct a checksum-valid
  SRAM manual slot and change its stat fields before loading instead.
- BlastEm accepts speed controls `4` for 400% and `0` for 100%. The fast setting
  was stable for enemy/NPC movement and battle animation; dialogue and accepted
  captures were returned to 100%. Start-menu rows need distinct Down holds with
  about 0.6 seconds between them. Important C/Start events were reliable at
  `0.3..0.5` second holds in the remote WSLg session.
- Live play defeated Zorum and six imperial commanders, traversed the complete
  turn-3 Liana/Hein/Scott tutorial chain, later reinforcement/Vargas events,
  ordinary Vargas retreat, and every post-battle page. Evidence includes
  `b2bd_s03_turn3_entry_01.png` through `_15.png`,
  `b2bd_s03_zorum_quote_hit1.png`, `b2bdv2_s03_after_turn16.png`, and
  `b2bdv2_s03_vargas_retreat_02.png` through `_13.png` under `captures/run`.
  `b2bdv2_s03_clear_after_result.png` shows `전과보고 / POINT 1340P`,
  `_clear_save_slot2.png` shows a real `시나리오 4` save, and
  `_next_scenario_selected.png` followed by `b2bdv2_s04_route.png` proves
  ordinary Scenario 4 entry without reset or freeze.
- Runtime review found two needlessly archaic Scenario 3 lines. Event records
  `0x18964C` and `0x1898F4` now read `가자! 모두 소녀를 잡아라!` and
  `하지만 여기까지다! 소녀는 데려가겠다!`. The masked knight capture was
  rechecked at original resolution and already says the natural
  `길 위에서 조심하십시오`; it was not changed based on a scaled-screen
  misreading. Exact-text regression assertions prevent the two accepted edits
  from reverting.
- Rebuilding after those edits produces production `F661` and Scenario 3 probe
  `AF5E`. A fresh live replay defeated Zorum and the pursuing commanders to
  activate the real records rather than a standalone renderer. Evidence
  `captures/run/af5e_s03_imperial_capture_line.png` visibly renders
  `제국군지휘관: 가자! 모두 소녀를 잡아라!`, and
  `captures/run/af5e_r3_last_enemy_post_3.png` visibly renders Vargas's
  `하지만 여기까지다! 소녀는 데려가겠다!`. Neither page clips, resets, or
  contains Japanese/broken glyphs. The first launcher attempt exited after an
  Xlib `BadRRModeError`; a clean no-click relaunch completed the accepted path,
  so this is host-window handling evidence rather than a ROM reset.

### Scenario 4 Ordinary Clear (2026-07-20)

- `tools/build_scenario4_clear_probe_rom.py` derives diagnostic `79DD` from
  production `F661`. It validates the Japanese Scenario 4 header at
  `0x180688`, deployment table at `0x1806A0`, and all eleven 36-byte fixed
  records before changing anything. Only Elwin's first deployment moves from
  `(7,38)` to `(7,22)`. Morgan remains the original name/class/level and stays
  at `(7,21)`; only his AT/DF become zero and his six mercenary slots become
  empty. NPCs, other commanders, events, completion logic, and rewards are
  untouched. The probe ROM is ignored.
- A recovered manual slot entered Scenario 4 through the stock selector with
  Elwin AT 99 / DF 96. Live captures verify the current briefing,
  `SCENARIO 4` deployment label, preparation panel, stock opening, and command
  UI. The adjacent Morgan was defeated through the normal attack command, not
  an event or RAM flag edit. `captures/run/79dd_s04_after_morgan_attack.png`
  and `_post_01.png` show the real battle and Morgan response.
- Frames `79dd_s04_post_00.png` through `_40.png` cover the complete successful
  post-battle sequence: the mystery knight pursues the enemy, Sherry joins,
  the priests survive, the Cross is awarded, and the party prepares to pursue
  Morgan. Names, classes, portraits, status bars, and dialogue render without
  Japanese residue or broken glyphs. `79dd_s04_post_40.png` shows
  `전과보고 / POINT 1280P`; `_post_41.png` shows a real `시나리오 5` save,
  and `79dd_s04_next_scenario.png` proves stock Scenario 5 route-map entry
  without reset or freeze.
- This verifies the ordinary successful completion only. Immediate Morgan
  defeat intentionally bypasses later-turn mind control, priest/NPC loss,
  defeat, and other conditional paths. Scenario 4 `turn_events` therefore
  remains `progressed_current`, and `branches_endings` remains pending rather
  than being promoted from this clear probe.

### Scenario 4 Late-Turn Progression And Shika Correction (2026-07-20)

- `tools/build_scenario4_clear_probe_rom.py --mode progression` derives a
  progression-only diagnostic while preserving every original deployment
  coordinate, identity, class, level, and event. It validates the Japanese
  Scenario 4 header, deployment table, and eleven fixed records, then changes
  only enemy records 5..10 to AT 0, DF 0, and no mercenaries. The clear mode
  remains unchanged and still moves only Elwin beside Morgan.
- Diagnostic `FD8E` first reached the complete turn 1, turn 3 tablet/Alhazard,
  and turn 5 Morgan mind-control/Liana recovery sequences. Source comparison
  found that Japanese `シカシカ!` / `シ、シカーッ!` had been mistransliterated
  as `싱싱!` / `싱, 싱갸!`. They are now `시카시카!` / `시, 시카앗!`.
- Replacing those strings directly would have renumbered established custom
  glyph IDs and invalidated every later direct-string consumer. The builder
  therefore keeps the retired syllables at their original allocation points
  and appends the newly required `시카앗` glyphs after all established event,
  ending, name, UI, and title-load vocabulary. Direct-string inventory remains
  byte-stable, and the custom glyph count remains 865 (`0x7000..0x7361`).
- Current production is `39BD`; the rebuilt clear probe is `BD39` and the
  progression probe is `40EA`. Derived diagnostic checksums are forced class
  application `FE20`, class transition `1CF8`, forced magic `0638`, stock
  Magic Arrow `D65E`, summon `50DA`, and item-surface inventory `9546`.
- A fresh `40EA` replay rechecked the stock opening and all scheduled events
  through the turn 5 command menu. `captures/run/40ea_s04_turn5_events_15.png`
  visibly renders `시카시카!` without clipping or corruption. The second cry
  belongs to a separate combat condition; it is encoding-tested but remains
  live-pending with NPC-loss, defeat, and other conditional branches.
- Scenario 4 `turn_events` is now `verified_probe`. `branches_endings` remains
  `pending`, so future sessions must not repeat the already covered scheduled
  events as if they were missing branch coverage.

### Scenario 5 North-Exit Completion (2026-07-20)

- Scenario 5 has two stock victory conditions: enemy annihilation within 20
  turns or north-edge arrival within 20 turns. The Japanese header is
  `0x18083C`, deployment table is `0x180858`, and the fixed list has nine
  36-byte records at `0x180870`. The first Elwin deployment is `(13,50)`.
- `tools/build_scenario5_escape_probe_rom.py` derives diagnostic `398C` from
  production `39BD`. It validates the source and input layouts, deployment,
  and all fixed records, then changes only the first deployment Y from 50 to
  1. Enemy records, events, abilities, rewards, and completion code remain
  byte-identical. Five tests lock the exact change scope and checksum.
- Live play entered Scenario 5 through the stock selector, traversed the
  briefing, preparation, automatic arrangement, opening, and command UI. The
  stock Move command crossed the north threshold and triggered the original
  escape completion; no event or work-RAM completion flag was patched.
- The complete path reached Sherry's level/class-change screens,
  `전과보고 / POINT 1400P`, a real `시나리오 6` save, `다음 시나리오`, and
  the Scenario 6 route map. Representative captures use the `398c_s05_`
  prefix. No Japanese residue, broken name/class/UI glyph, reset, or freeze
  appeared.
- Scenario 5 `completion` is now `verified_probe`. Enemy-annihilation victory,
  later turns, defeat branches, and the remaining commander hire lists stay
  pending and must not be conflated with this north-exit evidence.

### Scenario 6 Civilian-Safe Completion (2026-07-20)

- The Japanese Scenario 6 header is `0x1809B4`, the deployment table is
  `0x1809D0`, and the fixed list at `0x1809E6` contains thirteen 36-byte
  records beginning at `0x1809E8`. Records 0..3 are Aaron and the three
  resident NPCs; records 4..12 are enemy commanders. The first stock Elwin
  deployment remains `(4,26)`.
- `tools/build_scenario6_clear_probe_rom.py` derives diagnostic `5B6B` from
  production `39BD`. It validates the Japanese and input layouts plus every
  enemy record before changing anything. Allied/NPC records 0..3 and all
  events remain byte-identical. Enemy records 4..12 receive AT 0, DF 0, and
  empty mercenary slots. Visible records 4..11 move to `(4,25)`, `(7,26)`,
  `(9,28)`, `(11,26)`, `(15,26)`, `(4,27)`, `(7,28)`, and `(9,30)` so every
  diagnostic placement is cardinally adjacent to a stock player deployment.
  Hidden record 12 retains `(255,255)` and its original event state. Five
  tests lock the allowed change surface and checksum.
- A fresh live path entered Scenario 6 through the stock selector and crossed
  the current briefing, preparation, automatic arrangement, opening, and
  command UI. Normal attack commands defeated all visible enemies while all
  three residents survived. Captures verify Hein/Warlock, Liana/Cleric, and
  Sherry/Ranger and later Lord without broken names, classes, AT/DF labels, or
  Japanese residue. Sherry's level-triggered class change is a real stock
  transition, not a probe patch.
- The complete successful aftermath is retained as
  `captures/run/5b6b_s06_victory_01.png` through `_40.png`. It covers the
  Aaron/Sherry reunion, Alhazard manuscript discussion, residents thanking
  the party, `아뮬렛을 얻었다!`, and all result transitions.
  `5b6b_s06_victory_37.png` shows `전과보고 / POINT 2050P`, `_38.png` and
  `_40.png` show a real `시나리오 7` save, and
  `5b6b_s06_next_scenario.png` proves Scenario 7 route-map entry without reset
  or freeze. Scenario 6 `completion` is now `verified_probe`; civilian-loss,
  no-Amulet, defeat, and later conditional paths remain pending.
- Read-only GST inspection established the current battle-record layout used
  by later editor work: work RAM base `0x603C`, record size `0x60`, position at
  `+0x06/+0x07`, and defeated flag bit `0x80` at `+0x02`. Player records are
  runtime 0..4 and Scenario 6 fixed records map to runtime 5..17. This mapping
  was used only to locate the final live enemies; no completion or event flag
  was modified.
- Do not repeat direct GST stat writes. Editing `+0x3A/+0x3B` in a quicksave
  appeared to load but the next input reset into the opening sequence, so the
  untouched backup was restored and the run restarted. Validated SRAM roster
  patching before launch remained stable. Also note that `detect-command`
  cannot recognize Sherry's reduced four-row post-class-change command menu;
  it toggles the panel until stopped. Exit that panel manually before invoking
  the detector again.
- The shared level-up surface visibly renders `레벨이올랐다` without the
  intended space even though source `0x82ACE` is `레벨이 올랐다.`. This is a
  renderer/composition follow-up, not evidence of missing Scenario 6 dialogue,
  and remains open for a focused shared-UI fix.

### Scenario 7 Civilian-Safe Completion And Shared Messages (2026-07-20)

- The Japanese Scenario 7 header is `0x180BBC`, its deployment table is
  `0x180BDA`, and its fixed list at `0x180BF4` contains twelve 36-byte records
  beginning at `0x180BF6`. Records 0..2 are residents, record 3 is hidden
  Keith, record 4 at `0x180C86` is Ginam, and records 5..11 are the remaining
  enemies. The first stock Elwin deployment is `(7,20)`.
- `tools/build_scenario7_clear_probe_rom.py` derives `1A2E` from final production
  `BFBA`. It validates the complete Japanese/input layout and Ginam source
  record, then changes only Ginam's AT/DF to zero, removes his mercenaries,
  and moves him from `(6,6)` to `(7,19)`. Every resident, hidden Keith, other
  enemy, deployment, and event byte remains unchanged. Five tests lock the
  permitted record/checksum surface.
- A fresh live path used the stock selector, preparation, automatic placement,
  complete opening, Elwin's normal `공격`, and the adjacent Ginam target. All
  residents survived. The aftermath covers Keith and the Blue Dragon Knights,
  the Kalzath report, resident thanks, Mirage Robe and Runestone rewards,
  Sherry's stock class-change panel, `전과보고 / POINT 1760P`, a real
  `시나리오 8` save, `다음 시나리오`, and the Scenario 8 route map. Accepted
  evidence uses `captures/run/1a2e_s07_root_menu3.png`,
  `1a2e_s07_ginam_target.png`, `1a2e_s07_after_attack.png`, and
  `1a2e_s07_system_*`; `1a2e_s07_system_67.png` and `_68.png` prove the real
  Scenario 8 save, while `1a2e_s07_route_next4.png` proves the Scenario 8
  route map. Scenario 7 `completion` is now
  `verified_probe`; later-turn conditionals, civilian-death variants, defeat,
  and alternate rewards remain pending.
- The live reward originally exposed `미라쥬로브를손에넣었다!`, while level-up
  frames exposed original table entry 0 `は` after every dynamic commander name
  plus `레벨이올랐다.`. The complete shared table starts at `0x082ACA`, not
  `0x082ACE`: entry 0 is the one-glyph particle and entry 1 is the level text.
  Production now maps entry 0 to `의`. Only the source-validated shared system
  offsets preserve `SPACE_GLYPH`; other capacity-sensitive direct strings keep
  their established behavior. Short suffixes are now ` 1 상승`, ` 2 상승`,
  ` 습득!`, ` 사용 가능`, ` 획득!`, and ` 장비했다`.
- `captures/run/1a2e_s07_system_6.png` visibly proves `미라쥬로브 / 획득!`.
  `_60.png`, `_61.png`, `_62.png`, and `_65.png` prove the universal
  `{이름}의 / 레벨이 올랐다.` composition for Elwin, Hein, Sherry, and Aaron.
  Production checksum is `BFBA`; custom glyph count remains 865
  (`0x7000..0x7361`). Compatibility vocabulary preserves every pre-existing
  glyph ID, so the accepted item-surface fingerprint remains
  `5be15eded722526f4a630855c24aaaea15bdd4cf1898c0af6acde85ba608af02`.
  Direct/shared inventories were regenerated and retain zero unclassified
  direct candidates.
- Do not load a quicksave produced by an older checksum directly into a newly
  rebuilt ROM. Loading the `9431` pre-attack GST under the intermediate `262F`
  build terminated BlastEm. The accepted replay extracted only the validated
  manual SRAM slot
  and started a fresh runtime. Also do not use `detect-command` for this path:
  one attempt reached its 30-confirmation limit and consumed Elwin's action.
  Exact single-step captures established the last opening page and normal
  command menu before the accepted attack.
- Run the full test suite and production build sequentially. Several probe
  tests intentionally write temporary derivatives through the shared build
  path, so running `build_korean_jp_probe.py` concurrently with discovery can
  leave a derivative as the final file despite passing tests. The accepted
  order is full discovery, production rebuild, probe rebuild, then inventory
  regeneration; that order finishes at production `BFBA` and probe `1A2E`.

### Scenario 8 Completion And Battle-Stable Name Tiles (2026-07-20)

- The Japanese Scenario 8 header is `0x180DA6`, its deployment table is
  `0x180DC6`, and its fixed list at `0x180DE4` contains eleven 36-byte records
  beginning at `0x180DE6`. Kramer is record 5 at `0x180E9A`, originally
  `하이로드`, LV1, AT25, DF26 at `(38,8)` with six mercenary slots. The first
  stock Elwin deployment remains `(2,7)`.
- `tools/build_scenario8_clear_probe_rom.py` derives diagnostic `2209` from
  final production `CE96`. It validates the Japanese/input layouts and complete
  Kramer record, then changes only Kramer's AT/DF to zero, removes his six
  mercenaries, and moves him to `(2,6)`. Every other fixed record, deployment,
  event, class, identity, reward, and completion byte remains unchanged. Five
  tests lock the permitted record/checksum surface.
- The first normal Elwin attack intentionally did not finish the scenario. The
  stock boss-survival path left Kramer at HP 1, spawned Vargas and Zolm, and
  played their retreat exchange. Repeated C at that point only toggles the
  enemy status popup; this is not a hang. End the turn through Start, let the
  stock enemy/tutorial sequence return to Elwin's command menu, then attack the
  adjacent Kramer a second time. The second normal attack completed the stage.
- Captures `2209_s08_after_attack.png`, `2209_s08_event_11.png`,
  `2209_s08_turn2_command2.png`, `2209_s08_kramer_second_target.png`, and
  `2209_s08_after_second_attack.png` cover both attacks and the real
  reinforcement/status path. `2209_s08_victory_23.png` shows
  `전과보고 / POINT 3020P`, `_24.png` and `_26.png` show Scenario 8 then the
  real `시나리오 9` save, and `2209_s08_next_scenario.png` proves stock
  Scenario 9 route-map entry without reset or freeze. Scenario 8 `completion`
  is `verified_probe`; timeout, defeat, and other conditional outcomes remain
  pending.
- The first `132D` run exposed graphic fragments in `발가스/제너럴` because
  Scenario 8 reinforcement graphics overwrite the previous tiles for `가`,
  `스`, and `럴`. Production remaps them to unused tail tiles
  `0x05F0..0x05F2` in the final dynamically restored byte-font bank while
  consuming retired iterator slots `0x0443/0x0444` so every later established
  mapping, notably `렌`, remains byte-identical.
- The intermediate `9A2C` replay proved `발가스/제너럴`, but its result screen
  exposed a second owner collision: `스코트` and `키스` ended in red sprite
  fragments. The result wrapper at `0x2B7D00` restored extension segments 1..4
  only. `BYTE_UI_ENDING_RESULT_RELOAD_SEGMENT_INDICES` now includes segment 5,
  and final `2209_s08_victory_23.png` shows both names intact.
- `tools/build_scenario8_status_probe_rom.py` is renderer-only evidence. The
  first attempt cleared the hidden Vargas record's bit and set coordinates,
  but the game correctly did not deploy an event-owned record. The retained
  method instead gives the already relocated clear-target Kramer the stock
  Vargas name and General class IDs. It changes no production ROM and must not
  be cited as natural event-placement or completion evidence.

### Scenario 9 Ordinary Clear (2026-07-20)

- The Japanese Scenario 9 header is `0x180F72`, its deployment table is
  `0x180F92`, and its fixed list at `0x180FB0` contains thirteen 36-byte
  records beginning at `0x180FB2`. Laird is record 3 at `0x18101E`, originally
  name ID `0x11`, class ID `0x43` (Silver Knight), AT36, DF26 at `(14,15)`.
  The first stock player deployment remains Elwin at `(8,28)`.
- `tools/build_scenario9_clear_probe_rom.py` derives diagnostic checksum
  `AF92` from production `CE96`. It validates the Japanese and input layouts,
  the deployment pointer and complete Laird record, then changes only Laird's
  AT/DF to zero, removes his six mercenaries, and moves him to `(8,27)`.
  Every other fixed record, deployment, event, identity, class, reward, and
  completion byte remains unchanged. Five tests lock this permitted surface
  and exact checksum.
- A normal Elwin `공격` selected the adjacent Laird and completed the stock
  stage. `af92_s09_laird_target_selected.png` shows `레아드 / 실버나이트`;
  `af92_s09_after_laird_attack.png` begins the real aftermath. The complete
  retreat, Leon/Kalxath defense, Jessica/Alhazard explanation, commander
  level-up sequence, and result proceeded without Japanese residue, reset, or
  freeze. `af92_s09_post_62.png` shows `전과보고 / POINT 3060P`,
  `af92_s09_post_64.png` shows the real `시나리오 10` save, and
  `af92_s09_next_scenario.png` proves entry to the stock Scenario 10 route map.
  Scenario 9 `completion` is `verified_probe`; timeout, defeat, later-turn
  conditionals, and other branches remain pending.
- BlastEm ran at 960x720 for this session. The current automation's fixed
  320x240 crop coordinates therefore failed to recognize the visible command
  menu and could enter the inner order submenu or consume an action. Exact
  manual inputs after a clean restart produced the accepted evidence. This is
  a host detector scaling bug, not a ROM reset or command-menu regression;
  normalize captures before fixed-coordinate detection in a later tooling fix.

### Uppercase Project Credit And Selector VRAM Collision (2026-07-20)

- The current title and synthetic final staff-roll records use the requested
  uppercase ID: `한글화: HSP1324` and `한국어화 HSP1324`. The former custom
  lowercase `h/p/s` bitmap overrides were removed, so `HSP1324` now uses one
  coherent stock uppercase/digit font. Production checksum `6C85` is live
  verified in `captures/run/6c85_title_uppercase_live_3.png`. Older lowercase
  screenshots remain historical evidence for their checksums, not the current
  display contract.
- The mark that looked like `렛` or `렌` before selected preparation rows was
  not a text token or bad cursor offset. Plane tilemap inspection found the
  selector at tile `0x5F8`. In the broken Korean GST, tiles `0x5F8..0x5FB`
  exactly matched custom glyph ID `0x7234` (`뮬`); the Japanese GST contained
  the stock triangle there. The item-name overflow loader used 24 nominal
  slots at VRAM `0xB400..0xBFFF`, and glyph index 86 therefore began at
  `0xBF00`, overwriting selector tiles `0x5F8..0x5FF`.
- Production now stops the overflow bank at exclusive address `0xBF00`, giving
  22 safe slots. The dormant discard heading is the shorter `버릴 아이템`,
  reducing the item-name bank to exactly 86 glyphs (64 primary + 22 overflow)
  without changing any item name. `선택` remains in the shared local table for
  sound-test commands and does not enter the item-name overflow bank.
- Fresh captures `captures/run/6c85_cursor_fixed_prep.png` and
  `captures/run/6c85_cursor_fixed_arrange.png` show the normal white triangle
  before `용병고용` and `지휘관배치`; the latter also preserves `SCENARIO 1`.
  A post-fix GST comparison proves all eight selector tiles `0x5F8..0x5FF`
  byte-identical to the Japanese runtime. The regression test locks the
  `0xBF00` boundary, selector tile index, 22-slot capacity, and actual loader
  end.
- Because the loader boundary is part of the renderer-aware item fingerprint,
  the former `97E0` acceptance was not reused. Complete-secret-shop diagnostic
  `C80E` was freshly captured as `captures/run/c80e_item_id01.png` through
  `_id37.png`; all names, descriptions, prices, and source icons are intact,
  including `그레이프니르`, `걀라르호른`, and `아뮬렛`. The accepted new
  fingerprint is
  `eb1d9aadc20f3a46a8ab3f3b1d7cb757619dbe28551f52d757cce6814027b19c`;
  the rebuilt zero-price derivative is `9607`.
- Discard diagnostic `94DB` reused a copied, isolated full-inventory GST only
  to avoid repurchasing 40 items. Loading it under the new diagnostic redrew
  the current `버릴 아이템` heading, navigated from page 1 to page 9, retained
  normal cursor/page arrows, and returned stably after confirmation. Evidence
  is `captures/run/94db_discard_reused_state.png`,
  `94db_discard_page9.png`, and `94db_discard_confirm_return.png`. It is
  renderer/capacity evidence, not a natural event-award ownership proof.
- Do not repeat the two discarded cursor experiments. `Cursor Backing Probe`
  (`5DD7`) blanked preceding glyph-list words and did not change the mark;
  `Cursor Spacing Probe` (`0192`) moved the label but left the mark intact.
  They are ignored diagnostics and are not production fixes.

### Resolution-Aware Battle Command Detection (2026-07-20)

- Scenario 9's real 960x720 outer command panel in
  `captures/run/af92_s09_outer_command.png` occupied about 46.4% of the broad
  blue crop and only 4.1% of the command-interior white-text crop. The former
  fixed thresholds therefore rejected it even though the ROM screen was
  correct.
- `battle_command_menu_visible()` now accepts the observed high-resolution
  proportions and also requires the narrow command panel's right gold frame
  in the normalized source-pixel band `x=94..106, y=42..144`. Wider dialogue,
  preparation, result, route, and title panels place their right edge outside
  that band and remain rejected.
- Detector tests cover the sparse 960x720 four-row panel and the formerly
  risky wide result-panel shape. Direct checks accept the real Scenario 3 and
  Scenario 9 command captures while rejecting Scenario 9 dialogue,
  preparation, result, and route/title captures. This is host automation only;
  it changes no ROM byte.

### Scenario 10 Monster Clear And Editor Mapping (2026-07-21)

- The Japanese Scenario 10 header is `0x181186`, its deployment pointer at
  header `+0x08` resolves to `0x1811A2`, and the first stock Elwin deployment
  is `(5,28)`. The fixed list contains thirteen `0x24`-byte records beginning
  at `0x1811BA`: two pirates and Lester at indices 0..2, five Scylla at 3..7,
  three Great Slime at 8/10/12, and two Werewolf at 9/11. Monster source
  coordinates are hidden `(255,255)` until the stock event places them.
- Read-only GST inspection maps Scenario 10 fixed records 0..12 to runtime
  commander groups 5..17 at work RAM `0x603C + group*0x60`; player groups are
  0..4. Runtime class IDs are `0x53` Scylla, `0x51` Great Slime, and `0x50`
  Werewolf. The stock TURN 3 event placed groups 8..17 at `(17,14)`, `(5,20)`,
  `(7,21)`, `(27,17)`, `(25,21)`, `(28,28)`, `(14,29)`, `(4,29)`, `(22,30)`,
  and `(12,30)` before their normal AI movement. These are the verified
  scenario/editor ownership facts; summon members remain separate member
  records and must not be exposed as commanders.
- Diagnostic `4591`, derived from production `6C85`, changed only monster
  AT/DF, their six mercenary slots, Elwin's initial deployment, and the ROM
  checksum. It did not alter an event or completion flag. The real TURN 3
  spawn occurred, normal player attacks killed four nearby monster
  commanders, and the unmodified pirate AI killed the remaining Scylla while
  they had AT/DF zero. The final normal Elwin attack defeated the last Great
  Slime. Captures `4591_s10_monster_spawn_dialogue.png` through
  `4591_s10_victory_16.png` retain the complete later-turn and victory path;
  `_victory_17.png` is `전과보고 / POINT 2470P`, `_victory_19.png` is the real
  `시나리오 11` save, and `4591_s11_route_entry2.png` proves route entry
  without reset or freeze. Scenario 10 `turn_events` and `completion` are now
  `verified_probe`; defeat, pirate-loss, retreat, and other conditional paths
  remain pending.
- The accepted run exposed orphan punctuation/word wrapping in four records.
  Production shortens `0x1960AC`, `0x1960D4`, `0x196DE4`, and `0x196F1E` so a
  period/question mark or the final syllable of `한다` cannot occupy a line by
  itself. It also exposed corrupted first Latin glyphs in shared level-up
  `AT가/DF가/MP가`. The direct renderer already owns stable Japanese-source
  Latin tokens, so production `33EF` reuses `006D 006E`, `005F 0097`, and
  `00AB 0070` respectively and appends only the Korean `가`. Tests lock the
  native prefixes; live post-level verification of `33EF` remains pending.
- `tools/build_scenario10_clear_probe_rom.py` is now narrower than the accepted
  exploratory run. It validates the complete Japanese/input layout and every
  monster record, preserves stock deployment and all events, and changes only
  monster AT/DF plus their mercenary slots. Against production `33EF` it builds
  ignored diagnostic checksum `0CF8`. Do not reintroduce the `(10,26)` Elwin
  deployment: live play proved the monster reveal is the fixed TURN 3 event,
  not a movement trigger.
- Do not repeat direct GST stat/event writes. The working method was a fresh
  ROM path plus source-validated diagnostic records. Save-state editing can
  load under a mismatched callback and reset at the next input, so GST was used
  only for read-only record/coordinate inspection and ordinary quicksave
  recovery.

### Occlusion-Safe BlastEm Capture (2026-07-21)

- Standard desktop screenshots captured Chrome whenever it covered BlastEm.
  `capture_blastem_window.py --xlib-only` reads the BlastEm X11 client directly
  and remained correct while the window was fully occluded. The sequence
  runner now exposes `--xlib-capture` and forwards it to every detector/capture
  call; `--send-event` keeps emulator input window-local without stealing the
  user's foreground focus. Tests cover that forwarding path.
- Fresh BlastEm intro playback can outlast the old 12-second fixed delay. A
  reliable selector route waits for the intro, sends START to skip it, sends
  START again for the title menu, enters LOAD, selects the Scenario 2 SRAM,
  and only then enters the selector code. Sending the code during the intro
  can land in name entry and must not be treated as a ROM failure.

### Scenario 11 Fire Route Clear And Scenario 12 Entry (2026-07-21)

- `tools/build_scenario11_clear_probe_rom.py` derived live diagnostic `D091`
  from production `33EF`. It validates the Japanese Scenario 11 header at
  `0x18138E`, deployment table at `0x1813AC`, and all eleven `0x24`-byte fixed
  records before changing anything. `--safe-clear-layout --safe-jessica`
  changes only the six player deployment coordinates, Jessica's fixed X/Y,
  enemy records 1..10 AT/DF/mercenaries/level/class, visible enemy coordinates,
  and the ROM checksum. Jessica's identity, stats, class, mercenaries, and every
  event/completion handler remain unchanged. Twelve tests lock the permitted
  bytes. Production `C3D8` rebuilt the same probe fields as `607A`; the current
  Scenario 12 dialogue build `96D5` rebuilds them as `3377`. `D091` remains the
  checksum of the retained live-clear evidence rather than a current derivative.
- The accepted layout puts the six players at `(18,20)`, `(17,20)`, `(19,20)`,
  `(18,19)`, `(17,19)`, `(19,19)`, Jessica at `(18,18)`, and fixed visible
  enemies around them. The final hidden enemy record keeps `(255,255)`. Live
  `d091_retreat_20.png` proves the stock Egbert retreat event placed the
  unmodified Jessica record at the safe coordinate with her original stats.
- Read-only GST inspection confirmed that fixed coordinates are not final
  runtime coordinates. Players occupy runtime groups 0..5, Jessica group 6,
  and fixed enemy records 1..10 map to runtime groups 7..16. The stock event
  moved fixed enemy record 7 to `(17,30)`; it advanced to `(17,24)` before the
  final fight. Hidden fixed record 10 appeared as runtime group 16 at `(21,20)`
  and moved to `(20,20)`. The editor must continue labeling X/Y as read-only
  initial placement, not a guaranteed spawn or turn coordinate.
- The complete live route traversed Egbert's retreat, the turn-6 fire exchange,
  TURN 7 through TURN 9, and the hidden reinforcement without Japanese text,
  broken names/classes, reset, or freeze. Elwin normally defeated the southern
  messenger and Sherry normally defeated the final reinforcement. Captures
  `d091_turn9_battle.png`, `d091_turn9_enemy16_target.png`, and
  `d091_turn9_enemy16_battle.png` retain those normal attack paths.
- Victory captures `d091_s11_victory_01.png` through `_17.png` retain the stock
  aftermath. `_18.png` is `전과보고 / POINT 3770P`, `_20.png` writes a real
  `시나리오 11` slot before the dynamic save update, `_21.png` visibly shows
  the resulting `시나리오 12` slot, and `d091_s11_next_selected.png` selects
  `다음 시나리오`. `d091_s12_route.png`, `d091_s12_title.png`, and
  `d091_s12_brief_00.png` through `_04.png` prove ordinary Scenario 12 route,
  `성지 레이텔`, complete current briefing, and preparation entry. Scenario 11
  `turn_events` and `completion` are now `verified_probe`; alternate loss and
  conditional branches remain pending.
- The movement/attack input sequence was clarified during this run. Direction
  events must use a short hold such as `@0.02`; `0.25` auto-repeats and skips
  several map cells. From a commander, C opens the outer menu, C selects
  `이동`, short directions choose the destination, C stages the move, short
  directions place the cursor on the adjacent enemy, and C starts battle. B
  cancels a staged move and restores the original runtime coordinate. Start
  menu rows still require four separate Down events with about 0.6 seconds
  between them before choosing `턴 종료`.
- Do not retry the rejected `3FE1` layout that hid fixed enemy records 2..9; a
  Scenario 11 slot stayed black immediately after load. Earlier `D079` left
  Jessica exposed to the fire deadline. `D085` reached TURN 8 and reduced the
  visible force but retained timing-sensitive Jessica placement. The built-in
  enemy-control code did not enable control through either direct events or
  focused XTest. Direct live GST HP/stat edits were also unstable at later
  transitions. `D091` plus source-validated SRAM roster fields was the accepted
  route; GST remained read-only except for ordinary quicksave recovery.
- Scenario 11 runtime review exposed an orphan final period at event address
  `0x1986FE`. The accepted text is now `뭐라고요!? …알겠습니다`; an exact
  address test prevents the period from returning as a centered line by itself.
  The preparation detector's ornate-divider gold threshold is now `0.14`
  because the real Scenario 11 divider measures about 14.9%; the former 18%
  threshold could advance into the hire menu instead of stopping on preparation.
- Rebuilding that one reviewed text change produces production checksum `C3D8`
  with 864 custom glyphs. The direct Scenario 11 renderer at
  `captures/analysis/s11_render_c3d8/scenario_11_pages_07.png` shows physical
  page 85 ending cleanly at `…알겠습니다` with no orphan punctuation. This is
  static renderer evidence; the surrounding D091 live clear remains the runtime
  evidence for the unmodified event flow and completion handler.
- `tools/scenario_data.py` now has a direct JSON CLI for one, several, or all 31
  scenarios. Its schema separates editable `level/at/df/class_id/mercenaries`
  from read-only identity, role, offset, hidden state, and coordinates, and
  explicitly warns that event scripts may override initial X/Y. The existing
  `editor/server.py` GUI continues to use the same validated data layer and
  writes a separate ROM rather than overwriting production.

### Scenario 12 Guardian Probe And HUD Overlap Diagnosis (2026-07-21)

- `tools/scenario_data.py` no longer labels every Scenario 2+ fixed record as
  generic `배치`. The read-only byte at fixed-record offset `+0x08` is exposed
  as `side_id` and maps observed values `01/03/04/08` to `아군 이벤트`,
  `NPC / 아군`, `적군`, and `특수 진영`. Tests cover Scenarios 6, 12, 15,
  and 22. This restores the editor GUI's enemy filter without guessing from a
  unit sprite or record position.
- `tools/build_scenario12_clear_probe_rom.py` validates the Japanese Scenario
  12 header `0x181554`, deployment table `0x181574`, and all eleven fixed
  records. Its normal mode changes only enemy AT/DF and mercenary slots. The
  optional compact mode additionally moves seven player deployments and the
  ten initially visible guardians; identities, classes, levels, hidden
  Egbert, and event handlers remain unchanged. Production `96D5` builds the
  current compact derivative as checksum `E14C`.
- The accepted live `0E4F` run used the earlier compact derivative made from
  production `C3D8`. It entered Scenario 12 from the real Scenario 11 save,
  completed automatic deployment and the full opening, normally defeated all
  ten visible guardians over ten turns, and triggered the stock hidden Egbert
  and Dark Rod sequence. Victory dialogue is currently paused before the
  result/save transition, so Scenario 12 completion is not yet promoted to
  `verified_probe`.
- The user's reported colored shape above Hein's `D99`, between DF and MP, is
  not a Korean glyph. Enlarging `0e4f_s12_victory15.png`, `_20.png`, and
  `_21_xlib.png` shows a 16x16 map-unit sprite crossing the lower status plane;
  `MP13` remains complete. It appears on Hein pages only after compact player
  placement and is absent from stock-coordinate Scenario 12 captures such as
  `c765_s12_opening_elwin.png`. Do not patch the byte font or status renderer
  for this diagnostic-only overlap. Use the normal probe (stock player
  coordinates) for UI evidence, and treat compact-layout screenshots with a
  sprite over the HUD as route evidence only.
- Live review found several awkward or orphaned Scenario 12 lines. Production
  `96D5` changes `0x199638`, `0x199DCA`, `0x199E26`, `0x19A67A`, `0x19A6D6`,
  and both source-only Liana-return records `0x19A87E/0x19A8F4`. The latter now
  says `{0002}가 납치됐다면 지금까지 싸운 보람이 없어`; five records omit
  a final period that previously occupied a line by itself. Exact translation
  tests lock the accepted wording. These edits have passed the reviewed-event
  and target-residue tests plus a complete production build, but still need
  live verification after the foreground-input pause ends.

### Scenario 13 Clear Probe Prepared Offline (2026-07-21)

- The Japanese Scenario 13 header is `0x181720`; header `+0x08` resolves to
  deployment table `0x181740`. After the table's leading word, the seven stock
  player deployments are `(16,3)`, `(20,2)`, `(24,2)`, `(28,3)`, `(22,4)`,
  `(20,6)`, and `(24,6)`. The fixed list contains thirteen `0x24`-byte enemy
  records at `0x181760..0x181933`.
- Fixed record 8 is `조름/하이로드`, LV9, AT29, DF31 at `(19,27)`. Records
  10..12 are hidden `(255,255)` reinforcements: `발가스/제너럴`,
  `레온/로얄가드`, and `레아드/실버나이트`. Their Japanese IDs, classes,
  levels, hidden flags, and source mercenary IDs are locked by tests rather
  than inferred from sprites.
- `tools/build_scenario13_clear_probe_rom.py` validates the complete Japanese
  and production layouts before writing. It changes every enemy's AT/DF to
  zero, clears only their six mercenary slots, and moves only Zorum from
  `(19,27)` to `(16,4)`, immediately below stock Elwin at `(16,3)`. The player
  deployment table, all identities/classes/levels, hidden reinforcements, and
  event handlers remain byte-identical. Production `96D5` builds diagnostic
  checksum `81E3`, SHA-256
  `4ca123e8600626a1bbff19dfb0abfa6124d5df80879adbae5baca16545b7c5b9`.
- The intended live sequence is not an immediate boss kill: advance ordinary
  turns first to retain the Fire Dragon Corps tactics and hidden reinforcement
  dialogue, then normally attack adjacent Zorum after the late events, retain
  every victory page, result, a real Scenario 14 save, and route entry. Until
  that run is complete, Scenario 13 `turn_events` remains
  `progressed_current` and `completion` remains `pending`.
- This implementation and its six focused tests were completed without
  launching, focusing, or sending input to BlastEm while the user was playing
  another game.
