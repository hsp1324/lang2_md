# 최신 AI 클래스 작업물

## 공통 클래스 어두운 경계 보정 v64

엘윈에서 직접 편집한 로드 `04`, 하이로드 `0B`, 메이지 `13`,
아크메이지 `14`, 소드마스터 `1A`를 기준으로 투명하게 뚫려 맵
배경이 통과하던 목·팔·몸통·얼굴·장비 경계를 원작 윤곽색
`#242424`으로 막았다. 같은 클래스 템플릿을 쓰는 AI 재디자인 30개에
같은 구조를 적용했으며, 원본 유지 클래스와 이미 채워진 머리·갑옷·무기
픽셀은 변경하지 않았다. 엘윈 5개의 직접 편집은
`editor/ai_class_design_overrides.json`에, 다른 지휘관의 공통 경계는
`tools/build_ai_class_sprite_assets.py`의 잠긴 머리·탈것 제외 규칙에 저장되어
전체 AI 자산을 다시 빌드해도 유지된다.

현재 적용 중인 최신 작업물은
[`latest/elwin-hero-v2`](latest/elwin-hero-v2),
[`latest/elwin-mounted-v2`](latest/elwin-mounted-v2),
[`latest/shared-archmage-lester-v1`](latest/shared-archmage-lester-v1),
[`latest/shared-hein-classes-v1`](latest/shared-hein-classes-v1),
[`latest/shared-high-lord-hein-v1`](latest/shared-high-lord-hein-v1),
[`latest/shared-swordmaster-hein-v1`](latest/shared-swordmaster-hein-v1),
[`latest/shared-lord-elwin-high-lord-v1`](latest/shared-lord-elwin-high-lord-v1),
[`latest/liana-lana-strict16-v1`](latest/liana-lana-strict16-v1),
[`latest/sherry-v2`](latest/sherry-v2),
[`latest/hein`](latest/hein), [`latest/lester`](latest/lester)이다.

현재 엘윈 로드는 사용자가 승인한 기존 엘윈 하이로드 디자인을 그대로
재배치한 결과다. 이전에 별도로 만든 보병 로드 v2는 삭제하지 않고 비교용
시안으로 보존한다.

- 이전 보병 로드 AI 원화·최종 16×16:
  [`latest/elwin-lord-v2`](latest/elwin-lord-v2)
- 이전 시안 생성·검증 기준:
  [`README.md`](latest/elwin-lord-v2/README.md),
  [`PROMPTS.md`](latest/elwin-lord-v2/PROMPTS.md)

엘윈 히어로 최신 v2는 원작·현재 73픽셀 얼굴 마스크만 최초 입력으로
사용해 만든 넓은 보병 히어로다. 백은·왕청 중갑, 금장 견갑, 진홍 망토와
손에 연결된 대형 검을 사용하며 16개 행·열을 전부 채운다.

엘윈 하이랜더·실버나이트 최신 v2는 원작 전체와 각각의 현재 얼굴·탈것
마스크만 입력으로 사용해 새로 생성했다. 하이랜더 얼굴 `60/60`, 탈것
`86/86`픽셀과 실버나이트 얼굴 `59/59`, 탈것 `108/108`픽셀을 원본으로
완전히 고정한 뒤 AI 갑옷·옷·창·방패만 16×16로 변환했다. 두 결과 모두
16개 행·열을 전부 사용하고 보이는 색은 각각 10색, 12색이다.

- 최종 비교:
  [`all-elwin-mounted-v2.png`](latest/elwin-mounted-v2/all-elwin-mounted-v2.png)
- AI 원화·최종 16×16:
  [`latest/elwin-mounted-v2`](latest/elwin-mounted-v2)
- 생성·변환 기준:
  [`README.md`](latest/elwin-mounted-v2/README.md),
  [`PROMPTS.md`](latest/elwin-mounted-v2/PROMPTS.md)

레스터의 사용자 편집 아크메이지는 동일 클래스 8명의 공통 장비·실루엣
템플릿으로 사용한다. 헤인의 사용자 승인 프리스트와 사용자 편집 메이지,
하이프리스트도 같은 방식으로 대상 캐릭터에 적용한다. 각 캐릭터의 현재
얼굴 마스크는 그대로 유지하고 장비 주색만 캐릭터별로 바꾼다.
헤인 아크메이지도 기존 에디터 저장 이력은 보존하되 레스터 아크메이지
공통 템플릿을 우선 적용한다.
헤인 하이로드의 빨간 망토는 헤인 로드·아크메이지와 맞춘 밝은 연두색으로
바꾸며, 변경 전 빨간 버전과 보호 마스터는 그대로 보관한다.

