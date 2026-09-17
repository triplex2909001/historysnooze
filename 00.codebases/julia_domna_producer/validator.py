"""
HISTORYSNOOZE: AUDIT & GATEKEEPER VALIDATOR
Module: validator.py
SSOT-compliant with 02_SCRIPT_SOP_&_GATEKEEPERS.md & 04_VISUAL_PROMPT_ENGINE.md.
Rule <= 150 lines strictly enforced.
"""

import re
from typing import Dict, List, Tuple
from outline_data import JULIA_DOMNA_OUTLINE
from script_aggregator import ALL_PARTS
from prompt_builder import generate_combined_imageprompts_text


def validate_gk1_outline() -> Tuple[bool, List[str]]:
    """Audit GK1: Outline structure and forbidden keywords."""
    errors = []
    acts = JULIA_DOMNA_OUTLINE.get("acts", [])
    if len(acts) != 3:
        errors.append(f"GK1 Error: Expected 3 acts, found {len(acts)}")

    total_parts = sum(len(act.get("parts", [])) for act in acts)
    if total_parts != 15:
        errors.append(f"GK1 Error: Expected 15 parts, found {total_parts}")

    for act in acts:
        for part in act.get("parts", []):
            if "dim the lights" in part.get("summary", "").lower():
                errors.append(f"GK1 Error: 'dim the lights' forbidden in Outline summary (Part {part['part']})")

    return len(errors) == 0, errors


def validate_gk2_script() -> Tuple[bool, List[str], Dict[int, int]]:
    """Audit GK2: 15 parts, word count, 10 paras/part, forbidden symbols, numbers."""
    errors = []
    word_counts = {}
    total_words = 0
    forbidden_symbols = re.compile(r"[\*#@\$%\^&~/\\\|<>{}\[\]\+=]")

    # Check Part 01 opening
    p01_first = ALL_PARTS[1][0]
    if "now, dim the lights" not in p01_first.lower():
        errors.append("GK2 Error: Part 01 Beat 01 missing mandatory 'dim the lights' host opening cue.")

    # Check Parts 02-14 for forbidden dim the lights
    for p_num in range(2, 15):
        for para in ALL_PARTS[p_num]:
            if "dim the lights" in para.lower():
                errors.append(f"GK2 Error: Forbidden 'dim the lights' found in Part {p_num}")

    # Check Part 15 sleep wind-down
    p15_last = ALL_PARTS[15][-1]
    if "sweet dreams" not in p15_last.lower():
        errors.append("GK2 Error: Part 15 missing 'sweet dreams' closing wind-down.")

    for p_num, paras in ALL_PARTS.items():
        if len(paras) != 10:
            errors.append(f"GK2 Error: Part {p_num:02d} has {len(paras)} paragraphs (expected 10).")

        part_text = " ".join(paras)
        words = len(part_text.split())
        word_counts[p_num] = words
        total_words += words

        # Check raw digits (must be words)
        digit_matches = re.findall(r"\b\d+\b", part_text)
        if digit_matches:
            errors.append(f"GK2 Error: Raw digits found in Part {p_num:02d}: {digit_matches[:5]}")

        # Check forbidden symbols
        symbol_matches = forbidden_symbols.findall(part_text)
        if symbol_matches:
            errors.append(f"GK2 Error: Forbidden symbols found in Part {p_num:02d}: {set(symbol_matches)}")

    return len(errors) == 0, errors, word_counts


def validate_gk3_prompts() -> Tuple[bool, List[str], int]:
    """Audit GK3: 150 prompts, single lines, JPG format, double newline separation."""
    errors = []
    prompt_text = generate_combined_imageprompts_text().strip()
    prompts = prompt_text.split("\n\n")

    if len(prompts) != 150:
        errors.append(f"GK3 Error: Expected 150 prompts, found {len(prompts)}")

    for idx, p in enumerate(prompts, start=1):
        if "\n" in p:
            errors.append(f"GK3 Error: Prompt #{idx} contains internal newlines (must be 1 line).")
        if not p.startswith(f"beat_P"):
            errors.append(f"GK3 Error: Prompt #{idx} invalid filename prefix: {p[:20]}")
        if ".gif" in p.lower():
            errors.append(f"GK3 Error: Prompt #{idx} contains .gif (0% GIF rule).")

    return len(errors) == 0, errors, len(prompts)
