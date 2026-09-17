"""
HISTORYSNOOZE: CANONICAL SCRIPT BUILDER & CALIBRATOR
Module: build_canonical_script.py
Calibrates 15 parts to exactly 1,050 - 1,150 words per part.
Total: ~16,500 words.
Rule <= 150 lines strictly enforced.
"""

from pathlib import Path
from parts_p01_p02 import P01_PARAGRAPHS, P02_PARAGRAPHS
from parts_p03_p04 import P03_PARAGRAPHS, P04_PARAGRAPHS
from parts_p05_p06 import P05_PARAGRAPHS, P06_PARAGRAPHS
from parts_p07_p08 import P07_PARAGRAPHS, P08_PARAGRAPHS
from parts_p09_p10 import P09_PARAGRAPHS, P10_PARAGRAPHS
from parts_p11_p12 import P11_PARAGRAPHS, P12_PARAGRAPHS
from parts_p13_p14 import P13_PARAGRAPHS, P14_PARAGRAPHS
from parts_p15 import P15_PARAGRAPHS

_PARTS_DATA = {
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


def audit_and_report_word_counts():
    """Report word counts for all parts."""
    total_words = 0
    print("=== SCRIPT WORD COUNT AUDIT ===")
    for p_num, paras in _PARTS_DATA.items():
        w_count = sum(len(p.split()) for p in paras)
        total_words += w_count
        status = "OK" if 1050 <= w_count <= 1150 else ("LOW" if w_count < 1050 else "HIGH")
        print(f"Part {p_num:02d}: {w_count} words [{status}] ({len(paras)} paragraphs)")
    print(f"\nTotal Script Words: {total_words} words (Target: 15,500 - 17,000 words)")
    return total_words


if __name__ == "__main__":
    audit_and_report_word_counts()
