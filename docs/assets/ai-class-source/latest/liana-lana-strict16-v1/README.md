# 리아나·라나 엄격 논리16 AI 원화

생성 AI가 16×16 요청을 사실상 약 32×32 밀도로 그리던 문제를 줄이기
위해 입력과 출력 모두 1254px로 맞추고, 캔버스를 정확히 16개 행·열로
나눈 대형 셀만 사용하도록 반복 생성한 작업물이다.

## 처리 순서

1. 리아나 세이지에서 다시 저장한 얼굴 마스크 82픽셀을 공통 기준으로
   사용한다.
2. 클래스별 AI 후보를 생성한다.
3. 머리 이동, 작은 하위 셀, 과도한 세부 묘사가 있는 후보는 폐기한다.
4. 채택 후보에는 82개 얼굴 셀을 원화 단계에서 다시 정확히 고정한다.
5. 피사체를 자르거나 늘리지 않고 전체 캔버스의 16개 행·열을 읽는다.
6. 리아나는 적색, 라나는 같은 실루엣의 청색 장비로 만든다.
7. 원본 머리를 유지하면서 가시색을 메가드라이브 4bpp 한도인 15색
   이하로 맞춘다.

## 폴더

- `candidates`: 모든 생성 후보와 머리 고정 실패 후보
- `selected-sources`: 채택 후보에 82셀 얼굴을 먼저 고정한 AI 원화
- `native16-red`: 에디터가 읽는 리아나 빨강 16×16
- `native16-blue`: 에디터가 읽는 라나 파랑 16×16
- `previews-red`, `previews-blue`: 최근접 확대 확인 이미지
- `strict16-ai-and-native16-comparison.png`: 선택 원화와 최종본 비교
- `validation-report.json`: 격자·머리·팔레트·캔버스 검사 결과
- `sage-face-refresh-report.json`: 22개 최종본의 얼굴 일치와 마스크 밖
  장비 0픽셀 변경 검사 결과
- `PROMPTS.md`: 최종 공통 프롬프트와 클래스별 지시

세이지 얼굴 마스크만 다시 적용할 때는 기존 장비 기준 폴더를 지정해
다음 도구를 사용한다.

```bash
python3 tools/apply_liana_lana_sage_face_mask.py \
  --baseline-root docs/assets/ai-class-source/archive/liana-lana/before-sage-face-v39
```

직전 v38 얼굴 적용 전 작업은
`archive/liana-lana/before-sage-face-v39`에 보관했다. 직전 v37 작업은
`archive/liana-lana/before-strict16-v38/liana-lana-paired-v37`에
보관했다.

## 최신 세이지 전용 얼굴 갱신

리아나 세이지에서 다시 저장한 91픽셀 머리 마스크를 라나 세이지에도
복사했다. 이번 갱신은 `18` 세이지 두 장에만 적용하며 나머지 클래스의
장비와 얼굴은 변경하지 않는다.

```bash
python3 tools/sync_liana_lana_sage_mask.py
```

검증 결과는 `sage-only-face-refresh-report.json`에 기록한다.
