#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

from tools.class_ability_data import (
    ABILITY_COUNT,
    ABILITY_REQUIREMENT_TABLE,
    CLASS_ABILITY_OFFSETS,
    EMPTY_ABILITY,
    read_ability_definitions,
    read_class_ability_unlocks,
)
from tools.class_change_data import CLASS_COUNT, COMMANDER_COUNT
from tools.class_hire_data import (
    CLASS_RECORD_SIZE,
    CLASS_RECORD_TABLE,
    class_record_offset,
)


INITIAL_COMMANDER_ROSTER_TABLE = 0x05E64A
INITIAL_COMMANDER_RECORD_SIZE = 0x0E

CLASS_MP_GROWTH_OFFSET = 0x0A
CLASS_AT_GROWTH_OFFSET = 0x0B
CLASS_DF_GROWTH_OFFSET = 0x0C
CLASS_MOVEMENT_OFFSET = 0x0D
CLASS_SOLDIER_AT_CORRECTION_OFFSET = 0x0F
CLASS_SOLDIER_DF_CORRECTION_OFFSET = 0x10
GROWTH_TABLE = 0x082922
GROWTH_LEVEL_COUNT = 10
STOCK_GROWTH_PATTERN_COUNT = (
    ABILITY_REQUIREMENT_TABLE - GROWTH_TABLE
) // GROWTH_LEVEL_COUNT

# The stock level-up helper receives the class-record displacement in D1,
# the reached level in D2, and the stock growth-pattern ID in D3.  AT, DF,
# and MP call the same helper, so the expanded routine distinguishes the
# stat by the BSR return address and looks up an independent ten-byte row.
GROWTH_HELPER_HOOK = 0x014AE4
GROWTH_HELPER_ORIGINAL = bytes.fromhex("45 F9 00 08 29 22")
GROWTH_AT_RETURN = 0x01487C
GROWTH_DF_RETURN = 0x0148A6
GROWTH_MP_RETURN = 0x0148D0
GROWTH_OVERRIDE_ROUTINE = 0x3D0000
GROWTH_OVERRIDE_ROUTINE_LIMIT = 0x3D0100
GROWTH_OVERRIDE_AT_TABLE = 0x3D1000
GROWTH_OVERRIDE_DF_TABLE = 0x3D2200
GROWTH_OVERRIDE_MP_TABLE = 0x3D3400
GROWTH_OVERRIDE_TABLE_SIZE = CLASS_COUNT * CLASS_RECORD_SIZE
GROWTH_OVERRIDE_END = GROWTH_OVERRIDE_MP_TABLE + GROWTH_OVERRIDE_TABLE_SIZE
GROWTH_OVERRIDE_EMPTY = 0xFF
EXPANDED_ROM_SIZE = 0x400000

PLAYABLE_CLASS_MIN = 0x01
PLAYABLE_CLASS_MAX = 0x2C


@dataclass(frozen=True)
class CommanderStartingRecord:
    commander_id: int
    class_id: int
    mp: int
    level: int
    experience: int
    at: int
    df: int
    offset: int


@dataclass(frozen=True)
class ClassProgression:
    class_id: int
    movement: int
    soldier_at_correction: int
    soldier_df_correction: int
    growth_codes: tuple[int, int, int]
    mp_growth: tuple[int, ...]
    at_growth: tuple[int, ...]
    df_growth: tuple[int, ...]
    ability_ids: tuple[int, ...]
    offset: int


class _M68KCode:
    def __init__(self) -> None:
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def emit(self, payload: str | bytes) -> None:
        self.code.extend(
            bytes.fromhex(payload) if isinstance(payload, str) else payload
        )

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate M68K label {name}")
        self.labels[name] = len(self.code)

    def branch_word(self, opcode: int, label: str) -> None:
        self.code.extend(opcode.to_bytes(2, "big"))
        self.fixups.append((len(self.code), label))
        self.code.extend(b"\x00\x00")

    def finish(self) -> bytes:
        for displacement_offset, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"undefined M68K label {label}")
            displacement = self.labels[label] - displacement_offset
            if not -0x8000 <= displacement <= 0x7FFF:
                raise ValueError(f"M68K branch to {label} is out of range")
            self.code[displacement_offset : displacement_offset + 2] = (
                displacement & 0xFFFF
            ).to_bytes(2, "big")
        return bytes(self.code)


