#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_korean_chapter1 as chapter1
import build_korean_chapter1_natural_jamo as chapter1_natural
import build_korean_chapter1_setup_complete as setup
import build_korean_machine_jamo as base
import build_korean_machine_jamo_fixedfont as fixedfont


OUT = Path("Langrisser II (Korean Complete WIP).md")
SCENARIO_POINTER_TABLE = 0x9CF7C
SCENARIO_COUNT = 31
DIALOGUE_COPY_LIMIT_OFFSET = 0xA8735
DIALOGUE_COPY_LIMIT = 0xFE
DIALOGUE_MAPPER_START_OFFSET = 0xA874A
DIALOGUE_MAPPER_END_OFFSET = 0xA8816
DIALOGUE_MAPPER_HOOK_OFFSET = 0xAF7E8
DIALOGUE_CUSTOM_CODES = tuple(range(0xD9, 0xF4)) + (0xF9,)
DIALOGUE_CUSTOM_TILES = (
    0x21,
    0x22,
    0x23,
    0x25,
    0x27,
    0x2A,
    0x2E,
    0x2F,
    0x3A,
    0xCD,
    0x5B,
    0x5C,
    0x5D,
    0x5E,
    0x5F,
    0x60,
    0x6D,
    0x62,
    0x63,
    0x64,
    0x71,
    0x66,
    0x67,
    0x68,
    0x69,
    0x6A,
    0x6B,
    0x6C,
)
if len(DIALOGUE_CUSTOM_CODES) != len(DIALOGUE_CUSTOM_TILES):
    raise ValueError("dialogue custom code/tile table size mismatch")
DIALOGUE_CUSTOM_TILE_BY_CODE = dict(zip(DIALOGUE_CUSTOM_CODES, DIALOGUE_CUSTOM_TILES))
USE_EXTENDED_DIALOGUE_CODES = True

# Keep the original English VWF entries needed by the title screen and any
# short labels that do not yet fit the jamo encoding budget.
VWF_RESERVED = b"PressStartButtonNCSCorpSave"
VWF_ASCII_RESERVED = b" .,!?:0123456789"
COMPOUND_JAMO_FALLBACKS = {
    "ㄲ": "ㄱㄱ",
    "ㄳ": "ㄱㅅ",
    "ㄵ": "ㄴㅈ",
    "ㄶ": "ㄴㅎ",
    "ㄸ": "ㄷㄷ",
    "ㄺ": "ㄹㄱ",
    "ㄻ": "ㄹㅁ",
    "ㄼ": "ㄹㅂ",
    "ㄽ": "ㄹㅅ",
    "ㄾ": "ㄹㅌ",
    "ㄿ": "ㄹㅍ",
    "ㅀ": "ㄹㅎ",
    "ㅃ": "ㅂㅂ",
    "ㅄ": "ㅂㅅ",
    "ㅆ": "ㅅㅅ",
    "ㅉ": "ㅈㅈ",
    "ㅘ": "ㅗㅏ",
    "ㅙ": "ㅗㅐ",
    "ㅚ": "ㅗㅣ",
    "ㅝ": "ㅜㅓ",
    "ㅞ": "ㅜㅔ",
    "ㅟ": "ㅜㅣ",
    "ㅢ": "ㅡㅣ",
    "ㅒ": "ㅑㅣ",
    "ㅖ": "ㅕㅣ",
}