헤인 하이로드와 헤인 소드마스터도 공통 템플릿으로 사용한다. 하이로드는
엘윈·리아나·라나·쉐리·헤인·스코트·키스·아론·제시카에 적용하고,
소드마스터는 엘윈의 별도 디자인을 보호한 채 헤인·키스·아론·제시카에
헤인 장비 좌표와 캐릭터별 색을 적용한다. 엘윈의 기존 하이로드 디자인은
엘윈 로드로 재배치한다.

제시카의 하이로드 `0B`와 소드마스터 `1A`는 공통 장비 중심보다 원본
머리·얼굴이 한 칸 왼쪽에 놓여 보이므로, 최종 합성 단계에서 보이는
머리·얼굴 픽셀만 오른쪽으로 한 칸 이동한다. 하이로드는 이동된 결과를
사용자가 다시 저장한 이전 편집 이력 대신 헤인 하이로드의 파랑·금색
갑옷·방패·검 실루엣을 다시 적용한다. 망토는 밝은 하늘색·파랑·진한
파랑의 3단 명암으로 바꾼다. 소드마스터도 합성 단계에서 머리만 이동한다.
갑옷·견갑·방패·검은 이동하지 않는다.

제시카 메이지 `13`도 기존 빨강 로브 편집 이력은 보존하되 헤인의 승인된
메이지 실루엣을 다시 기준으로 사용한다. 얼굴·청색 머리와 목제 지팡이,
녹색 보석은 유지하고 로브·망토만 진한 파랑·중간 파랑·밝은 하늘색
3단 명암으로 바꾼다. 양쪽 어깨 장식 11픽셀은 원본 제시카 메이지처럼
빨강·진홍 명암으로 남긴다.

제시카 소드마스터 `1A`는 사용자가 저장한 오른쪽 1칸 머리 정렬과 현재
빨강·회청색 배색, 장검, 회색 부츠를 그대로 유지한다. 상체와 허리 사이의
빈 9행, 오른쪽 소매, 하단 망토 주름에서 끊겨 보이던 연결부만 소폭
보정한다. 보정 전 저장본은
`archive/jessica-swordmaster-before-polish-v1/`에 보존한다.

엘윈 소드마스터 `1A`는 사용자가 새로 그린 하단 망토 좌표를 보존하고
원작 엘윈 지휘관 망토와 같은 선명한 진홍색으로 보정한다. 엘윈 메이지
`13`은 이전 사용자 시안 이력은 보관하되 헤인의 사용자 편집 메이지
장비·지팡이·실루엣을 우선 적용하며, 연결된 왼쪽 망토만 엘윈과 같은
진홍색 명암으로 바꾼다.

에디터 클래스 트리는 캐릭터당 대표 히든 경로 하나만 담은 10개 물리
전직 레코드와 별도로, 원작 캐릭터 전용 스프라이트 표에 있는 복수 히든
경로도 표시한다. 엘윈의 로얄나이트, 리아나·라나의 에이전트·자베라,
쉐리의 드래곤마스터·프린세스, 헤인·레스터의 자베라, 제시카의 서머너를
포함해 10개가 복원되어 전체 에디터 AI 자산은 180개다. 이 보조 히든
클래스는 캐릭터 전용 원작 16×16을 편집 가능한 초기값으로 사용하며,
실제 ROM 전직 레코드는 변경하지 않는다.

