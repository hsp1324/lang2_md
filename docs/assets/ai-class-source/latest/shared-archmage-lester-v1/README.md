# 레스터 아크메이지 공통 템플릿 v1

사용자가 AI 클래스 에디터에서 직접 수정한 레스터 아크메이지 `9:14`
16×16을 장비·실루엣 기준으로 사용한다. 아크메이지가 있는 상위 중복
클래스 8명은 같은 옷·망토·지팡이 좌표를 공유하고, 각 캐릭터의 현재
보이는 얼굴·머리 픽셀과 원본 클래스 팔레트를 적용한다. 얼굴 마스크의
투명 좌표는 장비를 지우지 않는다. 아론 아크메이지의 연결된 망토·로브는
기본 캐릭터와 같은 흰색·황토색 명암으로 바꾸되 흰색을 넓은 주면으로,
황토색을 주름·테두리로 사용한다. 분리된 지팡이의 파란 마력 효과는
유지한다.
이전 밝은 은백색 결과, 첫 청색 결과, 짙은 청색 결과는 각각
`archive/aaron-archmage-before-blue-v1/`,
`archive/aaron-magic-before-deeper-blue-v1/`,
`archive/aaron-before-sky-blue-v1/`에 보존한다.
변경 직전 v51은 `archive/aaron-before-ochre-capes-v1/`에 보존한다.
황토색 비중이 더 높았던 v52는
`archive/aaron-archmage-before-white-balance-v1/`에 보존한다.

- 원본 기준: `master/lester-14-user-edited.png`
- 실제 입력: `logical16/`
- 전체 비교: `all-archmage-variants.png`
- 검증: `validation-report.json`

8명 모두 보이는 얼굴·머리 픽셀 100%, 가시색 15색 이하, 빈 행·열
없음으로 검증한다.
