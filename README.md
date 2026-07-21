# Langrisser II Korean ROM Hack WIP

랑그릿사 II 메가드라이브 한국어화를 진행 중인 작업 폴더입니다.

프로젝트 개발자: **hsp1324**

게임 내 첫 타이틀과 스태프롤 마지막 화면에는 한국어화 개발자 아이디를 게임 글꼴에 맞춘 대문자 `HSP1324`로 표기합니다.

다른 PC나 다른 Codex 세션에서 이어서 작업할 때는 먼저 [HANDOFF.md](HANDOFF.md)를 읽습니다. 필요한 로컬 ROM/에뮬레이터 파일, 빌드/실행 명령, 테스트 매크로, 해결/미해결 이슈를 그 문서에 정리했습니다.

초기 작업은 영어판 고정 폰트를 기준으로 진행했지만, 슬롯 충돌이 많아 일본판의 16x16 glyph 로딩 시스템을 분석하는 방향으로 전환했습니다. 일본판은 각 텍스트 레코드가 사용할 glyph 목록을 먼저 VRAM에 올리고, 본문은 그 목록의 로컬 인덱스를 참조합니다.

## 필요한 파일

이 저장소는 ROM 바이너리를 추적하지 않습니다. 현재 일본판 기반 빌드에는 아래 일본판 ROM만 필요합니다. 영어판은 legacy 스크립트를 다시 실행할 때만 선택적으로 둡니다.

- `roms/original/Langrisser II (Japan).md`
- `roms/original/Langrisser II (English).md` (legacy 전용, 선택)

## 주요 파일

