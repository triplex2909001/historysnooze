#!/usr/bin/env python3
"""
Canonical Production Generator for Emperor Nero Sleep Documentary
Generates:
1. 15-Part ambient sleep narration script (150 paragraphs, ~15,500-16,500 words).
2. 150 unique, cinematic 4K visual prompt beats with Reference Anchor Kit tags.
3. Formatted DOCX outline and script, JSON metadata, combined prompts file.
4. Uploads clean authentic assets to Google Drive folder 1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT.
5. Updates Google Sheets row 11 in tab "Pipeline" with direct URLs and timestamp.
"""

import os
import sys
import json
import docx
from datetime import datetime
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Constants & SSOT
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
GDRIVE_FOLDER_ID = "1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
IDEA_ID = "id_jt1ps3"
CHARACTER_NAME = "Emperor Nero"
DOC_TITLE = "Emperor Nero: The Darkest Midnight Before the Fall of Rome | The History Snooze"

PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output") / "Emperor Nero - Emperor Nero - The Darkest Midnight Before the Fall of Rome _ The History Snooze"
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"
MEDIA_DIR = PROJECT_ROOT / "02. Media Generation"
AUDIO_DIR = MEDIA_DIR / "audio"
KEYFRAMES_DIR = MEDIA_DIR / "keyframes"

