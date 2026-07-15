#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


GENESIS_GAME_GENIE_ALPHABET = "ABCDEFGHJKLMNPRSTVWXYZ0123456789"


@dataclass(frozen=True)
class GameGeniePatch:
    code: str
    address: int
    value: int


def decode_genesis_game_genie(code: str) -> GameGeniePatch:
    normalized = code.strip().upper()
    if len(normalized) != 9 or normalized[4] != "-":
        raise ValueError("Genesis Game Genie code must use the form XXXX-XXXX")

    encoded = normalized[:4] + normalized[5:]
    try:
        values = [GENESIS_GAME_GENIE_ALPHABET.index(char) for char in encoded]
    except ValueError as error:
        raise ValueError(f"invalid Genesis Game Genie code {code!r}") from error

    address = 0
    value = 0
    value |= values[0] << 3
    value |= values[1] >> 2
    address |= (values[1] & 0x03) << 14
    address |= values[2] << 9
    address |= ((values[3] & 0x0F) << 20) | ((values[3] >> 4) << 8)
    address |= (values[4] >> 1) << 16
    value |= (values[4] & 0x01) << 12
    value |= ((values[5] & 0x01) << 15) | ((values[5] >> 1) << 8)
    address |= (values[6] & 0x07) << 5
    value |= (values[6] >> 3) << 13
    address |= values[7]
    return GameGeniePatch(normalized, address, value)
