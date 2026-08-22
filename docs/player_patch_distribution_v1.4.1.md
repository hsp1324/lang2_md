# v1.4.1 일반 사용자용 패치 배포

> 상태: **v1.4.1 정식 배포**. GitHub Release에는 운영체제별 패처 5개만
> 올리고 ROM과 BPS 파일은 별도로 배포하지 않습니다.

일본판 `Langrisser II (Japan)` ROM 또는 그 ROM이 들어 있는 ZIP을 패처에서
고르면 Original·Normal·Hard ROM 세 개가 생성됩니다.

```text
Langrisser II (Korean Original v1.4.1).md
Langrisser II (Korean Normal v1.4.1).md
Langrisser II (Korean Hard v1.4.1).md
```

## 지원 원본

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

## 결과 검증값

| 판 | MD 체크섬 | SHA-256 |
| --- | --- | --- |
| Original | `1727` | `25e3c8d3c97996f3c44e7058523a235946982fa9e51d8678cac369788d9b864a` |
| Normal | `B7CB` | `d630325fd088810f264d50a902604063f2df7bd4bfa68f7827b6cf1c0cc63a9e` |
| Hard | `5676` | `8626d19b6eb784f8f027fbd3bf47f660146ccbfef7bfdaf020033d6fb51f5a8a` |

## 공개 Release 자산 계약

Release 태그와 표시 제목은 모두 `v1.4.1`으로 사용합니다. v1.4.1 Release에는
다음 플랫폼 패처를 정확히 5개만 올립니다.

```text
Langrisser-II-Korean-Patcher-v1.4.1.exe
Langrisser-II-Korean-Patcher-v1.4.1-linux-x86_64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.1-linux-arm64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.1-macos-arm64.app.zip
Langrisser-II-Korean-Patcher-v1.4.1-macos-x86_64.app.zip
```

각 패처에는 `v1.4.1.json`과 세 BPS가 내장됩니다. 원본 ROM과 사용자 SRAM은
덮어쓰지 않습니다. 기존 저장은 ROM과 같은 기본 파일명으로 복사한 `.srm`을
게임 안의 `불러오기`로 여세요.
