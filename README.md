# Langrisser II Korean ROM Hack WIP

랑그릿사 II 메가드라이브 한국어화를 진행 중인 작업 폴더입니다.

초기 작업은 영어판 고정 폰트를 기준으로 진행했지만, 슬롯 충돌이 많아 일본판의 16x16 glyph 로딩 시스템을 분석하는 방향으로 전환했습니다. 일본판은 각 텍스트 레코드가 사용할 glyph 목록을 먼저 VRAM에 올리고, 본문은 그 목록의 로컬 인덱스를 참조합니다.

## 필요한 파일

이 저장소는 ROM 바이너리를 추적하지 않습니다. 빌드하려면 작업 폴더 루트에 아래 파일을 직접 두어야 합니다.

- `Langrisser II (English).md`
- `Langrisser II (Japan).md`

## 주요 파일

- `build_korean_jp_probe.py`: 현재 우선 진행 중인 일본판 텍스트/glyph 시스템 기반 빌더입니다.
- `build_korean_complete_wip.py`: 영어판 고정 폰트 기반 초기 실험 빌더입니다.
- `tools/jp_text_font_analyzer.py`: 일본판 16비트 텍스트 스트림, glyph 목록, `0x40000` JP font 포맷을 오프라인 분석/렌더링하는 도구입니다.
- `build_korean_chapter1_natural_jamo.py`: 1장 자연스러운 한국어 대사 override가 들어 있습니다.
- `build_korean_machine_jamo.py`: VWF 대사 재배치와 한글 자모 인코딩 기반 코드입니다.
- `build_korean_machine_jamo_fixedfont.py`: 전투 대사 고정 폰트 패치 실험 코드입니다.
- `script_extract/english_records.json`: 추출한 영어 대사 레코드입니다.
- `script_extract/korean_records_google.json`: 기계 번역 기반 전체 대사 레코드입니다.
- `romhack_capture.py`: BlastEm 자동 입력/캡처 보조 스크립트입니다.

## 빌드

일본판 기반 probe:

```bash
python3 build_korean_jp_probe.py
```

출력 파일:

```text
Langrisser II (Korean JP Probe).md
```

기존 영어판 기반 WIP:

```bash
python3 build_korean_complete_wip.py
```

출력 파일:

```text
Langrisser II (Korean Complete WIP).md
```

## 실행

BlastEm이 `tools/blastem/`에 있는 경우:

```bash
env LD_LIBRARY_PATH=tools/blastem/lib tools/blastem/blastem "Langrisser II (Korean Complete WIP).md"
```

일본판 기반 probe를 실행하려면 ROM 이름만 바꿉니다.

```bash
env LD_LIBRARY_PATH=tools/blastem/lib tools/blastem/blastem "Langrisser II (Korean JP Probe).md"
```

현재 확인된 기본 키:

- `Return`: Start
- `d`: C / 결정
- `s`: B / 취소

영어판 기반 WIP의 1장 진입 테스트 흐름:

```text
Start, Start, C, B(A 선택), Left, Up, C(Done), C
```

일본판 기반 probe에서는 이름 입력 화면의 기본 이름을 그대로 쓸 수 있으므로 이름 화면에서 `Start`를 누르면 바로 진행됩니다.

```text
Start(컷신 스킵), Start(타이틀), C, Start(이름 확정), C
```

## 현재 상태

### 일본판 기반 새 방향

- 일본판 텍스트 포인터 테이블을 확인했습니다.
  - 조건 화면: 포인터 테이블 `0x98D7A`, glyph 목록 테이블 `0x986C6`
  - 시나리오 설명: 포인터 테이블 `0x9CF7C`, glyph 목록 테이블 `0x9B2FC`
- 일본판 glyph 원본은 `0x40000`부터 시작하며, glyph 1개는 64바이트입니다.
- 실제 변환은 ROM의 `0x2C390` 루틴과 일치합니다. 각 glyph는 16비트 행 32개를 2bpp 8x8 타일 4개로 변환하고, 화면에서는 2x2 타일로 배치됩니다.
- `tools/jp_text_font_analyzer.py`로 에뮬레이터 실행 없이 원문/폰트/패치 결과를 이미지로 확인할 수 있습니다.
- `build_korean_jp_probe.py`는 일본판 ROM에 한글 glyph를 `0x260` 이후 슬롯에 넣고, 시나리오 설명/조건 화면/직접 문자열 일부를 한국어로 바꾸는 프로토타입입니다.
- 직접 문자열 중 일부는 `FFFF` 종료 문자열이 아니라 고정 길이 문자열입니다. 예: `0x97034=兵士配属`, `0x9703C=アイテム装備`, `0x97048=ショップ`, `0x97050=指揮官配置`.
- 현재 일본판 기반 probe에서 준비 메뉴 `용병고용`, `장비착용`, `상점`, `지휘관배치`, 상점 `구입/판매/취소`, 전투 명령 `이동/공격/마법/소환/치료/명령`을 고정 길이 패치로 처리합니다.

분석 예시:

```bash
python3 tools/jp_text_font_analyzer.py report --samples 2
python3 tools/jp_text_font_analyzer.py render-text --table scenarios --index 0 --base 0x40000 --format jp2bpp16 --mapped --cols 18 --scale 4
python3 tools/jp_text_font_analyzer.py --rom "Langrisser II (Korean JP Probe).md" render-text --table conditions --index 0 --base 0x40000 --format jp2bpp16 --mapped --cols 18 --scale 4
python3 tools/jp_text_font_analyzer.py render-direct-strings --start 0x97000 --end 0x97800 --scale 3
```

### 영어판 기반 WIP

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