def commander_starting_record_offset(commander_id: int) -> int:
    if not 1 <= commander_id <= COMMANDER_COUNT:
        raise ValueError(f"commander ID must be 1..{COMMANDER_COUNT}")
    return (
        INITIAL_COMMANDER_ROSTER_TABLE
        + (commander_id - 1) * INITIAL_COMMANDER_RECORD_SIZE
    )


def read_commander_starting_record(
    source: bytes | bytearray,
    commander_id: int,
) -> CommanderStartingRecord:
    offset = commander_starting_record_offset(commander_id)
    if len(source) < offset + INITIAL_COMMANDER_RECORD_SIZE:
        raise ValueError("ROM is too short for the initial commander roster")
    return CommanderStartingRecord(
        commander_id=commander_id,
        class_id=source[offset],
        mp=source[offset + 1],
        level=source[offset + 2],
        experience=source[offset + 3],
        at=source[offset + 4],
        df=source[offset + 5],
        offset=offset,
    )


def read_commander_starting_records(
    source: bytes | bytearray,
) -> tuple[CommanderStartingRecord, ...]:
    return tuple(
        read_commander_starting_record(source, commander_id)
        for commander_id in range(1, COMMANDER_COUNT + 1)
    )


def patch_commander_starting_classes(
    data: bytearray,
    rows: list[dict[str, object]],
) -> None:
    if len(rows) != COMMANDER_COUNT:
        raise ValueError(
            f"expected {COMMANDER_COUNT} starting classes, got {len(rows)}"
        )
    for expected_id, row in enumerate(rows, 1):
        commander_id = int(row["commander_id"])
        if commander_id != expected_id:
            raise ValueError("commander starting rows must stay ordered")
        class_id = int(row["starting_class_id"])
        if not 0 <= class_id < CLASS_COUNT:
            raise ValueError(
                f"commander {commander_id} starting class is invalid"
            )
        data[commander_starting_record_offset(commander_id)] = class_id


def _stock_growth_values(
    source: bytes | bytearray,
    growth_code: int,
) -> tuple[int, ...]:
    if not 0 <= growth_code < STOCK_GROWTH_PATTERN_COUNT:
        raise ValueError(
            f"growth pattern 0x{growth_code:02X} is outside the stock table"
        )
    offset = GROWTH_TABLE + growth_code * GROWTH_LEVEL_COUNT
    return tuple(source[offset : offset + GROWTH_LEVEL_COUNT])


def _override_growth_values(
    source: bytes | bytearray,
    table: int,
    class_id: int,
) -> tuple[int, ...] | None:
    installed_hook = (
        bytes.fromhex("4E F9")
        + GROWTH_OVERRIDE_ROUTINE.to_bytes(4, "big")
    )
    if (
        len(source) < GROWTH_OVERRIDE_END
        or source[GROWTH_HELPER_HOOK : GROWTH_HELPER_HOOK + 6]
        != installed_hook
    ):
        return None
    offset = table + class_id * CLASS_RECORD_SIZE
    if source[offset] == GROWTH_OVERRIDE_EMPTY:
        return None
    return tuple(source[offset : offset + GROWTH_LEVEL_COUNT])


def read_class_progression(
    source: bytes | bytearray,
    class_id: int,
) -> ClassProgression:
    base = class_record_offset(class_id)
    growth_codes = tuple(
        source[base + offset]
        for offset in (
            CLASS_MP_GROWTH_OFFSET,
            CLASS_AT_GROWTH_OFFSET,
            CLASS_DF_GROWTH_OFFSET,
        )
    )
    if not all(code < STOCK_GROWTH_PATTERN_COUNT for code in growth_codes):
        raise ValueError(
            f"class 0x{class_id:02X} does not use playable growth patterns"
        )
    overrides = (
        _override_growth_values(source, GROWTH_OVERRIDE_MP_TABLE, class_id),
        _override_growth_values(source, GROWTH_OVERRIDE_AT_TABLE, class_id),
        _override_growth_values(source, GROWTH_OVERRIDE_DF_TABLE, class_id),
    )
    growth_values = tuple(
        override if override is not None else _stock_growth_values(source, code)
        for override, code in zip(overrides, growth_codes)
    )
    return ClassProgression(
        class_id=class_id,
        movement=source[base + CLASS_MOVEMENT_OFFSET],
        soldier_at_correction=source[
            base + CLASS_SOLDIER_AT_CORRECTION_OFFSET
        ],
        soldier_df_correction=source[
            base + CLASS_SOLDIER_DF_CORRECTION_OFFSET
        ],
        growth_codes=(growth_codes[0], growth_codes[1], growth_codes[2]),
        mp_growth=growth_values[0],
        at_growth=growth_values[1],
        df_growth=growth_values[2],
        ability_ids=read_class_ability_unlocks(source, class_id).ability_ids,
        offset=base,
    )


