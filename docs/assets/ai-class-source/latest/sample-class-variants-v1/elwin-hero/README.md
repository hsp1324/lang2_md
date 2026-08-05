# 엘윈 히어로 5안 샘플 v1

엘윈 히어로 디자인 비교용 독립 샘플이다. 공용 에디터 manifest나 실제
게임 적용 파일은 수정하지 않는다.

## 생성 입력

- ROM 실루엣·색감: `elwin-hero-rom-original-neutral-32x.png`
- 얼굴·머리 identity: `elwin-hero-identity-73px-neutral-32x.png`

최초 생성은 위 두 레퍼런스만 사용했다. 이전 AI 히어로 이미지는 어느
호출에도 넣지 않았다. built-in `image_gen`을 서로 독립된 프롬프트로
5회 호출했다.

## 결과

- `ai/01.png`~`05.png`: built-in 생성 결과에서 녹색 크로마 배경을
  제거하고 순검정을 차콜 `#242424`로 정규화한 투명 PNG
- `logical16/01.png`~`05.png`: 각 AI 원안의 구도·장비 역할을 직접
  16×16로 재구성하고 현재 `1:22` identity 73픽셀을 ROM에서 exact-copy
- `previews/01.png`~`05.png`: logical16의 32배 nearest-neighbor 확대
- `all-elwin-hero-samples.png`: AI 원안과 logical16 전체 비교
- `validation-report.json`: 소스 투명도와 native16 정량 검증
- `raw-chroma/`: built-in 생성 직후의 보존 원본
- `prompts/01.txt`~`05.txt`: 선택된 5안의 최초 생성 프롬프트

2안은 머리 상단 여백만 바꾸는 1회 타깃 수정을 시험했지만 캐릭터가
과도하게 축소되어 선택하지 않았다. 원본과 프롬프트는 각각
`raw-chroma/02-targeted-not-selected.png`,
`prompts/02-targeted-not-selected.txt`에 비교용으로 남겼다.

재생성:

```bash
python3 tools/build_elwin_hero_sample_variants.py
```
