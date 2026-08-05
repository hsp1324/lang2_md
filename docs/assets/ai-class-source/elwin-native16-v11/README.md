# Elwin native16 v11

히어로의 외소한 몸을 넓고 무거운 중장 실루엣으로 다시 생성한 현재 적용
묶음이다.

- `22 Hero`: 원작 전체 스프라이트와 사용자 마스크만 입력했다. 머리와
  눈·머리카락 위치, 보행 방향과 무기 위치를 유지하면서 어깨, 은백색
  흉갑, 양팔, 허리와 두 다리를 넓혔다.
- 나머지 9개 클래스는 v10 채택본을 유지했다.
- 첫 히어로 재생성은 마스크 일치율 87.7%로 폐기했다.
- 두 번째 재생성은 66/73픽셀(90.4%)로 통과했다.

## 크기와 정체성 검증

- 머리에 연결된 히어로 몸·장비: v10 77 → v11 90논리픽셀
- 최종 마스크 고정 후 히어로 73픽셀: 원작과 100% 일치
- 하이랜더·나이트마스터는 v10과 같은 원작 말 외곽 보존 변환 유지

## 재생성

```sh
python3 tools/normalize_elwin_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/elwin-native16-v11/raw \
  --output-dir docs/assets/ai-class-source/elwin-native16-v11 \
  --preserve-original-mounts
```

생성 프롬프트는 `PROMPTS.md`에 기록했다.
