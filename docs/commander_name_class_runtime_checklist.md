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

## Scenario 1 Multi-Turn Scratch Regression

휴대폰 RetroArch와 production `45D8`의 새 BlastEm 실행에서 처음에는 정상인
하단 이름·클래스가 3~4턴 무렵 지도/전투 그래픽 조각으로 바뀌는 현상을 모두
재현했다. 한글 문자열이나 저장 데이터가 바뀐 것이 아니라, 하단 상태창이 참조하는
동적 이름 타일 `0x5D8..0x5DF`와 클래스 타일 `0x5E0..0x5E7`을 VRAM
`0xA000` 대상 그래픽 로더가 나중에 덮어쓴 문제였다.

Production `6E2C`는 원본 `JSR 0x99B2`가 확인된 `0x00F176`, `0x00F330`,
`0x011984`의 세 호출 뒤 현재 런타임 레코드의 이름과 클래스를 같은 동적 타일에
동기식으로 다시 그린다. `$A628`이 유효 런타임 범위 밖이면 아무 작업도 하지 않으며,
레지스터와 원본 그래픽 로드 결과를 보존한다.

같은 실행에서 아군을 움직이지 않고 1~4턴의 415개 장면을 전부 보존했다.
적장 `제국지휘관`, 적 병사 `솔저`, `레아드`, `레온`, NPC `민병대`,
`사제/프리스트`의 이름·클래스가 지도 이동, 대사 초상화, 전투 전후에 모두
정상이다. 전체 확대 시트는
`captures/analysis/6e2c_s01_turn1_status_sheet.png`부터
`turn4_status_sheet.png`까지이며, 재개 가능한 상태는
`captures/analysis/6e2c_s01_turn5_command_clean.gst`이다.

## Direct Status-Path Regression

`6E2C` 이후에도 일부 하단 상태 갱신은 동적 맵 정보 경로가 아니라 원본
`0x0105BC` 직접 렌더러를 호출했다. 이 경로는 이름·클래스 문자열이 올바른데도
Window 타일맵에 고정 글꼴 ID를 기록하므로, 해당 고정 타일이 지도/전투 그래픽에
덮이면 `스`, `크`, `렌`, `가`, `터` 같은 특정 칸만 다시 깨질 수 있었다.

Production `4234`는 이름 테이블 `0x0618E8`과 클래스 테이블
`0x05E6D6/0x05E5CA`에 한해 `0x2B88C0` 동적 직접 렌더러를 사용한다.
`0x01042E/0x010444`의 숨은 BSR 경로와 `0x01B546` 초상화 대사 갱신을
포함하며, 후일담 다중 행 렌더러에는 적용하지 않는다. 각 글리프 호출 전후로
목적지 오프셋 D0를 보존해야 한다. 이 보존이 빠진 첫 구현은 상태창 작업 RAM
밖에 기록해 리셋됐으며 폐기했다.

현재 빌드의 필수 회귀 결과는 다음과 같다.

| Scenario | Side/type | Name / class | Result |
| --- | --- | --- | --- |
| 21 probe `5E20` | 적 고정 레코드 | 레스터 / 매직나이트 | 통과 |
| 21 probe `5E20` | 적 고정 레코드 | 서큐버스 / 서큐버스 | 통과 |
| 21 probe `5E20` | 적 고정 레코드 | 제시카 / 비숍 | 통과 |
| 1 production `4234` | 적 지휘관 | 발드 / 파이터 | 턴 5·6 통과 |
| 1 production `4234` | 적 병사 | 발드 / 창병 | 턴 5·6 통과 |
| 1 production `4234`, 실제 SRAM 신규 실행 | 적 지휘관 | 제국지휘관 / 세인트 | 턴 1·3 통과 |
| 1 production `4234`, 실제 SRAM 신규 실행 | 적 병사 | 제국지휘관 소속 병사 | 턴 1·3·4 통과 |
| 1 production `4234`, 실제 SRAM 신규 실행 | 적 지휘관 | 레아드 / 매직나이트 | 턴 1 통과 |
| 1 production `4234`, 실제 SRAM 신규 실행 | 적 지휘관 | 레온 / 나이트마스터 | 턴 1 통과 |
| 1 production `4234`, 실제 SRAM 신규 실행 | 적 지휘관 | 발드 / 파이터 | 턴 4 통과 |

