import { describe, expect, it } from "vitest";
import { parsePromptsFile, type ParsedBeat } from "../src/cli.js";

describe("Adversarial Prompt Parsing (parsePromptsFile)", () => {
  describe("Pathological colons handling", () => {
    it("preserves multiple colons in the prompt body without truncation", () => {
      const input = "beat_P01_B01.jpg: [CHARACTER: ref_basho] Dawn: mist rises over the river: temple bell resonates in distance.";
      const [beat] = parsePromptsFile(input);
      expect(beat).toBeDefined();
      expect(beat.id).toBe("beat_P01_B01");
      expect(beat.character).toEqual(["ref_basho"]);
      expect(beat.prompt).toBe("Dawn: mist rises over the river: temple bell resonates in distance.");
    });

    it("handles colons inside tag values cleanly", () => {
      const input = "beat_P01_B02.jpg: [PROP: tool:chisel:v1] [SETTING: loc:edo:fukagawa] The artisan at work.";
      const [beat] = parsePromptsFile(input);
      expect(beat).toBeDefined();
      expect(beat.ingredients).toEqual(["tool:chisel:v1", "loc:edo:fukagawa"]);
      expect(beat.prompt).toBe("The artisan at work.");
    });

    it("rejects lines where colon is at index 0 (no ID)", () => {
      const input = ": [CHARACTER: ref_basho] Missing ID prefix.";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(0);
    });

    it("rejects lines with no colon at all", () => {
      const input = "beat_P01_B03.jpg Missing colon delimiter entirely.";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(0);
    });

    it("rejects lines where prompt after colon is completely empty", () => {
      const input = "beat_P01_B04.jpg:     ";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(0);
    });

    it("correctly splits on first colon even if ID contains colons", () => {
      const input = "prefix:beat_P01_B05.jpg: [CHARACTER: ref_basho] A complex id line.";
      const [beat] = parsePromptsFile(input);
      expect(beat).toBeDefined();
      expect(beat.id).toBe("prefix");
      expect(beat.prompt).toBe("beat_P01_B05.jpg: A complex id line.");
    });
  });

  describe("Windows CRLF vs Unix LF vs Mixed line endings", () => {
    it("handles Windows CRLF (\\r\\n) without leaving carriage returns", () => {
      const input = "beat_P01_B01.jpg: [CHARACTER: ref_basho] Line one.\r\nbeat_P01_B02.jpg: [SETTING: ref_fukagawa] Line two.\r\n";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(2);
      for (const b of beats) {
        expect(b.id).not.toContain("\r");
        expect(b.prompt).not.toContain("\r");
        for (const c of b.character) expect(c).not.toContain("\r");
        for (const ing of b.ingredients) expect(ing).not.toContain("\r");
      }
      expect(beats[0].prompt).toBe("Line one.");
      expect(beats[1].prompt).toBe("Line two.");
    });

    it("handles mixed LF and CRLF with blank lines containing carriage returns", () => {
      const input = "beat_P01_B01.jpg: Prompt A\r\n\r\nbeat_P01_B02.jpg: Prompt B\n\r\nbeat_P01_B03.jpg: Prompt C\n";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(3);
      expect(beats.map((b) => b.id)).toEqual(["beat_P01_B01", "beat_P01_B02", "beat_P01_B03"]);
    });
  });

  describe("Empty lines and whitespace padding", () => {
    it("ignores spaces, tabs, and empty lines across the file", () => {
      const input = `

\t\t
beat_P01_B01.jpg:    [CHARACTER: ref_basho]   Prompt with internal padding.
  \t
beat_P01_B02.jpg: Normal prompt.

`;
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(2);
      expect(beats[0].prompt).toBe("Prompt with internal padding.");
      expect(beats[1].prompt).toBe("Normal prompt.");
    });
  });

  describe("Comment lines with colons and special tokens", () => {
    it("skips comments containing colons, beats syntax, or reference tags", () => {
      const input = `
# Comment: this is a header note
# beat_P01_B01.jpg: [CHARACTER: ref_fake] Commented beat
   # Indented comment with colon: value
\t# Tabbed comment: [SETTING: ref_fake]
beat_P01_B01.jpg: [CHARACTER: ref_basho] Valid beat prompt.
# Trailing comment: end of file
`;
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(1);
      expect(beats[0].id).toBe("beat_P01_B01");
      expect(beats[0].character).toEqual(["ref_basho"]);
      expect(beats[0].prompt).toBe("Valid beat prompt.");
    });
  });

  describe("Multiple tags of same and mixed types", () => {
    it("extracts multiple character tags into character array", () => {
      const input = "beat_P01_B01.jpg: [CHARACTER: ref_basho] [CHARACTER: ref_sora] [CHARACTER: ref_villager] Meeting at the crossroads.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref_basho", "ref_sora", "ref_villager"]);
      expect(beat.ingredients).toEqual([]);
      expect(beat.prompt).toBe("Meeting at the crossroads.");
    });

    it("extracts multiple setting, prop, and ingredient tags into ingredients array in appearance order", () => {
      const input = "beat_P01_B02.jpg: [SETTING: ref_hut] [PROP: ref_staff] [INGREDIENT: ref_tea] [PROP: ref_hat] Inside the hut.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual([]);
      expect(beat.ingredients).toEqual(["ref_hut", "ref_staff", "ref_tea", "ref_hat"]);
      expect(beat.prompt).toBe("Inside the hut.");
    });

    it("handles interleaved character and ingredient tags", () => {
      const input = "beat_P01_B03.jpg: [CHARACTER: ref_basho] [PROP: ref_inkstone] [CHARACTER: ref_sora] [SETTING: ref_inn] Writing verse together.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref_basho", "ref_sora"]);
      expect(beat.ingredients).toEqual(["ref_inkstone", "ref_inn"]);
      expect(beat.prompt).toBe("Writing verse together.");
    });
  });

  describe("Mixed case and plural tag forms", () => {
    it("supports all casing variations and plural aliases", () => {
      const input = `
beat_01.jpg: [cHaRaCtEr: ref_1] Prompt 1
beat_02.jpg: [CHARACTERS: ref_2] Prompt 2
beat_03.jpg: [setting: ref_3] Prompt 3
beat_04.jpg: [SETTINGS: ref_4] Prompt 4
beat_05.jpg: [prop: ref_5] Prompt 5
beat_06.jpg: [PROPS: ref_6] Prompt 6
beat_07.jpg: [ingredient: ref_7] Prompt 7
beat_08.jpg: [INGREDIENTS: ref_8] Prompt 8
`;
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(8);
      expect(beats[0].character).toEqual(["ref_1"]);
      expect(beats[1].character).toEqual(["ref_2"]);
      expect(beats[2].ingredients).toEqual(["ref_3"]);
      expect(beats[3].ingredients).toEqual(["ref_4"]);
      expect(beats[4].ingredients).toEqual(["ref_5"]);
      expect(beats[5].ingredients).toEqual(["ref_6"]);
      expect(beats[6].ingredients).toEqual(["ref_7"]);
      expect(beats[7].ingredients).toEqual(["ref_8"]);
    });
  });

  describe("Tag names with numbers, hyphens, underscores, dots, and whitespace", () => {
    it("parses tags with alphanumeric, hyphen, dot, and underscore characters", () => {
      const input = "beat_P01_B01.jpg: [CHARACTER: ref-char_matsuo-basho.v1] [PROP: item-123_456.final] Walking along.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref-char_matsuo-basho.v1"]);
      expect(beat.ingredients).toEqual(["item-123_456.final"]);
      expect(beat.prompt).toBe("Walking along.");
    });

    it("trims internal whitespace within tag brackets", () => {
      const input = "beat_P01_B02.jpg: [CHARACTER:    ref_basho_spaced   ]   [PROP:  \t ref_staff_tabbed \t ] A quiet path.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref_basho_spaced"]);
      expect(beat.ingredients).toEqual(["ref_staff_tabbed"]);
      expect(beat.prompt).toBe("A quiet path.");
    });

    it("ignores empty tag values without crashing or creating empty entries", () => {
      const input = "beat_P01_B03.jpg: [CHARACTER:] [PROP:   ] An open field.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual([]);
      expect(beat.ingredients).toEqual([]);
      expect(beat.prompt).toBe("An open field.");
    });
  });

  describe("Tag stripping and whitespace edge cases", () => {
    it("cleanly strips tags at the start of prompt without leading space", () => {
      const input = "beat_01.jpg: [CHARACTER: ref_basho] [SETTING: ref_fukagawa] Dawn breaks over the thatched roof.";
      const [beat] = parsePromptsFile(input);
      expect(beat.prompt).toBe("Dawn breaks over the thatched roof.");
      expect(beat.prompt.startsWith(" ")).toBe(false);
    });

    it("cleanly strips tags in the middle of prompt without duplicate spaces", () => {
      const input = "beat_02.jpg: Master [CHARACTER: ref_basho] and disciple [CHARACTER: ref_sora] walk along the river.";
      const [beat] = parsePromptsFile(input);
      expect(beat.prompt).toBe("Master and disciple walk along the river.");
      expect(beat.prompt).not.toContain("  ");
    });

    it("cleanly strips tags at the end of prompt without trailing space", () => {
      const input = "beat_03.jpg: Footsteps fade into the morning mist [SETTING: ref_trail] [PROP: ref_staff]";
      const [beat] = parsePromptsFile(input);
      expect(beat.prompt).toBe("Footsteps fade into the morning mist");
      expect(beat.prompt.endsWith(" ")).toBe(false);
    });

    it("strips adjacent tags with no separating spaces", () => {
      const input = "beat_04.jpg: [CHARACTER: ref_basho][SETTING: ref_fukagawa][PROP: ref_staff]Silent meditation.";
      const [beat] = parsePromptsFile(input);
      expect(beat.prompt).toBe("Silent meditation.");
      expect(beat.character).toEqual(["ref_basho"]);
      expect(beat.ingredients).toEqual(["ref_fukagawa", "ref_staff"]);
    });

    it("skips beats that contain only tags and no actual scene prompt", () => {
      const input = "beat_05.jpg: [CHARACTER: ref_basho] [SETTING: ref_fukagawa]\nbeat_06.jpg: Valid prompt.";
      const beats = parsePromptsFile(input);
      expect(beats).toHaveLength(1);
      expect(beats[0].id).toBe("beat_06");
      expect(beats[0].prompt).toBe("Valid prompt.");
    });

    it("preserves non-tag bracketed text in prompt body", () => {
      const input = "beat_07.jpg: [CHARACTER: ref_basho] A traveler [carrying a woven basket] walks through the gate.";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref_basho"]);
      expect(beat.prompt).toBe("A traveler [carrying a woven basket] walks through the gate.");
    });

    it("preserves non-ASCII / Unicode Japanese text without corruption", () => {
      const input = "beat_08.jpg: [CHARACTER: ref_basho] 静けさや岩にしみ入る蝉の声。芭蕉の句。";
      const [beat] = parsePromptsFile(input);
      expect(beat.character).toEqual(["ref_basho"]);
      expect(beat.prompt).toBe("静けさや岩にしみ入る蝉の声。芭蕉の句。");
    });
  });
});
