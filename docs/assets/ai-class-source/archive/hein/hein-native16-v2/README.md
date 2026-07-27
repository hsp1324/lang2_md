# Hein native16 v2

기존 `hein-native16-v1` AI 원화의 장비·무기·실루엣을 재사용하면서,
사용자가 다시 편집한 헤인 마스크로 머리·얼굴을 재구성한 현재 적용
묶음이다. 이 단계에서는 새 이미지를 생성하지 않았다.

- 상위 중복 클래스 11개만 적용하며 기본 클래스는 ROM 원본 그대로다.
- 기존 AI 원화를 16×16로 정규화한 뒤 새 사용자 마스크 58~72픽셀을
  원작 값으로 100% 고정했다.
- 몸에 연결된 장비 픽셀은 클래스별 61~116픽셀이다.
- 세이지의 기존 원화만 높이가 14행이어서, 머리는 움직이지 않고 기존
  최하단 발 색을 15·16행까지 연장해 바닥 정렬했다.
- `hein-v2-contact-sheet.png`는 재구성된 11개를 한 장에 모은 시트다.
- `hein-v2-ai-final-rom.png`는 재구성 원화, 최종 ROM 팔레트 16×16,
  원작 ROM을 함께 비교한다.

## 재구성

```sh
python3 tools/normalize_hein_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/hein-native16-v2/raw \
  --output-dir docs/assets/ai-class-source/hein-native16-v2
```