SCENARIO_DESCRIPTIONS = [
    """시나리오 1
시작의 날

홀로 여행하던 엘윈은
살라스의 작은 마을에서
잠시 쉬고 있었다.
그는 마을 사람들과
잘 어울렸고,
어린 마법사 헤인과도
곧 친구가 되었다.

어느 조용한 날,
헤인이 엘윈이 머무는
여관으로 다급히 뛰어왔다.
그는 레이갈드 제국군이
마을을 습격하고 있으며,
리아나가 위험하다고 알렸다.

엘윈은 검을 움켜쥐고
그녀를 구하러 달려갔다.""",
    """시나리오 2
여행의 시작

레이갈드 제국군에게서 리아나를
구한 엘윈 일행은 살라스 영주
로렌의 저택을 찾았다. 로렌은
리아나를 에스톨의 빛의 대신전까지
호위해 달라고 부탁했다. 제국이
무슨 목적으로 리아나를 노리는지
알 수 없었기에, 그녀를 위험에서
지키려는 것이었다.

일행이 리아나의 호위를 맡으려던
무렵, 발가스 장군의 오른팔 조름이
이끄는 부대가 로렌의 저택으로
다가오고 있었다.""",
    """시나리오 3
조름의 반격

조름의 포위망에서 벗어난 엘윈
일행은 에스톨의 빛의 대신전으로
가기 위해 산길을 서둘렀다.

그러나 부상과 피로가 쌓인 채로는
추격을 따돌릴 수 없었다. 결국
조름이 이끄는 추격대가 일행을
따라잡았다.

수많은 적 앞에서 적은 병력으로
불리한 싸움을 치러야 했다.""",
    """시나리오 4
빛의 신전

수수께끼의 기사 덕분에 발가스
장군을 물리친 일행은 에스톨의
빛의 대신전으로 향했다. 그곳에만
도착하면 수많은 신관전사가
리아나를 지켜 줄 터였다.

그러나 일행이 대신전에서 본 것은
신전을 공격하려는 레이갈드 제국
흑룡마도사단의 모습이었다.""",
    """시나리오 5
짐승의 포효

빛의 대신전은 예상보다 피해가
컸다. 적이 다시 공격하면 리아나를
지켜 낼 수 없는 상태였다.

게다가 모건은 근처 마을로 달아나
죄 없는 주민들까지 해치려 했다.
엘윈 일행은 새로 동료가 된 소녀
쉐리와 함께 모건을 뒤쫓았다.""",
    """시나리오 6
노병 아론

웨어울프의 공격을 물리치고 모건을
뒤쫓은 엘윈 일행. 그러나 모건은
이미 마을 앞까지 와 있었다.
마을에는 그들에게 중요한 무언가가
있는 모양이었다.

몰려드는 마법사들을 두려워해
달아나는 주민들 사이에서, 날카로운
눈빛의 늙은 검객 한 사람만이
용감히 맞서고 있었다.""",
    """시나리오 7
깨어나는 망자

쉐리의 검 스승 아론과 합류한
일행은 그곳에서 밤을 보냈다.
주변은 어둠에 잠겨 낮의 격전이
거짓말처럼 고요했다.

그러나 마을 밖 묘지에서는 여러
남자가 의식을 치르고 있었다.
사람들이 편히 잠든 사이, 사악하고
불길한 존재가 태어나려 했다.""",
    """시나리오 8
하늘의 다리

완전 무장한 레이갈드 제국의
청룡기사단이 칼자스 성으로
향한다는 보고를 키스에게서 받은
쉐리는 급히 성으로 돌아가려 했다.
키스마저 자리를 비운 성은 수비가
허술해, 적에게 노려지면 버틸 수
없었다.

칼자스 성으로 가는 길에는 거대한
협곡이 있었다. 일행이 협곡의
흔들다리를 건너려 하자 적이 앞을
막고 다리를 끊으려 했다. 여기서
다리를 잃으면 귀환이 크게 늦어진다.
엘윈 일행은 강행 돌파를 시도했다.""",
    """시나리오 9
칼자스 성 공방전

거침없는 진격으로 적을 물리치고
협곡을 무사히 건넌 엘윈 일행은
칼자스 성으로 서둘렀다.

숲을 지나 탁 트인 곳에 나오자,
청룡기사단의 맹공을 필사적으로
견디는 칼자스 성이 보였다. 아무리
견고한 성이라도 레온과 레아드가
이끄는 정예부대를 오래 버티기는
어려웠다.

칼자스 성을 둘러싼 격렬한 공방전이
막 시작되려 했다.""",
    """시나리오 10
랄강의 수호자

에스톨의 사제에게서 마검
알하자드의 두려운 힘을 들은 엘윈
일행은 알하자드를 완전히 부활시킬
다크로드라는 마법 도구가
필요하다는 사실도 알게 되었다.
다크로드만 손에 넣으면
제국의 야망을 막을 수 있었다.

일행은 다크로드의 행방을 알 만한
대마법사를 찾아 랄강으로 급히
향했다. 이제 그들의 눈앞에 랄강이
가로놓여 있었다.""",
    """시나리오 11
불길 속에서

레스터의 안내를 받은 엘윈 일행은
다크로드의 행방을 알아내기 위해
수백 년을 살았다는 대마법사
제시카를 찾아가려 했다.

그러나 레이갈드 제국의 참모이자
흑룡마도사단을 이끄는 에그베르트가
그때를 노려 몰래 함정을 파 두었다.""",
    """시나리오 12
성지 레이텔

성지 레이텔. 바위산에 둘러싸인
그곳 한구석에는 모르는 사람이라면
지나칠 만큼 교묘히 숨겨진 입구가
있었다. 다크로드를 안치한 신전으로
이어지는 동굴이었다.

입구에는 사람이 다녀간 흔적도,
먼저 갔을 에그베르트의 모습도
없었다. 그러나 동굴 안에서는
다크로드를 지키라는 명을 받은
고대의 수호자들이 침입자를
기다리고 있었다.""",
    """시나리오 13
염룡병단과의 결전

고대의 수호자들을 쓰러뜨리고
다크로드를 손에 넣으려던 엘윈
일행 앞에 에그베르트가 나타났다.
그는 마법으로 다크로드를 빼앗고,
칼자스 성의 리아나를 납치하려는
듯 순간이동으로 사라졌다.

리아나가 걱정된 일행은 칼자스
성으로 서둘렀지만, 발가스 장군이
염룡병단을 이끌고 앞을 막았다.""",
    """시나리오 14
성검 랑그릿사

수백 년 전 빛의 후예들이
다스렸던 발디아 왕국.
전설이 된 옛 성은 깊은 호수
밑에서 조용히 잠들어 있었다.
봉인이 풀려 모습을 드러낸
발디아 성 가장 깊은 곳에는
전설의 성검 랑그릿사가
안치되어 있었다.

그러나 같은 목적을 지닌
청룡기사단도 그곳에 나타났다.
성검 랑그릿사를 둘러싼 싸움이
다시 시작되려 했다.""",
    """시나리오 15
빙룡병단장 이멜다

성검 랑그릿사를 손에 넣은
엘윈 일행은 납치된 리아나를
구하려 레이갈드 제국으로 향했다.
남은 시간은 얼마 없었다.
가장 짧은 길로 가려면
롤렉 강을 건너야 했다.

그러나 맞은편에서는 이멜다 장군이
기다리고 있었다.
불리한 전황이지만 다른 길을
찾을 여유도 없었다.
엘윈은 리아나를 생각하며
검을 들었다.""",
    """시나리오 16
레이갈드 제도

어둠의 공주는 누군가에게
조종당한 리아나인 듯했다.
달라진 리아나를 눈앞에서 본
엘윈 일행은 충격에 빠졌지만
계속 나아가 마침내 황제
베른하르트의 성에 도착했다.

공격하기 어렵고 지키기 쉬운 성은
공성전에 큰 위력을 보였다.
한 세대 만에 나라를 세우고
대륙 대부분을 정복한 베른하르트는
알하자드로 대륙 통일까지
이루려 했다.

알하자드의 봉인이 풀리기 전에
성에 들어가야 했다.
그러나 성문 앞에는 숙적 레온과
청룡기사단이 기다렸다.""",
    """시나리오 17
황제와 어둠의 왕자

청룡기사단을 돌파해 성에 들어간
엘윈 일행이 옥좌를 바라보자,
건장한 남자가 흥미로운 듯 그들을
내려다보고 있었다.
그가 바로 황제 베른하르트였다.
그 모습은 왕이라기보다 한 명의
전사에 가까웠지만 황제의 위엄도
함께 지니고 있었다.

그 곁에 남자가 숨어 있었다.
사악한 미소를 띤 그는 일행을
흥미롭게 지켜보았다.
정예부대를 뚫고 온 일행 앞에서도
베른하르트는 조금도 당황하지 않고
결전의 순간을 맞으려 했다.""",
    """시나리오 18
어둠의 공주

어둠의 왕자 보젤을 쫓아 벨제리아로
향하던 엘윈 일행은 마물에게
습격받는 마을을 발견했다.

마물에게 쫓겨 달아나는 사람들을
보며 한 소녀가 즐겁게 웃고 있었다.
일행이 그 소녀를 바라보자, 마물을
조종하고 있던 사람은 다름 아닌
리아나였다. 엘윈은 당황했지만
리아나를 막기 위해 달려 나갔다.""",
    """시나리오 19
미레일 항구 전투

보젤을 쓰러뜨리기 위해 벨제리아로
향하던 일행은 어둠의 공주에게
습격받던 마을을 구했다. 주민들은
제국군이 미레일 항구에서 배를
준비하고 있다고 알려 주었다.

그 배를 빼앗으면 디레스 해협을
건너 벨제리아로 갈 수 있었다.
항구가 보이자 짐을 싣는 대형선이
나타났다. 작전이 성공하면 배를
통째로 빼앗을 수 있었다. 엘윈
일행은 배를 탈취할 작전을 시작했다.""",
    """시나리오 20
붉게 물든 바다

이멜다를 물리치고 배를 빼앗은
엘윈 일행은 리아나를 구하려
벨제리아로 향했다.

잔잔한 날씨와 바다는 순조로운
항해를 예고하는 듯했지만, 이윽고
벨제리아 쪽에서 대형선 한 척이
다가왔다. 보젤의 마력에 조종되는
마물 부대가 탄 요격선이었다.

두 배 사이에 건널판이 놓이면서
선상 전투가 시작되었다.""",
    """시나리오 21
마리오네트

금단의 땅 벨제리아.
수백 년 전 빛의 후예들이 보젤을
쓰러뜨렸다고 전해지는 산맥에
둘러싸인 땅이었다. 혼돈의 신이
봉인되었다는 저주받은 대지가
수평선 너머 모습을 드러냈다.

엘윈 일행이 입구를 찾아 상륙하려
하자, 보젤에게 다시 조종당하는
어둠의 공주가 앞을 막았다.""",
    """시나리오 22
알하자드의 부활

마검 알하자드의 해방을 막으려
엘윈 일행은 어둠의 신전에
도착했다.

어두운 신전 깊은 곳에는 사악한
신의 석상이 있었고, 그 앞 제단에는
한 자루의 검이 놓여 있었다. 제단
양옆에는 서로 꼭 닮은 리아나와
또 한 명의 소녀가 서 있었다.

제단 앞에서 검은 망토를 걸치고
주문을 외는 남자는 벨제리아 성에
있던 어둠의 왕자 보젤이었다. 그의
입에서 흘러나온 주문은 알하자드의
봉인이 곧 풀린다는 사실을 알렸다.""",
    """시나리오 23
봉인의 열쇠

마침내 알하자드의 봉인이
풀렸다. 죽은 줄 알았던
베른하르트가 나타나 보젤에게서
알하자드를 빼앗고, 대륙 통일의
야망을 드러냈다.

제시카의 마법으로 베른하르트는
벨제리아까지 날아갔다. 보젤의
마력에서 풀려난 리아나와 라나의
도움을 받은 엘윈 일행은
랑그릿사의 힘이 아직 완전하지
않다는 사실을 알았다.

그 힘을 해방할 홀리로드를 찾아
엘라드의 유적으로 향했다.""",
    """시나리오 24
빛과 어둠

엘라드에서 청룡기사 레아드와
격전을 벌인 끝에 엘윈 일행은
마침내 홀리로드를 손에 넣었다.

빛의 무녀 리아나와 라나는
랑그릿사의 봉인을 풀 의식을
시작했다. 전설의 성검이 진정한
힘을 되찾으려는 순간이었다.

하지만 그때를 기다리던
베른하르트가 엘윈 일행을
공격했다.""",
    """시나리오 25
대륙 최강의 기사

모든 악의 근원인 저주받은 성,
벨제리아. 그 가장 깊은 곳에서
알하자드를 든 베른하르트 황제가
기다리고 있었다.

그러나 그 앞을 제국 청룡기사단장
레온과 에그베르트가 가로막았다.
에그베르트 곁에는 붙잡힌
제시카도 있었다. 한 치도 물러설
수 없는 격전이 시작되려 했다.""",
    """시나리오 26
흑룡마도사단의 함정

숙적 레온을 쓰러뜨리고 벨제리아
성에 잠입한 엘윈 일행은 지하
신전으로 이어지는 통로를 서둘러
달렸다.

그러나 흑룡마도사단을 이끄는
에그베르트가 함정을 파고
기다리고 있었다. 포위망 안에
들어선 일행에게 흑룡마도사단의
강력한 마법 집중 공격이
쏟아지려 했다.""",
    """시나리오 27
전설의 끝

에그베르트의 강력한 마법 공격을
견뎌 낸 엘윈 일행은 마침내
베른하르트가 기다리는 최심부의
신전에 도착했다.

어둠의 신전은 섬뜩할 만큼
고요했다. 제단에는 알하자드를 든
베른하르트가 서 있었다. 궁지에
몰렸지만 파괴적인 힘을 지닌
마검을 든 그의 눈은 자신감과
투지로 가득했다.

수천 년에 걸친 빛과 어둠의
전설이 이제 막을 내리려 했다.""",
    """시나리오 X1
근육의 신전

에그베르트에게 다크로드를
빼앗겼지만, 엘윈 일행은 비밀
통로를 발견해 조사하기로 했다.
리아나가 걱정되었으나 칼자스 성
사람들에게 맡겼으니 크게 염려할
필요는 없었다.

통로 끝에는 기묘한 형상의 석상이
늘어선 신전이 있었다. 바셀린을
바르고 근육을 단련하는 뜨거운
남자들이 모인, 금단의 근육
신전이었다.""",
    """시나리오 X2
디레스 해협의 격전

수평선 너머 제국군을 추격하려고
아직 준비가 끝나지 않은 대형선을
두고, 엘윈 일행은 소형선으로
뒤를 쫓았다.

그 부대는 원래 이멜다 장군을
지원하러 가던 중이었지만, 엘윈
일행이 예상보다 빨리 움직여
제때 도착하지 못했다.

소형선으로 나타난 일행을 발견한
레이갈드의 지휘관은 장군의 원수를
갚으려 맹공을 퍼부었다.""",
    """시나리오 X3
마룡의 둥지

신전에서 마룡의 둥지로 이어지는
지하도를 발견한 엘윈 일행은
위험을 무릅쓰고 통로를 나아갔다.

출구에 겨우 도착하자 그곳은
그레이트드래곤이 사는 용의
둥지였다. 그 한가운데에는 젊은
여성 마법사가 홀로 서 있었다.

그녀는 누구이며 무엇을 위해
이곳에 사는가? 모든 것이
수수께끼에 싸인 기묘한 소녀였다.""",
    """시나리오 X4
죽음의 탑

에그베르트의 도전을 받아 죽음의
탑으로 향한 엘윈 일행은 그곳에서
베른하르트를 비롯한 강적들과
싸우게 되었다.

그들은 에그베르트의 술법과
알하자드의 마력으로 평소 이상의
힘을 발휘했다. 게다가 동료들은
각 층에 붙잡혀 세뇌당했고,
전황은 엘윈 일행에게 매우
불리했다.

강적을 물리치고 죽음의 탑을
공략할 수 있을지는 모두 엘윈의
전술에 달려 있었다.""",
]

