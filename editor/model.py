from __future__ import annotations

import json
from pathlib import Path

from tools.class_ability_data import EMPTY_ABILITY, read_ability_definitions
from tools.class_change_data import (
    COMMANDER_COUNT,
    class_change_chain_pointer,
    hidden_class_routes,
    read_class_change_chain,
)
from tools.class_hire_data import read_class_hire_unlocks
from tools.class_progression_data import (
    PLAYABLE_CLASS_MAX,
    PLAYABLE_CLASS_MIN,
    read_commander_starting_records,
    read_playable_class_progressions,
)
from tools.item_data import (
    ITEM_EFFECT_TYPES,
    effect_record_offset,
    price_offset,
    read_items,
    special_behavior,
)
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


ROOT = Path(__file__).resolve().parents[1]
ITEM_METADATA = ROOT / "localization/item_shop_inventory.json"
CLASS_ABILITY_METADATA = ROOT / "localization/class_abilities.json"


def _semantic_transition_tiers(
    transitions: tuple[object, ...],
    starting_class_id: int,
) -> dict[int, int]:
    """Derive tiers from the real starting class, not physical row order.

    Keith and Lester use custom tier-one classes whose transition rows are
    deliberately stored outside the first physical record.  The old editor
    therefore displayed their promoted class as tier one.  Following the
    graph from the initial roster is both accurate and stable after edits.
    """

    by_current = {
        transition.current_class: transition
        for transition in transitions
    }
    result = {starting_class_id: 1}
    pending = [starting_class_id]
    while pending:
        current = pending.pop(0)
        transition = by_current.get(current)
        if transition is None:
            continue
        next_tier = result[current] + 1
        for candidate in transition.candidates:
            if candidate not in by_current:
                continue
            old_tier = result.get(candidate)
            if old_tier is None or next_tier < old_tier:
                result[candidate] = next_tier
                pending.append(candidate)
    return result


def item_editor_model(
    data: bytes,
    metadata_path: Path = ITEM_METADATA,
) -> dict[str, object]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_by_id = {int(row["id"]): row for row in metadata["items"]}
    items = []
    for record in read_items(data):
        row = metadata_by_id[record.item_id]
        items.append({
            "item_id": record.item_id,
            "category": row["category"],
            "name": row["target_korean"],
            "original_name": row["original_name"],
            "description": row["target_description"],
            "icon_url": f"/item-icons/{record.item_id:02d}.png",
            "price_units": record.price_units,
            "purchase_price": record.price_units * 10,
            "price_offset": price_offset(record.item_id),
            "effect_offset": effect_record_offset(record.item_id),
            "effects": [
                {
                    "effect_type": effect.effect_type,
                    "value": effect.value,
                }
                for effect in record.effects
            ],
            "special_behavior": list(special_behavior(record.item_id)),
        })
    return {
        "items": items,
        "effect_types": [
            {"id": effect_type, "name": label}
            for effect_type, label in ITEM_EFFECT_TYPES.items()
        ],
    }


def class_change_editor_model(
    data: bytes,
    reference_rom: bytes,
) -> dict[str, object]:
    classes = class_names(reference_rom)
    commanders = []
    preview_ids = set()
    starting_records = read_commander_starting_records(data)
    for commander_id in range(1, COMMANDER_COUNT + 1):
        pointer = class_change_chain_pointer(data, commander_id)
        chain = read_class_change_chain(data, commander_id)
        starting = starting_records[commander_id - 1]
        semantic_tiers = _semantic_transition_tiers(
            chain,
            starting.class_id,
        )
        transitions = []
        for index, transition in enumerate(chain):
            preview_ids.add(transition.current_class)
            preview_ids.update(transition.candidates)
            if index == 0:
                fallback_tier = 1
            elif index <= 3:
                fallback_tier = 2
            elif index <= 8:
                fallback_tier = 3
            else:
                fallback_tier = 4
            source_tier = semantic_tiers.get(
                transition.current_class,
                fallback_tier,
            )
            transitions.append({
                "index": index,
                "source_tier": source_tier,
                "current_class": transition.current_class,
                "candidates": list(transition.candidates),
                "offset": pointer + index * 8,
            })
        hidden_routes = []
        for route in hidden_class_routes(commander_id):
            preview_ids.add(route.current_class)
            preview_ids.update(route.candidates)
            hidden_routes.append({
                "current_class": route.current_class,
                "hidden_class": route.candidates[0],
            })
        commanders.append({
            "commander_id": commander_id,
            "name": KOREAN_NAME_BY_ID[commander_id],
            "pointer": pointer,
            "starting_class_id": starting.class_id,
            "starting_class_offset": starting.offset,
            "starting_level": starting.level,
            "starting_experience": starting.experience,
            "starting_stats": {
                "mp": starting.mp,
                "at": starting.at,
                "df": starting.df,
            },
            "transitions": transitions,
            "hidden_class_routes": hidden_routes,
        })
    return {
        "classes": classes,
        "preview_class_ids": sorted(preview_ids),
        "class_hires": [
            {
                "class_id": record.class_id,
                "hire_class_ids": list(record.hire_class_ids),
                "offset": record.offset,
            }
            for record in (
                read_class_hire_unlocks(data, class_id)
                for class_id in range(len(classes))
            )
        ],
        "hire_class_ids": list(range(0x62, 0x72)),
        "commanders": commanders,
    }


def class_progression_editor_model(
    data: bytes,
    reference_rom: bytes,
    metadata_path: Path = CLASS_ABILITY_METADATA,
) -> dict[str, object]:
    classes = class_names(reference_rom)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_by_id = {
        int(row["id"]): row
        for row in metadata["abilities"]
    }
    definitions = read_ability_definitions(data)
    abilities = []
    for definition in definitions:
        row = metadata_by_id[definition.ability_id]
        abilities.append({
            "ability_id": definition.ability_id,
            "name": row["name"],
            "kind": definition.kind,
            "required_level": definition.required_level,
            "runtime_mask": definition.runtime_mask,
        })

    progression_rows = []
    for progression in read_playable_class_progressions(data):
        info = classes[progression.class_id]
        padded_abilities = list(progression.ability_ids)
        padded_abilities.extend(
            [EMPTY_ABILITY] * (4 - len(padded_abilities))
        )
        progression_rows.append({
            "class_id": progression.class_id,
            "name": info["ko"],
            "original_name": info["jp"],
            "record_offset": progression.offset,
            "movement": progression.movement,
            "soldier_at_correction": progression.soldier_at_correction,
            "soldier_df_correction": progression.soldier_df_correction,
            "growth_codes": list(progression.growth_codes),
            "growth": {
                "mp": list(progression.mp_growth),
                "at": list(progression.at_growth),
                "df": list(progression.df_growth),
            },
            "ability_ids": padded_abilities,
        })
    return {
        "classes": progression_rows,
        "abilities": abilities,
        "empty_ability_id": EMPTY_ABILITY,
        "class_id_range": [PLAYABLE_CLASS_MIN, PLAYABLE_CLASS_MAX],
        "notes": {
            "growth": (
                "Growth is edited per playable commander class through an "
                "expanded-ROM override; shared stock base AT/DF bytes stay unchanged."
            ),
            "ability_level": (
                "Required levels belong to each ability globally and affect every "
                "class that contains that ability."
            ),
            "summon": (
                "Class data grants the Summon command; summon creature choices are "
                "controlled by stock equipment and summon tables."
            ),
        },
    }
