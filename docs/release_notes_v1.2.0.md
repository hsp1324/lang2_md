# 랑그릿사 II 한국어 패치 v1.2.0

## 다운로드

일반판 또는 하드판 완성 ROM을 내려받아 에뮬레이터에서 바로 실행할 수
있습니다. 일본판 ROM에 직접 적용하려는 사용자를 위해 Windows 패처와
BPS 패치도 함께 제공합니다. Windows 패처에는 Python 설치가 필요하지
않습니다.

```text
Langrisser.II.Korean.v1.2.0.md
Langrisser.II.Korean.Hard.T1.2.0.B1.2.0.md
```

## 사용법

1. 합법적으로 보유한 메가드라이브판 `Langrisser II (Japan)` ROM 또는
   해당 ROM이 든 ZIP을 준비합니다.
2. 패처를 실행하고 원본 파일을 선택합니다.
3. 패처가 일반판과 하드판을 생성하고 SHA-256을 검증합니다.
4. 기존 `.srm`을 이어서 사용하려면 패처의 선택 항목에서 저장 파일과
   연결할 버전을 지정합니다.

## 생성 파일

```text
Langrisser II (Korean v1.2.0).md
Langrisser II (Korean Hard T1.2.0 B1.2.0).md
```

## 원본 검증값

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

512바이트 헤더가 붙은 덤프는 헤더를 제외한 내용이 위 값과 일치할 때만
허용합니다. 다른 지역판이나 이미 수정된 ROM은 거부합니다.

## 결과 검증값

```text
일반판
1934476c9719cba1b4a53869aa2af3b1345a70456045f9d6ea2ce243eefb6d80

하드판
a6b4cb1fbad2d22fda9e8393fe80682d171ed5a6c817e6004f2edd05886e3a62
```

## 세이브 주의사항

게임 안에서 저장한 `.srm`은 새 ROM 이름으로 연결해 이어서 사용할 수
있습니다. `.state`, `.state*`, `.gst` 같은 에뮬레이터 상태 저장은 버전 간
호환을 보장하지 않으므로 새 ROM에서는 게임 안의 `불러오기`를 사용하세요.

이 Release에는 완성된 일반판·하드판 ROM, Windows 패처, 일반판·하드판
BPS와 SHA-256 검증값이 포함됩니다.
