# Jessica Zarvera fresh sample variants

This folder contains five independent sample designs for Jessica's Zarvera class (`10:26`). It is intentionally isolated from the editor manifest and the production aggregate.

## Inputs

Every AI call used only these two references:

- `jessica-zarvera-summoner-ai-v1-fresh/references/10-26-zarvera-rom-original-32x.png`
- `jessica-zarvera-summoner-ai-v1-fresh/references/10-26-jessica-identity-only-32x.png`

No previous AI output or common class guide was supplied. Variant 2's first generation was rejected for a small head and tall body; the accepted replacement was generated again from the same two references only and is the image saved here.

## Layout

- `raw-ai/`: original built-in imagegen output, including the green chroma background
- `ai/`: the same accepted outputs after chroma-key removal
- `prompts/`: the five selected generation prompts
- `logical16/`: manually repixelled native 16x16 sprites
- `previews/`: exact 16x nearest-neighbor enlargement of each native sprite
- `all-ai-variants.png`: one-board comparison of the five accepted AI concepts
- `all-logical16-variants.png`: one-board comparison of the five native 16x16 results
- `all-ai-and-logical16-variants.png`: paired AI/native comparison board
- `validation-report.json`: per-variant validation details

The logical sprites restore all 73 pixels of Jessica's current identity mask at the original, unshifted coordinates. The production aggregate applies Jessica's final `(+1, 0)` identity translation later; these samples do not apply that shift twice.

Rebuild the logical sprites and comparison boards with:

```bash
python3 tools/build_jessica_zarvera_sample_variants.py
```
