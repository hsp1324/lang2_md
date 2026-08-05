# 클래스 디자인 5안 비교 샘플 v1

현재 디자인이 만족스럽지 않았던 세 클래스를 기존 AI 시안 없이 다시
생성한 비교용 자산이다.

| 폴더 | 지휘관·클래스 | 시안 수 |
|---|---|---:|
| `elwin-hero` | 엘윈 · 히어로 (`1:22`) | 5 |
| `jessica-zarvera` | 제시카 · 자베러 (`10:26`) | 5 |
| `jessica-summoner` | 제시카 · 서머너 (`10:28`) | 5 |

각 폴더에는 다음 파일이 있다.

- `ai/01.png`~`05.png`: built-in `image_gen`으로 독립 생성한 AI 원안
- `logical16/01.png`~`05.png`: AI 원안을 보고 다시 짠 native 16×16
- `previews/01.png`~`05.png`: nearest-neighbor 확대본
- `prompts/01.txt`~`05.txt`: 각 독립 호출에 실제 사용한 프롬프트
- `validation-report.json`: 얼굴 고정, 색상 수, 연결성, 빈 행·열 검증

최초 생성 입력은 각 클래스의 ROM 원본과 해당 지휘관의 identity-only
이미지 두 장뿐이다. 이 폴더보다 앞서 만든 AI 결과나 공통 클래스
디자인은 최초 생성 입력으로 사용하지 않았다.

제시카의 source `logical16`은 기존 빌드 파이프라인과 동일하게 얼굴
좌표가 이동 전 상태다. 에디터 게시 단계에서는 장비를 움직이지 않고
얼굴·머리 73픽셀만 오른쪽으로 한 칸 옮긴 현행 최종 좌표로 변환한다.
따라서 source를 aggregate 빌더에 넣을 때와 웹 에디터에서 비교할 때
얼굴 이동이 중복되지 않는다.

웹 에디터용 축소 자산과 전체 비교 시트는 다음 명령으로 갱신한다.

```bash
python3 tools/build_sample_class_sprite_catalog.py
```

게시 결과는 `editor/static/sample-class-sprites/`에 들어가며, 에디터의
`샘플 클래스` 탭에서 3개 클래스별 5안을 나열한다. 샘플을 불러오는
동작은 New 클래스 편집 캔버스만 바꾸고 자동 저장하지 않는다.
