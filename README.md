# 랑그릿사 II 메가드라이브 한국어화

메가드라이브판 **랑그릿사 II 일본판**을 한국어로 즐길 수 있게 만드는 비공식 패치 프로젝트입니다.

프로젝트 개발자: **hsp1324**

> 최신 공개 버전은 `v1.3.8`입니다. 세 가지 완성판은
> GitHub Releases의 Windows·Linux·macOS 패처로 일본판 ROM에 적용해 사용합니다.
> 동작은 `RetroArch`(Genesis Plus GX 기준) 환경에서 검증되었으므로 우선적으로
> `RetroArch` 사용을 권장합니다.

## 가장 간단한 다운로드

사용 중인 운영체제와 CPU에 맞는 패처를 받아 일본판 ROM에 적용합니다.

- **Windows**: [Langrisser-II-Korean-Patcher-v1.3.8.exe](https://github.com/hsp1324/lang2_md/releases/download/v1.3.8/Langrisser-II-Korean-Patcher-v1.3.8.exe)
- **Linux x86_64**: [Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64.tar.gz](https://github.com/hsp1324/lang2_md/releases/download/v1.3.8/Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64.tar.gz)
- **Linux ARM64**: [Langrisser-II-Korean-Patcher-v1.3.8-linux-arm64.tar.gz](https://github.com/hsp1324/lang2_md/releases/download/v1.3.8/Langrisser-II-Korean-Patcher-v1.3.8-linux-arm64.tar.gz)
- **macOS Apple Silicon**: [Langrisser-II-Korean-Patcher-v1.3.8-macos-arm64.app.zip](https://github.com/hsp1324/lang2_md/releases/download/v1.3.8/Langrisser-II-Korean-Patcher-v1.3.8-macos-arm64.app.zip)
- **macOS Intel**: [Langrisser-II-Korean-Patcher-v1.3.8-macos-x86_64.app.zip](https://github.com/hsp1324/lang2_md/releases/download/v1.3.8/Langrisser-II-Korean-Patcher-v1.3.8-macos-x86_64.app.zip)

검증값은 [v1.3.8 Release](https://github.com/hsp1324/lang2_md/releases/tag/v1.3.8)에서 확인할 수 있습니다.

### v1.3.8 변경 사항

- 최신 디자인 일반판과 하드판의 로렌 하이로드 맵 외형을 연보라가 아닌
  **밝은 빨강 → 짙은 빨강** 두 단계 그라데이션으로 변경했습니다. 방패·장식·
  검·원작 디자인판은 건드리지 않았습니다. 에디터의 로렌 미리보기도 같은
  빨강 명암과 따뜻한 하이라이트로 맞췄습니다.

- 키스·레스터·제시카가 아군으로 합류할 때 목표 레벨을 강제로 맞추는 대신
  원작 2단계 레벨에 해당하는 고정 경험치량을 한 번만 받도록 수정했습니다.
  선택한 클래스의 경험치 게이지 길이에 따라 최종 레벨과 남은 경험치가
  자연스럽게 달라지며 Original·Normal·Hard의 지급량은 같습니다.
- 레스터의 시나리오 10 합류 직후 `나이트 / 크로코로드 / 샤먼` 전직 선택이
  생략되던 경우와, 일반 타이틀의 LOAD에서 예전 임시 시나리오 값 때문에
  합류 복구·룬스톤 선택이 잘못 판정될 수 있던 문제를 수정했습니다.
- 하드판에서 사망하면 패배하는 리아나·사제·주민·NPC 지휘관·제시카 19명의
  방어력을 해당 장의 적 공격 강화분만큼 보정했습니다. 이름·클래스·레벨·
  공격력·위치·AI·용병 구성은 유지합니다.
- 시나리오 14의 레온·엘윈 대사 뒤 빈 창, 엔딩의 스콧·아론·제시카 문장 분리,
  제보된 대사 175건 가운데 의미나 조사가 명확히 잘못된 48건을 수정했습니다.
- 시나리오 1의 레아드·레온·제국군 지휘관 대사 6건을 문맥에 맞게 추가
  교정했습니다. `자경단가` 조사는 `자경단이`로 표시됩니다.
- Original·Normal·Hard를 각각 1장부터 비밀 시나리오를 포함한 마지막 27장과
  Fin 화면까지 연속 저장 진행해 총 93개 장별 진행을 확인했습니다. 더 확장된
  재검증은 계속합니다. 1.3.8은 이 검증본의 게임 로직을 유지하고 로렌의
  최신 디자인 맵 팔레트만 빨간색 명암으로 교정했습니다.

### v1.3.6에서 포함된 수정

- 키스의 호크로드 공격모션이 시스터로 나오고, 맵 외형·능력치·경험치바가
  드래곤나이트 것으로 나오던 오류를 수정했습니다. 호크로드는 이제 키스의
  비행 탑승 전투모션과 전용 맵 디자인, 올바른 성장 데이터를 사용합니다.
- 같은 원인이 있던 레스터의 크로코로드도 뱀파이어 전투모션과 잘못된
  서펜나이트 데이터를 사용하지 않도록 함께 수정했습니다.
- 룬스톤을 어느 단계에서 사용해도 키스는 `로드 / 호크로드 / 힐러`,
  레스터는 `나이트 / 크로코로드 / 샤먼`, 제시카는
  `힐러 / 소서러 / 로드`의 2단계 선택창으로 돌아갑니다.
- 격리된 BlastEm 가상 화면에서 세 인물의 2·3·4·5단계 총 12개 상태에
  실제 룬스톤을 장착·소모해 선택창과 LV1 초기화를 확인했습니다. 키스와
  레스터는 5단계에서 호크로드·크로코로드를 직접 골라 적용했고, 키스의
  실제 전투 화면도 확인했습니다.
- v1.3.5까지의 합류 시점 전직, 파이터 LV11·12 구 세이브 복구, 시나리오
  1~31 및 하드 밸런스 수정은 그대로 포함합니다.

## 세 가지 버전

- **원작 디자인판(Original)**: 원작의 맵 캐릭터 디자인과 밸런스를 유지하고 한국어화와 키스·레스터·제시카 합류 진행 수정을 적용합니다.
- **최신 디자인 일반판(Normal)**: New 디자인의 최신 사용자 디자인과 한국어화를 적용하며 난이도는 원작 기준입니다.
- **최신 디자인 하드판(Hard)**: 최신 사용자 디자인과 한국어화에 적 지휘관·용병 강화 밸런스를 더합니다.

패처는 일본판 ROM 또는 ZIP 하나를 고르면 위 세 ROM을 모두 생성합니다.

```text
Langrisser II (Korean Original v1.3.8).md
Langrisser II (Korean Normal v1.3.8).md
Langrisser II (Korean Hard v1.3.8).md
```

## Windows에서 패치하기

EXE를 실행하고 일본판 ROM 또는 ZIP, 결과 폴더를 고른 뒤 `패치 시작`을
누릅니다. 기존 게임 내 저장을 새 ROM 이름으로 연결하려면 `.srm` 파일과
대상 버전도 함께 고릅니다.

## Linux에서 패치하기

사용 중인 CPU에 맞는 `linux-x86_64.tar.gz` 또는 `linux-arm64.tar.gz`를
받아 압축을 풉니다. 파일 관리자에서 실행하거나 터미널에서 다음과 같이
실행합니다.

```bash
tar -xzf Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64.tar.gz
chmod +x Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64
./Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64
```

화면 없이 명령줄로도 실행할 수 있습니다.

```bash
./Langrisser-II-Korean-Patcher-v1.3.8-linux-x86_64 \
  --rom "/path/to/Langrisser II (Japan).md" \
  --output-dir "/path/to/output"
```

ARM64에서는 명령의 파일명을 `Langrisser-II-Korean-Patcher-v1.3.8-linux-arm64`로
바꿉니다.

## macOS에서 패치하기

M1 이후 Mac은 `macos-arm64.app.zip`, Intel Mac은 `macos-x86_64.app.zip`을
받습니다. ZIP을 풀고 `Langrisser II Korean Patcher v1.3.8.app`을 실행합니다.
이 패처는 Apple Developer ID로 공증되지 않았으므로 처음 한 번은 Finder에서
앱을 오른쪽 클릭한 뒤 `열기`를 선택해야 할 수 있습니다. macOS 보안을
전체적으로 끄지는 마세요.

터미널에서 실행하려면 앱 내부 실행 파일을 사용합니다.

```bash
"./Langrisser II Korean Patcher v1.3.8.app/Contents/MacOS/Langrisser II Korean Patcher v1.3.8" \
  --rom "/path/to/Langrisser II (Japan).zip" \
  --output-dir "/path/to/output" \
  --save "/path/to/old-save.srm" \
  --save-target normal
```

Linux와 macOS 모두 일본판 ROM이 ZIP 안에 있어도 `--rom`에 ZIP 경로를
지정할 수 있습니다. `--save-target`은 `pure`, `normal`, `hard` 중
하나입니다. 상태 저장 파일이 아니라 게임 안에서 저장한 `.srm`을 사용해야
합니다.

## 게임 데이터 에디터 사용법

에디터에서는 31개 시나리오의 배치·클래스·LV·AT·DF·용병, 아이템의
가격과 효과, 10명 지휘관의 실제 시작 클래스와 클래스 체인지 경로,
전직 용병 해금을 브라우저에서 수정할 수 있습니다. `클래스 수정` 탭에서는
지휘관 클래스의 MV·용병 A+/D+, LV1~10 MP/AT/DF 성장, 레벨업 때 배우는
마법·소환과 공통 습득 레벨도 바꿀 수 있습니다.

먼저 저장소를 내려받습니다.

```bash
git clone https://github.com/hsp1324/lang2_md.git
cd lang2_md
```

다음 두 ROM을 아래 경로에 둡니다. 폴더가 없으면 직접 만듭니다.

```text
roms/builds/Langrisser II (Korean).md
roms/original/Langrisser II (Japan).md
```

첫 번째 파일에는 Release에서 받은 일반판 ROM을 복사해 사용합니다.
두 번째 일본판 ROM은 에디터가 원본 이름·클래스·그래픽을 대조하는 기준
자료로 사용합니다. 현재 에디터의 편집 ROM 생성은 일반판을 기준으로 하며,
하드판을 기준으로 직접 편집하는 기능은 제공하지 않습니다.

Windows에서는 다음 명령으로 실행합니다.

```powershell
py -m pip install Pillow
py editor/server.py
```

macOS·Linux에서는 다음 명령을 사용합니다.

```bash
python3 -m pip install Pillow
python3 editor/server.py
```

브라우저에서 `http://127.0.0.1:8765`를 열고 원하는 값을 수정한 다음
오른쪽 위의 `편집 ROM 빌드`를 누릅니다. 기준 ROM은 덮어쓰지 않으며 다음
파일이 생성됩니다.

```text
roms/builds/Langrisser II (Korean Editor Edit).md
```

`클래스 체인지`에서 1단계의 경로 출발 클래스를 바꾸면 새 게임·최초 합류에
쓰는 실제 시작 클래스도 함께 바뀝니다. 별도의 `실제 시작 클래스` 선택기로
이미 경로에 있는 상위 클래스부터 시작하게 할 수도 있습니다. 기존 `.srm`에
이미 생성된 지휘관은 초기 로스터 변경이 소급되지 않으므로 새 게임에서
확인해 주세요. 단, 정식 v1.3.7 ROM은 공개 v1.3.1~v1.3.3 구 세이브의 키스·레스터가
파이터 레벨 10 이상에서 막힌 경우를 게임 안에서 자동 복구합니다. `다음 클래스`를
바꾸면 해당 클래스만 교체되며 그 뒤에
연결된 기존 전직 선택지는 유지됩니다.

`클래스 체인지 → New 디자인`의 16×16 디자인 편집 결과는 현재 편집 ROM에
자동 적용되지 않습니다. 시나리오 배치의 클래스 ID만 바꾸는 작업도 이미
저장된 런타임 마법·소환 권한을 자동 재계산하지 않습니다. 마법·소환 습득 규칙은
`클래스 수정` 탭에서 별도로 지정합니다. 자세한 구조와 제한은
[게임 데이터 편집기 구조](docs/editor_data_model.md)를 참고하세요.

## 기존 세이브로 업데이트하기

기존 게임 내 저장인 `.srm`은 새 버전에서도 이어서 사용할 수 있습니다.

1. 기존 버전에서 게임 내 저장을 합니다.
2. 에뮬레이터를 완전히 종료합니다.
3. 기존 `.srm` 파일을 복사하여 원본을 보존합니다.
4. 복사본의 기본 파일명을 새 ROM과 똑같이 맞춥니다.
5. 새 ROM을 실행하고 게임 안의 `불러오기`로 저장을 엽니다.

예를 들어 새 ROM이 `Langrisser II (Korean Normal v1.3.8).md`이면 다음 저장
파일이 생성됩니다.

```text
Langrisser II (Korean Normal v1.3.8).srm
```

에뮬레이터의 상태 저장 파일(`.state`, `.state*`, `.gst`)은 ROM 내부 코드와 실행 중 메모리를 포함하므로 다른 빌드와의 호환을 보장하지 않습니다. 업데이트 후 문제가 보이면 상태 저장 대신 게임 내 저장인 `.srm`으로 다시 시작해 주세요.

자세한 절차는 [세이브를 유지하는 업데이트 안내](docs/save_preserving_rom_updates.md)를 참고하세요.

## 자주 생기는 문제

- **업데이트 후 글자나 그림이 깨짐**: 이전 상태 저장을 사용하지 말고 게임 내 `.srm` 저장으로 불러옵니다.
- **세이브가 보이지 않음**: ROM과 `.srm`의 기본 파일명이 같은지, 해당 에뮬레이터 코어의 저장 폴더에 있는지 확인합니다.
- **실행 불가/동작 불안정**: 현재 이 패치 빌드는 `RetroArch`(Genesis Plus GX 기준)에서
  정상 동작을 기준으로 검증했습니다. 일부 `Gens` 계열 에뮬레이터는
  장면 전환/입력 처리에서 오류가 보고되었으므로, 동작이 안 되면
  `RetroArch` 환경에서 재시도해 주세요.

## 문서

- [v1.3.8 상세 검증 기록](docs/v1.3.8_validation.md)
- [v1.3.8 패치 배포 안내](docs/player_patch_distribution_v1.3.8.md)
- [세이브를 유지하는 업데이트 안내](docs/save_preserving_rom_updates.md)
- [게임 데이터 편집기 구조](docs/editor_data_model.md)
- [개발·빌드·분석·검증 상세 문서](docs/development_guide.md)
- [다른 환경에서 개발을 이어가기 위한 인수인계](HANDOFF.md)

개발용 빌드 명령, ROM 구조, 글꼴과 VRAM 분석, 시나리오별 검증 도구 및 실기 증거는 README에서 분리해 [개발 문서](docs/development_guide.md)에 보존했습니다.

## 주의

이 프로젝트의 한국어판은 원작 회사의 공식 제품이 아닌 비공식 한국어화판입니다.
