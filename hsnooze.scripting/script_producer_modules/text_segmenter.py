"""
HistorySnooze Script Producer - Narrative Text Segmentation Helpers
Module: text_segmenter.py
Rule <= 150 lines compliant.
"""

import re
from typing import List


def segment_part_text(
    part_index: int, part_text: str, target_beats: int = 10
) -> List[str]:
    """
    Segments a single part's text into exactly target_beats narrative paragraphs.
    Uses sentence-level splitting for longer paragraphs and merging for shorter paragraphs.
    Defensively handles Windows CRLF (\\r\\n), mixed line endings, and empty/whitespace text.
    """
    if not part_text or not part_text.strip():
        return [f"Narrative beat {i}" for i in range(1, target_beats + 1)]

    normalized = part_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_paras = [
        p.strip()
        for p in re.split(r"\n\s*\n", normalized)
        if p.strip() and not p.strip().startswith("---")
    ]
    if not raw_paras:
        return [f"Narrative beat {i}" for i in range(1, target_beats + 1)]

    if len(raw_paras) == target_beats:
        return raw_paras

    paras = list(raw_paras)
    while len(paras) < target_beats:
        longest_idx = max(
            range(len(paras)), key=lambda i: len(paras[i].split())
        )
        longest_p = paras[longest_idx]
        sentences = re.split(r"(?<=[.!?])\s+", longest_p)
        if len(sentences) <= 1:
            break
        mid = max(1, len(sentences) // 2)
        p_a = " ".join(sentences[:mid])
        p_b = " ".join(sentences[mid:])
        paras = paras[:longest_idx] + [p_a, p_b] + paras[longest_idx + 1 :]

    while len(paras) > target_beats:
        shortest_pair_idx = min(
            range(len(paras) - 1),
            key=lambda i: len(paras[i].split()) + len(paras[i + 1].split()),
        )
        merged = paras[shortest_pair_idx] + " " + paras[shortest_pair_idx + 1]
        paras = (
            paras[:shortest_pair_idx] + [merged] + paras[shortest_pair_idx + 2 :]
        )

    return paras
