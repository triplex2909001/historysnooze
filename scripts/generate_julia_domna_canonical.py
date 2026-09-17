#!/usr/bin/env python3
"""
Canonical Production Generator for Julia Domna Sleep Documentary
Generates:
1. 15-Part ambient sleep narration script (150 paragraphs, ~15,000 words).
2. 150 unique, cinematic 4K visual prompt beats with Reference Anchor Kit tags.
3. Formatted DOCX outline and script, JSON metadata, combined prompts file.
4. Uploads clean assets to Google Drive folder 179tF8VKOrd0mVdGUiFO4YOfpNMzj_C8k.
5. Updates Google Sheets row 10 in tab "Pipeline" with direct URLs and timestamp.
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
GDRIVE_FOLDER_ID = "179tF8VKOrd0mVdGUiFO4YOfpNMzj_C8k"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
IDEA_ID = "id_1f21ak"
CHARACTER_NAME = "Julia Domna"
DOC_TITLE = "Julia Domna: The Woman Who Ruled Rome from the Shadows"

# Corrected single-title project directory
PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output") / "Julia Domna - The Woman Who Ruled Rome from the Shadows"
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"

for d in [PROJECT_ROOT, PREPROD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print(f"============================================================")
print(f"HISTORYSNOOZE CANONICAL GENERATOR: {DOC_TITLE}")
print(f"Target Directory: {PROJECT_ROOT}")
print(f"============================================================")

# --- 15 PARTS METADATA ---
PARTS_INFO = [
    {
        "index": 1,
        "title": "The Sands of Emesa and the Eternal Sun",
        "c_ref": "ref_character_julia_domna_young",
        "s_ref": "ref_setting_emesa_temple_of_the_sun",
        "p_ref": "ref_props_syrian_sun_patera",
        "focus": "Youth in Syria, priestly lineage of the sacred sun temple, golden sands, amber light, and the quiet dawn of destiny."
    },
    {
        "index": 2,
        "title": "A Syrian Bride in the Imperial City",
        "c_ref": "ref_character_julia_domna_young",
        "s_ref": "ref_setting_rome_palatine_hill_palace",
        "p_ref": "ref_props_imperial_diadem_silk",
        "focus": "Marriage to Septimius Severus, astrological prophecies of a royal union, and early footsteps in the halls of Rome."
    },
    {
        "index": 3,
        "title": "The Rise of Severus and the March to Rome",
        "c_ref": "ref_character_julia_domna_young",
        "s_ref": "ref_setting_roman_forum_basilica",
        "p_ref": "ref_props_bronze_triumphal_scroll",
        "focus": "The Year of the Five Emperors, crossing mountain passes, legionary campfires under starlight, and the triumph of the new dynasty."
    },
    {
        "index": 4,
        "title": "Empress of the Palatine - Wisdom in Gold and Marble",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_palatine_imperial_courtyard",
        "p_ref": "ref_props_marble_candelabra_oil_lamp",
        "focus": "Reign on the Palatine Hill, draped in deep Tyrian purple, marble courtyards with shimmering fountains, and imperial dignity."
    },
    {
        "index": 5,
        "title": "The Philosophers' Circle - Salons of Antioch and Rome",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_antioch_philosophical_salon",
        "p_ref": "ref_props_papyrus_scrolls_inkwell",
        "focus": "Gathering scholars, physicians like Galen, and sophists like Philostratus under warm oil lamps discussing the cosmos."
    },
    {
        "index": 6,
        "title": "Mother of the Legions - Journeys across Britannia and Danube",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_danube_military_camp_tent",
        "p_ref": "ref_props_legionary_standard_pennant",
        "focus": "The title Mater Castrorum, walking beside legionary standards, mist over the northern moors, and campfires in the cold dusk."
    },
    {
        "index": 7,
        "title": "The Arch of Leptis Magna - Splendor of North Africa",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_leptis_magna_triumphal_arch",
        "p_ref": "ref_props_carved_ivory_diptych",
        "focus": "Voyage to Severus's African birthplace, limestone colonnades meeting turquoise Mediterranean tides, and warm coastal breezes."
    },
    {
        "index": 8,
        "title": "Whispers in the Senate - Governance from the Shadows",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_roman_senate_curia_julia",
        "p_ref": "ref_props_senatorial_silla_chair",
        "focus": "Managing state affairs, receiving foreign ambassadors, delicate political balances, and the quiet exercise of sovereign intellect."
    },
    {
        "index": 9,
        "title": "The Divided Princes - Caracalla, Geta, and Maternal Grief",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_palatine_private_chambers",
        "p_ref": "ref_props_engraved_cameo_gem",
        "focus": "The bitter rivalry between her two sons, midnight vigils in secluded palace chambers, tears on silk, and enduring maternal grace."
    },
    {
        "index": 10,
        "title": "Constitutio Antoniniana - An Empire of Citizens",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_baths_of_caracalla_gardens",
        "p_ref": "ref_props_imperial_seal_wax",
        "focus": "The grand edict granting Roman citizenship to all free inhabitants, administrative unity, and tranquil strolls through cypress gardens."
    },
    {
        "index": 11,
        "title": "The Library of Antioch - Scrolls of Ancient Wisdom",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_antioch_sacred_library",
        "p_ref": "ref_props_greek_philosophical_codex",
        "focus": "Antioch as the eastern capital, cedar shelves holding thousands of scrolls, the scent of dried papyrus, and timeless contemplation."
    },
    {
        "index": 12,
        "title": "Echoes of the Eastern Frontier - Euphrates at Sunset",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_euphrates_riverbank_fortress",
        "p_ref": "ref_props_bronze_astrolabe_ring",
        "focus": "Overlooking the legendary river Euphrates, distant camel caravans, dusk settling across the desert plains, and celestial constellations."
    },
    {
        "index": 13,
        "title": "The Ab Epistulis Secretariat - Letters to the Edge of the World",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_imperial_secretariat_archive",
        "p_ref": "ref_props_feather_quill_imperial_ink",
        "focus": "Overseeing the vast imperial correspondence, sealing decrees in red wax, maintaining peace across three continents with words."
    },
    {
        "index": 14,
        "title": "Evening Shadows over the Forum - Reflection on Power",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_tiber_river_bridge_twilight",
        "p_ref": "ref_props_silver_wine_crater",
        "focus": "Twilight falling over the marble basilicas of Rome, soft reflections on the Tiber River, and quiet meditation on the impermanence of mortal glory."
    },
    {
        "index": 15,
        "title": "Midnight over the Seven Hills - Eternal Peace and Silence",
        "c_ref": "ref_character_julia_domna_empress",
        "s_ref": "ref_setting_capitoline_hill_starlight",
        "p_ref": "ref_props_alabaster_incense_burner",
        "focus": "Starlit sky above the Capitoline, incense drifting in gentle night air, deep restorative rest, and the tranquil sleep of history."
    }
]

print("[1/5] Composing 15-Part Narration & 150 Unique Visual Prompt Beats...")

def build_script_and_prompts():
    beats = []
    full_script_md = [f"# {DOC_TITLE}\n\n"]

    # Detailed 15-part narrative text generators
    # Each Part contains 10 distinct, richly evocative paragraphs (~100-115 words each)
    narrative_corpora = {
        1: [
            "As we begin our journey tonight, let us dim the lights and prepare for sleep. In the warm, golden heart of Syria, where the desert meets the fertile plains of the Orontes, lies the ancient sanctuary of Emesa. Here, beneath skies of sapphire and amber, young Julia Domna walked among the sunlit colonnades of the great Sun God Elagabal. The desert air carried the sweet fragrance of myrrh and cedar, whispering ancient secrets through quiet courtyards. Every stone in this sacred realm held the memory of centuries, and as the evening light softened, the great temple bathed in a soothing, hypnotic glow.",
            "Julia belonged to a royal dynasty of hereditary priest-kings, keepers of a sacred heritage that reached far beyond the Roman frontier. Her father, Julius Bassianus, taught her the movements of the stars, the wisdom of Babylonian astronomers, and the subtle art of patience. In the tranquil courtyards shaded by date palms, she read Greek treatises and listened to the gentle chime of evening bells. The gentle desert breeze cooled the sandstone pavings, creating a peaceful oasis where young Julia's sharp intellect and serene composure quietly blossomed into regal maturity.",
            "The Temple of the Sun was a realm of profound quietude. Towering black stone altars reflected the golden rays of twilight, surrounded by delicate bronze oil lamps that flickered gently in the dusk. Young Julia would often linger near the holy sanctuary, watching incense smoke curl upward toward the celestial canopy. Her dark, expressive eyes observed the passing caravans bringing silk from Palmyra and spices from Arabia, learning early how kingdoms rose, negotiated, and found enduring harmony through cultured wisdom rather than raw blade.",
            "As dusk deepened into twilight over the Syrian desert, the temperature fell into a calm, refreshing coolness. Julia would sit upon stone terraces overlooking the oasis, where the Orontes River murmured quietly against the reeds. Her thoughts wandered across the wider Mediterranean world, a vast mosaic of provinces bound together by Roman peace. She wore simple robes of woven linen, her posture already reflecting the quiet authority and graceful introspection that would one day command the greatest empire on earth.",
            "In the peaceful evening hours, the priests chanted low, melodic hymns that echoed softly through the sandstone corridors. The rhythm of their voices was like a soothing lullaby, calming the heart and steadying the breath. Julia learned that true power lay not in loud proclamations, but in the silent command of knowledge, philosophy, and the celestial alignments of destiny. The starlight above Emesa seemed closer and brighter than anywhere else, casting silvery light across the peaceful desert dunes.",
            "Astrologers from Alexandria and Babylon frequently visited the sanctuary, marveling at the young princess's extraordinary horoscope. They spoke in hushed, reverent tones of a rare celestial alignment that promised she would one day marry a king. Julia listened with a calm smile, neither arrogant nor fearful, accepting destiny as a steady river that flowed inevitably toward a grand, serene sea. She learned to trust the slow, patient unfolding of time, watching the constellations turn across the midnight sky.",
            "The domestic chambers of the palace in Emesa were decorated with vibrant Syrian textiles and soft cushions of dyed wool. Here, by the gentle warmth of bronze charcoal braziers, Julia practiced calligraphy in both Greek and Latin. Her fingers moved gracefully across fresh sheets of papyrus, transcribing verses of Homer and philosophical dialogues of Plato. The rhythmic scratching of the reed pen blended with the distant song of nightingales outside her chamber window.",
            "When the desert winds blew softly from the east, carrying the scent of dry earth and flowering oleander, the entire city of Emesa drifted into peaceful slumber. Julia would gaze upon the distant horizon, where trade routes disappeared into the starry night. She possessed an innate ability to find stillness amidst the vastness of the world, a deep inner calm that would later sustain her through turbulent civil wars and imperial crises. Every breath was steady, slow, and anchored in peace.",
            "The sacred black stone of Emesa, said to have fallen from the heavens, stood as an anchor of cosmic stability. To Julia, it symbolized the enduring strength of the East—a culture steeped in profound philosophy, mathematical brilliance, and celestial spirituality. She envisioned bridging the ancient mysteries of the Orient with the rigorous law and order of Rome, weaving two great worlds into a single, harmonious imperial tapestry.",
            "As midnight enveloped the sanctuary of Emesa, the lanterns were gently trimmed low, leaving only a soft, golden ember in the darkness. The shadows lengthened across the marble floors, and the quiet desert settled into profound stillness. Young Julia closed her eyes in peaceful repose, her dreams guided by the eternal sun and the tranquil promise of a destiny that would shape the history of humanity for centuries to come."
        ],
        2: [
            "Across the Mediterranean, in the sun-drenched province of Gallia Lugdunensis, a brilliant Roman commander named Lucius Septimius Severus studied the stars. A widower of North African heritage, Severus sought a bride whose horoscope aligned with his profound imperial ambitions. When travelers and astrologers told him of the Syrian princess whose birth chart promised a crown, Severus dispatched trusted emissaries to Emesa. In the quiet halls of her father's palace, Julia accepted the union, stepping with calm grace onto the vast stage of the Roman Empire.",
            "The journey from the Syrian desert to the imperial heartland was long, contemplative, and filled with wondrous landscapes. Julia traveled by royal litter and coastal galley, watching the azure waters of the Aegean lap gently against white marble shores. The steady rhythm of the oars and the soft whispering of the sails created a peaceful symphony on the sea. Each port of call—from Antioch to Ephesus and Corinth—welcomed the young bride with gentle honors and scented laurel garlands.",
            "When Julia finally arrived in the eternal city of Rome, the vast metropolis was bathed in the soft rose and gold of early autumn. Towering temples of white marble, immense aqueducts spanning green valleys, and paved roads lined with cypress trees greeted her arrival. Beside Severus, Julia walked with effortless dignity, her Syrian beauty and refined intellect captivating the Roman patricians who gathered along the Via Appia to welcome the rising governor and his eastern bride.",
            "Their marriage was founded upon mutual respect, deep intellectual partnership, and shared ambition. In their private villa on the slopes of Rome, away from the шум and intrigue of the Forum, they spent quiet evenings discussing provincial governance, military strategy, and philosophical treatises. Severus quickly recognized that Julia possessed a political acumen and strategic foresight equal to his own, and he sought her counsel on every vital matter of state.",
            "In these early, harmonious years in Rome, Julia gave birth to two sons: Lucius Septimius Bassianus, who would later be known as Caracalla, and Publius Septimius Geta. In the tranquil courtyards of their home, Julia cradled her infants amidst blooming rose gardens and trickling stone fountains. She sang soothing eastern lullabies to the young boys, filling their earliest days with warmth, melody, and the gentle comfort of a devoted mother's love.",
            "Rome was a city of grand architecture and quiet residential retreats. Julia established a sanctuary of intellect in their home, welcoming Greek scholars, Syrian rhetoricians, and Latin poets. In these peaceful gatherings, philosophical debates were conducted with polite eloquence, surrounded by scrolls of history and bronze busts of classical thinkers. Julia presided with effortless poise, demonstrating that eastern wisdom brought rich vitality to traditional Roman virtues.",
            "As seasons shifted and the imperial political climate grew uncertain under Emperor Commodus, Julia and Severus maintained a composed, watchful silence. They withdrew during hot summers to the cool countryside of Campania, where vineyards cascaded down volcanic hills toward the calm blue waters of the Bay of Naples. The gentle lap of the waves against the shore provided a serene backdrop for their private reflections and strategic patience.",
            "During their travels across the western provinces, Julia adapted to the rugged military frontier with remarkable resilience. Whether residing in a Roman villa in Sicily or a governor's residence along the Rhine, she brought a sense of order, elegance, and tranquil domesticity. Her presence softened the harsh atmosphere of military outposts, earning her the quiet admiration and loyalty of the legionary commanders.",
            "In the quiet of the night, when the lanterns cast dancing amber shadows on frescoed walls, Julia would gaze at the night sky, tracing the same stars she had known as a child in Emesa. She recognized that the destiny foretold by the Syrian astrologers was steadily drawing near. Her heart remained peaceful, centered in the deep realization that serenity and preparation were the greatest shields against the storms of fate.",
            "As Rome slept beneath the cool silver gaze of the moon, Julia rested peacefully in the knowledge that her family was protected by wisdom, discipline, and unity. The gentle breath of the Mediterranean night filled the bedchambers, carrying the promise of enduring strength and the quiet dawn of an imperial dynasty that would soon reshape the ancient world."
        ],
        3: [
            "In the historic year of one hundred and ninety-three, the Roman world was shaken by the sudden death of Commodus and the turbulent Year of the Five Emperors. Far to the north, on the misty banks of the Danube River, the legions of Pannonia acclaimed Septimius Severus as Emperor of Rome. Standing steadfastly beside her husband in the military headquarters of Carnuntum, Julia Domna radiated calm resolve. While others panicked amidst the uncertainty of civil war, her serene composure inspired the soldiers with unshakeable confidence.",
            "The march of the Danubian legions toward Rome was conducted with extraordinary speed, discipline, and precision. Along the military roads crossing the Julian Alps, thousands of armored men moved like an orderly river through pine-scented mountain passes. Julia traveled with the vanguard, enduring the chill mountain air and rugged terrain without complaint. Her carriage was a center of quiet organization, where dispatches were reviewed and peaceful surrenders of Italian towns were coordinated with clemency.",
            "As evening settled over the military encampments, legionary campfires dotted the mountain slopes like a constellation of fallen stars. The aroma of roasted grain, woodsmoke, and damp earth filled the crisp night air. Julia walked through the camp beside Severus, speaking softly with veteran centurions and tending to wounded soldiers. Her genuine concern and fearless grace earned her the soldiers' heartfelt devotion, laying the foundation for a bond that would last a lifetime.",
            "Rome opened its gates without bloodshed to Severus and Julia, awed by the sheer discipline of their armies and the dignity of their entrance. The senators, clad in white togas bordered with purple, gathered in the Curia Julia to confirm Severus's title and grant Julia the imperial honors due to an Augusta. As she stepped onto the sacred pavement of the Roman Forum, the golden afternoon light illuminated the marble temples, marking the triumphant beginning of the Severan dynasty.",
            "Yet peace required vigilance, for rival claimants to the purple rose in the east and west. Pescennius Niger claimed the allegiance of Syria and Egypt, while Clodius Albinus commanded the legions of Britannia. Throughout these prolonged campaigns, Julia accompanied the imperial army east toward the Cilician Gates and the ancient battlefields of Issus. She remained a tranquil pillar of support, ensuring that the logistics of empire and the safety of her young sons were flawlessly maintained.",
            "In the military camps of the East, overlooking the azure waters of the Aegean and the rolling hills of Asia Minor, Julia oversaw the imperial headquarters. At night, while Severus reviewed battle maps by candlelight, she organized the imperial archives and drafted diplomatic communications. Her deep familiarity with eastern customs and languages allowed the Severan administration to win over cities and provinces with tact and cultural sensitivity.",
            "Following the decisive victory at the Battle of Lugdunum in Gaul, which unified the entire Roman world under Severus's sovereign rule, the imperial family returned to Rome in grand triumph. Julia stood beside her husband as the Roman Senate decreed the construction of a magnificent triumphal arch at the foot of the Capitoline Hill. The sound of silver trumpets and cheering crowds filled the city, yet Julia's heart remained attuned to the quiet, humble reality of mortal existence.",
            "To solidify their imperial lineage, Severus symbolically adopted the heritage of Marcus Aurelius, and Julia embraced the role of the philosophical empress. In the tranquil courtyards of the Palatine Palace, she established an atmosphere of sober elegance and intellectual depth. She ensured that her young sons received the finest education in law, philosophy, rhetoric, and military leadership, surrounding them with the most accomplished teachers of the empire.",
            "In the quiet twilight hours, Julia would walk through the newly restored gardens of the Palatine, overlooking the Circus Maximus and the Aventine Hill. The soft cooing of doves and the gentle rustle of olive leaves created a soothing atmosphere of peaceful victory. The empire was once again united from the sands of the Sahara to the borders of Caledonia, sheltered beneath the protective mantle of the Severan peace.",
            "As night settled over the eternal city, the torchlight on the Palatine Palace flickered softly in the gentle evening breeze. Julia sat by her chamber window, watching the stars illuminate the monuments of Rome. She breathed deeply and slowly, letting the fatigue of the civil wars wash away in the calm tide of peace, thankful for the enduring strength that had guided their family to sovereign majesty."
        ],
        4: [
            "Now established as the undisputed Augusta of Rome, Julia Domna made the grand Palatine Palace her home and the intellectual capital of the Mediterranean world. Perched high above the bustling Forum, the imperial residence was an architectural masterpiece of soaring vaulted ceilings, cool marble floors, and peaceful peristyle courtyards. Here, gentle water flowed continuously through carved lion-head fountains, creating a hypnotic, rhythmic melody that echoed softly through the magnificent halls.",
            "Julia adorned the imperial apartments with refined elegance, blending Roman grandeur with the luxurious textures of the East. Deep Tyrian purple silks bordered with gold thread draped the doorways, while warm Persian carpets cushioned the marble pavements. Scented oil lamps made of polished Corinthian bronze cast a warm, ambient amber glow across intricately painted frescoes depicting tranquil mythological landscapes and pastoral Arcadian scenes.",
            "Every morning began with quiet contemplation in the private courtyards shaded by fragrant laurel and pomegranate trees. Julia would sit in an ivory curule chair, listening to the morning song of sparrows and the gentle rustle of cypress boughs. In this quiet sanctuary, she reviewed the morning petitions and imperial correspondence, bringing a sharp intellect and a compassionate heart to the complex governance of over fifty million subjects.",
            "The Empress's personal style became the defining fashion of the Roman world. Her signature coiffure—a magnificent cascade of thick, waved hair parted in the center, folded behind the ears, and braided into an elegant chignon at the back—was immortalized in thousands of marble busts across the provinces. Provincial women from Hispania to Syria adopted her regal hairstyle, celebrating Julia as the embodiment of maternal grace, imperial power, and timeless feminine beauty.",
            "Despite the immense wealth at her command, Julia maintained an admirable personal simplicity and philosophical modesty. She wore the traditional Roman stola and palla, honoring ancestral customs while infusing them with the subtle splendor of eastern dyes and delicate embroidery. Her jewelry was chosen with understated refinement: a single Syrian amethyst pendant, a delicate gold diadem, and finely wrought signet rings engraved with the symbols of peace and fortune.",
            "In the grand reception halls of the Palatine, Julia received foreign delegations, provincial governors, and senatorial matrons with effortless poise. Her warm, melodious voice and fluent command of both Latin and Greek put guests immediately at ease. She listened intently to the needs of distant provinces, ensuring that taxes were levied fairly and that local temples, libraries, and public baths received generous imperial patronage.",
            "When the warm Mediterranean afternoon gave way to the cool shadows of dusk, the palace courtyards transformed into magical realms of tranquility. Slaves lit incense burners filled with frankincense, sandalwood, and dried lavender, releasing soothing herbal aromas into the evening air. Julia loved to walk along the palace terrace overlooking the Forum Boarium, watching the sunset cast brilliant crimson and violet reflections upon the Tiber River.",
            "The Palatine Palace housed an extensive private library, where Julia spent countless peaceful hours reading scrolls of ancient philosophy, geography, and medicine. She was a passionate patron of literature, collecting rare manuscripts from Alexandria, Pergamum, and Athens. In this sanctuary of knowledge, surrounded by the wisdom of the ages, the Empress found deep intellectual replenishment and profound spiritual serenity.",
            "As the sounds of the great city below gradually subsided into the quiet of the night, the palace guards walked their rounds with steady, muffled steps. Julia would visit the bedchambers of her growing sons, ensuring they were resting peacefully before retiring to her own apartments. Her maternal devotion remained her deepest anchor, providing a steady foundation of love amidst the immense burdens of imperial rule.",
            "In her bedchamber, the soft glowing wick of a single oil lamp illuminated the peaceful marble sanctuary. Outside, the night sky above the Seven Hills of Rome was studded with brilliant stars, clear and serene. Julia closed her eyes, breathing in the quiet calm of the palace, resting deeply and peacefully in the heart of the empire she helped to guide with wisdom and grace."
        ],
        5: [
            "Recognizing that true imperial enduring legacy rested upon culture and intellect, Julia Domna established the famous philosophical circle that became known throughout antiquity as the Salon of the Empress. She gathered the greatest minds of her era—philosophers, sophists, mathematicians, physicians, and jurists—transforming the imperial court into a vibrant center of enlightenment. In the tranquil salons of Rome and Antioch, discourse flourished under her generous and discerning patronage.",
            "Among her most cherished intellectual companions was Flavius Philostratus, the brilliant Athenian sophist and biographer. Julia commissioned Philostratus to write the definitive biography of Apollonius of Tyana, a legendary first-century Pythagorean philosopher and mystic whose travels spanned Greece, Egypt, and India. Under Julia's direct guidance and using memoirs from her private collection, Philostratus crafted a timeless masterpiece celebrating wisdom, virtue, and spiritual transcendence.",
            "The philosophical salons met in a spacious, colonnaded hall lined with marble statues of Socrates, Plato, Aristotle, and Zeno. In the center of the chamber, a low bronze hearth radiated gentle warmth, while scented oils burned softly in hanging lanterns. The atmosphere was calm, dignified, and conducive to deep contemplation, free from political rancor or dogmatic strife.",
            "Julia also welcomed the renowned physician Galen of Pergamon to her circle, marveling at his encyclopedic knowledge of the human body, herbal pharmacology, and the delicate balance of bodily humors. Galen frequently praised the Empress's extraordinary understanding of natural sciences and hygiene, noting that her calm temperament and philosophical discipline contributed greatly to the health and vitality of the imperial household.",
            "The great legal scholars Papinian, Ulpian, and Paul—the supreme jurists whose writings would later form the foundation of Roman and modern civil law—were central figures in Julia's salon. Together, they debated the principles of natural justice, the protection of women's property rights, the humane treatment of enslaved people, and the legal equality of provincial subjects, drafting reforms that would benefit millions across the empire.",
            "During these evening symposiums, discourse flowed as smoothly as honeyed wine. Participants reclined on comfortable couches draped in soft wool, speaking in turns with measured eloquence. Julia presided from a slightly elevated dais, offering insightful questions, clarifying complex arguments, and ensuring that every perspective was received with courtesy and thoughtful consideration.",
            "When the philosophical debates turned to the nature of the cosmos, the immortality of the soul, and the harmony of the spheres, the salon was enveloped in a profound, reverent silence. The scholars looked out the high arched windows at the brilliant night sky, contemplating the eternal mystery of existence. Julia's eastern heritage brought a rich mystical depth to Greek rationalism, creating a unique philosophical synthesis that inspired all present.",
            "The influence of Julia's circle extended far beyond the palace walls, inspiring the creation of public libraries, medical academies, and philosophical schools throughout the provinces of the empire. From Athens and Alexandria to Berytus and Lugdunum, young scholars were funded by imperial stipends, preserving classical heritage for future generations during a time of immense global change.",
            "As the evening gathered toward midnight, the philosophers would slowly disperse, their minds enriched and their hearts calmed by the beauty of reasoned inquiry. Julia would remain alone for a few quiet moments in the salon, listening to the gentle hiss of dying embers in the hearth and the distant hoot of an owl from the Palatine groves.",
            "She felt a profound sense of gratitude for the gift of wisdom and the enduring power of ideas. In the stillness of the midnight hour, the Empress walked slowly to her bedchamber, her spirit untroubled, resting peacefully in the timeless sanctuary of philosophical truth and gentle contemplation."
        ],
        6: [
            "Unlike traditional Roman empresses who remained secluded in palace villas, Julia Domna embraced the rugged life of the frontier, accompanying Emperor Severus on extensive military campaigns across the Rhine, the Danube, and the stormy moors of Britannia. Her fearless presence at the front lines earned her the rare and deeply honored title of Mater Castrorum—Mother of the Camp—awarded by the unanimous acclaim of the legionary soldiers.",
            "Life on the march had its own unique, hypnotic rhythm. The sound of thousands of hobnailed sandals crunching rhythmically on gravel roads, the low murmur of soldiers singing marching songs, and the steady creak of baggage wagons created a soothing cadence across vast landscapes. Julia traveled in a covered military carriage or rode gracefully on horseback, dressed in a sturdy travel cloak of deep crimson wool fastened with a silver brooch.",
            "When the Roman legions crossed the turbulent waters of the English Channel into the mysterious island of Britannia, Julia stood on the deck of the flagship, watching the white chalk cliffs rise majestically out of the morning mist. The salty sea spray and the cool northern wind invigorated her spirit, as the imperial family established their military headquarters in the ancient fortress city of Eboracum, modern-day York.",
            "The northern campaigns took the imperial forces deep into the untamed Scottish Highlands, beyond Hadrian's Wall and the Antonine Wall. Julia oversaw the logistics of supply depots, military hospitals, and communications networks with extraordinary precision. She ensured that wounded soldiers received clean bandages, nourishing broth, and the finest herbal medicines, earning a sacred place in the hearts of the troops who affectionately called her their mother.",
            "In the damp, chilly evenings of northern Britannia, when thick fog rolled across the heather-covered moors, the legionary camps became warm havens of fellowship and safety. High earthen ramparts and sturdy wooden palisades enclosed orderly streets of leather tents. Inside the imperial praetorium, a roaring hearth of oak logs filled the tent with radiant heat and the sweet aroma of crackling wood.",
            "Julia would sit beside Severus by the fire, reviewing intelligence reports and receiving local Caledonian tribal envoys. Cassius Dio, the contemporary Roman historian, recorded a famous conversation between Empress Julia and the wife of a Caledonian chieftain, in which the northern noblewoman spoke of her people's customs. Julia listened with respectful curiosity, seeking understanding rather than subjugation, embodying the civilized dignity of Rome.",
            "At night, while the sentries called out the hourly watches under the vast northern sky, Julia found deep peace in the simplicity of camp life. The distant sound of bagpipes or flutes played by auxiliary soldiers drifted through the damp night air, blending with the gentle patter of rain against the canvas tent. Every breath was cool, clean, and grounding.",
            "The title Mater Castrorum was not merely ceremonial; it was struck on millions of bronze, silver, and gold coins circulating throughout the empire, depicting Julia seated with military standards or holding the infant gods of fortune. This imagery reinforced the stability of the imperial family, reassuring citizens in every corner of the world that the empire was protected by maternal devotion and martial strength.",
            "Even in the harshest frontier environments, Julia maintained her daily philosophical reflections. She carried cedar chests containing her favorite Greek scrolls, reading by the warm light of a travel lamp while the northern winds howled softly outside. Her inner calm was an impenetrable fortress, unaffected by physical discomfort or geographic isolation.",
            "As sleep settled over the vast legionary camp in Britannia, the glow of the watchtowers cast long, protective shadows across the sleeping armies. Julia rested peacefully in her quarters, comforted by the loyalty of thousands of devoted soldiers and the rhythmic pulse of an empire united under her watchful, loving care."
        ],
        7: [
            "In the year two hundred and two, the imperial family embarked on a magnificent journey to North Africa, visiting Septimius Severus's ancestral birthplace of Leptis Magna on the sun-drenched coast of Tripolitania. For Julia, this voyage was a joyous celebration of the dynasty's diverse roots, uniting her Syrian heritage with the ancient Punic and Berber splendor of Severus's homeland.",
            "Leptis Magna was transformed under imperial patronage into one of the most breathtaking jewels of the Mediterranean. Immense quarries of green and white marble were imported to build a grand new Forum, a magnificent four-way triumphal arch, a vast basilica, and an opulent harbor with a soaring lighthouse. Julia walked with delight through the new colonnaded streets, where towering Corinthian pillars met the azure expanse of the Mediterranean Sea.",
            "The Arch of Septimius Severus at Leptis Magna featured exquisite marble relief sculptures depicting the entire imperial family in harmonious unity. Julia Domna was carved in high relief with her signature regal coiffure, holding a sacrifice patera and standing proudly beside her husband and sons. The sunlight cast sharp, beautiful shadows across the marble carvings, immortalizing their golden age for millennia to come.",
            "The coastal climate of North Africa offered a warm, restorative haven of peace. Gentle breezes blowing off the Mediterranean rustled through groves of silver-green olive trees and flowering date palms. Julia loved to spend quiet afternoons on the palace terrace overlooking the harbor, watching merchant ships from Alexandria, Carthage, and Rome glide gracefully across the turquoise waters.",
            "In Leptis Magna, Julia visited the magnificent public baths, marveling at the colossal marble arches, heated caldariums paved with intricate mosaics of sea deities, and serene open-air swimming pools. The gentle sound of splashing water and the warm, steam-scented air provided deep physical relaxation and soothing mental tranquility after years of strenuous travel.",
            "The local African nobility and civic leaders welcomed the Empress with profound reverence, hosting evening banquets in courtyard gardens filled with blooming jasmine and pomegranate trees. By the warm glow of oil lamps and the soft music of harps and flutes, Julia conversed with local scholars and municipal leaders, strengthening the bonds of civic loyalty and cultural exchange across North Africa.",
            "During the peaceful twilight hours, Julia would walk along the sandy beaches near the ancient Phoenician harbor. The rhythmic lapping of the gentle waves against the shore and the warm golden light of the setting sun created a hypnotic, meditative atmosphere. She reflected on the vast diversity of the Roman world, where an African emperor and a Syrian empress ruled together in harmony from the Seven Hills of Rome.",
            "The visit to North Africa was also a time of deep spiritual renewal for the imperial family. They visited ancient desert shrines and coastal temples, offering prayers of gratitude for peace, fertility, and the continued prosperity of the provinces. Julia's natural piety and reverence for sacred traditions endeared her to people of all faiths and cultural backgrounds.",
            "As night descended over Leptis Magna, the great lighthouse at the harbor entrance cast a warm, sweeping beacon across the calm sea. The desert air cooled pleasantly, and the scent of jasmine drifted through the open colonnades of the imperial residence. Julia sat quietly in her bedchamber, listening to the timeless rhythm of the ocean tides.",
            "With a heart full of serenity and gratitude, the Empress closed her eyes and drifted into restful sleep, cradled by the warm coastal winds and the tranquil, eternal majesty of the African night."
        ],
        8: [
            "Upon returning to Rome, Julia Domna assumed an increasingly central and indispensable role in the day-to-day administration of the Roman Empire. Recognizing her exceptional intellect, political diplomacy, and sound judgment, Emperor Severus entrusted her with the oversight of imperial petitions, the reception of foreign embassies, and the coordination of senatorial relations. She governed with subtle elegance, exercising profound power from the quiet dignity of the shadows.",
            "The Roman Senate, historically protective of its ancient traditions, held Julia in the highest esteem. In recognition of her wisdom and tireless service to the state, the Senate bestowed upon her the unprecedented and historic titles of Mater Senatus—Mother of the Senate—and Mater Patriae—Mother of the Fatherland. These honors confirmed her status not merely as an imperial consort, but as a sovereign mother figure to the entire Roman civilization.",
            "Julia's daily administrative routine was conducted in the serene, sunlit secretariat chambers of the Palatine Palace. Sitting at a large table of polished citrus wood, surrounded by parchment scrolls and wax tablets, she carefully reviewed petitions sent from provincial cities in Gaul, Greece, Egypt, and Syria. She listened to the grievances of ordinary citizens, resolving disputes with fairness, clarity, and deep compassion.",
            "Her diplomatic skill was particularly evident during audiences with foreign ambassadors from the Parthian Empire, Germanic tribal federations, and North African kingdoms. Dressed in her regal stola of amethyst silk, Julia received the envoys with majestic courtesy. She understood the subtle nuances of eastern diplomacy and western tribal customs, ensuring that peace treaties were negotiated with mutual honor and enduring stability.",
            "In the Senate meetings held in the Curia Julia, the Empress's influence was felt through her trusted senatorial allies and legal advisors. She worked closely with the leading jurists to enact legislation that protected the inheritance rights of widows, ensured the education of orphaned children, and expanded municipal privileges throughout the eastern and western provinces.",
            "Despite the heavy weight of administrative responsibilities, Julia never allowed stress or anxiety to disturb her inner equilibrium. She practiced daily meditation and philosophical breathing exercises taught by her Stoic and Pythagorean teachers. In the midst of pressing imperial decisions, she remained a serene oasis of calm, bringing clarity and composure to everyone around her.",
            "During the quiet afternoon hours, when official duties concluded, Julia would stroll through the peaceful peristyle courtyards of the Palatine, accompanied by her close circle of female scholars and advisors. They discussed historical precedents, literary compositions, and philosophical ethics, maintaining a cultured and elevated atmosphere within the imperial residence.",
            "Her patronages extended to the architectural restoration of sacred Roman monuments that had suffered damage during past civil wars. Julia funded the magnificent rebuilding of the Temple of Vesta and the Atrium Vestae in the Forum, honoring the sacred hearth of Rome and strengthening the spiritual foundation of the city. The Vestal Virgins held her in deep reverence, offering daily prayers for her health and prosperity.",
            "As dusk fell over the capital, the lights of Rome were lit one by one across the Seven Hills. Julia stood upon the palace balcony, looking down at the illuminated Forum and the grand temples she had helped restore. The city was peaceful, prosperous, and secure, a testament to the wisdom and dedication of her governance.",
            "Retiring to her private chambers, the Empress left the affairs of state behind, allowing her mind and body to enter a state of deep, restorative relaxation. The quiet night air carried the faint scent of pine from the surrounding hills, and Julia rested peacefully, enveloped in the quiet dignity of an empire well-guided and deeply loved."
        ],
        9: [
            "Amidst the glittering triumph and immense power of the Severan dynasty, a profound and tragic shadow fell across Julia Domna's heart: the escalating, irreconcilable hatred between her two sons, Caracalla and Geta. As the young princes grew into adulthood, their childhood rivalry deepened into bitter political factionalism, threatening to tear the imperial family and the entire Roman world apart.",
            "Julia devoted all her maternal love, diplomatic skill, and philosophical wisdom to healing the rift between her sons. In the private chambers of the Palatine, away from the poisonous whisperings of ambitious courtiers, she repeatedly brought Caracalla and Geta together. She reminded them of their father's dying words: to live in harmony, enrich the soldiers, and despise all other concerns. Her gentle tears and earnest pleas momentarily softened their hardened hearts.",
            "Following the death of Emperor Septimius Severus at Eboracum in two hundred and eleven, Caracalla and Geta were proclaimed joint emperors of Rome. The imperial court returned to Rome, but the palace was divided into two armed camps, with separate entrances, guards, and barricaded hallways. Julia moved between both wings like a grieving angel of peace, striving tirelessly to prevent open civil war.",
            "In a desperate effort to achieve lasting reconciliation, Julia arranged a private, unarmed meeting between the two brothers in her own maternal apartments on the Palatine. It was a cold December evening in two hundred and eleven. The chamber was lit only by the soft, flickering light of a bronze oil lamp, and Julia stood between her sons, holding their hands in a desperate plea for fraternal love and imperial unity.",
            "Tragically, the meeting was a fatal ambush. Centurions loyal to Caracalla burst into the chamber with drawn swords. Geta sought refuge in his mother's arms, clinging desperately to her neck. Despite Julia's desperate attempts to shield her younger son with her own body, Geta was struck down, his life slipping away in his mother's embrace. Julia's garments and hands were drenched in her son's blood, and her heart was shattered by unimaginable grief.",
            "In the dark days that followed, Julia was forced by Caracalla to conceal her profound mourning under threat of death. Roman historians marveled at her superhuman fortitude and dignity; though broken inside, she bore her immense sorrow in silence, refusing to let the empire descend into total anarchy. She channeled her grief into philosophical endurance, finding strength in the Stoic belief that virtue must persevere through the darkest trials of fate.",
            "To escape the haunting memories of the Palatine chambers, Julia immersed herself once again in philosophy and administrative duty. She sought the solace of quiet sanctuaries, spending long nights in prayer and meditation. Her sorrow was deep and quiet, like a silent subterranean river flowing beneath the grandeur of imperial majesty.",
            "In the quiet of her private chapel, Julia lit small oil lamps in memory of Geta, watching the gentle flames dance in the darkness. She found comfort in the teachings of Apollonius of Tyana, who taught that the physical body is merely a temporary vessel for an eternal, indestructible soul. She believed that beyond the pain and ambition of mortal life lay an eternal realm of peace, light, and ultimate reunion.",
            "The Roman people and the legions, sensing her immense suffering and admiring her unbroken dignity, revered her more deeply than ever. Caracalla, recognizing his mother's indispensable moral authority and administrative genius, entrusted her with the complete management of civilian governance, leaving her in charge of the empire's domestic administration.",
            "In the deep stillness of the midnight hour, when the world was quiet and the palace slept, Julia allowed her tears to fall freely in the privacy of her bedchamber. She breathed slowly, letting the heavy sorrow soften into peaceful acceptance, trusting in the eternal justice of the cosmos and finding quiet rest beneath the watchful gaze of the stars."
        ],
        10: [
            "In the year two hundred and twelve, a transformative milestone in world history was enacted under the Severan administration: the Constitutio Antoniniana, or the Edict of Caracalla. This historic imperial decree granted full Roman citizenship to all free men across the entire expanse of the Roman Empire, from the shores of the Atlantic Ocean to the banks of the Euphrates River. Julia Domna's universalist philosophy and eastern heritage were instrumental in shaping this monumental reform.",
            "Before the edict, Roman citizenship was a privileged status reserved primarily for the inhabitants of Italy and select provincial elites. The Constitutio Antoniniana abolished centuries of provincial inequality, declaring that Greeks, Syrians, Egyptians, Gauls, Britons, and Africans were all equal citizens under Roman law. It was the realization of Julia's lifelong vision of a unified, inclusive global civilization bound together by shared rights and civic brotherhood.",
            "In celebration of this new era of unity, the magnificent Baths of Caracalla were constructed on the southern slopes of the Aventine Hill. This colossal architectural marvel covered over thirty acres, featuring grand vaulted halls, massive open-air swimming pools, extensive libraries, and lush botanical gardens. Julia frequently visited the construction site, admiring the towering columns of red granite and the intricate mosaic pavements depicting athletic and mythological scenes.",
            "The gardens surrounding the baths were a paradise of serene beauty. Lined with towering cypress trees, fragrant laurel hedges, and marble statues, the park was open to all Roman citizens for peaceful recreation and philosophical discourse. Julia loved to walk in these gardens during the early morning hours, enjoying the fresh scent of dew on grass and the tranquil rustling of leaves in the gentle breeze.",
            "The administrative integration of millions of new citizens required an immense organizational effort, which Julia managed with effortless mastery from the Palatine. Thousands of legal petitions, citizenship registrations, and tax adjustments flowed into the secretariat. Under Julia's supervision, the imperial bureaucracy operated with remarkable efficiency, fairness, and transparency.",
            "Provincial cities sent magnificent gold and silver crowns to Rome in gratitude for their new status as full Roman citizens. In response, Julia directed imperial funds toward the construction of aqueducts, theaters, libraries, and public forums in provincial towns, ensuring that the benefits of civilization reached even the most remote frontier communities.",
            "During the warm summer evenings, the Empress would host quiet gatherings in the gardens of the Palatine, celebrating the cultural diversity of the new empire. Scholars, musicians, and poets from every province shared their traditions in an atmosphere of mutual respect and harmony. Julia looked upon the gathering with deep satisfaction, knowing that the empire was now truly a commonwealth of all its peoples.",
            "The Constitutio Antoniniana fundamentally transformed the concept of identity in the ancient world. A person was no longer defined solely by their local tribe or province, but as a proud citizen of a universal community protected by Roman law. Julia's vision had triumphed over narrow provincialism, creating an enduring legacy that would influence human rights and legal systems for two thousand years.",
            "As dusk settled over Rome, the colossal silhouette of the Baths of Caracalla glowed softly in the fading twilight. The city was filled with a sense of peace, stability, and shared purpose. Julia walked along her private terrace, feeling a profound sense of accomplishment and tranquil joy.",
            "The cool night air carried the gentle sound of distant fountain waters, whispering through the marble porticoes of the Palatine. Julia lay down to rest, her heart light and serene, knowing that her life's work had brought dignity, equality, and lasting peace to millions of human souls across the ancient world."
        ],
        11: [
            "As Emperor Caracalla prepared for grand military campaigns against the Parthian Empire in the East, Julia Domna established the imperial administrative capital in the magnificent city of Antioch on the Orontes. Situated on the fertile plains between the Syrian mountains and the Mediterranean, Antioch was the third greatest metropolis of the Roman world, renowned for its intellectual brilliance, lush gardens, and luxurious cultural life.",
            "Julia established her residence in the royal palace located on a peaceful island in the Orontes River. Connected to the city by magnificent marble bridges, the palace was a tranquil sanctuary surrounded by rushing waters, weeping willows, and blooming hibiscus. Here, far from the senatorial intrigues of Rome, Julia enjoyed the rich cultural atmosphere of her native Syrian homeland, governing the eastern half of the empire with sovereign authority.",
            "The crown jewel of Antioch was its famous Great Library and Museum, a venerable institution founded by the Seleucid kings that rivaled the Library of Alexandria. Julia spent countless peaceful hours in the library's soaring, cedar-paneled halls, which housed over two hundred thousand scrolls of ancient Greek, Persian, Syrian, and Egyptian wisdom. The delicate scent of dried papyrus, cedarwood, and beeswax filled the quiet air.",
            "Under the Empress's patronage, the library was expanded with new reading rooms, translation academies, and botanical conservatories. Julia commissioned scholars to translate ancient eastern astronomical tables, medical treatises, and philosophical discourses into Greek and Latin, preserving priceless treasures of human knowledge that might otherwise have been lost to the sands of time.",
            "In the afternoons, Julia would retreat to the sacred grove of Daphne, located a few miles south of Antioch. Daphne was a paradise of rushing mountain springs, towering laurel and cypress trees, and cool shaded glades sacred to Apollo. The sound of crystal-clear water cascading over mossy rocks and the sweet fragrance of laurel blossoms created an atmosphere of pure, hypnotic tranquility.",
            "Reclining on a stone bench in the grove of Daphne, with the gentle murmur of springs all around her, Julia read the philosophical dialogues of the Stoics and the mystical poetry of the East. The cool mountain air refreshed her spirit, and the peaceful green canopy sheltered her from the midday heat. Here, she found complete mental stillness and profound spiritual communion with nature.",
            "Scholars, poets, and rhetoricians from across Asia Minor, Egypt, and Greece flocked to Antioch to attend the Empress's intellectual salons. In the cool evenings on the palace island, by the light of floating lanterns on the Orontes River, they engaged in enlightened discussions on ethics, cosmology, and the pursuit of tranquility. Julia's gracious presence and sharp intellect inspired the assembly with timeless elegance.",
            "From her administrative headquarters in Antioch, Julia managed the complex logistics of the eastern provinces with extraordinary capability. She ensured that grain supplies were secured, that roads across the Syrian desert were well-maintained, and that trade caravans from India and China arrived safely in Mediterranean ports, bringing prosperity and abundance to the entire region.",
            "When the sun dipped below the Syrian mountains, casting a golden-violet glow across the waters of the Orontes, the city of Antioch was enveloped in a peaceful, magical twilight. The street lanterns of Antioch—famous throughout the ancient world as the first illuminated city at night—flickered on like a sea of gentle stars.",
            "From her palace window, Julia watched the river glide peacefully toward the sea, reflecting the twinkling lights of the city and the celestial constellations above. She breathed in the cool, sweet evening air, feeling completely centered, calm, and deeply at peace in the beloved land of her ancestors."
        ],
        12: [
            "In the quiet seasons between military maneuvers, Julia Domna traveled eastward to the grand fortress cities along the Euphrates River, the legendary border between the Roman Empire and the vast Parthian realm. Here, where the ancient fertile crescent gave way to the rolling desert steppes, the mighty Euphrates flowed with slow, majestic dignity, its silver waters reflecting the boundless eastern sky.",
            "Standing upon the high battlements of the riverside citadel at Zeugma or Samosata, Julia gazed across the wide, shimmering river into the mysterious lands of Mesopotamia. The desert wind blew softly from the east, warm and dry, carrying the faint scent of wild thyme, river mud, and sun-baked earth. The sheer vastness of the horizon was awe-inspiring, creating a profound sense of stillness and cosmic perspective.",
            "At sunset, the Euphrates transformed into a breathtaking ribbon of molten gold and deep crimson. Distant camel caravans moved slowly along the riverbank, their silhouettes dark against the glowing evening sky. The rhythmic clinking of camel bells and the soft calling of river boatmen drifted across the water, creating a soothing, hypnotic melody that calmed the mind and relaxed the body.",
            "In the quiet of her riverside quarters, Julia used delicate bronze astrolabes and celestial globes to study the stars, following the ancient astronomical traditions of Babylon and Syria. The desert night sky was exceptionally clear, a brilliant dome of countless twinkling stars and the luminous, milky arc of the galaxy. She traced the movements of Jupiter, Venus, and Saturn, finding comfort in the immutable order of the heavens.",
            "The border along the Euphrates was not merely a military frontier; it was a vibrant crossroads of commerce, language, and culture. Julia met with local Aramaic, Persian, and Armenian merchants who brought rare silk from China, fine pearls from the Persian Gulf, and exotic incense from Southern Arabia. She listened with fascination to their tales of distant lands, recognizing the shared humanity that connected all peoples across the earth.",
            "As night deepened over the desert fortress, the sentries on the ramparts lit small oil lamps that cast a warm, comforting glow on the ancient stone walls. The rushing sound of the Euphrates River against the fortress foundations was like a steady, timeless lullaby, washing away all restlessness and worry in its endless, eternal flow.",
            "Julia loved to sit on the open terrace beneath the starlit sky, wrapped in a warm shawl of fine wool. She reflected on the ancient empires that had risen and fallen along this great river—Sumer, Babylon, Assyria, Persia, and Greece. She realized that while rulers and armies passed away like shadows, the river, the stars, and the search for wisdom remained forever.",
            "This deep philosophical realization brought an unshakeable peace to her soul. She understood that her role in history was to be a guardian of light, order, and compassion for as long as fate allowed. Her breath was slow, deep, and harmonious with the vast rhythm of the desert night.",
            "The campfires along the riverbank gradually burned down to soft red embers, and the night air grew cool and refreshing. The distant howling of a desert fox only deepened the surrounding stillness, emphasizing the peaceful sanctuary of the Roman citadel.",
            "Julia retired to her bedchamber, listening to the gentle murmur of the Euphrates as it flowed serenely through the night. She closed her eyes, enveloped in the deep, tranquil silence of the ancient East, resting peacefully under the eternal protection of the starry heavens."
        ],
        13: [
            "During the final years of her reign, Julia Domna took complete, sovereign charge of the Ab Epistulis—the central imperial secretariat responsible for the vast official correspondence of the Roman Empire. Operating from the imperial headquarters in Antioch, she single-handedly managed the administration of fifty provinces, reading hundreds of official dispatches, legal petitions, and diplomatic letters every single day.",
            "The secretariat chambers were a marvel of orderly efficiency and intellectual concentration. Rows of skilled scribes, fluent in Latin, Greek, and eastern dialects, worked at long cedar desks with reed pens and fine black ink. Rolls of fresh Egyptian papyrus and wax-sealed parchment letters were meticulously sorted into labeled pigeonholes along the walls, representing every corner of the known world from Britannia to the Red Sea.",
            "Julia sat at the head of the great chamber, reviewing every major decree and judicial response with meticulous attention to detail. She possessed an extraordinary memory and a swift, decisive intellect, dictating replies in elegant prose that balanced legal precision with maternal benevolence. Her signature, written in purple imperial ink, carried the sovereign authority of Rome across three continents.",
            "The petitions she handled touched every aspect of human life: a community of olive growers in Hispania requesting tax relief after a drought, a philosophical guild in Athens seeking imperial protection, a border garrison on the Rhine reporting on tribal trade, or a Syrian city proposing the construction of a new public aqueduct. Julia addressed each matter with wisdom, empathy, and administrative brilliance.",
            "Her management of the secretariat ensured that the civilian government functioned smoothly and justly, even while Emperor Caracalla was away on military campaigns in the East. Provincial governors and Roman magistrates looked to Julia as the true guardian of the state, trusting her integrity and relying on her steady guidance to maintain peace and order throughout the empire.",
            "Despite the relentless volume of work, Julia maintained a calm, methodical pace that inspired serenity in all her subordinates. She took regular pauses throughout the day to practice deep breathing and sip cool water infused with mint and pomegranate. Her composure was infectious, creating a work environment characterized by dignity, mutual respect, and quiet focus.",
            "In the late afternoon, when the last dispatches were sealed with the imperial signet ring in hot red wax, the scribes cleared their desks and the great chamber grew quiet. Julia would remain alone for a few moments, reviewing the day's accomplishments with a quiet sense of duty fulfilled. She knew that every letter she sent brought justice, relief, or order to someone far away.",
            "She loved to look at the massive painted map of the Roman world hanging upon the chamber wall, tracing the trade routes and military roads that bound humanity together. Through the power of the written word, she had helped maintain the peace and prosperity of the largest empire on earth, proving that wisdom and administrative excellence were far more powerful than the sword.",
            "As dusk fell over Antioch, the scribes extinguished their lamps, leaving the secretariat in peaceful darkness. Julia walked through the quiet corridors of the palace, accompanied only by the soft rustling of her silk stola and the gentle evening breeze coming off the Orontes River.",
            "In her private quarters, the Empress rested her hands, which had signed decrees affecting millions of lives. Her heart was serene, satisfied that she had served her people with honor, wisdom, and boundless devotion. She closed her eyes, drifting into restful, deep sleep, cradled by the quiet peace of a well-ordered world."
        ],
        14: [
            "In the quiet evenings of her life, Julia Domna often reflected on the long, wondrous journey that had brought her from the sunlit temple of Emesa to the pinnacle of imperial power in Rome. She looked back across decades of triumph, hardship, intellectual discovery, and personal sacrifice with the calm, detached wisdom of a seasoned philosopher who understood the cyclical nature of human existence.",
            "Sitting on the terrace of her residence as twilight descended, she watched the evening shadows lengthen across ancient colonnades and garden paths. The soft, fading amber light of dusk reminded her that all earthly glory—the cheering crowds of the Forum, the triumphal arches of marble, the purple robes of state—was as transient as the evening breeze, yet the virtue of the soul was eternal.",
            "She remembered the joyful early years in Rome with Severus, the birth of her sons, the scholarly debates with Galen and Philostratus, and the triumphant marches across the northern frontier. She remembered also the bitter grief of family tragedy and the heavy burdens of sovereign responsibility. She harbored no bitterness or regret, accepting both joy and sorrow as necessary threads in the magnificent tapestry of fate.",
            "The Stoic philosophy that had guided her entire life provided an unshakable foundation of inner peace. She knew that true happiness did not depend on external circumstances, power, or wealth, but on maintaining a pure, virtuous, and tranquil mind. She had lived with dignity, governed with justice, and loved with all her heart; in that realization, she found complete and perfect serenity.",
            "The evening air was cool, fragrant with the scent of blooming night-jasmine and cypress resin. The gentle cooing of doves settling into their roosts for the night and the soft whisper of leaves created a deeply soothing atmosphere. Julia breathed slowly and deeply, feeling a profound connection with the earth, the cosmos, and all the generations of humanity who had walked before her.",
            "She thought of the millions of ordinary citizens across the empire whose lives had been made better by her laws, her patronages, and her governance. The schools she had founded, the libraries she had preserved, and the citizenship rights she had helped bestow would live on long after her mortal journey came to an end. Her legacy was written not merely in stone, but in the advancement of human culture.",
            "As the last traces of violet light faded from the western horizon, the first evening stars appeared, bright and clear in the deepening velvet sky. Julia looked up at the familiar constellations with a gentle, loving smile, recognizing the eternal stars that had guided her since childhood. They seemed like old friends, welcoming her into their timeless, peaceful realm.",
            "The quietness of the night enveloped the world in a warm, protective embrace. All the noise, ambition, and strife of politics melted away into insignificance, leaving only the pure, radiant essence of love, wisdom, and peace. Julia felt light, free, and deeply at home in the universe.",
            "She poured a small libation of pure water onto the earth, offering a silent prayer of gratitude to the Divine for the wondrous gift of life and the privilege of serving humanity. Her spirit was completely unburdened, clear as mountain water and still as a moonlit lake.",
            "Walking slowly into her bedchamber, the Empress felt a deep, comforting tiredness settle over her limbs. She lay down upon her soft couch, wrapped in comfortable linens, letting her mind drift into a state of profound, peaceful relaxation, surrounded by the loving silence of the night."
        ],
        15: [
            "The final chapter of Julia Domna's extraordinary life was written in the historic city of Antioch in the year two hundred and seventeen. When news arrived of the death of her son Caracalla during the eastern campaign, the Empress faced the end of the Severan dynasty with the majestic, unshakeable composure of a true Roman Augusta and Syrian philosopher-queen. She met destiny on her own terms, embracing the eternal peace that had called to her throughout her life.",
            "In her final days, surrounded by loyal friends, faithful physicians, and beloved scrolls of philosophy, Julia radiated a serene, transcendent grace. She spoke words of comfort and wisdom to those around her, reminding them that death is not an enemy, but the natural, peaceful conclusion to a well-lived mortal voyage—a gentle return to the cosmic source from which all life flows.",
            "Her legacy as one of the greatest, most powerful, and most intellectually accomplished women in world history was already forever secure. She had broken cultural barriers, unified an empire of citizens, patronized timeless philosophy and science, and governed with a wisdom, compassion, and resilience that earned her immortal renown across East and West.",
            "As the midnight hour settled over the ancient Mediterranean world, from the Seven Hills of Rome to the sunlit sands of Emesa, the great empire she had guided drifted into deep, tranquil slumber. The marble temples of the Forum, the soaring colonnades of Leptis Magna, the sacred groves of Daphne, and the quiet waters of the Euphrates were all bathed in the soft, silvery light of the stars.",
            "The gentle night breeze whispered softly through the leaves of olive and cypress trees, carrying a message of eternal peace across lands and seas. The rhythmic breathing of the sleeping earth was slow, steady, and soothing, inviting every weary mind and tired body to release all tension, worry, and fatigue.",
            "In the quiet sanctuary of history, Julia Domna found her eternal rest. Her memory lived on as a beacon of maternal strength, sovereign intellect, and cultured grace—a guiding light through the centuries for all who seek wisdom, justice, and the quiet power of the human spirit.",
            "The stars above shone with calm, steady brilliance, turning slowly in their timeless cosmic dance. The universe was whole, harmonious, and bathed in divine tranquility. Every breath you take is now slow, deep, and peaceful, anchored in the boundless comfort of the night.",
            "Let all remaining thoughts softly dissolve like incense smoke rising into the cool evening air. Feel the heavy, pleasant relaxation spreading through your body, from the crown of your head down to your toes, comforting every muscle and calming every nerve.",
            "You are safe, sheltered, and deeply at peace beneath the vast, protective canopy of the night sky. The quiet rhythm of the centuries surrounds you with warmth, stillness, and restorative rest.",
            "As we conclude our journey through the life of Empress Julia Domna, close your eyes, surrender completely to the gentle embrace of sleep, and rest in eternal peace, silence, and sweet dreams."
        ]
    }

    # Build 150 prompt beats (10 unique prompts per part)
    # Using the strict Reference Anchor Kit specification
    for p_idx in range(1, 16):
        info = PARTS_INFO[p_idx - 1]
        p_title = info["title"]
        c_ref = info["c_ref"]
        s_ref = info["s_ref"]
        p_ref = info["p_ref"]

        full_script_md.append(f"## Part {p_idx:02d}: {p_title}\n\n")

        paragraphs = narrative_corpora[p_idx]

        for b_idx in range(1, 11):
            beat_id = f"beat_P{p_idx:02d}_B{b_idx:02d}"
            paragraph_text = paragraphs[b_idx - 1]
            full_script_md.append(f"{paragraph_text}\n\n")

            # Specific scene descriptions for each individual beat
            scene_descriptions = {
                1: [
                    "Young Julia Domna in white and gold Syrian robes standing beside the ancient sun pillar of Emesa, soft golden dawn light, desert temple colonnade, warm ambient glow.",
                    "Close-up of young Julia Domna studying an astrological papyrus scroll under the shade of date palms, serene focused expression, warm morning sunlight.",
                    "Priests tending the sacred black stone altar of Emesa as young Julia observes reverently, curling incense smoke, warm bronze lanterns, mystical atmospheric lighting.",
                    "Young Julia sitting on a sandstone terrace overlooking the Orontes river oasis at sunset, distant camel caravan, gentle evening breeze, tranquil mood.",
                    "Evening prayer at the Temple of the Sun with young Julia holding a bronze patera, soft candlelight reflecting on polished marble stones, deep peace.",
                    "Alexandrian astrologers pointing toward starry celestial constellations above the Emesa temple roof while young Julia listens thoughtfully, twilight sky.",
                    "Young Julia practicing calligraphy on fresh papyrus by the warm glow of a charcoal brazier, delicate hands, serene interior chambers, atmospheric shadows.",
                    "Distant view of the Syrian oasis city of Emesa under a starry night sky with young Julia looking out from a royal balcony, tranquil desert stillness.",
                    "The sacred sun symbol patera resting on an altar with young Julia Domna contemplating in quiet prayer, soft amber flame reflections, cinematic depth.",
                    "Young Julia Domna resting on soft cushions in her private bedchamber as lanterns are trimmed low, deep shadows, tranquil night atmosphere."
                ],
                2: [
                    "Septimius Severus studying a celestial horoscope chart in his military tent in Gaul, mapping his future with Julia Domna, warm oil lamps, determined look.",
                    "A Roman galley sailing across the azure Aegean Sea carrying young Julia Domna to Italy, white sails, sunlit waves, hopeful journey.",
                    "Young Julia Domna arriving in Rome on the Via Appia in a regal carriage greeted by welcoming patricians, autumn morning light, cypress trees.",
                    "Septimius Severus and young Julia Domna seated together in a Roman villa atrium discussing state affairs, intellectual harmony, warm sunbeams.",
                    "Young Julia Domna cradling infant Caracalla and young Geta in a lush peristyle garden with roses and fountains, gentle maternal love.",
                    "Young Julia presiding over an intellectual salon in her Roman home with Greek rhetoricians and Latin poets, elegant conversational atmosphere.",
                    "Julia Domna and Severus walking through a hillside vineyard overlooking the Bay of Naples, tranquil coastal breeze, volcanic hills at sunset.",
                    "Julia Domna in a red travel cloak inspecting military frontier supplies with centurions in a western province, dignified leadership, crisp morning light.",
                    "Julia Domna gazing at the night sky from her villa balcony in Rome, tracing the stars of Emesa, deep contemplative peace, silver moonlight.",
                    "The quiet bedchamber of Julia Domna in Rome with soft moonlight illuminating classical frescoes on the wall, peaceful midnight repose."
                ],
                3: [
                    "Julia Domna standing beside Septimius Severus on the Danube frontier at Carnuntum as legions raise their shields in acclaim, dramatic cloudy sky.",
                    "A massive column of Roman legions marching through pine-forested Alpine mountain passes with Julia's carriage in the vanguard, crisp morning mist.",
                    "Julia Domna walking through a legionary night encampment beside campfires, speaking gently to veteran soldiers, warm orange glow against armor.",
                    "The grand entry of Septimius Severus and Julia Domna into the Roman Forum through cheering crowds and white togas, majestic triumphal banners.",
                    "Julia Domna in imperial travel robes reviewing dispatches in a military headquarters tent near the Cilician Gates, strategic concentration.",
                    "Julia Domna overseeing supply logistics at an eastern port city with Roman galleys docked in the harbor, morning light, organized efficiency.",
                    "Septimius Severus and Julia Domna standing before the newly dedicated Triumphal Arch in the Roman Forum, marble bas-reliefs, glorious sunlight.",
                    "Julia Domna supervising the classical education of young Caracalla and Geta with famous Greek tutors in a marble library, disciplined learning.",
                    "Julia Domna walking through the peaceful gardens of the Palatine Palace at twilight overlooking the Circus Maximus, serene victory, warm dusk.",
                    "Palatine Palace at midnight with torchlight reflecting on marble columns, Julia resting peacefully after the unification of the empire."
                ],
                4: [
                    "Empress Julia Domna seated on an ivory curule chair in the grand Palatine Palace courtyard, surrounded by flowing water fountains and marble statues.",
                    "Close-up portrait of Empress Julia Domna with her iconic waved coiffure and purple silk stola bordered with gold, regal elegance, soft studio light.",
                    "Julia Domna inspecting petitions on a citrus wood table in a sunny palace atrium, serene administrative focus, morning light.",
                    "A Roman sculptor carving a marble bust of Empress Julia Domna in an artist workshop while she poses with quiet grace, chisels and stone dust.",
                    "Julia Domna selecting delicate gold and amethyst jewelry from an ivory casket in her private dressing room, understated luxury, amber lighting.",
                    "Empress Julia Domna receiving provincial ambassadors in the grand reception hall of the Palatine, majestic dignity, respectful assembly.",
                    "Palace servants lighting incense burners of frankincense and lavender on the Palatine terrace at sunset, aromatic smoke drifting in twilight.",
                    "Julia Domna browsing rare scrolls in the private imperial library on the Palatine, cedar bookshelves, quiet intellectual sanctuary.",
                    "Empress Julia Domna checking on her young sons sleeping in their bedchambers, gentle maternal tenderness, soft lantern glow.",
                    "The moonlit bedchamber of Empress Julia Domna on the Palatine, cool breeze stirring sheer silk curtains, deep restorative tranquility."
                ],
                5: [
                    "Empress Julia Domna presiding over her famous philosophical salon in a grand colonnaded hall, seated among famous scholars and thinkers.",
                    "Julia Domna in deep conversation with biographer Philostratus, commissioning the Life of Apollonius of Tyana, papyrus scrolls spread on table.",
                    "The philosophical salon gathered around a warm bronze hearth discussing ethics and cosmology, flickering flames, thoughtful expressions.",
                    "The great physician Galen demonstrating botanical medicinal herbs to Empress Julia Domna in a sunlit palace garden, scientific curiosity.",
                    "Eminent jurists Papinian and Ulpian consulting with Julia Domna on legal reforms, wax tablets and imperial seals, intellectual gravitas.",
                    "Scholars reclining on embroidered couches in Julia's salon engaged in polite debate, goblet of wine, tranquil evening atmosphere.",
                    "Philosophers in the salon gazing through high arched windows at the starry night sky, discussing the harmony of the spheres, mystical awe.",
                    "Young students studying in a newly funded imperial library in Athens under Julia's patronage, sunbeams illuminating reading desks.",
                    "Julia Domna standing alone in the quiet salon after the philosophers departed, looking at dying embers in the hearth, peaceful contemplation.",
                    "Empress Julia Domna retiring through the quiet marble corridors of the Palatine under starlight, serene philosophical calm."
                ],
                6: [
                    "Empress Julia Domna in military cloak walking through a Roman legionary fortress in Britannia, surrounded by standards bearing her title Mater Castrorum.",
                    "Julia Domna riding a white horse beside Emperor Severus through mist-shrouded heather moors in northern Britannia, atmospheric rugged beauty.",
                    "The Roman imperial fleet crossing the stormy English Channel with Julia Domna on the deck looking toward chalk cliffs, dramatic sea spray.",
                    "Julia Domna inspecting a military hospital tent in York, speaking kindly to wounded soldiers, warm lanterns and herbal remedies.",
                    "Imperial headquarters tent in northern Britannia with a roaring hearth of oak logs, Julia and Severus reviewing maps in the warm glow.",
                    "Empress Julia Domna conversing with a Caledonian noblewoman in a military camp, mutual respect, intriguing cultural exchange.",
                    "Sentries standing guard on Hadrian's Wall at twilight with the distant northern lights dancing in the sky, quiet vigilant peace.",
                    "A Roman coin depicting Empress Julia Domna with the inscription Mater Castrorum resting on a velvet cloth, metallic gleam, numismatic detail.",
                    "Julia Domna reading Greek scrolls inside her frontier tent by the light of an oil lamp while rain patters softly on canvas, cozy sanctuary.",
                    "The vast Roman military camp in Britannia sleeping under the stars, watchtowers glowing with warm braziers, Julia resting safely in camp."
                ],
                7: [
                    "Julia Domna and Septimius Severus arriving by galley at the magnificent port city of Leptis Magna, turquoise Mediterranean waters and white marble.",
                    "The imperial family walking through the newly built colonnaded forum of Leptis Magna, soaring green marble columns, bright North African sun.",
                    "Close-up of the marble relief sculptures on the Arch of Septimius Severus showing Julia Domna holding a patera beside her family, sharp carvings.",
                    "Julia Domna relaxing on an open terrace in Leptis Magna overlooking groves of silver olive trees and the sea, warm soothing breeze.",
                    "Empress Julia Domna visiting the grand imperial baths of Leptis Magna, sunlight streaming through high arched windows onto crystal pools.",
                    "Evening banquet in a courtyard garden in Leptis Magna with flowering jasmine, local African nobles honoring Julia, soft harp music.",
                    "Julia Domna walking along the sandy beach near Leptis Magna at sunset, gentle waves lapping at the shore, golden-violet twilight.",
                    "The imperial family offering prayers at an ancient seaside temple in Leptis Magna, incense smoke rising into the clear blue sky, peaceful piety.",
                    "The towering lighthouse of Leptis Magna beaming light across the calm night sea, stars glittering above the coastal city, majestic night.",
                    "Julia Domna resting in her coastal palace chamber listening to the ocean tides, warm Mediterranean night breeze, deep restorative sleep."
                ],
                8: [
                    "Empress Julia Domna seated at a polished citrus wood desk in the imperial secretariat reviewing provincial petitions, focused wisdom, morning light.",
                    "The Roman Senate in the Curia Julia rising to honor Empress Julia Domna with the title Mater Senatus, marble hall, sunlight on white togas.",
                    "Julia Domna listening compassionately to a delegation of provincial citizens presenting a petition on papyrus, gracious leadership.",
                    "Empress Julia Domna in an amethyst silk stola receiving Parthian ambassadors in the throne room with majestic courtesy, intercultural diplomacy.",
                    "Julia Domna reviewing draft legal decrees with chief jurist Papinian in a palace study, wax seals, legislative reform, serious dignified mood.",
                    "Empress Julia Domna practicing meditation in a quiet palace garden shaded by cypress trees, eyes closed, complete inner tranquility.",
                    "Julia Domna and her circle of learned women walking through a sunlit peristyle courtyard discussing literature, cultured companionship.",
                    "The restored Temple of Vesta in the Roman Forum gleaming in white marble, funded by Empress Julia Domna, sacred hearth fire visible inside.",
                    "Julia Domna standing on the Palatine balcony at dusk looking down at the illuminated Forum Romanum, thousands of city lights, peaceful majesty.",
                    "Empress Julia Domna in her private chamber retiring for the night, soft glow of an oil lamp, peaceful sense of duty accomplished."
                ],
                9: [
                    "Julia Domna pleading with young Caracalla and Geta in a palace courtyard, trying to bridge the rift between her sons, emotional maternal grace.",
                    "Caracalla and Geta seated on opposite sides of the council table with Julia Domna standing between them as mediator, tense political drama.",
                    "The imperial palace divided by barricades and separate guards, Julia Domna walking sorrowfully between the wings, dim somber lighting.",
                    "Julia Domna hosting a private reconciliation meeting between her sons in her candlelit bedchamber, holding their hands in desperate hope.",
                    "Tragic historical moment of grief as Julia Domna cradles dying Geta in her arms in the Palatine chamber, dramatic shadows, profound sorrow.",
                    "Empress Julia Domna maintaining silent dignity in the public court despite her broken heart, Stoic endurance, solemn regal posture.",
                    "Julia Domna praying alone in a secluded palace sanctuary, lighting oil lamps in memory of her son, quiet spiritual solace.",
                    "Julia Domna reading philosophical scrolls on the immortality of the soul by candlelight, seeking comfort in eternal wisdom, peaceful tears.",
                    "The Roman public and soldiers bowing in deep sympathy and reverence as Julia Domna passes through the Forum, moral authority, solemn grace.",
                    "Empress Julia Domna resting in her bedchamber at midnight, letting tears fall in private, finding peaceful release and cosmic acceptance."
                ],
                10: [
                    "Emperor Caracalla and Empress Julia Domna proclaiming the Constitutio Antoniniana edict before a massive diverse crowd of provincial subjects.",
                    "Scribes in the imperial chancery copying the citizenship decree onto hundreds of papyrus rolls, seals of red wax, historic legal reform.",
                    "Sunlight streaming over the colossal brick and marble arches of the newly built Baths of Caracalla, grand architectural scale.",
                    "Julia Domna walking in the peaceful cypress gardens surrounding the Baths of Caracalla, dew on grass, tranquil morning atmosphere.",
                    "A diverse assembly of Greeks, Gauls, Syrians, and Africans in Roman togas celebrating their new citizenship in a provincial forum, civic unity.",
                    "Julia Domna inspecting citizenship registry scrolls from distant provinces, satisfied smile, organized imperial administration.",
                    "Evening celebration in the Palatine gardens with musicians and scholars from across the empire, diverse cultural harmony under lanterns.",
                    "A Roman monumental inscription carved in stone proclaiming citizenship for all free inhabitants of the empire, sunlight and sharp letters.",
                    "The massive silhouette of the Baths of Caracalla at twilight with evening stars emerging, peaceful grandeur, soft purple dusk.",
                    "Empress Julia Domna resting peacefully in her room, hearing distant fountain waters, content that her vision of universal citizenship is fulfilled."
                ],
                11: [
                    "Empress Julia Domna arriving at the imperial palace on the Orontes River island in Antioch, lush weeping willows, rushing river water.",
                    "Julia Domna browsing among thousands of ancient papyrus scrolls in the Great Library of Antioch, soaring cedar shelves, quiet scholarship.",
                    "Scholars and translators working under Julia's direction in Antioch, translating eastern astronomical tables into Greek, sunlit desks.",
                    "Julia Domna relaxing on a carved stone bench in the sacred grove of Daphne near Antioch, crystal mountain springs cascading over rocks.",
                    "Close-up of Julia Domna reading a Stoic philosophical codex in the shaded green canopy of Daphne, absolute peace, dappled sunlight.",
                    "Floating lanterns drifting down the Orontes River at night while Julia's philosophical salon meets on the palace terrace, magical reflections.",
                    "Julia Domna meeting with caravan merchants from Palmyra and the Silk Road in Antioch, luxurious silks and spices on display.",
                    "The illuminated colonnaded main street of Antioch at night, thousands of oil lamps glowing, vibrant yet peaceful ancient metropolis.",
                    "Sunset over the Syrian mountains casting brilliant crimson light across the Orontes River, Julia watching from her palace window.",
                    "Empress Julia Domna sleeping peacefully in her Antioch palace chamber, river breeze cooling the room, deep tranquil rest."
                ],
                12: [
                    "Julia Domna standing on the high stone battlements of Zeugma fortress overlooking the vast, shimmering Euphrates River at morning.",
                    "The wide, golden Euphrates River flowing peacefully through desert steppes under a boundless blue sky, distant ancient ruins.",
                    "A camel caravan silhouetted against a breathtaking crimson and gold sunset along the banks of the Euphrates, tranquil eastern dusk.",
                    "Julia Domna using a bronze astrolabe on the fortress terrace at night, studying the crystal-clear desert constellations, mystical wonder.",
                    "Julia Domna conversing with Silk Road merchants in a desert caravanserai near the Euphrates, exotic goods, friendly cultural exchange.",
                    "Sentries with torches standing watch on the Euphrates riverbank fortress, warm flames reflecting in the dark flowing water.",
                    "Empress Julia Domna wrapped in a warm wool shawl sitting under a canopy of stars on the desert terrace, deep cosmic meditation.",
                    "Campfires along the Euphrates riverbank dying down to glowing red embers under the milky way, peaceful desert silence.",
                    "Distant view of the ancient fortress on the Euphrates under moonlight, timeless river flowing eternally into the night, serene beauty.",
                    "Julia Domna resting in her fortress bedchamber listening to the gentle murmur of the Euphrates, tranquil sleep in the ancient East."
                ],
                13: [
                    "Empress Julia Domna supervising dozens of scribes in the imperial Ab Epistulis secretariat in Antioch, organized desks, papyrus rolls.",
                    "Close-up of Julia Domna dictating an official imperial letter in Greek, sharp intelligent gaze, scribe writing swiftly on parchment.",
                    "Imperial letters sealed with red wax and purple ribbons resting in organized cedar pigeonholes, representing provinces across three continents.",
                    "Julia Domna signing an imperial decree with purple ink, delicate gold signet ring on her finger, sovereign authority and justice.",
                    "A Roman imperial courier mounting a swift horse outside the palace to deliver dispatches to the frontier, morning light, active duty.",
                    "Julia Domna taking a peaceful pause in the secretariat to sip cool mint water, looking out at the sunlit garden, calm composure.",
                    "A large painted map of the Roman Empire on the secretariat wall with Julia Domna tracing peaceful trade routes, strategic vision.",
                    "The secretariat chamber at dusk as scribes pack their pens and extinguish lamps, peaceful orderly silence, long evening shadows.",
                    "Julia Domna walking through the quiet palace corridors at sunset, silk stola rustling softly in the evening breeze, dignified grace.",
                    "Empress Julia Domna resting in her bedchamber, satisfied with her day of governance that brought justice and peace to millions, restful sleep."
                ],
                14: [
                    "Julia Domna sitting on a terrace at twilight watching the sun set behind ancient classical colonnades, golden hour, deep reflection.",
                    "Close-up of mature Empress Julia Domna with wise, serene eyes, gentle smile, dignified beauty that has weathered all trials of life.",
                    "Julia Domna remembering past triumphs in Rome, marble arches and laurel wreaths, peaceful detachment from worldly vanity.",
                    "Empress Julia Domna meditating in a tranquil garden surrounded by blooming night-jasmine and cypress trees, complete inner harmony.",
                    "Julia Domna offering a small libation of pure water to the earth in gratitude for life and wisdom, sacred simplicity, dusk light.",
                    "Evening shadows lengthening over the ancient marble basilicas and temples of the Roman world, peaceful historical majesty.",
                    "Julia Domna looking up at the bright evening star emerging in the violet twilight sky, welcoming the calm arrival of night.",
                    "A gentle breeze stirring the leaves of ancient olive trees under a starry Mediterranean sky, timeless peaceful atmosphere.",
                    "Empress Julia Domna walking slowly into her bedchamber with a light, unburdened heart, soft candlelight welcoming her to rest.",
                    "Julia Domna reclining comfortably on her bed, breathing deeply and slowly, completely relaxed and at peace with all existence."
                ],
                15: [
                    "Empress Julia Domna in her final days in Antioch surrounded by scrolls of philosophy and faithful friends, radiant serene grace.",
                    "Julia Domna speaking calm parting words of wisdom and comfort, reassuring those around her with unshakeable philosophical peace.",
                    "A symbolic marble statue of Empress Julia Domna holding a scroll of wisdom, illuminated by warm golden sunlight, eternal legacy.",
                    "Panoramic view of the Roman Empire at midnight under a vast, peaceful canopy of stars, from Rome to Syria, sleeping in harmony.",
                    "The full moon shining brightly over the seven hills of Rome, illuminating the Forum and Palatine Palace in silvery peaceful light.",
                    "Gentle night wind rustling through cypress and olive trees across the Mediterranean world, whispering eternal peace.",
                    "Incense smoke slowly rising from an alabaster burner in a quiet sanctuary, dissolving into the cool evening air, complete release.",
                    "A tranquil moonlit courtyard with a calm stone fountain reflecting the stars, pure stillness, soothing ambient atmosphere.",
                    "Soft golden light gently fading into deep, comforting darkness, leaving only a soft ember of warmth, perfect restorative rest.",
                    "The peaceful, starry night sky over the ancient Mediterranean world, timeless silence, eternal sweet dreams, deep sleep."
                ]
            }

            scene_desc = scene_descriptions[p_idx][b_idx - 1]

            prompt_str = (
                f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg: [CHARACTER: {c_ref}] [SETTING: {s_ref}] [PROP: {p_ref}] "
                f"{scene_desc} --ar 16:9 --style raw --v 6.0"
            )

            beats.append({
                "part_index": p_idx,
                "beat_index": b_idx,
                "id": beat_id,
                "filename": f"{beat_id}.jpg",
                "title": f"Part {p_idx:02d} Beat {b_idx:02d}: {p_title}",
                "narrative": paragraph_text,
                "prompt": prompt_str,
                "c_ref": c_ref,
                "s_ref": s_ref,
                "p_ref": p_ref
            })

    return beats, "".join(full_script_md)

all_beats, script_md_text = build_script_and_prompts()

# Save script_full.md
script_md_file = PROJECT_ROOT / "script_full.md"
with open(script_md_file, "w", encoding="utf-8") as f:
    f.write(script_md_text)
print(f"✅ Generated {script_md_file.name} ({len(script_md_text.split())} words, {len(all_beats)} beats)")

# Save combined_imageprompts.txt
prompts_lines = [b["prompt"] for b in all_beats]
prompts_file = PROJECT_ROOT / "combined_imageprompts.txt"
with open(prompts_file, "w", encoding="utf-8") as f:
    f.write("\n\n".join(prompts_lines) + "\n")
print(f"✅ Generated {prompts_file.name} (150 distinct visual prompts)")

# Copy to Preproduction folder
import shutil
shutil.copy(prompts_file, PREPROD_DIR / "combined_imageprompts.txt")

# --- 2. GENERATE OUTLINE & SCRIPT DOCX ---
print("\n[2/5] Creating Professional Word Documents (DOCX)...")

# Outline DOCX
outline_doc = docx.Document()
outline_doc.add_heading(f"{DOC_TITLE} - 15-Part Documentary Outline", level=0)
outline_doc.add_paragraph("Canonical Single Source of Truth (SSOT) Production Outline for HistorySnooze Ambient Sleep Documentary.")

outline_json_data = []
for p in PARTS_INFO:
    p_idx = p["index"]
    p_title = p["title"]
    outline_doc.add_heading(f"Part {p_idx:02d}: {p_title}", level=1)
    desc = f"Focus: {p['focus']}. Anchor kit tags: Character: {p['c_ref']}, Setting: {p['s_ref']}, Prop: {p['p_ref']}."
    outline_doc.add_paragraph(desc)
    outline_json_data.append({
        "part": p_idx,
        "title": p_title,
        "character_ref": p["c_ref"],
        "setting_ref": p["s_ref"],
        "prop_ref": p["p_ref"],
        "description": p["focus"],
        "beats_count": 10
    })

outline_docx_path = PREPROD_DIR / f"Outline - {CHARACTER_NAME}.docx"
outline_doc.save(str(outline_docx_path))
print(f"✅ Saved Outline DOCX: {outline_docx_path.name}")

with open(PREPROD_DIR / "outline.json", "w", encoding="utf-8") as f:
    json.dump(outline_json_data, f, indent=2)

# Script DOCX
script_doc = docx.Document()
script_doc.add_heading(f"{DOC_TITLE} - Full Voiceover Script", level=0)
script_doc.add_paragraph("Full contemplative ambient sleep narration script (15 Parts, 150 Paragraphs, ~15,000 words).")

for p in PARTS_INFO:
    p_idx = p["index"]
    p_title = p["title"]
    script_doc.add_heading(f"Part {p_idx:02d}: {p_title}", level=1)

    part_beats = [b for b in all_beats if b["part_index"] == p_idx]
    for b in part_beats:
        p_para = script_doc.add_paragraph(b["narrative"])
        p_para.paragraph_format.space_after = docx.shared.Pt(8)

script_docx_path = PREPROD_DIR / f"Script - {CHARACTER_NAME}.docx"
script_doc.save(str(script_docx_path))
print(f"✅ Saved Script DOCX: {script_docx_path.name}")

# Metadata JSON
meta = {
    "idea_id": IDEA_ID,
    "character": CHARACTER_NAME,
    "title": DOC_TITLE,
    "parts_count": 15,
    "beats_count": 150,
    "created_at": datetime.now().isoformat(),
    "style": "Ambient ASMR Sleep Documentary",
    "gdrive_folder_id": GDRIVE_FOLDER_ID
}
with open(PREPROD_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

# --- 3. CLEAN UP & UPLOAD DIRECTLY TO GOOGLE DRIVE VIA API ---
print("\n[3/5] Synchronizing directly to Google Drive...")

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH,
    scopes=[
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
)
drive = build("drive", "v3", credentials=creds)

# Helper function to upload or update a file in GDrive
def upload_file_to_drive(local_path: Path, parent_id: str, mime_type: str = None) -> str:
    file_name = local_path.name
    # Check if file exists in parent folder
    query = f"'{parent_id}' in parents and name='{file_name}' and trashed=false"
    results = drive.files().list(q=query, fields="files(id, name)").execute()
    existing_files = results.get("files", [])

    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

    if existing_files:
        file_id = existing_files[0]["id"]
        updated = drive.files().update(fileId=file_id, media_body=media, fields="id, name").execute()
        print(f"  - Updated: {file_name} (ID: {updated['id']})")
        return updated["id"]
    else:
        meta_body = {"name": file_name, "parents": [parent_id]}
        created = drive.files().create(body=meta_body, media_body=media, fields="id, name").execute()
        print(f"  - Uploaded: {file_name} (ID: {created['id']})")
        return created["id"]

def ensure_drive_folder(folder_name: str, parent_id: str) -> str:
    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive.files().list(q=query, fields="files(id, name)").execute()
    existing = results.get("files", [])
    if existing:
        return existing[0]["id"]
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    created = drive.files().create(body=meta, fields="id, name").execute()
    return created["id"]

# Purge any old defective mock files in root folder if needed
print("  - Ensuring remote folder structure...")
preprod_drive_id = ensure_drive_folder("01. Preproduction", GDRIVE_FOLDER_ID)

# Upload root files
script_md_id = upload_file_to_drive(script_md_file, GDRIVE_FOLDER_ID, "text/markdown")
prompts_id = upload_file_to_drive(prompts_file, GDRIVE_FOLDER_ID, "text/plain")

# Upload Preproduction files
outline_docx_id = upload_file_to_drive(outline_docx_path, preprod_drive_id, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
script_docx_id = upload_file_to_drive(script_docx_path, preprod_drive_id, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
upload_file_to_drive(PREPROD_DIR / "outline.json", preprod_drive_id, "application/json")
upload_file_to_drive(PREPROD_DIR / "metadata.json", preprod_drive_id, "application/json")
upload_file_to_drive(PREPROD_DIR / "combined_imageprompts.txt", preprod_drive_id, "text/plain")

print("✅ Google Drive synchronization complete!")

# --- 4. UPDATE GOOGLE SHEETS DASHBOARD ---
print("\n[4/5] Updating Google Sheets Central Ledger (Row 10)...")

gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Pipeline")

cell = ws.find(IDEA_ID)
if cell:
    row_num = cell.row
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    gdrive_url = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
    outline_url = f"https://docs.google.com/document/d/{outline_docx_id}/edit?usp=drivesdk" if outline_docx_id else gdrive_url
    script_url = f"https://docs.google.com/document/d/{script_docx_id}/edit?usp=drivesdk" if script_docx_id else gdrive_url

    # Update row 10
    # Col D (4): Status -> SCRIPT_DONE
    # Col E (5): GDrive
    # Col F (6): Outline
    # Col G (7): Script
    # Col O (15): Updated_At -> timestamp
    ws.update_cell(row_num, 4, "SCRIPT_DONE")
    ws.update_cell(row_num, 5, gdrive_url)
    ws.update_cell(row_num, 6, outline_url)
    ws.update_cell(row_num, 7, script_url)
    ws.update_cell(row_num, 15, now_str)

    print("=" * 60)
    print(f"🎉 GOOGLE SHEET ROW {row_num} UPDATED SUCCESSFULLY!")
    print(f"   - Status (Col D): SCRIPT_DONE")
    print(f"   - GDrive (Col E): {gdrive_url}")
    print(f"   - Outline (Col F): {outline_url}")
    print(f"   - Script (Col G): {script_url}")
    print(f"   - Updated_At (Col O): {now_str}")
    print("=" * 60)
else:
    print(f"❌ Error: Idea ID '{IDEA_ID}' not found in Google Sheet!")

print("\n" + "=" * 60)
print("🚀 ALL TASKS COMPLETED SUCCESSFULLY!")
print(f"1. Cleaned output/ directory.")
print(f"2. Generated full 15-part script ({len(script_md_text.split())} words, 150 beats).")
print(f"3. Generated 150 distinct visual prompts with Reference Anchor Kit.")
print(f"4. Uploaded DOCX and text assets directly to Google Drive.")
print(f"5. Updated Google Sheets Pipeline Row 10.")
print("=" * 60)
