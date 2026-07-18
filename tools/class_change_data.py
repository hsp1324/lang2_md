#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


CLASS_CHANGE_POINTER_TABLE = 0x08253A
COMMANDER_COUNT = 10
REGULAR_TRANSITION_COUNT = 9
CLASS_COUNT = 157


@dataclass(frozen=True)
class ClassTransition:
    current_class: int
    candidates: tuple[int, ...]


def be16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def class_change_chain_pointer(
    source: bytes | bytearray, commander_id: int
) -> int:
    if not 1 <= commander_id <= COMMANDER_COUNT:
        raise ValueError(f"commander ID must be 1..{COMMANDER_COUNT}")
    offset = CLASS_CHANGE_POINTER_TABLE + (commander_id - 1) * 4
    pointer = be32(source, offset)
    if not 0 <= pointer <= len(source) - 0x4E:
        raise ValueError(
            f"commander {commander_id} class-change pointer is out of range: "
            f"0x{pointer:06X}"
        )
    return pointer


def read_class_change_chain(
    source: bytes | bytearray, commander_id: int
) -> tuple[ClassTransition, ...]:
    pointer = class_change_chain_pointer(source, commander_id)
    transitions: list[ClassTransition] = []
    for index in range(REGULAR_TRANSITION_COUNT):
        offset = pointer + index * 8
        values = tuple(be16(source, offset + word * 2) for word in range(4))
        if any(value >= CLASS_COUNT for value in values):
            raise ValueError(
                f"commander {commander_id} regular transition {index} "
                "contains an invalid class ID"
            )
        transitions.append(ClassTransition(values[0], values[1:]))

    terminal_offset = pointer + REGULAR_TRANSITION_COUNT * 8
    terminal = ClassTransition(
        be16(source, terminal_offset),
        (be16(source, terminal_offset + 2),),
    )
    if terminal.current_class >= CLASS_COUNT or terminal.candidates[0] >= CLASS_COUNT:
        raise ValueError(
            f"commander {commander_id} terminal transition contains an invalid class ID"
        )
    if be16(source, terminal_offset + 4) != 0xFFFF:
        raise ValueError(
            f"commander {commander_id} class-change chain has no terminal sentinel"
        )
    transitions.append(terminal)

    current_classes = [transition.current_class for transition in transitions]
    if len(set(current_classes)) != len(current_classes):
        raise ValueError(
            f"commander {commander_id} class-change chain repeats a current class"
        )
    return tuple(transitions)


def transition_for_class(
    source: bytes | bytearray, commander_id: int, current_class: int
) -> ClassTransition:
    for transition in read_class_change_chain(source, commander_id):
        if transition.current_class == current_class:
            return transition
    raise ValueError(
        f"commander {commander_id} has no class-change transition from "
        f"class 0x{current_class:02X}"
    )
