# v1.4.0 일반 사용자용 패치 배포

> 상태: **v1.4.0 정식 배포**. GitHub Release에는 운영체제별 패처 5개만
> 올리고 ROM과 BPS 파일은 별도로 배포하지 않습니다.

일본판 `Langrisser II (Japan)` ROM 또는 그 ROM이 들어 있는 ZIP을 패처에서
고르면 Original·Normal·Hard ROM 세 개가 생성됩니다.

```text
Langrisser II (Korean Original v1.4.0).md
Langrisser II (Korean Normal v1.4.0).md
Langrisser II (Korean Hard v1.4.0).md
```

## 지원 원본

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

## 결과 검증값

| 판 | MD 체크섬 | SHA-256 |
| --- | --- | --- |
| Original | `070E` | `27bf66ae23b98dbb3460c20e899566bf5e55f83f080fe5b1ee72e053845e1418` |
| Normal | `A7B2` | `6ee6b5e4a2829dd190e07d348d69dc170d2485ab3370968fe4446c5db137a1af` |
| Hard | `455D` | `df24cae24fded4e10626f016ecba71e63eb304494a5102c7703f8ee0315b8230` |

## 공개 Release 자산 계약

Release 태그와 표시 제목은 모두 `v1.4.0`으로 사용합니다. v1.4.0 Release에는
다음 플랫폼 패처를 정확히 5개만 올립니다.

```text
Langrisser-II-Korean-Patcher-v1.4.0.exe
Langrisser-II-Korean-Patcher-v1.4.0-linux-x86_64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.0-linux-arm64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.0-macos-arm64.app.zip
Langrisser-II-Korean-Patcher-v1.4.0-macos-x86_64.app.zip
```

각 패처에는 `v1.4.0.json`과 세 BPS가 내장됩니다. 원본 ROM과 사용자 SRAM은
덮어쓰지 않습니다. 기존 저장은 ROM과 같은 기본 파일명으로 복사한 `.srm`을
게임 안의 `불러오기`로 여세요.
