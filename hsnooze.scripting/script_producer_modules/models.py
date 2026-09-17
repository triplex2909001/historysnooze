"""
HistorySnooze Script Producer - Data Models and Mappings
Module: models.py
Rule <= 150 lines compliant.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class StoryBeat:
    part_index: int
    beat_index: int
    beat_id: str
    title: str
    narrative_text: str
    scene_description: str
    character_ref: Optional[str] = None
    setting_ref: Optional[str] = None
    prop_ref: Optional[str] = None
    ingredient_ref: Optional[str] = None


PART_SETTINGS: Dict[int, str] = {
    1: "ref_setting_iga_ueno",
    2: "ref_setting_edo_nihonbashi",
    3: "ref_setting_fukagawa_interior",
    4: "ref_setting_fukagawa_exterior",
    5: "ref_setting_fuji_river_trail",
    6: "ref_setting_senju_dock",
    7: "ref_setting_nikko_cedars",
    8: "ref_setting_yamadera_temple",
    9: "ref_setting_mogami_river",
    10: "ref_setting_kisakata_lagoon",
    11: "ref_setting_shirakawa_barrier",
    12: "ref_setting_genjuan_bamboo",
    13: "ref_setting_kyoto_rakushisha",
    14: "ref_setting_tokaido_highway",
    15: "ref_setting_withered_moor",
}

CONTEXTUAL_PROP_MAP: Dict[Tuple[int, int], str] = {
    (1, 1): "ref_props_travel_gear",
    (1, 7): "ref_props_inkstone_brush",
    (1, 8): "ref_props_inkstone_brush",
    (1, 9): "ref_props_tea_hearth_irori",
    (1, 10): "ref_props_inkstone_brush",
    (2, 7): "ref_props_inkstone_brush",
    (3, 3): "ref_props_basho_leaves",
    (3, 5): "ref_props_basho_leaves",
    (3, 7): "ref_props_basho_leaves",
    (3, 8): "ref_props_inkstone_brush",
    (3, 9): "ref_props_tea_hearth_irori",
    (4, 4): "ref_props_basho_leaves",
    (4, 8): "ref_props_tea_hearth_irori",
    (5, 1): "ref_props_travel_gear",
    (5, 2): "ref_props_travel_gear",
    (5, 8): "ref_props_tea_hearth_irori",
    (5, 9): "ref_props_inkstone_brush",
    (6, 1): "ref_props_travel_gear",
    (6, 3): "ref_props_travel_gear",
    (6, 4): "ref_props_travel_oi",
    (6, 7): "ref_props_travel_gear",
    (7, 3): "ref_props_inkstone_brush",
    (7, 7): "ref_props_travel_gear",
    (8, 2): "ref_props_travel_gear",
    (8, 4): "ref_props_inkstone_brush",
    (9, 2): "ref_props_travel_gear",
    (9, 5): "ref_props_inkstone_brush",
    (10, 2): "ref_props_travel_gear",
    (10, 3): "ref_props_inkstone_brush",
    (11, 1): "ref_props_travel_gear",
    (11, 3): "ref_props_travel_gear",
    (11, 9): "ref_props_tea_hearth_irori",
    (12, 3): "ref_props_inkstone_brush",
    (12, 5): "ref_props_inkstone_brush",
    (12, 7): "ref_props_inkstone_brush",
    (13, 2): "ref_props_inkstone_brush",
    (13, 4): "ref_props_inkstone_brush",
    (14, 1): "ref_props_travel_gear",
    (14, 7): "ref_props_inkstone_brush",
    (14, 8): "ref_props_inkstone_brush",
    (15, 3): "ref_props_travel_gear",
    (15, 9): "ref_props_inkstone_brush",
}