REGEX_REPLACEMENTS = [
    (r"Dark\s+Rod", "다크로드"),
    (r"Holy\s+Rod", "홀리로드"),
    (r"Rayguard\s+Castle", "레이갈드 성"),
    (r"Rayguard\s+Empire", "레이갈드 제국"),
    (r"Direth\s+Channel", "디레스 해협"),
    (r"Rahl\s+River", "랄강"),
    (r"Fire\s+Dragon\s+Army", "염룡병단"),
    (r"Blue\s+Dragon\s+Knights", "청룡기사단"),
    (r"Black\s+Dragon\s+Sorcerers", "흑룡마도사단"),
    (r"Ultimate\s+Aerial\s+Squadron", "궁극 비행부대"),
    (r"Words\s+of\s+Wisdom", "교훈"),
    (r"Temple\s+of\s+Darkness", "어둠의 신전"),
    (r"Prince\s+of\s+Darkness", "어둠의 왕자"),
    (r"Descendants\s+of\s+Light", "빛의 후예"),
    (r"God\s+of\s+Chaos", "혼돈의 신"),
    (r"Sword\s+of\s+Darkness", "어둠의 검"),
    (r"Dark\s+Princess", "어둠의 공주"),
    (r"Roleck\s+River", "롤렉 강"),
    (r"Grand\s+Empire", "대제국"),
    (r"Great\s+Light\s+Temple", "빛의 대신전"),
    (r"Great\s+\n?\s*빛의\s+사원", "빛의 대신전"),
    (r"Attack\s+Up", "공격 강화"),
    (r"Eggbe+rt", "에그베르트"),
    (r"BEA-U-TI-FUL", "아름답다"),
    (r"S-E-C-R-E-T", "비밀"),
    (r"\*?GRUNT\*?", "으랏"),
    (r"\*?Grunt\*?", "으랏"),
    (r"\bKO\b", "쓰러뜨리"),
    (r"\bOUR\b", "우리"),
    (r"\bYOU\b", "너"),
]

WORD_REPLACEMENTS = {
    "Alhazard": "알하자드",
    "Langrisser": "랑그릿사",
    "Rayguard": "레이갈드",
    "Velzeria": "벨제리아",
    "Kalzath": "칼자스",
    "Salrath": "살라스",
    "Reitel": "레이텔",
    "Estol": "에스톨",
    "Baltia": "발디아",
    "Eliza": "엘리자",
    "Doren": "도렌",
    "Faias": "파이어스",
    "Mireil": "미레일",
    "Idaten": "이다텐",
    "Benten": "벤텐",
    "Castle": "성",
    "Darkness": "어둠",
    "Elrahd": "엘라드",
    "By": "그런데",
    "Fire": "불",
    "Dragon": "용",
    "Army": "군",
    "Grand": "대",
    "Empire": "제국",
    "Great": "큰",
    "Attack": "공격",
    "Up": "강화",
    "Channel": "해협",
    "River": "강",
    "Lady": "아가씨",
    "Miss": "아가씨",
    "Sir": "님",
    "Lord": "주군",
}

RARE_JAMO_REPLACEMENTS = [
    ("가라앉", "침몰하"),
    ("얘기", "이야기"),
    ("얘들", "너희들"),
    ("얘야", "이봐"),
    ("걔", "그자"),
    ("늙은", "나이 든"),
    ("늙", "나이 들"),
    ("낡은", "오래된"),
    ("낡", "오래되"),
    ("붉은", "빨간"),
    ("붉", "빨갛"),
    ("맑", "깨끗하"),
    ("읽", "보다"),
    ("밟", "짓누르"),
    ("앉", "자리하"),
    ("싫", "원치 않"),
    ("옳", "맞"),
    ("뚫", "돌파하"),
    ("닳", "해지"),
    ("웨이브", "파도"),
    ("퀘", "케"),
    ("꿰", "뚫"),
    ("쉐", "셰"),
    ("짧", "짤막하"),
]

UI_TEXT_RANGES = [
    (0xA7415, 0xA74C0),
    (0xA8DA2, 0xA8F90),
    (0xA9004, 0xA905A),
    (0xA9184, 0xA91B9),
    (0xAD7E0, 0xAD820),
    (0xAE700, 0xAE740),
    (0xAE73F, 0xAF200),
    (0x1B8E04, 0x1BA07A),
    (0x1BC1DD, 0x1BC600),
]

UI_TERMS = {
    "Battle Route": "전투 경로",
    "Prologue": "서장",
    "Results": "결과",
    "Save": "저장",
    "Load": "불러",
    "Purchase Items": "아이템구매",
    "Sell Items": "아이템판매",
    "Enter Hero's Name": "주인공 이름",
    "Scenario": "시나리오",
    "Continue": "계속하기",
    "Next Scenario": "다음 시나리오",
    "No Data": "없음",
    "Bad Data": "오류",
    "Shop": "상점",
    "Move": "이동",
    "Attack": "공격",
    "Magic": "마법",
    "Summon": "소환",
    "Treat": "치료",
    "Orders": "명령",
    "Magic Arrow": "마법화살",
    "Blast": "폭발",
    "Thunder": "번개",
    "Fireball": "화염구",
    "Meteor": "운석",
    "Blizzard": "눈보라",
    "Tornado": "회오리",
    "Turn Undead": "언데드",
    "Earthquake": "지진",
    "Heal 1": "힐 1",
    "Heal 2": "힐 2",
    "Force Heal 1": "광역힐 1",
    "Force Heal 2": "광역힐 2",
    "Sleep": "수면",
    "Mute": "침묵",
    "Protection": "보호",
    "Attack Up": "공격강화",
    "Zone": "공간",
    "Teleport": "순간이동",
    "Illusion": "환영",
    "Resist": "저항",
    "Charm": "매혹",
    "Elemental": "정령",
    "Freiya": "프레이야",
    "White Dragon": "백룡",
    "Valkyrie": "발키리",
    "Sleipnir": "슬레이프",
    "Fenrir": "펜릴",
    "Yrmgard": "위르가",
    "Background Color": "배경색",
    "Button Configuration": "버튼설정",
    "Next Unit": "다음유닛",
    "Cancel": "취소",
    "Decide": "결정",
    "Options Menu": "옵션메뉴",
    "Exit": "나가기",
    "Enemy Defeated": "적 격파",
    "Enemy Killed": "적 처치",
    "Operation Miss": "작전 실패",
    "Magic Miss": "마법 실패",
    "Magic Success": "마법 성공",
    "Health Full": "체력 최대",
    "Battle": "전투",
    "Opening 1": "오프닝 1",
    "Opening 2": "오프닝 2",
    "Ending 1": "엔딩 1",
    "Ending 2": "엔딩 2",
    "Ending 3": "엔딩 3",
    "Ending 4": "엔딩 4",
    "Requiem": "진혼곡",
    "Window Open": "창 열기",
    "Window Close": "창 닫기",
    "Select 1": "선택 1",
    "Select 2": "선택 2",
    "Add": "추가",
    "Knife": "단검",
    "War Hammer": "해머",
    "Great Sword": "대검",
    "Wand": "지팡이",
    "Flame Lance": "화염창",
    "Devil Axe": "마도끼",
    "Dragon Slayer": "용살검",
    "Langrisser": "랑그릿사",
    "Masayan Sword": "마사야검",
    "Iron Dumbbell": "철아령",
    "Holy Rod": "홀리로드",
    "Dark Rod": "다크로드",
    "Alhazard": "알하자드",
    "Longbow": "장궁",
    "Arbalist": "쇠뇌",
    "Small Shield": "소형방패",
    "Large Shield": "대형방패",
    "Chain Mail": "사슬갑옷",
    "Plate Armor": "판금갑옷",
    "Assault Suit": "강습복",
    "Robe": "로브",
    "Dragonscale": "용비늘",
    "Mirage Robe": "환영로브",
    "Runestone": "룬스톤",
    "Cross": "십자가",
    "Necklace": "목걸이",
    "Orb": "보주",
    "Speedboots": "신속화",
    "Crown": "왕관",
    "Aura": "오라",
    "Angel Wing": "천사의날개",
    "Carbunkle": "카벙클",
    "Gleipnir": "글레이프",
    "Amulet": "부적",
    "Erwin": "엘윈",
    "Liana": "리나",
    "Cherie": "쉐리",
    "Hein": "헤인",
    "Scott": "스콧",
    "Keith": "키스",
    "Aaron": "아론",
    "Lester": "레스더",
    "Jessica": "제시카",
    "Mystery Knight": "수수께끼 기사",
    "Mystery": "수수께",
    "Leon": "레온",
    "Bernhardt": "베른하트",
    "Vargas": "발가스",
    "Laird": "레드",
    "Baldo": "발도",
    "Zorum": "조름",
    "Egbert": "에그벨",
    "Imelda": "이멜다",
    "Morgan": "모르건",
    "Ginam": "기남",
    "Seigal": "시갈",
    "Folgert": "폴거트",
    "Soldier": "솔저",
    "General": "장군",
    "Clergyman": "성직자",
    "Clergy": "성직",
    "Villager": "주민",
    "Pirate": "해적",
    "Town Guard": "마을경비",
    "Imperial General": "제국장군",
    "Imperial Soldier": "제국병",
    "Werewolf": "늑대인간",
    "Great Slime": "대슬라임",
    "Scylla": "스킬라",
    "Iron Golem": "철골렘",
    "Lich": "리치",
    "Living Armor": "생갑옷",
    "Vampire Lord": "흡혈군주",
    "Ghost": "유령",
    "Cerberus": "케르베르",
    "Master Dinosaur": "거대공룡",
    "Master": "마스터",
    "Dinosaur": "공룡",
    "Wyvern": "와이번",
    "Great Dragon": "대드래곤",
    "Minotaur": "미노타",
    "Kraken": "크라켄",
    "Succubus": "서큐버스",
    "Demon Lord": "마왕",
    "Demon": "악마",
    "Aniki": "형님",
    "Witch": "마녀",
    "Priest": "사제",
    "Fighter": "전사",
    "Cleric": "성직자",
    "Warlock": "흑마법",
    "Lord": "로드",
    "Knight": "기사",
    "Hawk": "매",
    "Croc": "악어",
    "Healer": "힐러",
    "Sorcerer": "마도사",
    "Shaman": "주술사",
    "High Lord": "상급로드",
    "High": "상급",
    "lander": "랜더",
    "Unicorn": "유니콘",
    "Dragon": "드래곤",
    "Serpent": "해룡",
    "Bishop": "주교",
    "Mage": "마법사",
    "Archmage": "대마법사",
    "Wizard": "위저드",
    "Saint": "성자",
    "Sage": "현자",
    "Sword Master": "검성",
    "Sword": "검사",
    "Grand": "그랜드",
    "Silver": "은",
    "King": "왕",
    "Ranger": "레인저",
    "Hero": "영웅",
    "Agent": "요원",
    "Princess": "공주",
    "Summoner": "소환사",
    "Royal Guard": "왕실근위",
    "Royal": "왕실",
    "Rider": "기수",
    "Vampire": "흡혈귀",
    "Thief": "도적",
    "Swordsman": "검사",
    "Assassin": "암살자",
    "Necro-": "사령",
    "mancer": "술사",
    "Paladin": "성기사",
    "Emperor": "황제",
    "Zarvera": "자르베라",
    "Slime": "슬라임",
    "Armor": "갑옷",
    "Dark Princess": "어둠공주",
    "Dark Master": "어둠군주",
    "Pikeman": "창병",
    "Phalanx": "방진병",
    "Gladiator": "검투사",
    "Armored Soldier": "중장병",
    "Armored": "중장",
    "Horseman": "기병",
    "Heavy Horseman": "중기병",
    "Heavy": "중",
    "Dragoon": "용기병",
    "Elf": "엘프",
    "Ballista": "발리스타",
    "Monk": "몽크",
    "Guard": "가드",
    "Merman": "어인",
    "Griffin": "그리폰",
    "Angel": "천사",
    "Civilian": "민간인",
    "Berserker": "버서커",
    "Barbarian": "야만인",
    "Dark Elf": "다크엘프",
    "Lizardman": "리자드맨",
    "Dark Guardian": "어둠수호",
    "Skeleton": "해골",
    "Zombie": "좀비",
    "Gargoyle": "가고일",
    "Wolfman": "늑대인간",
    "Bone": "뼈",
    "Leviathan": "레비아탄",
    "Golem": "골렘",
    "Bat": "박쥐",
    "Archdemon": "대악마",
    "Wraith": "망령",
    "Hellhound": "지옥견",
    "Body": "육체",
    "Builder": "단련",
}

