# 최신 AI 클래스 작업물

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

공통 템플릿의 머리 마스크는 `v45`부터 보이는 얼굴·머리 픽셀만 유지한다.
마스크 안의 투명 좌표에서는 장비를 지우지 않아 리아나·라나의 긴 머리
마스크와 겹치는 방패·견갑·무기 외곽을 보존한다. 재배색은 임의 고채도
색이 아니라 대상의 원본 클래스 팔레트를 사용한다. 특히 아론 메이지와
아크메이지는 빨강·자주색 대신 원본의 회색·백색·청회색으로 복원했다.
현재 아론 메이지와 아크메이지는 같은 짙은 왕청색·중청색·하늘색 계열로
통일했다. 아크메이지는 밝은 은백색만으로 형태가 흐려지던 문제를 없애고,
첫 청색 적용본보다 명암을 한 단계 짙게 했다. 아론 소드마스터는 사용자가
다시 저장한 얼굴 마스크로 얼굴 픽셀을 복원했다. 엘윈 로드와 하이로드의
망토는 원본 엘윈과 같은 선명한 빨강으로 맞췄다. 이전 적용본은 archive에
남겨 두었다.

로렌은 NPC 전용 하이로드 `9B`를 사용한다. 플레이어 하이로드 `0B`와
이름·원본 실루엣은 같지만 내부 클래스 레코드가 별도이므로, `9B`만
초록·진초록·금색으로 재배색해 다른 NPC와 구분한다.

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

이전 헤인 시안은 `archive/hein` 아래에 버전별로 보관한다. 원작과 사용자
마스크처럼 재생성에 필요한 기준 자료는 기존 가이드 폴더에 유지한다.

레스터 최신 작업은 위저드 `15`의 기존 AI 원화를 유지하면서 최종
16×16에서 잘못 주색이 된 빨강을 보라색으로 다시 디자인한 결과다.
AI 원화·최종본·비교 이미지는 [`latest/lester`](latest/lester)에
정리하며, 이전 변환본은 `archive/lester` 아래에 보관한다.
