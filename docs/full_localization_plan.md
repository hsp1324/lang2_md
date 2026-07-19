# Full Localization Plan

The active Goal is full Korean localization of the Japanese Mega Drive ROM.
Work is split into stages so each checkpoint can be built, tested, live-checked,
documented, committed, and pushed independently.

## Current Stage Status (2026-07-19)

The broad Goal below remains the final acceptance contract. Day-to-day work must
follow this status table so a resume does not repeat already accepted work.

| Stage | Status | Resume rule |
| --- | --- | --- |
| 1. Inventory and coverage | Complete baseline | 783 direct-word, 348 pointer-referenced direct-byte, and 449 conservative inline-byte candidates are classified with zero unknowns. Re-scan only after reachable pointer or builder coverage changes. |
| 2. Shared UI and global names | In progress | 119/120 declared patches differ intentionally; work only from the six explicit gaps in `docs/ui_patch_surface_inventory.md`. |
| 3. Scenarios 2-10 | Static/opening complete; route completion pending | Use pending `completion` and `branches_endings` cells in the generated runtime inventory. |
| 4. Scenarios 11-20 | Static/opening complete; route completion pending | Use pending `completion` and `branches_endings` cells in the generated runtime inventory. |
| 5. Scenarios 21-31 and endings | Static/opening complete; route completion pending | The 90 epilogues and 23 ending-visit records are structurally complete and renderer-verified; natural branch selection remains distinct evidence. |
| 6. Full regression and release | Pending | Start only after the runtime inventory has no required pending paths and the six UI gaps are resolved or explicitly accepted. |

Stage 2 complete-item checkpoint is closed. Production checksum `2282` splits
the 84 item-name glyphs at the stock 64-slot VRAM boundary: slots `0..63` stay
at `0x2000`, while slots `64..83` use the free `0xB400..0xBDFF` range before
the plane table at `0xC000`. Both shop-list renderers and the purchase-popup
builder select the correct bank, so late names and messages no longer turn into
item icons. Diagnostic checksum `7E0B` has the renderer-aware accepted surface
fingerprint; price-only derivative `4C04` verifies `그레이프니르`,
`걀라르호른`, `아뮬렛`, and the `단검` regression in BlastEm. The earlier
`D304` capture set still covers all 37 descriptions, prices/stat lines, and
visible icons. Decoded icon resource 391 remains byte-identical to the Japanese
ROM. Resume Stage 2 only from the six gaps in
`docs/ui_patch_surface_inventory.md`.

Accepted completed work is a regression contract, not a recurring task. Re-run
it only when a later change shares its renderer/data ownership or an automated
test fails. The authoritative machine-readable state is
`localization/runtime_verification.json`; regenerate
`docs/runtime_verification_inventory.md` after changing it.

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
- Scan conservative inline `FF` byte strings independently of pointer tables. The
  77-row hidden sound-test label table is now localized and live-verified; retain
  its source hash, sound-ID preservation test, and `(2,2)` plus held-B access proof.
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
  ending, credits, and error/status UI paths.
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
- Keep `localization/runtime_verification.json` and the generated
  `docs/runtime_verification_inventory.md` current; static modification does
  not replace per-scenario live verification.
- Expand the scenario editor only for fields whose runtime ownership is proven.
- Produce the final documented build, commit, and push.

`LV`, `AT`, `DF`, `MP`, and `HP` may remain as standard game abbreviations. Large
English labels may remain only when they are conventional, space-constrained, and
explicitly recorded as intentional rather than missed Japanese text.
