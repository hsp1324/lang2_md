# Elwin native16 v10

원작 유사성을 우선해 메이지, 하이랜더, 나이트마스터를 다시 생성한
현재 적용 묶음이다.

- `13 Mage`: 원작의 보행 자세, 넓은 로브, 지팡이, 청색·은색·적색
  계열을 유지하고 중청색·보라색 장식만 소폭 추가했다.
- `0C Highlander`: 원작의 작은 횡방향 말, 기수 위치, 말의 목·머리·다리,
  붉은 안장을 유지하고 은색 기병 장식을 소폭 추가했다.
- `1B Knight Master`: 원작의 갈회색 횡방향 말과 기수·장비 배치를
  유지하고 은색 중장갑과 붉은 띠를 소폭 추가했다.
- 나머지 7개 클래스는 v9 채택본을 유지했다.

세 새 이미지의 입력은 해당 클래스의
`../elwin-head-ratio-guides-v2/*-original-full-ratio.png`와
`*-masked-identity.png`뿐이다. 이전 AI 출력은 이미지 참조로 사용하지
않았다.

하이랜더와 나이트마스터는 AI 원화의 말이 최종 팔레트 변환에서 작고
어둡게 뭉개지지 않도록 원작 말의 점유 외곽을 보존한다. AI 원화는
말 중앙의 안장·기병 장비 영역에만 합성한다. 재생성 명령은 다음과 같다.

```sh
python3 tools/normalize_elwin_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/elwin-native16-v10/raw \
  --output-dir docs/assets/ai-class-source/elwin-native16-v10 \
  --preserve-original-mounts
```

## 검증

- 메이지 AI 원출력 마스크 일치율: 95.7%
- 하이랜더 AI 원출력 마스크 일치율: 96.7%
- 나이트마스터 AI 원출력 마스크 일치율: 98.3%
- 마스크 고정 후 세 클래스와 전체 10개 정체성 픽셀: 원작과 100% 일치
- 머리에 연결된 몸·장비: 67~98논리픽셀

## 파일

- `raw/`: 채택한 이미지 생성·편집 원출력
- `logical16/`: 16×16 변환 및 사용자 마스크 완전 고정본
- 루트 클래스 PNG: 에디터 입력용 nearest-neighbor 확대본
- `elwin-v10-raw-ai-contact-sheet.png`: 원출력 10개 합본
- `elwin-v10-contact-sheet.png`: 마스크 고정 후 10개 합본
- `elwin-v10-ai-final-rom.png`: AI 원화·최종 16×16·ROM 비교 합본
- `comparisons/`: 클래스별 비교 이미지
- `validation-report.json`: 자동 검증 결과

최종 이미지 생성 지시는 `PROMPTS.md`에 기록했다.