대표 캡처는 `captures/analysis/5e20_s21_enemy_status_sheet.png`,
`captures/analysis/4234_s01_enemy_commander_soldiers_status.png`,
`captures/run/4234_s01_turn6_enemy_target.png`,
`captures/run/4234_s01_turn6_enemy_soldier.png`이다. 저장 상태의 하단 행도
이름에 `0x5D8..`, 클래스에 `0x5E0..`를 사용함을 확인했다. 완료 직전의
불완전 S21 GST가 구형 ROM에서도 표시를 끄는 검은 화면은 합격/실패 판정에
사용하지 않는다.

추가 `4234` 검증은 교차 체크섬 GST를 사용하지 않고 실제 SRAM과 시나리오
선택 비기로 처음부터 진입했다. 설명, 준비, 출격 대사, 적/NPC 행동을 그대로
통과해 `TURN 4`에서 다시 적장과 병사를 선택했다. 대표 캡처는
`captures/run/4234_s01_production_enemy_commander_fresh2.png`,
`captures/run/4234_s01_production_turn3_enemy_candidate3.png`,
`captures/run/4234_s01_production_turn3_enemy_soldier_left.png`,
`captures/run/4234_s01_production_turn4_enemy_search4.png`,
`captures/run/4234_s01_production_turn4_enemy_neighbor_right.png`이다.
휴대폰의 이전 RetroArch 화면에서 `가드맨`의 `가`, `프리스트`와
`나이트마스터`의 동일한 `스` 칸만 그래픽 조각으로 바뀐 것은 이 직접 렌더러
수정 전 증상과 일치한다. 현재 롬에서 재발하면 문자열이나 클래스 ID를 다시
바꾸기 전에 휴대폰에 복사된 롬 체크섬과 RetroArch의 실제 로드 파일을 먼저
확인한다.

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
계속 통과시켜야 한다. 전투 연출의 중앙 하단 `地形`은 이후 production
`45D8`에서 `지형`으로 수정·실기 검증되었으며 더 이상 미완료 항목이 아니다.

## Scenario 22 Turn-4 And Completion Matrix

Production `4234` 기반 stock-layout probe `123D`는 실제 턴 4까지 진행한 뒤
다음 적장 상태를 직접 선택했다.

| Role | Name | Class | Result |
| --- | --- | --- | --- |
| 적장 | 제국지휘관 | 세인트 | 통과 |
| 적장 | 제국지휘관 | 아크메이지 | 통과 |
| 적장 | 에그베르트 | 자베라 | 통과 |
| 적장 | 보젤 | 다크마스터 | 통과 |
| 적장 | 라나 | 다크프린세스 | 통과 |
| 적장 | 리치 | 리치 | 통과 |
| 적장 | 아이언골렘 | 아이언골렘 | 통과 |

`다크마스터`, `다크프린세스`에 이전 모바일 재현 대상 글자 `스`, `터`가
포함되지만 턴 4에도 손상되지 않았다. 대표 캡처는
`captures/run/123d_s22_turn4_empire_commander_hover.png`,
`captures/run/123d_s22_turn4_empire_archmage1_hover.png`,
`captures/run/123d_s22_turn4_bozel_hover.png`,
`captures/run/123d_s22_turn4_lana_hover.png`,
`captures/run/123d_s22_turn4_egbert_hover.png`,
`captures/run/123d_s22_turn4_lich_hover.png`,
`captures/run/123d_s22_turn4_iron_golem_hover.png`이다.

Completion-layout probe `A263`에서는 라나·보젤·제국지휘관·에그베르트·
아이언골렘·베른하르트의 상태 행과 전투창도 통과했다. 특히 숨은
`베른하르트/엠퍼러`는 보젤 이벤트 전까지 `(255,255)`를 유지했고, 등장 뒤
`captures/run/a263_s22_turn2_hein_magic_bernhardt_target.png`에서 온전하게
표시됐다. `제국군지휘관`은 원본 대사 전용 화자 문자열이고 지도 레코드의
`제국지휘관`과 별도이므로 손상이나 표기 회귀로 판정하지 않는다.

