# Elwin native16 v8

엘윈 상위 중복 클래스의 머리와 몸이 서로 다른 해상도로 보이던 v7 문제를
수정한 묶음이다. 사용자가 괜찮다고 확인한 비숍은 그대로 유지했고,
나머지 9개 클래스는 새로 생성했다.

새 이미지 생성 호출에는 해당 클래스의 다음 두 파일만 입력했다.

- `../elwin-head-ratio-guides-v2/XX-original-full-ratio.png`
- `../elwin-head-ratio-guides-v2/XX-masked-identity.png`

v5, v6, v7, direct 시트나 다른 AI 결과를 이미지 레퍼런스로 사용하지
않았다. 유지한 비숍도 다른 클래스의 레퍼런스로 사용하지 않았다.

## 채택 조건

- AI 원출력의 사용자 마스크 픽셀 일치율 90% 이상
- 머리에 연결된 몸·장비 픽셀 45개 이상
- 머리와 몸이 같은 16×16 논리픽셀 크기로 보일 것
- 얼굴 바로 아래에 넓은 목·어깨 또는 기수 몸통이 연결될 것
- 보병 몸은 하단 절반을 넓게 채우고, 말은 작은 정밀화가 아닌 굵은
  블록 실루엣일 것
- 잘린 장비, 머리 영역을 침범한 무기, 작은 몸, 미세 장식은 폐기

최종 원출력 머리 일치율은 90.4~100%이며, 마스크 고정 후와 실제
에디터 자산에서는 모든 마스크 좌표가 원작과 100% 일치한다.

## 파일

- `raw/`: 채택한 이미지 생성 원출력
- `logical16/`: 16×16 변환 및 사용자 마스크 완전 고정본
- 루트 클래스 PNG: `logical16`을 nearest-neighbor로 확대한 에디터 입력
- `elwin-v8-raw-ai-contact-sheet.png`: 원출력 10개 합본
- `elwin-v8-contact-sheet.png`: 마스크 고정 후 10개 합본
- `elwin-v8-ai-final-rom.png`: AI 원화·최종 16×16·ROM 비교 합본
- `comparisons/`: 클래스별 비교 이미지
- `validation-report.json`: 머리 일치율과 연결된 몸 픽셀 검증

최종 프롬프트 규칙은 `PROMPTS.md`에 기록했다.
