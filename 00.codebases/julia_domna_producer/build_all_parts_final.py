"""
HISTORYSNOOZE: MASTER CALIBRATED PARTS BUILDER
Module: build_all_parts_final.py
Calibrates all 15 parts to 1,070 - 1,130 words per part.
SSOT-compliant with 01_STYLE_BIBLE through 06_PIPELINE_AUTOMATION_SPEC.
Rule <= 150 lines strictly enforced.
"""

from auto_calibrator import calibrate_part_paras
from build_parts_p01_p06 import P01, P02, P03, P04, P05, P06
from raw_text_act2 import P07_RAW, P08_RAW, P09_RAW, P10_RAW
from raw_text_act3 import P11_RAW, P12_RAW, P13_RAW, P14_RAW, P15_RAW
from script_master_factory import write_modular_file


def build_and_calibrate_all():
    """Calibrate and write all 8 parts files."""
    print("=== CALIBRATING ALL 15 PARTS TO 1,070 - 1,130 WORDS ===")

    # Calibrate each part
    p01_cal = calibrate_part_paras(P01, 1090)
    p02_cal = calibrate_part_paras(P02, 1090)
    p03_cal = calibrate_part_paras(P03, 1090)
    p04_cal = calibrate_part_paras(P04, 1090)
    p05_cal = calibrate_part_paras(P05, 1090)
    p06_cal = calibrate_part_paras(P06, 1090)
    p07_cal = calibrate_part_paras(P07_RAW, 1090)
    p08_cal = calibrate_part_paras(P08_RAW, 1090)
    p09_cal = calibrate_part_paras(P09_RAW, 1090)
    p10_cal = calibrate_part_paras(P10_RAW, 1090)
    p11_cal = calibrate_part_paras(P11_RAW, 1090)
    p12_cal = calibrate_part_paras(P12_RAW, 1090)
    p13_cal = calibrate_part_paras(P13_RAW, 1090)
    p14_cal = calibrate_part_paras(P14_RAW, 1090)
    p15_cal = calibrate_part_paras(P15_RAW, 1090)

    # Write modular files
    write_modular_file("parts_p01_p02.py", "P01_PARAGRAPHS", p01_cal, "P02_PARAGRAPHS", p02_cal)
    write_modular_file("parts_p03_p04.py", "P03_PARAGRAPHS", p03_cal, "P04_PARAGRAPHS", p04_cal)
    write_modular_file("parts_p05_p06.py", "P05_PARAGRAPHS", p05_cal, "P06_PARAGRAPHS", p06_cal)
    write_modular_file("parts_p07_p08.py", "P07_PARAGRAPHS", p07_cal, "P08_PARAGRAPHS", p08_cal)
    write_modular_file("parts_p09_p10.py", "P09_PARAGRAPHS", p09_cal, "P10_PARAGRAPHS", p10_cal)
    write_modular_file("parts_p11_p12.py", "P11_PARAGRAPHS", p11_cal, "P12_PARAGRAPHS", p12_cal)
    write_modular_file("parts_p13_p14.py", "P13_PARAGRAPHS", p13_cal, "P14_PARAGRAPHS", p14_cal)
    write_modular_file("parts_p15.py", "P15_PARAGRAPHS", p15_cal)

    print("=== ALL 15 PARTS SUCCESSFULLY CALIBRATED & WRITTEN ===")


if __name__ == "__main__":
    build_and_calibrate_all()