`123D`와 `A263`은 적 용병을 제거하는 완주용 진단 ROM이다. 따라서 이 두
세션은 적 병사 검증 근거가 아니다. 적 병사는 용병 보존 production 구성에서
별도로 확인해야 한다.

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

## Scenario 21 Turn 4 and Completion Check

Production `4234` 기반 completion probe `5E20`을 turn 4까지 진행한 뒤 지도
이동, 초상화 대사, 파이어볼, 일반 전투를 연속 통과시켰다. 다음 조합은 하단
상태창이나 지휘관 메뉴에서 모두 온전했다.

| Side | Name | Class | Context |
| --- | --- | --- | --- |
| 적군 지휘관 | 서큐버스 | 서큐버스 | turn 4 하단 상태창 |
| 적군 병사 | 서큐버스 | 서큐버스 | turn 4 인접 병사 하단 상태창 |
| 아군 | 레스터 | 매직나이트 | 명령·마법 목록 |
| 아군 | 제시카 | 비숍 | 하단 상태창 |
| 아군 | 쉐리 | 로드 | 북쪽 크라켄 전투 |
| 아군 | 아론 | 로드 | 중앙 크라켄 전투 |
| 아군 | 키스 | 호크나이트 | 남쪽 크라켄 전투 |
| 적군 | 크라켄 | 크라켄 | 세 reveal 위치와 전투창 |

특히 이전 지연 손상에서 반복된 `키`, `스`, `크`, `트`를 같은 세션의 turn 4
및 세 번의 전투 뒤에도 확인했다. 빈 지형은 `SCENARIO 21 / TURN 4`로
표시되어 과거 `SCENAR록O` 손상도 재발하지 않았다. 대표 증거는
`captures/run/5e20_s21_scan_up.png`,
`captures/run/5e20_s21_scan_left.png`,
`captures/run/5e20_s21_kraken_south_keith_menu.png`과
`captures/run/5e20_s21_kraken_north_battle_02.png`이다.

## Scenario 23 Battle And Completion Matrix

Production `AD99` 기반 all-enemy probe `F04D`와 completion-target probe
`F0FC`에서 다음 조합을 확인했다.

| Side | Name | Class | Context |
| --- | --- | --- | --- |
| 아군 | 엘윈 | 로드 | 드래곤로드 전투 |
| 아군 | 헤인 | 샤먼 | 팔라딘 전투 |
| 적군 | 제국지휘관 | 드래곤로드 | 상세창·전투 |
| 적군 | 제국지휘관 | 팔라딘 | 하단 상태창·전투 |
| 적군 | 레아드 | 실버나이트 | 턴 이벤트 하단 상태창 |
| 적군 | 제국지휘관 | 위저드 | 턴 2 하단 상태창 |

실기와 읽기 전용 GST 대조로 플레이어 런타임 그룹은 `0..8`, 고정 적군은
`9..19`임을 확인했다. `F0FC`는 원본 record 0 드래곤로드만 보이게 한
완료 전용 ROM이며 다른 적의 이름·클래스 검증 근거로 사용하지 않는다.
`F04D`와 `F0FC` 모두 적 용병을 제거하므로 적 병사 이름 검증 근거도 아니다.
대표 증거는 `captures/run/84e8b_s23_dragonlord_detail_hp1.png`,
`captures/run/f3be_s23_hein_paladin_battle_start.png`,
`captures/run/f0fc_s23_battle.png`이다.

적 용병을 제거하지 않은 production `AD99` 정식 배치도 별도로 출격시켰다.
이 런은 이전 완료 경로가 만든 Scenario 23 수동 저장을 사용했으며 아군 저장
AT/DF만 진단값이다. 적군 record, 좌표, 클래스, 용병 구성은 production
그대로다.

