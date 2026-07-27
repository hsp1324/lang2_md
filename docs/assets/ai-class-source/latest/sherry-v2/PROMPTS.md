# 쉐리 v2 이미지 생성 프롬프트

## 실행 방식

Codex 내장 `imagegen`의 로컬 참조 이미지 모드를 사용했다. 클래스마다
`reference-cards/NN.png` 한 장을 입력하고 서로 다른 호출로 생성했다.
카드의 왼쪽은 ROM 원작 전체, 오른쪽은 현재 사용자 얼굴 마스크다.

## 공통 프롬프트

```text
Use case: identity-preserve.
Asset type: Sega Mega Drive tactical-RPG map character sprite source.
Input image: one reference card; LEFT is Sherry's original full 16x16
sprite and exact scale/pose reference, RIGHT is the exact protected face,
eyes, eye-white, silver hair and jaw-length short bob identity region.

Create ONE newly designed Sherry class sprite, not a comparison card and
not two figures. Draw directly as an exact 16 columns by 16 rows logical
pixel sprite. Every visible logical pixel must be one large uniform square
block: no smaller subpixels, anti-aliasing, gradients, painterly texture or
tiny details.

Preserve the protected head at the same coordinates and nearly
pixel-for-pixel: large head occupying about the top 9 of 16 rows, blue eye
plus white eye pixel, silver jaw-length short bob. Absolutely no long hair,
ponytail, helmet, hood, hat, crown, second face or duplicated head.

Connect the protected head naturally to neck, torso and equipment. Use the
whole 16x16 square efficiently: hair reaches the top, feet or mount reach
the bottom, weapon/cape/mount uses outer columns. Nothing is cropped. Keep
the figure large and readable, not skinny.

Scene/backdrop: perfectly flat solid #ff00ff chroma-key background, one
uniform color with no texture, border, shadow, glow, floor or gradient.
Do not use #ff00ff or pure #000000 as equipment fill; dark outline may use
very dark charcoal. Limited vivid Mega Drive palette, maximum roughly
15 foreground colors.

Constraints: exactly one sprite, no text, labels, frame, watermark or
extra character.
```

## 클래스별 장비 지시

- `04 LORD`: 보행. 넓은 은색 지휘관 갑옷, 풍성한 금색 견갑, 짧은 검,
  진홍 망토.
- `0B HIGH LORD`: 보행. 로드보다 강한 중장 은색 판금, 대형 금색 견갑,
  검, 청색 방패, 진홍 지휘관 망토.
- `13 MAGE`: 보행. 왕청색 로브, 보라 맨틀, 금장, 청록 수정 지팡이.
- `14 ARCHMAGE`: 보행. 메이지보다 강한 백청보라 로브, 큰 금장 견갑,
  녹색 수정 지팡이.
- `15 WIZARD`: 보행. 남색·인디고 로브, 보라 패널, 강한 금장, 적색
  보석 지팡이. 메이지보다 약하거나 가늘게 보이지 않게 한다.
- `17 SAINT`: 보행. 백금색 성직 로브, 청색 스톨, 금색 견갑, 성직
  지팡이.
- `19 PALADIN`: 보행 고정. 백은색 판금, 대형 금색 견갑, 검, 청색
  방패. 말이나 탈것을 금지한다.
- `1D SILVER KNIGHT`: 말 한 마리 탑승. 담청은색 기수 갑옷, 남색 마갑,
  진홍 포인트, 긴 은색 창. 말의 몸·다리·꼬리·발굽을 프레임 안에 둔다.
- `1E DRAGON LORD`: 드래곤 한 마리 탑승. 녹청색 드래곤, 진홍 날개,
  은금색 기수 갑옷. 드래곤 머리·몸·날개·꼬리·발톱을 프레임 안에 둔다.
- `21 RANGER`: 보행. 녹갈색 경량 갑옷, 붉은 스카프, 큰 활과 손.
- `23 HIGH MASTER`: 보행. 최상위 백청색 로브/경갑, 풍성한 금색 견갑,
  청록 보석, 층진 짧은 망토, 장식 수정 지팡이.

생성 모델이 참조 카드의 얼굴 좌표를 완전히 복사하지 못한 부분은
`selected-sources` 단계에서 현재 사용자 마스크의 논리셀을 원본 그대로
합성했다. 최종 16×16에서는 동일 셀을 다시 검증한다.
