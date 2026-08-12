# 일반 사용자용 GitHub 패치 배포

> 상태: **v1.3.7 공개 배포**. 아래 해시와 파일명은 공개 릴리스의 정확한
> 배포 계약이다. 2026-08-13 재배포본은 연속 저장 진행을 통과한 게임 로직을
> 유지하고 시나리오 1 대사와 로렌 맵 팔레트를 교정했으며, BPS 무결성을
> 재검사했다.

## 권장 사용자 흐름

일반 사용자는 GitHub Releases에서 Windows·Linux·macOS 중
자신의 운영체제와 CPU에 맞는 패처를 받아 일본판 ROM에 적용한다.

1. Windows는 `Langrisser-II-Korean-Patcher-v1.3.7.exe`, Linux와 macOS는
   README에 표시된 아키텍처별 압축 파일을 내려받는다.
2. 일본판 `Langrisser II` ROM 또는 해당 ROM이 든 ZIP과 같은 폴더에 둔다.
3. 패처를 실행한다.
4. 폴더에서 지원 원본을 자동으로 찾지 못했을 때만 파일 선택창으로 ROM을
   지정한다. 512바이트 헤더가 붙은 덤프와 ZIP 내부 파일도 검증한다.
5. 패처가 원작 디자인판, 최신 디자인 일반판, 최신 디자인 하드판을 각각 새
   파일로 만든다.

```text
Langrisser II (Korean Original v1.3.7).md
Langrisser II (Korean Normal v1.3.7).md
Langrisser II (Korean Hard v1.3.7).md
```

하드판의 번역 버전과 밸런스 버전은 모두 1.3.7이므로 파일명은
`Hard v1.3.7`로 간단히 표시한다. ROM 내부 메타데이터에는 T/B를 함께 남긴다.
원본 ROM, SRAM 저장, 에뮬레이터 상태 저장은 수정하지 않는다.
결과를 쓰기 전에 원본 해시를 확인하고, 임시 파일에 패치를 적용한 뒤 세 결과
해시까지 확인한 경우에만 최종 파일명으로 바꾼다.

## 지원 원본

v1.3.7 결과를 만드는 일본판 원본은 다음과 같다.

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

이 값과 일치하지 않는 ROM은 패치하지 않는다. 이미 수정된 ROM, 다른 지역판,
손상된 덤프에는 사용자가 이해할 수 있는 오류를 표시한다. 512바이트 헤더가
있는 덤프는 헤더를 제외한 내용이 위 해시와 일치할 때만 정규화한다.

## v1.3.7 배포 결과 검증값

```text
원작 디자인판
크기:    4,194,304 bytes
SHA-256: 604d022080ae701a8b2ff0dd9f6906143e1483a74be5ac4ba9f8a2cffa051bff

최신 디자인 일반판
크기:    4,194,304 bytes
SHA-256: 05f8ced0854b78b23eaf2c48b153d000fa56969cc5549a1d01df3dd86a19b32a

최신 디자인 하드판 (v1.3.7)
크기:    4,194,304 bytes
SHA-256: 1b5735c1b1b0620f8131c3291208f605d95a7e5293e63de36627b83f3a9001bd
```

패처는 세 결과를 각각 검증한다. 한 결과라도 다르면 생성된 임시 파일을 최종
파일로 승격하지 않는다. 게임 로직은 세 프로필의 1장부터 Fin까지 31개 장씩,
총 93개 연속 저장 진행을 통과한 직전 v1.3.7과 같고, 새 해시는 시나리오 1
대사와 로렌의 연보라 맵 팔레트 교정 및 BPS 왕복 검사를 반영한다.

## GitHub 저장소와 Release 구성

저장소 Git 이력에는 일본판 원본 또는 패치 완료 ROM을 커밋하지 않는다.
패처 소스와 다음 BPS 입력 자산은 저장소에서 관리하고 플랫폼 패처 안에
포함한다.

```text
README.md
patcher/
patches/
  v1.3.7.json
  original-v1.3.7.bps
  normal-v1.3.7.bps
  hard-v1.3.7.bps
.github/workflows/
  build-v1.3-patcher.yml
  build-v1.3-patcher-platforms.yml
```

v1.3.7 Release에는 다음 플랫폼 패처를 정확히 5개만 올린다.

```text
Langrisser-II-Korean-Patcher-v1.3.7.exe
Langrisser-II-Korean-Patcher-v1.3.7-linux-x86_64.tar.gz
Langrisser-II-Korean-Patcher-v1.3.7-linux-arm64.tar.gz
Langrisser-II-Korean-Patcher-v1.3.7-macos-arm64.app.zip
Langrisser-II-Korean-Patcher-v1.3.7-macos-x86_64.app.zip
```

