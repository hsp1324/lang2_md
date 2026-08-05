# Elwin native16 v5

엘윈의 상위 중복 클래스 10개를 동일한 규칙으로 새로 생성한 최종 AI
원화다. Codex 내장 이미지 생성으로 클래스마다 별도 호출했으며,
하이로드와 히어로는 첫 결과의 머리가 작아 머리 크기만 한 번 더
보정했다.

## 입력 역할

- 이미지 1: `elwin-head-ratio-guides-v2/*-original-full-ratio.png`
  — 원작 전체 16×16의 머리·몸·장비 비율 기준
- 이미지 2: `elwin-head-ratio-guides-v2/*-masked-identity.png`
  — 사용자가 저장한 원본 얼굴·머리·눈 정체성 픽셀 기준
- 이미지 3: 이전 클래스 원화 — 장비 종류와 색 참고만 사용

## 공통 프롬프트 핵심

> Create a brand-new strict native 16x16 Mega Drive commander sprite.
> Match Image 1's original Elwin head-to-body proportion and Image 2's identity.
> The visible hair-and-face head must be exactly 5 to 6 logical pixels tall,
> about one third of the full sprite. The complete character, equipment, and
> mount must fill 15 to 16 logical rows; use the remaining two-thirds for
> readable armor, robes, weapons, legs, or horse body. Use one implicit 16x16
> grid, hard nearest-neighbor square clusters, a limited ROM-like palette,
> black outlines, and a perfectly flat #ff00ff background. No antialiasing,
> tiny body, huge head, cropped parts, extra objects, text, or watermark.

## 클래스

- `04-lord.png`: 보행, 은색 지휘관 갑옷, 청금 방패, 검, 짧은 적색 망토
- `0B-high-lord.png`: 보행, 중장 은금 갑옷, 대형 청금 방패, 검, 긴 망토
- `0C-highlander.png`: 기병, 청회색 장갑마, 은색 경기병 갑옷, 세운 창
- `12-bishop.png`: 보행, 백회색 제의, 붉은 스톨, 녹색 보석 지팡이
- `13-mage.png`: 보행, 남색 전투 로브, 붉은 안감, 녹색 보석 지팡이
- `14-archmage.png`: 보행, 백남색 다층 로브, 금장, 고급 지팡이
- `1A-swordmaster.png`: 보행, 경량 은남색 갑옷, 양손검, 붉은 허리띠
- `1B-knight-master.png`: 기병, 갈색 장갑마, 은적색 중갑, 기병검
- `1D-silver-knight.png`: 기병, 담청 장갑마, 은청 갑옷, 수평 장창
- `22-hero.png`: 보행, 백은색 영웅 갑옷, 금장, 검, 붉은 망토

`elwin-v5-contact-sheet.png`는 열 개 원화를 한눈에 비교하는 시트다.
최종 16×16에서는 `editor/ai_identity_masks.json`의 사용자 좌표를 원작
ROM 픽셀로 복원하므로 얼굴·머리·눈은 정확히 일치한다.
