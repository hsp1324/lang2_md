# ROM 기준 클래스 디자인 10안 v3

샘플 클래스 탭의 34개 캐릭터·클래스 조합, 총 340안을 원본 일본판 ROM
스프라이트를 주 디자인 기준으로 다시 생성한 작업물이다.

- 입력: 캐릭터별 정확한 ROM 16×16 스프라이트와 원작 클래스 계보 보드
- 얼굴: 사용자가 저장한 얼굴·머리 마스크와 맞닿은 어두운 경계 한 겹
- 제외: 이전 AI 원화, 공통 몸통 템플릿, 다른 캐릭터 디자인의 단순 색상 교체
- 변형: 무기 방향·무기 머리·망토/소매·어깨·하단 실루엣
- 변환: AI 보드의 각 후보를 직접 축소하며 빈 행·열이나 연결선을 강제로 만들지 않음
- 색상: ROM 팔레트와 후보별 장비 강조색을 합친 15색 이하 동적 팔레트
- 검증: 얼굴 경계 일치, ROM 상대 크기, 픽셀 밀도, 색 수, 후보 간 장비·실루엣 차이

전체 결과는 [all-ai-and-logical16.png](all-ai-and-logical16.png)에서 볼 수
있다. 캐릭터별 비교판은 `contact-sheets/commanders/`, 클래스별 AI 원본과
최종 16×16은 각 그룹 폴더의 `ai/`와 `logical16/`에 있다.

`validation-report.json`은 340/340 후보와 34/34 다양성 그룹이 모두
통과한 결과를 기록한다. 제시카 자베러 01의 사용자 확정 세로 장창형은
장비 디자인을 유지하고 확장된 얼굴 경계만 다시 복원했다.

재구축 도구:

```bash
python3 tools/build_rom_anchored_sample_campaign.py prepare
python3 tools/build_rom_anchored_sample_campaign.py publish
```
