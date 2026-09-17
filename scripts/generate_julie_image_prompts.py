"""
HistorySnooze: Master Image Prompts Generator for Julie d'Aubigny
SSOT-compliant with Documents/Structure/04_VISUAL_PROMPT_ENGINE.md
Generates exactly 150 visual beats (10 beats/part across 15 parts)
using the 3-Tier Visual Formula.
"""

import os
from pathlib import Path
from typing import List, Dict

FORBIDDEN_WORDS = [
    "photorealistic", "3d render", "cgi", "octane render",
    "cyberpunk", "modern", "anime", "border", "frame",
    "parchment edge", "margin", ".gif", "--ar", "--v 6", "--style"
]

MASTER_STYLE_TAIL = (
    "cinematic historical film still, shot on 35mm anamorphic lens, "
    "authentic seventeenth-century French Baroque lighting, warm chiaroscuro candlelit shadows, "
    "rich painterly textures, subtle film grain, muted earthy and jewel-tone palette, "
    "wide 16:9 composition, full bleed edge-to-edge canvas, 4K UHD"
)

def build_julie_daubigny_prompts() -> List[Dict[str, str]]:
    prompts = []

    # =========================================================================
    # PART 01: The Grand Stables of Versailles - The Riding Master's Daughter
    # =========================================================================
    p1_beats = [
        # B01
        "Young Julie d'Aubigny as a bold twelve-year-old maiden walking through the dawn mist across the cobblestones of the Grand Stables of Versailles, morning fog rising softly around limestone arches, soft golden autumn light breaking over slate palace roofs",
        # B02
        "Gaston d'Aubigny the equerry standing tall beside his young daughter Julie in the stable courtyard, instructing her on equestrian posture beside a magnificent white Iberian thoroughbred horse, cedar wood shavings on the stone floor",
        # B03
        "Young Julie d'Aubigny riding a spirited dark stallion with effortless upright posture across the raked sand arena of the royal stables, early morning sunlight streaming through high arched windows in long diagonal beams",
        # B04
        "Interior of the Versailles harness room with rows of polished brass buckles and honey-toned leather saddles, young Julie carefully rubbing beeswax oil into a supple bridle under warm lantern glow",
        # B05
        "Young Julie d'Aubigny in simple uncorseted linen shirt and woolen doublet holding a wooden practice foil, mirroring the precise fencing stance of a palace arms master inside a vaulted stone training hall",
        # B06
        "High vantage view from the upper limestone gallery of the Grand Stables, young Julie looking out peacefully over the vast gardens and misty fountains of Versailles bathed in late afternoon amber light",
        # B07
        "Candlelit domestic study above the stables, Gaston d'Aubigny tutoring young Julie with open leatherbound books of classical literature and Italian poetry, quill and inkwell resting on polished walnut table",
        # B08
        "Young Julie d'Aubigny standing near an open stone archway listening attentively to the distant chapel choir, her expressive face softly illuminated as she hums harmonies in her rich natural contralto voice",
        # B09
        "Quiet evening stable corridor with glowing iron lanterns casting warm amber light on oak stalls, young Julie gently stroking the muzzle of a resting chestnut mare settling into fresh clover hay",
        # B10
        "Night falling over the Grand Stables of Versailles, silent riding rings beneath a velvet starlit sky, young Julie resting peacefully in her quiet chamber by the soft glow of a dying hearth"
    ]
    p1_anchor = "seventeenth-century Versailles classical French limestone architecture, royal stables and equestrian grounds, authentic period woolen clothing and leather tack"

    for b_idx, beat in enumerate(p1_beats, 1):
        prompts.append({
            "part": 1,
            "beat": b_idx,
            "filename": f"beat_P01_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p1_anchor,
            "full_prompt": f"{beat}, {p1_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 02: The Art of the Blade - A Maiden in Men's Doublet
    # =========================================================================
    p2_beats = [
        # B01
        "Young Julie d'Aubigny stepping into a prestigious Parisian Salle d'Armes, dressed in tailored male woolen doublet, breeches, and soft leather riding boots, holding a slender French practice foil with calm poise",
        # B02
        "Fencing master in dark velvet coat observing young Julie execute a swift and balanced lunge on the wooden piste, mirrored walls reflecting candlelight and chalk footwork lines on the polished oak floor",
        # B03
        "Close composition of young Julie d'Aubigny parrying a master's thrust with micro-second precision, steel blades crossing with subtle sparks in the warm ambient light of the fencing academy",
        # B04
        "Master swordsmen in seventeenth-century Parisian attire gathered along the hall benches, watching with quiet respect as Julie effortlessly disengages her foil and touches her opponent's jacket",
        # B05
        "Julie in discussion with Count d'Armagnac inside an elegant Parisian library, ornate gilded moldings, velvet drapery, and parchment letters spread across a carved desk",
        # B06
        "Artisan bladesmith's forge on the Pont Neuf, orange glowing embers and flying sparks, master armorer balancing a finely balanced Toledo steel rapier blade on his fingertip before Julie",
        # B07
        "Julie practicing rapid blade drills alone at dawn in the misty park of Saint-Germain, breath misting in the cool morning air, graceful athletic motion among ancient oak trees",
        # B08
        "Candlelit chamber overlooking the Seine at twilight, Julie seated at a polished wooden harpsichord practicing vocal scales, her rapier resting in its scabbard across a nearby armchair",
        # B09
        "Julie surrounded by admiring young Parisian aristocrats and fencing students in a quiet salon, smiling with modest wit and quiet confidence while leaning gently on a wooden chair",
        # B10
        "Midnight silence in Julie's Parisian chamber, moonbeams illuminating a clean oiled steel rapier resting on a linen cloth, peaceful tranquil atmosphere of deep rest and contemplation"
    ]
    p2_anchor = "late seventeenth-century Paris, French fencing academies, authentic Salle d'Armes interior, classical Louis XIV Parisian architecture and period gentleman's costume"

    for b_idx, beat in enumerate(p2_beats, 1):
        prompts.append({
            "part": 2,
            "beat": b_idx,
            "filename": f"beat_P02_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p2_anchor,
            "full_prompt": f"{beat}, {p2_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 03: The Flight with Sérannes - Highwaymen and the Road South
    # =========================================================================
    p3_beats = [
        # B01
        "Julie d'Aubigny in cavalier riding cloak and broad tricorn hat mounting her horse at midnight outside a Parisian coaching gate, departing beside the master duelist Sérannes",
        # B02
        "Julie and Sérannes riding side by side along a moonlit southern French post road, shadows of tall poplars stretching across the packed dirt path under a vast star-filled sky",
        # B03
        "Panoramic view of the French countryside at sunrise, rolling lavender hills and distant limestone hills of Provence, horses trotting steadily on the open highway",
        # B04
        "Cozy rustic coaching inn at dusk, roaring stone fireplace casting warm orange light on timber beams, Julie in men's traveling doublet resting with a pewter mug of warm cider",
        # B05
        "Julie d'Aubigny and Sérannes preparing a small campfire beneath ancient spreading oak trees, gentle smoke rising into the tranquil twilight air, saddlebags resting on mossy ground",
        # B06
        "Confrontation with shadowy highwaymen along a narrow wooded mountain road, Julie drawing her gleaming rapier with calm fearless determination in the twilight gloom",
        # B07
        "Julie expertly disarming an armed bandit leader with a lightning-fast circular parry, sending his weapon flying into the leaves without shedding blood, calm heroic poise",
        # B08
        "Julie and Sérannes arriving at a sun-drenched hilltop overlooking a Provencal village with terracotta tiled roofs and cypress trees, horses resting by a stone fountain",
        # B09
        "Evening dinner in a warm provincial tavern, Julie entertaining the local innkeeper and travelers with captivating stories and charismatic laughter by the hearth fire",
        # B10
        "Night sky over the Provencal countryside, quiet coaching inn courtyard with resting horses and lanterns, Julie gazing up at the serene canopy of brilliant southern stars"
    ]
    p3_anchor = "seventeenth-century southern France, scenic rural post roads, ancient Provencal coaching inns, authentic French cavalier traveling cloaks and leather tack"

    for b_idx, beat in enumerate(p3_beats, 1):
        prompts.append({
            "part": 3,
            "beat": b_idx,
            "filename": f"beat_P03_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p3_anchor,
            "full_prompt": f"{beat}, {p3_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 04: Duelists on the Traveling Stage - Defeating Men Across the Provinces
    # =========================================================================
    p4_beats = [
        # B01
        "Crowded marketplace square in Poitiers, colorful canvas awnings and half-timbered houses, Julie d'Aubigny standing atop a raised wooden fencing stage in men's fencing breeches",
        # B02
        "Julie d'Aubigny challenging a boastful local fencing master, holding her rapier with elegant poise as the provincial crowd watches in suspense under bright afternoon sun",
        # B03
        "Dynamic fencing duel on the open-air wooden stage, Julie executing a flawless low-line thrust, touching her challenger's waistcoat with pinpoint precision",
        # B04
        "Provincial crowd cheering with delight, throwing silver coins onto the stage, Julie bowing with courtly elegance and removing her wide-brimmed feathered cavalier hat",
        # B05
        "A skeptical town gentleman questioning Julie's identity, Julie boldly opening the top buttons of her linen shirt with a radiant defiant smile to prove her womanhood to the stunned crowd",
        # B06
        "Quiet afternoon backstage behind the traveling theater tent, Julie counting coins into a leather pouch with Sérannes while resting on a wooden trunk",
        # B07
        "Julie demonstrating complex rapier and main-gauche dual-blade techniques to eager young provincial swordsmen in a shaded cobblestone tavern courtyard",
        # B08
        "Sunset over a vineyard near Bordeaux, Julie walking peacefully through rows of ripening grapes, listening to the gentle evening breeze rustling the vine leaves",
        # B09
        "Lively candlelit tavern gathering, Julie singing a soulful French ballad in her deep contralto voice, patrons listening in mesmerized silence around rustic oak tables",
        # B10
        "Peaceful night over the provincial market town, empty wooden stage resting beneath the moonlit sky, lanterns flickering out in the surrounding stone houses"
    ]
    p4_anchor = "seventeenth-century French provincial towns, Bordeaux and Poitiers marketplaces, authentic Renaissance half-timbered architecture, period crowd attire"

    for b_idx, beat in enumerate(p4_beats, 1):
        prompts.append({
            "part": 4,
            "beat": b_idx,
            "filename": f"beat_P04_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p4_anchor,
            "full_prompt": f"{beat}, {p4_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 05: The Songbird of Marseille - Triumph in the Southern Sun
    # =========================================================================
    p5_beats = [
        # B01
        "Sunlight gleaming over the vibrant Old Port of Marseille, sailing merchant frigates anchored in turquoise water, Julie d'Aubigny arriving at the bustling limestone quayside",
        # B02
        "Julie entering Pierre Gaultier's newly founded Marseille Opera Academy, grand vaulted hall filled with harpsichords, music stands, and singing students",
        # B03
        "Pierre Gaultier the composer listening with wide-eyed astonishment as Julie sings an operatic aria, her resonant contralto voice filling the vaulted acoustic chamber",
        # B04
        "Julie rehearsing her debut role on the stage of the Marseille Opera, dressed in elegant silk theatrical gown, sheet music folios resting on the orchestra rail",
        # B05
        "Opening night at Marseille Opera, Julie performing center stage beneath glowing oil chandeliers, audience in balconies applauding with passionate enthusiasm",
        # B06
        "Julie standing on a scenic stone terrace overlooking the Mediterranean at sunset, sea breeze gently lifting her dark curls as she studies an illuminated music score",
        # B07
        "Meeting a beautiful young noblewoman in an elegant Marseille garden courtyard filled with blooming orange blossoms and stone fountains under golden afternoon light",
        # B08
        "Late night celebration with opera musicians and artists in a candlelit seaside tavern, wine glasses raised in toast, violins and lutes resting on chairs",
        # B09
        "Julie walking along the quiet stone pier of Marseille at dawn, gentle waves lapping against the hull of wooden ships, pink and amber light across the horizon",
        # B10
        "Starlit night over Marseille harbor, glowing lanterns on ship masts reflecting in the calm dark water, peaceful lull of the Mediterranean sea"
    ]
    p5_anchor = "seventeenth-century Marseille and Mediterranean French coast, classical Baroque opera academy, authentic harbor architecture and period theater costumes"

    for b_idx, beat in enumerate(p5_beats, 1):
        prompts.append({
            "part": 5,
            "beat": b_idx,
            "filename": f"beat_P05_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p5_anchor,
            "full_prompt": f"{beat}, {p5_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 06: The Cloister of Avignon - The Midnight Fire and the Daring Escape
    # =========================================================================
    p6_beats = [
        # B01
        "Ancient stone walls of the Visitandine convent in Avignon towering beneath a twilight sky, massive arched oak doors and gothic windows surrounded by quiet cypress trees",
        # B02
        "Julie d'Aubigny entering the convent disguised as a humble postulant in simple dark woolen novice robes, lowering her gaze with quiet theatrical discipline",
        # B03
        "Peaceful cloistered convent garden at sunset, stone arcade walkways and blooming white rose bushes, Julie walking quietly alongside her cloistered young lover",
        # B04
        "Candlelit convent chapel during evening vespers, nuns kneeling in prayer, soft flickering taper candles illuminating stone statues and incense smoke",
        # B05
        "Julie secretly preparing the midnight escape, placing a recently deceased nun's body respectfully upon the bed in the stone cell to create an illusion",
        # B06
        "Controlled candle flame catching the straw mattress in the stone cell, dramatic amber firelight illuminating the ancient limestone walls without harming the building",
        # B07
        "Julie and her lover escaping through a side cloister arched doorway into the cool moonlit garden, silhouettes moving swiftly beneath the vaulted stone colonnade",
        # B08
        "Julie in cavalier attire helping her companion mount a waiting horse outside the convent stone walls in the quiet pre-dawn mist",
        # B09
        "Two riders galloping across the open plains of Provence as the golden sun rises over lavender fields, wind billowing through Julie's dark hair",
        # B10
        "Peaceful morning campsite by a clear mountain stream in the foothills of Provence, gentle morning sunlight filtering through pine branches as the lovers rest safely"
    ]
    p6_anchor = "seventeenth-century Avignon, gothic and Romanesque convent cloister architecture, stone vaulted chapels, authentic religious habit and cavalier riding gear"

    for b_idx, beat in enumerate(p6_beats, 1):
        prompts.append({
            "part": 6,
            "beat": b_idx,
            "filename": f"beat_P06_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p6_anchor,
            "full_prompt": f"{beat}, {p6_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 07: The Road to Paris and the Duel of Count d'Albert
    # =========================================================================
    p7_beats = [
        # B01
        "Crowded coaching inn near Villeperdue on the northern road, travelers gathered around the central hearth, young Count d'Albert seated with fellow aristocratic officers",
        # B02
        "Tavern confrontation when Count d'Albert insults Julie believing her to be a delicate youth, Julie rising calmly with an icy aristocratic glare",
        # B03
        "Stepping outside into the moonlit meadow behind the inn, Julie and Count d'Albert drawing their polished steel rapiers under the silver glow of the moon",
        # B04
        "Intense midnight duel, rapier blades clashing in the silver moonlight, Julie executing a masterclass in French smallsword footwork and timing",
        # B05
        "Decisive stroke where Julie's blade pierces d'Albert's shoulder, disarming him instantly while leaving him otherwise unharmed, d'Albert yielding with astonishment",
        # B06
        "Julie gently bandaging Count d'Albert's shoulder by the inn's fireplace, revealing her true identity, d'Albert looking at her with profound admiration and chivalric devotion",
        # B07
        "Morning light over the inn courtyard, Julie and Count d'Albert sharing a warm farewell handshake as lifelong friends and comrades-in-arms",
        # B08
        "Julie riding alone through the lush green forests of the Loire Valley, sunlight filtering through ancient beech and oak canopies",
        # B09
        "Stopping at a serene riverbank along the Loire, Julie watering her horse and gazing toward the distant towers of a French chateau",
        # B10
        "Twilight on the outskirts of Paris, city gates and Notre-Dame cathedral silhouette visible on the horizon beneath a peaceful evening sky"
    ]
    p7_anchor = "seventeenth-century Loire Valley and French coaching inns, moonlit dueling clearings, authentic French noble rapier design and cavalier attire"

    for b_idx, beat in enumerate(p7_beats, 1):
        prompts.append({
            "part": 7,
            "beat": b_idx,
            "filename": f"beat_P07_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p7_anchor,
            "full_prompt": f"{beat}, {p7_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 08: The Golden Gates of the Palais-Royal - Debut as Pallas Athena
    # =========================================================================
    p8_beats = [
        # B01
        "Versailles royal antechamber, Count d'Armagnac presenting a formal petition for royal pardon to King Louis XIV seated on his gilded armchair",
        # B02
        "Royal pardon scroll bearing the golden wax seal of the Sun King, resting on an ornate velvet desk beside an inkstand and quill",
        # B03
        "Audition room at the Paris Opera, composer and directors listening spellbound as Julie sings a demanding passage from Lully's Cadmus et Hermione",
        # B04
        "Backstage wardrobe at the Palais-Royal opera house, dressmakers adjusting Julie's magnificent stage costume as Pallas Athena with bronze cuirass and blue silk",
        # B05
        "Sensational stage debut of Julie as Pallas Athena, descending onto the stage holding a gleaming spear, oil footlights illuminating her heroic beauty",
        # B06
        "Wide shot of the packed Palais-Royal opera house, Parisian nobility in gilded loges and balconies cheering with thunderous applause",
        # B07
        "Julie bowing gracefully on stage, bouquets of fresh lilies and roses landing at her feet on the wooden stage floorboards",
        # B08
        "Post-performance reception in the grand salon of the opera, courtiers and aristocrats clamoring to congratulate the new star of Paris",
        # B09
        "Julie in her dressing room quietly removing her theatrical helmet, gazing into the candlelit mirror with calm satisfaction and pride",
        # B10
        "Midnight streets of Paris around the Palais-Royal, cobblestones glistening after light rain, quiet dignity of the city resting under the stars"
    ]
    p8_anchor = "seventeenth-century Paris Opera, Salle du Palais-Royal, authentic French Baroque stage machinery, gilded proscenium, and Louis XIV royal costumes"

    for b_idx, beat in enumerate(p8_beats, 1):
        prompts.append({
            "part": 8,
            "beat": b_idx,
            "filename": f"beat_P08_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p8_anchor,
            "full_prompt": f"{beat}, {p8_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 09: Masterpieces of Lully and Campra - Clorinda the Warrior Maiden
    # =========================================================================
    p9_beats = [
        # B01
        "Composer André Campra at his harpsichord in a sunlit Parisian studio, writing the score of Tancrède with Julie d'Aubigny standing beside him reviewing the vocal lines",
        # B02
        "Illuminated manuscript page of the opera Tancrède, ornate musical notes and Italian-French libretto dedicated to Mademoiselle de Maupin",
        # B03
        "Julie rehearsing a dramatic stage duel scene with opera choristers, combining real sword mastery with theatrical musical rhythm on the rehearsal floor",
        # B04
        "Julie performing the role of the warrior maiden Clorinda on the Paris Opera stage, wearing ornate silver-and-velvet armor, singing with deep emotional resonance",
        # B05
        "Dramatic tragic scene of Clorinda's death in Tancrède, Julie singing her final sorrowful aria beneath dramatic stage lighting as the orchestra plays softly",
        # B06
        "Audience members wiping away tears in the velvet boxes of the Palais-Royal, deeply moved by Julie's authentic emotional delivery and vocal warmth",
        # B07
        "Orchestra pit of the Paris Opera, violinists, cellists, and theorbists performing in synchronized harmony by the warm glow of candle music stands",
        # B08
        "Julie in her private study studying classical opera scores by candlelight, her beloved rapier leaning against the bookcase beside music volumes",
        # B09
        "Walking through the Tuileries gardens in the quiet autumn afternoon, fallen golden leaves carpeting the paths, Julie wrapped in an elegant dark velvet cloak",
        # B10
        "Night falling over the Seine river, bridges illuminated by flickering gas lanterns, serene melodic silence settling over Paris"
    ]
    p9_anchor = "late seventeenth-century French Baroque opera, André Campra's Tancrède, authentic theatrical warrior costume, period instruments and score manuscripts"

    for b_idx, beat in enumerate(p9_beats, 1):
        prompts.append({
            "part": 9,
            "beat": b_idx,
            "filename": f"beat_P09_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p9_anchor,
            "full_prompt": f"{beat}, {p9_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 10: The Masked Ball of Monsieur - A Kiss, A Challenge, and Three Rapiers
    # =========================================================================
    p10_beats = [
        # B01
        "Palais-Royal grand ballroom during Monsieur's royal masked ball, hundreds of courtiers in elaborate Baroque costumes and Venetian masks dancing beneath crystal chandeliers",
        # B02
        "Julie d'Aubigny arriving dressed impeccably in men's court velvet suit, crimson waistcoat, lace cravat, and a delicate gilded carnival mask, exuding dashing charm",
        # B03
        "Julie boldly kissing a beautiful young marquise on the dance floor in front of astonished courtiers, sparking whispers and gasps across the ballroom",
        # B04
        "Three offended noble cavaliers confronting Julie near the grand marble staircase, demanding satisfaction and challenging her to an immediate duel",
        # B05
        "Julie leading the three challengers out into the dark, moonlit garden terrace behind the Palais-Royal, cool night air swirling around stone statues",
        # B06
        "Julie fighting the first nobleman in the garden clearing, swiftly parrying his blade and disarming him with effortless grace in seconds",
        # B07
        "Julie engaging the second and third challengers one after another, her rapier dancing through the silver moonlight with flawless technical precision",
        # B08
        "All three noblemen defeated and resting wounded on the garden bench, Julie politely sheathing her rapier, bowing courteously, and returning inside to the ball",
        # B09
        "Ballroom guests whispering in awe as Julie rejoins the festivities completely unruffled, raising a glass of champagne with a confident smile",
        # B10
        "Dawn breaking over the palace gardens, mist lingering around marble fountains and silent lawns as the masked revelers disperse into the morning"
    ]
    p10_anchor = "seventeenth-century Palais-Royal royal masquerade, French courtly ballroom, authentic Baroque velvet masquerade costumes and moonlit formal palace gardens"

    for b_idx, beat in enumerate(p10_beats, 1):
        prompts.append({
            "part": 10,
            "beat": b_idx,
            "filename": f"beat_P10_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p10_anchor,
            "full_prompt": f"{beat}, {p10_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 11: The Decree of the Sun King - Sovereign Grace and Dueling Laws
    # =========================================================================
    p11_beats = [
        # B01
        "Grand Hall of Mirrors at Versailles, morning sunlight flooding through high arched windows and reflecting off hundreds of mirrored panels, courtiers whispering in small groups",
        # B02
        "King Louis XIV the Sun King seated on his gilded throne, listening with an amused twinkle in his eye as ministers report Julie's duel with three men",
        # B03
        "Louis XIV famously declaring with a royal chuckle that his royal edicts against dueling applied only to gentlemen, not to women, granting her full immunity",
        # B04
        "Courtiers and ministers in elaborate wigs and brocade coats smiling in amused agreement with the King's witty sovereign decision",
        # B05
        "Official royal scribe drafting the second royal pardon decree on thick vellum with ornate calligraphy and royal seals",
        # B06
        "Julie receiving the news in her Paris salon, smiling warmly as she reads the King's sovereign pardon by the light of a tall window",
        # B07
        "Julie visiting the gardens of Versailles at dusk, walking along the Grand Canal with calm majestic dignity as the orange sunset reflects on the water",
        # B08
        "Statue of Apollo emerging from his fountain in the Versailles gardens, golden evening light catching water droplets in suspended motion",
        # B09
        "Quiet evening reception at Versailles, Julie conversing gracefully with court artists, philosophers, and musicians near a marble fireplace",
        # B10
        "Night falling over the Palace of Versailles, golden facade glowing beneath a crescent moon, tranquil royal symmetry resting in absolute peace"
    ]
    p11_anchor = "seventeenth-century Versailles court, Hall of Mirrors, King Louis XIV royal throne room, authentic Sun King era court dress and gilded Baroque interiors"

    for b_idx, beat in enumerate(p11_beats, 1):
        prompts.append({
            "part": 11,
            "beat": b_idx,
            "filename": f"beat_P11_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p11_anchor,
            "full_prompt": f"{beat}, {p11_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 12: The Brussels Interlude - The Bavarian Elector and the Jewel Box
    # =========================================================================
    p12_beats = [
        # B01
        "Snowy Grand Place of Brussels in winter, ornate guildhalls with golden gables illuminated by lantern light against the twilight snow",
        # B02
        "Julie arriving at the Brussels court of Maximilian II Emanuel, Elector of Bavaria, stepping out of a lacquered horse-drawn carriage in warm furs",
        # B03
        "Julie performing at the Brussels court theater, singing for the Bavarian nobility in an intimate, richly tapestried salon",
        # B04
        "The Elector of Bavaria presenting Julie with an ornate velvet-lined jewel box filled with forty thousand gold coins as a token of romantic favor",
        # B05
        "Julie proudly and disdainfully returning the jewel box through the Elector's emissary, declaring her love and art cannot be purchased, standing tall with noble pride",
        # B06
        "Julie packing her leather travel trunk in her Brussels apartment, preparing to return to Paris, calm independent spirit shining in her eyes",
        # B07
        "Carriage journey through snowy Flanders forests, pine trees heavy with white snow, horses' breath steaming in the crisp winter air",
        # B08
        "Warm evening at a Flemish coaching inn, glowing hearth fire, Julie sketching a new melody on a piece of paper by candle glow",
        # B09
        "Crossing the frontier back into the kingdom of France at dawn, morning sun turning the winter snow into glistening gold",
        # B10
        "Quiet arrival back in Paris, city rooftops dusted with snow, welcoming glow of windows along the familiar streets of the capital"
    ]
    p12_anchor = "seventeenth-century Brussels and Flanders, winter Flemish Baroque architecture, princely court interiors, authentic winter travel cloaks and furs"

    for b_idx, beat in enumerate(p12_beats, 1):
        prompts.append({
            "part": 12,
            "beat": b_idx,
            "filename": f"beat_P12_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p12_anchor,
            "full_prompt": f"{beat}, {p12_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 13: The Queen of the Paris Opera - Glory Under the Chandelier Lights
    # =========================================================================
    p13_beats = [
        # B01
        "Julie d'Aubigny at the pinnacle of her fame, standing center stage at the Paris Opera dressed in a breathtaking royal brocade gown with gold embroidery",
        # B02
        "Massive crystal chandeliers hanging from the gilded ceiling of the opera, hundreds of beeswax candles casting warm radiant light over the performers",
        # B03
        "Julie singing a triumphant solo aria, her deep expressive contralto voice resonating through every tier of the packed opera house",
        # B04
        "Close portrait of Julie performing with intense emotional depth, expressive dark eyes reflecting stage light, calm noble stage presence",
        # B05
        "The entire Paris Opera house standing in a roaring ovation, nobles and commoners cheering, petals raining down onto the stage apron",
        # B06
        "Julie receiving royal congratulations backstage from the Duke of Orléans and prominent patrons of the arts in a lavish reception room",
        # B07
        "Julie's opulent private dressing room, vanity mirror surrounded by floral bouquets, velvet armchairs, and stacks of admiring letters",
        # B08
        "Late night quiet in the empty Paris Opera auditorium, single ghost candle illuminating the vast deserted stage and gilded balconies",
        # B09
        "Julie walking along the moonlit banks of the Seine near the Île de la Cité, quiet rippling water reflecting the stars above Paris",
        # B10
        "Midnight peace over Paris, silhouette of Notre-Dame against the deep indigo sky, city resting in tranquil silence after the night's triumph"
    ]
    p13_anchor = "seventeenth-century Paris Opera, grand French Baroque theatrical architecture, opulent gold leaf ornamentation, and authentic prima donna costumes"

    for b_idx, beat in enumerate(p13_beats, 1):
        prompts.append({
            "part": 13,
            "beat": b_idx,
            "filename": f"beat_P13_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p13_anchor,
            "full_prompt": f"{beat}, {p13_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 14: The Passing of the Marquise de Florensac - Grief in the Quiet Shadows
    # =========================================================================
    p14_beats = [
        # B01
        "Intimate candlelit salon in an elegant Parisian hôtel particulier, Julie d'Aubigny and the beautiful Marquise de Florensac sharing quiet tender conversation",
        # B02
        "Soft rain falling against leaded glass windows overlooking a private garden courtyard, melancholy warmth inside the velvet-draped chamber",
        # B03
        "Julie sitting beside the ailing Marquise de Florensac's bed, gently holding her hand in the quiet glow of a single tallow candle",
        # B04
        "The passing of the Marquise, Julie bowing her head in profound quiet grief, solemn stillness filling the dimly lit room",
        # B05
        "Solemn funeral mass in a quiet Parisian church, tall candles casting long shadows across limestone columns and carved stone tombs",
        # B06
        "Julie standing alone in black mourning attire beside a stone sarcophagus, rain gently tapping on the stained glass windows above",
        # B07
        "Julie walking through the autumn mist of Paris, solitary figure in dark cloak, leaves falling gently from the chestnut trees along the boulevards",
        # B08
        "Quiet evening in Julie's Parisian lodgings, packing away her stage costumes and placing her rapier inside a polished cedar chest",
        # B09
        "Julie gazing out over the rooftops of Paris for the last time at twilight, choosing to leave the worldly stage behind for good",
        # B10
        "Night settling over Paris, misty river Seine flowing quietly into the dark, peaceful melancholy and serene acceptance in the air"
    ]
    p14_anchor = "seventeenth-century Parisian private mansions, solemn Baroque church architecture, authentic French period mourning dress and candlelit interiors"

    for b_idx, beat in enumerate(p14_beats, 1):
        prompts.append({
            "part": 14,
            "beat": b_idx,
            "filename": f"beat_P14_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p14_anchor,
            "full_prompt": f"{beat}, {p14_anchor}, {MASTER_STYLE_TAIL}"
        })

    # =========================================================================
    # PART 15: The Abbey in Provence - Eternal Serenity and the Legend of La Maupin
    # =========================================================================
    p15_beats = [
        # B01
        "Julie d'Aubigny traveling southward along a peaceful Provencal countryside road, golden late afternoon sunlight bathing cypress groves and olive orchards",
        # B02
        "Secluded Romanesque stone abbey nestled in the rolling hills of Provence, lavender fields blooming in soft purple hues around the ancient perimeter",
        # B03
        "Julie entering the tranquil abbey courtyard, received with quiet warmth and kindness by the resident abbess and sisters",
        # B04
        "Julie walking peacefully along the arched stone cloister walkways, gentle sunlight creating rhythmic patterns of light and shadow on the stone floor",
        # B05
        "Julie tending to the abbey herb garden, lavender, rosemary, and sage bushes releasing their soothing aroma in the warm southern breeze",
        # B06
        "Quiet abbey library, Julie reading classical philosophical manuscripts by the soft afternoon light streaming through high arched windows",
        # B07
        "Julie singing softly in the empty stone abbey chapel at dusk, her rich contralto voice echoing gently among the ancient vaulted stone arches",
        # B08
        "Julie resting on a stone bench overlooking the vast Provencal valley at sunset, sky painted in brilliant shades of amber, violet, and gold",
        # B09
        "A peaceful simple stone chamber, Julie resting calmly under a linen blanket, breath slow, deep, and steady, heart at complete peace with her extraordinary life",
        # B10
        "The timeless stone abbey of Provence beneath an infinite tapestry of stars, gentle wind whispering through the cypress trees, immortal peaceful legend of Julie d'Aubigny"
    ]
    p15_anchor = "seventeenth-century Romanesque stone abbey in Provence, tranquil lavender fields and cypress groves, authentic simple monastic clothing and peaceful ambient lighting"

    for b_idx, beat in enumerate(p15_beats, 1):
        prompts.append({
            "part": 15,
            "beat": b_idx,
            "filename": f"beat_P15_B{b_idx:02d}.jpg",
            "tier1": beat,
            "tier2": p15_anchor,
            "full_prompt": f"{beat}, {p15_anchor}, {MASTER_STYLE_TAIL}"
        })

    return prompts


def validate_and_save_prompts(prompts: List[Dict[str, str]], target_path: Path):
    """Validates prompts against SSOT rules and writes to file."""
    assert len(prompts) == 150, f"Expected 150 prompts, got {len(prompts)}"

    formatted_lines = []
    for p in prompts:
        prompt_str = p["full_prompt"].strip()
        filename = p["filename"]

        # Validate length
        if len(prompt_str) > 1500:
            raise ValueError(f"Prompt {filename} exceeds 1500 chars ({len(prompt_str)} chars)")

        # Validate forbidden tokens
        for forbidden in FORBIDDEN_WORDS:
            if forbidden in prompt_str.lower():
                raise ValueError(f"Prompt {filename} contains forbidden word: {forbidden}")

        # Validate single line
        if "\n" in prompt_str:
            raise ValueError(f"Prompt {filename} has newline inside prompt string")

        formatted_lines.append(f"{filename}: {prompt_str}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n\n".join(formatted_lines) + "\n"
    target_path.write_text(content, encoding="utf-8")
    print(f"✅ Successfully validated and saved 150 prompts to:\n📁 {target_path}")


if __name__ == "__main__":
    prompts = build_julie_daubigny_prompts()

    # Save to 01. Preproduction and 02. Media Generation/combined
    project_root = Path("output/Julie d'Aubigny - Julie d'Aubigny - The Swordswoman Who Set Paris Ablaze and Defied the King")
    p1_file = project_root / "01. Preproduction" / "combined_imageprompts.txt"
    p2_file = project_root / "02. Media Generation" / "combined" / "combined_imageprompts.txt"

    validate_and_save_prompts(prompts, p1_file)
    validate_and_save_prompts(prompts, p2_file)
    print("🎯 All 150 beats successfully generated and verified compliant with 04_VISUAL_PROMPT_ENGINE.md!")
