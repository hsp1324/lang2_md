# Elwin native16 v14

v13 전체 디자인을 유지하고 아크메이지만 작게 보정한 현재 적용 묶음이다.

- 아크메이지의 머리·얼굴·몸 크기·발·지팡이 위치·녹색 보석은 유지했다.
- 흰색 외부 로브와 남색 중심부에 왕청색/보라색 어깨 맨틀, 절제된 금장을
  추가했다.
- 아크메이지 채택 AI 원화 머리 일치: 66/69픽셀(95.7%)
- 아크메이지 머리에 연결된 몸·장비: 85논리픽셀
- 최종 마스크 69픽셀: 원작과 100% 일치
- 로드, 하이로드, 하이랜더, 비숍, 메이지, 소드마스터, 나이트마스터,
  실버나이트, 히어로는 v13 채택본을 그대로 유지했다.
- 10개 클래스 모두 머리 원시 일치율 90% 이상과 몸 연결 검증을 통과했다.

## 재생성

```sh
python3 tools/normalize_elwin_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/elwin-native16-v14/raw \
  --output-dir docs/assets/ai-class-source/elwin-native16-v14 \
  --preserve-original-mounts \
  --broaden-hero-sword \
  --dual-sword-layout
```

생성 프롬프트와 입력 역할은 `PROMPTS.md`에 기록했다.