공통 템플릿의 머리 마스크는 `v45`부터 보이는 얼굴·머리 픽셀만 유지한다.
마스크 안의 투명 좌표에서는 장비를 지우지 않아 리아나·라나의 긴 머리
마스크와 겹치는 방패·견갑·무기 외곽을 보존한다. 재배색은 임의 고채도
색이 아니라 대상의 원본 클래스 팔레트를 사용한다. 하이로드도 리아나는
빨강·진홍 망토, 라나는 파랑·남청 망토를 사용해 두 자매의 색 대비를
유지한다. 라나 하이로드의 갑옷 넓은 면은 라나 원본의 하늘색, 음영은
원본 중간 파랑으로 다시 맞추고 망토는 중간 파랑·진한 파랑으로
분리한다. 양쪽 발·부츠의 회색 7픽셀은 유지한다. 리아나의 이전 파란
하이로드 편집본은 archive에 보존한다.
아론 로드는 회색
망토와 회색 방패가 겹쳐 보이지 않도록 망토를 황토색, 방패를 나이트와
같은 파랑·하늘색 계열로 분리했다. 메이지와 아크메이지는 기본 아론의
흰색·황토색 망토를 이어 가되 아크메이지는 흰색을 넓은 주면으로 쓰고
황토색을 주름·테두리에 남긴다. 지팡이의 파란 마력 효과는 유지한다.
하이로드의 방패와 청색 장비도 나이트 방패와 같은 하늘색 계열로
맞췄다. 아론 소드마스터는 사용자가 다시 저장한 얼굴
마스크로 얼굴 픽셀을 복원했다. 엘윈 로드와 하이로드의 망토는 원본
엘윈과 같은 선명한 빨강으로 맞췄다. 엘윈 로드의 오른쪽 방패는 현재
하이로드처럼 둥근 실루엣과 파랑·금색 격자 명암으로 구성했다.
이전 적용본은 archive에 남겨 두었다.

로렌은 NPC 전용 하이로드 `9B`를 사용한다. 플레이어 하이로드 `0B`와
내부 클래스 레코드는 별도다. 시나리오 1의 민병대는 일반 NPC 로드
`99`를 사용하며, 두 클래스 모두 원본 스프라이트 `0x1C`를 공유한다.
민병대 `99`는 흰색 갑옷 면을 살리고 회색 명암을 옅은 금빛 아이보리와
따뜻한 갈색으로 바꾼다. NPC 프리스트 `9C`의 제의와 두건도 같은
옅은 크림 아이보리·금빛 아이보리·따뜻한 갈색 명암을 사용해 시나리오
1에서 둘이 한 쌍처럼 보이게 한다. 순백색이던 밝은 면에는 가장 옅은
아이보리만 더한다.

로렌 `9B`는 투구와 갑옷의 순백색 하이라이트에 아주 옅은 라일락을
더하고 회색 명암을 샤먼 `0A`와 같은 밝은 라벤더와 진한 자주색으로
바꾼다. 오른쪽 흰 검과
파랑·하늘색 방패, 금색 테두리, 얼굴과 실루엣의 모든 픽셀 위치는
민병대와 로렌 모두 원본을 유지한다.

시나리오 10의 적 해적은 NPC 파이레츠 `9A`를 사용한다. 원본
스프라이트 `0x1C`의 흰 검·파란 방패·금색 테두리와 실루엣은 유지하고,
중립 회색 갑옷 면을 옅은 하늘색과 차분한 해군 청회색으로 바꾼다.
순백색 갑옷 면에도 에디터 시안에서만 알아볼 수 있을 정도의 옅은
하늘색을 더한다.

샤먼 `0A`는 몸의 보라색 제의와 두건을 같은 그라데이션으로 연결한다.
두건의 흰 하이라이트는 유지하고 앞쪽 회색 면은 밝은 라벤더로, 뒤쪽
청회색 음영은 진한 자주색으로 바꾼다. 얼굴·눈·지팡이와 실루엣은
유지하며, 캐릭터별 머리카락을 쓰는 지휘관 샤먼에는 두건 재배색을
적용하지 않는다.

엘윈의 기존 하이로드 디자인은 변경 가능한 로드의 공통 템플릿으로
사용한다. 초기 클래스가 파이터라서 로드가 공유 묶음의 두 번째 디자인이
되는 엘윈·쉐리·스코트·키스·아론의 로드에 적용한다. 리아나·라나·헤인·
제시카의 로드는 묶음의 첫 원본 디자인이므로 유지하고, 레스터는 로드
클래스가 없다.

- 엘윈 하이로드 기반 로드 비교:
  [`all-lord-variants.png`](latest/shared-lord-elwin-high-lord-v1/all-lord-variants.png)

- 아크메이지 전체 비교:
  [`all-archmage-variants.png`](latest/shared-archmage-lester-v1/all-archmage-variants.png)
- 헤인 기준 세 클래스 전체 비교:
  [`all-hein-template-variants.png`](latest/shared-hein-classes-v1/all-hein-template-variants.png)
- 헤인 기준 하이로드 전체 비교:
  [`all-high-lord-variants.png`](latest/shared-high-lord-hein-v1/all-high-lord-variants.png)
