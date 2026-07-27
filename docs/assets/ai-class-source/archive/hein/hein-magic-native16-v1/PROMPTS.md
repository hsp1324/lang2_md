# Hein magic native16 v1

## Generation mode

- Generator: Codex built-in image generation
- Mode: `precise-object-edit`
- One independent image-generation call per class
- Background: flat exact `#ff00ff`
- Output use: native logical 16×16 map-sprite source

Each call used only three images:

1. the accepted existing AI class design from
   `editor/static/ai-class-sprites/source-cells/5-XX.png`;
2. the class's `XX-original-full-ratio.png`;
3. the class's `XX-masked-identity.png`.

The existing AI image supplied equipment, robe, staff and color design. The
original supplied complete 16×16 scale and placement. The masked image was the
absolute head, hair, face and eye identity lock.

## Common prompt

Rebuild the accepted design as a true logical 16×16 Mega Drive / Genesis
tactical-RPG map sprite. Preserve the large blue/cyan head, face direction,
black eye and adjacent white eye at the original size and coordinate. Keep the
head about one third of the full figure and connect it directly to the neck
and shoulders.

Use the complete 16-column space intelligently. Put a fully connected staff,
including crystal, hand and shaft, along the far right without clipping it.
Open the left sleeve and lower robe toward the left. Keep a compact centered
torso and a broad readable robe hem. The complete figure must be 15–16 logical
pixels tall and 14–16 logical pixels wide.

Every logical pixel must be one large, uniformly sized square block. Use hard
pixel clusters, flat colors, a strong dark outline and a small bright
4bpp-style palette. Do not use a small centered figure, narrow robe, detached
staff, micro-pixels, antialiasing, gradients, soft shading, text, labels,
extra figures or scenery.

## Class-specific direction

### 09 Sorcerer

Preserve the dark navy and royal-blue robe, gold collar and trim, and
purple-red orb staff. Keep the complete orb and shaft on the right and make
the dark robe hem broad and symmetric.

Accepted output:
`raw/09-sorcerer-ai.png`

### 13 Mage

Preserve the vivid royal-blue robe, cyan sleeve highlights, pale-blue trim,
gold shoulder clasp and green crystal staff. Use two readable blue/cyan robe
folds. Keep Mage simpler and lighter than Archmage.

Accepted output:
`raw/13-mage-ai.png`

### 14 Archmage

Preserve the bright white/cobalt/cyan ceremonial robe, broad gold collar and
belt, and large blue crystal staff. Make it visibly broader, brighter and
stronger than Mage. Use the full 16-column width, a wide white/cobalt hem with
three simple folds, broad mantle and complete crystal staff.

Accepted output:
`raw/14-archmage-ai.png`

## Post-processing

The connected magenta-keyed figure is fitted with nearest-neighbour sampling
to 16×16. Exact current user-mask and protected eye pixels are then restored
from the ROM original. The remaining 4bpp slots retain the AI equipment hues
after snapping them to Mega Drive channel levels.

Final files:

- `logical16/09-sorcerer.png`
- `logical16/13-mage.png`
- `logical16/14-archmage.png`
- `hein-magic-ai-and-16x16.png`
