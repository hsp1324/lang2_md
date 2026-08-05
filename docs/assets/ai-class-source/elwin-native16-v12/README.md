# Elwin native16 v12

히어로의 칼·손 가독성을 수정하고 소드마스터를 쌍검으로 다시 생성한
현재 적용 묶음이다.

## Hero

- 원작 전체 스프라이트와 사용자 마스크만 입력했다.
- 채택 AI 원화는 마스크 73/73픽셀이 처음부터 일치한다.
- 왼쪽 칼날, 금색 가드, 손잡이, 왼손과 팔이 하나로 연결된다.
- 양손과 장비는 `x=0`, `x=15`에 닿지 않는다.
- AI 원화의 색 블록 10픽셀을 복제해 몸·장비를 74에서
  84논리픽셀로 보강했다.

## Swordmaster

- 원작 전체 스프라이트와 사용자 마스크만 입력했다.
- 채택 AI 원화는 마스크 69/69픽셀이 처음부터 일치한다.
- 좌우 손에 각각 손잡이·가드·은색 칼날이 연결된다.
- 왼쪽 칼끝의 가장자리 픽셀 하나만 제거해 한 픽셀 여백을 확보했다.
- 팔레트 변환에서 칼날이 검게 뭉개지지 않도록 좌우 칼날 중심 한
  픽셀씩을 은백색으로 고정했다.
- 최종 좌우 칼 영역은 각각 8논리픽셀이다.

나머지 8개 클래스는 v11 채택본을 유지했다.

## 재생성

```sh
python3 tools/normalize_elwin_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/elwin-native16-v12/raw \
  --output-dir docs/assets/ai-class-source/elwin-native16-v12 \
  --preserve-original-mounts \
  --broaden-hero-sword \
  --dual-sword-layout
```

생성 프롬프트와 폐기 기준은 `PROMPTS.md`에 기록했다.