- 헤인 기준 소드마스터 전체 비교:
  [`all-swordmaster-variants.png`](latest/shared-swordmaster-hein-v1/all-swordmaster-variants.png)

쉐리 최신 v2는 원작 전체와 현재 사용자 얼굴 마스크만 입력으로 사용해
상위 중복 클래스 11종을 내장 이미지 생성으로 각각 새로 만든 결과다.
이전 쉐리 AI 이미지는 입력하지 않았다. 선택 원화 단계에서 큰 얼굴,
눈·흰자, 은발 단발 셀을 정확히 고정하고, 최종 16×16에서는 16개 행·열을
모두 사용한다.

- 전체 비교:
  [`latest/sherry-v2/sherry-v2-editor-final-comparison.png`](latest/sherry-v2/sherry-v2-editor-final-comparison.png)
- 원시 AI:
  [`latest/sherry-v2/sherry-v2-raw-ai.png`](latest/sherry-v2/sherry-v2-raw-ai.png)
- 생성·변환 기준:
  [`latest/sherry-v2/README.md`](latest/sherry-v2/README.md),
  [`latest/sherry-v2/PROMPTS.md`](latest/sherry-v2/PROMPTS.md)

리아나·라나 최신 v39 작업은 1254px AI 캔버스를 정확한 16개 논리 행·열
기준으로 다시 생성한 결과다. 작은 32×32식 세부 블록이 많은 후보는
폐기하고, 선택 원화 단계에서 리아나 세이지에서 다시 저장한 82픽셀 얼굴
마스크를 먼저 완전히 고정한 뒤 전체 캔버스를 16×16로 읽는다. 이 얼굴
마스크는 리아나·라나 11개 클래스 모두에 적용했다. 피사체 크롭이나
가로세로 강제 확대를 사용하지 않는다. 리아나는 적색, 라나는 같은
좌표의 청색 장비다.

- 실제 16×16 AI 청색·적색 원화:
  [`latest/liana-lana-strict16-v1`](latest/liana-lana-strict16-v1)
- 에디터 입력 원화:
  [`native16-blue`](latest/liana-lana-strict16-v1/native16-blue),
  [`native16-red`](latest/liana-lana-strict16-v1/native16-red)
- 전체 비교:
  [`strict16-ai-and-native16-comparison.png`](latest/liana-lana-strict16-v1/strict16-ai-and-native16-comparison.png)
- 생성·변환 기준:
  [`README.md`](latest/liana-lana-strict16-v1/README.md),
  [`PROMPTS.md`](latest/liana-lana-strict16-v1/PROMPTS.md)

- AI 신규 원화: [`latest/hein/raw`](latest/hein/raw)
- 배경 제거 원화: [`latest/hein/clean`](latest/hein/clean)
- 최종 16×16: [`latest/hein/logical16`](latest/hein/logical16)
- 전체 비교:
  [`latest/hein/hein-latest-ai-and-16x16.png`](latest/hein/hein-latest-ai-and-16x16.png)
- 생성·변환 기준: [`latest/hein/PROMPTS.md`](latest/hein/PROMPTS.md)

헤인 소서러 `09`는 확대된 현재 얼굴·청색 머리 픽셀과 승인된 헤인
메이지의 장비 문법을 함께 레퍼런스로 넣어 별도로 다시 생성했다. 최종
몸체에 ROM 얼굴을 덮어씌우지 않고 AI 생성 단계에서 같은 얼굴·머리
형태를 유지한다. 원본 비율을 보존한 16×16 최근접 변환 뒤 메가드라이브
채널값 15색으로 정리했다. 프리스트 `11`과 하이프리스트 `16`은 에디터의
AI 원화 칸에서 중간 축소 셀이 아니라 각 승인 마스터 원본을 직접
표시한다.

- 소서러 원본·16×16·프롬프트:
  [`latest/hein-sorcerer-v2`](latest/hein-sorcerer-v2)

이전 헤인 시안은 `archive/hein` 아래에 버전별로 보관한다. 원작과 사용자
마스크처럼 재생성에 필요한 기준 자료는 기존 가이드 폴더에 유지한다.

레스터 최신 작업은 위저드 `15`의 기존 AI 원화를 유지하면서 최종
16×16에서 잘못 주색이 된 빨강을 보라색으로 다시 디자인한 결과다.
AI 원화·최종본·비교 이미지는 [`latest/lester`](latest/lester)에
정리하며, 이전 변환본은 `archive/lester` 아래에 보관한다.
