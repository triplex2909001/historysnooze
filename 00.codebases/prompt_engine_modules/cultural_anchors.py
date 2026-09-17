"""
HistorySnooze Prompt Engine - Cultural & Period Anchors
Module: cultural_anchors.py
Rule <= 150 lines compliant.
"""

import re
from typing import Dict, List

# CULTURAL & HISTORICAL PERIOD ANCHOR REGISTRY
CULTURAL_ANCHORS: Dict[str, Dict[str, str]] = {
    "matsuo_basho": {
        "era": "Seventeenth-century Edo period Japan",
        "period_anchor": (
            "seventeenth-century Edo-period Japan, authentic traditional Japanese timber architecture, "
            "sloping ishigaki stone foundations, white shikkui plaster walls, dark ceramic kawara tile roofs, "
            "wooden yagura pavilions, sliding paper shoji screens, tatami mats, peaceful Zen garden aesthetics"
        ),
        "style_fusion": (
            "late-15th-century illuminated manuscript style painting fused with Japanese Edo gold-leaf screen aesthetics "
            "(Kano and Rimpa school traditions), tempera and shell-gold accents, flat Japanese perspective, "
            "fine brown-ink outlines"
        ),
        "negative_constraints": (
            "strictly authentic feudal Japanese architecture, no European castle battlements, "
            "no Western stone towers, no conical medieval turrets, no Gothic fortress walls"
        ),
    },
    "musa_i_of_mali": {
        "era": "Fourteenth-century Mali Empire",
        "period_anchor": (
            "fourteenth-century Mali Empire and Trans-Saharan desert crossroads, authentic West African Sudano-Sahelian "
            "adobe architecture, monumental sun-dried earth-brick compounds, protruding toron timber beams, "
            "smooth clay plaster, conical earthen minarets, woven Sahelian textiles, royal Mandinka regalia"
        ),
        "style_fusion": (
            "late-15th-century illuminated manuscript style painting fused with Sahelian royal court gold-leaf traditions, "
            "tempera and burnished shell-gold accents, flat perspective, fine brown-ink outlines"
        ),
        "negative_constraints": (
            "strictly authentic medieval West African and Saharan setting, no European stone castles, "
            "no Gothic cathedrals, no Romanesque masonry, no Western knights, no European battlements"
        ),
    },
    "marcus_aurelius": {
        "era": "Second-century Imperial Rome",
        "period_anchor": (
            "second-century Imperial Rome (Pax Romana), authentic classical Roman architecture, "
            "monumental marble colonnades, Corinthian columns, Roman fora, barrel-vaulted stone basilicas, "
            "terracotta-tiled porticos"
        ),
        "style_fusion": (
            "illuminated manuscript style painting fused with classical Roman fresco and gold-leaf mosaic aesthetics, "
            "tempera and shell-gold accents, flat perspective, fine brown-ink outlines"
        ),
        "negative_constraints": (
            "strictly authentic classical Roman antiquity setting, no medieval Gothic castles, "
            "no European feudal battlements"
        ),
    },
    "default": {
        "era": "Historical period authentic setting",
        "period_anchor": "authentic regional historical vernacular architecture and setting",
        "style_fusion": (
            "late-15th-century illuminated manuscript style painting, tempera and shell-gold, "
            "flat medieval perspective, fine brown-ink outlines"
        ),
        "negative_constraints": (
            "historically accurate setting, strictly no anachronistic architecture, no out-of-period structures"
        ),
    },
}

SIGNATURE_FRAME_TAIL = (
    "full-bleed edge-to-edge painting extending to all four edges of the 16:9 canvas, "
    "zero margins, no outer paper, no parchment border, no decorative frame, no page border, "
    "wide cinematic 16:9 composition, ultra-high-resolution (4K)"
)

FORBIDDEN_TERMS = [
    "photorealistic",
    "3d render",
    "cgi",
    "octane render",
    "cyberpunk",
    "modern",
    "anime",
    "border",
    "frame",
    "parchment edge",
    "margin",
    ".gif",
]

VALID_TAG_TYPES = ["CHARACTER", "SETTING", "PROP", "INGREDIENT"]
TAG_REGEX = re.compile(
    r"\[(CHARACTER|SETTING|PROP|INGREDIENT):\s*([^\]]+)\]", re.IGNORECASE
)


def resolve_character_anchor(character_name: str) -> Dict[str, str]:
    slug = re.sub(r"[^a-z0-9_]", "_", character_name.lower().strip())
    for key in CULTURAL_ANCHORS:
        if key in slug or slug in key:
            return CULTURAL_ANCHORS[key]
    return CULTURAL_ANCHORS["default"]
