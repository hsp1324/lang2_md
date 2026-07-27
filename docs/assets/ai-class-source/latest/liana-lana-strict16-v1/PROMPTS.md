# 엄격 논리16 생성 프롬프트

기본 제공 이미지 생성 도구를 사용했으며, 모든 클래스는
`guides-1254/08-head-only-1254.png`를 편집 대상으로 사용했다.

## 최종 공통 프롬프트

```text
Use case: precise-object-edit
Asset type: extremely coarse enlarged literal 16x16 fantasy
strategy-game sprite.

Edit only magenta cells. Preserve every non-magenta input square exactly,
including all magenta gaps within the fixed head. Do not move, resize,
redraw, center, or decorate the fixed head.

Exactly 16 columns and 16 rows. The large input square is the smallest
allowed mark. Whole cells only. Use only eight visible subject colors and
large solid clusters. No half-cells and no 32x32 detail.

Liana main equipment is red, with white, gold, brown, skin, and charcoal.
Fill the bottom row and use both horizontal edges. The main item is on
image-right. Empty background remains flat #ff00ff.

No gradients, antialiasing, texture, tiny highlights, realistic detail,
text, frame, UI, extra person, extra human head, or detached fragments.
```

## 클래스별 추가 지시

- `08` 힐러: 적백 치유 로브, 금장, 오른쪽 청색 수정 지팡이
- `0B` 하이로드: 보병 백은 판금, 큰 견갑, 적색 망토, 오른쪽 검
- `11` 프리스트: 적백 제의, 금장, 오른쪽 성직 지팡이
- `13` 메이지: 넓은 적백 로브, 짧은 맨틀, 오른쪽 수정 지팡이
- `14` 아크메이지: 큰 적색 견갑 두 덩어리, 백색 중앙 로브,
  오른쪽 대형 청색 수정 지팡이
- `15` 위저드: 적백 장포와 망토, 금장, 오른쪽 보석 지팡이
- `16` 하이프리스트: 큰 백색 맨틀 두 덩어리, 적색 중앙 제의,
  오른쪽 단순 성직 지팡이, 머리 장식 금지
- `18` 세이지: 적백 학자 로브, 몸에 연결된 마도서, 오른쪽 지팡이
- `19` 팔라딘: 한 명의 기수와 한 마리의 말, 긴 적색 마갑 몸통,
  이미지 왼쪽 말 머리, 바닥의 네 다리, 오른쪽 검
- `1D` 실버나이트: 팔라딘과 같은 단순 기병 구조, 오른쪽 끝 수직 장창
- `28` 서머너: 짙은 적색 룬 로브, 연결된 두루마리, 오른쪽 수정 지팡이

## 선택 기준

- 원시 후보의 작은 하위 셀과 머리 이동을 검사하고 실패 후보는 보관만 한다.
- 선택 후보에는 74개 머리 셀을 1254px 원화 단계에서 다시 고정한다.
- 전체 캔버스를 크롭 없이 16개 동일 영역으로 읽는다.
- 최종 머리 74셀 일치, 청·적 알파 일치, 가시색 15개 이하,
  16개 행·열 사용 조건을 모두 만족해야 적용한다.