| Side | Name | Class | Context |
| --- | --- | --- | --- |
| 적장 | 제국지휘관 | 드래곤로드·팔라딘·세인트·위저드 | TURN 1 하단 상태창 |
| 적장 | 레아드 | 실버나이트 | TURN 1 하단 상태창 |
| 적 병사 | 엘리멘탈 | 엘리멘탈 | 드래곤로드 인접 병사 |
| 적 병사 | 팔랑크스 | 팔랑크스 | 팔라딘·위저드 인접 병사 |
| 적 병사 | 헤비호스맨 | 헤비호스맨 | 팔라딘 인접 병사 |
| 적 병사 | 로얄호스 | 로얄호스 | 레아드 인접 병사 |
| 적 병사 | 다크엘프 | 다크엘프 | 세인트 인접 병사 |
| 적 병사 | 버서커 | 버서커 | 세인트 인접 병사 |
| 적 병사 | 발리스타 | 발리스타 | 위저드 인접 병사, TURN 1·2 |

전체 적군 행동이 끝나 `TURN 2`에 도달한 뒤에도
`제국지휘관/위저드`와 `발리스타`가 정상 표시됐다. 같은 발리스타를
0·1·2·3·5초에 캡처한 하단 이름·클래스 영역도 픽셀 단위로 동일했다.
대표 증거는 `captures/run/ad99_s23_stock_enemy0_dragonlord.png`,
`captures/run/ad99_s23_stock_enemy1_merc_bottom_left.png`,
`captures/run/ad99_s23_stock_laird_merc.png`,
`captures/run/ad99_s23_stock_saint_merc_upper_right.png`,
`captures/run/ad99_s23_stock_wizard_merc_right.png`,
`captures/run/ad99_s23_turn2_cluster_unit.png`, 그리고
`captures/run/ad99_s23_turn2_cluster_commander.png`이다.

## Scenario 24 Stock Enemy And Completion Matrix

Production `AD99` 정식 배치를 이전 장의 실제 저장 데이터로 출격시켜
적군과 용병을 제거하지 않은 상태로 확인했다.

| Side | Name | Class | Context |
| --- | --- | --- | --- |
| 적장 | 데몬로드 | 데몬로드 | 하단 상태창·상세창 |
| 적장 | 리치 | 리치 | 하단 상태창·상세창 |
| 적장 | 케르베로스 | 케르베로스 | 하단 상태창·상세창 |
| 적장 | 뱀파이어로드 | 뱀파이어로드 | 하단 상태창·상세창·전투 |
| 적 병사 | 아크데몬 | 아크데몬 | 데몬로드·뱀파이어로드 인접 병사 |
| 적 병사 | 엘리멘탈 | 엘리멘탈 | 데몬로드 인접 병사 |
| 적 병사 | 발리스타 | 발리스타 | 리치 인접 병사 |
| 적 병사 | 골렘 | 골렘 | 리치 인접 병사 |
| 적 병사 | 헬하운드 | 헬하운드 | 케르베로스 인접 병사 |
| 적 병사 | 뱀파이어배트 | 뱀파이어배트 | 뱀파이어로드 인접 병사 |

전체 적군 행동과 두 장의 뱀파이어로드 대사를 통과해 `TURN 2`의 정상
엘윈 명령창으로 돌아왔다. 같은 데몬로드의 이름·클래스 영역을
0·1·2·3·5초에 캡처한 픽셀 해시는 모두 동일했다. 베른하르트는 원본
이벤트대로 `TURN 2`까지 숨은 상태이므로 이 정식 배치 실행은
`베른하르트/엠퍼러`의 화면 증거로 사용하지 않는다.

