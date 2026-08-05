# Elwin native16 v4

엘윈 하이랜더, 비숍, 나이트마스터, 실버나이트의 큰 머리 비율 수정
원화다. Codex 내장 이미지 편집으로 클래스마다 한 장씩 생성했다.

입력 역할:

- 이미지 1: 같은 클래스의 `elwin-native16-v3` 편집 대상
- 이미지 2: `elwin-head-ratio-guides-v1/*-full-ratio-guide.png`
- 이미지 3: `elwin-head-ratio-guides-v1/*-masked-head-guide.png`

공통 프롬프트 핵심:

> Preserve the exact Elwin head identity from Image 3 and match Image 2's
> full-sprite proportions. Enlarge the head/hair/face to occupy the same top
> 9 logical rows of a native 16x16 Mega Drive sprite, then compress and
> reposition the torso, class equipment, and mount beneath it. Keep one
> complete centered sprite on a perfectly flat #ff00ff background. Use hard
> nearest-neighbor square pixel clusters, no antialiasing, no extra objects,
> text, or watermark.

클래스별로 장비 조건만 달리했다.

- `0C-highlander.png`: 청회색 장갑마, 은색 갑옷, 진홍 띠, 세운 창
- `12-bishop.png`: 보행, 백회색 제의, 붉은 스톨, 녹색 보석 지팡이
- `1B-knight-master.png`: 갈색 장갑마, 은적색 중갑, 금장, 검
- `1D-silver-knight.png`: 담청색 장갑마, 은청색 갑옷, 수평 장창

AI 원화는 머리 크기와 전체 장비 비율을 정하는 디자인 입력이다. 최종
16×16에서는 `editor/ai_identity_masks.json`의 사용자 마스크 좌표를
원작 ROM 픽셀로 다시 기록하므로 얼굴·머리·눈은 정확히 일치한다.
