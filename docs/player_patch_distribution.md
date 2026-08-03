# 일반 사용자용 GitHub 패치 배포

## 권장 사용자 흐름

Windows 사용자는 GitHub Releases에서 단일 패처를 내려받아 일본판 ROM과
같은 폴더에서 한 번 실행하는 것을 기본 흐름으로 삼는다.

1. `Langrisser-II-Korean-Patcher-v1.2.0.exe`를 내려받는다.
2. 일본판 `Langrisser II` ROM 또는 해당 ROM이 든 ZIP과 같은 폴더에 둔다.
3. 패처를 실행한다.
4. 폴더에서 지원 원본을 자동으로 찾지 못했을 때만 파일 선택창으로 ROM을
   지정한다. 512바이트 헤더가 붙은 덤프와 ZIP 내부 파일도 검증한다.
5. 패처가 일반판과 하드판을 각각 새 파일로 만든다.

```text
Langrisser II (Korean v1.2.0).md
Langrisser II (Korean Hard T1.2.0 B1.2.0).md
```

원본 ROM, SRAM 저장, 에뮬레이터 상태 저장은 수정하지 않는다. 결과를 쓰기
전에 원본 해시를 확인하고, 임시 파일에 패치를 적용한 뒤 결과 해시까지
확인한 경우에만 최종 파일명으로 바꾼다.

## 지원 원본

현재 1.2.0 결과를 만들 때 사용한 일본판 원본은 다음과 같다.

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

이 값과 일치하지 않는 ROM은 패치하지 않는다. 이미 수정된 ROM, 다른 지역판,
손상된 덤프에는 사용자가 이해할 수 있는 오류를 표시한다. 512바이트 헤더가
있는 덤프를 지원하려면 헤더를 제외한 내용이 위 해시와 일치할 때만 자동으로
정규화한다.

## 1.2.0 결과 검증값

```text
일반판
크기:    4,194,304 bytes
SHA-256: 1934476c9719cba1b4a53869aa2af3b1345a70456045f9d6ea2ce243eefb6d80

하드판
크기:    4,194,304 bytes
SHA-256: a6b4cb1fbad2d22fda9e8393fe80682d171ed5a6c817e6004f2edd05886e3a62
```

패처는 두 결과를 각각 검증한다. 한 결과라도 다르면 생성된 임시 파일을 최종
파일로 승격하지 않는다.

## GitHub 저장소와 Release 구성

저장소에는 원본 또는 패치 완료 ROM을 커밋하지 않는다. 패처 소스, BPS,
사용법, 라이선스와 검증값만 관리한다.

```text
README.md
patcher/
patches/
  normal-v1.2.0.bps
  hard-t1.2.0-b1.2.0.bps
.github/workflows/build-v1.2-patcher.yml
```

`v1.2.0` Release에는 다음 파일을 올린다.

```text
Langrisser-II-Korean-Patcher-v1.2.0.exe
SHA256SUMS.txt
```

BPS를 직접 적용하려는 고급 사용자용으로 두 `.bps` 파일을 별도 자산으로
제공한다. 전체 일본판 ROM, 완성 ROM, 개인 `.srm`, `.sav`, `.state`,
`.gst` 파일은 Release에 포함하지 않는다.

## 단일 실행 패처 요구사항

패처는 별도의 Python 설치나 명령 프롬프트를 요구하지 않는 단일 Windows
실행 파일로 만든다. 다음 동작을 한 번의 실행에 포함한다.

- 실행 파일 옆에서 지원 원본을 자동 탐색하고, 없으면 파일 선택창을 연다.
- ZIP을 선택하면 지원 원본을 메모리에서 검증하며 ROM을 따로 추출하지 않는다.
- 원본 크기와 SHA-256을 검사한다.
- 원본을 덮어쓰지 않고 일반판과 하드판 BPS를 각각 적용한다.
- 출력 크기와 SHA-256을 확인한다.
- 성공한 두 파일의 위치를 표시하고 폴더 열기 버튼을 제공한다.
- 이미 같은 이름의 결과가 있으면 사용자 확인 없이 덮어쓰지 않는다.
- 어느 단계에서 실패해도 원본과 기존 결과 파일을 그대로 둔다.
- 기존 한국어판 `.srm`을 선택하면 원본 저장을 보존한 채 새 ROM 이름으로
  검증 복사한다. 대상 이름에 다른 저장이 있으면 덮어쓰지 않는다.

`patcher/langrisser_ii_korean_patcher.py`가 이 사용자 흐름을 구현한다.
현재 `tools/rom_update.py`에는 BPS 생성·적용과 CRC 검증 코드가 있고,
`tools/build_rom_update_package.py`에는 manifest와 업데이트 ZIP 생성 경로가
있다. 같은 모듈의 `migrate-save` 명령은 기존 게임 내 저장을 새 ROM
파일명으로 원자적 복사하고 원본 해시를 재검증한다. 단일 실행 배포기는
이 검증 로직을 PyInstaller 단일 실행 파일로 감싸 일본판 2 MiB 원본에서
4 MiB 일반판·하드판 두 결과를 생성한다.

## 저장 파일 안내

ROM 업데이트 전에 게임 안에서 저장하고 에뮬레이터를 완전히 종료한다.
SRAM 기반 `.srm`은 ROM 파일명과 맞춰 계속 사용할 수 있다. 상태 저장은
ROM 코드 주소와 실행 중 메모리를 포함하므로 다른 빌드에서 호환을 보장하지
않는다. 이전 상태 저장을 불러온 뒤 보이는 문제는 새 ROM 자체의 검증 결과로
취급하지 않는다.

자세한 기존 한국어판 업데이트와 롤백 절차는
[`save_preserving_rom_updates.md`](save_preserving_rom_updates.md)를 따른다.
