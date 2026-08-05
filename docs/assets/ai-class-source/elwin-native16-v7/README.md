# Elwin native16 v7

엘윈 상위 중복 클래스 10개를 완전히 새로 생성한 원화 묶음이다.
Codex 내장 이미지 생성의 각 호출에는 다음 두 파일만 입력했다.

- `../elwin-head-ratio-guides-v2/XX-original-full-ratio.png`
- `../elwin-head-ratio-guides-v2/XX-masked-identity.png`

v5, v6, direct 시트, 이전 AI 보드나 이전 생성 결과는 이미지 입력으로
사용하지 않았다.

## 채택 조건

- AI 원출력의 마스크 픽셀 일치율 90% 이상
- 머리와 실제로 연결된 몸·장비 픽셀 45개 이상
- 보행/기마 구도와 장비가 16×16 캔버스 안에 전부 표시
- 잘린 말·무기, 이동하거나 작아진 머리, 좁아 떠 보이는 몸은 재생성

채택한 원출력은 `raw/`에 있다. 이를 논리 16×16으로 축소한 뒤 사용자
마스크 좌표를 원작 픽셀로 고정한 파일은 `logical16/`에 있다. 루트의
클래스 PNG는 같은 논리 원화를 1024×1024 nearest-neighbor로 확대한
에디터 입력이다.

검증 수치는 `validation-report.json`에 있으며, 최종 10개 원출력 머리
일치율은 90.4~100%, 저장 원화의 마스크 일치율은 모두 100%다.

## 확인 이미지

- `elwin-v7-raw-ai-contact-sheet.png`: 채택된 AI 원출력 10개를 한 장에 표시
- `elwin-v7-contact-sheet.png`: 마스크 고정 후 AI 원화 10개를 한 장에 표시
- `elwin-v7-ai-final-rom.png`: AI 원화, 에디터용 16×16, 원작 ROM 비교
- `comparisons/`: 클래스별 AI/16×16/ROM 비교

최종 채택 프롬프트 규칙은 `PROMPTS.md`에 기록했다.
