# 최신 리아나 힐러 기반 리아나·라나 힐러 v1

사용자가 에디터에서 직접 수정한 최신 리아나 힐러 `2:08`을 장비·지팡이·
망토 좌표의 마스터로 사용한다. 리아나는 저장본을 그대로 유지하고 라나
힐러 `3:08`은 같은 좌표에서 붉은 장비색만 파랑·하늘색으로 바꾼다.
두 캐릭터의 금발·얼굴·눈은 각각의 최신 마스크와 ROM 원본 픽셀을
사용한다.

- `master/02-08-liana-user-edited.png`: 최신 사용자 편집 마스터
- `logical16/`: 본편 적용 논리16
- `previews/`: 최근접 확대본
- `previous/`: 적용 전 소스와 라나 힐러
- `all-liana-lana-healer-variants.png`: 두 결과 비교
- `validation-report.json`: 얼굴·팔레트 검증

재적용 명령:

```bash
python3 tools/build_liana_lana_healer_variants.py
```