- `scripts/build_korean_jp_probe.py`: 현재 우선 진행 중인 일본판 텍스트/glyph 시스템 기반 빌더입니다.
- `scripts/legacy/build_korean_complete_wip.py`: 영어판 고정 폰트 기반 초기 실험 빌더입니다.
- `tools/jp_text_font_analyzer.py`: 일본판 16비트 텍스트 스트림, glyph 목록, `0x40000` JP font 포맷을 오프라인 분석/렌더링하는 도구입니다.
- `tools/jp_byte_table_analyzer.py`: 클래스/용병/몬스터명 8비트 문자열 테이블 분석 도구입니다.
- `tools/render_jp_byte_strings.py`: 준비창/상점처럼 1바이트 문자열을 쓰는 작은 UI 텍스트를 오프라인 렌더링하는 도구입니다.
- `tools/find_decompressed_tile.py`: `0x9DFE` 그래픽 압축 블록에서 특정 VRAM 타일 원본을 찾는 분석 도구입니다.
- `tools/analyze_name_entry_vram.py`: GST 저장 상태에서 VRAM/plane CSV와 렌더 이미지를 뽑아 이름 입력 화면과 메뉴 타일 배치를 추적합니다.
- `docs/name_entry_analysis.md`: 일본판 이름 입력 레이아웃, 현재 안전한 57자 한글 선택표, 저장 바이트, 확정 시 인덱스→글리프 변환 훅과 실기 검증 기록입니다.
- `docs/sram_relocation.md`: 4 MiB ROM 확장으로 겹친 SRAM을 `0x400001`로 옮긴 주소 패치와 저장/불러오기 실기 검증 기록입니다.
- `docs/class_change_analysis.md`: 클래스 체인지 15슬롯 공유 글리프와 두 레이아웃의 인덱스 소유권 및 한국어 슬롯 배치를 기록합니다.
- `tools/build_class_change_probe_rom.py`: 지정한 지휘관·현재 클래스·활성 런타임 슬롯의 원본 후보 ID로 클래스 체인지 화면을 직접 열거나, `--end-turn-only`로 정상 턴 종료 레벨업 적용 경로를 재현하는 비배포 진단 ROM을 만듭니다. Start 직접 진입은 화면/이동 검사용이며 실제 적용 증거로 사용하지 않습니다.
- `tools/capture_class_change_transition.py`: 지정한 원본 클래스 전이의 진단 ROM 빌드, 격리 BlastEm 새 부팅, 명령 화면 감지, Start 진단 진입, 모든 후보 행 캡처와 종료를 한 번에 수행합니다.
- `tools/capture_class_change_chain.py`: 한 지휘관 체인에서 아직 화면 검증되지 않은 고유 전이만 골라 위 자동 캡처를 순차 실행하고, 완전한 기존 캡처 세트는 건너뛰어 중단 후 재개합니다.
- `tools/class_change_inventory.py`: 일본판의 플레이어 지휘관 10명 클래스 체인 100개 전이를 주소·원문·한글 표기·화면/적용 실기 상태와 함께 JSON/Markdown으로 생성합니다.
- `tools/match_vram_glyph_crops.py`: 실행 캡처의 특정 글자 crop을 VRAM 타일 후보와 비교해 어떤 tile ID가 화면에 보이는지 좁히는 도구입니다.
- `tools/capture_blastem_window.py`: 실행 중인 BlastEm 화면을 캡처합니다. Windows 배율을 반영한 DWM 데스크톱 캡처를 우선하고 `xwd`, Xlib 순으로 fallback하며 자동 경로는 포커스를 바꾸지 않습니다. `--print-window`는 가려진 OpenGL 창에서 이전 프레임 잔상이 섞일 수 있는 진단 전용 옵션입니다. `--allow-focus-steal`은 사용자가 다른 작업을 하지 않을 때 한 번만 명시적으로 허용해야 합니다.
- `tools/send_blastem_keys.py`: BlastEm 창에 테스트용 키 입력을 보냅니다.
- `tools/scenario_data.py`: MD판 31개 시나리오의 고정 배치 레코드를 읽고 제한된 필드를 패치하거나 편집기용 JSON으로 내보냅니다. 좌표는 초기 고정 배치일 뿐 이벤트가 실시간으로 덮어쓸 수 있어 읽기 전용입니다.
- `tools/jp_event_inventory.py`: `0x18011A`의 31개 이벤트 블록을 따라가 대사 후보 페이지와 현재 빌드의 변경 여부를 JSON/Markdown으로 생성합니다.
- `tools/english_dialogue_inventory.py`: 레거시 영문 추출본의 3바이트 이벤트 복귀값으로 2,978개 시나리오 대사와 104개 엔딩/에필로그 대사를 분류합니다. 이 값은 일본판 문자열 주소가 아니며 영문/기계번역은 검토용 참고 자료입니다.
- `tools/render_event_pages.py`: 시나리오별 일본판 대사 후보를 주소와 제어코드가 보이는 개별 PNG 및 묶음 시트로 렌더링합니다. 예: `python3 tools/render_event_pages.py --scenario 14`.
- 수동 저장 슬롯이 든 `load-screen` 테스트 SRAM을 재사용해 특정 장으로 바로 들어갈 때는 `python3 tools/run_blastem_sequence.py scenario-select --scenario-number 14 --reuse-runtime-state --click-window --replace-existing`을 사용합니다. 비기 직후 동적 숫자가 붙는 화면에서 멈추려면 같은 옵션으로 `scenario-select-entry`를 사용합니다. 선택 비기 입력이 불안정할 때는 검증된 GST의 수동 슬롯 레코드를 `python3 tools/run_blastem_sequence.py launch-only --manual-slot-gst captures/analysis/dac0_s02_cursor_a.gst --replace-existing`으로 격리 SRAM에 복구한 뒤 화면을 확인하며 `LOAD`로 진입합니다. 복구 도구는 슬롯 체크섬·유효 비트뿐 아니라 게임이 요구하는 SRAM 포맷 마커 `0x1FEE = 0x07CA`도 초기화하고 검증합니다.
- `tools/jp_global_inventory.py`: 클래스·아이템·인물 이름의 공유 1바이트 테이블과 전역 글꼴 충돌 가능성을 JSON/Markdown으로 생성합니다.
- `tools/jp_resource_inventory.py`: 조건·시나리오 설명·아이템·마법·용병 전투명·상태 메시지의 16비트 리소스 변경/검수 상태를 생성합니다.
- `tools/item_shop_inventory.py`: 원본 전체 아이템 비기 목록의 ID `1..37`, 일본어명, 한국어 이름·설명, 가격표, 아이콘 VRAM 타일과 실기 검증 상태를 `localization/item_shop_inventory.json` 및 `docs/item_shop_runtime_matrix.md`로 생성합니다.
- `tools/capture_item_shop_inventory.py`: 현재 생산 ROM에서 전체 아이템 진단 체크섬과 ASCII 캡처 접두사를 자동 산출하고, 5행씩 8페이지인 ID `1..37`을 개별 캡처합니다. 마지막 페이지는 2행이므로 전환 후 Up 1회만 사용합니다. `--start-item/--end-item`으로 재개하고, 실제 상점 설명 패널을 검사하며, 예외가 나도 BlastEm을 종료합니다. Windows DWM 캡처가 멈추거나 단일 디스플레이의 팔레트 값이 낮을 때는 `--xlib-only`를 사용합니다. 40칸 보유 한도 검증에는 배포 ROM을 바꾸지 않는 `python3 tools/build_item_shop_probe_rom.py --free-prices` 진단 옵션을 사용합니다.
- `tools/build_discard_prompt_probe_rom.py`: 40칸이 찬 진단 상점에서 원본 아이템 지급 루틴과 사용되지 않던 폐기 목록 콜백을 연결합니다. 배포 ROM에는 없는 진단 흐름이며 `버릴 아이템`, 5행 목록, 9페이지 이동과 확정 복귀를 검사할 때만 사용합니다.
- `tools/jp_ui_surface_inventory.py`: 빌더가 선언한 UI 패치 주소와 압축 작은 글꼴 재배치, 아직 조사할 UI 범주를 기록합니다.
- `tools/jp_compressed_resource_inventory.py`: `0x0B0000`의 429개 압축 리소스를 타입 1 RLE·타입 2 타일 평면·타입 3 LZSS 전용 디코더로 해제해 크기·해시·포인터 변경과 확인된 소유권을 기록합니다.
- `tools/jp_direct_string_inventory.py`: 이벤트 블록 밖의 보수적인 `FFFF` 종료 16비트 문자열 후보를 소유권별로 분류합니다.
- `tools/jp_direct_byte_string_inventory.py`: ROM의 짝수 주소를 32비트 포인터로 보수적으로 해석해 실제 참조되는 `FF` 종료 CP932/ASCII 바이트 문자열 후보를 분류합니다.
- `tools/jp_inline_byte_string_inventory.py`: 포인터 표에 잡히지 않는 `FF` 종료 반각 일본어/ASCII 연속열 중 의미 문자가 3개 이상인 후보를 보수적으로 스캔합니다. 현재 646개를 전부 분류하며, 실기 검증된 77행 숨김 사운드 테스트 표와 정적으로 소유권을 확인한 원본 `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ` 레코드를 구분해 기록합니다. 폐기 목록의 실제 한글 실기 증거는 별도 16x16 렌더러 진단으로 관리합니다.
- `tools/runtime_verification_inventory.py`: 31개 장의 설명·조건·준비·오프닝·전투·턴 이벤트·클리어·분기/엔딩 실기 상태를 `localization/runtime_verification.json`에서 검증해 Markdown 체크리스트로 만듭니다. 정적 번역 완료와 실기 완료를 구분합니다.
- `tools/build_epilogue_probe_rom.py`: 원본 엔딩 선택 루틴의 조건표를 임시로 바꿔 지정한 후일담 레코드를 실제 엔딩 렌더러로 확인할 개발용 ROM을 만듭니다. `--start-slot 14/15`로 리아나·세계 특수 경로부터 시작할 수 있습니다.
- `tools/build_ending_dialogue_probe_rom.py`: 재배치된 엔딩 방문 대사 23개를 83페이지 진단 스트림으로 연결해 실제 방문 대사 렌더러에서 전 페이지를 확인합니다. 선택 조건 자체를 증명하는 ROM은 아니며 생성 ROM과 manifest는 커밋하지 않습니다.
- `tools/build_scenario27_ending_probe_rom.py`: 시나리오 27의 베른하르트를 엘윈 바로 위에 두고 능력치와 용병을 제한해 원작 결말·후일담 진입을 단축합니다. 피해 난수로 HP 1이 남을 수 있으므로 공격 직전 상태 저장 후 재시도해야 합니다. 두 프로브 ROM은 배포·커밋하지 않으며 구조와 사용 순서는 `docs/epilogue_probe.md`에 기록합니다.
- `tools/build_title_save_probe_rom.py`: 타이틀의 LOAD 진입 두 곳만 원본 SAVE 렌더러로 돌리는 진단 ROM을 만들어 `저장`과 `다음 시나리오` 고정 레코드의 실제 소유권을 확인합니다. 정상 시나리오 클리어 작업 RAM이 없으므로 슬롯의 동적 숫자·스프라이트 품질 검증에는 사용하지 않습니다.
- `tools/build_scenario1_clear_probe_rom.py`: 시나리오 1의 발드만 첫 플레이어 배치 슬롯 옆으로 옮기고 AT/DF와 용병을 제거한 진단 ROM을 만듭니다. 원본 이벤트·클리어·저장 렌더러는 건드리지 않으며 정상 클리어 뒤 결과 화면과 동적 저장 슬롯을 짧게 검증할 때만 사용합니다.
- `tools/build_scenario1_great_slime_status_probe_rom.py`: 위 시나리오 1 표시 대상에 일본판 시나리오 10의 실제 그레이트슬라임 이름·클래스 ID만 적용합니다. 작은 상태/전투 글꼴 충돌을 빠르게 재현하는 비배포 표시 진단이며 시나리오 진행 증거로 사용하지 않습니다.
- `tools/build_scenario2_escape_probe_rom.py`: 시나리오 2의 승리 조건인 `리아나 북쪽 도착`을 원본 이벤트로 빠르게 재현하기 위해 리아나의 고정 배치 Y 좌표만 `18→1`로 바꿉니다. 원본 헤더·배치표·리아나 레코드를 검증하고 이벤트 및 다른 필드는 건드리지 않습니다. 생성 ROM은 커밋하지 않으며 전과보고·저장·3장 진입까지 실기로 검증했습니다.
- `tools/build_scenario3_clear_probe_rom.py`: 시나리오 3의 원본 이벤트·배치 구조는 유지하고 적 지휘관 8명의 AT/DF·용병·초기 좌표만 제한합니다. 이벤트 출현 좌표는 원본 스크립트가 다시 지정할 수 있습니다. 수동 슬롯의 엘윈 AT/DF를 높여 정상 전투·턴 이벤트·발가스 퇴각·전과보고·저장·4장 진입을 검증할 때 사용하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario4_clear_probe_rom.py`: 기본 `clear` 모드는 첫 엘윈 배치만 모건 옆으로 옮기고 모건의 AT/DF·용병만 제한해 정상 전투와 5장 진입을 확인합니다. `--mode progression`은 모든 배치 좌표와 이벤트를 보존한 채 적 고정 레코드 5~10의 AT/DF·용병만 제한해 1·3·5턴의 마법 도구·세뇌 이벤트를 확인합니다. 두 모드 모두 일본판 헤더·배치표·11개 고정 레코드를 먼저 검증하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario5_escape_probe_rom.py`: 시나리오 5의 승리 조건 `20턴 내 북쪽 도착`을 원본 이벤트로 재현하기 위해 첫 엘윈 배치의 Y만 `50→1`로 바꿉니다. 원본 헤더·배치표·9개 고정 레코드를 검증하고 적·이벤트·보상은 건드리지 않습니다. 실제 이동 확정 뒤 전과보고·6장 저장·6장 진입까지 실기로 검증했으며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario6_clear_probe_rom.py`: 시나리오 6의 아군·NPC·민간인·이벤트를 보존하고 적 고정 레코드 4~12의 AT/DF와 용병만 제한합니다. 가시 적 8명은 원본 플레이어 배치의 직교 인접 칸으로 옮겨 실제 공격 명령으로 민간인 전원 생존 클리어를 재현합니다. 아뮬렛 보상, 전과보고, 7장 저장과 진입까지 실기로 검증했으며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario7_clear_probe_rom.py`: 시나리오 7의 주민·숨은 키스·나머지 적·이벤트를 보존하고 기남 한 명의 AT/DF·용병·좌표만 제한합니다. 원본 엘윈 배치 바로 위에서 실제 공격 명령으로 기남을 격파해 주민 전원 생존, 미라쥬로브와 룬스톤 보상, 전과보고, 8장 저장과 진입까지 실기로 검증하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario8_clear_probe_rom.py`: 시나리오 8의 크레이머 한 명만 원본 엘윈 배치 바로 위로 옮기고 AT/DF와 용병을 제한합니다. 첫 정상 공격은 원본 보스 생존 처리로 HP 1을 남기므로 턴 종료 뒤 두 번째 정상 공격으로 격파해야 합니다. 발가스 증원·퇴각 대사, 전과보고, 9장 저장과 진입까지 실기로 검증하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario8_status_probe_rom.py`: 위 클리어 진단의 크레이머 표시 레코드에 원본 발가스 이름·제너럴 클래스 ID만 임시 적용해 상태창 글꼴을 짧게 재현합니다. 숨김 발가스의 플래그만 해제하는 방식은 이벤트 배치를 만들지 못하므로 사용하지 않습니다. 이 ROM은 표시 경로 진단 전용이며 배포·커밋하지 않습니다.
- `tools/build_scenario9_clear_probe_rom.py`: 시나리오 9의 레아드 한 명만 원본 엘윈 배치 바로 위로 옮기고 AT/DF와 용병을 제한합니다. 실제 공격 명령으로 레아드를 격파해 전체 퇴각·알하자드 설명·레벨업·전과보고·10장 저장과 진입까지 실기로 검증하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario11_clear_probe_rom.py`: 시나리오 11의 일본판 헤더·배치표·11개 고정 레코드를 검증하고 적 능력치·용병을 제한합니다. `--safe-clear-layout --safe-jessica` 진단 조합은 이벤트를 보존한 채 전투 진영과 제시카만 화재 밖으로 옮겨 9턴 화재·숨은 증원·전과보고·12장 저장과 진입까지 실기로 검증하며 생성 ROM은 커밋하지 않습니다.
- `tools/build_scenario12_clear_probe_rom.py`: 시나리오 12의 일본판 헤더·배치표·11개 수호자 레코드를 검증하고 적 AT/DF·용병만 제한합니다. 선택적인 압축 배치는 클리어 경로 진단용이며 이벤트 카메라에서 맵 스프라이트가 HUD 위로 보일 수 있으므로 UI 증거에는 원본 플레이어 좌표를 보존하는 기본 모드를 사용합니다.
- `tools/build_scenario13_clear_probe_rom.py`: 시나리오 13의 일본판 헤더·7개 플레이어 배치·13개 적 레코드를 검증하고 적 AT/DF·용병만 제한한 뒤 조름만 원본 엘윈 바로 아래로 옮깁니다. 숨김 발가스·레온·레아드의 정체·클래스·레벨·숨김 상태와 모든 이벤트를 보존하므로 후반 턴 이벤트를 확인한 뒤 조름을 정상 공격으로 격파할 때 사용합니다.
- `tools/build_scenario14_clear_probe_rom.py`: 시나리오 14의 일본판 헤더·7명 배치표·11개 적 레코드를 검증하고 적 AT/DF·용병만 제한합니다. 이름·클래스·레벨·좌표와 숨은 레온 및 이벤트는 모두 보존하며, 랑그릿사 목표 타일은 실기 좌표를 확인하기 전까지 임의로 재배치하지 않습니다.
- `tools/build_scenario15_clear_probe_rom.py`: 시나리오 15의 일본판 헤더·7명 배치표·12개 고정 레코드를 검증하고 적 레코드 1~11의 AT/DF·용병만 제한합니다. 아군 스코트와 원본 좌표, 이멜다 및 숨은 스큐라·라나·와이번의 정체·클래스·레벨·숨김 상태와 이벤트를 보존합니다.
- `tools/build_scenario16_clear_probe_rom.py`: 시나리오 16의 일본판 헤더·8명 배치표·10개 적 레코드를 검증하고 AT/DF·용병만 제한합니다. 레온·레아드와 숨은 라나·고스트의 정체·클래스·레벨·좌표 및 모든 이벤트를 보존합니다.
- `tools/build_scenario17_clear_probe_rom.py`: 시나리오 17의 일본판 헤더·8명 배치표·11개 적 레코드를 검증하고 AT/DF·용병만 제한합니다. 베른하르트·보젤과 숨은 매직나이트의 정체·클래스·레벨·좌표 및 모든 이벤트를 보존합니다.
- `tools/build_scenario18_clear_probe_rom.py`: 시나리오 18의 일본판 헤더·8명 배치표·주민 2명·적군 9명을 검증합니다. 주민 레코드는 통째로 보존하고 적군 AT/DF·용병만 제한해 라나·그레이트드래곤과 주민 생존 이벤트를 실기로 확인할 때 사용합니다.
- `tools/build_scenario19_clear_probe_rom.py`: 시나리오 19의 일본판 헤더·8명 배치표·적군 10명을 검증하고 AT/DF·용병만 제한합니다. 이멜다와 숨은 레아드·제국 증원의 정체·클래스·레벨·좌표 및 모든 이벤트를 보존합니다.
- `tools/build_scenario20_clear_probe_rom.py`: 시나리오 20의 일본판 헤더·8명 배치표·적군 10명을 검증하고 AT/DF·용병만 제한합니다. 파이어스와 숨은 와이번·크라켄의 정체·클래스·레벨·좌표 및 키스 관련 해상 이벤트를 보존합니다.
- `tools/build_scenario21_clear_probe_rom.py`: 시나리오 21의 일본판 헤더·8명 배치표·적군 11명을 검증하고 AT/DF·용병만 제한합니다. 라나와 숨은 크라켄·제국 아크메이지의 정체·클래스·레벨·좌표 및 모든 이벤트를 보존합니다.
- `tools/build_scenario22_clear_probe_rom.py`: 시나리오 22의 일본판 헤더·8명 배치표·12개 고정 레코드를 검증합니다. 아군 리아나는 통째로 보존하고, 이벤트 전환용 특수 진영과 숨은 베른하르트를 포함한 전투 레코드 1~11의 AT/DF·용병만 제한합니다.
- `tools/build_scenario23_clear_probe_rom.py`: 시나리오 23의 일본판 헤더·9명 배치표·적군 11명을 검증하고 AT/DF·용병만 제한합니다. 레아드와 제국 드래곤로드·팔라딘·세인트·위저드의 정체·클래스·레벨·좌표 및 성스러운 지팡이 관련 이벤트를 보존합니다.
- `tools/build_scenario24_clear_probe_rom.py`: 시나리오 24의 일본판 헤더·9명 배치표·11개 고정 레코드를 검증합니다. 특수 진영 베른하르트는 통째로 보존하고 데몬로드·리치·케르베로스·뱀파이어로드 적군 10명의 AT/DF·용병만 제한합니다.
- `tools/build_scenario25_clear_probe_rom.py`: 시나리오 25의 일본판 헤더·9명 배치표·12개 고정 레코드를 검증합니다. 아군 제시카는 통째로 보존하고 레온·레아드·에그베르트 및 숨은 드래곤로드를 포함한 적군 11명의 AT/DF·용병만 제한합니다.
- `tools/build_scenario26_clear_probe_rom.py`: 시나리오 26의 일본판 헤더·10명 배치표·적군 10명을 검증하고 AT/DF·용병만 제한합니다. 아크메이지·위저드·세인트·나이트마스터와 에그베르트의 정체·클래스·레벨·좌표 및 이벤트를 보존합니다.
- `tools/build_scenario27_clear_probe_rom.py`: 시나리오 27의 일본판 헤더·10명 배치표·적군 10명을 검증하고 AT/DF·용병만 제한합니다. 베른하르트와 숨은 레온을 포함한 정체·클래스·레벨·좌표·숨김 상태 및 이벤트를 보존합니다.
- `tools/build_scenario28_clear_probe_rom.py`: 시나리오 28의 일본판 헤더·7명 배치표·빌더 적군 9명을 검증하고 AT/DF·용병만 제한합니다. 일반 형님과 아돈·삼손·바란의 이름 ID·클래스·레벨·좌표 및 이벤트를 보존합니다.
- `tools/build_scenario29_clear_probe_rom.py`: 비밀 시나리오 X2의 일본판 헤더·8명 배치표·적군 9명을 검증하고 AT/DF·용병만 제한합니다. 제국 서펜·드래곤 부대와 세이갈·폴거의 이름·클래스·레벨·좌표 및 이벤트를 보존합니다.
- `tools/build_scenario30_clear_probe_rom.py`: 비밀 시나리오 X3의 일본판 헤더·9명 배치표·적군 11명을 검증하고 AT/DF·용병만 제한합니다. 그레이트드래곤과 일반 마녀/메이지, 숨은 마녀/세인트의 서로 다른 원본 레코드 및 이벤트를 보존합니다.
- `tools/build_scenario31_clear_probe_rom.py`: 비밀 시나리오 X4의 일본판 헤더·10명 배치표·전투 레코드 10개를 검증하고 기본 모드에서는 AT/DF·용병만 제한합니다. `--compact-layout`은 원본 클래스·진영을 유지한 전투 UI 진단용이고, `--completion-layout`은 원본 베른하르트 레코드 하나만 엘윈 옆에 둬 최종 보스 사망·전과보고·저장 핸들러를 확인하는 비배포 진단용입니다. 후자의 레코드 수/좌표는 이름·클래스·진영 근거로 사용하지 않습니다.
- `tools/game_genie.py`, `tools/build_game_genie_probe_rom.py`: 명시한 Genesis Game Genie 코드를 주소/워드로 해석하고 무시되는 실험 ROM을 만듭니다. 코드 호환 리비전을 자동 판별하지 않으며, 프로젝트 원본은 일본판 REV00입니다. REV01용 공개 코드는 주소가 정상적으로 보여도 REV00을 리셋시킬 수 있으므로 프리셋을 제공하지 않습니다.
- `editor/server.py`: 클래스, LV, AT, DF, 용병 구성을 수정하는 로컬 시나리오 편집기입니다.
- `scripts/legacy/`: 영어판 기반 초기 실험 스크립트 보관 위치입니다.
- `script_extract/english_records.json`: 추출한 영어 대사 레코드입니다.
- `script_extract/korean_records_google.json`: 기계 번역 기반 전체 대사 레코드입니다.
- `scripts/legacy/romhack_capture.py`: BlastEm 자동 입력/캡처 보조 스크립트입니다.
- `roms/builds/`: 생성된 테스트 ROM 출력 위치입니다.
- `captures/`: 분석 이미지와 실행 캡처 출력 위치입니다.

## 빌드

일본판 기반 probe:

```bash
python3 scripts/build_korean_jp_probe.py
```

빌더는 ROM 끝을 `0x3FFFFF`로 확장하면서 원본 SRAM과 검증된 저장 루틴
절대주소를 `0x400001..0x403FFF`로 함께 옮깁니다. 원본 `0x200001` 주소를
유지하면 확장 ROM과 겹쳐 저장 파일이 기록되지 않습니다.

출력 파일:

```text
roms/builds/Langrisser II (Korean JP Probe).md
```

## 시나리오 편집기

에뮬레이터 없이 로컬 편집기를 실행합니다.

```bash
python3 editor/server.py
```

브라우저에서 `http://127.0.0.1:8765`를 엽니다. 31개 시나리오를 선택할 수 있고, 현재 확정된 필드인 클래스, LV, AT, DF, 용병 6칸만 수정합니다. `편집 ROM 빌드`는 원본을 덮어쓰지 않고 다음 파일을 만듭니다.

