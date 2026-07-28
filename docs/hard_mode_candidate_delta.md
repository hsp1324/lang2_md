# 표준 하드 최신 후보 전이 검증

## 대상

- 이전 배포 후보: `roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md`
  - MD 체크섬 `1011`
  - SHA-256 `c46249fdc50db4010115e5509c173de007761f5a42562345eca747506b43227b`
- 최신 플레이 후보: `roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md`
  - MD 체크섬 `8674`
  - SHA-256 `142580f8ff9021f011ae5da186c7685f9ed7f7bd01d1ebdb9959148f9691cd27`

최신 파일은 사용자가 릴리스라고 명시하기 전의 빌드 후보다. 따라서
`roms/releases`의 `1.0.0/1.0.0` 파일은 교체하지 않는다.

## 결과

두 ROM 사이의 변경은 365바이트다. 모두 다음 소유 범위 안에 있다.

- MD 헤더 체크섬
- 전과보고 `적군` 글자 레코드와 복원 루틴
- 선택 용병 이름/클래스 동적 글자 슬롯
- 커스텀 맵 스프라이트의 비활성 회색 상태 변환 훅·루틴·표
- 로렌의 두 맵 스프라이트 프레임

시나리오 고정 배치, 하드 보정 표와 로더, 이벤트, AI, SRAM 설명자에는
변경 바이트가 없다. 따라서 이전 후보의 31/31 런타임 적재 및 첫 턴
진행 증거는 밸런스 데이터에 한해 계승한다. 글자와 스프라이트는 최신
후보에서 별도의 실기 캡처로 확인한다.

기계 판독 원장은 `localization/hard_mode_candidate_delta.json`이며,
다음 명령은 소유 범위 밖 바이트가 하나라도 바뀌면 실패한다.

```bash
python3 tools/verify_hard_candidate_delta.py --check
python3 -m unittest tests.test_hard_candidate_delta
```

## 최신 후보 실기 표본

시나리오 4는 `8674` 후보에서 이전 후보의 실행 상태를 직접 재사용하지
않고, 같은 최신 ROM으로 만든 시나리오 2 저장 슬롯을 복구한 뒤 시나리오
선택 비기로 새로 진입했다. 자동 배치·출격 뒤 다음 항목을 확인했다.

- 아군 런타임 그룹: 3개
- 하드 대상 고정 레코드: 6개
- 실제 적 런타임 그룹: 8~13
- 클래스·이름·LV·지휘관 AT/DF·병사 A+/D+·용병: 6/6 일치
- 런타임 예외: 0개

별도 원장은 `localization/hard_mode_current_candidate_runtime.json`이다.
로컬 증거는 다음 파일에 보존한다.

- 화면: `captures/run/hard_8674_s04_entry.png`
- 진입 GST: `captures/analysis/hard_8674_s04_entry_turn1_entry.gst`
- 진입 GST SHA-256:
  `ade2fee468a2318556faf02e80caf38ce6e001695eea896ec8be0d62ff59bc6d`

시나리오 5는 위 시나리오 4의 최신 후보 GST에서 저장 슬롯을 복구해
연속 진입했다.

- 아군 런타임 그룹: 5개
- 하드 대상 고정 레코드: 9개
- 실제 적 런타임 그룹: 5~13
- 클래스·이름·LV·지휘관 AT/DF·병사 A+/D+·용병: 9/9 일치
- 런타임 예외: 0개
- 화면: `captures/run/hard_8674_s05_entry.png`
- 진입 GST: `captures/analysis/hard_8674_s05_entry_turn1_entry.gst`
- 진입 GST SHA-256:
  `7140fb55513bcefddb142c262ddd66e374b706252dfa05860965e1c54b1e54f9`
- 추가 화면 `captures/run/hard_8674_s05_turn1_map.png`에서
  `모건 / 소서러` 하단 상태 글자와 첫 대사 화면이 정상임을 확인했다.
