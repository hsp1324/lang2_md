# 생성 프롬프트

사용한 방식: Codex 내장 이미지 생성, identity-preserve.

입력 레퍼런스:

1. 현재 헤인 소서러 `5/09.png`를 최근접 1024×1024로 확대한 얼굴·머리·
   자세 기준
2. 승인된 헤인 메이지 `5/13.png`를 최근접 1024×1024로 확대한 장비
   픽셀 문법 기준

```text
Use case: identity-preserve
Asset type: project-bound 16×16 Mega Drive character sprite concept, delivered as a 1024×1024 nearest-neighbor enlargement of an exact 16×16 logical pixel grid.
Input images: Image 1 is the Hein Sorcerer edit target and exact identity/pose reference; Image 2 is Hein's approved Mage equipment-language reference only.
Primary request: Redesign Hein specifically as a clearly readable SORCERER, not a Mage. Preserve Hein's face, eye, skin pixels, blue/cyan hair silhouette, head size, hairline, and facing direction from Image 1 as faithfully as possible. Redesign the body and equipment naturally around that same head.
Design: a compact lower-tier sorcerer with a dark indigo and royal-blue robe, cyan folded-cloth highlights, a short shoulder mantle, narrow waist, and one simple wooden staff on image-right topped by a small pale-cyan crystal. The robe and staff must be simpler and less ornate than the Mage in Image 2, but visibly more magical than a generic Warlock. Keep the full character broad and readable, occupying nearly all 16 rows and about 14–15 columns without cropping.
Pixel construction: exactly 16 logical columns by 16 logical rows. Every colored shape must be made only from large square cells aligned to that grid, each logical cell enlarged to 64×64 pixels. Hard nearest-neighbor edges only. No antialiasing, no gradients, no sub-pixel details, no cells smaller than one logical grid square, no smooth curves. Use at most 15 visible subject colors.
Scene/backdrop: perfectly flat solid #ff00ff chroma-key background, one uniform color, no shadow, gradient, texture, floor, or lighting variation. Do not use #ff00ff in the character.
Constraints: one character only; front three-quarter game sprite; exact recognizable Hein head and hair; connected body, robe, sleeves, hands, and staff; staff must not touch the canvas edge; no text, UI, border, watermark, extra character, mount, shield, oversized hat, face replacement, realistic rendering, blur, glow haze, tiny decorative noise, or cropped pixels.
```
