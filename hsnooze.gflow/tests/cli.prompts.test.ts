import { describe, expect, it } from "vitest";
import { parsePromptsFile, type ParsedBeat } from "../src/cli.js";

describe("parsePromptsFile", () => {
  it("parses clean prompt without reference tags", () => {
    const raw = "beat_P01_B01.jpg: A peaceful Zen garden with mossy stones.";
    const result = parsePromptsFile(raw);
    expect(result).toEqual([
      {
        id: "beat_P01_B01",
        prompt: "A peaceful Zen garden with mossy stones.",
        character: [],
        ingredients: []
      }
    ]);
  });

  it("extracts [CHARACTER: ...] into character array and strips from prompt", () => {
    const raw = "beat_P01_B02.jpg: [CHARACTER: ref_character_matsuo_basho] Matsuo Bashō walking on an ancient trail.";
    const result = parsePromptsFile(raw);
    expect(result[0]).toEqual({
      id: "beat_P01_B02",
      prompt: "Matsuo Bashō walking on an ancient trail.",
      character: ["ref_character_matsuo_basho"],
      ingredients: []
    });
  });

  it("extracts [SETTING: ...], [PROP: ...], [INGREDIENT: ...] into ingredients array", () => {
    const raw = "beat_P01_B03.jpg: [CHARACTER: ref_character_basho] [SETTING: ref_setting_edo_hermitage] [PROP: ref_prop_bamboo_staff] [INGREDIENT: ref_flower] Deep in thought by the hearth.";
    const result = parsePromptsFile(raw);
    expect(result[0]).toEqual({
      id: "beat_P01_B03",
      prompt: "Deep in thought by the hearth.",
      character: ["ref_character_basho"],
      ingredients: [
        "ref_setting_edo_hermitage",
        "ref_prop_bamboo_staff",
        "ref_flower"
      ]
    });
  });

  it("handles case insensitivity, plural tags, and interior whitespace", () => {
    const raw = "beat_P02_B04.jpg: [characters:  ref_character_sora  ] [settings: ref_mountain_trail ] [props: bamboo_staff ] Sora resting beneath a cedar.";
    const result = parsePromptsFile(raw);
    expect(result[0].character).toEqual(["ref_character_sora"]);
    expect(result[0].ingredients).toEqual(["ref_mountain_trail", "bamboo_staff"]);
    expect(result[0].prompt).toBe("Sora resting beneath a cedar.");
  });

  it("supports multiple character tags on a single beat", () => {
    const raw = "beat_P03_B01.jpg: [CHARACTER: ref_character_basho] [CHARACTER: ref_character_sora] Master and disciple conversing.";
    const result = parsePromptsFile(raw);
    expect(result[0].character).toEqual(["ref_character_basho", "ref_character_sora"]);
    expect(result[0].prompt).toBe("Master and disciple conversing.");
  });

  it("strips various image extensions from beat ID", () => {
    const raw = `
beat_01.jpg: Prompt 1
beat_02.jpeg: Prompt 2
beat_03.png: Prompt 3
beat_04.webp: Prompt 4
beat_05: Prompt 5
    `.trim();
    const result = parsePromptsFile(raw);
    expect(result.map((b) => b.id)).toEqual(["beat_01", "beat_02", "beat_03", "beat_04", "beat_05"]);
  });

  it("skips comments and empty lines", () => {
    const raw = `
# Header comment explaining the file
# Another comment line

beat_P01_B01.jpg: Prompt one

# Mid-file comment
beat_P01_B02.jpg: Prompt two

# Trailing comment
    `;
    const result = parsePromptsFile(raw);
    expect(result).toHaveLength(2);
    expect(result[0].id).toBe("beat_P01_B01");
    expect(result[1].id).toBe("beat_P01_B02");
  });

  it("collapses internal and trailing whitespace properly when stripping tags", () => {
    const raw = "beat_P05_B10.jpg: [CHARACTER: basho]   [SETTING: hermitage]   Morning rain on the leaves.   ";
    const result = parsePromptsFile(raw);
    expect(result[0].prompt).toBe("Morning rain on the leaves.");
  });
});
