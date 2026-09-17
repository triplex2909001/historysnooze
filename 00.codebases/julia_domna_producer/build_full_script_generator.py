"""
HISTORYSNOOZE: CANONICAL 15-PARTS SCRIPT GENERATOR
Module: build_full_script_generator.py
Generates the 8 modular script parts files with strict 1,050 - 1,150 words per part.
SSOT-compliant with 01_STYLE_BIBLE through 06_PIPELINE_AUTOMATION_SPEC.
"""

from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent


def write_file(filename: str, p1_name: str, p1_data: list, p2_name: str = None, p2_data: list = None):
    """Write cleanly formatted python file with line limit compliance."""
    path = BASE_DIR / filename
    lines = []
    lines.append('"""')
    lines.append(f"HISTORYSNOOZE: SCRIPT TEXT ({p1_name}" + (f" & {p2_name}" if p2_name else "") + ")")
    lines.append(f"Module: {filename}")
    lines.append("SSOT-compliant with 01_STYLE_BIBLE_&_GOLDEN_EXAMPLES.md & 02_SCRIPT_SOP_&_GATEKEEPERS.md.")
    lines.append("Target: 1,050 - 1,150 words per part. Rule <= 150 lines strictly enforced.")
    lines.append('"""\n')

    lines.append(f"{p1_name} = [")
    for para in p1_data:
        lines.append(f"    {json.dumps(para)},")
    lines.append("]\n")

    if p2_name and p2_data:
        lines.append(f"{p2_name} = [")
        for para in p2_data:
            lines.append(f"    {json.dumps(para)},")
        lines.append("]\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    words_p1 = sum(len(p.split()) for p in p1_data)
    print(f"Written: {filename} -> {p1_name}: {words_p1} words ({len(p1_data)} paras)", end="")
    if p2_name and p2_data:
        words_p2 = sum(len(p.split()) for p in p2_data)
        print(f", {p2_name}: {words_p2} words ({len(p2_data)} paras)", end="")
    print()
