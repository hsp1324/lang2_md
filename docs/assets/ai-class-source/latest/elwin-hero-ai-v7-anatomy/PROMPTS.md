# 엘윈 히어로 v7 생성 프롬프트

Codex 내장 `image_gen` 모드를 사용했다.

## 1. ROM 원본과 얼굴 마스크만 사용한 신규 생성

```text
Use case: stylized-concept
Asset type: native 16×16 Mega Drive tactical-RPG map character sprite concept, enlarged with nearest-neighbor square pixels
Primary request: Redesign Elwin's final Hero class from the original ROM reference so the anatomy is immediately readable at 16×16. Start from the ROM pose and identity, not from any previous generated Hero design.
Input images: Image 1 is Elwin's original ROM Hero sprite and is the authority for overall scale, red-haired identity, original diagonal-sword pose, heroic build, and red/blue/steel palette. Image 2 is the current 73-pixel identity-only reference and is the authority for head, hair, eye, and head scale. Do not copy the neutral background.
Subject: exactly one unmounted adult male Hero Elwin. He holds exactly one large continuous sword diagonally along image-left, from the upper-left blade tip down to a clearly visible hilt and hand near the waist. His red-haired head, dark neck gap, armored torso, sword-side shoulder, upper arm, forearm, gripping hand, opposite shoulder/arm/hand, two legs, and red cape must each read as separate connected body/equipment regions.
Anatomy layout: keep the head at the ROM scale and location. Put a one-logical-pixel dark separator beneath the face before the neck/armor. The sword-side arm must form a continuous chain: shoulder -> upper arm -> elbow/forearm -> skin-colored hand -> gold/brown hilt -> silver blade. The hand must not merge into the torso or blade. The opposite arm must have its own shoulder and forearm silhouette and must not become part of the cape. The blue torso/tabard must be a closed central mass with dark outline and must not merge into either hand.
Style/medium: authentic early-1990s 16-bit Mega Drive pixel art; design on an invisible exact 16×16 logical grid and display it enlarged. Hard square pixels only, broad clusters, at most 15 visible colors, no antialiasing, no smooth gradients, no details smaller than one logical pixel.
Composition/framing: original ROM-like three-quarter battle stance, full body visible, broad heroic proportions, one connected character. Use the full logical square but keep sword, hair, cape, hands, arms, legs, and feet inside the canvas without cropping.
Scene/backdrop: perfectly uniform flat light gray, no border, no grid lines, no gradient, no shadow.
Color/material separation: silver/white sword and armor; gold/brown hilt and joints; skin-colored hands; dark navy/black anatomy outlines; closed royal-blue torso panel; deep-red cape behind the body only; original red/brown hair.
Constraints: every limb connects naturally to the torso; exactly one sword; both hands and both arms visible or structurally legible; head/body/weapon are not fused; no full empty logical row or column; no text or watermark.
Avoid: sword crossing through the face, detached sword segment, white mouth-like band under the face, hand cut off by scaling, floating hand, arms fused into chest, cape mistaken for an arm, tiny skinny body, oversized head, shield, second sword, horse, smooth high-resolution painting, pure-black or magenta background, purple/magenta edge halo.
```

## 2. 선택 후보의 망토·세부 밀도 단순화

```text
Use case: identity-preserve
Asset type: native logical 16×16 Mega Drive tactical-RPG map sprite concept, enlarged with nearest-neighbor square pixels
Input images: Image 1 is the newly generated anatomy-readable Elwin Hero candidate to refine; Image 2 is the authoritative current Elwin head/hair identity and scale.
Primary request: Preserve Image 1's excellent readable anatomy and original-ROM diagonal-sword pose, but simplify it into a much coarser sprite concept that can be repixelled to native 16×16 without losing the hands, arms, body, sword, or head.
Change only these points:
1. Reduce the red cape to a compact shape behind the image-right shoulder, torso, and right leg; remove the huge wing-like cape spread on image-left.
2. Keep exactly one continuous upper-left diagonal sword, one gold/brown hilt, and one skin-colored gripping hand. Keep the blade visually separated from the head.
3. Keep both shoulders, both arms, both hands, the closed blue torso, two armored legs, and both feet clearly separate with a one-logical-pixel dark outline between adjacent parts.
4. Simplify at least half of the tiny armor highlights and checker-like decorations into broad clusters.
5. Preserve the original red-haired head scale from Image 2 and keep one dark logical row beneath the face; never place a white horizontal band under the face.
Logical-pixel requirement: rebuild on an invisible exact 16-columns by 16-rows grid. Each visible square must be one complete logical cell with no smaller subdivisions. Use at most 15 visible colors and only hard square edges.
Composition: one broad adult Hero, full body inside the square, no cropping. Sword tip uses upper-left; compact cape uses right edge; feet use bottom edge. One connected figure.
Scene/backdrop: perfectly uniform flat light gray; no grid lines, border, gradient, or shadow.
Avoid: giant cape, fused arm and cape, detached hand, hand merged into the hilt, sword crossing the face, mouth-like white neck band, tiny skinny torso, giant head, second sword, shield, horse, antialiasing, smooth painting, magenta/purple halo, text, watermark.
```
