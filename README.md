# Langrisser II Korean ROM Hack WIP

랑그릿사 II 메가드라이브 한국어화를 진행 중인 작업 폴더입니다.

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
- `docs/name_entry_analysis.md`: 일본판 이름 입력 레이아웃, 84자 한글 선택표, 저장 바이트, 확정 시 인덱스→글리프 변환 훅과 실기 검증 기록입니다.
- `docs/class_change_analysis.md`: 클래스 체인지 15슬롯 공유 글리프와 두 레이아웃의 인덱스 소유권 및 한국어 슬롯 배치를 기록합니다.
- `tools/match_vram_glyph_crops.py`: 실행 캡처의 특정 글자 crop을 VRAM 타일 후보와 비교해 어떤 tile ID가 화면에 보이는지 좁히는 도구입니다.
- `tools/capture_blastem_window.py`: 실행 중인 BlastEm 화면을 캡처합니다. `xwd`가 실패하면 Xlib 직접 캡처로 fallback합니다.
- `tools/send_blastem_keys.py`: BlastEm 창에 테스트용 키 입력을 보냅니다.
- `tools/scenario_data.py`: MD판 31개 시나리오의 고정 배치 레코드를 읽고 제한된 필드를 패치합니다.
- `tools/jp_event_inventory.py`: `0x18011A`의 31개 이벤트 블록을 따라가 대사 후보 페이지와 현재 빌드의 변경 여부를 JSON/Markdown으로 생성합니다.
- `tools/jp_global_inventory.py`: 클래스·아이템·인물 이름의 공유 1바이트 테이블과 전역 글꼴 충돌 가능성을 JSON/Markdown으로 생성합니다.
- `tools/jp_resource_inventory.py`: 조건·시나리오 설명·아이템·마법·용병 전투명·상태 메시지의 16비트 리소스 변경/검수 상태를 생성합니다.
- `tools/jp_ui_surface_inventory.py`: 빌더가 선언한 UI 패치 주소와 압축 작은 글꼴 재배치, 아직 조사할 UI 범주를 기록합니다.
- `tools/jp_compressed_resource_inventory.py`: `0x0B0000`의 429개 압축 리소스를 타입 1 RLE·타입 2 타일 평면·타입 3 LZSS 전용 디코더로 해제해 크기·해시·포인터 변경과 확인된 소유권을 기록합니다.
- `tools/jp_direct_string_inventory.py`: 이벤트 블록 밖의 보수적인 `FFFF` 종료 16비트 문자열 후보를 소유권별로 분류합니다.
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

시나리오 포인터 표는 `0x18005E`이며 각 헤더의 `+0x0C`가 고정 배치 목록을 가리킵니다. 목록은 2바이트 개수 뒤에 36바이트 레코드가 이어집니다. 검증된 편집 필드는 레벨 `+0x0E`, AT/DF `+0x12/+0x13`, 이름/클래스 `+0x1A/+0x1B`, 용병 6칸 `+0x1E..+0x23`입니다. 좌표와 이벤트 플래그는 읽기만 하며 의미가 완전히 확정되기 전에는 쓰지 않습니다.

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
python3 tools/jp_compressed_resource_inventory.py
python3 tools/jp_direct_string_inventory.py
```

전체 한글화 단계와 현재 이벤트 범위는 `docs/full_localization_plan.md`, `docs/full_localization_inventory.md`, `localization/event_pages.json`에 기록합니다. 전역 이름 테이블 조사는 `docs/global_localization_inventory.md`, `localization/global_strings.json`에, 공유 16비트 리소스는 `docs/shared_word_resource_inventory.md`, `localization/shared_word_resources.json`에 기록합니다. UI 선언과 조사 공백은 `docs/ui_patch_surface_inventory.md`, `localization/ui_patch_surfaces.json`에, 압축 리소스 전체 표는 `docs/compressed_resource_inventory.md`, `localization/compressed_resources.json`에, 직접 문자열 후보는 `docs/direct_word_candidate_inventory.md`, `localization/direct_word_candidates.json`에 기록합니다. `modified`나 `touched`는 일본판과 바이트 또는 글꼴이 다르다는 뜻이며 완역·실기 검증 완료를 의미하지 않습니다.

직접 문자열 후보 783개는 모두 포인터 레코드, 선언된 패치, 엔딩/후일담,
이름 입력·크레딧·화면별 토큰, 또는 렌더로 확인한 데이터 오탐으로 분류했습니다.
이 과정에서 부분 패치로 가려졌던 미번역 엔딩 대사 14페이지와 인물별 후일담
97페이지를 별도 작업 대상으로 확인했습니다.

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

이 실험 옵션들은 기본 빌드에서 꺼져 있습니다. `--patch-class-byte-table`과 `--patch-class-byte-subset`은 전체 클래스/용병명 1바이트 문자열을 넓게 건드리는 실험용입니다. 현재 기본 빌드는 1장 확인에 필요한 이름/클래스/용병/아이템 라벨만 별도 `BYTE_UI_STRING_PATCHES`로 제한해서 패치합니다. 작은 UI 폰트는 그래픽 리소스 `#1`을 새 위치로 재압축/재배치해 함께 패치합니다. 문제가 생길 때는 `--no-patch-byte-ui-strings`로 작은 UI 문자열과 시스템 폰트 리소스 패치만 빼서 원인을 분리합니다. `--include-unsafe-direct-names`는 `0x974xx` 후보 이름 테이블을 건드려 이름 확정 이후 진행을 깨뜨릴 수 있습니다.

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

