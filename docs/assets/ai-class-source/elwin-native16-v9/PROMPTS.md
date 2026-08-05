# Elwin v9 prompt set

내장 이미지 생성 도구를 사용했다. 수정하지 않은 7개 클래스의 프롬프트는
`../elwin-native16-v8/PROMPTS.md`에 있다.

## Lord

v8 로드를 유일한 편집 대상으로 사용했다. 모든 픽셀 경계와 머리, 검,
방패, 망토, 다리, 배경을 그대로 두고 기존 어깨·가슴 갑옷 셀만
steel blue, pale blue-silver, deep navy와 금색 두 셀 이하로 바꾸도록
지시했다. 머리띠가 파랗게 변한 첫 편집은 폐기했다.

## Highlander

`0C-original-full-ratio.png`와 `0C-masked-identity.png`만 입력했다.
머리 영역과 주변 빈 공간을 그대로 유지하고, 하단에 넓은 몸통, 둥근
뒷부분, 꼬리, 비스듬한 목, 작은 귀, 경사진 이마, 돌출된 주둥이,
분리된 다리와 바닥의 굽이 있는 옆모습 말을 만들도록 지시했다.
무기는 제거해 머리 마스크와 말 실루엣에 집중했다.

## Mage

v8 메이지를 편집 대상으로, 원작 전체 비율과 사용자 마스크를 정체성
기준으로 사용했다. 넓은 로브의 모든 경계와 지팡이를 유지하면서
거의 검은 남색을 saturated royal blue, cobalt blue, violet collar,
pale silver-blue shoulders, 작은 crimson·gold 강조색으로 교체했다.
