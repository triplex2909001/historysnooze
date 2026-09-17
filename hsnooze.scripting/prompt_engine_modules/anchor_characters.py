"""
HistorySnooze Prompt Engine - Character Anchors
Module: anchor_characters.py
Rule <= 150 lines compliant.
"""

from typing import Any, Dict

BASHO_CHARACTER_ANCHORS: Dict[str, Dict[str, Any]] = {
    "ref_character_basho_young": {
        "id": "ref_character_basho_young",
        "tag_type": "CHARACTER",
        "file_name": "ref_character_basho_young.jpg",
        "aliases": [
            "basho_young",
            "young_basho",
            "kinsaku",
            "matsuo_kinsaku",
            "ref_character_basho_young.jpg",
        ],
        "description": (
            "Full-body portrait of seventeenth-century Japanese samurai youth Matsuo Kinsaku (young Bashō), "
            "aged twenty, handsome youthful visage with clear observant eyes, neat samurai topknot (chonmage), "
            "dark indigo-dyed hemp kimono with subtle sleeve crest, hakama trousers, white tabi socks with clean "
            "straw waraji sandals, slender wakizashi companion sword at waist, standing poised amidst morning mist on an ancient road"
        ),
    },
    "ref_character_basho_traveler": {
        "id": "ref_character_basho_traveler",
        "tag_type": "CHARACTER",
        "file_name": "ref_character_basho_traveler.jpg",
        "aliases": [
            "basho_traveler",
            "traveler_basho",
            "basho_pilgrim",
            "ref_character_basho_traveler.jpg",
            "ref_character_basho",
            "basho",
            "matsuo_basho",
            "ref_character_matsuo_basho",
            "ref_character_matsuo_basho.jpg",
            "protagonist",
        ],
        "description": (
            "Full-body portrait of seventeenth-century Japanese wandering poet pilgrim Matsuo Bashō, aged forty-five, "
            "weathered contemplative visage with deep thoughtful eyes, wispy beard, traveler topknot beneath a conical "
            "woven sedge hat (sugegasa) on upper back, dark indigo coarse hemp traveler kimono with patched sleeves, "
            "straw sandals (waraji), carrying a gnarled wooden pilgrim walking staff, standing in morning mist on a mountain road"
        ),
    },
    "ref_character_basho_elder": {
        "id": "ref_character_basho_elder",
        "tag_type": "CHARACTER",
        "file_name": "ref_character_basho_elder.jpg",
        "aliases": [
            "basho_elder",
            "elder_basho",
            "master_basho",
            "tosei",
            "master_tosei",
            "ref_character_basho_elder.jpg",
        ],
        "description": (
            "Full-body portrait of revered master poet Matsuo Bashō in his final mature years, aged fifty-one, "
            "venerable dignified countenance with fine laugh lines, profound serene gaze radiating inner detachment (karumi), "
            "silver-streaked wispy beard, faded charcoal-grey monk-style hemp robe (kesa) over simple kimono, holding a slender "
            "bamboo calligraphy brush, resting on tatami mats in soft warm lantern light"
        ),
    },
    "ref_character_sora": {
        "id": "ref_character_sora",
        "tag_type": "CHARACTER",
        "file_name": "ref_character_sora.jpg",
        "aliases": [
            "sora",
            "kawai_sora",
            "companion",
            "ref_character_sora.jpg",
        ],
        "description": (
            "Full-body portrait of Kawai Sora, faithful disciple and traveling companion of Matsuo Basho, thirty-five "
            "years old, earnest calm face, shaved crown with short neat hair in Buddhist layman style, wearing simple "
            "dark charcoal hemp robes with sleeves tied up for walking, carrying a woven straw backpack (oi) strapped "
            "across shoulders holding travel journals and ink, wearing straw sandals (waraji) on dusty feet, standing quietly beside a mountain marker"
        ),
    },
    "ref_character_buccho": {
        "id": "ref_character_buccho",
        "tag_type": "CHARACTER",
        "file_name": "ref_character_buccho.jpg",
        "aliases": [
            "buccho",
            "buccho_osho",
            "zen_master_buccho",
            "ref_character_buccho.jpg",
        ],
        "description": (
            "Full-body portrait of venerable Zen master Buccho Oshō, spiritual teacher and neighbor of Basho at Fukagawa, "
            "aged sixty, shaven head, deeply etched serene features expressing profound Zen enlightenment, wearing traditional "
            "layered dark Buddhist monastic robes and a brown silk kesa stole draped diagonally across shoulder, holding "
            "carved wooden prayer beads (juzu), standing gracefully in quiet contemplation"
        ),
    },
}
