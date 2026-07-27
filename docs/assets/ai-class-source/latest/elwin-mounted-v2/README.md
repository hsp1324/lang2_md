# 엘윈 하이랜더·실버나이트 v2

엘윈의 `0C 하이랜더`와 `1D 실버나이트`를 원작 전체 이미지, 현재 얼굴
마스크, 현재 탈것 마스크만 참조해 새로 생성한 작업이다. 이전 AI 생성
이미지는 최초 입력으로 사용하지 않았다.

최종 적용 규칙은 다음과 같다.

- 얼굴·머리·눈은 각각 현재 사용자 마스크 `60`, `59`픽셀을 원본과
  바이트 단위로 일치시킨다.
- 탈것은 현재 사용자 마스크 `86`, `108`픽셀을 원본과 일치시킨다.
  투명 픽셀도 잠금 대상이므로 탈것 주변 빈 공간을 AI 배경이나 장비로
  잘못 채우지 않는다.
- AI가 제안한 갑옷·옷·창·방패 부분만 논리 16×16 격자에 스냅한다.
- 16개 행과 열을 모두 사용하고, 보라색 배경과 완전 검정을 제거한다.
- 메가드라이브 4bpp 제한에 맞춰 보이는 색을 15색 이하로 제한한다.

주요 파일:

- `raw/`: 이미지 생성 원본 후보
- `logical16/`: 에디터와 빌드가 사용하는 실제 16×16 원화
- `all-elwin-mounted-v2.png`: 두 클래스 최종 비교
- `validation-report.json`: 얼굴·탈것·팔레트·캔버스 검증
- `guides/`: 생성에 사용한 원작·얼굴 마스크·탈것 마스크

재변환:

```bash
python3 tools/normalize_elwin_mounted_ai_source.py \
  --highlander-raw docs/assets/ai-class-source/latest/elwin-mounted-v2/raw/0C-highlander-v2.png \
  --silver-knight-raw docs/assets/ai-class-source/latest/elwin-mounted-v2/raw/1D-silver-knight-v2.png
```
