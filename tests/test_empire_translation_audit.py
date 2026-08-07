import json
import re

from tools.audit_empire_translation import audit_script
from tools.build_korean_empire import controls
from tools.prepare_empire_review import layout_event_text


def test_scenario_description_0001_is_an_actor_control() -> None:
    script = json.load(open("localization/empire/reviewed/script_ko.json"))
    first = script["scenario_description_records"][0]
    assert "{0001}" in first["source_chinese"]
    assert "{0001}" in first["draft_korean"]
    assert "\f" not in first["draft_korean"]
    assert controls([0xFFF7, 0x0001]) == [(0xFFF7, 0x0001)]


def test_current_empire_review_has_complete_record_inventory() -> None:
    script = json.load(open("localization/empire/reviewed/script_ko.json"))
    report = audit_script(script)
    assert report["record_counts"] == report["expected_record_counts"]
    assert report["release_ready"]
    assert report["review_status_counts"] == {"human reviewed": 3277}


def test_event_layout_keeps_controls_atomic_and_fits_every_page() -> None:
    laid_out = layout_event_text(
        "폐하, {0001}님께서 아주 긴 제국편 대사를 말하고 계십니다. "
        "이 문장은 다음 대화창으로 안전하게 이어져야 합니다."
    )
    assert "{0001}" in laid_out
    for page in laid_out.split("\f"):
        lines = page.split("\n")
        assert len(lines) <= 3
        for line in lines:
            visible = re.sub(r"\{[0-9A-Fa-f]{4}\}", "이름이름이름", line)
            assert len(visible) <= 24
