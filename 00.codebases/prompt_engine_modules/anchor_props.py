"""
HistorySnooze Prompt Engine - Props Anchors
Module: anchor_props.py
Rule <= 150 lines compliant.
"""

from typing import Any, Dict

BASHO_PROPS_ANCHORS: Dict[str, Dict[str, Any]] = {
    "ref_props_inkstone_brush": {
        "id": "ref_props_inkstone_brush",
        "tag_type": "PROP",
        "file_name": "ref_props_inkstone_brush.jpg",
        "aliases": [
            "inkstone_brush",
            "inkstone",
            "brush",
            "suzuri_fude",
            "writing_tools",
            "ref_prop_bamboo_staff_inkstone",
            "bamboo_staff_inkstone",
            "ref_props_inkstone_brush.jpg",
        ],
        "description": (
            "Intimate still life macro composition of authentic Japanese poet writing tools on a dark aged cedarwood writing desk, "
            "a carved antique slate stone inkstone (suzuri) filled with glossy black sumi ink, beside a slender carved bamboo calligraphy "
            "brush (fude) with delicate pointed horsehair bristles, a freshly unrolled scroll of fibrous handmade mulberry washi paper "
            "bearing faint vertical haiku characters in brushstroke ink, soft warm candlelight glinting off the wet ink pool"
        ),
    },
    "ref_props_travel_gear": {
        "id": "ref_props_travel_gear",
        "tag_type": "PROP",
        "file_name": "ref_props_travel_gear.jpg",
        "aliases": [
            "travel_gear",
            "bamboo_staff_hat",
            "pilgrim_gear",
            "staff_hat",
            "ref_prop_bamboo_staff_inkstone",
            "bamboo_staff_inkstone",
            "ref_props_travel_gear.jpg",
        ],
        "description": (
            "Still life arrangement of Edo-period wandering poet pilgrim traveling gear resting against a rustic wooden veranda post, "
            "a wide conical woven bamboo and sedge straw hat (sugegasa) with braided chin strap, a polished amber-brown dried gourd flask "
            "(hyotan) for water with red silk cord, a sturdy bamboo walking staff worn smooth by handgrip, and folded straw rain cape (mino), peaceful evening ambient light"
        ),
    },
    "ref_props_basho_leaves": {
        "id": "ref_props_basho_leaves",
        "tag_type": "PROP",
        "file_name": "ref_props_basho_leaves.jpg",
        "aliases": [
            "basho_leaves",
            "banana_leaves",
            "plantain_leaves",
            "ref_props_basho_leaves.jpg",
        ],
        "description": (
            "Close-up still life macro shot of broad, fibrous green banana plant (bashō) leaves heavy with glistening drops of fresh "
            "evening rain, delicate natural vein patterns illuminated by soft diffuse daylight, gentle water droplets clinging to the "
            "glossy deep-green leaf margins, tranquil Zen garden atmosphere"
        ),
    },
    "ref_props_tea_hearth_irori": {
        "id": "ref_props_tea_hearth_irori",
        "tag_type": "PROP",
        "file_name": "ref_props_tea_hearth_irori.jpg",
        "aliases": [
            "tea_hearth_irori",
            "irori",
            "tea_hearth",
            "iron_kettle",
            "tetsubin",
            "ref_props_tea_hearth_irori.jpg",
        ],
        "description": (
            "Intimate cozy still life of a traditional Japanese sunken square hearth (irori) set into aged cedarwood floorboards, "
            "glowing white and amber charcoal embers radiating gentle warmth, dark textured cast-iron tea kettle (tetsubin) suspended "
            "from a carved wooden jizaikagi hearth hanger, delicate wisps of steam rising into calm dim room"
        ),
    },
    "ref_props_travel_oi": {
        "id": "ref_props_travel_oi",
        "tag_type": "PROP",
        "file_name": "ref_props_travel_oi.jpg",
        "aliases": [
            "travel_oi",
            "pilgrim_backpack",
            "straw_backpack",
            "oi",
            "ref_props_travel_oi.jpg",
        ],
        "description": (
            "Authentic Edo-period wandering pilgrim traveler backpack chest (oi), crafted from lightweight woven wicker and dark "
            "lacquered cedar framing with woven hemp shoulder straps, open front showing carefully stacked travel journals bound in "
            "washi paper, ink case, brush holder, and spare waraji straw sandals tied beneath"
        ),
    },
}
