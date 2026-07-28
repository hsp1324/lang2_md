# 세이브를 유지하는 한국어판 ROM 업데이트

## 보장 범위

한국어 오탈자나 글리프 문제를 수정한 새 ROM을 배포할 때 플레이어의
게임 내 저장을 유지하기 위한 절차다.

- 업데이트 도구는 ROM 파일만 읽고 교체한다.
- `.srm`, `.sram`, `.sav`, `.state*`, `.gst` 파일은 열거나 수정하지 않는다.
- 기존 ROM과 정확히 같은 경로와 파일명을 유지한다. 파일명으로 SRAM을
  연결하는 RetroArch 등의 에뮬레이터가 기존 저장을 그대로 찾을 수 있다.
- 교체 전 ROM은 같은 폴더의
  `원래이름.md.before-새버전.bak`에 보관한다.
- 지원하는 이전 ROM의 SHA-256과 BPS CRC32가 모두 맞아야 쓸 수 있다.
- 새 ROM은 임시 파일에서 SHA-256, MD 헤더 체크섬, 크기, SRAM 설명자를
  검증한 뒤 `os.replace`로 원자적으로 교체한다.
- 교체 후 검증이 실패하면 `.bak`에서 원래 ROM을 자동 복구한다.

이 보장은 **게임 내 저장(SRAM)** 에 적용된다. 에뮬레이터 상태 저장은
CPU, RAM, 실행 중인 코드 주소를 포함할 수 있으므로 새 ROM과의 호환을
보장하지 않는다. 업데이트 전 게임 안에서 저장하고 에뮬레이터를 완전히
종료해야 한다.

현재 세이브 형식 ID는 `lang2-ko-sram-v1`이다. 이전 ROM과 새 ROM은
다음 12바이트 MD SRAM 헤더도 같아야 한다.

```text
5241F8200040000100403FFF
```

패키지 빌더는 ROM 크기, 이 설명자 또는 세이브 형식 ID가 바뀌면 패키지
생성을 거부한다. 저장 구조를 바꿔야 한다면 형식 ID를 올리고 별도의
검증된 SRAM 변환기를 먼저 만들어야 한다.

## 플레이어 사용법

### Windows

1. 게임 안에서 저장하고 에뮬레이터를 완전히 종료한다.
2. 배포 ZIP을 푼다.
3. 사용 중인 `Langrisser II (Korean).md`를 `apply_update.bat` 위로
   끌어 놓는다.
4. 출처 버전과 대상 버전을 확인하고 `y`를 입력한다.
5. 기존 게임 내 저장을 불러온다. 상태 저장은 불러오지 않는다.

Python 3가 필요하다. 먼저 쓰기 없이 검증하려면 다음 명령을 사용한다.

```powershell
py -3 apply_update.py apply --package . `
  --rom "C:\Games\Langrisser II (Korean).md" --dry-run
```

### Linux와 macOS

```bash
./apply_update.sh "/games/Langrisser II (Korean).md"
```

### Android RetroArch

1. 게임 안에서 저장하고 RetroArch를 완전히 종료한다.
2. 기존 ROM을 다른 폴더에 백업한다.
3. 패키지의 `patches/`에서 자신의 이전 버전에 맞는 `.bps`를 일반 BPS
   패처로 적용한다.
4. 결과 ROM을 기존 ROM과 **완전히 같은 경로와 파일명**으로 둔다.
5. RetroArch 저장 폴더의 기존 `.srm`은 그대로 둔다.

모바일 BPS 앱이 결과 이름에 `(patched)` 등을 붙이면 기존 SRAM과
연결되지 않을 수 있다. 이 경우 결과 ROM의 이름만 기존 이름으로
되돌린다. 기존 ROM 백업은 `.md.bak`처럼 에뮬레이터가 게임으로 스캔하지
않는 확장자를 사용한다.

## 개발자 릴리스 절차

### 1. 현재 배포 ROM 보관

ROM 바이너리는 Git에서 추적하지 않는다. 수정 전에 현재 등록된 배포본을
로컬 보관해야 BPS 기준 파일을 잃지 않는다.

```bash
python3 tools/archive_rom_release.py
```

현재 `localization/rom_update_releases.json`의 `ko-99fd`를 검증하고 다음
경로에 보관한다.

```text
roms/releases/Langrisser II (Korean ko-99fd).md
```

보관 경로도 `.gitignore` 대상이다. 같은 해시의 파일이 이미 있으면
명령은 아무것도 덮어쓰지 않고 성공한다. 다른 내용이 있으면 중단한다.

### 2. 수정·빌드·회귀 검증

한국어화를 수정하고 정상 배포 ROM을 다시 만든다. 기존
`release_acceptance.py`와 관련 실기 검증을 통과시킨 뒤 새 릴리스 ID를
정한다. 릴리스 ID 예시는 `ko-2026.08.01.1`이다.

### 3. 업데이트 패키지 생성

```bash
python3 tools/build_rom_update_package.py \
  --target-rom "roms/builds/Langrisser II (Korean).md" \
  --target-release ko-2026.08.01.1 \
  --source \
    "ko-99fd=roms/releases/Langrisser II (Korean ko-99fd).md" \
  --output "dist/Langrisser-II-Korean-ko-2026.08.01.1-update.zip"
```

여러 이전 배포본을 한 번에 지원하려면 `--source`를 반복한다. 패키지는
각 SHA-256에 맞는 BPS를 자동 선택한다. ZIP에는 전체 ROM이 들어가지
않으며 다음 파일만 들어간다.

```text
update.json
patches/*.bps
apply_update.py
apply_update.bat
apply_update.sh
README_KO.txt
RELEASE_NOTES_KO.txt  # --release-notes를 지정한 경우
```

### 4. 실제 이전 배포본으로 최종 검사

복사본에서만 실행한다.

```bash
cp "roms/releases/Langrisser II (Korean ko-99fd).md" /tmp/update-test.md
python3 tools/rom_update.py apply \
  --package "dist/Langrisser-II-Korean-ko-2026.08.01.1-update.zip" \
  --rom /tmp/update-test.md --yes
sha256sum /tmp/update-test.md
```

새 ROM 해시가 `update.json`의 대상 해시와 같고, 원래 ROM이 `.bak`으로
남으며, 테스트용 `.srm`의 해시가 전후 동일한지 확인한다.

### 5. 릴리스 목록 갱신

배포가 확정된 뒤 `localization/rom_update_releases.json`에 새 레코드를
추가하고 `current_release`를 새 ID로 바꾼다. 이전 레코드는 삭제하지
않는다. 다음 패치가 그 해시를 지원하는 근거가 된다.

## 자동 테스트

```bash
python3 -m unittest tests.test_rom_update -v
```

테스트는 BPS 네 동작의 해석, 잘못된 원본·손상 패치 거부, dry-run,
중복 적용, SRAM 헤더 변경 거부, 원자적 같은 이름 교체, ROM 백업,
`.srm/.sav/.state/.gst` 바이트 불변, 현재 릴리스 등록값을 검사한다.
