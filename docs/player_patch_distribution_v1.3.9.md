# v1.3.9 일반 사용자용 패치 배포

> 상태: **v1.3.9 공개 배포 완료**. GitHub Release에는 운영체제별 패처 5개만
> 올리고 ROM과 BPS 파일은 별도로 배포하지 않습니다.

일본판 `Langrisser II (Japan)` ROM 또는 그 ROM이 들어 있는 ZIP을 패처에서
고르면 Original·Normal·Hard ROM 세 개가 생성됩니다. 원본 ROM과 기존 SRAM은
덮어쓰지 않습니다.

```text
Langrisser II (Korean Original v1.3.9).md
Langrisser II (Korean Normal v1.3.9).md
Langrisser II (Korean Hard v1.3.9).md
```

## 지원 원본

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

## 결과 검증값

| 판 | MD 체크섬 | SHA-256 |
| --- | --- | --- |
| Original | `FDD5` | `4d06fa849b27d6e2182a48c9cb60c9ef61f74ccd8cfbb119f1695b680223efc6` |
| Normal | `2E0A` | `36a857eeef644032eedcdaa2168e81ac1fa39c1dd429f6ec38dcd51aa7b50c71` |
| Hard | `C57A` | `ae40a8f1c115f78653b3d39e8a6087950aee5a95fe94108b49fe694c6a27246d` |

## 공개 Release 자산 계약

Release 태그와 표시 제목은 모두 짧게 `v1.3.9`로 사용합니다.
v1.3.9 Release에는 다음 플랫폼 패처를 정확히 5개만 올립니다.

```text
Langrisser-II-Korean-Patcher-v1.3.9.exe
Langrisser-II-Korean-Patcher-v1.3.9-linux-x86_64.tar.gz
Langrisser-II-Korean-Patcher-v1.3.9-linux-arm64.tar.gz
Langrisser-II-Korean-Patcher-v1.3.9-macos-arm64.app.zip
Langrisser-II-Korean-Patcher-v1.3.9-macos-x86_64.app.zip
```

각 패처에는 `v1.3.9.json`과 Original·Normal·Hard BPS가 내장됩니다. BPS,
일본판 원본, 사용자 SRAM, 상태 저장 파일은 Release 자산으로 별도 업로드하지
않습니다.

## 안전한 업데이트

게임 안에서 저장한 `.srm`은 새 ROM 이름에 맞춰 복사해 이어서 사용할 수
있습니다. 에뮬레이터 상태 저장은 코드와 메모리를 포함하므로 버전 사이에
재사용하지 마세요. 자세한 절차는
[세이브를 유지하는 업데이트 안내](save_preserving_rom_updates.md)를 참고하세요.
