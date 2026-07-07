# Langrisser II Korean ROM Hack WIP

랑그릿사 II 메가드라이브 영어판을 기준으로 한국어화를 진행 중인 작업 폴더입니다.

## 필요한 파일

이 저장소는 ROM 바이너리를 추적하지 않습니다. 빌드하려면 작업 폴더 루트에 아래 파일을 직접 두어야 합니다.

- `Langrisser II (English).md`
- `Langrisser II (Japan).md`는 비교용이며 현재 빌드에는 필수는 아닙니다.

## 주요 파일

- `build_korean_complete_wip.py`: 현재 메인 빌더입니다.
- `build_korean_chapter1_natural_jamo.py`: 1장 자연스러운 한국어 대사 override가 들어 있습니다.
- `build_korean_machine_jamo.py`: VWF 대사 재배치와 한글 자모 인코딩 기반 코드입니다.
- `build_korean_machine_jamo_fixedfont.py`: 전투 대사 고정 폰트 패치 실험 코드입니다.
- `script_extract/english_records.json`: 추출한 영어 대사 레코드입니다.
- `script_extract/korean_records_google.json`: 기계 번역 기반 전체 대사 레코드입니다.
- `romhack_capture.py`: BlastEm 자동 입력/캡처 보조 스크립트입니다.

## 빌드

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

현재 확인된 기본 키:

- `Return`: Start
- `d`: C / 결정
- `s`: B / 취소

1장 진입 테스트 흐름:

```text
Start, Start, C, C(A 선택), Left, Up, C(Done), C
```

## 현재 상태

- 오프닝 일부 한글 출력 확인됨.
- 1장 준비 화면의 기본 항목은 한국어로 표시됩니다.
- 헤인, 전사, 워록, 솔저, 가드, 단검 등 1장 기본 이름 일부가 한국어로 표시됩니다.
- 조건 화면은 `승리조건`, `패배조건`을 한국어로 표시합니다.
- 전투 경로 메뉴의 `Arrange`, `Reorder`, `Auto-Arrange`, `Examine Enemy`, `Sortie`는 `배치`, `순서`, `자동`, `적군`, `출격`으로 표시됩니다.
- 이름 입력 화면은 고정 폰트 충돌을 피하기 위해 현재 `A`와 `Done`만 남기는 임시 표시 패치를 사용합니다.
- 전투 대사는 별도 고정 폰트 패치를 통해 본문 출력이 다시 동작합니다. 화자 이름 `Hein`은 `헤인` 전용 코드로 덮어씁니다.
- 상태창의 `LV`, `AT`, `DF`, `HP`, `MV`, `MP`, `Range`, `Adjust` 등은 영어 약어를 유지합니다.
- 명령 아이콘 `move/fight/guard/manual`이 한글 글자로 깨지는 문제를 막기 위해 고정 폰트 타일 `F4-F7`은 보호 대상으로 분리 중입니다.

## 주의할 점

- 준비/조건 화면, 전투 대사, 오프닝은 서로 다른 폰트/타일 렌더러를 사용합니다. ROM 용량만 늘린다고 모든 한글 출력 문제가 해결되지는 않습니다.
- 전투 대사 쪽은 별도 고정 폰트 경로를 타므로, VWF 한글 코드와 고정 폰트 타일 충돌을 같이 관리해야 합니다.
- `Battle Route`, `Prologue`, `Scenario`, `Turn` 같은 특수 제목/전투 하단 라벨은 일반 고정 폰트와 다른 경로가 섞여 있어 아직 별도 분석이 필요합니다.
- UI 슬롯이 매우 빡빡합니다. `아/중/립/금/고`처럼 일부 글자는 코드표 슬롯 대신 직접 고정 타일에 배치합니다.
- `!`, `?` 같은 문장부호는 대사 의미에 중요하므로 보존해야 합니다.
