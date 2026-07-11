# Full Localization Plan

The active Goal is full Korean localization of the Japanese Mega Drive ROM.
Work is split into stages so each checkpoint can be built, tested, live-checked,
documented, committed, and pushed independently.

## Stage 1: Inventory And Coverage

- Identify every text pointer, glyph list, token stream, and compressed UI resource.
- Generate a per-scenario event-page inventory and Japanese-residue report.
- Inventory shared class, item, and actor/NPC/monster byte-string tables, including
  raw-string changes and global-font collision risks.
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
