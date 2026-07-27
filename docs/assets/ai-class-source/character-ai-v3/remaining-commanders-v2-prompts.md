# Remaining commander v2 generation prompts

## Mode and references

- Mode: built-in image generation, one fresh square class sheet per commander.
- Input images: only that commander's
  `original-reference-board.png` and `masked-identity-board.png`.
- Previous AI sheets, identity-locked class boards, and Elwin style sheets were
  not used as image inputs.
- Output: hard-edged Mega Drive/Genesis pixel art on exact `#ff00ff`, followed
  by nearest-neighbour 16×16 reduction, ROM-palette mapping, and exact
  restoration of every saved mask pixel.

## Common prompt

Create one compact pixel-art class sheet for a Sega Mega Drive / Genesis
16×16 tactical-RPG commander. Treat the original-reference board as the exact
full-sprite scale and proportion reference and the masked-identity board as an
identity lock. Keep the same large head, hair silhouette, face direction,
black eye pixel and adjacent pale eye-white pixel in every occupied cell.
Never shrink the head or detach it from the body. Change only class armor,
robes, weapons, shields, ornaments, cape, and mounts. Use a limited bright
Mega Drive palette, large square pixels, hard edges, no antialiasing, no text,
no labels, no scenery, and no cropping. Center one complete figure per cell on
solid exact `#ff00ff`. Leave every unused cell completely empty.

## Liana

Eleven cells in reading order:

1. Healer: white/blue holy robe and small staff.
2. High Lord: silver/blue/gold armor, sword, shield, broad pauldrons.
3. Priest: white/red/gold robe and cross staff.
4. Mage: vivid blue robe and red-orb staff.
5. Archmage: upgraded white/blue/gold mantle and crystal staff.
6. Wizard: violet robe and elemental staff.
7. High Priest: ornate white/gold holy robe.
8. Sage: blue/white mantle and jewel staff.
9. Paladin: heavy silver/gold armor, sword, shield.
10. Silver Knight: one compact coherent horse rider.
11. Summoner: purple/navy robe and summoning staff.

Keep Liana's original large blond head and short rounded hair mass.

## Lana

Use the same eleven class positions as Liana, but give the new equipment a
distinct aqua/cobalt/white/gold color family. Keep Lana's own body/equipment
designs distinct while restoring the exact Liana-derived saved masks in the
final 16×16 result. Only Silver Knight is mounted.

## Scott

Eight cells in reading order:

1. Lord: on foot, silver armor, sword and compact shield.
2. High Lord: on foot, upgraded gold pauldrons and blue shield.
3. Highlander: compact horse rider and lance.
4. Paladin: on foot, bright silver/gold armor, sword and shield.
5. Knight Master: compact armored horse rider.
6. Silver Knight: stronger silver/blue horse rider.
7. Dragon Lord: compact coherent blue dragon rider.
8. Royal Knight: ornate silver/gold horse rider.

Keep Scott's large dark hair silhouette, green highlight, face, and eye pixels.

## Keith

Ten cells in reading order:

1. Lord: on foot, silver/red armor and sword.
2. High Lord: on foot, gold pauldrons, blue shield and sword.
3. Priest: white robe and green-jewel holy staff.
4. Wizard: navy robe and blue-jewel staff.
5. High Priest: ornate white/gold robe.
6. Paladin: heavy silver armor, sword and shield.
7. Swordmaster: on foot with two readable swords.
8. Silver Knight: compact horse rider.
9. Dragon Lord: blue/red dragon rider.
10. Dragon Master: upgraded gold/blue dragon rider.

Keep Keith's original large dark navy swept hair and pale side-facing face.

## Aaron

Ten cells in reading order:

1. Lord: on foot, silver/blue armor, sword and shield.
2. High Lord: on foot, upgraded silver/gold armor and larger pauldrons.
3. Highlander: compact dark-horse rider and lance.
4. Mage: on foot, warm brown/red robe and short staff.
5. Archmage: on foot, burgundy/gold robe and crystal staff.
6. Saint: on foot, white/gold holy armor and staff or mace.
7. Paladin: on foot, bright heavy armor, sword and shield.
8. Swordmaster: on foot, broad fighting pose.
9. Knight Master: compact armored horse rider and lance.
10. High Master: on foot, broad strongest warrior and large sword.

