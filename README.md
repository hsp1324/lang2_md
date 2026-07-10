# Langrisser II Korean ROM Hack WIP

랑그릿사 II 메가드라이브 한국어화를 진행 중인 작업 폴더입니다.

다른 PC나 다른 Codex 세션에서 이어서 작업할 때는 먼저 [HANDOFF.md](HANDOFF.md)를 읽습니다. 필요한 로컬 ROM/에뮬레이터 파일, 빌드/실행 명령, 테스트 매크로, 해결/미해결 이슈를 그 문서에 정리했습니다.

초기 작업은 영어판 고정 폰트를 기준으로 진행했지만, 슬롯 충돌이 많아 일본판의 16x16 glyph 로딩 시스템을 분석하는 방향으로 전환했습니다. 일본판은 각 텍스트 레코드가 사용할 glyph 목록을 먼저 VRAM에 올리고, 본문은 그 목록의 로컬 인덱스를 참조합니다.

## 필요한 파일

이 저장소는 ROM 바이너리를 추적하지 않습니다. 빌드하려면 아래 위치에 원본 ROM을 직접 두어야 합니다.

- `roms/original/Langrisser II (English).md`
- `roms/original/Langrisser II (Japan).md`

## 주요 파일

- `scripts/build_korean_jp_probe.py`: 현재 우선 진행 중인 일본판 텍스트/glyph 시스템 기반 빌더입니다.
- `scripts/legacy/build_korean_complete_wip.py`: 영어판 고정 폰트 기반 초기 실험 빌더입니다.
- `tools/jp_text_font_analyzer.py`: 일본판 16비트 텍스트 스트림, glyph 목록, `0x40000` JP font 포맷을 오프라인 분석/렌더링하는 도구입니다.
- `tools/jp_byte_table_analyzer.py`: 클래스/용병/몬스터명 8비트 문자열 테이블 분석 도구입니다.
- `tools/render_jp_byte_strings.py`: 준비창/상점처럼 1바이트 문자열을 쓰는 작은 UI 텍스트를 오프라인 렌더링하는 도구입니다.
- `tools/find_decompressed_tile.py`: `0x9DFE` 그래픽 압축 블록에서 특정 VRAM 타일 원본을 찾는 분석 도구입니다.
- `tools/analyze_name_entry_vram.py`: GST 저장 상태에서 VRAM/plane CSV와 렌더 이미지를 뽑아 이름 입력 화면과 메뉴 타일 배치를 추적합니다.
- `tools/match_vram_glyph_crops.py`: 실행 캡처의 특정 글자 crop을 VRAM 타일 후보와 비교해 어떤 tile ID가 화면에 보이는지 좁히는 도구입니다.
- `tools/capture_blastem_window.py`: 실행 중인 BlastEm 화면을 캡처합니다. `xwd`가 실패하면 Xlib 직접 캡처로 fallback합니다.
- `tools/send_blastem_keys.py`: BlastEm 창에 테스트용 키 입력을 보냅니다.
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
- 2026-07-09 기준 자동 입력은 최소 0.8초 간격을 둡니다. 상점 구매 검증은 `python3 tools/run_blastem_sequence.py shop-buy`, 지휘관 배치 검증은 `python3 tools/run_blastem_sequence.py arrange`, 첫 전투 대사 검증은 `python3 tools/run_blastem_sequence.py deploy-dialogue`를 사용합니다.

영어판 기반 WIP의 1장 진입 테스트 흐름:

```text
Start, Start, C, B(A 선택), Left, Up, C(Done), C
```

일본판 기반 probe에서는 이름 입력 화면의 기본 이름을 그대로 쓸 수 있으므로 이름 화면에서 `Start`를 누르면 바로 진행됩니다.

```text
Start(컷신 스킵), Start(타이틀), C, Start(이름 확정), C
```

BlastEm이 기존 SRAM을 자동으로 불러오면 ROM 변경과 별개로 이름 입력/진행 테스트 결과가 달라질 수 있습니다. 테스트가 이상하면 아래 파일을 백업 후 새로 시작합니다.

```text
~/.local/share/blastem/Langrisser II (Korean JP Probe)/save.sram
```

## 현재 상태

### 일본판 기반 새 방향

- 일본판 텍스트 포인터 테이블을 확인했습니다.
  - 조건 화면: 포인터 테이블 `0x98D7A`, glyph 목록 테이블 `0x986C6`
  - 시나리오 설명: 포인터 테이블 `0x9CF7C`, glyph 목록 테이블 `0x9B2FC`
