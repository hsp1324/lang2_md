from pathlib import Path

import pytest

from tools.empire_profile import (
    DEFAULT_EMPIRE_ROM,
    DEFAULT_JAPANESE_ROM,
    EMPIRE_SOURCE_SHA256,
    derive_empire_class_labels,
    derive_empire_name_labels,
    validate_empire_source,
)


@pytest.fixture(scope="module")
def empire() -> bytes:
    if not DEFAULT_EMPIRE_ROM.exists():
        pytest.skip("Empire source ROM is not available")
    return DEFAULT_EMPIRE_ROM.read_bytes()


@pytest.fixture(scope="module")
def japanese() -> bytes:
    return DEFAULT_JAPANESE_ROM.read_bytes()


def test_source_identity(empire: bytes) -> None:
    validate_empire_source(empire)
    assert len(EMPIRE_SOURCE_SHA256) == 64


def test_reordered_empire_class_labels(empire: bytes, japanese: bytes) -> None:
    labels = derive_empire_class_labels(empire, japanese)
    assert len(labels) == 157
    assert labels[0x00] == "파이터"
    assert labels[0x22] == "마샬"
    assert labels[0x27] == "퀸"
    assert labels[0x6D] == "워리어"
    assert labels[0x70] == "호크가드"
    assert labels[0x69] == "로얄호스"


def test_reordered_empire_actor_labels(empire: bytes, japanese: bytes) -> None:
    labels = derive_empire_name_labels(empire, japanese)
    assert len(labels) == 117
    assert labels[0x01] == "베른하르트"
    assert labels[0x04] == "이멜다"
    assert labels[0x05] == "에그베르트"
    assert labels[0x06] == "레온"
    assert labels[0x08] == "발가스"
    assert labels[0x09] == "로우가"
    assert labels[0x0A] == "소니아"
    assert labels[0x0E] == "엘윈"
    assert labels[0x16] == "사제"
    assert labels[0x1F] == "모건"
    assert labels[0x26] == "크라우스"
