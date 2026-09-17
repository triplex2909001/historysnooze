"""
HISTORYSNOOZE: SCRIPT AGGREGATOR
Module: script_aggregator.py
SSOT-compliant with 02_SCRIPT_SOP_&_GATEKEEPERS.md.
Rule <= 150 lines strictly enforced.
"""

from typing import Dict, List
from parts_p01_p02 import P01_PARAGRAPHS, P02_PARAGRAPHS
from parts_p03_p04 import P03_PARAGRAPHS, P04_PARAGRAPHS
from parts_p05_p06 import P05_PARAGRAPHS, P06_PARAGRAPHS
from parts_p07_p08 import P07_PARAGRAPHS, P08_PARAGRAPHS
from parts_p09_p10 import P09_PARAGRAPHS, P10_PARAGRAPHS
from parts_p11_p12 import P11_PARAGRAPHS, P12_PARAGRAPHS
from parts_p13_p14 import P13_PARAGRAPHS, P14_PARAGRAPHS
from parts_p15 import P15_PARAGRAPHS

ALL_PARTS: Dict[int, List[str]] = {
    1: P01_PARAGRAPHS,
    2: P02_PARAGRAPHS,
    3: P03_PARAGRAPHS,
    4: P04_PARAGRAPHS,
    5: P05_PARAGRAPHS,
    6: P06_PARAGRAPHS,
    7: P07_PARAGRAPHS,
    8: P08_PARAGRAPHS,
    9: P09_PARAGRAPHS,
    10: P10_PARAGRAPHS,
    11: P11_PARAGRAPHS,
    12: P12_PARAGRAPHS,
    13: P13_PARAGRAPHS,
    14: P14_PARAGRAPHS,
    15: P15_PARAGRAPHS,
}


def get_all_parts() -> Dict[int, List[str]]:
    """Return dictionary of 15 parts with 10 paragraphs each."""
    return ALL_PARTS


def get_part_paragraphs(part_num: int) -> List[str]:
    """Return 10 paragraphs for a given part number."""
    return ALL_PARTS.get(part_num, [])


def get_full_script_markdown() -> str:
    """Generate complete markdown script text formatted cleanly."""
    lines = []
    lines.append("# Julia Domna: The Woman Who Ruled Rome from the Shadows\n")
    lines.append("## Full Canonical Script (15 Parts, 150 Beats)\n\n")

    for part_num in range(1, 16):
        lines.append(f"### Part {part_num:02d}\n\n")
        paragraphs = ALL_PARTS[part_num]
        for p in paragraphs:
            lines.append(f"{p}\n\n")

    return "".join(lines).strip()