# Wide fixed-font UI has only 56 safe tile slots when the name entry screen's
# English alphabet is preserved. The chapter 1 preparation UI already consumes
# most of that budget, so only add terms that fit within the remaining glyphs.
SAFE_WIDE_UI_TERMS: dict[str, str] = {}

DIRECT_WIDE_UI_PATCHES: list[tuple[int, int, str]] = []
DIRECT_TILEMAP16_PATCHES: list[tuple[int, int, str]] = []
DIRECT_TILEBYTE_PATCHES: list[tuple[int, int, str]] = [
    (0x9B26D, len("Player"), "P"),
    (0xA1089, len("Player"), "P"),
    (0xA2DC4, len("Player"), "P"),
    (0x9B278, len("Enemy"), "E"),
    (0xA2E53, len("Enemy"), "E"),
    (0x9B2A3, len("NPC"), "NPC"),
]
EXTRA_WIDE_FIXED_PATCHES = [
    (0x1B9418, len("Warlock"), "워록"),
    (0x1B95EC, len("Warlock"), "워록"),
    (0x1BA48C, len("Warlock"), "워록"),
    (0x1BA662, len("Warlock"), "워록"),
    (0x1BAE90, len("Warlock"), "워록"),
    (0x1BB093, len("Warlock"), "워록"),
    (0x1BB98C, len("Warlock"), "워록"),
    (0x1BBB39, len("Warlock"), "워록"),
]
ROUTE_MENU_TILE_GLYPHS: dict[str, int] = {
    # Route menu labels need more Korean glyphs than the shared fixed-font pool
    # can hold after title/status tiles are reserved. These tile IDs are blank
    # in the original fixed font and are not referenced by the route-menu text
    # tilemap itself.
    "순": 0x8B,
    "서": 0x8C,
    "동": 0x8D,
    "적": 0x8E,
    "군": 0x8F,
    "출": 0xCF,
    "격": 0xF9,
}
CUSTOM_FIXED_TILE_GLYPHS: dict[str, int] = {
    "자": 0x90,
    "금": 0x91,
    "고": 0x92,
    "상": 0x93,
    "점": 0x94,
}
DIALOGUE_NAME_GLYPHS = ("헤", "인")
TITLE_FIXED_RESERVED_TEXT = "StartLoadPressButtonNCSCorp"
TITLE_FIXED_RESERVED_CODES = (
    0xB1,
    0xB5,
    0xBE,
    0xBF,
    0xC0,
    0xC2,
    0xC3,
    0xC4,
    0xC5,
)
ROUTE_MENU_TILEMAP16_PATCHES: list[tuple[int, int, str]] = [
    (0x1E7EC8, len("Arrange"), "배치"),
    (0x1E7ED8, len("Reorder"), "순서"),
    (0x1E7EE8, len("Auto-Arrange"), "자동"),
    (0x1E7F02, len("Examine Enemy"), "적군"),
    (0x1E7F1E, len("Sortie"), "출격"),
]
NAME_ENTRY_GRID_START = 0xA3948
NAME_ENTRY_GRID_END = 0xA3ABC
NAME_ENTRY_DONE_OFFSET = 0xA3AB8
NAME_ENTRY_DONE_LENGTH = len("Done")
NAME_ENTRY_GRID_TEXT_BYTES = (
    set(range(0x30, 0x3A))
    | set(range(0x41, 0x5B))
    | set(range(0xB1, 0xCB))
    | {0x2C, 0x2D, 0x3F, 0xD0, 0xD1, 0xD2, 0xD5, 0xD6, 0xD7, 0xD8}
)
DIALOGUE_FIXED_CODE_CANDIDATES = tuple(
    list(range(0x98, 0xA4))
    + list(range(0xA9, 0xB0))
    + list(range(0xB0, 0xC0))
    + [0xCB, 0xCC, 0xD7, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF]
)
NARROW_UI_GLYPHS = {
    "병",
    "사",
    "단",
    "헤",
    "인",
    "전",
    "워",
    "록",
    "솔",
    "저",
    "가",
    "드",
    "상",
    "점",
    "소",
    "지",
    "금",
    "구",
    "매",
    "판",
    "고",
    "용",
    "검",
    "장",
    "비",
    "배",
    "치",
    "순",
    "서",
    "자",
    "동",
    "적",
    "군",
    "출",
    "격",
    "볼",
    "도",
    "파",
    "주",
}
CONDITION_POINTER_TABLE = 0x98D7A
CONDITION_POINTER_COUNT = 32
CONDITION_FIXED_GLYPHS = (
    "승",
    "리",
    "조",
    "건",
    "패",
    "배",
    "볼",
    "도",
    "주",
    "처",
    "치",
)
EXPERIENCE_BAR_TILES = set(range(0xD0, 0xE8))
DIALOGUE_ASCII_RESERVED_TEXT = "LVATDFHPMVRangeAdjustDone0123456789 .,!?:;-'\"/|+ADxE"


def complete_wide_tilemap16_patches() -> list[tuple[int, int, str]]:
    patches: list[tuple[int, int, str]] = []
    for offset, length, text in setup.WIDE_TILEMAP16_PATCHES:
        if text == "소지금":
            text = "자금"
        elif text == "용병 고용":
            text = "고용"
        elif text == "장비 착용":
            text = "장비"
        elif text == "지휘관 배치":
            text = "배치"
        patches.append((offset, length, text))
    return patches


def complete_wide_tilebyte_patches() -> list[tuple[int, int, str]]:
    patches: list[tuple[int, int, str]] = []
    for offset, length, text in setup.WIDE_TILEBYTE_PATCHES:
        if text == "소지금":
            text = "자금"
        patches.append((offset, length, text))
    return patches


def complete_wide_fixed_patches() -> list[tuple[int, int, str]]:
    patches: list[tuple[int, int, str]] = []
    for offset, length, text in setup.WIDE_FIXED_PATCHES:
        if text == "헤인":
            continue
        if text == "전사":
            text = "전사"
        if text == "솔저":
            text = "솔저"
        elif text == "가드":
            text = "가드"
        patches.append((offset, length, text))
    patches.extend(EXTRA_WIDE_FIXED_PATCHES)
    return patches


def postprocess_translation(text: str) -> str:
    for pattern, replacement in REGEX_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = text.replace(" / ", "\n")
    for pattern, replacement in REGEX_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    def replace_word(match: re.Match[str]) -> str:
        return WORD_REPLACEMENTS.get(match.group(0), "그")

    text = re.sub(r"[A-Za-z][A-Za-z\-]*", replace_word, text)
    text = text.replace("[em", "그들").replace(']운명"', "운명")
    for old, new in RARE_JAMO_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def is_jamo(ch: str) -> bool:
    return "\u3130" <= ch <= "\u318f"


