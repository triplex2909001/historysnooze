"""
HistorySnooze: Canonical 150-Beat Image Prompt Builder for Julie d'Aubigny
SSOT-compliant with NotebookLM 813e73eb-7327-4c9b-9651-fe416e6d180c,
04_VISUAL_PROMPT_ENGINE.md, and Gatekeeper GK3.
Strictly incorporates the FIXED ILLUMINATED MANUSCRIPT STYLE TAIL.
"""

import sys
import json
from pathlib import Path

SCRIPTS_DIR = Path("/media/vpsg16gb/Media/historysnooze/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))
from julie_canonical_data import CANONICAL_SCENES

# Master Fixed Style Tail from NotebookLM SSOT
SIGNATURE_FRAME_TAIL = (
    "late-15th-century illuminated manuscript style painting, tempera and shell-gold, "
    "flat medieval perspective, fine brown-ink outlines, full-bleed edge-to-edge painting extending "
    "to all four edges of the 16:9 canvas, zero margins, no outer paper, no parchment border, "
    "no decorative frame, no page border, wide cinematic 16:9 composition, ultra-high-resolution (4K)"
)

PERIOD_ANCHOR = (
    "seventeenth-century Baroque France and Paris of King Louis XIV, authentic French classical architecture, "
    "limestone arches, grand stables of Versailles, French Salle d'Armes, Palais-Royal opera house, "
    "authentic period woolen doublets, cavalier boots, rapiers, and Baroque royal silk court dress, "
    "strictly authentic 17th-century French historical setting"
)

PARTS_ANCHORS = [
    {
        "part": 1,
        "c_ref": "ref_character_julie_daubigny_young",
        "s_ref": "ref_setting_versailles_grand_stables",
        "p_ref": "ref_props_french_training_foil",
    },
    {
        "part": 2,
        "c_ref": "ref_character_julie_daubigny_young",
        "s_ref": "ref_setting_paris_fencing_school",
        "p_ref": "ref_props_french_court_rapier",
    },
    {
        "part": 3,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_travel_road",
        "p_ref": "ref_props_travel_leather_trunk",
    },
    {
        "part": 4,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_tavern_courtyard",
        "p_ref": "ref_props_french_court_rapier",
    },
    {
        "part": 5,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_marseille_opera_harbor",
        "p_ref": "ref_props_baroque_opera_score",
    },
    {
        "part": 6,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_avignon_convent_night",
        "p_ref": "ref_props_monastery_incense_cross",
    },
    {
        "part": 7,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_travel_road",
        "p_ref": "ref_props_french_court_rapier",
    },
    {
        "part": 8,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_gilded_pallas_helmet_spear",
    },
    {
        "part": 9,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_baroque_opera_score",
    },
    {
        "part": 10,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_versailles_hall_of_mirrors",
        "p_ref": "ref_props_baroque_carnival_mask",
    },
    {
        "part": 11,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_versailles_hall_of_mirrors",
        "p_ref": "ref_props_royal_pardon_scroll",
    },
    {
        "part": 12,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_brussels_court_salon",
        "p_ref": "ref_props_travel_leather_trunk",
    },
    {
        "part": 13,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_baroque_opera_score",
    },
    {
        "part": 14,
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_fontainebleau_forest_clearing",
        "p_ref": "ref_props_baroque_carnival_mask",
    },
    {
        "part": 15,
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_monastery_sanctuary",
        "p_ref": "ref_props_monastery_incense_cross",
    },
]

FORBIDDEN_WORDS = [
    "photorealistic", "3d render", "cgi", "octane render",
    "cyberpunk", "modern", "anime", ".gif",
    "--ar", "--v 6", "--style"
]

def generate_canonical_prompts():
    prompts_list = []

    for p_info in PARTS_ANCHORS:
        p_idx = p_info["part"]
        c_ref = p_info["c_ref"]
        s_ref = p_info["s_ref"]
        p_ref = p_info["p_ref"]

        scenes = CANONICAL_SCENES[str(p_idx)] if str(p_idx) in CANONICAL_SCENES else CANONICAL_SCENES[p_idx]
        assert len(scenes) == 10, f"Part {p_idx} has {len(scenes)} scenes instead of 10"

        for b_idx, scene_raw in enumerate(scenes, 1):
            beat_filename = f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg"

            # Clean scene of redundant tail artifacts
            scene_clean = scene_raw.strip().rstrip(". ")
            for suffix in [
                ", wide cinematic 16:9 composition, ultra-high-resolution 4K",
                ", wide cinematic 16:9 composition, ultra-high-resolution (4K)",
                ", cinematic wide angle",
                "wide cinematic 16:9 composition, ultra-high-resolution 4K",
            ]:
                if scene_clean.endswith(suffix):
                    scene_clean = scene_clean[:-len(suffix)].rstrip(",. ")

            # 3-Tier Assembly with Fixed Style Tail
            prompt_str = (
                f"{beat_filename}: [CHARACTER: {c_ref}] [SETTING: {s_ref}] [PROP: {p_ref}] "
                f"{scene_clean}, {PERIOD_ANCHOR}, {SIGNATURE_FRAME_TAIL}"
            )

            # Validate Length
            if len(prompt_str) > 1500:
                raise ValueError(f"{beat_filename} exceeds 1500 characters ({len(prompt_str)})")

            # Validate Forbidden terms
            for term in FORBIDDEN_WORDS:
                if term in prompt_str.lower():
                    raise ValueError(f"{beat_filename} contains forbidden term: {term}")

            # Validate no newlines
            if "\n" in prompt_str:
                raise ValueError(f"{beat_filename} contains newline")

            prompts_list.append(prompt_str)

    assert len(prompts_list) == 150, f"Expected 150 prompts, got {len(prompts_list)}"
    return prompts_list


if __name__ == "__main__":
    prompts = generate_canonical_prompts()

    project_root = Path("/media/vpsg16gb/Media/historysnooze/output/Julie d'Aubigny - Julie d'Aubigny - The Swordswoman Who Set Paris Ablaze and Defied the King")
    p1_file = project_root / "01. Preproduction" / "combined_imageprompts.txt"
    p2_file = project_root / "02. Media Generation" / "combined" / "combined_imageprompts.txt"

    formatted_content = "\n\n".join(prompts) + "\n"

    p1_file.write_text(formatted_content, encoding="utf-8")
    p2_file.write_text(formatted_content, encoding="utf-8")

    print(f"✅ Generated and validated 150 prompts with FIXED ILLUMINATED MANUSCRIPT STYLE!")
    print(f"📁 01: {p1_file}")
    print(f"📁 02: {p2_file}")
    print(f"Sample Beat 01:\n{prompts[0]}\n")
