#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

from tools.class_change_data import read_class_change_chain
from tools.class_hire_data import (
    CLASS_COUNT,
    CLASS_RECORD_SIZE,
    CLASS_RECORD_TABLE,
    class_record_offset,
)


CLASS_ABILITY_OFFSETS = (0x16, 0x17, 0x18, 0x19)
EMPTY_ABILITY = 0xFF
MAGIC_ABILITY_COUNT = 22
SUMMON_ABILITY_ID = 22
ABILITY_COUNT = SUMMON_ABILITY_ID + 1
ABILITY_REQUIREMENT_TABLE = 0x0829CC
ABILITY_MASK_TABLE = 0x0829FA
MAGIC_COMMAND_MASK = 1 << 0
SUMMON_COMMAND_MASK = 1 << 23


@dataclass(frozen=True)
class AbilityDefinition:
    ability_id: int
    required_level: int
    runtime_mask: int

    @property
    def kind(self) -> str:
        return "summon" if self.ability_id == SUMMON_ABILITY_ID else "magic"


@dataclass(frozen=True)
class ClassAbilityUnlocks:
    class_id: int
    ability_ids: tuple[int, ...]
    offset: int


def read_ability_definitions(
    source: bytes | bytearray,
) -> tuple[AbilityDefinition, ...]:
    definitions = []
    for ability_id in range(ABILITY_COUNT):
        requirement_offset = ABILITY_REQUIREMENT_TABLE + ability_id * 2
        mask_offset = ABILITY_MASK_TABLE + ability_id * 4
        required_level = int.from_bytes(
            source[requirement_offset : requirement_offset + 2],
            "big",
        )
        runtime_mask = int.from_bytes(
            source[mask_offset : mask_offset + 4],
            "big",
        )
        expected_mask = 1 << (ability_id + 1)
        if runtime_mask != expected_mask:
            raise ValueError(
                f"ability {ability_id} mask changed: "
                f"0x{runtime_mask:08X} != 0x{expected_mask:08X}"
            )
        if not 1 <= required_level <= 10:
            raise ValueError(
                f"ability {ability_id} has invalid requirement "
                f"{required_level}"
            )
        definitions.append(
            AbilityDefinition(
                ability_id=ability_id,
                required_level=required_level,
                runtime_mask=runtime_mask,
            )
        )
    return tuple(definitions)


def read_class_ability_unlocks(
    source: bytes | bytearray,
    class_id: int,
) -> ClassAbilityUnlocks:
    base = class_record_offset(class_id)
    values = tuple(
        source[base + relative]
        for relative in CLASS_ABILITY_OFFSETS
    )
    invalid = [
        value
        for value in values
        if value != EMPTY_ABILITY and not 0 <= value < ABILITY_COUNT
    ]
    if invalid:
        raise ValueError(
            f"class 0x{class_id:02X} has invalid ability IDs "
            + ", ".join(f"0x{value:02X}" for value in invalid)
        )
    ability_ids = tuple(value for value in values if value != EMPTY_ABILITY)
    return ClassAbilityUnlocks(
        class_id=class_id,
        ability_ids=ability_ids,
        offset=base + CLASS_ABILITY_OFFSETS[0],
    )


def learned_runtime_mask(
    source: bytes | bytearray,
    class_id: int,
    level: int,
) -> int:
    if not 1 <= level <= 10:
        raise ValueError("level must be 1..10")
    definitions = read_ability_definitions(source)
    result = 0
    for ability_id in read_class_ability_unlocks(source, class_id).ability_ids:
        definition = definitions[ability_id]
        if level >= definition.required_level:
            result |= definition.runtime_mask | MAGIC_COMMAND_MASK
    return result


def ability_ids_from_runtime_mask(runtime_mask: int) -> tuple[int, ...]:
    if not 0 <= runtime_mask <= 0xFFFFFFFF:
        raise ValueError("runtime mask must fit one long word")
    return tuple(
        ability_id
        for ability_id in range(ABILITY_COUNT)
        if runtime_mask & (1 << (ability_id + 1))
    )


def natural_class_paths(
    source: bytes | bytearray,
    commander_id: int,
) -> tuple[tuple[int, ...], ...]:
    transitions = read_class_change_chain(source, commander_id)
    candidates_by_class = {
        transition.current_class: transition.candidates
        for transition in transitions
    }
    paths: list[tuple[int, ...]] = []

    def visit(path: tuple[int, ...]) -> None:
        candidates = candidates_by_class.get(path[-1])
        if candidates is None:
            paths.append(path)
            return
        for candidate in candidates:
            if candidate in path:
                raise ValueError(
                    f"commander {commander_id} class-change cycle at "
                    f"0x{candidate:02X}"
                )
            visit((*path, candidate))

    visit((transitions[0].current_class,))
    if len(paths) != 27:
        raise ValueError(
            f"commander {commander_id} has {len(paths)} terminal paths, "
            "expected 27"
        )
    return tuple(paths)


def ability_ids_for_classes(
    source: bytes | bytearray,
    class_ids: tuple[int, ...] | list[int] | set[int],
) -> tuple[int, ...]:
    result: set[int] = set()
    for class_id in class_ids:
        result.update(
            read_class_ability_unlocks(source, class_id).ability_ids
        )
    return tuple(sorted(result))


def all_class_ability_unlocks(
    source: bytes | bytearray,
) -> tuple[ClassAbilityUnlocks, ...]:
    expected_end = CLASS_RECORD_TABLE + CLASS_COUNT * CLASS_RECORD_SIZE
    if len(source) < expected_end:
        raise ValueError("ROM is too short for the class record table")
    return tuple(
        read_class_ability_unlocks(source, class_id)
        for class_id in range(CLASS_COUNT)
    )
