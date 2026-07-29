# 표준 하드 플레이 후보

## 현재 파일

- ROM: `roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md`
- 릴리스 ID: `ko-hard-t1.0.0-b1.0.0`
- MD 체크섬: `5BE8`
- SHA-256:
  `227e7a25818860ebd674d62bda3ca748901aaa45f0919c3eb1ae4340157742bd`
- 크기: 4 MiB
- 세이브 형식: `lang2-ko-sram-v1`
- SRAM 설명자: `5241F8200040000100403FFF`

이 파일은 최종 릴리스가 아니라 사용자 플레이 검증용 후보이다.
사용자가 명시적으로 릴리스했다고 말할 때까지 타이틀과 파일명의
번역/밸런스 버전은 `1.0.0/1.0.0`으로 유지한다.

현재 `roms/releases` 파일과 검증된 `roms/builds` 파일은 바이트 단위로
같다. 이전 체크섬 `1011` 후보는
`roms/releases/archive/Langrisser II (Korean Hard T1.0.0 B1.0.0 checksum-1011).md`
에 보존한다. 두 후보의 578바이트 전이와 현재 후보 실기 표본은
`docs/hard_mode_candidate_delta.md` 및
`localization/hard_mode_candidate_delta.json`에 기록한다.

## 적용 범위

- 적 고정 배치 레코드 300개의 지휘관 AT/DF 강화
- 같은 300개 레코드의 적 전용 병사 A+/D+ 강화
- 용병 304칸을 구간별 보수적 상위 병종으로 교체
- 공용 클래스 레코드 157개는 변경하지 않음
- 이벤트 진영 전환, 아군 지원, 연출용 강적은 자동 강화에서 제외
- 소환물 병사 교체는 런타임 안전성이 충분히 확인되지 않아 보류
- 하드판 타이틀만 영문 로고를 금색 계열로 바꾸고 `하드 모드`,
  `새 게임(하드)`를 표시
- 메이지·아크메이지·로드·하이로드·프리스트·하이프리스트의 승인된
  지휘관별 새 맵 스프라이트 40개 적용

정확한 장별 수치와 주소는 `docs/hard_mode_changes.md` 및
`localization/hard_mode_plan.json`에 기록한다.

## 검증 상태

현재 `5BE8` 후보는 ROM 크기, 소유 주소 범위, 300개 레코드의 적용값,
40개 클래스 스프라이트의 매핑·두 프레임 데이터, MD 체크섬, SRAM
설명자 및 일반판 불변 검사를 자동 테스트로 통과했다. 현재 ROM은
준비·상태창 동적 글자와 커스텀 클래스 비활성 맵 스프라이트 수정도
포함한다. 완성 ROM에서
40개 스프라이트를 다시 추출한 결과는
`localization/ai_class_map_sprite_rom.json`과
`docs/assets/ai_class_map_sprite_rom_contact_sheet.png`에 기록했다.
직전 `0718` 후보를 커밋 `1360b69`에서 재현해 비교한 결과 변경
10,266바이트는 모두 40개 매핑·80개 프레임·헤더 체크섬에 속하며,
밸런스·이벤트·AI 영역 변경은 0이다:
`localization/ai_class_release_delta.json`

- 현재 `5BE8` 후보는 31/31개 시나리오에서 자동 배치·출격 후 하드
  대상의 실제 RAM 적재값을 확인했다:
  `localization/hard_mode_current_candidate_runtime.json`
- 현재 `5BE8` 후보는 31/31개 시나리오에서 대사를 넘기고 첫 턴의
  정상 종점까지 진행했다:
  `localization/hard_mode_current_candidate_first_turn.json`,
  `docs/hard_mode_current_candidate_first_turn.md`
- 현재 후보는 전체 장 공략이나 용병 고용·이동 없이 일회용 진단
  ROM으로 여섯 변경 클래스에 직접 진입했다. 각 클래스가 변경 후
  맵으로 복귀하고, 3초 안정 대기와 상태창 표시를 통과했으며 GST의
  클래스·지휘관 ID도 일치했다:
  `localization/ai_class_runtime_spot_check.json`,
  `docs/assets/ai_class_runtime_spot_check.png`
- 빌드·스프라이트·체크섬·SRAM·일반판 불변성 관련 정적 검사 62개를
  통과했다.

이 검증은 모든 장의 로딩, 첫 턴 이벤트, 진영 진행과 기본 진행
가능성을 확인한 것이다. 실제 난이도, 전투 감각, 장 전체 클리어
가능성, 중후반 증원·분기·엔딩까지의 완주는 사용자가 플레이하며
검증한다. 따라서 현재 파일은 계속 플레이 후보이며 최종 릴리스가
아니다.

실제 플레이 결과는 `localization/hard_mode_playtest.json`과
`docs/hard_mode_playtest.md`에 후보 SHA-256별로 누적한다.
`python3 tools/hard_mode_playtest.py --check --require-complete`가
31/31을 통과하기 전에는 최종 릴리스로 판정하지 않는다.

## 저장을 유지하며 후보 갱신

1. 게임 안에서 저장한다.
2. 에뮬레이터를 완전히 종료한다.
3. 현재 ROM과 `.srm`을 백업한다.
4. 수정 ROM을 현재 ROM과 정확히 같은 경로와 파일명에 적용한다.
5. `.srm` 또는 `.sav`는 바꾸지 않는다.

에뮬레이터 상태 저장은 실행 중인 코드 주소를 포함할 수 있으므로
호환을 보장하지 않는다. 다음 후보가 생기면 현재 후보 해시를 원본으로
하는 BPS 패키지를 `tools/build_rom_update_package.py`로 만든다.