```text
roms/builds/Langrisser II (Korean Scenario Edit).md
```

시나리오 포인터 표는 `0x18005E`이며 각 헤더의 `+0x0C`가 고정 배치 목록을 가리킵니다. 목록은 2바이트 개수 뒤에 36바이트 레코드가 이어집니다. 쓰기가 검증되어 현재 노출한 필드는 레벨 `+0x0E`, AT/DF `+0x12/+0x13`, 클래스 `+0x1B`, 용병 6칸 `+0x1E..+0x23`입니다. 이름 ID `+0x1A`, 좌표, 이벤트 플래그는 문맥 표시용으로만 읽으며 의미와 파급 범위가 완전히 확정되기 전에는 쓰지 않습니다.

GUI와 같은 검증 데이터 계층을 JSON으로 확인하거나 다른 편집기에서 재사용하려면 다음처럼 실행합니다. `--scenario`를 반복하지 않으면 31개 전부를 내보냅니다.

```bash
python3 tools/scenario_data.py --scenario 11 --output captures/analysis/scenario11_editor.json
```

내보낸 `x/y`는 고정 배치표의 초기값입니다. 시나리오 이벤트가 등장·퇴각·증원 좌표를 다시 쓰는 경우가 있으므로 편집 가능 필드는 `level/at/df/class_id/mercenaries`로 제한합니다. 진영은 레코드 `+0x08`의 원본 바이트를 읽어 `side_id`로 내보내며, 확인된 `01/03/04/08`을 각각 아군 이벤트, NPC/아군, 적군, 특수 진영으로 표시합니다. `side_id` 역시 아직 읽기 전용입니다.