def read_playable_class_progressions(
    source: bytes | bytearray,
) -> tuple[ClassProgression, ...]:
    return tuple(
        read_class_progression(source, class_id)
        for class_id in range(PLAYABLE_CLASS_MIN, PLAYABLE_CLASS_MAX + 1)
    )


def _normalize_growth(values: object, label: str) -> tuple[int, ...]:
    if not isinstance(values, list) or len(values) != GROWTH_LEVEL_COUNT:
        raise ValueError(f"{label} growth needs ten level values")
    normalized = tuple(int(value) for value in values)
    if any(not 0 <= value <= 99 for value in normalized):
        raise ValueError(f"{label} growth values must be 0..99")
    return normalized


def _build_growth_override_routine() -> bytes:
    code = _M68KCode()
    code.emit("28 17")  # move.l (a7),d4 -- BSR return address
    for label, return_address in (
        ("at", GROWTH_AT_RETURN),
        ("df", GROWTH_DF_RETURN),
        ("mp", GROWTH_MP_RETURN),
    ):
        code.emit(bytes.fromhex("0C 84") + return_address.to_bytes(4, "big"))
        code.branch_word(0x6700, label)  # beq.w
    code.branch_word(0x6000, "stock")
    for label, table in (
        ("at", GROWTH_OVERRIDE_AT_TABLE),
        ("df", GROWTH_OVERRIDE_DF_TABLE),
        ("mp", GROWTH_OVERRIDE_MP_TABLE),
    ):
        code.label(label)
        code.emit(bytes.fromhex("45 F9") + table.to_bytes(4, "big"))
        code.branch_word(0x6000, "override")
    code.label("override")
    code.emit("D4 C1")  # adda.w d1,a2 -- class ID * record size
    code.emit("18 12")  # move.b (a2),d4 -- 0xFF means no override
    code.emit("0C 04 00 FF")
    code.branch_word(0x6700, "stock")
    code.emit("D4 C2 53 8A")  # adda.w d2,a2; subq.l #1,a2
    code.emit("78 00 18 12 4E 75")  # zero-extend byte; rts
    code.label("stock")
    code.emit("45 F9 00 08 29 22")
    code.emit("D6 43 38 03 D6 43 D6 43 D6 44 D6 42 53 43")
    code.emit("78 00 18 32 30 00 4E 75")
    return code.finish()


def _install_growth_override_tables(
    data: bytearray,
    override_growth: dict[int, tuple[tuple[int, ...], ...]],
) -> None:
    if len(data) < EXPANDED_ROM_SIZE:
        raise ValueError(
            "class growth editing requires the expanded Korean ROM"
        )
    routine = _build_growth_override_routine()
    if GROWTH_OVERRIDE_ROUTINE + len(routine) > GROWTH_OVERRIDE_ROUTINE_LIMIT:
        raise ValueError("class growth override routine exceeds its slot")
    hook = bytes(data[GROWTH_HELPER_HOOK : GROWTH_HELPER_HOOK + 6])
    installed_hook = (
        bytes.fromhex("4E F9")
        + GROWTH_OVERRIDE_ROUTINE.to_bytes(4, "big")
    )
    if hook not in (GROWTH_HELPER_ORIGINAL, installed_hook):
        raise ValueError("stock class growth helper hook changed")

    occupied = data[GROWTH_OVERRIDE_ROUTINE:GROWTH_OVERRIDE_END]
    if hook == GROWTH_HELPER_ORIGINAL and any(
        value != 0xFF for value in occupied
    ):
        raise ValueError("class growth override ROM region is not blank")

    data[GROWTH_OVERRIDE_ROUTINE:GROWTH_OVERRIDE_ROUTINE_LIMIT] = (
        routine
        + b"\xFF" * (
            GROWTH_OVERRIDE_ROUTINE_LIMIT
            - GROWTH_OVERRIDE_ROUTINE
            - len(routine)
        )
    )
    for table in (
        GROWTH_OVERRIDE_AT_TABLE,
        GROWTH_OVERRIDE_DF_TABLE,
        GROWTH_OVERRIDE_MP_TABLE,
    ):
        data[table : table + GROWTH_OVERRIDE_TABLE_SIZE] = (
            b"\xFF" * GROWTH_OVERRIDE_TABLE_SIZE
        )
    for class_id, (mp_growth, at_growth, df_growth) in override_growth.items():
        relative = class_id * CLASS_RECORD_SIZE
        for table, values in (
            (GROWTH_OVERRIDE_MP_TABLE, mp_growth),
            (GROWTH_OVERRIDE_AT_TABLE, at_growth),
            (GROWTH_OVERRIDE_DF_TABLE, df_growth),
        ):
            offset = table + relative
            data[offset : offset + GROWTH_LEVEL_COUNT] = bytes(values)
    data[GROWTH_HELPER_HOOK : GROWTH_HELPER_HOOK + 6] = installed_hook


