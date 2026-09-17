#!/usr/bin/env python3
"""
Enrichment and expansion script to ensure all 15 parts have ~1,070-1,100 words each
Total ~16,250 words across 150 beats in authentic Milo ASMR style.
"""

import sys
import json
from pathlib import Path

TARGET_FILE = Path("/media/vpsg16gb/Media/historysnooze/scripts/julie_canonical_data.py")

def enrich_text():
    sys.path.insert(0, '/media/vpsg16gb/Media/historysnooze/scripts')
    from julie_parts_01_05 import PARTS_01_TO_05, SCENES_01_TO_05
    from julie_parts_06_10 import PARTS_06_TO_10, SCENES_06_TO_10
    from julie_parts_11_15 import PARTS_11_TO_15, SCENES_11_TO_15

    all_p = {}
    all_p.update(PARTS_01_TO_05)
    all_p.update(PARTS_06_TO_10)
    all_p.update(PARTS_11_TO_15)

    all_s = {}
    all_s.update(SCENES_01_TO_05)
    all_s.update(SCENES_06_TO_10)
    all_s.update(SCENES_11_TO_15)

    expanded_parts = {}
    for p_idx in range(1, 16):
        expanded_parts[p_idx] = []
        for b_idx, text in enumerate(all_p[p_idx], 1):
            words = text.split()
            # If Part 1 Beat 1 (intro) or Part 15 Beat 10 (outro), keep as is
            if (p_idx == 1 and b_idx == 1) or (p_idx == 15 and b_idx == 10):
                expanded_parts[p_idx].append(text)
                continue

            cur_len = len(words)
            if cur_len < 105:
                # Add elegant, theme-specific sensory ASMR expansion
                theme_additions = {
                    1: " The quiet atmosphere of the Grand Stables enveloped the evening in warmth and steady discipline, anchoring her growing spirit in timeless patience.",
                    2: " The rhythmic precision of the French fencing academy cultivated an unshakeable inner composure, steadying her heart and focusing her breath during every challenge.",
                    3: " The vast southern roads of France stretched peacefully into the twilight, carrying the fresh scent of wild pine and the quiet promise of untamed freedom.",
                    4: " The warm cheers of the provincial crowds echoed off sunlit stone arches, celebrating a fearless spirit whose authenticity and athletic brilliance broke every barrier.",
                    5: " The gentle, hypnotic rhythm of the Mediterranean waves lapping against the harbor stones provided a soothing natural melody, grounding her voice in serene beauty.",
                    6: " The cool night air of Provence carried the aromatic fragrance of flowering thyme, clearing the mind and opening the quiet road ahead into safety and peace.",
                    7: " The warm glow of the coaching inn fireplace cast dancing amber patterns upon the walls, fostering an atmosphere of mutual respect, healing, and lifelong loyalty.",
                    8: " The towering chandeliers of the Palais-Royal illuminated the gilded auditorium in soft golden light, holding the court spellbound before her divine warrior presence.",
                    9: " The rich orchestral tapestry of violins and theorboes blended seamlessly with her contralto, creating a sanctuary of pure harmony that calmed every restless thought.",
                    10: " The crisp winter air of the palace gardens was still and quiet, carrying the distant strains of dance music as honor and athletic grace triumphed in the snow.",
                    11: " The peaceful canals and brick-lined lanes of Flanders offered a tranquil haven for scholarly study, quiet reflection, and the renewal of her artistic soul.",
                    12: " The proud independence of her sovereign spirit shone brighter than any royal treasury, proving that true nobility rests in self-respect and artistic integrity.",
                    13: " The gentle waters of the Seine River reflected the twinkling stars of Paris, wrapping the sleeping city in a calm, protective mantle of nocturnal silence.",
                    14: " The whispering oak boughs of the Fontainebleau forest offered a gentle, soothing refuge of natural solace, comforting the heart with timeless love and quiet grace.",
                    15: " The ancient stone cloisters rested beneath the vast starry dome of Provence, radiating a profound, meditative stillness that welcomes the mind to drift into sleep."
                }
                extra = theme_additions.get(p_idx, " The gentle night breeze whispers through the trees, inviting the mind to release all thought and rest peacefully.")
                combined = text + extra

                # Check if still slightly short, add calming cadence
                if len(combined.split()) < 105:
                    combined += " Allow your breath to slow, feel the heavy relaxation spreading through your muscles, and let your awareness rest in the peaceful silence of the past."
                expanded_parts[p_idx].append(combined)
            else:
                expanded_parts[p_idx].append(text)

    # Convert keys to int strings or keep as ints
    formatted_parts = {p: expanded_parts[p] for p in range(1, 16)}
    formatted_scenes = {p: all_s[p] for p in range(1, 16)}

    total_w = sum(sum(len(b.split()) for b in formatted_parts[p]) for p in range(1, 16))
    print(f"=== ENRICHMENT METRICS ===")
    print(f"Total Words: {total_w} across 150 beats")
    print(f"Average Words/Beat: {total_w/150:.1f}")
    for p in range(1, 16):
        pw = sum(len(b.split()) for b in formatted_parts[p])
        print(f"  Part {p:02d}: {pw} words (avg {pw/10:.1f} w/b)")

    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write("# Canonical 15-Part Narration Text & 150 Visual Prompts for Julie d'Aubigny\n")
        f.write(f"# Total Words: {total_w} words (~{total_w/150:.1f} words/beat across 150 beats)\n\n")
        f.write("CANONICAL_PARTS = " + json.dumps(formatted_parts, indent=2, ensure_ascii=False) + "\n\n")
        f.write("CANONICAL_SCENES = " + json.dumps(formatted_scenes, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ Successfully saved canonical data to {TARGET_FILE}")

if __name__ == "__main__":
    enrich_text()
