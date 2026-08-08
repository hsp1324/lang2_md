# 랑그릿사 II 메가드라이브 한국어화

메가드라이브판 **랑그릿사 II 일본판**을 한국어로 즐길 수 있게 만드는 비공식 패치 프로젝트입니다.

프로젝트 개발자: **hsp1324**

> 최신 공개 버전은 `v1.3.2`입니다. 세 가지 완성판은
> GitHub Releases의 패처(EXE)로 일본판 ROM에 적용해 사용합니다.  
> 동작은 `RetroArch`(Genesis Plus GX 기준) 환경에서 검증되었으므로 우선적으로
> `RetroArch` 사용을 권장합니다.

## 가장 간단한 다운로드

원하는 버전은 다음 패처를 받아 일본판 ROM에 적용합니다.

- [Langrisser-II-Korean-Patcher-v1.3.2.exe](https://github.com/hsp1324/lang2_md/releases/download/v1.3.2/Langrisser-II-Korean-Patcher-v1.3.2.exe)

검증값은 [v1.3.2 Release](https://github.com/hsp1324/lang2_md/releases/tag/v1.3.2)에서 확인할 수 있습니다.

## 세 가지 버전

- **원작 디자인판**: 원작의 맵 캐릭터 디자인과 밸런스를 유지하고 한국어화와 키스·레스터·제시카 합류 진행 수정을 적용합니다.
- **최신 디자인 일반판**: `New 클래스`의 최신 사용자 디자인과 한국어화를 적용하며 난이도는 원작 기준입니다.
- **최신 디자인 하드판**: 최신 사용자 디자인과 한국어화에 적 지휘관·용병 강화 밸런스를 더합니다.

Windows 패처는 일본판 ROM 또는 ZIP 하나를 고르면 위 세 ROM을 모두 생성합니다.

## macOS에서 패치하기

macOS에서는 EXE 대신 저장소의 Python 패처를 바로 실행할 수 있습니다. 별도
Python 패키지는 필요하지 않습니다.

```bash
git clone https://github.com/hsp1324/lang2_md.git
cd lang2_md
python3 patcher/langrisser_ii_korean_patcher.py \
  --rom "/path/to/Langrisser II (Japan).md" \
  --output-dir "/path/to/output"
```

일본판 ROM이 ZIP 안에 있어도 `--rom`에 ZIP 경로를 지정하면 됩니다. 기존
게임 내 저장도 함께 연결하려면 `--save`와 연결할 버전을 지정합니다.

```bash
python3 patcher/langrisser_ii_korean_patcher.py \
  --rom "/path/to/Langrisser II (Japan).zip" \
  --output-dir "/path/to/output" \
  --save "/path/to/old-save.srm" \
  --save-target normal
```

`--save-target`은 `pure`, `normal`, `hard` 중 하나입니다. 상태 저장 파일이
아니라 게임 안에서 저장한 `.srm`을 사용해야 합니다.

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
확인해 주세요.

`New 클래스`의 16×16 디자인 편집 결과는 현재 편집 ROM에 자동 적용되지
않습니다. 시나리오 배치의 클래스 ID만 바꾸는 작업도 이미 저장된 런타임
마법·소환 권한을 자동 재계산하지 않습니다. 마법·소환 습득 규칙은
`클래스 수정` 탭에서 별도로 지정합니다. 자세한 구조와 제한은
[게임 데이터 편집기 구조](docs/editor_data_model.md)를 참고하세요.

## 기존 세이브로 업데이트하기

기존 게임 내 저장인 `.srm`은 새 버전에서도 이어서 사용할 수 있습니다.

1. 기존 버전에서 게임 내 저장을 합니다.
2. 에뮬레이터를 완전히 종료합니다.
3. 기존 `.srm` 파일을 복사하여 원본을 보존합니다.
4. 복사본의 기본 파일명을 새 ROM과 똑같이 맞춥니다.
5. 새 ROM을 실행하고 게임 안의 `불러오기`로 저장을 엽니다.

예를 들어 새 ROM이 `Langrisser II (Normal v1.3.2).md`이면 다음 저장
파일이 생성됩니다.

```text
Langrisser II (Normal v1.3.2).srm
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

- [세이브를 유지하는 업데이트 안내](docs/save_preserving_rom_updates.md)
- [게임 데이터 편집기 구조](docs/editor_data_model.md)
- [개발·빌드·분석·검증 상세 문서](docs/development_guide.md)
- [다른 환경에서 개발을 이어가기 위한 인수인계](HANDOFF.md)

개발용 빌드 명령, ROM 구조, 글꼴과 VRAM 분석, 시나리오별 검증 도구 및 실기 증거는 README에서 분리해 [개발 문서](docs/development_guide.md)에 보존했습니다.

## 주의

이 프로젝트의 한국어판은 원작 회사의 공식 제품이 아닌 비공식 한국어화판입니다.