세 BPS 파일과 manifest는 각 패처에 내장하므로 Release 자산으로 별도 업로드하지 않는다.
`SHA256SUMS*.txt`도 정확한 5개 계약에는 포함하지 않는다.
워크플로의 수동 preflight artifact와 로그에서 계산하고, 공개 후 GitHub API
digest와 실제 다운로드 SHA-256을 대조해 릴리스 기록에 남긴다. 일본판 원본
ROM과 개인 `.srm`, `.sav`, `.state`, `.gst` 파일도 Release에 포함하지 않는다.

## 404를 만들지 않는 배포 순서

1. 동결 ROM/BPS의 전체 회귀 검증을 끝내고 같은 해시로 다시 빌드한다.
2. 패치·manifest·패처 코드·두 플랫폼 워크플로를 `main`에 먼저 commit/push한다.
   GitHub의 `release: published` 이벤트는 워크플로가 기본 브랜치에 있어야
   실행된다.
3. 두 워크플로를 `workflow_dispatch`로 실행한다. Actions artifact에서 다섯
   패처를 내려받아 이름, SHA-256, PE/ELF/Mach-O 아키텍처, Linux 실행 권한,
   압축 무결성과 가능한 네이티브 `--self-test`를 확인한다.
4. v1.3.7 태그와 Release를 게시한다. 게시 이벤트로 실행된 두 워크플로가
   정확한 다섯 자산을 업로드한다.
5. `tools/verify_v137_release_assets.py`로 GitHub Release API의 자산 이름 집합이
   정확히 다섯 개인지 확인하고, 다섯 파일을 다시 내려받아 API digest와 실제
   SHA-256 및 컨테이너·아키텍처·권한·네이티브 self-test를 검증한다.
6. 다섯 URL이 모두 HTTP 200이고 크기가 0보다 크며 전체 검증이 통과한 뒤에만
   README의 최신 버전, 다운로드 링크, 사용 예시와 검증 문서를 v1.3.7로 바꿔
   push한다.

`release: published` 방식은 게시 직후 빌드가 끝나기 전까지 Release 화면에
자산이 아직 없는 짧은 구간이 생길 수 있다. 위 순서는 그동안 공개 README가
존재하지 않는 v1.3.7 파일을 가리켜 404를 내는 일을 막는다. Release 화면까지
무공백으로 공개해야 한다면 수동 preflight 산출물을 draft Release에 먼저
업로드해 실물을 검증한 뒤 게시하는 별도 절차를 사용한다.

## 단일 실행 패처 요구사항

패처는 별도의 Python 설치를 요구하지 않는 실행 파일 또는 앱으로 만든다.
다음 동작을 한 번의 실행에 포함한다.

- 실행 파일 옆에서 지원 원본을 자동 탐색하고, 없으면 파일 선택창을 연다.
- ZIP을 선택하면 지원 원본을 메모리에서 검증하며 ROM을 따로 추출하지 않는다.
- 원본 크기와 SHA-256을 검사한다.
- 원본을 덮어쓰지 않고 세 버전의 BPS를 각각 적용한다.
- 출력 크기와 SHA-256을 확인한다.
- 성공한 세 파일의 위치와 검증값을 표시한다.
- 이미 같은 이름의 결과가 있으면 사용자 확인 없이 덮어쓰지 않는다.
- 어느 단계에서 실패해도 원본과 기존 결과 파일을 그대로 둔다.
- 기존 한국어판 `.srm`을 선택하면 원본 저장을 보존한 채 새 ROM 이름으로
  검증 복사한다. 대상 이름에 다른 저장이 있으면 덮어쓰지 않는다.

`patcher/langrisser_ii_korean_patcher.py`가 이 사용자 흐름을 구현한다.
`--self-test`는 내장 manifest와 세 BPS의 크기·해시·BPS 체크섬을 검사하고,
일본판 ROM을 함께 지정하면 세 결과를 실제로 적용해 최종 해시까지 확인한다.

## 저장 파일 안내

ROM 업데이트 전에 게임 안에서 저장하고 에뮬레이터를 완전히 종료한다.
SRAM 기반 `.srm`은 ROM 파일명과 맞춰 계속 사용할 수 있다. 상태 저장은 새
코드 주소와 호환을 보장하지 않으므로 다른 ROM 해시로 옮기지 않는다. 이전
상태 저장을 불러온 뒤 보이는 문제는 새 ROM 자체의 검증 결과로 취급하지
않는다.

자세한 기존 한국어판 업데이트와 롤백 절차는
[`save_preserving_rom_updates.md`](save_preserving_rom_updates.md)를 따른다.
