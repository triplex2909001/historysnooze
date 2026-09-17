"""
HistorySnooze Prompt Engine - Settings Anchors Part 1 (Settings 1-7)
Module: anchor_settings_part1.py
Rule <= 150 lines compliant.
"""

from typing import Any, Dict

BASHO_SETTINGS_PART1: Dict[str, Dict[str, Any]] = {
    "ref_setting_iga_ueno": {
        "id": "ref_setting_iga_ueno",
        "tag_type": "SETTING",
        "file_name": "ref_setting_iga_ueno.jpg",
        "aliases": [
            "iga_ueno",
            "ueno_castle",
            "iga",
            "part_01_setting",
            "ref_setting_iga_ueno.jpg",
        ],
        "description": (
            "Establishing wide shot of Ueno Castle and rural mountain basin of Iga Province at lavender twilight, "
            "feathery red Japanese pines, sloping ishigaki stone castle foundations rising above autumn mist, "
            "thatched peasant cottages and samurai compounds with dark kawara roof tiles nestled among rolling green hills, peaceful evening woodsmoke rising"
        ),
    },
    "ref_setting_edo_nihonbashi": {
        "id": "ref_setting_edo_nihonbashi",
        "tag_type": "SETTING",
        "file_name": "ref_setting_edo_nihonbashi.jpg",
        "aliases": [
            "edo_nihonbashi",
            "nihonbashi",
            "kanda_waterworks",
            "part_02_setting",
            "ref_setting_edo_nihonbashi.jpg",
        ],
        "description": (
            "Bustling historic Edo merchant capital centered around the grand arched wooden span of Nihonbashi Bridge in early morning mist, "
            "traditional timber shopfronts with blue noren curtains, Kanda canal waterworks with raised earthen dikes and heavy cedar sluice gates, "
            "distant white shikkui warehouses (kura) lining sparkling waterways"
        ),
    },
    "ref_setting_fukagawa_interior": {
        "id": "ref_setting_fukagawa_interior",
        "tag_type": "SETTING",
        "file_name": "ref_setting_fukagawa_interior.jpg",
        "aliases": [
            "fukagawa_interior",
            "fukagawa",
            "edo_hermitage",
            "hermitage",
            "ref_setting_edo_hermitage",
            "ref_setting_edo_hermitage.jpg",
            "basho_an",
            "part_03_setting",
            "ref_setting_fukagawa_interior.jpg",
        ],
        "description": (
            "Interior establishing wide shot of Matsuo Basho humble thatched hermitage hut in Fukagawa, quiet weathered "
            "cedarwood timber walls, aged tatami grass mats on floor, low rustic wooden writing desk with dark slate inkstone, "
            "bamboo brush, and folded washi paper scroll, small ceramic teapot on hearth with faint embers, soft warm oil lantern light, sliding wooden shoji screen open to garden"
        ),
    },
    "ref_setting_fukagawa_exterior": {
        "id": "ref_setting_fukagawa_exterior",
        "tag_type": "SETTING",
        "file_name": "ref_setting_fukagawa_exterior.jpg",
        "aliases": [
            "fukagawa_exterior",
            "sumida_riverbank",
            "basho_exterior",
            "part_04_setting",
            "ref_setting_fukagawa_exterior.jpg",
        ],
        "description": (
            "Serene exterior view of the humble thatched Fukagawa hermitage perched on the tidal marsh riverbank of the Sumida River, "
            "broad green banana (basho) plant leaves wet with steady evening rain swaying in gentle wind, weathered bamboo fence, "
            "tidal marsh reeds, distant river barges gliding on grey misty waters"
        ),
    },
    "ref_setting_fuji_river_trail": {
        "id": "ref_setting_fuji_river_trail",
        "tag_type": "SETTING",
        "file_name": "ref_setting_fuji_river_trail.jpg",
        "aliases": [
            "fuji_river_trail",
            "fuji_river",
            "satta_pass",
            "part_05_setting",
            "ref_setting_fuji_river_trail.jpg",
        ],
        "description": (
            "Winding gravel pilgrim footpath running along rushing turquoise waters of Fuji River in crisp autumn mist, "
            "distant snow-crested cone of Mount Fuji rising majestically above golden fog, switchbacks of Satta Pass overlooking Suruga Bay with ancient pines clinging to ocean cliffs"
        ),
    },
    "ref_setting_senju_dock": {
        "id": "ref_setting_senju_dock",
        "tag_type": "SETTING",
        "file_name": "ref_setting_senju_dock.jpg",
        "aliases": [
            "senju_dock",
            "senju_departure",
            "sumida_ferry",
            "part_06_setting",
            "ref_setting_senju_dock.jpg",
        ],
        "description": (
            "Historic wooden riverboat ferry landing dock at Senju on upper Sumida River at pink-tinged spring dawn, "
            "wide wooden barges moored along riverbank, weeping willows with fresh green buds, unpaved northern highway "
            "stretching northward into soft morning haze, traditional post-station wooden gatehouses"
        ),
    },
    "ref_setting_nikko_cedars": {
        "id": "ref_setting_nikko_cedars",
        "tag_type": "SETTING",
        "file_name": "ref_setting_nikko_cedars.jpg",
        "aliases": [
            "nikko_cedars",
            "toshogu_cedars",
            "urami_falls",
            "part_07_setting",
            "ref_setting_nikko_cedars.jpg",
            "tohoku_trail",
            "ref_setting_tohoku_trail",
            "ref_setting_tohoku_trail.jpg",
            "mountain_pass",
            "ref_setting_mountain_pass",
            "ref_setting_mountain_pass.jpg",
            "oku_no_hosomichi",
        ],
        "description": (
            "Sacred ancient forest grove of towering giant cryptomeria redwoods and cedar trees at Nikko, morning mountain mist "
            "swirling between mossy roots and stone lanterns, ornate vermilion-lacquered Toshogu shrine gateways glowing through "
            "cedar canopy, roaring Urami waterfall cascading into crystalline mountain gorge"
        ),
    },
}