완료 전용 `08D4`는 원본 record 10 `뱀파이어로드/뱀파이어로드`만
공격 대상으로 남기고 엘윈을 바로 아래에 배치한다. 전투창의
`엘윈/로드`, `뱀파이어로드`, `-AT-`, `-DF-`, `-지형-`을 확인했고,
완료 대사·전과보고·`시나리오 25` 저장·다음 시나리오 진입까지
정상 통과했다. 대표 증거는
`captures/run/08d4_s24_vampire_attack.png`,
`captures/run/08d4_s24_after_vampire_event_44.png`,
`captures/run/ad99_s24_stock_demonlord_status.png`,
`captures/run/ad99_s24_stock_vampire_status.png`,
`captures/run/ad99_s24_stock_elemental.png`,
`captures/run/ad99_s24_stock_golem.png`,
`captures/run/ad99_s24_stock_vampirebat.png`, 그리고
`captures/run/ad99_s24_stock_turn2_command.png`이다.

## Scenario 25 Stock Enemy And Completion Matrix

Production `AD99` 정식 배치를 시나리오 24 완료 과정에서 만든 실제
시나리오 25 저장 데이터로 출격시켰다. 적군과 용병을 제거하지 않은 상태에서
다음 고유 조합을 하단 상태창으로 확인했다.

| Side | Name | Class | Context |
| --- | --- | --- | --- |
| 저장 슬롯 아군 | 제시카 | 비숍 | 적군보기·전장 |
| 적장 | 레온 | 로얄가드 | TURN 1 하단 상태창 |
| 적장 | 레아드 | 실버나이트 | TURN 1 하단 상태창 |
| 적장 | 에그베르트 | 자베라 | TURN 1 하단 상태창 |
| 적장 | 제국지휘관 | 나이트마스터·위저드·팔라딘 | TURN 1 하단 상태창 |
| 적 병사 | 로얄호스 | 로얄가드·실버나이트·나이트마스터 인접 병사 |
| 적 병사 | 아머솔저 | 위저드 인접 병사 |
| 적 병사 | 헤비호스맨 | 팔라딘 인접 병사 |
| 적 병사 | 그리폰 | 에그베르트 인접 병사 |

전체 적군 행동을 통과해 `SCENARIO 25 / TURN 2`를 직접 확인했다. TURN 2
에서도 `제국지휘관/나이트마스터`, `로얄호스`,
`제국지휘관/위저드`, `아머솔저`, `헤비호스맨`이 정상 표시됐다.
같은 나이트마스터 하단 이름·클래스 영역을 TURN 1과 TURN 2에서 각각
0·1·2·3·5초에 캡처했으며, 각 턴의 다섯 픽셀 해시가 모두 동일했다.
따라서 이번 생산판 실행에서는 과거 모바일 캡처의 `스`·`터` 지연 손상이
재현되지 않았다. 원본 record 11 드래곤로드는 TURN 2까지 HP 0,
좌표 `(255,255)`인 이벤트 대기 상태라 아직 화면 검증 근거로 사용하지 않는다.

완료 전용 `7607`은 아군 제시카를 보존하고 원본 record 1 레온만 공격
대상으로 남긴다. 정상 엘윈 공격은 `엘윈/로드`, `레온/로얄가드` 전투를
거쳐 전체 후속 대사, 아이템 초과·버리기, 레벨업·클래스 체인지,
`전과보고`, 실제 `시나리오 26` 저장, 다음 시나리오 경로와 설명까지
리셋 없이 통과했다.

대표 증거는
`captures/run/ad99_s25_laird_commander_hover.png`,
`captures/run/ad99_s25_leon_commander_hover.png`,
`captures/run/ad99_s25_egbert_commander_hover.png`,
`captures/run/ad99_s25_nightmaster_commander_hover.png`,
`captures/run/ad99_s25_wizard_commander_hover.png`,
`captures/run/ad99_s25_enemy_paladin_commander_hover.png`,
`captures/run/ad99_s25_laird_royal_horse_hover.png`,
`captures/run/ad99_s25_egbert_merc_hover.png`,
`captures/run/ad99_s25_wizard_merc_hover.png`,
`captures/run/ad99_s25_enemy_paladin_merc_hover.png`,
`captures/run/ad99_s25_turn_counter_after_phase.png`,
`captures/run/ad99_s25_turn2_nightmaster_hover_precise.png`,
`captures/run/ad99_s25_turn2_armored_soldier_hover.png`, 그리고
`captures/run/7607_s25_after_leon_detector_stop.png`이다.