고정 배치 레코드의 클래스 ID만 바꾸면 화면상의 클래스명과 능력치는 바뀌지만 마법·소환 명령은 부여되지 않습니다. REV00 시나리오 1에서 레아드를 `서머너`로 바꾼 실기 검증에서도 `이동/공격/치료/명령`만 남았습니다. 전투 중 유닛 구조체에서는 `+0x50` long의 비트 0과 17이 각각 마법·소환 명령 조건이지만, 고정 배치 레코드에서 이 런타임 값으로 이어지는 소유권은 아직 확정하지 않았습니다. 따라서 현재 편집기는 클래스 선택을 능력·마법 세트 편집으로 취급하지 않으며, 원본 필드 매핑이 검증될 때까지 별도 기능으로 노출하지 않습니다.

이름 포인터 표 `0x0618E8`은 105개가 아니라 117개입니다. 편집기 메타데이터는
일본 원문의 반복 포인터를 보존해 0~116번 전부에 한국어 목표를 지정했으며,
몬스터·형님·마녀·신관·제국병·파이어스와 마지막 공백 ID까지 포함합니다.

정적 검증:

```bash
python3 -m unittest tests.test_scenario_data tests.test_jp_event_inventory tests.test_jp_global_inventory
python3 tools/jp_event_inventory.py
python3 tools/jp_global_inventory.py
python3 tools/jp_resource_inventory.py
python3 tools/jp_ui_surface_inventory.py
python3 tools/class_change_inventory.py
python3 tools/jp_compressed_resource_inventory.py
python3 tools/jp_direct_string_inventory.py
python3 tools/jp_direct_byte_string_inventory.py
```

전체 한글화 단계와 현재 이벤트 범위는 `docs/full_localization_plan.md`, `docs/full_localization_inventory.md`, `localization/event_pages.json`에 기록합니다. 전역 이름 테이블 조사는 `docs/global_localization_inventory.md`, `localization/global_strings.json`에, 공유 16비트 리소스는 `docs/shared_word_resource_inventory.md`, `localization/shared_word_resources.json`에 기록합니다. UI 선언과 조사 공백은 `docs/ui_patch_surface_inventory.md`, `localization/ui_patch_surfaces.json`에, 압축 리소스 전체 표는 `docs/compressed_resource_inventory.md`, `localization/compressed_resources.json`에, 16비트 직접 문자열 후보는 `docs/direct_word_candidate_inventory.md`, `localization/direct_word_candidates.json`에, 포인터 참조 바이트 문자열 후보는 `docs/direct_byte_string_candidate_inventory.md`, `localization/direct_byte_string_candidates.json`에 기록합니다. `modified`나 `touched`는 일본판과 바이트 또는 글꼴이 다르다는 뜻이며 완역·실기 검증 완료를 의미하지 않습니다.

직접 문자열 후보 783개는 모두 포인터 레코드, 선언된 패치, 엔딩/후일담,
이름 입력·크레딧·화면별 토큰, 또는 렌더로 확인한 데이터 오탐으로 분류했습니다.
이 과정에서 부분 패치로 가려졌던 엔딩 방문 대사 23개와 인물별·세계 후일담
90개 레코드를 별도 작업 대상으로 확인했습니다. 원본 레코드 용량 때문에
붙여 썼던 문장은 UI 제약이 아니었습니다. 현재 후일담 90개 레코드는 원본 해시,
제어 코드, 페이지 수와 개별 포인터를 검증한 뒤 `0x2C0000..0x2CAxxx` 확장
영역으로 옮겨 자연스러운 띄어쓰기와 줄바꿈을 적용했습니다. 정적 렌더러와
직접 문자열 인벤토리도 일본판에서는 원본 주소, 한글판에서는 재배치 포인터를
따릅니다. 엔딩 방문 대사 23개도 `0x2D0000`부터 재배치해 같은 방식으로
띄어쓰기를 적용했습니다. 생산 checksum `E38B` 기반 진단 checksum `F852`는
23개·83페이지를 실제 방문 렌더러로 모두 재생한 뒤 마지막 숲 장면과 정상
SEGA 재기동까지 도달했습니다. 시나리오 27 원작 결말을 거쳐 일반 캐릭터, 리아나, 세계 후일담
선택·렌더러 경로도 실제 BlastEm에서 검증했습니다. 재현 절차와 체크섬은
`docs/epilogue_probe.md`를 참고합니다.

패치 원인 분리용 옵션:

```bash
python3 scripts/build_korean_jp_probe.py --skip-condition
python3 scripts/build_korean_jp_probe.py --skip-scenarios
python3 scripts/build_korean_jp_probe.py --skip-direct
python3 scripts/build_korean_jp_probe.py --skip-items
python3 scripts/build_korean_jp_probe.py --no-patch-byte-ui-strings
```

실험용 옵션:

```bash
python3 scripts/build_korean_jp_probe.py --patch-class-byte-table
python3 scripts/build_korean_jp_probe.py --patch-class-byte-subset
python3 scripts/build_korean_jp_probe.py --include-unsafe-direct-names
```

이 실험 옵션들은 기본 빌드에서 꺼져 있습니다. `--patch-class-byte-table`과 `--patch-class-byte-subset`은 원본 클래스 문자열을 제자리에서 넓게 덮는 과거 실험 경로입니다. 현재 기본 빌드는 그 경로 대신 117개 이름과 157개 클래스/용병 문자열 전체를 확장 영역으로 재배치하고 `00,index` 인코딩으로 표시합니다. 준비창의 짧은 메뉴·상점 라벨은 별도 `BYTE_UI_STRING_PATCHES`로 처리합니다. 작은 UI 폰트는 그래픽 리소스 `#1`을 새 위치로 재압축/재배치해 함께 패치합니다. 문제가 생길 때는 `--no-patch-byte-ui-strings`로 전체 재배치와 작은 UI 문자열·시스템 폰트 패치를 함께 빼서 원인을 분리합니다. `--include-unsafe-direct-names`는 `0x974xx` 후보 이름 테이블을 건드려 이름 확정 이후 진행을 깨뜨릴 수 있습니다.

기존 영어판 기반 WIP는 참고용 legacy입니다:

```bash
python3 scripts/legacy/build_korean_complete_wip.py
```

출력 파일:

```text
Langrisser II (Korean Complete WIP).md
```

## 실행

BlastEm이 `tools/blastem/`에 있는 경우:

```bash
env LD_LIBRARY_PATH=tools/blastem/lib tools/blastem/blastem "roms/builds/Langrisser II (Korean JP Probe).md"
```

현재 확인된 기본 키:

- `Return`: Start
- `d`: C / 결정
- `s`: B / 취소

반복 테스트용 시퀀스:

```bash
python3 tools/run_blastem_sequence.py shop
```

이 도구는 BlastEm 실행 후 12초에 첫 `Start`, 그 2초 뒤 두 번째 `Start`를 보내고 `C -> C -> C -> B 유지 -> C -> 아래 -> 아래 -> C -> C -> C`를 이어 보냅니다. `tools/send_blastem_keys.py`의 키 표기는 `key[@hold][:wait]` 형식입니다. 예를 들어 `b@3.0:0.15`는 B를 3초 누른 뒤 0.15초 기다립니다. BlastEm 속도 키 `4`는 400%로 적/NPC 이동과 전투 애니메이션을 빠르게 넘길 때, `0`은 100%로 대사와 캡처를 확인할 때 사용합니다.

입력 자동화 주의점:

