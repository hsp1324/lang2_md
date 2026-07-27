# 쉐리 전 클래스 AI 디자인 v2

쉐리의 기본 클래스는 그대로 두고, 하위 클래스와 맵 스프라이트가 겹치는
상위 클래스 11종을 모두 새 AI 원화와 네이티브 16×16 디자인으로
교체한 묶음이다.

## 생성 기준

- Codex 내장 `imagegen`을 클래스별로 한 번씩 별도 호출했다.
- 입력은 각 클래스의 현재 ROM 원작과 사용자가 저장한 얼굴 마스크뿐이다.
- 이전 쉐리 AI 그림은 생성 입력으로 사용하지 않았다.
- 큰 얼굴, 눈·흰자, 턱선 길이의 은발 단발을 유지한다.
- 생성 장비 원화의 얼굴 논리셀을 먼저 원본으로 고정한 뒤, 피사체를
  자르지 않고 전체 AI 캔버스를 16×16로 직접 읽는다.
- 최종본은 16개 행·열을 모두 사용하고 가시색을 15색 이하로 제한한다.
- 로드·하이로드·메이지·아크메이지·위저드·세인트·팔라딘·레인저·
  하이마스터는 보행, 실버나이트는 말, 드래곤로드는 드래곤 탑승이다.

## 폴더

- `guides`: 현재 원작과 사용자 마스크
- `reference-cards`: 이미지 생성에 사용한 원작+마스크 입력 카드
- `raw`: 내장 이미지 생성의 변경되지 않은 출력
- `selected-sources`: AI 장비 원화에 원본 얼굴 논리셀을 고정한 채택본
- `logical16`: 에디터가 사용하는 실제 16×16 원화
- `sherry-v2-raw-ai.png`: 11개 원시 AI 결과 모음
- `sherry-v2-ai-final-rom.png`: 채택 AI·최종 16×16·ROM 원작 비교
- `sherry-v2-editor-final-comparison.png`: 에디터 실제 반영본 비교
- `validation-report.json`: 얼굴·연결 몸체·16행·16열 검사
- `PROMPTS.md`: 공통 프롬프트와 클래스별 장비 지시

## 재변환

```bash
python3 tools/normalize_sherry_ai_source.py \
  --all-raw-dir docs/assets/ai-class-source/latest/sherry-v2/raw \
  --output-dir docs/assets/ai-class-source/latest/sherry-v2
```

직전 v1 작업물은
`archive/sherry/before-v2/sherry-native16-v1`에 보관했다.
