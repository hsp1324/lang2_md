# 생성형 AI 프롬프트

모드는 Codex 내장 `image_gen`을 사용했다. 로컬 입력은 먼저 화면으로
확인했고, 이전 AI 작업물이나 공통 클래스 도안은 최초 생성 입력에서
제외했다.

## 자베라 최초 생성

```text
Use case: stylized-concept
Asset type: Mega Drive tactical-RPG map character sprite concept that will be repixelled to native 16×16
Primary request: Create a completely new design for Jessica's advanced magical class "Zarvera". Start fresh; do not reuse or infer any previous AI design, common class template, armor layout, weapon layout, or prior color guide.
Input images: Image 1 is the original ROM sprite and may be used ONLY to understand Jessica's identity, head scale, full-body scale, and logical 16×16 placement; ignore and redesign all clothing, equipment, pose details, and class silhouette. Image 2 is the identity-only reference and is the authority for Jessica's face, large cyan/blue hair, eye placement, and head size.
Subject: one unmounted Jessica, front-facing three-quarter tactical map-sprite pose, unmistakably the same large-headed Jessica; invent an elegant and powerful high-tier Zarvera outfit and a fresh readable magical silhouette.
Style/medium: authentic early-1990s 16-bit Mega Drive pixel art; strict logical 16×16 design enlarged with nearest-neighbor hard square pixels. Exactly 16 logical pixel cells across and 16 down. Use large simple clusters, no details smaller than one logical cell, no antialiasing.
Composition/framing: exactly one complete sprite, centered but using the entire square; head occupies roughly the same 16×16 area and placement as Image 2; head and body must form one coherent connected figure; weapon/equipment, hair, sleeves, robe/cape, and feet all remain fully inside the square with no cropping.
Scene/backdrop: perfectly flat uniform light-gray background, clearly separate from the sprite, no border, no frame, no grid, no shadow.
Constraints: preserve Jessica's recognizable cyan/blue hair mass, face scale, and eyes; generate all equipment from scratch; limited 15-visible-color game palette; readable dark internal separators at face/neck/body boundaries; one cohesive silhouette; no empty full row or full column in the logical 16×16 design; no text, labels, watermark, mockup, or multiple variants.
Avoid: tiny head, chibi head detached from body, smooth high-resolution painting, 32×32 or 64×64 detail density, gradients, antialiasing, pure-black background, purple/magenta outline or border, background color incorporated into the character, cropped weapon, cropped feet, floating accessories.
```

## 자베라 선택 후보 보정

```text
Use case: identity-preserve
Asset type: native logical 16×16 Mega Drive tactical-RPG sprite concept, shown enlarged with nearest-neighbor pixels
Input images: Image 1 is the newly generated fresh Zarvera candidate to refine; Image 2 is the authoritative original Jessica face/hair identity and scale.
Primary request: Keep the fresh Zarvera costume idea from Image 1, but correct only the logical-pixel density and Jessica's proportions so it can genuinely collapse into a readable native 16×16 sprite.
Required edit: rebuild the picture on an invisible EXACT 16-columns by 16-rows logical grid. Each output block must be one full logical cell, with no subdivisions. Reduce and simplify Jessica's hair/head so it occupies only the top 6 logical rows and closely matches the placement and scale of Image 2. Give the connected torso, robe, arms, staff, and feet the remaining 10 rows. Remove at least half of the small decorative details and convert them into broad, readable clusters.
Composition: exactly one full-body unmounted sprite; use all edges of the 16×16 square while keeping every element fully visible; head, neck, and torso are one connected silhouette.
Scene/backdrop: perfectly uniform flat light gray, no grid lines, no frame, no border, no gradient, no shadow.
Constraints: preserve cyan/blue Jessica identity; preserve the fresh dark elegant Zarvera concept, one staff and one casting hand; at most 15 visible colors; hard square pixels; dark face/neck/body separators; no empty full row or column.
Avoid: giant head, tiny body, detached hair, more than 16 logical blocks on either axis, subpixel highlights, checker details, antialiasing, smooth painting, floating jewelry, cropped equipment, magenta/purple halo, text, watermark.
```

## 서머너 생성

```text
Use case: stylized-concept
Asset type: native 16×16 Mega Drive tactical-RPG map sprite design, displayed enlarged with nearest-neighbor pixels
Primary request: Create a completely fresh design for Jessica's advanced class "Summoner". Do not reuse any earlier AI image, common class template, prior equipment layout, or prior palette guide.
Input images: Image 1 is the original ROM sprite; use it only for Jessica's identity, head scale, and 16×16 body proportions, and ignore its clothes/equipment. Image 2 contains only the current locked Jessica face and cyan/blue hair and is the identity authority.
Subject: one unmounted Jessica, clearly recognizable as the same large-blue-haired character, with a newly invented, elegant high-tier summoner costume and one strong class-defining magical silhouette. The summoned-magic idea must be conveyed within her worn/held equipment, not by a separate creature or floating detached object.
Style/medium: strict early-1990s 16-bit Mega Drive pixel art. The design consists of EXACTLY 16 logical square cells across and 16 logical square cells down, enlarged evenly. Every visible block must equal one logical 16×16 pixel; no half-cells, no tiny sub-pixels, no antialiasing, no high-resolution texture. Use broad simple pixel clusters and at most 15 visible colors.
Composition/framing: full body in one connected figure. Preserve the reference head at its original approximate size: head/hair occupies about the top 6 of the 16 logical rows, not half the canvas. Body/equipment occupies rows 6–15. Use all four sides of the logical square without cropping any hair, hands, equipment, robe, or feet.
Scene/backdrop: perfectly uniform flat light gray, no border, no frame, no grid lines, no gradient, no shadow.
Constraints: invent all clothing and equipment from scratch; preserve cyan/blue hair mass, face size, and eye relationship from Image 2; coherent neck connection; readable dark separators at face/neck/robe boundaries; no completely empty logical row or column; exactly one sprite; no text or watermark.
Avoid: giant head, tiny body, detached head, separate summoned creature, floating UI ornament, excessive jewelry, smooth painting, 32×32/64×64 detail density, pure-black or purple background, magenta/purple edge halo, background sampled as clothing, cropping.
```