for d in [PROJECT_ROOT, PREPROD_DIR, MEDIA_DIR, AUDIO_DIR, KEYFRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Clean up old fake audio and keyframes
for f in AUDIO_DIR.glob("*.wav"):
    f.unlink()
for f in KEYFRAMES_DIR.glob("*.jpg"):
    f.unlink()

print(f"============================================================")
print(f"HISTORYSNOOZE CANONICAL GENERATOR: {DOC_TITLE}")
print(f"Target Directory: {PROJECT_ROOT}")
print(f"============================================================")

PARTS_INFO = [
    {
        "index": 1,
        "title": "The Sunrise at Antium and the Child of Bronze",
        "c_ref": "ref_character_emperor_nero_young",
        "s_ref": "ref_setting_antium_coastal_palace",
        "p_ref": "ref_props_roman_bronze_cradle",
        "focus": "Birth at coastal Antium, sea spray at dawn, the bronze-bearded Ahenobarbus lineage, exile of Agrippina, and childhood under seaside breezes."
    },
    {
        "index": 2,
        "title": "Return from Exile and the Poisoned Banquet of Claudius",
        "c_ref": "ref_character_emperor_nero_young",
        "s_ref": "ref_setting_rome_palatine_hill_courtyard",
        "p_ref": "ref_props_poisoned_mushroom_platter",
        "focus": "Recall from exile, Agrippina's marriage to Claudius, adoption into the Claudian dynasty, the fateful autumn banquet, and elevation to Caesar at seventeen."
    },
    {
        "index": 3,
        "title": "The Golden Five Years - Seneca, Burrus, and the New Age",
        "c_ref": "ref_character_emperor_nero_young",
        "s_ref": "ref_setting_seneca_philosophy_library",
        "p_ref": "ref_props_papyrus_scroll_philosophy",
        "focus": "The Quinquennium Neronis, Stoic wisdom under Seneca's library lamps, Burrus maintaining the legions, arts, music, and peaceful imperial administration."
    },
    {
        "index": 4,
        "title": "The Shadow in the Banqueting Hall - The Fall of Britannicus",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_imperial_banquet_hall",
        "p_ref": "ref_props_golden_goblet_wine",
        "focus": "Growing rivalry, the poisoned wine goblet during the winter feast of Saturnalia, silent courtiers, and the descent into solitary paranoia on the Palatine."
    },
    {
        "index": 5,
        "title": "The Empress Mother and the Golden Court of Baiae",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_palatine_private_gardens",
        "p_ref": "ref_props_golden_lyre_instrument",
        "focus": "The rise of Poppaea Sabina, artistic obsession with the Greek cithara, deep fracture with Agrippina, and tension under moonlit coastal colonnades."
    },
    {
        "index": 6,
        "title": "The Crimson Bay of Pozzuoli - A Mother's Fate",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_bay_of_naples_night",
        "p_ref": "ref_props_imperial_ship_lantern",
        "focus": "The collapsible pleasure vessel on the calm Tyrrhenian waters, torches reflecting on the dark waves, the midnight villa raid, and remorse."
    },
    {
        "index": 7,
        "title": "The Great Fire of Rome - The Night of Ash and Starlight",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_great_fire_of_rome_ruins",
        "p_ref": "ref_props_crimson_torch_flame",
        "focus": "The blaze erupting near Circus Maximus in July 64, sky bathed in amber and crimson embers, relief camps in imperial gardens, and poetic lamentations."
    },
    {
        "index": 8,
        "title": "The Domus Aurea - The Revolving Palace of Ivory and Gold",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_domus_aurea_golden_hall",
        "p_ref": "ref_props_domus_aurea_ivory_ceiling",
        "focus": "The architectural wonder across the Oppian Hill, revolving dining ceiling showering rose petals, man-made sea, and the colossal bronze statue."
    },
    {
        "index": 9,
        "title": "The Pisonian Shadow - Whispers, Philosophy, and Daggers",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_roman_curia_marble_baths",
        "p_ref": "ref_props_senatorial_piso_scroll",
        "focus": "The 65 AD conspiracy, betrayal uncovered by slaves, the noble farewells of Seneca and Lucan, and the arbiter of elegance Petronius."
    },
    {
        "index": 10,
        "title": "The Greek Odyssey - The Artist-Emperor and the Crown of Laurel",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_olympia_greece_temple",
        "p_ref": "ref_props_greek_laurel_wreath",
        "focus": "Triumph in Greece, chariot races at Olympia, singing before amphitheatres under starlight, cutting the first turf of the Corinth Canal."
    },
    {
        "index": 11,
        "title": "The Gathering Tempest - Echoes of Revolt from Gaul and Hispania",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_palatine_silent_hallway",
        "p_ref": "ref_props_praetorian_deserted_helmet",
        "focus": "Rebellions of Vindex in Gaul and Galba in Hispania, intercepted letters arriving by night couriers, and the sudden silence of the Senate."
    },
    {
        "index": 12,
        "title": "The Deserted Palatine - Empty Chambers and Vanishing Guards",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_empty_emperor_chambers",
        "p_ref": "ref_props_unlit_oil_lamp",
        "focus": "Midnight abandonment, Praetorian guards bribed away, echoing footsteps through marble galleries, and the lonely emperor seeking refuge."
    },
    {
        "index": 13,
        "title": "The Midnight Escape - The Cloaked Ride along the Via Nomentana",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_nomentana_road_misty_night",
        "p_ref": "ref_props_cloak_hood_rain",
        "focus": "Four loyal freedmen, thunderstorms over the Roman Campagna, muffled hooves in the mud, lightning revealing ruined aqueducts, and flight to Phaon's villa."
    },
    {
        "index": 14,
        "title": "The Final Sanctuary - The Cellar of Phaon and the Last Artist",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_phaon_suburban_villa_room",
        "p_ref": "ref_props_iron_dagger_blade",
        "focus": "Hiding in the reed cellar, the decree of the Senate declaring him a public enemy, horsemen approaching at dawn, the whisper of 'Qualis artifex pereo'."
    },
    {
        "index": 15,
        "title": "The Ashes of the Pincian Hill - Memory, Starlight, and Eternal Rome",
        "c_ref": "ref_character_emperor_nero_emperor",
        "s_ref": "ref_setting_pincian_hill_twilight",
        "p_ref": "ref_props_marble_funeral_urn",
        "focus": "The loyal concubine Acte laying him to rest on the Pincian Hill, fresh flowers left on his tomb for centuries, the Nero Redivivus myth, and midnight stillness."
    }
]

print(f"Loaded {len(PARTS_INFO)} parts metadata.")
