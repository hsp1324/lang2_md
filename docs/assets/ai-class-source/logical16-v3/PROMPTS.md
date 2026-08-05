# Logical16 v3 AI generation record

## Mode and input policy

- Generator: Codex built-in image generation
- Mode: `precise-object-edit`
- One fresh 4×4 sheet was generated for each non-Elwin commander.
- Image inputs for each sheet were limited to that commander's
  `logical16-v3-guides/<name>/original-reference-board.png` and
  `masked-identity-board.png`.
- No previous AI sheet or Elwin image was supplied as an image input.
- Elwin was intentionally left on the accepted `elwin-native16-v16` sources.

## Common generation instruction

Edit the supplied original 4×4 reference board into a Mega Drive / Genesis
tactical-RPG class sheet. The occupied cells and their coordinates must stay
exactly aligned with the reference board. In every occupied cell draw one
complete character that already behaves like a true logical 16×16 sprite:
at most 16 logical columns and 16 logical rows, with every logical pixel
represented by one large, flat, uniformly sized square block. Use hard edges,
simple connected shapes and a small bright console palette. Do not use
micro-pixels, antialiasing, gradients, soft shading, painterly detail, text,
labels, scenery, borders, detached hands or detached equipment.

Treat the original-reference board as the absolute full-sprite scale,
placement, pose, face direction and head-to-body proportion reference. Treat
the masked-identity board as an absolute keep guide. Preserve the same large
head, hair silhouette, face, black eye pixel and adjacent pale eye-white pixel
in every cell. The head must remain roughly one third of the complete
unmounted sprite and must connect naturally to the neck and shoulders. Change
only armor, robes, cape, ornaments, shield, weapon and the class-appropriate
mount. Keep the complete sprite inside its cell. Fill unused cells with flat
exact `#ff00ff`.

The complete connected figure is recovered even when the generator places a
robe, staff or mount a few source pixels across a nominal cell border. The
recovered logical figure is reduced to 16×16 with nearest-neighbour sampling.
The 15 visible 4bpp color slots reserve the exact original identity colors
first, then retain the generated equipment's dominant hues after snapping
them to Mega Drive channel levels. Every current user-mask pixel and protected
eye pixel is finally restored byte-for-byte from the original ROM sprite.

## Commander-specific class order

### Liana

Keep the large rounded blond head. Reading order: Healer, High Lord, Priest,
Mage, Archmage, Wizard, High Priest, Sage, Paladin, Silver Knight, Summoner.
Use white/blue/gold holy and magic equipment with vivid class accents. Only
Silver Knight is mounted.

### Lana

Use the same class order as Liana and keep the same saved head-mask geometry,
but make Lana's equipment visually distinct with aqua, cobalt, white and gold.
Only Silver Knight is mounted.

### Sherry

Keep the same jaw-length silver short bob in every class; never turn it into
long hair. Reading order: Lord, High Lord, Mage, Archmage, Wizard, Saint,
Paladin, Silver Knight, Dragon Lord, Ranger, High Master. Silver Knight uses
one coherent horse and Dragon Lord one coherent dragon; the others are on
foot.

### Hein

Keep the large blue/cyan hair mass and original face direction. Reading order:
Sorcerer, Shaman, High Lord, Mage, Archmage, Wizard, High Priest, Sage,
Paladin, Swordmaster, Summoner. All are on foot. Swordmaster visibly carries
two swords.

### Scott

Keep the large dark hair and green highlight. Reading order: Lord, High Lord,
Highlander, Paladin, Knight Master, Silver Knight, Dragon Lord, Royal Knight.
Lord, High Lord and Paladin are on foot. Highlander, Knight Master, Silver
Knight and Royal Knight use a compact horse; Dragon Lord uses a compact blue
dragon.

### Keith

Keep the large swept dark-navy head and pale side-facing face. Reading order:
Lord, High Lord, Priest, Wizard, High Priest, Paladin, Swordmaster,
Silver Knight, Dragon Lord, Dragon Master. Swordmaster has two readable
swords; Silver Knight uses a horse; Dragon Lord and Dragon Master have
progressively stronger coherent dragons.

### Aaron

Keep the broad adult build and very large silver/gray head; never replace it
with a small realistic head. Reading order: Lord, High Lord, Highlander, Mage,
Archmage, Saint, Paladin, Swordmaster, Knight Master, High Master. Highlander
and Knight Master alone are mounted. High Lord, Paladin and High Master must
read as broad, strong upper classes.

### Lester

Keep the large swept white/silver hair, forward white extension and
gray-violet shadow pixels. Reading order: Highlander, Mage, Archmage, Wizard,
Paladin, Knight Master, Silver Knight, Serpent Lord, Serpent Master. The three
knight classes use compact horses; Serpent Lord and Serpent Master use
progressively stronger coherent blue sea serpents.

### Jessica

Use Jessica Sorcerer's same saved cobalt/cyan head and face geometry in every
class. Reading order: Sorcerer, High Lord, Priest, Mage, Archmage, Wizard,
High Priest, Sage, Paladin, Swordmaster, Zavela. All are on foot.
Swordmaster carries two swords. Zavela uses an ornate ceremonial robe and
crescent/orb staff.

## Accepted outputs

- `liana/liana-logical16-sheet-ai.png`
- `lana/lana-logical16-sheet-ai.png`
- `sherry/sherry-logical16-sheet-ai.png`
- `hein/hein-logical16-sheet-ai.png`
- `scott/scott-logical16-sheet-ai.png`
- `keith/keith-logical16-sheet-ai.png`
- `aaron/aaron-logical16-sheet-ai.png`
- `lester/lester-logical16-sheet-ai.png`
- `jessica/jessica-logical16-sheet-ai.png`