def patch_class_progressions(
    data: bytearray,
    rows: list[dict[str, object]],
) -> None:
    expected_ids = list(range(PLAYABLE_CLASS_MIN, PLAYABLE_CLASS_MAX + 1))
    actual_ids = [int(row["class_id"]) for row in rows]
    if actual_ids != expected_ids:
        raise ValueError(
            "playable class progression rows must stay complete and ordered"
        )

    override_growth: dict[int, tuple[tuple[int, ...], ...]] = {}
    growth_changed = False
    for row in rows:
        class_id = int(row["class_id"])
        current = read_class_progression(data, class_id)
        base = class_record_offset(class_id)
        for key, relative in (
            ("movement", CLASS_MOVEMENT_OFFSET),
            ("soldier_at_correction", CLASS_SOLDIER_AT_CORRECTION_OFFSET),
            ("soldier_df_correction", CLASS_SOLDIER_DF_CORRECTION_OFFSET),
        ):
            value = int(row[key])
            if not 0 <= value <= 255:
                raise ValueError(
                    f"class 0x{class_id:02X} {key} must be 0..255"
                )
            data[base + relative] = value

        growth = row["growth"]
        if not isinstance(growth, dict):
            raise ValueError("class growth must be an object")
        values = (
            _normalize_growth(growth["mp"], "MP"),
            _normalize_growth(growth["at"], "AT"),
            _normalize_growth(growth["df"], "DF"),
        )
        has_existing_override = any(
            _override_growth_values(data, table, class_id) is not None
            for table in (
                GROWTH_OVERRIDE_MP_TABLE,
                GROWTH_OVERRIDE_AT_TABLE,
                GROWTH_OVERRIDE_DF_TABLE,
            )
        )
        if has_existing_override:
            override_growth[class_id] = values
        if values != (current.mp_growth, current.at_growth, current.df_growth):
            growth_changed = True
            override_growth[class_id] = values

        abilities = [int(value) for value in row["ability_ids"]]
        if len(abilities) != len(CLASS_ABILITY_OFFSETS):
            raise ValueError("each class needs exactly four ability slots")
        nonempty = [value for value in abilities if value != EMPTY_ABILITY]
        if len(set(nonempty)) != len(nonempty):
            raise ValueError(f"class 0x{class_id:02X} repeats an ability")
        if any(
            value != EMPTY_ABILITY and not 0 <= value < ABILITY_COUNT
            for value in abilities
        ):
            raise ValueError(f"class 0x{class_id:02X} has an invalid ability")
        for relative, value in zip(CLASS_ABILITY_OFFSETS, abilities):
            data[base + relative] = value

    if growth_changed:
        _install_growth_override_tables(data, override_growth)


def patch_ability_requirements(
    data: bytearray,
    rows: list[dict[str, object]],
) -> None:
    if len(rows) != ABILITY_COUNT:
        raise ValueError(f"expected {ABILITY_COUNT} ability definitions")
    definitions = read_ability_definitions(data)
    for expected_id, row in enumerate(rows):
        ability_id = int(row["ability_id"])
        if ability_id != expected_id:
            raise ValueError("ability definitions must stay ordered")
        required_level = int(row["required_level"])
        if not 1 <= required_level <= 10:
            raise ValueError("ability required level must be 1..10")
        if int(row.get("runtime_mask", definitions[ability_id].runtime_mask)) != (
            definitions[ability_id].runtime_mask
        ):
            raise ValueError("ability runtime masks are read-only")
        offset = ABILITY_REQUIREMENT_TABLE + ability_id * 2
        data[offset : offset + 2] = required_level.to_bytes(2, "big")
