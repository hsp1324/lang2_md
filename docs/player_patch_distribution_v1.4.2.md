# v1.4.2 일반 사용자용 패치 배포

> 상태: **v1.4.2 정식 배포**. GitHub Release에는 운영체제별 패처 5개만
> 올리고 ROM과 BPS 파일은 별도로 배포하지 않습니다.

일본판 `Langrisser II (Japan)` ROM 또는 그 ROM이 들어 있는 ZIP을 패처에서
고르면 Original·Normal·Hard ROM 세 개가 생성됩니다.

```text
Langrisser II (Korean Original v1.4.2).md
Langrisser II (Korean Normal v1.4.2).md
Langrisser II (Korean Hard v1.4.2).md
```

## 지원 원본

```text
크기:    2,097,152 bytes
SHA-256: a6e10e82b1e8fd32d8e4ae2ce76ab689cd789d93f854aa1788abc1e9795ddb3b
```

## 결과 검증값

| 판 | MD 체크섬 | SHA-256 |
| --- | --- | --- |
| Original | `1827` | `0a5794a2914db8b13ab8ece10efaedfec5a746e91fe3a195c369b5357a12805f` |
| Normal | `B8CB` | `46a092f8fa6725a3b18df961889f253b69a6493ca3870c38c60d6c3e02129414` |
| Hard | `5876` | `fb366b9ed905d828bdf84b7aecb7fbaac016e8d07a379033082f24718bdd7f55` |

## 공개 Release 자산 계약

Release 태그와 표시 제목은 모두 `v1.4.2`로 사용합니다. v1.4.2 Release에는
다음 플랫폼 패처를 정확히 5개만 올립니다.

```text
Langrisser-II-Korean-Patcher-v1.4.2.exe
Langrisser-II-Korean-Patcher-v1.4.2-linux-x86_64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.2-linux-arm64.tar.gz
Langrisser-II-Korean-Patcher-v1.4.2-macos-arm64.app.zip
Langrisser-II-Korean-Patcher-v1.4.2-macos-x86_64.app.zip
```

각 패처에는 `v1.4.2.json`과 세 BPS가 내장됩니다. 원본 ROM과 사용자 SRAM은
덮어쓰지 않습니다. 기존 저장은 ROM과 같은 기본 파일명으로 복사한 `.srm`을
게임 안의 `불러오기`로 여세요.
