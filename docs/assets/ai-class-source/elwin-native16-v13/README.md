# Elwin native16 v13

소드마스터 쌍검을 유지하면서 양쪽 어깨에 하이로드 계열의 풍성한 금색
견갑을 추가한 현재 적용 묶음이다.

- 원작 전체 스프라이트와 사용자 마스크를 정체성 기준으로 사용했다.
- 사용자가 직접 지정한 하이로드는 견갑 크기와 장비 분위기 기준으로만
  추가 사용했다.
- 양쪽 견갑은 암금색 외곽, 금색 본체, 연노랑 강조색의 2~3논리픽셀
  덩어리다.
- 채택 AI 원화 머리 일치: 64/69픽셀(92.8%)
- 머리에 연결된 몸·장비: 72논리픽셀
- 좌우 칼 영역: 각각 9논리픽셀
- 마스크 고정 후 69픽셀: 원작과 100% 일치
- 나머지 9개 클래스는 v12 채택본을 유지했다.

첫 금색 견갑 시안은 62/69로 기준에 한 픽셀 부족해 폐기했고, 머리만
보정한 후속 편집은 격자가 밀려 16/69로 폐기했다.

## 재생성

```sh
python3 tools/normalize_elwin_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/elwin-native16-v13/raw \
  --output-dir docs/assets/ai-class-source/elwin-native16-v13 \
  --preserve-original-mounts \
  --broaden-hero-sword \
  --dual-sword-layout
```

생성 프롬프트와 입력 역할은 `PROMPTS.md`에 기록했다.
