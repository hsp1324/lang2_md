# 제시카 자베라·서머너 신규 AI v1

제시카 `10:26` 자베라와 `10:28` 서머너를 이전 AI 원화, 공통 클래스
템플릿, 기존 장비·색상 가이드 없이 새로 만들었다. 생성 입력은 각 클래스의
ROM 원본과 현재 73픽셀 얼굴·머리 마스크뿐이다.

- `selected-sources/`: 이번 작업에서 새로 생성해 선택한 AI 원화
- `logical16/`: AI 원화의 큰 장비 군집을 다시 찍은 네이티브 16×16
- `previews/`: 네이티브 결과의 nearest-neighbor 확대본
- `10-26-comparison.png`, `10-28-comparison.png`: ROM / AI / 16×16 비교
- `all-jessica-fresh-classes.png`: 두 클래스의 AI 원화와 16×16을 한 장에 정리
- `validation-report.json`: 얼굴 73픽셀, 15색, 연결성, 빈 행·열, 몸통 구멍 검증
- `PROMPTS.md`: 실제 생성과 보정에 사용한 프롬프트

자베라는 짙은 망토·백은 견갑·오른쪽 보석 지팡이, 서머너는 흰 맨틀·
남청 로브·왼쪽 소환 지팡이로 서로 다른 실루엣을 사용한다. 두 소스의
얼굴은 이동 전 ROM 좌표에 있으며, 전체 에셋 빌드가 제시카의 최종 얼굴을
오른쪽으로 정확히 한 칸 옮긴다.

재생성:

```bash
python3 tools/build_jessica_fresh_magic_classes.py --prepare-references
python3 tools/build_jessica_fresh_magic_classes.py
python3 tools/build_ai_class_sprite_assets.py
```
