/**
 * Adversarial Stress Test Suite for GFlow CLI Tag Stripping & Parsing Logic.
 * Agent: challenger_m_a_1 (Empirical Challenger)
 * Tests hsnooze.gflow/dist/src/cli.js (parsePromptsFile).
 */

const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..");
const { parsePromptsFile } = require(path.join(REPO_ROOT, "hsnooze.gflow/dist/src/cli.js"));

console.log("=== Running GFlow Tag Stripping & Parsing Adversarial Tests ===");

// 1. Reference imageprompts file parsing (25 anchors)
function testReferencePromptsParsing() {
  console.log("1. Testing 25 Reference Prompts Parsing...");
  const refPath = path.join(REPO_ROOT, "hsnooze.gflow/reference_imageprompts.txt");
  const content = fs.readFileSync(refPath, "utf-8");
  const beats = parsePromptsFile(content);

  assert.strictEqual(beats.length, 25, `Expected 25 anchors, got ${beats.length}`);

  const expectedIds = [
    "ref_character_basho_young",
    "ref_character_basho_traveler",
    "ref_character_basho_elder",
    "ref_character_sora",
    "ref_character_buccho",
    "ref_setting_iga_ueno",
    "ref_setting_edo_nihonbashi",
    "ref_setting_fukagawa_interior",
    "ref_setting_fukagawa_exterior",
    "ref_setting_fuji_river_trail",
    "ref_setting_senju_dock",
    "ref_setting_nikko_cedars",
    "ref_setting_yamadera_temple",
    "ref_setting_mogami_river",
    "ref_setting_kisakata_lagoon",
    "ref_setting_shirakawa_barrier",
    "ref_setting_genjuan_bamboo",
    "ref_setting_kyoto_rakushisha",
    "ref_setting_tokaido_highway",
    "ref_setting_withered_moor",
    "ref_props_inkstone_brush",
    "ref_props_travel_gear",
    "ref_props_basho_leaves",
    "ref_props_tea_hearth_irori",
    "ref_props_travel_oi",
  ];

  const parsedIds = beats.map((b) => b.id);
  for (const exp of expectedIds) {
    assert(parsedIds.includes(exp), `Missing parsed anchor ID: ${exp}`);
  }

  for (const b of beats) {
    assert(!b.id.endsWith(".jpg"), `ID should not include extension: ${b.id}`);
    assert.strictEqual(b.character.length, 0, `Ref prompt should have no character tag: ${b.id}`);
    assert.strictEqual(b.ingredients.length, 0, `Ref prompt should have no ingredients: ${b.id}`);
    assert(!b.prompt.includes("["), `Unstripped bracket in prompt ${b.id}: ${b.prompt}`);
    assert(!b.prompt.includes("]"), `Unstripped bracket in prompt ${b.id}: ${b.prompt}`);
    assert(!/\s{2,}/.test(b.prompt), `Whitespace unnormalized in ${b.id}`);
    assert(b.prompt.length > 50, `Prompt suspiciously short for ${b.id}`);
  }
  console.log("   -> Passed: All 25 reference prompts cleanly parsed.");
}

// 2. Combined imageprompts file parsing (150 beats)
function testCombinedPromptsParsing() {
  console.log("2. Testing 150 Combined Beat Prompts Parsing...");
  const combPath = path.join(REPO_ROOT, "hsnooze.gflow/combined_imageprompts.txt");
  const content = fs.readFileSync(combPath, "utf-8");
  const beats = parsePromptsFile(content);

  assert.strictEqual(beats.length, 150, `Expected 150 beats, got ${beats.length}`);

  const partSettingMap = {
    1: "ref_setting_iga_ueno",
    2: "ref_setting_edo_nihonbashi",
    3: "ref_setting_fukagawa_interior",
    4: "ref_setting_fukagawa_exterior",
    5: "ref_setting_fuji_river_trail",
    6: "ref_setting_senju_dock",
    7: "ref_setting_nikko_cedars",
    8: "ref_setting_yamadera_temple",
    9: "ref_setting_mogami_river",
    10: "ref_setting_kisakata_lagoon",
    11: "ref_setting_shirakawa_barrier",
    12: "ref_setting_genjuan_bamboo",
    13: "ref_setting_kyoto_rakushisha",
    14: "ref_setting_tokaido_highway",
    15: "ref_setting_withered_moor",
  };

  for (let i = 0; i < beats.length; i++) {
    const b = beats[i];
    const partNum = Math.floor(i / 10) + 1;
    const beatNum = (i % 10) + 1;
    const expectedId = `beat_P${String(partNum).padStart(2, "0")}_B${String(beatNum).padStart(2, "0")}`;
    assert.strictEqual(b.id, expectedId, `Beat ID mismatch at index ${i}`);

    // Character life stage verification
    assert(b.character.length >= 1, `Missing character at ${b.id}`);
    if (partNum <= 2) {
      assert.strictEqual(b.character[0], "ref_character_basho_young", `P${partNum} should be basho_young`);
    } else if (partNum === 3 || partNum === 4 || partNum >= 12) {
      assert.strictEqual(b.character[0], "ref_character_basho_elder", `P${partNum} should be basho_elder`);
    } else if (partNum >= 5 && partNum <= 11) {
      if (b.id === "beat_P06_B04") {
        assert.strictEqual(b.character[0], "ref_character_sora", "P06_B04 should be sora");
      } else {
        assert.strictEqual(b.character[0], "ref_character_basho_traveler", `P${partNum} should be basho_traveler`);
      }
    }

    // Setting 1:1 verification
    const expectedSetting = partSettingMap[partNum];
    assert(
      b.ingredients.includes(expectedSetting),
      `Missing expected 1:1 setting ${expectedSetting} at ${b.id}, got ${b.ingredients}`
    );

    // Clean prompt verification
    assert(!b.prompt.includes("["), `Unstripped bracket in prompt ${b.id}: ${b.prompt}`);
    assert(!b.prompt.includes("]"), `Unstripped bracket in prompt ${b.id}: ${b.prompt}`);
    assert(!b.prompt.includes("CHARACTER:"), `Unstripped tag in ${b.id}`);
    assert(!b.prompt.includes("SETTING:"), `Unstripped tag in ${b.id}`);
    assert(!b.prompt.includes("PROP:"), `Unstripped tag in ${b.id}`);
    assert(!/\s{2,}/.test(b.prompt), `Double spaces in ${b.id}`);
    assert(b.prompt.trim() === b.prompt, `Leading/trailing whitespace in ${b.id}`);
    assert(b.prompt.length <= 1500, `Clean prompt exceeds 1500 chars in ${b.id}`);
  }
  console.log("   -> Passed: All 150 beats cleanly parsed and validated.");
}

