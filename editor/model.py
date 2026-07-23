from __future__ import annotations

import json
from pathlib import Path

from tools.class_change_data import (
    COMMANDER_COUNT,
    class_change_chain_pointer,
    read_class_change_chain,
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
    for commander_id in range(1, COMMANDER_COUNT + 1):
        transitions = []
        for index, transition in enumerate(
            read_class_change_chain(data, commander_id)
        ):
            preview_ids.add(transition.current_class)
            preview_ids.update(transition.candidates)
            transitions.append({
                "index": index,
                "current_class": transition.current_class,
                "candidates": list(transition.candidates),
            })
        commanders.append({
            "commander_id": commander_id,
            "name": KOREAN_NAME_BY_ID[commander_id],
            "pointer": class_change_chain_pointer(data, commander_id),
            "transitions": transitions,
        })
    return {
        "classes": classes,
        "preview_class_ids": sorted(preview_ids),
        "commanders": commanders,
    }
