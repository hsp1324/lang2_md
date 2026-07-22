# Commander Name And Class Runtime Checklist

지휘관 이름, 클래스, 용병 이름은 모든 시나리오의 필수 통과 항목이다. 대사가
정상이어도 아래 화면 중 하나에서 한 글자라도 깨지거나 일본어가 남으면 해당
시나리오를 완료 처리하지 않는다.

## Required Surfaces

- 지휘관 준비창의 전체 로스터: 첫 페이지와 좌우로 넘긴 모든 페이지
- 지휘관 배치창의 선택 패널과 자동 배치 뒤 상태
- 맵 하단 상태창: 아군, 적군, NPC 지휘관과 인접 용병
- 지휘관 상세창: 이름, 클래스, 공격/방어, 지휘범위, 수정치
- 전투 명령창과 전투 연출 좌우 이름/클래스
- 대사 초상화가 뜬 동안의 화자 이름/클래스와 하단 상태창
- 레벨업, 클래스 체인지 전후의 이름/클래스
- 전과보고의 모든 참가 지휘관 이름

## Per-Scenario Rule

1. 일본 ROM의 `name_id`, `class_id`, 용병 ID를 먼저 기록한다.
2. 아군, 적군, NPC 고정 레코드와 이벤트 증원 레코드를 모두 포함한다.
3. 현재 저장 데이터에서 변한 아군 클래스도 별도로 기록한다.
4. 각 진영에서 최소 한 명은 하단 상태창, 상세창, 전투창을 모두 캡처한다.
5. 새 초상화, 전투 스프라이트, 증원, 레벨업 뒤 같은 항목을 다시 확인한다.
6. 캡처 파일과 ROM checksum을 `HANDOFF.md`와 런타임 인벤토리에 남긴다.

## Scenario 21 Shared-VRAM Regression

일본 원본의 고정 적군/NPC 레코드는 다음과 같다.

| Record | Name | Class |
| --- | --- | --- |
| 0, 4 | 서큐버스 | 서큐버스 |
| 1, 6 | 리빙아머 | 리빙아머 |
| 2, 5 | 리치 | 리치 |
| 3 | 라나 | 다크프린세스 |
| 7, 8, 9 | 크라켄 | 크라켄 |
| 10 | 제국지휘관 | 아크메이지 |

전투 그래픽이 VRAM `0x6000`과 `0x7000`을 사용하면서 한글 확장 글꼴
segment 0 (`0x340..0x347`)과 segment 1 (`0x398..0x3AF`)을 계속 덮는다.
단순 전투 종료 복원이나 맵 상태 갱신 시 반복 복원으로는 해결되지 않았다.

Production `C1A2`는 맵 하단 이름 8타일 `0x5D8..0x5DF`와 클래스 8타일
`0x5E0..0x5E7`을 분리하고, 현재 문자열의 8x8 글리프만 동기식으로 쓰는 전용
렌더러를 사용한다. S21 completion probe `DD8E`에서 실제 라나 전투와 초상화,
전리품, 제국군 증원 이벤트 뒤 다음 항목을 확인했다.

- `제국지휘관/아크메이지`, `서큐버스/서큐버스`, `리빙아머/리빙아머`,
  `리치/리치`
- `헤인/샤먼`, `레스터/매직나이트`, `제시카/소서러`,
  `스코트/드래곤나이트`
- 라나 전투 화면의 `로드/다크프린세스`와 전투 후 상세창의
  `제국지휘관/아크메이지`, `서큐버스/서큐버스`

대표 증거는 `captures/run/c1a2_s21_hein_shaman_postbattle_status.png`,
`c1a2_s21_succubus_postbattle_status.png`,
`c1a2_s21_succubus_postbattle_popup.png`과
`c1a2_s21_map_after_lana_event.png`이다. 준비창 8명은
`c1a2_s21_equip_01_elwin_road.png`부터
`c1a2_s21_equip_08_scott_dragonknight.png`까지 따로 남겼다.

