"""
HISTORYSNOOZE: CANONICAL PARTS GENERATOR
Module: generate_all_canonical_parts.py
Generates the 8 parts modules with 1,050 - 1,150 words per part.
SSOT-compliant with 01_STYLE_BIBLE through 06_PIPELINE_AUTOMATION_SPEC.
"""

from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent

# We will define the full canonical text for all 15 parts
# Each part contains exactly 10 paragraphs.
# Each part is carefully calibrated to 1,070 - 1,130 words.

# Let's write the generator function
def write_modular_file(filename: str, p1_name: str, p1_list: list, p2_name: str = None, p2_list: list = None):
    out_path = BASE_DIR / filename
    lines = []
    lines.append('"""')
    lines.append(f"HISTORYSNOOZE: SCRIPT TEXT ({p1_name}" + (f" & {p2_name}" if p2_name else "") + ")")
    lines.append(f"Module: {filename}")
    lines.append("SSOT-compliant with 01_STYLE_BIBLE_&_GOLDEN_EXAMPLES.md & 02_SCRIPT_SOP_&_GATEKEEPERS.md.")
    lines.append("Target: 1,050 - 1,150 words per part. Rule <= 150 lines strictly enforced.")
    lines.append('"""\n')

    lines.append(f"{p1_name} = [")
    for para in p1_list:
        lines.append(f"    {json.dumps(para)},")
    lines.append("]\n")

    if p2_name and p2_list:
        lines.append(f"{p2_name} = [")
        for para in p2_list:
            lines.append(f"    {json.dumps(para)},")
        lines.append("]\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Written: {filename}")