// 3. Adversarial hostile inputs to parsePromptsFile
function testAdversarialInputs() {
  console.log("3. Testing Adversarial Hostile Inputs to GFlow Parser...");

  // Test 3.1: Stacking multiple tags back to back without space
  const input1 = "beat_P01_B01.jpg:[CHARACTER:ref_character_basho][SETTING:ref_setting_iga_ueno][PROP:ref_props_travel_gear]A solitary traveller.";
  const [b1] = parsePromptsFile(input1);
  assert(b1, "Failed to parse back-to-back tags");
  assert.deepStrictEqual(b1.character, ["ref_character_basho"]);
  assert.deepStrictEqual(b1.ingredients, ["ref_setting_iga_ueno", "ref_props_travel_gear"]);
  assert.strictEqual(b1.prompt, "A solitary traveller.");

  // Test 3.2: Plural tag variants
  const input2 = "beat_P02_B01.png: [CHARACTERS: ref_character_basho_young] [SETTINGS: ref_setting_edo_nihonbashi] [PROPS: ref_props_inkstone_brush] Edo bridge scene.";
  const [b2] = parsePromptsFile(input2);
  assert(b2);
  assert.deepStrictEqual(b2.character, ["ref_character_basho_young"]);
  assert.deepStrictEqual(b2.ingredients, ["ref_setting_edo_nihonbashi", "ref_props_inkstone_brush"]);
  assert.strictEqual(b2.prompt, "Edo bridge scene.");

  // Test 3.3: Case insensitivity
  const input3 = "beat_P03_B01.webp: [character: ref_character_basho_elder] [setting: ref_setting_fukagawa_interior] [prop: ref_props_tea_hearth_irori] Tea time.";
  const [b3] = parsePromptsFile(input3);
  assert(b3);
  assert.deepStrictEqual(b3.character, ["ref_character_basho_elder"]);
  assert.deepStrictEqual(b3.ingredients, ["ref_setting_fukagawa_interior", "ref_props_tea_hearth_irori"]);
  assert.strictEqual(b3.prompt, "Tea time.");

  // Test 3.4: Internal whitespace padding around tag values
  const input4 = "beat_P04_B01.jpeg:   [CHARACTER:   ref_character_basho_traveler   ]   [SETTING:   ref_setting_nikko_cedars   ]   Forest grove.   ";
  const [b4] = parsePromptsFile(input4);
  assert(b4);
  assert.deepStrictEqual(b4.character, ["ref_character_basho_traveler"]);
  assert.deepStrictEqual(b4.ingredients, ["ref_setting_nikko_cedars"]);
  assert.strictEqual(b4.prompt, "Forest grove.");

  // Test 3.5: Multiple colons in scene description
  const input5 = "beat_P05_B01.jpg: [CHARACTER: ref_basho] Time: 05:30: dawn: golden light shines through: mist.";
  const [b5] = parsePromptsFile(input5);
  assert(b5);
  assert.strictEqual(b5.prompt, "Time: 05:30: dawn: golden light shines through: mist.");

  // Test 3.6: Non-whitelisted bracketed annotations (should be preserved in prompt)
  const input6 = "beat_P06_B01.jpg: [CHARACTER: ref_basho] [SETTING: ref_senju] Scene with [16:9 canvas] aspect.";
  const [b6] = parsePromptsFile(input6);
  assert(b6);
  assert.strictEqual(b6.prompt, "Scene with [16:9 canvas] aspect.");

  // Test 3.7: Prompt with only tags and no descriptive text
  const input7 = "beat_P07_B01.jpg: [CHARACTER: ref_basho] [SETTING: ref_nikko]";
  const beats7 = parsePromptsFile(input7);
  assert.strictEqual(beats7.length, 0, "Beats with zero clean text should be omitted");

  // Test 3.8: Malformed lines: comments, missing colons, empty lines
  const input8 = `
  # Leading comment
  beat_P08_B01.jpg: [CHARACTER: ref_basho] Real beat.
  # Mid comment with colon: value
  corrupted_line_without_colon
  : colon_at_start_no_id
  beat_P08_B02.jpg:
  beat_P08_B03.jpg: [SETTING: ref_yamadera] Another real beat.
  `;
  const beats8 = parsePromptsFile(input8);
  assert.strictEqual(beats8.length, 2);
  assert.strictEqual(beats8[0].id, "beat_P08_B01");
  assert.strictEqual(beats8[1].id, "beat_P08_B03");

  console.log("   -> Passed: All adversarial hostile inputs handled safely without crashes.");
}

testReferencePromptsParsing();
testCombinedPromptsParsing();
testAdversarialInputs();

console.log("\nALL GFLOW ADVERSARIAL TESTS PASSED CLEANLY!");
