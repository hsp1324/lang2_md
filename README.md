# 랑그릿사 II 메가드라이브 한국어화

메가드라이브판 **랑그릿사 II 일본판**을 한국어로 즐길 수 있게 만드는 비공식 패치 프로젝트입니다.

프로젝트 개발자: **hsp1324**

> 최신 공개 버전은 `v1.2.0`입니다. 완성된 일반판과 하드판 ROM을
> 바로 내려받을 수 있으며, 직접 패치하는 방식도 함께 제공합니다.

## 가장 간단한 다운로드

원하는 버전을 받아 에뮬레이터에서 바로 실행합니다.

- [일반판 v1.2.0 ROM](https://github.com/hsp1324/lang2_md/releases/download/v1.2.0/Langrisser.II.Korean.v1.2.0.md)
- [하드판 T1.2.0 B1.2.0 ROM](https://github.com/hsp1324/lang2_md/releases/download/v1.2.0/Langrisser.II.Korean.Hard.T1.2.0.B1.2.0.md)

두 파일과 패처·BPS·검증값은 [v1.2.0 Release](https://github.com/hsp1324/lang2_md/releases/tag/v1.2.0)에서 한꺼번에 볼 수 있습니다.

## 일본판 ROM에 직접 패치하기

완성 ROM 대신 직접 패치하려면 다음 순서로 적용합니다.

1. [Langrisser-II-Korean-Patcher-v1.2.0.exe](https://github.com/hsp1324/lang2_md/releases/download/v1.2.0/Langrisser-II-Korean-Patcher-v1.2.0.exe)를 받습니다.
2. 패처를 일본판 ROM 또는 그 ROM이 든 ZIP과 같은 폴더에 둡니다.
3. 패처를 한 번 실행합니다.
4. 자동으로 찾지 못하면 파일 선택창에서 일본판 ROM이나 ZIP을 지정합니다.
5. 패치와 결과 검증이 끝나면 같은 폴더에 일반판과 하드판이 생성됩니다.

```text
Langrisser II (Korean v1.2.0).md
Langrisser II (Korean Hard T1.2.0 B1.2.0).md
```

패처는 원본 ROM과 ZIP을 덮어쓰지 않으며, 올바른 일본판인지 확인한 뒤
새 파일을 만듭니다. Python 설치는 필요하지 않습니다. macOS·Linux·Android에서는
Release에 함께 제공되는 BPS 패치를 호환 패처로 적용할 수도 있습니다.

## 필요한 원본 ROM

패처나 BPS로 직접 만들 때는 메가드라이브판 `Langrisser II (Japan)` ROM이 필요합니다.

지원하는 원본의 검증값은 다음과 같습니다.

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

다른 지역판, 이미 수정된 ROM, 손상된 덤프는 지원하지 않습니다. 512바이트 헤더가 붙은 덤프는 패처가 지원 여부를 별도로 확인합니다.

## 일반판과 하드판

- **일반판**: 원작에 가까운 난이도로 한국어화를 적용한 버전입니다.
- **하드판**: 같은 한국어화를 바탕으로 적 지휘관과 용병의 능력 및 구성을 강화한 버전입니다.

`v1.2.0` 결과 ROM의 검증값은 다음과 같습니다.

```text
일반판 SHA-256
1934476c9719cba1b4a53869aa2af3b1345a70456045f9d6ea2ce243eefb6d80

하드판 SHA-256
a6b4cb1fbad2d22fda9e8393fe80682d171ed5a6c817e6004f2edd05886e3a62
```

## 기존 세이브로 업데이트하기

기존 게임 내 저장인 `.srm`은 새 버전에서도 이어서 사용할 수 있습니다.
Windows 패처에서 기존 세이브를 선택하면 파일 이름을 직접 바꿀 필요가
없습니다.

1. 기존 버전에서 게임 내 저장을 합니다.
2. 에뮬레이터를 완전히 종료합니다.
3. 패처의 `기존 세이브(선택)`에서 `.srm` 파일을 지정합니다.
4. 세이브를 연결할 일반판 또는 하드판을 선택하고 패치를 시작합니다.
5. 패처가 기존 `.srm`을 그대로 보존하고, 같은 저장 폴더에 새 ROM과
   이름이 같은 `.srm`을 검증하여 복사합니다.
6. 새 ROM을 실행하고 게임 안의 `불러오기`로 저장을 엽니다.

예를 들어 새 ROM이 `Langrisser II (Korean v1.2.0).md`이면 다음 저장
파일이 생성됩니다.

```text
Langrisser II (Korean v1.2.0).srm
```

대상 이름에 다른 저장 파일이 이미 있으면 확인 없이 덮어쓰지 않습니다.

에뮬레이터의 상태 저장 파일(`.state`, `.state*`, `.gst`)은 ROM 내부 코드와 실행 중 메모리를 포함하므로 다른 빌드와의 호환을 보장하지 않습니다. 업데이트 후 문제가 보이면 상태 저장 대신 게임 내 저장인 `.srm`으로 다시 시작해 주세요.

자세한 절차는 [세이브를 유지하는 업데이트 안내](docs/save_preserving_rom_updates.md)를 참고하세요.

## 자주 생기는 문제

- **원본 ROM을 찾지 못함**: 패처와 일본판 ROM을 같은 폴더에 두거나 파일 선택창에서 직접 지정합니다.
- **지원하지 않는 ROM이라고 표시됨**: 일본판 여부와 위 SHA-256을 확인합니다.
- **업데이트 후 글자나 그림이 깨짐**: 이전 상태 저장을 사용하지 말고 게임 내 `.srm` 저장으로 불러옵니다.
- **세이브가 보이지 않음**: 패처에서 기존 `.srm`을 다시 연결하고 ROM과 `.srm`의 기본 파일명이 같은지 확인합니다.

## 문서

- [일반 사용자용 패치 배포 규격](docs/player_patch_distribution.md)
- [세이브를 유지하는 업데이트 안내](docs/save_preserving_rom_updates.md)
- [개발·빌드·분석·검증 상세 문서](docs/development_guide.md)
- [다른 환경에서 개발을 이어가기 위한 인수인계](HANDOFF.md)

개발용 빌드 명령, ROM 구조, 글꼴과 VRAM 분석, 시나리오별 검증 도구 및 실기 증거는 README에서 분리해 [개발 문서](docs/development_guide.md)에 보존했습니다.

## 주의

이 프로젝트의 한국어판은 원작 회사의 공식 제품이 아닌 비공식 한국어화판입니다.
