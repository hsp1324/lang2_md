# 엘윈 히어로 AI v7 — 신체·무기 분리

현재 v6에서 얼굴 아래 흰 띠가 입처럼 보이고 반대편 팔이 망토에 섞이던
문제를 해결하기 위해 다시 만들었다. 최초 생성 입력은 엘윈 히어로 ROM
원본과 현재 73픽셀 얼굴·머리 마스크뿐이며, 이전 히어로 AI 원화는 넣지
않았다.

선정한 신규 AI 원화의 원본형 대각 대검, 양쪽 팔·손, 닫힌 왕청 몸통,
양쪽 다리, 작은 오른쪽 진홍 망토를 네이티브 16×16로 다시 픽셀화했다.

- 검: `검날 → 금색 가드 → 피부색 손 → 은색 팔` 네 단계 연결
- 반대팔: `견갑 → 은색 팔 → 피부색 손` 뒤에 암색 경계를 두고 망토 분리
- 머리/몸: 얼굴 아래 `x6..9/y9`를 어두운 목 경계로 닫음
- 몸통: `x7..9/y10..14` 왕청색 면을 닫힌 덩어리로 유지
- 다리/발: 두 다리와 두 발 사이에는 `x8/y15` 한 칸만 비움

얼굴·머리·눈 73/73픽셀, 단일 연결 실루엣, 10색, 빈 행·열 및 몸통
구멍·순수 검정·자홍 오염 없음과 위 다섯 가지 의미 좌표 검증을 통과한다.

- `selected-sources/22-hero-ai.png`: 선택한 신규 AI 원화
- `22-hero.png`, `logical16/22-hero.png`: 최종 네이티브 16×16
- `elwin-hero-v7-comparison.png`: ROM / v6 / 신규 AI / v7 비교
- `PROMPTS.md`: 실제 생성 프롬프트
- `validation-report.json`: 자동 검증 결과

재생성:

```bash
python3 tools/build_elwin_hero_ai_v7.py --prepare-references
python3 tools/build_elwin_hero_ai_v7.py
python3 tools/build_ai_class_sprite_assets.py
```
