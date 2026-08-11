#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


CLASS_CHANGE_POINTER_TABLE = 0x08253A
COMMANDER_COUNT = 10
REGULAR_TRANSITION_COUNT = 9
MAX_TRANSITION_COUNT = 32
CLASS_COUNT = 157


@dataclass(frozen=True)
class ClassTransition:
    current_class: int
    candidates: tuple[int, ...]


# The Japanese chains contain ten records and only one terminal fifth-tier
# route per commander. Relocated patched chains may contain additional
# records, so the parser follows the actual sentinel. The stock commander
# sprite tables and original class trees expose these extra fifth-tier
# destinations too; keep them as read-only editor metadata.
HIDDEN_CLASS_ROUTES: dict[int, tuple[ClassTransition, ...]] = {
    1: (
        ClassTransition(0x1A, (0x22,)),  # Sword Master -> Hero
        ClassTransition(0x1B, (0x29,)),  # Knight Master -> Royal Knight
    ),
    2: (
        ClassTransition(0x19, (0x28,)),  # Paladin -> Summoner
        ClassTransition(0x16, (0x25,)),  # High Priest -> Agent
        ClassTransition(0x15, (0x26,)),  # Wizard -> Zarvera
    ),
    3: (
        ClassTransition(0x19, (0x28,)),
        ClassTransition(0x16, (0x25,)),
        ClassTransition(0x15, (0x26,)),
    ),
    4: (
        ClassTransition(0x21, (0x23,)),  # Ranger -> High Master
        ClassTransition(0x1E, (0x24,)),  # Dragon Lord -> Dragon Master
        ClassTransition(0x1D, (0x27,)),  # Silver Knight -> Princess
    ),
    5: (
        ClassTransition(0x15, (0x28,)),  # Wizard -> Summoner
        ClassTransition(0x14, (0x26,)),  # Arch Mage -> Zarvera
    ),
    6: (
        ClassTransition(0x1B, (0x29,)),  # Knight Master -> Royal Knight
    ),
    7: (
        ClassTransition(0x1E, (0x24,)),  # Dragon Lord -> Dragon Master
    ),
    8: (
        ClassTransition(0x1A, (0x23,)),  # Sword Master -> High Master
    ),
    9: (
        ClassTransition(0x1F, (0x2A,)),  # Serpent Lord -> Serpent Master
        ClassTransition(0x14, (0x26,)),  # Arch Mage -> Zarvera
    ),
    10: (
        ClassTransition(0x14, (0x26,)),  # Arch Mage -> Zarvera
        ClassTransition(0x18, (0x28,)),  # Sage -> Summoner
    ),
}


def hidden_class_routes(commander_id: int) -> tuple[ClassTransition, ...]:
    if not 1 <= commander_id <= COMMANDER_COUNT:
        raise ValueError(f"commander ID must be 1..{COMMANDER_COUNT}")
    return HIDDEN_CLASS_ROUTES[commander_id]


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
    if not 0 <= pointer <= len(source) - 6:
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
    for index in range(MAX_TRANSITION_COUNT):
        offset = pointer + index * 8
        if offset + 6 > len(source):
            raise ValueError(
                f"commander {commander_id} class-change chain ends outside ROM"
            )
        current_class = be16(source, offset)
        first_candidate = be16(source, offset + 2)
        sentinel_or_second = be16(source, offset + 4)
        if sentinel_or_second == 0xFFFF:
            if current_class >= CLASS_COUNT or first_candidate >= CLASS_COUNT:
                raise ValueError(
                    f"commander {commander_id} terminal transition {index} "
                    "contains an invalid class ID"
                )
            transitions.append(
                ClassTransition(current_class, (first_candidate,))
            )
            break

        third_candidate = be16(source, offset + 6)
        values = (
            current_class,
            first_candidate,
            sentinel_or_second,
            third_candidate,
        )
        if any(value >= CLASS_COUNT for value in values):
            raise ValueError(
                f"commander {commander_id} transition {index} "
                "contains an invalid class ID"
            )
        transitions.append(ClassTransition(current_class, values[1:]))
    else:
        raise ValueError(
            f"commander {commander_id} class-change chain has no terminal "
            f"sentinel within {MAX_TRANSITION_COUNT} records"
        )

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


def patch_class_change_chain(
    data: bytearray,
    commander_id: int,
    transitions: list[dict[str, object]] | tuple[ClassTransition, ...],
) -> None:
    pointer = class_change_chain_pointer(data, commander_id)
    current_transition_count = len(read_class_change_chain(data, commander_id))
    if len(transitions) != current_transition_count:
        raise ValueError(
            f"commander {commander_id} needs "
            f"{current_transition_count} transitions"
        )

    normalized: list[ClassTransition] = []
    for index, source_transition in enumerate(transitions):
        if isinstance(source_transition, ClassTransition):
            transition = source_transition
        else:
            transition = ClassTransition(
                int(source_transition["current_class"]),
                tuple(int(value) for value in source_transition["candidates"]),
            )
        expected_candidates = 3 if index < len(transitions) - 1 else 1
        if len(transition.candidates) != expected_candidates:
            raise ValueError(
                f"commander {commander_id} transition {index} needs "
                f"{expected_candidates} candidate classes"
            )
        values = (transition.current_class, *transition.candidates)
        if any(not 0 <= value < CLASS_COUNT for value in values):
            raise ValueError(
                f"commander {commander_id} transition {index} contains "
                "an invalid class ID"
            )
        normalized.append(transition)

    current_classes = [transition.current_class for transition in normalized]
    if len(set(current_classes)) != len(current_classes):
        raise ValueError(
            f"commander {commander_id} class-change chain repeats a current class"
        )

    for index, transition in enumerate(normalized[:-1]):
        offset = pointer + index * 8
        values = (transition.current_class, *transition.candidates)
        data[offset : offset + 8] = b"".join(
            value.to_bytes(2, "big") for value in values
        )

    terminal = normalized[-1]
    terminal_offset = pointer + (len(normalized) - 1) * 8
    data[terminal_offset : terminal_offset + 6] = (
        terminal.current_class.to_bytes(2, "big")
        + terminal.candidates[0].to_bytes(2, "big")
        + b"\xFF\xFF"
    )


def patch_class_change_chains(
    data: bytearray,
    commanders: list[dict[str, object]],
) -> None:
    if len(commanders) != COMMANDER_COUNT:
        raise ValueError(
            f"expected {COMMANDER_COUNT} commander chains, got {len(commanders)}"
        )
    for expected_id, commander in enumerate(commanders, 1):
        commander_id = int(commander["commander_id"])
        if commander_id != expected_id:
            raise ValueError("commander IDs must be ordered and unchanged")
        patch_class_change_chain(data, commander_id, commander["transitions"])