- 중간 캡처/분석을 끼우면 타이틀 idle 컷신이 다시 떠서 입력 순서가 어긋납니다. 상점 확인처럼 빠른 진입이 필요한 테스트는 시퀀스를 한 번에 보낸 뒤 마지막 화면만 캡처합니다.
- Barrier나 다른 창 포커스 때문에 XTest 입력이 터미널/채팅창으로 갈 수 있습니다. 자동 입력 전에는 BlastEm 창을 클릭해서 SDL 포커스를 잡아야 합니다.
- `--send-event`는 키를 BlastEm 창에 직접 보내므로 다른 프로그램에 키가 들어가는 문제를 줄입니다. 자동 테스트용 설정은 호스트 게임패드 바인딩도 제거하므로 다른 게임에서 사용하는 Xbox 패드가 BlastEm을 동시에 조작하지 않습니다.
- 자동 테스트 실행은 BlastEm에 `320 240` 크기 인자를 넘겨 작은 창으로 띄웁니다. 큰 창이 필요하면 `tools/run_blastem_sequence.py`에 `--window-width 640 --window-height 480`을 명시합니다.
- 예전 성공 캡처(`captures/run/font_resource_08_conditions.png` -> `font_resource_11_shop_knife.png`)는 빠른 진입과 `B` 길게 누르기를 분리해서 보낸 흐름입니다. 현재 도구는 키별 hold를 지원하므로 같은 흐름을 한 명령으로 재현할 수 있습니다.
- 현재 확인된 일본판 시작 타이밍은 `load ROM` 후 12초에 첫 `Start`, 그 2초 뒤 두 번째 `Start`입니다. 이보다 빠르면 첫 입력이 씹히고, 늦으면 타이틀 idle 컷신으로 들어갑니다.
- 일반 화면 전환 자동 입력은 최소 0.8초 간격을 둡니다. 단, 시나리오 선택 비기의 `Left, Right, Start, C` 네 키는 0.05초 간격이어야 하며 도구가 이 타이밍을 별도로 적용합니다. 상점 구매 검증은 `python3 tools/run_blastem_sequence.py shop-buy`, 지휘관 배치 검증은 `python3 tools/run_blastem_sequence.py arrange`, 전투 명령은 `python3 tools/run_blastem_sequence.py battle-command`, 첫 턴 종료 후 대사는 `python3 tools/run_blastem_sequence.py first-turn-dialogue`를 사용합니다.
- `tools/send_blastem_keys.py`는 RandR에서 활성 모니터 중 가장 넓은 출력을 골라 BlastEm 창을 배치합니다. 현재 Windows의 가로형 서브 모니터는 X 출력 `XWAYLAND8` (`1920,717`, 3440x1440)입니다. 다른 출력을 강제하려면 `BLASTEM_MONITOR=<X 출력명>`을 설정하고, RandR를 쓸 수 없으면 기존 `(40,40)` 위치로 돌아갑니다. `--send-event` 모드는 창 위치만 맞추고 활성 창 요청이나 포커스 변경을 하지 않으므로 사용자가 다른 게임을 하는 동안에는 이 모드만 허용합니다.
- `tools/capture_blastem_window.py`는 WSLg에서 Windows DWM 창 경계, Windows 배율, X11 클라이언트 오프셋을 함께 적용해 게임 영역을 우선 캡처합니다. DWM 경로는 `CopyFromScreen`만 사용하며 창 활성화나 포커스 변경을 하지 않습니다. 가려진 OpenGL 창을 `PrintWindow`로 찍으면 갱신되지 않은 타일이 현재 화면에 합성될 수 있으므로 자동 fallback과 실기 합격 자료에서 제외했습니다. 자동 시퀀스에는 포커스 강탈 옵션이 없으며, 단발 캡처의 `--allow-focus-steal`만 사용자가 자리를 비우지 않았음을 확인한 뒤 명시적으로 사용할 수 있습니다.
- 준비 메뉴의 네 항목은 모두 6칸 폭입니다. 원본 토큰 표가 후행 공백에 사용한 `0x05FC`는 준비 화면에서 다시 로드되지 않아 직전 시나리오 설명 글자가 남을 수 있습니다. 빌더는 원본 네 행과 구분자를 검증한 뒤 다섯 후행 셀을 준비 화면에서 실제로 로드되는 공백 타일 `0x0540`으로 바꿉니다.
- 다른 장의 설명을 넘길 때는 고정 횟수로 C를 누르지 말고, 실행 중인 창에 `python3 tools/run_blastem_sequence.py detect-prep --no-launch --send-event --capture-prefix captures/run/sNN_brief.png`를 사용합니다. 준비창의 좌우 패널과 소지금 패널을 감지한 즉시 멈추며 `--capture-prefix`는 탐지 과정의 모든 화면을 번호별로 보존합니다. 같은 옵션은 `detect-command`의 오프닝/턴 이벤트 검수에도 사용할 수 있습니다.
- `scenario-select`는 선택기 진입에 필요한 수동 세이브 슬롯을 보존하기 위해 `captures/runtime/load-screen`을 기본 초기화하지 않습니다. 다른 시퀀스의 격리 런타임은 기존처럼 `--reuse-runtime-state`를 주지 않으면 새로 만듭니다.
- `scenario-select-entry`는 `Left, Right, Start, C` 비기 입력 직후 멈추고 시나리오 이동이나 확정을 보내지 않습니다. 전체 `scenario-select`와 같은 단일 입력 명령을 사용하므로, 창을 나눠 조작하다 비기가 누락되는 이전 실패를 반복하지 않습니다.
- 시나리오 선택 비기의 시작 행은 항상 1이 아니라 선택한 수동 슬롯에 저장된 현재 시나리오입니다. 도구는 슬롯 1의 유효 비트와 체크섬을 확인하고 첫 워드의 시나리오 번호를 읽은 뒤 `--scenario-number`까지 필요한 `Up/Down`만 보냅니다. 선택 후 보이는 경로 지도에서 다음 `C`부터 설명 스크롤이 시작됩니다.
- `launch-only`도 `load-screen` 격리 런타임을 보존하며 게임 입력을 전혀 보내지 않습니다. `--manual-slot-gst`는 GST 작업 RAM의 `0xA49C/0xBD6E/0xC7F2` 세 구간을 수동 슬롯 1로 직렬화하고 체크섬과 유효 비트를 다시 계산하므로, 빌드가 달라 이전 GST 자체를 직접 로드할 수 없을 때 사용합니다.
- 복구한 수동 슬롯의 지휘관 진행도만 실험할 때는 `--runtime-name`으로 격리 폴더를 지정하고 `--manual-slot-commander-id 1 --manual-slot-level 9 --manual-slot-experience 16 --manual-slot-expected-class 0x01`을 함께 사용합니다. 필요하면 `--manual-slot-class`, `--manual-slot-at`, `--manual-slot-df`도 덧붙입니다. 24바이트 지휘관 레코드의 확인된 오프셋은 클래스 `+0`, 레벨 `+2`, EXP `+3`, AT `+4`, DF `+5`이며 도구는 원본 클래스와 `0..99` 능력치 범위를 검사하고 슬롯 체크섬을 다시 계산합니다. 준비/배치 중 런타임 동기화가 값을 되돌릴 수 있으므로 클래스 체인지 실기 확인에는 `tools/build_class_change_probe_rom.py`의 원본 핸들러 경로를 사용합니다.
- 실행 중인 BlastEm이 있으면 캡처 도구가 이전 창을 잡을 수 있으므로 시퀀스는 기본적으로 중단됩니다. 테스트 창으로 교체해도 될 때만 `--replace-existing`을 사용합니다. 새 창에 `--click-window`를 지정하면 원격 데스크톱 뒤 입력 누락을 줄이기 위해 첫 입력 전에 BlastEm 키보드 캡처를 한 번 켭니다.

영어판 기반 WIP의 1장 진입 테스트 흐름:

```text
Start, Start, C, B(A 선택), Left, Up, C(Done), C
```

일본판 기반 probe에서는 이름 입력 화면의 기본 이름을 그대로 쓸 수 있으므로 이름 화면에서 `Start`를 누르면 바로 진행됩니다.
현재 이름 입력표는 공유 상태/아이콘 타일을 침범하지 않는 57개 한글 음절을 선택할 수 있습니다. 기본 `엘윈`의 이름 확정과 시나리오 진입을 BlastEm에서 검증했습니다. 과거 84자 표에서 `폴`을 직접 선택하는 훅도 검증했지만 전역 작은 글꼴 충돌 때문에 현재 표에서는 제외했습니다. 임의의 모든 한글 조합을 지원하려면 이름 화면 전용 글꼴 또는 조합형 입력기가 필요합니다.

```text
Start(컷신 스킵), Start(타이틀), C, Start(이름 확정), C
```

BlastEm이 기존 SRAM을 자동으로 불러오면 ROM 변경과 별개로 이름 입력/진행 테스트 결과가 달라질 수 있습니다. 테스트가 이상하면 아래 파일을 백업 후 새로 시작합니다.

```text
~/.local/share/blastem/Langrisser II (Korean JP Probe)/save.sram
```

## 현재 상태

### 일본판 기반 새 방향

