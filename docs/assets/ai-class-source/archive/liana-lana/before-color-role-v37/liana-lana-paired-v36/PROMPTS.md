# 고정 머리 네이티브 16×16 생성·재합성 기준

## 최신 v36 마스크 재합성

AI 몸·장비 원화는 직전 결과를 그대로 유지했다. 사용자가 다시 저장한
리아나 힐러 `2:08`의 74픽셀 마스크를 리아나·라나 11종 전체에 같은
좌표로 복사하고, 각 클래스의 해당 좌표에는 그 클래스 ROM 원본 픽셀을
복원했다. 아래 프롬프트는 유지 중인 AI 몸·장비 원화를 만들 때 사용한
생성 기준이며 이번 재합성에서는 AI를 다시 호출하지 않았다. 4bpp 색
제한을 넘은 라나 실버나이트는 마스크 밖 금색 1픽셀만 가장 가까운 기존
금색으로 합쳤다.

## 기존 AI 원화 생성 시 공통 입력

각 클래스마다 원본 16×16에서 얼굴·머리카락·눈·흰자·목 윤곽을 남긴
가이드를 편집 대상으로 사용했다. 현재 `head-guides`는 최신 힐러 74픽셀
공통 마스크가 실제로 적용된 범위를 보여 준다.

## 공통 프롬프트

```text
Use case: precise-object-edit
Asset type: literal native 16x16 Mega Drive strategy-RPG sprite displayed
enlarged.

The input is a fixed 16x16 head-only identity target. Every visible
non-magenta block is immutable Liana hair, face, eye, eye-white, neck, or
head outline. Keep every one at exactly the same logical coordinate, size,
shape, and color. Do not redraw, duplicate, move, crop, or scale the head.
Magenta cells are editable/background.

Create exactly ONE connected class body around this fixed large head.
Place the character's left-hand main weapon on IMAGE-RIGHT at logical
columns 13-15. No weapon or detached cluster on image-left.

Exactly 16 uniform logical square pixels per side on the unchanged canvas.
No subpixel detail, antialiasing, gradient, texture, grid line, text, UI,
or second sprite. Keep the fixed head as the top third. Use row 15, useful
connected equipment at column 0, and the right-hand weapon at column 15.
Flat #ff00ff only in empty cells. Use 12-15 flat Mega Drive-like colors and
charcoal #242424 instead of pure black. No purple/magenta on the subject and
no black background. Actual 16x16 game-pixel data, not a high-resolution
pixel-art illustration.
```

## 클래스별 지시

- `08` 힐러: 백청색 치유 로브, 담청 견갑, 수정 지팡이
- `0B` 하이로드: 백은 판금, 큰 견갑, 청색 망토, 장검
- `11` 프리스트: 백청색 제의, 금색 성직 지팡이
- `13` 메이지: 남청색 로브, 담청 맨틀, 수정 지팡이
- `14` 아크메이지: 메이지보다 넓고 강한 백청색 로브와 큰 수정 지팡이
- `15` 위저드: 청백색 로브와 긴 망토, 장식 지팡이
- `16` 하이프리스트: 프리스트보다 풍성한 백청색 제의와 성직 지팡이
- `18` 세이지: 청백색 로브, 몸에 연결된 마도서, 수정 지팡이
- `19` 팔라딘: 한 명의 백은 기수와 한 마리의 말, 청색 마갑, 오른쪽 검
- `1D` 실버나이트: 한 명의 백은 기수와 한 마리의 말, 청색 마갑,
  오른쪽 끝 수직 장창
- `28` 서머너: 남청색 룬 로브, 연결된 두루마리, 오른쪽 수정 지팡이

## 변환 불변 조건

- AI 출력의 피사체 경계를 자르지 않는다.
- 가로와 세로를 서로 다른 배율로 늘이지 않는다.
- 전체 출력 캔버스의 각 1/16 영역을 같은 목적지 좌표로 읽는다.
- 네이티브 16×16에 원본 머리 픽셀을 다시 넣어 원화 단계에서 확정한다.
- 라나는 완성된 리아나 16×16의 청색 장비만 적색으로 치환한다.
- 에디터 빌더는 이 원화를 재양자화하지 않고 바이트 그대로 사용한다.