시나리오 4에서도 교차 검증했다. `모건/소서러`와
`제국지휘관/워록`은 지도 하단 상태창과 상세창을 동시에 열어도 모두 정상이다.
대표 캡처는 `captures/run/c1a2_s04_morgan_popup_with_bottom.png`와
`captures/run/c1a2_s04_imperial_warlock_popup_with_bottom.png`이다. 후자의
정확 상태는 `captures/analysis/c1a2_s04_imperial_warlock_popup.gst`에
보존했다. VRAM 이름 슬롯 `0x5D8..0x5DC`는 정확히 `제국지휘관`, 클래스
슬롯 `0x5E0..0x5E1`은 정확히 `워록`의 원시 글리프와 일치한다.

이 결과는 동적 지도 렌더러가 원래 정적 배정 글자 `모`, `건`, `록`을 쓰는
대표 상세창과 공존함을 증명하지만, 전체 시나리오 검증을 대신하지 않는다.
아군·적군·NPC의 준비창, 하단 상태창, 상세창, 전투창, 대사창을 시나리오별로
계속 통과시켜야 한다. 현재 전투 연출의 중앙 하단 `地形`은 일본어 잔존으로
별도 미완료 항목이다.

## Scenario 4 Current-Build Matrix

Production `C1A2`에서 아래 고유 조합을 지도 하단과 상세창 또는 아군 명령창을
동시에 보이게 하여 확인했다.

| Side | Name | Class | Map | Popup/command |
| --- | --- | --- | --- | --- |
| 아군 | 엘윈 | 파이터 | 통과 | 통과 |
| 아군 | 헤인 | 워록 | 통과 | 통과 |
| 아군 | 스코트 | 파이터 | 통과 | 통과 |
| NPC | 리아나 | 클레릭 | 통과 | 통과 |
| NPC | 신관 | 클레릭 | 통과 | 통과 |
| NPC | 사제 | 프리스트 | 통과 | 통과 |
| 적군 | 제국지휘관 | 시프 | 통과 | 통과 |
| 적군 | 모건 | 소서러 | 통과 | 통과 |
| 적군 | 제국지휘관 | 샤먼 | 통과 | 통과 |
| 적군 | 제국지휘관 | 워록 | 통과 | 통과 |
| 이벤트 NPC | 수수께끼의 기사 | 파이터 | 통과 | 통과 |

동일한 이름/클래스의 중복 고정 레코드는 같은 재배치 문자열과 동적 글리프
경로를 사용한다. 원본에서 이벤트 동안만 잠깐 보이는 숨김 레코드 4는 진단 ROM
checksum `48C8`에서 숨김 비트와 좌표만 바꿨다. 일본 원본과 production의
`name_id 0x0B`, `class_id 0x01`, 레벨, AT/DF, 진영, 용병은 그대로다.
`captures/run/c1a2_s04_masked_knight_map_status.png`와
`c1a2_s04_masked_knight_popup_with_bottom.png`에서
`수수께끼의 기사/파이터`를 확인했다. 정확 상태는
`captures/analysis/c1a2_s04_masked_knight_popup.gst`이며, 이름 8칸은
`수수께끼의 기사`, 클래스 3칸은 `파이터`의 원시 글리프와 모두 정확히
일치한다. 원본 이벤트의 별도 화자명 `가면기사`도 정상이다.

`451E` clear probe와 AT/DF 99 진단 슬롯의 실제 엘윈-모건 전투에서는 좌우
클래스 `파이터/소서러`가 정상 표시됐다. AT/DF 99는 한 번의 전투로 이벤트를
진행하기 위한 격리 런타임 값일 뿐 production ROM이나 편집기 기본값이 아니다.
대표 캡처는
`captures/run/c1a2_s04_*_map_status.png`와
`captures/run/c1a2_s04_*_popup_with_bottom.png` 또는
`*_command_with_bottom.png`이다.