이 도구는 BlastEm 실행 후 12초에 첫 `Start`, 그 2초 뒤 두 번째 `Start`를 보내고 `C -> C -> C -> B 유지 -> C -> 아래 -> 아래 -> C -> C -> C`를 이어 보냅니다. `tools/send_blastem_keys.py`의 키 표기는 `key[@hold][:wait]` 형식입니다. 예를 들어 `b@3.0:0.15`는 B를 3초 누른 뒤 0.15초 기다립니다.

입력 자동화 주의점:

- 중간 캡처/분석을 끼우면 타이틀 idle 컷신이 다시 떠서 입력 순서가 어긋납니다. 상점 확인처럼 빠른 진입이 필요한 테스트는 시퀀스를 한 번에 보낸 뒤 마지막 화면만 캡처합니다.
- Barrier나 다른 창 포커스 때문에 XTest 입력이 터미널/채팅창으로 갈 수 있습니다. 자동 입력 전에는 BlastEm 창을 클릭해서 SDL 포커스를 잡아야 합니다.
- 자동 테스트 실행은 BlastEm에 `320 240` 크기 인자를 넘겨 작은 창으로 띄웁니다. 큰 창이 필요하면 `tools/run_blastem_sequence.py`에 `--window-width 640 --window-height 480`을 명시합니다.
- 예전 성공 캡처(`captures/run/font_resource_08_conditions.png` -> `font_resource_11_shop_knife.png`)는 빠른 진입과 `B` 길게 누르기를 분리해서 보낸 흐름입니다. 현재 도구는 키별 hold를 지원하므로 같은 흐름을 한 명령으로 재현할 수 있습니다.
- 현재 확인된 일본판 시작 타이밍은 `load ROM` 후 12초에 첫 `Start`, 그 2초 뒤 두 번째 `Start`입니다. 이보다 빠르면 첫 입력이 씹히고, 늦으면 타이틀 idle 컷신으로 들어갑니다.
- 자동 입력은 최소 0.8초 간격을 둡니다. 상점 구매 검증은 `python3 tools/run_blastem_sequence.py shop-buy`, 지휘관 배치 검증은 `python3 tools/run_blastem_sequence.py arrange`, 전투 명령은 `python3 tools/run_blastem_sequence.py battle-command`, 첫 턴 종료 후 대사는 `python3 tools/run_blastem_sequence.py first-turn-dialogue`를 사용합니다.

영어판 기반 WIP의 1장 진입 테스트 흐름:

```text
Start, Start, C, B(A 선택), Left, Up, C(Done), C
```