- 일본판 glyph 원본은 `0x40000`부터 시작하며, glyph 1개는 64바이트입니다.
- 실제 변환은 ROM의 `0x2C390` 루틴과 일치합니다. 각 glyph는 16비트 행 32개를 2bpp 8x8 타일 4개로 변환하고, 화면에서는 2x2 타일로 배치됩니다.
- `tools/jp_text_font_analyzer.py`로 에뮬레이터 실행 없이 원문/폰트/패치 결과를 이미지로 확인할 수 있습니다.
- 기본 빌드는 시나리오 설명 31개를 모두 한국어 텍스트로 패치합니다. 11장과 26장은 원본 레코드 용량에 맞춰 한국어 설명을 축약했습니다.
- 현재 준비창 메뉴, 아이템 이름/설명, 오프닝 일부, 시나리오 설명/조건은 일본판 16x16 glyph 경로로 처리합니다.
- 지휘관 이름과 클래스/용병명은 CP932 반각 가나 바이트 문자열 경로입니다. 1장에 필요한 `엘윈`, `리아나`, `헤인`, `볼도`, `파이터`, `워록`, `솔저`, `가드맨`, `단검`과 아이템 탭 `무기/방어구/아이템` 등의 문자열 바이트를 `BYTE_UI_STRING_PATCHES`로 제한 패치합니다.
- 준비창/상점의 작은 8x8 시스템 폰트는 `0x40000`의 16x16 일본어 폰트가 아니라 `0xB0000` 그래픽 리소스 테이블의 index `1`입니다. 원본 포인터는 `0x0B0A84`, 타입은 `0x03`, 압축 해제 루틴은 `0x9DFE`, 해제 길이는 `0x2000`입니다. 빌더는 이 리소스를 풀어 필요한 코드 타일에 한글 8x8 글리프를 넣고, 리터럴 압축 블록으로 `0x290000`에 재배치한 뒤 `0x0B0004` 포인터를 새 위치로 바꿉니다.
- 1바이트 UI 한글 글리프 코드는 `BYTE_UI_STABLE_CODE_BY_CHAR`로 고정합니다. 새 byte UI 문자열을 추가할 때 딕셔너리 순서가 바뀌어도 `엘윈`, `헤인`, `아이템` 등의 기존 표시가 다른 글자로 밀리지 않게 하기 위한 안전장치입니다.
- `scripts/build_korean_jp_probe.py`는 일본판 ROM에 한글 glyph를 `0x260` 이후 슬롯에 넣고, 시나리오 설명/조건 화면/직접 문자열 일부를 한국어로 바꾸는 프로토타입입니다.
- 직접 문자열 중 일부는 `FFFF` 종료 문자열이 아니라 고정 길이 문자열입니다. 예: `0x97034=兵士配属`, `0x9703C=アイテム装備`, `0x97048=ショップ`, `0x97050=指揮官配置`.
- 현재 일본판 기반 probe에서 준비 메뉴 `용병고용`, `장비착용`, `상점`, `지휘관배치`, 상점 `구입/판매/취소`, 전투 명령 `이동/공격/마법/소환/치료/명령`을 고정 길이 패치로 처리합니다.
- 조건 화면 32개는 glyph 목록 포인터를 `0x1E7000` 근처 빈 공간으로 재배치해서 한국어 화면으로 교체합니다. 원본 glyph 목록 공간이 짧은 조건도 있어서 재배치가 필요합니다.
- `0x82BFE` 근처 마법명과 `0x82D5A` 근처 용병명은 `FFFF` 종료 직접 문자열로 확인되어 한국어로 교체합니다.
- 아이템명은 `0xA14AC` glyph 목록과 `0xA1902` 포인터 테이블을 함께 사용합니다. glyph 목록을 `0x282000` 근처 빈 공간으로 재배치하고, 원본 glyph 목록 뒤에 한글 glyph를 추가해 아이템명을 한국어로 바꿉니다.
- 아이템 설명문은 별도 glyph 목록 `0xA152E`와 포인터 테이블 `0xA1D7C`를 사용합니다. glyph 목록 참조 `0x272BC`를 `0x1E9000`으로 재배치하고, 37개 설명 레코드를 45칸 고정 레이아웃에 맞춰 한국어로 교체합니다.
- 상태 메시지 중 `MP不足です`, `眠らされています`, `魔法を封じられています`는 `마나부족`, `수면상태`, `마법봉인`으로 교체합니다.
- 상점 메시지 중 `소지품 가득`, `더 이상 소지 불가` 계열 레코드는 앞쪽 제어 워드 `0000 0001 0012 0020`을 보존해야 합니다. 제어 워드를 텍스트로 덮으면 상점 창에 `구입판매더이...`처럼 메시지 본문이 메뉴 제목으로 표시됩니다.
- `WEPON`, `PROTECTER`, `ITEM`, `POINT`, `END` 같은 일부 ASCII 라벨은 별도 1바이트 고정 문자열입니다. `WEPON/PROTECTER/ITEM`은 준비/상점 탭에서 `무기/방어구/아이템`으로 바꾸지만, 금액 라벨 `POINT`는 준비창과 상점 내부에서 같은 모양으로 정상 표시되는 원본 경로를 유지합니다. 이 값을 16x16 직접 glyph 시퀀스로 바꾸면 준비창 왼쪽 아래 금액 라벨이 빨간 깨짐/빈 타일로 표시됩니다.
- 준비창 상태 패널 하단의 `シキハイ`/`シュウセイ` 라벨은 작은 UI 폰트 경로입니다. `シキハイ`는 `0x09AB36`, `0x09ACA8`의 16비트 타일 ID 시퀀스와 `0x0A3D15`의 5바이트 레이아웃 문자열을 함께 `지휘범위`로 바꿉니다. `シュウセイ`는 `0x09AB8C`, `0x09ACF0`의 16비트 타일 ID 시퀀스를 `수정`으로 바꿉니다. 2026-07-10 빌드 `C851`에서 준비창 표시를 확인했습니다.
- 아이템 보유 화면 제목 `アイテム所持` 계열은 상점 메시지 레코드와 겹칩니다. `0xA1716`은 제목이 아니라 `0000 0001 0012 0020` 제어 워드를 가진 `소지불가` 메시지 레코드이므로, 제목으로 덮으면 구매 팝업에 `입` 같은 잔여 글자가 남습니다. 현재 빌드는 아이템 glyph 목록의 0-5번 로컬 슬롯을 `아이템소지`, 첫 아이템 표시용 6-8번 슬롯을 `단검 + 공백`으로 분리하고, 구매 후 보유 팝업은 `단검 소지`로 표시되는 것을 2026-07-10 빌드 `8034`에서 확인했습니다.
- `0x018082`의 `ｱｲﾃﾑ ｾﾝﾀｸ` 문자열은 상점 관련 텍스트처럼 보이지만, 실제 상점 보유 화면 제목의 `アイテム` 접두부를 바꾸지 못했습니다. 이를 `BYTE_UI_STRING_PATCHES` 앞쪽에 넣으면 1바이트 한글 폰트 코드 배정 순서가 밀려 `엘윈`이 `아이`로 보이는 회귀가 생겼고, 맨 뒤에 넣으면 `엘윈/헤인`은 유지되지만 제목은 여전히 `アイテム소지`였습니다. 2026-07-10에 두 방식 모두 시도 후 되돌렸습니다.
- 전투 커맨드 메뉴는 `0x9706A`부터 이어지는 연속 글리프열로 읽습니다. `이동/공격/마법/소환/치료/명령`을 2글자씩 따로 패치하면 한 글자씩 밀리므로, 현재 빌드는 `이동공격마법소환치료명령`을 연속 스트림으로 씁니다. 첫 전투에서 사용 가능한 메뉴 `이동/공격/치료/명령` 표시를 확인했습니다.
- 지휘관 배치 메뉴는 일부 행이 일반 직접 문자열과 다르게 VRAM 타일 그래픽/다른 참조를 섞어 사용합니다. 2026-07-10 빌드 `BC63`에서 `지휘관배치`, `적군보기`, `출격`은 확인했고, 잔존 일본어 `移動順変更`은 VRAM tile `5A0-5B3`, `自動` 접두부는 `5B4-5B7`로 확인했습니다. 원본 ROM 평문 및 `0x0B0000` 그래픽 리소스 테이블에서는 해당 타일을 찾지 못했으므로 별도 압축/타일 경로 추적이 필요합니다.
- ROM 초반의 `SCENARIO` 시스템 메뉴 문자열은 `LOAD/SAVE/CONTINUE/SCENARIO/NOTHING` 테이블과 붙어 있고, `TURN` ASCII 문자열도 별도로 존재하지만, 둘 다 맵 위 `SCENARIO 1`/`TURN 1` 배너에는 영향을 주지 않았습니다. 해당 배너는 별도 타일/그래픽 경로로 봅니다.
- `0x97404` 이후 직접 문자열 후보는 렌더링상 캐릭터/몬스터명처럼 보이지만, 이름 화면의 실제 표시 테이블은 아니며 이름 확정 이후 진행과 충돌할 수 있습니다. 기본 빌드에서는 `UNSAFE_DIRECT_NAME_PATCHES`로 분리해 제외합니다.
- 클래스/용병/몬스터 이름 테이블은 별도 8비트 문자열 테이블입니다.
  - 포인터 테이블: `0x05E6D8`
  - 문자열 영역: `0x05E94A` 이후
  - 포인터는 `E953 0005`처럼 16비트 워드가 뒤집힌 형식이며 실제 주소는 `0x0005E953`입니다.
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
- 1장 조건 본문은 `볼도 처치`, `볼도 도주`, `A 패배`로 표시되며, 조건 화면 하단 세력 라벨은 현재 `P/E/NPC` 약어로 표시합니다.
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