def simplify_compat_jamo_text(text: str) -> str:
    out: list[str] = []
    for ch in base.to_compat_jamo(text):
        out.append(COMPOUND_JAMO_FALLBACKS.get(ch, ch))
    return "".join(out)


def collect_vwf_jamo(records: list[dict[str, object]]) -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    sources = [str(record["translation"]) for record in records]
    sources.extend(SCENARIO_DESCRIPTIONS)
    for text in sources:
        for ch in simplify_compat_jamo_text(text):
            if is_jamo(ch) and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    return chars


def collect_opening_hangul() -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    for parts in base.OPENING_PARTS.values():
        for part in parts:
            if not isinstance(part, str):
                continue
            for ch in part:
                if "가" <= ch <= "힣" and ch not in seen:
                    seen.add(ch)
                    chars.append(ch)
    return chars


def assign_vwf_codes(
    chars: list[str],
    opening_chars: list[str],
    preferred_jamo_map: dict[str, int] | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    reserved = set(VWF_ASCII_RESERVED) | set(VWF_RESERVED)
    if preferred_jamo_map is None:
        pool = [code for code in range(0x21, 0x7F) if code not in reserved]
        required = len(chars) + len(opening_chars)
        if required > len(pool):
            raise ValueError(f"Need {required} VWF slots, only {len(pool)} UI-safe slots")
        jamo_map = {ch: pool[idx] for idx, ch in enumerate(chars)}
    else:
        missing = [ch for ch in chars if ch not in preferred_jamo_map]
        if missing:
            raise ValueError(f"Missing preferred VWF codes for {missing}")
        jamo_map = {ch: preferred_jamo_map[ch] for ch in chars}
        bad_codes = [code for code in jamo_map.values() if code in reserved or not (0x21 <= code < 0x7F)]
        if bad_codes:
            raise ValueError(f"Preferred VWF codes are not VWF-safe: {bad_codes}")
        if len(set(jamo_map.values())) != len(jamo_map):
            raise ValueError("Preferred VWF jamo codes collide")

    used = reserved | set(jamo_map.values())
    opening_pool = [code for code in range(0x21, 0x7F) if code not in used]
    if len(opening_chars) > len(opening_pool):
        raise ValueError(f"Need {len(opening_chars)} opening VWF slots, only {len(opening_pool)} available")
    opening_map = {ch: opening_pool[idx] for idx, ch in enumerate(opening_chars)}
    return jamo_map, opening_map


def build_opening_glyph(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    import build_korean_wip as opening_wip

    return opening_wip.render_opening_glyph(text, font)


def encode_complete_opening_part(parts: list[str | bytes], opening_code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for part in parts:
        if isinstance(part, bytes):
            out.extend(part)
        else:
            for ch in part:
                if "가" <= ch <= "힣":
                    out.append(opening_code_map[ch])
                elif 0x20 <= ord(ch) <= 0x7E:
                    out.append(ord(ch))
                else:
                    out.append(ord("?"))
    return bytes(out)


def encode_scenario_text(text: str, code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in simplify_compat_jamo_text(text):
        if ch == "\n":
            out.append(0x0A)
        elif is_jamo(ch):
            out.append(code_map[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ord(ch))
        else:
            out.append(ord("?"))
    out.append(0x00)
    return bytes(out)


def encode_vwf_text(text: str, code_map: dict[str, int]) -> bytes:
    text = text.replace(" / ", "\n").replace("/", "\n")
    units: list[int] = []
    for ch in simplify_compat_jamo_text(text):
        if ch == "\n":
            units.append(0xFE)
        elif is_jamo(ch):
            units.append(code_map[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            units.append(ord(ch))
        else:
            units.append(ord("?"))
    return bytes(base.wrap_units(units))


def encode_vwf_inline(text: str, code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in simplify_compat_jamo_text(text):
        if ch == "\n":
            out.append(0x0A)
        elif is_jamo(ch):
            out.append(code_map[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ord(ch))
        else:
            out.append(ord("?"))
    return bytes(out)


def patch_vwf_inline_at(rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, int]) -> None:
    encoded = encode_vwf_inline(text, code_map)
    if len(encoded) > length:
        raise ValueError(f"VWF inline patch too long at 0x{offset:x}: {len(encoded)} > {length}: {text}")
    rom[offset : offset + length] = encoded + b" " * (length - len(encoded))


def patch_condition_fixed_inline_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, ...]]
) -> None:
    encoded = encode_condition_text(text, code_map)
    if len(encoded) > length:
        raise ValueError(f"condition fixed patch too long at 0x{offset:x}: {len(encoded)} > {length}: {text}")
    rom[offset : offset + length] = encoded + b" " * (length - len(encoded))


def patch_condition_screen_labels(rom: bytearray, code_map: dict[str, tuple[int, ...]]) -> int:
    patch_condition_fixed_inline_at(rom, 0xAD7F3, len("Conditions"), "조건", code_map)
    patch_condition_fixed_inline_at(rom, 0xAD80B, len("Scenario"), "1", code_map)
    return 2


def patch_condition_number_loop(rom: bytearray) -> int:
    # The original code scans the scenario-description text for the final
    # "o" in "Scenario", then prints the bytes after it as the number/title.
    # Korean descriptions do not contain that marker, so it can find a random
    # glyph code and print garbage. The localized label already includes "1".
    rom[0xAD6DA:0xAD6E4] = b"\x4E\x71" * 5
    return 1


def patch_scenario_descriptions(rom: bytearray, cursor: int, code_map: dict[str, int]) -> int:
    if len(SCENARIO_DESCRIPTIONS) != SCENARIO_COUNT:
        raise ValueError(f"Expected {SCENARIO_COUNT} scenario descriptions")
    for idx, text in enumerate(SCENARIO_DESCRIPTIONS):
        encoded = encode_scenario_text(text, code_map)
        pointer = SCENARIO_POINTER_TABLE + idx * 4
        rom[pointer : pointer + 4] = cursor.to_bytes(4, "big")
        rom[cursor : cursor + len(encoded)] = encoded
        cursor += len(encoded)
        if cursor & 1:
            cursor += 1
    return cursor


def wide_text_width(text: str) -> int:
    total = 0
    for ch in text:
        if ch == " " or 0x20 <= ord(ch) <= 0x7E:
            total += 1
        else:
            total += 2
    return total


def collect_wide_glyphs(texts: list[str], first_glyphs: tuple[str, ...] = ()) -> list[str]:
    glyphs: list[str] = []
    seen: set[str] = set()
    for glyph in first_glyphs:
        if glyph not in seen:
            seen.add(glyph)
            glyphs.append(glyph)
    for text in texts:
        for ch in text:
            value = ord(ch)
            if value < 0x20 or ch == " " or 0x20 <= value <= 0x7E or 0xC0 <= value <= 0xDF:
                continue
            if ch in CUSTOM_FIXED_TILE_GLYPHS:
                continue
            if ch in ROUTE_MENU_TILE_GLYPHS:
                continue
            if ch not in seen:
                seen.add(ch)
                glyphs.append(ch)
    return glyphs


def fixed_code_pool(
    *,
    ascii_only: bool = False,
    extra_reserved_codes: set[int] | None = None,
    extra_reserved_tiles: set[int] | None = None,
) -> list[int]:
    reserved_tiles = {ord(ch) for ch in DIALOGUE_ASCII_RESERVED_TEXT}
    reserved_tiles.update(chapter1.map_fixed_tile(ord(ch)) for ch in DIALOGUE_ASCII_RESERVED_TEXT)
    reserved_tiles.update(ord(ch) for ch in TITLE_FIXED_RESERVED_TEXT)
    reserved_tiles.update(chapter1.map_fixed_tile(ord(ch)) for ch in TITLE_FIXED_RESERVED_TEXT)
    reserved_tiles.update(TITLE_FIXED_RESERVED_CODES)
    reserved_tiles.update(chapter1.map_fixed_tile(code) for code in TITLE_FIXED_RESERVED_CODES)
    # The status panels and UI frames use several non-ASCII fixed tiles.
    # F=0x24, V=0x26, P=0x28; 0x29/0x3C/0x3D/0x40/0x7B are visible frame
    # or separator tiles on route/conditions/prep screens.
    # Raw/mapped lowercase-v tiles are also visible in the name entry grid.
    reserved_tiles.update(
        {
            0x24,
            0x26,
            0x28,
            0x29,
            0x3B,
            0x3C,
            0x3D,
            0x40,
            0x76,
            0x7B,
            0xC6,
            0xF8,
        }
    )
    reserved_tiles.update(range(0x41, 0x5B))
    # These fixed-font tiles are also used as the move/fight/guard/manual
    # order icons on unit sprites. Overwriting them turns the icons into text.
    reserved_tiles.update(range(0xF4, 0xF8))
    reserved_tiles.update(EXPERIENCE_BAR_TILES)
    if extra_reserved_tiles:
        reserved_tiles.update(extra_reserved_tiles)
    reserved_codes = set(extra_reserved_codes or ())
    reserved_tiles.update(chapter1.map_fixed_tile(code) for code in reserved_codes)
    code_pool: list[int] = []
    used_tiles: set[int] = set()
    source_codes = list(range(0x21, 0x7F)) if ascii_only else chapter1.CODE_POOL + list(range(0xC0, 0x100))
    for code in source_codes:
        tile = chapter1.map_fixed_tile(code)
        if tile in used_tiles or tile in reserved_tiles or code in reserved_tiles or code in reserved_codes:
            continue
        used_tiles.add(tile)
        code_pool.append(code)
    return code_pool


def assign_ascii_dialogue_fixed_codes(chars: list[str], extra_reserved_codes: set[int] | None = None) -> dict[str, int]:
    code_pool = fixed_code_pool(ascii_only=True, extra_reserved_codes=extra_reserved_codes)
    glyphs = list(chars)
    glyphs.extend(glyph for glyph in DIALOGUE_NAME_GLYPHS if glyph not in glyphs)
    if len(glyphs) > len(code_pool):
        raise ValueError(f"Need {len(glyphs)} dialogue glyph slots, only {len(code_pool)} ASCII-safe slots")
    return {ch: code_pool[idx] for idx, ch in enumerate(glyphs)}


def assign_extended_dialogue_fixed_codes(
    chars: list[str],
    *,
    extra_reserved_codes: set[int] | None = None,
    extra_reserved_tiles: set[int] | None = None,
) -> dict[str, int]:
    reserved_codes = set(extra_reserved_codes or ())
    reserved_codes.update({0xFE, 0xFF})
    reserved_tiles = set(extra_reserved_tiles or ())
    reserved_tiles.update(NAME_ENTRY_GRID_TEXT_BYTES)
    reserved_tiles.update(TITLE_FIXED_RESERVED_CODES)
    reserved_tiles.update(chapter1.map_fixed_tile(code) for code in TITLE_FIXED_RESERVED_CODES)
    reserved_tiles.update(chapter1.map_fixed_tile(code) for code in DIALOGUE_ASCII_RESERVED_TEXT.encode("ascii"))
    reserved_tiles.update(chapter1.map_fixed_tile(code) for code in TITLE_FIXED_RESERVED_TEXT.encode("ascii"))
    reserved_tiles.update({0x24, 0x26, 0x28, 0x29, 0x3B, 0x3C, 0x3D, 0x40, 0x77, 0x7B, 0xB0, 0xCB, 0xF8, 0xFA})
    reserved_tiles.update(range(0x80, 0x8B))
    reserved_tiles.update(range(0x95, 0xA9))
    reserved_tiles.update(range(0xF4, 0xF9))
    reserved_tiles.update(EXPERIENCE_BAR_TILES)

    code_pool: list[int] = []
    used_tiles: set[int] = set()
    for code, tile in zip(DIALOGUE_CUSTOM_CODES, DIALOGUE_CUSTOM_TILES):
        tile = dialogue_fixed_tile(code)
        if code in reserved_codes or tile in reserved_tiles or tile in used_tiles:
            continue
        used_tiles.add(tile)
        code_pool.append(code)

    glyphs = list(chars)
    glyphs.extend(glyph for glyph in DIALOGUE_NAME_GLYPHS if glyph not in glyphs)
    if len(glyphs) > len(code_pool):
        raise ValueError(f"Need {len(glyphs)} dialogue glyph slots, only {len(code_pool)} extended slots")
    return {ch: code_pool[idx] for idx, ch in enumerate(glyphs)}


def dialogue_fixed_tile(code: int) -> int:
    if USE_EXTENDED_DIALOGUE_CODES and code in DIALOGUE_CUSTOM_TILE_BY_CODE:
        return DIALOGUE_CUSTOM_TILE_BY_CODE[code]
    return chapter1.map_fixed_tile(code)


def patch_dialogue_copy_limit(rom: bytearray) -> int:
    if not USE_EXTENDED_DIALOGUE_CODES:
        return 0
    if rom[DIALOGUE_COPY_LIMIT_OFFSET] != 0x7F:
        raise ValueError(f"unexpected dialogue copy limit byte: 0x{rom[DIALOGUE_COPY_LIMIT_OFFSET]:02x}")
    rom[DIALOGUE_COPY_LIMIT_OFFSET] = DIALOGUE_COPY_LIMIT
    return 1


def patch_dialogue_tile_mapper(rom: bytearray) -> int:
    if not USE_EXTENDED_DIALOGUE_CODES:
        return 0
    original = bytes(rom[DIALOGUE_MAPPER_START_OFFSET:DIALOGUE_MAPPER_END_OFFSET])
    expected_prefix = bytes.fromhex("b0 3c 00 0e 67 72")
    if not original.startswith(expected_prefix):
        raise ValueError(f"unexpected dialogue mapper prefix: {original[:6].hex(' ')}")
    hook_len = len(DIALOGUE_CUSTOM_TILES) * 12 + len(original)
    hook_end = DIALOGUE_MAPPER_HOOK_OFFSET + hook_len
    if any(byte != 0xFF for byte in rom[DIALOGUE_MAPPER_HOOK_OFFSET:hook_end]):
        raise ValueError("dialogue mapper hook space is not empty")

    hook = bytearray()
    for code, tile in zip(DIALOGUE_CUSTOM_CODES, DIALOGUE_CUSTOM_TILES):
        # cmp.b #code,d0; bne.s +6; move.b #tile,d0; rts
        hook.extend((0xB0, 0x3C, 0x00, code, 0x66, 0x06, 0x10, 0x3C, 0x00, tile, 0x4E, 0x75))
    hook.extend(original)

    rom[DIALOGUE_MAPPER_HOOK_OFFSET:hook_end] = hook
    rom[DIALOGUE_MAPPER_START_OFFSET : DIALOGUE_MAPPER_START_OFFSET + 6] = (
        b"\x4E\xF9" + DIALOGUE_MAPPER_HOOK_OFFSET.to_bytes(4, "big")
    )
    return len(hook) + 6


def patch_dialogue_fixed_font(
    rom: bytearray, code_map: dict[str, int], font: ImageFont.FreeTypeFont
) -> list[tuple[str, int, int]]:
    mapped: list[tuple[str, int, int]] = []
    used_tiles: dict[int, str] = {}
    for glyph, code in code_map.items():
        tile = dialogue_fixed_tile(code)
        if tile in used_tiles:
            raise ValueError(f"dialogue tile collision: {glyph!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
        used_tiles[tile] = glyph
        tile_off = chapter1.FIXED_FONT_BASE + tile * chapter1.FIXED_TILE_SIZE
        rom[tile_off : tile_off + chapter1.FIXED_TILE_SIZE] = fixedfont.render_fixed_glyph(glyph, font)
        mapped.append((glyph, code, tile))
    return mapped


def assign_extended_fixed_codes(
    wide_glyphs: list[str],
    narrow_glyphs: tuple[str, ...],
    extra_reserved_codes: set[int] | None = None,
    extra_reserved_tiles: set[int] | None = None,
) -> tuple[dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
    code_pool = fixed_code_pool(extra_reserved_codes=extra_reserved_codes, extra_reserved_tiles=extra_reserved_tiles)
    narrow_set = set(narrow_glyphs)
    required = len(narrow_glyphs) + sum(
        1 if glyph in NARROW_UI_GLYPHS else 2 for glyph in wide_glyphs if glyph not in narrow_set
    )
    if required > len(code_pool):
        raise ValueError(f"Need {required} wide glyph slots, only {len(code_pool)}")

    wide_code_map: dict[str, tuple[int, ...]] = {}
    narrow_code_map: dict[str, tuple[int, ...]] = {}
    idx = 0
    for glyph in narrow_glyphs:
        narrow_code_map[glyph] = (code_pool[idx],)
        idx += 1
    for glyph in wide_glyphs:
        if glyph in narrow_code_map:
            wide_code_map[glyph] = narrow_code_map[glyph]
            continue
        width = 1 if glyph in NARROW_UI_GLYPHS else 2
        wide_code_map[glyph] = tuple(code_pool[idx : idx + width])
        idx += width
    return wide_code_map, narrow_code_map


def render_narrow_fixed_glyph(text: str) -> bytes:
    font_size = 8 if chapter1.FIXED_FONT_PATH.name.startswith("Galmuri") else 8 * 8
    font = ImageFont.truetype(str(chapter1.FIXED_FONT_PATH), font_size)
    canvas = Image.new("L", (8, 8), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (8 - width) // 2 - bbox[0]
    y = (8 - height) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)
    pixels: list[list[int]] = []
    for yy in range(8):
        row: list[int] = []
        for xx in range(8):
            row.append(3 if canvas.getpixel((xx, yy)) >= 96 else 1)
        pixels.append(row)
    return chapter1.encode_fixed_tile(pixels)


def patch_extended_fixed_font(
    rom: bytearray,
    code_map: dict[str, tuple[int, ...]],
    used_tiles: dict[int, str] | None = None,
) -> None:
    if used_tiles is None:
        used_tiles = {}
    for glyph, codes in code_map.items():
        tiles = tuple(chapter1.map_fixed_tile(code) for code in codes)
        for tile in tiles:
            if tile in used_tiles:
                if used_tiles[tile] == glyph:
                    continue
                raise ValueError(f"tile collision: {glyph!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
            used_tiles[tile] = glyph

        if len(codes) == 1:
            tile_data = render_narrow_fixed_glyph(glyph)
            tile_off = chapter1.FIXED_FONT_BASE + tiles[0] * chapter1.FIXED_TILE_SIZE
            rom[tile_off : tile_off + chapter1.FIXED_TILE_SIZE] = tile_data
        elif len(codes) == 2:
            left, right = setup.render_wide_fixed_glyph(glyph)
            left_off = chapter1.FIXED_FONT_BASE + tiles[0] * chapter1.FIXED_TILE_SIZE
            right_off = chapter1.FIXED_FONT_BASE + tiles[1] * chapter1.FIXED_TILE_SIZE
            rom[left_off : left_off + chapter1.FIXED_TILE_SIZE] = left
            rom[right_off : right_off + chapter1.FIXED_TILE_SIZE] = right
        else:
            raise ValueError(f"unsupported fixed glyph width for {glyph!r}: {codes}")


def patch_custom_fixed_tiles(rom: bytearray, used_tiles: dict[int, str] | None = None) -> None:
    if used_tiles is None:
        used_tiles = {}
    for glyph, tile in CUSTOM_FIXED_TILE_GLYPHS.items():
        if tile in used_tiles and used_tiles[tile] != glyph:
            raise ValueError(f"custom tile collision: {glyph!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
        used_tiles[tile] = glyph
        tile_off = chapter1.FIXED_FONT_BASE + tile * chapter1.FIXED_TILE_SIZE
        rom[tile_off : tile_off + chapter1.FIXED_TILE_SIZE] = render_narrow_fixed_glyph(glyph)


def patch_wide_text_mixed_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, ...]]
) -> None:
    codes: list[int] = []
    for ch in text:
        if ch == " ":
            codes.append(0x20)
        elif 0x20 <= ord(ch) <= 0x7E:
            codes.append(ord(ch))
        else:
            codes.extend(code_map[ch])
    if len(codes) > length:
        raise ValueError(f"wide patch too long at 0x{offset:x}: {len(codes)} > {length}: {text}")
    rom[offset : offset + length] = bytes(codes + [0x20] * (length - len(codes)))


def encode_wide_text_mixed(text: str, code_map: dict[str, tuple[int, ...]]) -> bytes:
    out: list[int] = []
    for ch in text:
        if ch == " ":
            out.append(0x20)
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ord(ch))
        else:
            out.extend(code_map[ch])
    return bytes(out)


def encode_mixed_tile_ids(text: str, code_map: dict[str, tuple[int, ...]]) -> list[int]:
    tiles: list[int] = []
    for ch in text:
        if ch == " ":
            tiles.append(0x20)
        elif ch in CUSTOM_FIXED_TILE_GLYPHS:
            tiles.append(CUSTOM_FIXED_TILE_GLYPHS[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            tiles.append(chapter1.map_fixed_tile(ord(ch)))
        else:
            tiles.extend(chapter1.map_fixed_tile(code) for code in code_map[ch])
    return tiles


def patch_mixed_tilemap16_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, ...]]
) -> None:
    tiles = encode_mixed_tile_ids(text, code_map)
    if len(tiles) > length:
        raise ValueError(f"mixed tilemap patch too long at 0x{offset:x}: {len(tiles)} > {length}: {text}")
    tiles.extend([0x20] * (length - len(tiles)))
    for idx, tile in enumerate(tiles):
        pos = offset + idx * 2
        rom[pos : pos + 2] = tile.to_bytes(2, "big")


def patch_mixed_tilebytes_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, ...]]
) -> None:
    tiles = encode_mixed_tile_ids(text, code_map)
    if len(tiles) > length:
        raise ValueError(f"mixed tile byte patch too long at 0x{offset:x}: {len(tiles)} > {length}: {text}")
    rom[offset : offset + length] = bytes(tiles + [0x20] * (length - len(tiles)))


def route_menu_tile_ids(text: str, code_map: dict[str, tuple[int, ...]]) -> list[int]:
    tiles: list[int] = []
    for ch in text:
        if ch == " ":
            tiles.append(0x20)
        elif ch in CUSTOM_FIXED_TILE_GLYPHS:
            tiles.append(CUSTOM_FIXED_TILE_GLYPHS[ch])
        elif ch in ROUTE_MENU_TILE_GLYPHS:
            tiles.append(ROUTE_MENU_TILE_GLYPHS[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            tiles.append(chapter1.map_fixed_tile(ord(ch)))
        else:
            tiles.extend(chapter1.map_fixed_tile(code) for code in code_map[ch])
    return tiles


def patch_route_menu_tilemap16_at(
    rom: bytearray, offset: int, length: int, text: str, code_map: dict[str, tuple[int, ...]]
) -> None:
    tiles = route_menu_tile_ids(text, code_map)
    if len(tiles) > length:
        raise ValueError(f"route menu patch too long at 0x{offset:x}: {len(tiles)} > {length}: {text}")
    tiles.extend([0x20] * (length - len(tiles)))
    for idx, tile in enumerate(tiles):
        pos = offset + idx * 2
        rom[pos : pos + 2] = tile.to_bytes(2, "big")


def patch_route_menu(rom: bytearray, code_map: dict[str, tuple[int, ...]]) -> int:
    for glyph, tile in ROUTE_MENU_TILE_GLYPHS.items():
        tile_off = chapter1.FIXED_FONT_BASE + tile * chapter1.FIXED_TILE_SIZE
        rom[tile_off : tile_off + chapter1.FIXED_TILE_SIZE] = render_narrow_fixed_glyph(glyph)

    patched = 0
    for offset, length, text in ROUTE_MENU_TILEMAP16_PATCHES:
        patch_route_menu_tilemap16_at(rom, offset, length, text, code_map)
        patched += 1
    return patched


def patch_name_entry_display(rom: bytearray, code_map: dict[str, tuple[int, ...]]) -> int:
    if USE_EXTENDED_DIALOGUE_CODES:
        return 0

    patched = 0
    for offset in range(NAME_ENTRY_GRID_START, NAME_ENTRY_GRID_END):
        if NAME_ENTRY_DONE_OFFSET <= offset < NAME_ENTRY_DONE_OFFSET + NAME_ENTRY_DONE_LENGTH:
            continue
        if rom[offset] in NAME_ENTRY_GRID_TEXT_BYTES:
            rom[offset] = 0x20
            patched += 1

    # Keep the default first initial visible. The Done command stays byte-for-byte
    # original because the name-entry logic uses this script for selection.
    # The selection table remains original, so the existing input flow still works.
    rom[NAME_ENTRY_GRID_START] = ord("A")
    return patched + 1


def patch_dialogue_name_tables(rom: bytearray, dialogue_code_map: dict[str, int]) -> int:
    hein = bytes([dialogue_code_map["헤"], dialogue_code_map["인"], 0x20, 0x20])
    patched = 0
    for offset in (0x1B8E22, 0x1B9C21, 0x1BC1F5):
        rom[offset : offset + len("Hein")] = hein
        patched += 1
    return patched


def encode_condition_text(text: str, code_map: dict[str, tuple[int, ...]]) -> bytes:
    out: list[int] = []
    for ch in text:
        value = ord(ch)
        if ch == " " or ch == "\n" or ch == "-":
            out.append(value)
        elif 0xC0 <= value <= 0xDF:
            out.append(value)
        elif 0x20 <= value <= 0x7E:
            out.append(value)
        else:
            out.extend(code_map[ch])
    return bytes(out)


CONDITION_TEXT_OVERRIDES = {
    0: "Victory\n -볼도 처치\n\nDefeat\n -볼도 도주\n -\xc1 패배",
}


def patch_condition_texts(rom: bytearray, code_map: dict[str, tuple[int, ...]]) -> int:
    patched = 0
    for idx, text in CONDITION_TEXT_OVERRIDES.items():
        if idx >= CONDITION_POINTER_COUNT:
            continue
        pointer = CONDITION_POINTER_TABLE + idx * 4
        start = int.from_bytes(rom[pointer : pointer + 4], "big")
        if not (0x98000 <= start < 0x9A000):
            continue
        end = rom.index(0x00, start)
        encoded = encode_condition_text(text, code_map)
        if len(encoded) > end - start:
            raise ValueError(f"condition text {idx} too long: {len(encoded)} > {end - start}")
        rom[start:end] = encoded + b" " * (end - start - len(encoded))
        patched += 1
    return patched


def patch_condition_headings(rom: bytearray, code_map: dict[str, tuple[int, ...]]) -> int:
    victory = encode_wide_text_mixed("승리조건", code_map)
    defeat = encode_wide_text_mixed("패배조건", code_map)
    if any(byte >= 0xC0 for byte in victory + defeat):
        raise ValueError("condition heading codes must stay below 0xc0 to avoid name-token conflicts")

    patched = 0
    for idx in range(CONDITION_POINTER_COUNT):
        pointer = CONDITION_POINTER_TABLE + idx * 4
        start = int.from_bytes(rom[pointer : pointer + 4], "big")
        if not (0x98000 <= start < 0x9A000):
            continue
        end = rom.index(0x00, start)
        data = bytearray(rom[start:end])
        old = bytes(data)
        if data.startswith(b"Victory\n"):
            data[: len(b"Victory")] = victory + b" " * (len(b"Victory") - len(victory))
        data = data.replace(b"\n\nDefeat\n", b"\n\n" + defeat + b" " * (len(b"Defeat") - len(defeat)) + b"\n")
        if bytes(data) != old:
            rom[start:end] = data
            patched += 1
    return patched


def build_search_ui_patches(source_rom: bytes) -> list[tuple[int, int, str]]:
    patches: list[tuple[int, int, str]] = []
    occupied: set[int] = set()
    terms = sorted(SAFE_WIDE_UI_TERMS.items(), key=lambda item: len(item[0]), reverse=True)
    for start, end in UI_TEXT_RANGES:
        for english, korean in terms:
            width = wide_text_width(korean)
            needle = english.encode("ascii")
            if width > len(needle):
                continue
            pos = start
            while True:
                hit = source_rom.find(needle, pos, end)
                if hit < 0:
                    break
                span = set(range(hit, hit + len(needle)))
                if not (span & occupied):
                    patches.append((hit, len(needle), korean))
                    occupied.update(span)
                pos = hit + 1
    return sorted(patches)


def apply_full_wide_ui_patches(
    rom: bytearray,
    source_rom: bytes,
    code_map: dict[str, tuple[int, ...]],
    condition_code_map: dict[str, tuple[int, ...]],
) -> int:
    used_tiles: dict[int, str] = {}
    patch_extended_fixed_font(rom, condition_code_map, used_tiles)
    patch_extended_fixed_font(rom, code_map, used_tiles)
    patch_custom_fixed_tiles(rom, used_tiles)
    patches = complete_wide_fixed_patches()
    patches.extend(build_search_ui_patches(source_rom))
    seen: set[tuple[int, int]] = set()
    applied = 0
    for offset, length, text in patches:
        key = (offset, length)
        if key in seen:
            continue
        seen.add(key)
        patch_wide_text_mixed_at(rom, offset, length, text, code_map)
        applied += 1
    for offset, length, text in DIRECT_WIDE_UI_PATCHES:
        patch_wide_text_mixed_at(rom, offset, length, text, code_map)
        applied += 1
    for offset, length, text in DIRECT_TILEMAP16_PATCHES:
        patch_mixed_tilemap16_at(rom, offset, length, text, code_map)
        applied += 1
    for offset, length, text in DIRECT_TILEBYTE_PATCHES:
        patch_mixed_tilebytes_at(rom, offset, length, text, code_map)
        applied += 1
    for offset, length, text in complete_wide_tilemap16_patches():
        patch_mixed_tilemap16_at(rom, offset, length, text, code_map)
        applied += 1
    for offset, length, text in complete_wide_tilebyte_patches():
        patch_mixed_tilebytes_at(rom, offset, length, text, code_map)
        applied += 1
    return applied


def main() -> int:
    if not base.FONT_PATH.exists():
        raise FileNotFoundError(base.FONT_PATH)

    source_rom = base.SRC.read_bytes()
    records = json.loads(base.TRANS.read_text(encoding="utf-8"))
    overrides = chapter1_natural.chapter1_record_translations(records)
    for record in records:
        idx = int(record["index"])
        text = overrides.get(idx, str(record["translation"]))
        record["translation"] = postprocess_translation(text)

    vwf_chars = collect_vwf_jamo(records)
    opening_chars = collect_opening_hangul()
    vwf_reserved = set(VWF_ASCII_RESERVED) | set(VWF_RESERVED)
    vwf_code_map, opening_code_map = assign_vwf_codes(vwf_chars, opening_chars)

    ui_patch_texts = [text for _, _, text in complete_wide_fixed_patches()]
    ui_patch_texts.extend(SAFE_WIDE_UI_TERMS.values())
    ui_patch_texts.extend(text for _, _, text in DIRECT_WIDE_UI_PATCHES)
    ui_patch_texts.extend(text for _, _, text in complete_wide_tilemap16_patches())
    ui_patch_texts.extend(text for _, _, text in complete_wide_tilebyte_patches())
    ui_patch_texts.extend(text for _, _, text in DIRECT_TILEMAP16_PATCHES)
    ui_patch_texts.extend(text for _, _, text in DIRECT_TILEBYTE_PATCHES)
    ui_patch_texts.extend(text for _, _, text in ROUTE_MENU_TILEMAP16_PATCHES)
    wide_chars = collect_wide_glyphs(ui_patch_texts)
    wide_code_map, condition_code_map = assign_extended_fixed_codes(
        wide_chars,
        CONDITION_FIXED_GLYPHS,
        extra_reserved_codes=set(DIALOGUE_CUSTOM_CODES),
        extra_reserved_tiles=set(DIALOGUE_CUSTOM_TILES),
    )
    ui_dialogue_reserved_tiles = set(CUSTOM_FIXED_TILE_GLYPHS.values()) | set(ROUTE_MENU_TILE_GLYPHS.values())
    ui_dialogue_reserved_tiles.update(chapter1.map_fixed_tile(code) for codes in wide_code_map.values() for code in codes)
    ui_dialogue_reserved_tiles.update(
        chapter1.map_fixed_tile(code) for codes in condition_code_map.values() for code in codes
    )
    dialogue_code_map = assign_extended_dialogue_fixed_codes(
        vwf_chars,
        extra_reserved_codes=vwf_reserved,
        extra_reserved_tiles=ui_dialogue_reserved_tiles,
    )

    rom = bytearray(source_rom)
    dialogue_copy_limit_patches = patch_dialogue_copy_limit(rom)
    dialogue_tile_mapper_patches = patch_dialogue_tile_mapper(rom)
    font_vwf = ImageFont.truetype(str(base.FONT_PATH), 16 * 8)

    copy_size = base.font_copy_size(rom)
    rom[base.RELOCATED_BITMAP_TABLE : base.RELOCATED_BITMAP_TABLE + copy_size] = rom[
        base.ORIGINAL_BITMAP_TABLE : base.ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[base.BITMAP_BASE_PATCH : base.BITMAP_BASE_PATCH + 4] = base.RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    font_cursor = base.RELOCATED_BITMAP_TABLE + copy_size
    for ch, code in vwf_code_map.items():
        glyph = base.render_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (font_cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        cursor_end = font_cursor + len(glyph)
        rom[font_cursor:cursor_end] = glyph
        font_cursor = cursor_end + (cursor_end & 1)

    for ch, code in opening_code_map.items():
        glyph = build_opening_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (font_cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        cursor_end = font_cursor + len(glyph)
        rom[font_cursor:cursor_end] = glyph
        font_cursor = cursor_end + (cursor_end & 1)

    font_fixed_dialogue = ImageFont.truetype(str(base.FONT_PATH), 8 * 8)
    fixed_dialogue_mapped = patch_dialogue_fixed_font(rom, dialogue_code_map, font_fixed_dialogue)

    old_to_new: dict[int, int] = {}
    script_cursor = base.SCRIPT_BASE
    rom[base.SCRIPT_BASE : base.SCRIPT_LIMIT] = b"\xff" * (base.SCRIPT_LIMIT - base.SCRIPT_BASE)
    for record in records:
        old = int(str(record["address"]), 16)
        prefix = bytes.fromhex(str(record["prefix"]))
        encoded = prefix + encode_vwf_text(str(record["translation"]), dialogue_code_map) + b"\xff\xff"
        old_to_new[old] = script_cursor
        rom[script_cursor : script_cursor + len(encoded)] = encoded
        script_cursor += len(encoded)
        if script_cursor & 1:
            script_cursor += 1

    patch_ranges = [(0x88000, 0x96000), (base.SCRIPT_LIMIT, 0x1F0000)]
    for old, new in old_to_new.items():
        old_b = old.to_bytes(4, "big")
        new_b = new.to_bytes(4, "big")
        for range_start, range_end in patch_ranges:
            start = range_start
            while True:
                hit = rom.find(old_b, start, range_end)
                if hit < 0:
                    break
                rom[hit : hit + 4] = new_b
                start = hit + 4

    data_cursor = script_cursor
    for name, parts in base.OPENING_PARTS.items():
        encoded = encode_complete_opening_part(parts, opening_code_map)
        rom[base.OPENING_POINTER_PATCHES[name] : base.OPENING_POINTER_PATCHES[name] + 4] = data_cursor.to_bytes(
            4, "big"
        )
        rom[data_cursor : data_cursor + len(encoded)] = encoded
        data_cursor += len(encoded)
        if data_cursor & 1:
            data_cursor += 1

    scenario_start = data_cursor
    data_cursor = patch_scenario_descriptions(rom, data_cursor, vwf_code_map)
    if data_cursor >= base.SCRIPT_LIMIT:
        raise ValueError(f"script overflow: 0x{data_cursor:x} >= 0x{base.SCRIPT_LIMIT:x}")

    ui_patches = apply_full_wide_ui_patches(rom, source_rom, wide_code_map, condition_code_map)
    dialogue_name_patches = patch_dialogue_name_tables(rom, dialogue_code_map)
    combined_condition_map = {**wide_code_map, **condition_code_map}
    condition_text_patches = patch_condition_texts(rom, combined_condition_map)
    condition_heading_patches = patch_condition_headings(rom, condition_code_map)
    condition_label_patches = patch_condition_screen_labels(rom, combined_condition_map)
    condition_number_patches = patch_condition_number_loop(rom)
    route_menu_patches = patch_route_menu(rom, combined_condition_map)
    name_entry_patches = patch_name_entry_display(rom, combined_condition_map)

    base.update_checksum_and_header(rom)
    OUT.write_bytes(rom)

    english_residue = [
        int(record["index"])
        for record in records
        if re.search(r"[A-Za-z]{2,}", str(record["translation"]))
    ]
    vwf_pool_size = len(set(range(0x21, 0x7F)) - vwf_reserved)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"records: {len(records)}")
    print(f"chapter 1 natural overrides: {len(overrides)}")
    print(f"VWF jamo glyphs: {len(vwf_chars)} / opening Hangul glyphs {len(opening_chars)} / reserved pool {vwf_pool_size}")
    condition_set = set(CONDITION_FIXED_GLYPHS)
    fixed_slots = len(CONDITION_FIXED_GLYPHS) + sum(
        1 if glyph in NARROW_UI_GLYPHS else 2 for glyph in wide_chars if glyph not in condition_set
    )
    print(f"wide UI glyphs: {len(wide_chars)} / condition glyphs {len(CONDITION_FIXED_GLYPHS)} / tile slots {fixed_slots}")
    print(f"wide UI patches: {ui_patches}")
    print(f"fixed dialogue tiles patched: {len(fixed_dialogue_mapped)}")
    print(f"dialogue copy limit patches: {dialogue_copy_limit_patches}")
    print(f"dialogue tile mapper patches: {dialogue_tile_mapper_patches}")
    print(f"dialogue name patches: {dialogue_name_patches}")
    print(f"condition label patches: {condition_label_patches}")
    print(f"condition number patches: {condition_number_patches}")
    print(f"condition text patches: {condition_text_patches}")
    print(f"condition heading patches: {condition_heading_patches}")
    print(f"route menu patches: {route_menu_patches}")
    print(f"name entry display patches: {name_entry_patches}")
    print(f"dialogue English residue records: {len(english_residue)}")
    print(f"font relocated: 0x{base.RELOCATED_BITMAP_TABLE:x}-0x{font_cursor:x}")
    print(f"script: 0x{base.SCRIPT_BASE:x}-0x{script_cursor:x}")
    print(f"opening: 0x{script_cursor:x}-0x{scenario_start:x}")
    print(f"scenarios: 0x{scenario_start:x}-0x{data_cursor:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