일본판 기반 probe에서는 이름 입력 화면의 기본 이름을 그대로 쓸 수 있으므로 이름 화면에서 `Start`를 누르면 바로 진행됩니다.
현재 이름 입력표는 게임 고유명사에 필요한 84개 한글 음절을 선택할 수 있습니다. 기본 `엘윈`뿐 아니라 `폴`을 직접 선택해 준비창과 출격 대화까지 유지되는 것을 BlastEm에서 검증했습니다. 임의의 모든 한글 조합을 지원하는 조합형 입력기는 아직 범위 밖입니다.

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
- 기본 빌드는 시나리오 설명 31개를 모두 한국어 텍스트로 패치합니다. 11장과 26장은 원본 레코드 용량에 맞춰 한국어 설명을 축약했습니다.
- 현재 준비창 메뉴, 아이템 이름/설명, 오프닝 일부, 시나리오 설명/조건은 일본판 16x16 glyph 경로로 처리합니다.
- 지휘관 이름과 클래스/용병명은 CP932 반각 가나 바이트 문자열 경로입니다. 실제 클래스 포인터 테이블 `0x05E6D6`의 일본어 원문을 빌드 중 검증한 뒤 1장에 필요한 `파이터`, `워록`, `솔저`, `가드맨`, `헤비호스맨`, `로얄호스` 등을 제한 패치합니다. 외형만 보고 `기병/중기병`처럼 일반화하지 않습니다. 작은 탭은 `WPN/ARMOR/ITEM`, 금액은 `소지금`을 사용합니다.
- 준비창/상점의 작은 8x8 시스템 폰트는 `0x40000`의 16x16 일본어 폰트가 아니라 `0xB0000` 그래픽 리소스 테이블의 index `1`입니다. 원본 포인터는 `0x0B0A84`, 타입은 `0x03`, 압축 해제 루틴은 `0x9DFE`, 해제 길이는 `0x2000`입니다. 빌더는 이 리소스를 풀어 필요한 코드 타일에 한글 8x8 글리프를 넣고, 리터럴 압축 블록으로 `0x290000`에 재배치한 뒤 `0x0B0004` 포인터를 새 위치로 바꿉니다.
- 1바이트 UI 한글 글리프 코드는 `BYTE_UI_STABLE_CODE_BY_CHAR`로 고정합니다. 새 byte UI 문자열을 추가할 때 딕셔너리 순서가 바뀌어도 `엘윈`, `헤인`, `아이템` 등의 기존 표시가 다른 글자로 밀리지 않게 하기 위한 안전장치입니다.
- `scripts/build_korean_jp_probe.py`는 일본판 ROM에 한글 glyph를 `0x260` 이후 슬롯에 넣고, 시나리오 설명/조건 화면/직접 문자열 일부를 한국어로 바꾸는 프로토타입입니다.
- 직접 문자열 중 일부는 `FFFF` 종료 문자열이 아니라 고정 길이 문자열입니다. 예: `0x97034=兵士配属`, `0x9703C=アイテム装備`, `0x97048=ショップ`, `0x97050=指揮官配置`.
- 현재 일본판 기반 probe에서 준비 메뉴 `용병고용`, `장비착용`, `상점`, `지휘관배치`, 상점 `구입/판매/취소`, 전투 명령 `이동/공격/마법/소환/치료/명령`을 고정 길이 패치로 처리합니다.
- 조건 화면 32개는 glyph 목록 포인터를 `0x1E7000` 근처 빈 공간으로 재배치해서 한국어 화면으로 교체합니다. 원본 glyph 목록 공간이 짧은 조건도 있어서 재배치가 필요합니다.
- `0x82BFE` 근처 마법명과 `0x82D5A` 근처 용병명은 `FFFF` 종료 직접 문자열로 확인되어 한국어로 교체합니다.
- `0x82ACE..0x82B90`의 레벨/AT/DF/MP 상승, 마법 습득, 아이템 획득·장비 메시지도 원본 토큰을 검증한 뒤 한국어로 교체합니다. `GAME OVER`는 관용 영문으로 유지하며, `0x82B78`의 비기성 문구는 실행 맥락 확인 전까지 보존합니다.
- `0x001068`에는 37개 장비명을 가리키는 워드 스왑 포인터 테이블이 별도로 있습니다. 첫 문자열 `0x0010FE` 단검부터 `0x0012E8` 아뮬렛까지 원본 블록 해시와 포인터 배열을 검증하고 한글화합니다. 랑그릿사 두 ID는 원본처럼 같은 문자열 포인터를 공유합니다.
- 아이템명은 `0xA14AC` glyph 목록과 `0xA1902` 포인터 테이블을 함께 사용합니다. glyph 목록을 `0x282000` 근처 빈 공간으로 재배치하고, 원본 glyph 목록 뒤에 한글 glyph를 추가해 아이템명을 한국어로 바꿉니다.
- 아이템 설명문은 별도 glyph 목록 `0xA152E`와 포인터 테이블 `0xA1D7C`를 사용합니다. glyph 목록 참조 `0x272BC`를 `0x1E9000`으로 재배치하고, 37개 설명 레코드를 45칸 고정 레이아웃에 맞춰 한국어로 교체합니다.
- 상태 메시지 중 `MP不足です`, `眠らされています`, `魔法を封じられています`는 `마나부족`, `수면상태`, `마법봉인`으로 교체합니다.
- 상점 메시지 중 `소지품 가득`, `더 이상 소지 불가` 계열 레코드는 앞쪽 제어 워드 `0000 0001 0012 0020`을 보존해야 합니다. 제어 워드를 텍스트로 덮으면 상점 창에 `구입판매더이...`처럼 메시지 본문이 메뉴 제목으로 표시됩니다.
- `WEPON`, `PROTECTER`, `ITEM`, `POINT`, `END` 같은 일부 ASCII 라벨은 별도 1바이트 고정 문자열입니다. 현재 작은 탭은 안전한 한글 슬롯을 정확한 클래스명에 우선 배정하기 위해 `WPN/ARMOR/ITEM`을 사용하고, 금액은 `소지금`으로 표시합니다. 금액 라벨은 `0x09ABC2`, `0x0A1896`의 5워드 `POINT` 영역만 바꾸며 앞의 통화 아이콘은 보존합니다.
- 준비창 상태 패널 하단의 `シキハイ`/`シュウセイ` 라벨은 작은 UI 폰트 경로입니다. `シキハイ`는 `0x09AB36`, `0x09ACA8`의 16비트 타일 ID 시퀀스와 `0x0A3D15`의 5바이트 레이아웃 문자열을 함께 `지휘범위`로 바꿉니다. `シュウセイ`는 `0x09AB8C`, `0x09ACF0`의 16비트 타일 ID 시퀀스를 `수정`으로 바꿉니다. 2026-07-10 빌드 `C851`에서 준비창 표시를 확인했습니다.
- 상점 제목/완료 메시지는 `0xA1716`의 31-glyph 목록을 VRAM `0xD000`에 로드해 공유합니다. 구매 제목은 0~5번 슬롯으로 `아이템 구입`, 완료 접미사는 6~12번 슬롯으로 `을 구입함`/`을 판매함`을 표시합니다. 이 목록을 짧은 문자열처럼 잘라 쓰면 `단검 소지` 뒤에 깨진 타일이 생깁니다. 판매 화면은 처음에 `0xA16D4` 목록을 로드하지만 아이템 처리 중 `0xA1716`으로 다시 덮이므로, 판매 제목 스트림 `0xA17B8`을 두 목록의 공통 11·12번 슬롯으로 바꿔 `아이템 판매`를 유지합니다. 최종 구매/판매 팝업 `단검을 구입함`, `단검을 판매함`을 실제 화면에서 확인했습니다.
- `0x018082`의 `ｱｲﾃﾑ ｾﾝﾀｸ` 문자열은 상점 관련 텍스트처럼 보이지만, 실제 상점 보유 화면 제목의 `アイテム` 접두부를 바꾸지 못했습니다. 이를 `BYTE_UI_STRING_PATCHES` 앞쪽에 넣으면 1바이트 한글 폰트 코드 배정 순서가 밀려 `엘윈`이 `아이`로 보이는 회귀가 생겼고, 맨 뒤에 넣으면 `엘윈/헤인`은 유지되지만 제목은 여전히 `アイテム소지`였습니다. 2026-07-10에 두 방식 모두 시도 후 되돌렸습니다.
- 전투 커맨드 메뉴는 `0x9706A`부터 이어지는 연속 글리프열로 읽습니다. `이동/공격/마법/소환/치료/명령`을 2글자씩 따로 패치하면 한 글자씩 밀리므로, 현재 빌드는 `이동공격마법소환치료명령`을 연속 스트림으로 씁니다. 첫 전투에서 엘윈의 `이동/공격/치료/명령`과 헤인의 `이동/공격/마법/치료/명령`을 실제 화면으로 확인했습니다. `소환`은 두 지휘관의 현재 클래스에는 표시되지 않습니다.
- 같은 전투 UI 글리프 목록은 유닛 안내도 공유합니다. 적군 `0x9AEE4`, NPC `0x9AF04`, 행동 완료 `0x9AF26` 토큰을 각각 `적군 유닛입니다`, `NPC 유닛입니다`, `행동완료 유닛입니다`로 바꿉니다. 원래 접미사 `ユニットです`의 마지막 `す` 슬롯은 공백으로 덮어 다른 안내에 일본어 한 글자가 남지 않게 합니다.
- 지휘관 배치 메뉴의 두 특수 행은 화면 로컬 glyph 목록 `0xA2BAC`을 사용합니다. 이 목록을 좁게 `이동순변경자`로 바꿔 `지휘관배치`, `이동순변경`, `자동배치`, `적군보기`, `출격` 전 행을 한국어로 확인했습니다.
- 전투 중 `Start` 메뉴는 glyph 목록 `0x970D4`와 5행 토큰 스트림 `0x9AD88`을 사용합니다. 현재 빌드는 원래 6칸 행 폭을 보존한 채 `저장`, `불러오기`, `승리조건`, `게임설정`, `턴 종료`로 표시합니다. `턴 종료` 후 Scenario 1 이벤트 5페이지와 `ENEMY PHASE` 진입까지 검증했습니다.
- ROM 초반의 `SCENARIO` 시스템 메뉴 문자열은 `LOAD/SAVE/CONTINUE/SCENARIO/NOTHING` 테이블과 붙어 있고, `TURN` ASCII 문자열도 별도로 존재하지만, 둘 다 맵 위 `SCENARIO 1`/`TURN 1` 배너에는 영향을 주지 않았습니다. 해당 배너는 별도 타일/그래픽 경로로 봅니다.
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