- 명칭은 MD 일본판 ROM의 실제 클래스/용병 ID와 3단계 구성을 우선합니다. 한국어 표기는 [랑그릿사 2](https://namu.wiki/w/%EB%9E%91%EA%B7%B8%EB%A6%BF%EC%82%AC%202), [시리즈 용병](https://namu.wiki/w/%EB%9E%91%EA%B7%B8%EB%A6%BF%EC%82%AC%20%EC%8B%9C%EB%A6%AC%EC%A6%88/%EC%9A%A9%EB%B3%91), [MD판 클래스](https://namu.wiki/w/%EB%9E%91%EA%B7%B8%EB%A6%BF%EC%82%AC%202/%ED%81%B4%EB%9E%98%EC%8A%A4), [클래스 체인지](https://namu.wiki/w/%EB%9E%91%EA%B7%B8%EB%A6%BF%EC%82%AC%202/%ED%81%B4%EB%9E%98%EC%8A%A4%20%EC%B2%B4%EC%9D%B8%EC%A7%80)를 참고합니다. PC/리메이크판과 MD판의 용병 단계가 다르면 ROM의 ID와 원문을 기준으로 결정합니다.
- 일본판 텍스트 포인터 테이블을 확인했습니다.
  - 조건 화면: 포인터 테이블 `0x98D7A`, glyph 목록 테이블 `0x986C6`
  - 시나리오 설명: 포인터 테이블 `0x9CF7C`, glyph 목록 테이블 `0x9B2FC`
- 일본판 glyph 원본은 `0x40000`부터 시작하며, glyph 1개는 64바이트입니다.
- 실제 변환은 ROM의 `0x2C390` 루틴과 일치합니다. 각 glyph는 16비트 행 32개를 2bpp 8x8 타일 4개로 변환하고, 화면에서는 2x2 타일로 배치됩니다.
- `tools/jp_text_font_analyzer.py`로 에뮬레이터 실행 없이 원문/폰트/패치 결과를 이미지로 확인할 수 있습니다.
- 기본 빌드는 시나리오 설명 31개를 모두 한국어 텍스트로 패치합니다. 원문 정보를 줄이지 않도록 glyph 목록은 `0x270000` 영역에, 토큰 스트림은 `0x274000` 영역에 재배치하고 포인터 테이블을 갱신합니다.
- 현재 준비창 메뉴, 아이템 이름/설명, 오프닝 일부, 시나리오 설명/조건은 일본판 16x16 glyph 경로로 처리합니다.
- 지휘관 이름과 클래스/용병명은 원래 CP932 반각 가나 바이트 문자열 경로입니다. 기본 빌드는 포인터 테이블 `0x0618E8`의 이름 117개와 `0x05E6D6`의 클래스/용병 157개를 원문 해시로 검증한 뒤 모두 확장 영역의 한국어 `00,index` 문자열로 재배치합니다. `파이터`, `워록`, `솔저`, `가드맨`, `헤비호스맨`, `로얄호스` 같은 명칭은 MD판 원문 ID를 기준으로 하며 외형만 보고 `기병/중기병`처럼 일반화하지 않습니다. 장비 탭은 `무기/방어구/장신구`, 금액은 `소지금`을 사용합니다.
- 2026-07-15에는 117개 이름과 157개 클래스 문자열 전체를 확장 ROM으로 옮기고 `00,index` 전용 인코딩과 16비트 VRAM 조회표를 추가했습니다. 준비 목록뿐 아니라 맵 큰 상태창의 별도 `0x2115E` 경로와 하단 상태바의 `0x105BC` 직접 복사 경로도 같은 인코딩을 해석합니다. 준비창 선택 이름 `0x229F4`, 배치 목록 `0x27A64`, 고용 병종 목록 `0x22AFC`도 별도 pair-aware 렌더러로 처리합니다. checksum `F153`에서 `엘윈/헤인/쉐리/아론/키스`와 `솔저/그리폰`을 준비·고용 화면에서, 앞선 `988E`에서 `제국지휘관/파이터`, `주민/클레릭`, `레아드/매직나이트`, `레온/나이트마스터`, `로얄호스`, `헤비호스맨`을 실전 상태창에서 확인했습니다. 종전의 15타일 `F0-FE -> 3F0-3FE` 경로는 이름 입력 호환용으로 유지합니다. 상세 주소, 원본 해시, 실패한 부분 패치는 `HANDOFF.md`의 `Full Byte Name And Class Tables`에 기록했습니다.
- 준비창/상점의 작은 8x8 시스템 폰트는 `0x40000`의 16x16 일본어 폰트가 아니라 `0xB0000` 그래픽 리소스 테이블의 index `1`입니다. 원본 포인터는 `0x0B0A84`, 타입은 `0x03`, 압축 해제 루틴은 `0x9DFE`, 해제 길이는 `0x2000`입니다. 빌더는 이 리소스를 풀어 필요한 코드 타일에 한글 8x8 글리프를 넣고, 리터럴 압축 블록으로 `0x290000`에 재배치한 뒤 `0x0B0004` 포인터를 새 위치로 바꿉니다.
- 1바이트 UI 한글 글리프 코드는 `BYTE_UI_STABLE_CODE_BY_CHAR`로 고정합니다. 새 byte UI 문자열을 추가할 때 딕셔너리 순서가 바뀌어도 `엘윈`, `헤인`, `아이템` 등의 기존 표시가 다른 글자로 밀리지 않게 하기 위한 안전장치입니다.
- `scripts/build_korean_jp_probe.py`는 확장 ROM의 16x16 한글 글리프를 `0x7000..0x73FE` 뱅크에 저장하고 `0x71FF`는 오프닝용 공백으로 예약합니다. 시나리오 글리프 목록은 `0x270000..0x273FFF`, 설명 토큰은 `0x274000..0x27FFFF`에 재배치하므로 글리프 저장 영역과 겹치지 않으며 일본판의 원래 레코드 길이에도 제한되지 않습니다.
- 직접 문자열 중 일부는 `FFFF` 종료 문자열이 아니라 고정 길이 문자열입니다. 예: `0x97034=兵士配属`, `0x9703C=アイテム装備`, `0x97048=ショップ`, `0x97050=指揮官配置`.
- 현재 일본판 기반 probe에서 준비 메뉴 `용병고용`, `장비착용`, `상점`, `지휘관배치`, 상점 `구입/판매/취소`, 전투 명령 `이동/공격/마법/소환/치료/명령`을 고정 길이 패치로 처리합니다.
- 조건 테이블 32개 중 실제 31개 시나리오 조건을 원래 포인터와 용량 안에서 한국어로 교체합니다. 마지막 32번째 레코드는 준비 UI가 공유하므로 원본 그대로 보존합니다. 이 레코드를 조건으로 오인해 바꾸면 준비 메뉴의 큰 글자가 사라집니다.
- `0x82BFE` 근처 마법명과 `0x82D5A` 근처 용병명은 `FFFF` 종료 직접 문자열로 확인되어 한국어로 교체합니다. 전투 중 마법 선택창은 이 문자열을 사용하지 않고 `0x09B0F4`의 길이표와 glyph `0x03C0`부터 시작하는 전용 폰트를 사용하므로 두 리소스를 함께 패치합니다. 마법명은 랑그릿사 2 마법 문서의 통용 표기를 화면 폭에 맞게 붙여 쓴 `매직애로우`, `파이어볼`, `블리져드`, `슬립`, `프로텍션`, `텔레포트` 등으로 통일합니다.
- `0x82ACA..0x82B90`의 이름 조사, 레벨/AT/DF/MP 상승, 마법 습득, 아이템 획득·장비 메시지도 원본 토큰을 검증한 뒤 한국어로 교체합니다. 이 검증된 공용 메시지들만 실제 공백 글리프를 보존하며, 용량이 짧은 접미사는 `획득`, `습득`, `사용 가능`, `장비했다`로 축약합니다. `GAME OVER`는 관용 영문으로 유지합니다. `0x82B78`의 디버그성 문구는 시스템 표 인덱스 12지만 플레이 가능한 클래스의 성장값은 `0..2`라 동적 접미사 인덱스 `5..6`만 도달하고, 엔트리/문자열 주소 직접 참조도 없어 실행 불가 원본 잔재로 보존합니다.
- `0x001068`에는 37개 장비명을 가리키는 워드 스왑 포인터 테이블이 별도로 있습니다. 첫 문자열 `0x0010FE` 단검부터 `0x0012E8` 아뮬렛까지 원본 블록 해시와 포인터 배열을 검증하고 한글화합니다. 랑그릿사 두 ID는 원본처럼 같은 문자열 포인터를 공유합니다.
- 아이템명은 `0xA14AC` glyph 목록과 `0xA1902` 포인터 테이블을 함께 사용합니다. 모든 이름 토큰을 다시 쓰므로 사용하지 않는 일본어 슬롯은 보존하지 않고, 제목/단검 공용 9개 슬롯과 실제 한국어 글리프만 `0x282000`에 재배치합니다. `0x21C72`의 원본 64-glyph 로드 수는 압축된 목록의 실제 길이로 맞추며 `moveq`의 안전 범위 127개를 빌드에서 검사합니다.
- 아이템 설명문은 별도 glyph 목록 `0xA152E`와 포인터 테이블 `0xA1D7C`를 사용합니다. 첫 설명·공백·수치·가격에 의미가 있는 0~14번 슬롯만 보존하고 실제 한국어 글리프를 뒤에 붙여 원본 192-glyph VRAM 로더 안에 수용합니다. 목록은 `0x286000`으로 재배치하고 37개 설명 레코드를 45칸 고정 레이아웃에 맞춰 교체합니다.
- 상태 메시지 중 `MP不足です`, `眠らされています`, `魔法を封じられています`는 `마나부족`, `수면상태`, `마법봉인`으로 교체합니다.
- 상점의 9칸 구매 거절 문구는 `아이템 구입 불가`입니다. 별도 아이템 지급 경로의 전체 보유 알림은 확장 영역으로 옮겨 `아이템이 가득 찼습니다` / `하나를 버려주세요`로 표시하며, 공간이 부족할 때도 다른 언어가 아니라 의미를 보존한 짧은 한국어 문구를 사용합니다. 두 경로의 앞쪽 제어 워드를 텍스트로 덮으면 메시지 본문이 메뉴 제목으로 표시되므로 포인터·제어 인자를 함께 검증합니다.
- `WEPON`, `PROTECTER`, `ITEM`, `POINT`, `END` 같은 일부 ASCII 라벨은 별도 1바이트 고정 문자열입니다. 장비 탭은 검증된 반각 가나 슬롯과 충돌하지 않는 대문자 타일 5개를 제한적으로 사용해 `무기/방어구/장신구`로 표시합니다. 금액은 `소지금`으로 표시하며, `0x09ABC2`, `0x0A1896`의 5워드 `POINT` 영역만 바꾸고 앞의 통화 아이콘은 보존합니다.
- 준비창 상태 패널 하단의 `シキハイ`/`シュウセイ` 라벨은 작은 UI 폰트 경로입니다. `シキハイ`는 `0x09AB36`, `0x09ACA8`의 16비트 타일 ID 시퀀스와 `0x0A3D15`의 5바이트 레이아웃 문자열을 함께 `지휘범위`로 바꿉니다. `シュウセイ`는 `0x09AB8C`, `0x09ACF0`의 16비트 타일 ID 시퀀스를 `수정`으로 바꿉니다. 2026-07-10 빌드 `C851`에서 준비창 표시를 확인했습니다.
- 상점 제목/완료 메시지는 `0xA1716`의 31-glyph 목록을 VRAM `0xD000`에 로드해 공유합니다. 구매 제목은 0~5번 슬롯으로 `아이템 구입`, 완료 접미사는 6~12번 슬롯으로 `을 구입함`/`을 판매함`을 표시합니다. 이 목록을 짧은 문자열처럼 잘라 쓰면 `단검 소지` 뒤에 깨진 타일이 생깁니다. 판매 화면은 처음에 `0xA16D4` 목록을 로드하지만 아이템 처리 중 `0xA1716`으로 다시 덮이므로, 판매 제목 스트림 `0xA17B8`을 두 목록의 공통 11·12번 슬롯으로 바꿔 `아이템 판매`를 유지합니다. 최종 구매/판매 팝업 `단검을 구입함`, `단검을 판매함`을 실제 화면에서 확인했습니다.
- `0x01807E`의 13바이트 원문 `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ`은 상점 제목이 아니라 사용되지 않던 폐기 목록 렌더러의 프롬프트입니다. 예전처럼 전역 1바이트 글꼴에 넣으면 코드 배정이 밀려 이름이 깨지므로, 현재는 `0x017F08`을 확장 16x16 렌더러 `0x2B8600`으로 보내 `버릴 아이템`, 아이템 5행, 좌우 화살표와 페이지 숫자를 함께 그립니다. 일반 상점은 40칸에서 구매를 거절하므로 진단 ROM만 원본 폐기 초기화 콜백을 호출합니다. 아이템 이름 넘침 은행은 VRAM `0xB400..0xBEFF`의 22슬롯만 사용하며, 바로 뒤 `0xBF00`의 공용 선택 화살표를 침범하지 않습니다.
- 전투 커맨드 메뉴는 `0x9706A`부터 이어지는 연속 글리프열로 읽습니다. `이동/공격/마법/소환/치료/명령`을 2글자씩 따로 패치하면 한 글자씩 밀리므로, 현재 빌드는 `이동공격마법소환치료명령`을 연속 스트림으로 씁니다. 첫 전투에서 엘윈의 `이동/공격/치료/명령`과 헤인의 `이동/공격/마법/치료/명령`을 실제 화면으로 확인했습니다. `소환`은 두 지휘관의 현재 클래스에는 표시되지 않습니다.
- `tools/capture_magic_application.py`는 시나리오 1의 하인 마법 메뉴부터 대상 지정, 삽입 전투 대사, 효과 완료, GST의 MP 감소까지 자동 검증합니다. `--stock-magic --magic-id 0 --target-key up`은 생산판의 마법 소유권/MP 분기를 그대로 둔 매직애로우 경로이고, 기본 모드는 `tools/build_magic_application_probe_rom.py`가 22개 마법을 진단용으로 노출한 경로입니다. checksum `49A2`에서 매직애로우가 발드에게 피해를 주고 MP `12→11`, checksum `797C`에서 어택이 MP `12→10`이 되는 것을 확인했습니다. 후자는 목록·대상·효과 렌더러 진단일 뿐 실제 습득/소유권 증거로 사용하지 않습니다.
- `tools/capture_summon_application.py`는 진단 ROM에서 하인의 `소환` 명령, 8개 목록, 배치, MP 소비와 생성된 소환물 상태까지 확인합니다. checksum `C41E`의 엘리멘탈은 MP `12→7`을 소비하고 하인 런타임 그룹의 7번 구성원 슬롯에 클래스 `0x8D`, 좌표 `(12,20)`으로 생성됐으며, 하단 `엘리멘탈`과 `이동/공격/마법` 메뉴가 정상 표시됩니다. 이 probe는 생산판의 자연 습득/소유권 증거가 아니라 공통 소환 렌더러와 적용 구조의 진단 증거입니다.
- 같은 전투 UI 글리프 목록은 유닛 안내도 공유합니다. 적군 `0x9AEE4`, NPC `0x9AF04`, 행동 완료 `0x9AF26` 토큰을 각각 `적군 유닛입니다`, `NPC 유닛입니다`, `행동완료 유닛입니다`로 바꿉니다. 원래 접미사 `ユニットです`의 마지막 `す` 슬롯은 공백으로 덮어 다른 안내에 일본어 한 글자가 남지 않게 합니다.
- 지휘관 배치 메뉴의 두 특수 행은 화면 로컬 glyph 목록 `0xA2BAC`을 사용합니다. 이 목록을 좁게 `이동순변경자`로 바꿔 `지휘관배치`, `이동순변경`, `자동배치`, `적군보기`, `출격` 전 행을 한국어로 확인했습니다.
- 배치를 마치지 않고 출격할 때의 로컬 토큰 경고 `0xA2C2E`도 미사용 글리프 슬롯 `0xA2B9C`을 이용해 `지휘관배치가끝나지않았습니다`로 표시합니다.
- 전투 중 `Start` 메뉴는 glyph 목록 `0x970D4`와 5행 토큰 스트림 `0x9AD88`을 사용합니다. 현재 빌드는 원래 6칸 행 폭을 보존한 채 `저장`, `불러오기`, `승리조건`, `게임설정`, `턴 종료`로 표시합니다. `턴 종료` 후 Scenario 1 이벤트 5페이지와 `ENEMY PHASE` 진입까지 검증했습니다.
- 타이틀 `LOAD` 화면은 별도 로컬 42글자 은행 `0x0A2F14`와 고정 슬롯 레코드 `0x0A30D6..0x0A3128`을 사용합니다. 커서와 숫자 0~9 슬롯은 보존하고 나머지만 한국어로 교체했으며, 3칸 원본 헤더에 맞지 않는 `불러오기`는 `0x2B7E00`으로 옮겨 표시합니다. checksum `B65D`에서 실제 자동 저장·정상 수동 저장·빈 슬롯·체크섬 손상 슬롯을 만들어 `이어하기`, `시나리오`, `데이터 없음`, `손상된 데이터`를 확인했습니다. 선택 비기의 숫자는 원판처럼 표제 상자의 다섯 번째 칸에 나타나므로, checksum `F04C`에서는 네 글자 표제를 첫 칸인 타일 X=`0x0F`로 옮겨 `불러오기2`가 겹치지 않게 했습니다. `captures/run/f04c_title_load_entry.png`, `captures/run/f04c_scenario_select_entry.png`, `captures/run/f04c_scenario_select_14.png`에서 정상 화면·비기 숫자·14장 진입을 확인했습니다. `0x0A311A`의 `다음 시나리오`는 비기 표제가 아니라 `0x029B70` 저장 렌더러 하단 레코드입니다. checksum `8AEA` 시나리오 1 클리어 진단에서 실제 작업 RAM을 유지한 채 `저장`, `시나리오 2`, `데이터 없음`, `다음 시나리오`와 동적 숫자를 확인했습니다.
- 시나리오 클리어 결과 제목 `戦果報告`는 전역 글꼴의 `戦/果/報/告` ID를 나열한 `0x0A2D88`의 유일한 4워드 목록입니다. 원본 네 ID와 뒤의 `FFFF`를 검증한 뒤 `전과보고`로 교체합니다. production checksum `AD01` 기반 클리어 진단 ROM `479F`에서 `captures/run/479f_s01_clear_result_current.png`의 제목을 실기로 확인했습니다. 같은 실행에서 빈 저장 슬롯과 저장 후 `시나리오 2` 동적 숫자도 `captures/run/479f_s01_clear_save_current.png`로 재검증했습니다.
- 첫 타이틀의 저작권 문구 아래에는 `한글화: HSP1324`를 표시합니다. 원본 타이틀은 정상 소문자 글꼴을 갖지 않고 해당 코드 일부를 지형/아이콘으로 재사용하므로 아이디는 원본 대문자/숫자 글꼴로 통일합니다. 타이틀에서만 압축 리소스 436을 VRAM 타일 `0x3A..0x73`에 덮어쓰고 다음 화면의 기존 글꼴 로더가 게임용 슬롯을 복원합니다. 같은 전용 리소스의 미사용 `a..g` 코드 위치를 이용해 첫 메뉴를 `새 게임 / 불러오기`로 바꾸며 원본 `PUSH START BUTTON`, 저작권, 게임 내 이름·클래스 글꼴은 보존합니다. 일본어 대형 로고는 별도 압축 리소스 393(원본 `0x120EEE`, 해제 후 5984바이트)과 28×8 배치 레코드 `0x0A429E`의 소유권을 확인한 뒤 같은 타일 수를 유지한 `랑그릿사` 그래픽으로 교체합니다. checksum `6C85`의 `captures/run/6c85_title_uppercase_live_3.png`에서 대형 `II`, 천사, 메뉴와 대문자 크레딧을 함께 실기 확인했습니다.
- 맵과 배치 화면의 `SCENARIO` 배너는 공통 8×8 바이트 글꼴의 ASCII `I` 타일 `0x49`를 실제로 사용합니다. 이 타일을 한글 `록`으로 재사용하면 `SCENAR록O`가 되므로 `I`는 원본 그대로 보존합니다. `록`은 이름 입력에서 확장 코드 `0xF6`, 전투 이름/클래스에서 동적 최종 은행 타일 `0x5D8`을 사용합니다. Scenario 2의 현재 배너 crop은 일본판과 픽셀 단위로 완전히 같습니다.
- 시나리오 8 증원 그래픽은 종전 `가/스/럴` 타일을 덮어쓰므로 세 글자는 맵 상태 갱신이 복원하는 최종 확장 은행 `0x5F0..0x5F2`로 옮깁니다. 전과보고 배경도 이 은행을 덮어쓰므로 전과보고 전용 이름 렌더러가 마지막 은행까지 다시 올립니다. checksum `2209`에서 실제 증원 `발가스/제너럴`, `스코트`, `키스`, 시나리오 9 저장과 다음 경로 진입을 확인했습니다.
- 시나리오 9는 production checksum `CE96`에서 만든 clear probe `AF92`로 레아드의 원본 이름·실버나이트 클래스·모든 이벤트를 보존한 채 일반 클리어를 확인했습니다. 실제 `공격` 뒤 전체 후속 대사, `전과보고 / POINT 3060P`, 실제 `시나리오 10` 저장과 다음 경로 진입까지 리셋·프리즈 없이 진행됐습니다.
- `0x97404` 이후 직접 문자열 후보는 렌더링상 캐릭터/몬스터명처럼 보이지만 이름 화면의 실제 표시 테이블은 아닙니다. 기본 빌드는 대부분을 `UNSAFE_DIRECT_NAME_PATCHES`로 제외하며, 실제 Scenario 1 대사에서 소유권을 확인한 `레온`, `레아드`, `주민`, `제국군지휘관` 항목만 좁게 활성화합니다.
- 클래스/용병/몬스터 이름 테이블은 별도 8비트 문자열 테이블입니다.
  - 포인터 테이블: `0x05E6D6`
  - 문자열 영역: `0x05E94A` 이후
  - 포인터는 68000 big-endian 32비트 값입니다. 과거 도구가 `0x05E6D8`에서 워드를 재조합한 것은 2바이트 어긋난 읽기였고 마지막 클래스 156에서 실패하므로 사용하지 않습니다.
  - 문자열 종료값은 `0xFF`이고, 일본판은 CP932 반각 가나를 사용합니다.
  - `tools/jp_byte_table_analyzer.py`로 일본어 원문, 영어판 대응명, 한국어 후보명을 CSV/이미지로 확인합니다.
- 캐릭터/NPC 이름 테이블은 `0x061AC5` 근처에 있으며 역시 `0xFF` 종료 반각 가나 바이트 문자열입니다. 예: `0x061AC5=エルウィン`, `0x061AD8=ヘイン`, `0x061B1C=ボルドー`.
- 작은 UI 폰트 추적에는 GST 저장 상태의 VRAM을 직접 렌더링하는 `tools/render_md_vram_tiles.py`와 `0x9DFE` 압축 블록 검색용 `tools/find_decompressed_tile.py`를 사용합니다. GST 파일의 VRAM 영역은 현재 `0x12478`부터 64KB로 확인했습니다.

분석 예시:

```bash
python3 tools/jp_text_font_analyzer.py report --samples 2
python3 tools/jp_text_font_analyzer.py render-text --table scenarios --index 0 --base 0x40000 --format jp2bpp16 --mapped --cols 18 --scale 4
python3 tools/jp_text_font_analyzer.py --rom "roms/builds/Langrisser II (Korean JP Probe).md" render-text --table conditions --index 0 --base 0x40000 --format jp2bpp16 --mapped --cols 18 --scale 4
python3 tools/jp_text_font_analyzer.py render-direct-strings --start 0x97000 --end 0x97800 --scale 3
python3 tools/jp_text_font_analyzer.py --rom "roms/builds/Langrisser II (Korean JP Probe).md" render-pointer-text --pointer-table 0xA1D7C --low 0xA1E10 --high 0xA2C00 --glyph-list 0x1E9000 --cols 15 --scale 3 --out item_descriptions_korean_probe_cols15.png
python3 tools/jp_byte_table_analyzer.py csv
python3 tools/jp_byte_table_analyzer.py sheet
python3 tools/analyze_name_entry_vram.py captures/analysis/name_entry_probe_fresh.gst --out-dir captures/analysis/name_entry_probe_fresh --scale 2 --label
python3 tools/match_vram_glyph_crops.py --gst captures/analysis/shop_after_shop_title_18082.gst --image captures/run/shop_after_shop_title_18082.png --crop s0:24:24 --crop-w 8 --crop-h 16 --block-w 1 --block-h 2 --column-major --out-csv captures/analysis/shop_title_crop_matches.csv --out-sheet captures/analysis/shop_title_crop_matches.png
```

### 영어판 기반 WIP / Legacy

- 오프닝 일부 한글 출력 확인됨.
- 1장 준비 화면의 기본 항목은 한국어로 표시됩니다.
- 헤인, 전사, 워록, 솔저, 가드, 단검 등 1장 기본 이름 일부가 한국어로 표시됩니다.
- 조건 화면은 `승리조건`, `패배조건`을 한국어로 표시합니다.
- 1장 조건 본문은 `발드 격파`, `엘윈 사망`, `발드가 우하단 도주`로 표시합니다.
- 전투 경로 메뉴의 `Arrange`, `Reorder`, `Auto-Arrange`, `Examine Enemy`, `Sortie`는 전용 고정 타일을 사용해 `배치`, `순서`, `자동`, `적군`, `출격`으로 표시합니다.
- 이름 입력 화면은 고정 폰트 충돌을 피하기 위해 현재 `A`와 `Done`만 남기는 임시 표시 패치를 사용합니다.
- 전투 대사는 별도 고정 폰트 패치를 통해 본문 출력이 다시 동작합니다. 화자 이름 `Hein`은 `헤인` 전용 코드로 덮어씁니다.
- 상태창의 `LV`, `AT`, `DF`, `HP`, `MV`, `MP`, `Range`, `Adjust` 등은 영어 약어를 유지합니다.
- 명령 아이콘 `move/fight/guard/manual`이 한글 글자로 깨지는 문제를 막기 위해 고정 폰트 타일 `F4-F7`은 보호 대상으로 분리 중입니다.

## 주의할 점

- 준비/조건 화면, 전투 대사, 오프닝은 서로 다른 폰트/타일 렌더러를 사용합니다. ROM 용량만 늘린다고 모든 한글 출력 문제가 해결되지는 않습니다.
- 전투 대사 쪽은 별도 고정 폰트 경로를 타므로, VWF 한글 코드와 고정 폰트 타일 충돌을 같이 관리해야 합니다.
- `Battle Route`, `Prologue`, `Scenario`, `Turn` 같은 특수 제목/전투 하단 라벨은 일반 고정 폰트와 다른 경로가 섞여 있어 아직 별도 분석이 필요합니다.
- UI 슬롯이 매우 빡빡합니다. `자/금/고/상/점`처럼 일부 글자는 코드표 슬롯 대신 직접 고정 타일에 배치하고, 전투 경로 메뉴 전용 글자는 별도 빈 타일 후보에 분리합니다.
- 타이틀의 `Press Start Button`, `Start`, `Load`, `NCS Corp.`에 쓰이는 고정 타일은 보호 대상입니다. 이 타일을 한글로 덮으면 시작 화면이 바로 깨집니다.
- `!`, `?` 같은 문장부호는 대사 의미에 중요하므로 보존해야 합니다.
- 영어판 고정 폰트에 한글을 계속 밀어 넣는 방식은 이름 입력, 타이틀, 명령 아이콘, 상태창 glyph와 충돌이 많습니다. 최종 방향은 일본판 glyph 시스템을 이용하는 방식이 더 적합합니다.
- 일본판도 모든 텍스트가 16x16 glyph 시스템은 아닙니다. 클래스/용병/몬스터 이름은 반각 가나용 8비트 렌더러를 사용하므로, 한글화하려면 이 렌더러의 폰트 위치 또는 로딩 경로를 별도로 찾아야 합니다.
- 스캔 결과가 텍스트처럼 보여도 바로 덮어쓰지 않습니다. `0x974xx`처럼 다른 게임 데이터와 겹치거나 진행 코드가 참조하는 영역일 수 있으므로, 포인터 소유권과 실제 화면 반영을 확인한 뒤 패치합니다.
