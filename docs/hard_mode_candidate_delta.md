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

시나리오 15와 16도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 15 | 7 | 11/11 | 8~18 | `473bc3241798ded1b58790a3fbf6ad99e634e74cf720d743a49f3105b96b8414` |
| 16 | 8 | 10/10 | 8~17 | `69303b039e3bccee6fb7c2215d085ca1bcd68559d4069497632135f0947a6e0e` |

시나리오 16은 이전 심층 검증도 보유하지만, 이번 상태는 시나리오 15의
체크섬-`8674` 저장 슬롯에서 직접 이어진 최신 후보 증거다. 화면은
`captures/run/hard_8674_s15_entry.png`와
`captures/run/hard_8674_s16_entry.png`에 보존한다.

시나리오 17과 18도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 17 | 8 | 11/11 | 8~18 | `37d7313a7dcd64dfc5e774c16dae378f6b8915353cd474cf0c2df04c843c5ef1` |
| 18 | 8 | 9/9 | 10~18 | `ddf9bbfc783db8e8b70fec66071b9fe4a2ac9869a71f449d1f3ede4a383324da` |

시나리오 18의 첫 실행 래퍼는 준비 화면 전에 종료 코드 143을 반환했지만
BlastEm 프로세스와 동일 저장 슬롯은 유지됐다. 같은 런타임을 재개해
준비 화면, 자동 배치, 출격을 통과했으며 ROM 재시작이나 타 ROM GST
이식은 없었다. 화면은 `captures/run/hard_8674_s17_entry.png`와
`captures/run/hard_8674_s18_entry.png`에 보존한다.

시나리오 19와 20도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 19 | 8 | 10/10 | 8~17 | `23a6b67050d9eae1eaa0e809fce8e606bbc6048ecb797bd3ff49f2975a9e0856` |
| 20 | 8 | 10/10 | 8~17 | `0f3bd3e1baa162b53ae33aad155e04bebb50f43f829508be590cc50455e0dae5` |

화면은 `captures/run/hard_8674_s19_entry.png`와
`captures/run/hard_8674_s20_entry.png`에 보존한다.

시나리오 21과 22도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 21 | 8 | 11/11 | 8~18 | `c2bcca9b36e33f9872502a440a7ba98f831dc4805c990b5327661dc087817dd7` |
| 22 | 8 | 11/11 | 9~19 | `835382bbfdfa71c86cd5c971f654b0c72881c41aa295178de93582013f83cd6f` |

화면은 `captures/run/hard_8674_s21_entry.png`와
`captures/run/hard_8674_s22_entry.png`에 보존한다.

시나리오 23과 24도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 23 | 9 | 11/11 | 9~19 | `3878d15305ba7ed95de2e9cbb63aca788ca58b8c4eb8c7ae3c8cd4877e08c666` |
| 24 | 9 | 10/10 | 10~19 | `864cedcda80b28b70ec73b8edeae8fbaa1b079ad0676a25fc6dd485dfc7d4ff2` |

시나리오 23의 첫 실행 래퍼도 준비 화면 전에 종료 코드 143을 반환했지만
동일 BlastEm 런타임을 재개해 검증했다. 화면은
`captures/run/hard_8674_s23_entry.png`와
`captures/run/hard_8674_s24_entry.png`에 보존한다.

시나리오 25와 26도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 25 | 9 | 11/11 | 10~20 | `b8dcaccfd7e9aca2024b977bcdfe570d14143ae3dd0211e0eb8944f4cb603457` |
| 26 | 10 | 10/10 | 10~19 | `363566df1964388dcc4ffa984328862e8c20ba352a0e96b8176f8f0e9925f5da` |

시나리오 25는 이전 심층 검증도 보유하지만, 이번 상태는 시나리오 24의
체크섬-`8674` 저장 슬롯에서 직접 이어진 최신 후보 증거다. 화면은
`captures/run/hard_8674_s25_entry.png`와
`captures/run/hard_8674_s26_entry.png`에 보존한다.

시나리오 27과 28도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 27 | 10 | 10/10 | 10~19 | `e35cd92cd482e98a5af0adbdf7f1be8d318f9cef087cd4d65fe6bfe56ab372cf` |
| 28 | 7 | 9/9 | 7~15 | `3ef850385b8d0a7e0191e9fb93e3501540a05f6debe05a4fb1b7009da5789b4b` |

시나리오 27은 이전 심층 검증도 보유하지만, 이번 상태는 시나리오 26의
체크섬-`8674` 저장 슬롯에서 직접 이어진 최신 후보 증거다. 화면은
`captures/run/hard_8674_s27_entry.png`와
`captures/run/hard_8674_s28_entry.png`에 보존한다.

시나리오 29와 30도 직전 최신 후보 상태에서 연속 진입했으며 런타임
예외 없이 모든 하드 대상 레코드가 일치했다.

| 시나리오 | 아군 그룹 | 하드 대상 | 실제 적 그룹 | GST SHA-256 |
| ---: | ---: | ---: | --- | --- |
| 29 | 8 | 9/9 | 8~16 | `91bc66ee344297b3a7572ac133f26d19f52587d0d234b1b0babe99ac0a883019` |
| 30 | 9 | 11/11 | 9~19 | `901555e61b57017effdbe5d0aa1c3875b8c518c960e79cb66083298757225a12` |

시나리오 29 하단의 `SCENARIO ?2`는 원작 비기 스테이지의 맵 상태
표기이며 깨진 한글 타일이 아니다. 화면은
`captures/run/hard_8674_s29_entry.png`와
`captures/run/hard_8674_s30_entry.png`에 보존한다.
