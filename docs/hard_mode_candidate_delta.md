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

시나리오 6은 시나리오 5의 최신 후보 GST에서 연속 진입했다. 표준 하드
프로필에서 용병 교체가 처음 적용되는 장이므로, 지휘관과 병사 보정뿐
아니라 계획된 용병 8칸의 교체값도 함께 대조했다.

- 아군 런타임 그룹: 5개
- 하드 대상 고정 레코드: 9개
- 실제 적 런타임 그룹: 9~17
- 클래스·이름·LV·지휘관 AT/DF·병사 A+/D+·용병: 9/9 일치
- 계획된 용병 교체: 8/8칸 일치
- 런타임 예외: 0개
- 화면: `captures/run/hard_8674_s06_entry.png`
- 진입 GST: `captures/analysis/hard_8674_s06_entry_turn1_entry.gst`
- 진입 GST SHA-256:
  `2ab66de2b9b9787e0cf4388736c6eb69fbb5dc291bc935dd24acf1396010fe2b`

시나리오 7과 8도 직전 시나리오의 최신 후보 저장 슬롯을 차례로 복구해
연속 진입했다. 두 장 모두 자동 배치·출격 뒤 클래스·이름·LV·지휘관
AT/DF·병사 A+/D+·용병을 고정 배치 원본과 대조했으며 예외가 없었다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 7 | 6 | 8/8 | 10~17 | `6c18eb4612cbb8e6cf5a22ff822f563e20d6c94b596bc237b58d4967f3914953` |
| 8 | 7 | 11/11 | 7~17 | `bfbb3a73e8e38fd39f0907b5715b14a57bfad4f8c4664d5c4251fabf713f4f84` |

화면은 각각 `captures/run/hard_8674_s07_entry.png`와
`captures/run/hard_8674_s08_entry.png`, 진입 상태는
`captures/analysis/hard_8674_s07_entry_turn1_entry.gst`와
`captures/analysis/hard_8674_s08_entry_turn1_entry.gst`에 보존한다.

시나리오 9와 10도 같은 최신 후보 저장 슬롯 계보로 연속 진입했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 9 | 7 | 10/10 | 10~19 | `6d5f549efa7e2db62b4fba1c3dacb1e51d2fb9d79ecd8b97bddcdaf7ea1162e8` |
| 10 | 5 | 13개 중 엄격 12/12 | 5~17 | `e9ef42fa1a0a8abea32869eb46abdc9f0108cc76b32150c25b03c0ef90b35251` |

시나리오 10 고정 레코드 1의 레스터는 원작이 플레이 가능한 로스터
성장 데이터로 능력치를 다시 쓰는 이미 문서화된 예외다. 클래스·이름·
용병은 엄격히 일치하고, AT/DF와 병사 보정만 원작 성장값을 유지한다.
이 정책은 `localization/hard_mode_runtime_exceptions.json`에 고정되어
있다. 화면은 `captures/run/hard_8674_s09_entry.png`와
`captures/run/hard_8674_s10_entry.png`에 보존한다.

시나리오 11과 12도 같은 방식으로 연속 진입했으며 런타임 예외 없이
모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 11 | 6 | 10/10 | 7~16 | `fb1a1e2aba3924dd54022ea9f524165f91fc8aeafc28003eac99615ec3408d59` |
| 12 | 7 | 11/11 | 7~17 | `f99778e7c8f7222ea36935dd1d6359d3aa76abedee7d7c00e3e088eabab6a179` |

화면은 `captures/run/hard_8674_s11_entry.png`와
`captures/run/hard_8674_s12_entry.png`에 보존한다.

시나리오 13과 14도 같은 방식으로 연속 진입했으며 런타임 예외 없이
모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 13 | 7 | 13/13 | 7~19 | `455333e1bf26129811f4788022c1585d64642eebaaa65af5b8bf2488a97ec358` |
| 14 | 7 | 11/11 | 7~17 | `a39b7c75faf91aaac0cfbb5c86f346771e8a0773bdb9bfdcc1091e66410b3cd3` |

화면은 `captures/run/hard_8674_s13_entry.png`와
`captures/run/hard_8674_s14_entry.png`에 보존한다.
