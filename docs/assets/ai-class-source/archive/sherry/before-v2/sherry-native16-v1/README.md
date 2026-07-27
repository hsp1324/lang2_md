# Sherry native16 v1

쉐리의 맵 스프라이트가 하위 클래스와 겹치는 상위 클래스 11개를
클래스별 AI 원화로 교체한 현재 적용 묶음이다. 기본 클래스와 단독
스프라이트 클래스는 ROM 원본을 그대로 사용한다.

- 입력은 각 클래스의 ROM 전체 16×16과 사용자가 편집한 마스크뿐이다.
- 이전 쉐리 AI 시트는 이미지 생성 입력으로 사용하지 않았다.
- 모든 클래스에서 큰 머리, 눈·흰자, 턱선 길이의 은발 단발을 유지했다.
- 로드·하이로드·메이지·아크메이지·위저드·세인트·팔라딘·레인저·
  하이마스터는 보행이다.
- 실버나이트는 말, 드래곤로드는 드래곤에 탑승한다.
- 원시 머리 일치율은 모두 90% 이상이며 최종 마스크는 100% 일치한다.
- `sherry-v1-contact-sheet.png`는 채택된 AI+마스크 16×16 원화를 한
  장에 모은 시트다.
- `sherry-v1-ai-final-rom.png`는 AI 원화, 최종 ROM 팔레트 16×16,
  원작 ROM을 한 장에서 비교한다.

## 재생성

```sh
python3 tools/normalize_sherry_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/sherry-native16-v1/raw \
  --output-dir docs/assets/ai-class-source/sherry-native16-v1
```

입력 역할과 클래스별 장비 프롬프트는 `PROMPTS.md`에 기록했다.
