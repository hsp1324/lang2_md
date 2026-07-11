# Full Localization Plan

The active Goal is full Korean localization of the Japanese Mega Drive ROM.
Work is split into stages so each checkpoint can be built, tested, live-checked,
documented, committed, and pushed independently.

## Stage 1: Inventory And Coverage

- Identify every text pointer, glyph list, token stream, and compressed UI resource.
- Generate a per-scenario event-page inventory and Japanese-residue report.
- Inventory shared class, item, and actor/NPC/monster byte-string tables, including
  raw-string changes and global-font collision risks.
- Inventory shared condition, scenario-description, item, magic, summon-class,
  mercenary-battle-name, and status-message word resources with explicit review flags.
- Inventory every builder-declared UI patch and compressed byte-font relocation;
  keep unresolved UI discovery categories explicit until their ROM ownership is proven.
- Parse and decompress the complete resource table with its type-specific RLE,
  tile-plane, and LZSS paths independently of UI assumptions; record size, hash,
  and pointer changes while leaving unknown ownership unknown.
- Link immediate resource-loader call sites to table IDs and retain dynamic call sites
  without guessing their runtime-selected IDs.
- Scan direct `FFFF` word-string candidates outside event blocks, classify known
  owners, and require render/code-reference proof before patching unknown candidates.
- Keep full ending-dialogue pages and character epilogues as explicit translation
  work even when a shorter suffix inside the same page has already been patched.
- Track word-swapped pointer tables separately from normal big-endian pointers;
  validate source hashes and duplicate-pointer semantics before writing them.
- Map name-entry initialization, editable-buffer, selectable-grid, and confirmation
  resources separately; a Korean default name is not completion of Korean input.
- Preserve shared class-change glyph indexes so the long prompt, short title,
  mercenary label, and magic label can be localized without rewriting layout code.
- Keep machine-readable addresses and a human-readable coverage table.

## Stage 2: Shared UI And Global Names

- Finish character, NPC, class, mercenary, item, magic, summon, and system-message names.
- Finish prep, hire, equipment, shop, deployment, battle, Start, save/load, class-change,
  ending, and error/status UI paths.
- Preserve the verified Scenario 1 byte-font slots and shared graphics.

## Stage 3: Scenarios 2-10

- Translate every event page, condition, branch, and battle message.
- Validate scenario transitions and representative combat/event paths in BlastEm.

## Stage 4: Scenarios 11-20

- Translate every event page, condition, branch, and battle message.
- Validate scenario transitions and representative combat/event paths in BlastEm.

## Stage 5: Scenarios 21-31 And Endings

- Translate every event page, hidden route, secret scenario, branch, and ending.
- Validate every reachable ending and special route.

## Stage 6: Full Regression And Release

- Reduce the Japanese-residue report to zero intentional untranslated entries.
- Run all static checks and full-route emulator regression captures.
- Expand the scenario editor only for fields whose runtime ownership is proven.
- Produce the final documented build, commit, and push.

`LV`, `AT`, `DF`, `MP`, and `HP` may remain as standard game abbreviations. Large
English labels may remain only when they are conventional, space-constrained, and
explicitly recorded as intentional rather than missed Japanese text.