Aaron is a broad adult male. His silver/gray head must remain about one third
of the complete sprite and must never be reduced to a small realistic head.

## Lester

Nine cells in reading order:

1. Highlander: compact silver/blue horse rider and lance.
2. Mage: brown/red robe and staff.
3. Archmage: wine-red/gold robe and crystal staff.
4. Wizard: deep blue/violet robe and elemental staff.
5. Paladin: bright silver/gold armor, sword and shield.
6. Knight Master: stronger silver/blue/gold horse rider.
7. Silver Knight: luminous silver horse rider.
8. Serpent Lord: compact blue sea-serpent rider.
9. Serpent Master: upgraded cobalt/cyan sea-serpent rider.

Keep Lester's large swept white/silver hair, forward white extension,
gray/violet shadow pixels, face, and eye pixels. The generated sheet compressed
these cells into three visual rows, so the builder uses the actual clean row
gaps at y=0, 380, 780, and 1254.

## Jessica

Eleven cells in reading order:

1. Sorcerer: red/black/blue robe and red-orb staff.
2. High Lord: white/blue/gold armor, sword and shield.
3. Priest: white/red/gold robe and cross staff.
4. Mage: vivid red/blue robe and ruby staff.
5. Archmage: upgraded white/blue/gold mantle and crystal staff.
6. Wizard: white/red pointed hat behind the locked hair and blue-orb staff.
7. High Priest: ornate white/gold holy robe.
8. Sage: white/light-gray cape and blue/gold staff.
9. Paladin: bright silver/blue/gold armor, sword and shield.
10. Swordmaster: two swords and a compact fighting pose.
11. Zavela: ornate ceremonial robe, crown-like ornament behind the hair, and
    crescent/orb staff.

All classes are on foot. Use Jessica Sorcerer's saved 73-pixel mask identically
for every upper class so the cobalt/cyan hair and face stay exactly consistent.

## Elwin Swordmaster mask refill

Mode: deterministic identity-mask composition on the previously accepted
dual-sword AI source. The newly saved mask contains 83 pixels, including the
outer gold shoulder coordinates. The v15 normalizer restores all 83 pixels
from the original ROM, retains both swords and hands, validates both blade
regions, and then supplies `elwin-native16-v15` to the editor build.

## Elwin Archmage v16 targeted edit

- Mode: built-in image generation, precise-object-edit.
- Edit target: `elwin-native16-v15/raw/14-archmage.png`.
- Lower-tier comparison only: `elwin-native16-v15/raw/13-mage.png`.
- Identity/proportion inputs:
  `elwin-head-ratio-guides-v2/14-original-full-ratio.png` and
  `14-masked-identity.png`.

Final prompt:

> Redesign only Elwin's Archmage equipment so it visibly looks stronger and
> more advanced than Mage. Preserve the same large head, red/brown hair,
> gray headband, black eye pixel and adjacent white eye pixel at the original
> scale and position. Keep him on foot. Give Archmage a wider final-tier
> battle-mage silhouette with large symmetric royal-blue and gold shoulder
> mantle, layered deep-navy and white ceremonial robe, broad gold edging,
> blue side cape panels, high collar, and a taller thick staff held by the
> right hand with a large cyan/royal-blue crystal in a gold frame. Make it
> broader, brighter, heavier and more ornate than Mage without becoming a
> knight. Use coarse native 16×16 Mega Drive pixel art, large simple color
> clusters and exact `#ff00ff` background. No mount, shield, sword, hat,
> detached hand/staff, crop, small head, narrow shoulder or muted gray-only
> robe.

The generated equipment was retained, then the saved 69 identity pixels were
composed into the exact logical grid before normalization. The accepted v16
source has 69/69 pre-lock and 69/69 final identity matches, with 103 connected
body/equipment pixels.
