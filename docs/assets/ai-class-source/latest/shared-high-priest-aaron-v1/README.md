# 아론 사용자 편집 하이프리스트 공통형 v1

에디터에서 사용자가 직접 저장한 아론 하이프리스트 `8:16`을 원본
마스터로 보존하고, 실제 하이프리스트가 있는 리아나·라나·헤인·키스·
아론·제시카에 같은 장비·지팡이·망토 좌표를 적용한다.

- 아론: 저장된 16×16을 픽셀 단위로 그대로 유지
- 리아나: 진홍·금색
- 라나: 남청·파랑·하늘색
- 헤인: 짙은 초록·연두
- 키스: 청록·파랑
- 제시카: 자주·보라·연보라
- 캐릭터별 현재 얼굴·머리·눈 마스크는 정확히 복원
- 투명색 제외 최대 15색, 빈 행·열 없음

이전 하이프리스트 결과는 `previous/`, 적용 전 얼굴 기준은
`references/`, 최종 결과는 `logical16/`에 보존한다.

```bash
python3 tools/build_shared_aaron_high_priest_variants.py capture
python3 tools/build_shared_aaron_high_priest_variants.py apply
```
