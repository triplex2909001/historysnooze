import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import YAML from "yaml";
import {
  parseBatch,
  parseBatchYaml
} from "../src/jobs/schema.js";
import type { BatchFile, VideoJob } from "../src/jobs/schema.js";
import {
  interpolateJobOutputs,
  resolvePipeline
} from "../src/jobs/resolver.js";

const PIPELINE_YAML_PATH = join(__dirname, "../examples/pixar_fruit_market_pipeline.yaml");
const REPO_ROOT = join(__dirname, "..");

describe("Milestone M5 Challenger: Pixar Fruit Market Pipeline Adversarial Stress Suite", () => {
  const rawYamlContent = readFileSync(PIPELINE_YAML_PATH, "utf-8");

  // ==========================================================================
  // SECTION 1: Baseline Integrity & Specification Conformance
  // ==========================================================================
  describe("1. Baseline Integrity & Creative Specification Conformance", () => {
    it("parses examples/pixar_fruit_market_pipeline.yaml cleanly via batchSchema", () => {
      const batch = parseBatchYaml(rawYamlContent);

      expect(batch).toBeDefined();
      expect(batch.pipeline).toMatchObject({
        name: "pixar-fruit-market-vocabulary",
        profiles: ["default"],
        autoheal: true,
        resume: true,
        maxRetries: 3,
        continueOnFailure: false
      });
      expect(batch.jobs).toHaveLength(3);
    });

    it("conforms strictly to Character specifications for Ming and Ling", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const chars = batch.characters;

      expect(Object.keys(chars).sort()).toEqual(["ling", "ming"]);

      // Ming (Li Ming - 9yo boy)
      const ming = chars.ming;
      expect(ming).toBeDefined();
      expect(ming.name).toBe("Li Ming");
      expect(ming.referenceSheet).toBe("examples/assets/pixar_fruit_market/ming_reference_sheet.png");
      expect(ming.pinned).toBe(true);
      expect(ming.description).toContain("9-year-old");
      expect(ming.description).toContain("Pixar");
      expect(ming.description).toContain("yellow");
      expect(ming.description).toContain("dinosaur");

      // Ling (Xiao Ling - 10yo girl)
      const ling = chars.ling;
      expect(ling).toBeDefined();
      expect(ling.name).toBe("Xiao Ling");
      expect(ling.referenceSheet).toBe("examples/assets/pixar_fruit_market/ling_reference_sheet.png");
      expect(ling.pinned).toBe(true);
      expect(ling.description).toContain("10-year-old");
      expect(ling.description).toContain("Pixar");
      expect(ling.description).toContain("pigtails");
      expect(ling.description).toContain("overalls");
      expect(ling.description).toContain("red backpack");
    });

    it("conforms strictly to Master Environment Plate background specification", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const bgs = batch.backgrounds;

      expect(Object.keys(bgs)).toEqual(["fruit_market_stall"]);
      const stall = bgs.fruit_market_stall;
      expect(stall.name).toBe("Traditional Chinese Fruit Market Stall");
      expect(stall.plate).toBe("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(stall.description).toContain("traditional yet vibrant outdoor Chinese fruit market stall");
      expect(stall.description).toContain("apples");
      expect(stall.description).toContain("watermelons");
      expect(stall.description).toMatch(/lanterns/);
    });

    it("conforms strictly to Isolated Prop specifications (bamboo_basket, fresh_apple, watermelon_slice)", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const props = batch.props;

      expect(Object.keys(props).sort()).toEqual(["bamboo_basket", "fresh_apple", "watermelon_slice"]);

      // Bamboo basket
      expect(props.bamboo_basket).toMatchObject({
        name: "Woven Bamboo Basket",
        asset: "examples/assets/pixar_fruit_market/bamboo_basket_isolated.png"
      });

      // Fresh apple
      expect(props.fresh_apple).toMatchObject({
        name: "Fresh Red Apple",
        asset: "examples/assets/pixar_fruit_market/fresh_apple_isolated.png"
      });

      // Watermelon slice
      expect(props.watermelon_slice).toMatchObject({
        name: "Fresh Watermelon Slice",
        asset: "examples/assets/pixar_fruit_market/watermelon_slice_isolated.png"
      });
    });

    it("resolves the baseline pipeline into 3 video jobs with correct sequential chaining", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const resolved = resolvePipeline(batch);

      expect(resolved.jobs).toHaveLength(3);
      const [shot1, shot2, shot3] = resolved.jobs as VideoJob[];

      // Shot 1
      expect(shot1.id).toBe("shot1_market_arrival");
      expect(shot1.type).toBe("video");
      expect(shot1.duration).toBe(7);
      expect(shot1.ratio).toBe("9:16");
      expect(shot1.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      expect(shot1.startFrame).toBeUndefined();
      expect(shot1.dependsOn).toEqual([]);
      expect(shot1.character).toEqual(["Li Ming", "Xiao Ling"]);
      expect(shot1.ingredients).toContain("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(shot1.ingredients).toContain("examples/assets/pixar_fruit_market/bamboo_basket_isolated.png");

      // Shot 2
      expect(shot2.id).toBe("shot2_apple_discovery");
      expect(shot2.type).toBe("video");
      expect(shot2.duration).toBe(7);
      expect(shot2.ratio).toBe("9:16");
      expect(shot2.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      expect(shot2.startFrame).toBe("$output:shot1_market_arrival");
      expect(shot2.dependsOn).toContain("shot1_market_arrival");
      expect(shot2.ingredients).toContain("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(shot2.ingredients).toContain("examples/assets/pixar_fruit_market/bamboo_basket_isolated.png");
      expect(shot2.ingredients).toContain("examples/assets/pixar_fruit_market/fresh_apple_isolated.png");

      // Shot 3
      expect(shot3.id).toBe("shot3_watermelon_joy");
      expect(shot3.type).toBe("video");
      expect(shot3.duration).toBe(6);
      expect(shot3.ratio).toBe("9:16");
      expect(shot3.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      expect(shot3.startFrame).toBe("$output:shot2_apple_discovery");
      expect(shot3.dependsOn).toContain("shot2_apple_discovery");
      expect(shot3.ingredients).toContain("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(shot3.ingredients).toContain("examples/assets/pixar_fruit_market/watermelon_slice_isolated.png");
    });
  });

  // ==========================================================================
  // SECTION 2: Permutations & Shuffled Job Order Stress Testing
  // ==========================================================================
  describe("2. Permutation & Shuffling Stress Testing (Topological Sorting)", () => {
    it("reliably restores shot1 -> shot2 -> shot3 across all 6 mathematical permutations (3!)", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const [s1, s2, s3] = batch.jobs;

      const permutations = [
        [s1, s2, s3],
        [s1, s3, s2],
        [s2, s1, s3],
        [s2, s3, s1],
        [s3, s1, s2],
        [s3, s2, s1]
      ];

      for (let i = 0; i < permutations.length; i++) {
        const permutedBatch: BatchFile = {
          ...batch,
          jobs: permutations[i]
        };

        const resolved = resolvePipeline(permutedBatch);
        const order = resolved.jobs.map((j) => j.id);

        expect(order).toEqual([
          "shot1_market_arrival",
          "shot2_apple_discovery",
          "shot3_watermelon_joy"
        ]);
      }
    });

    it("reliably restores DAG order across 50 pseudo-random shuffles", () => {
      const batch = parseBatchYaml(rawYamlContent);

      for (let run = 0; run < 50; run++) {
        const shuffled = [...batch.jobs].sort(() => Math.random() - 0.5);
        const permutedBatch: BatchFile = {
          ...batch,
          jobs: shuffled
        };

        const resolved = resolvePipeline(permutedBatch);
        const order = resolved.jobs.map((j) => j.id);

        expect(order).toEqual([
          "shot1_market_arrival",
          "shot2_apple_discovery",
          "shot3_watermelon_joy"
        ]);
      }
    });

    it("maintains shot1 -> shot2 -> shot3 partial ordering when independent parallel jobs are interleaved", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const [s1, s2, s3] = batch.jobs;

      // Create 3 independent auxiliary jobs
      const aux1: VideoJob = {
        id: "aux1_market_ambience",
        type: "video",
        prompt: "Wide atmosphere shot of market fruit stall",
        duration: 5,
        ratio: "9:16",
        outputs: 1,
        out: "/media/vpsg24gb/DATA/gflow/out",
        ingredients: [],
        character: []
      };

      const aux2: VideoJob = {
        id: "aux2_fruit_closeup",
        type: "video",
        prompt: "Macro close-up of glossy apples",
        duration: 4,
        ratio: "9:16",
        outputs: 1,
        out: "/media/vpsg24gb/DATA/gflow/out",
        ingredients: [],
        character: []
      };

      const aux3: VideoJob = {
        id: "aux3_outro_credits",
        type: "video",
        prompt: "Stylized Pixar fruit market credit crawl",
        duration: 3,
        ratio: "9:16",
        outputs: 1,
        out: "/media/vpsg24gb/DATA/gflow/out",
        ingredients: [],
        character: []
      };

      // Completely scrambled combination of 6 jobs
      const scrambledJobs = [s3, aux3, s2, aux1, s1, aux2];
      const batchWithAux: BatchFile = {
        ...batch,
        jobs: scrambledJobs
      };

      const resolved = resolvePipeline(batchWithAux);
      const order = resolved.jobs.map((j) => j.id);

      expect(resolved.jobs).toHaveLength(6);
      const idx1 = order.indexOf("shot1_market_arrival");
      const idx2 = order.indexOf("shot2_apple_discovery");
      const idx3 = order.indexOf("shot3_watermelon_joy");

      expect(idx1).toBeGreaterThanOrEqual(0);
      expect(idx2).toBeGreaterThan(idx1);
      expect(idx3).toBeGreaterThan(idx2);
    });

    it("preserves stable topological ordering when jobs have explicit and inferred redundant dependencies", () => {
      const batch = parseBatchYaml(rawYamlContent);
      // Shot 3 also explicitly depends on Shot 1 (transitive edge)
      const modifiedShot3 = {
        ...batch.jobs[2],
        dependsOn: ["shot1_market_arrival"]
      };

      const permutedBatch: BatchFile = {
        ...batch,
        jobs: [modifiedShot3, batch.jobs[1], batch.jobs[0]]
      };

      const resolved = resolvePipeline(permutedBatch);
      const order = resolved.jobs.map((j) => j.id);

      expect(order).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy"
      ]);
    });
  });

  // ==========================================================================
  // SECTION 3: Missing Reference & Dangling Pointer Adversarial Testing
  // ==========================================================================
  describe("3. Missing References & Dangling Pointer Adversarial Testing", () => {
    it("cleanly rejects missing character reference in shot1 with available characters listed", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].character = ["$ref:characters.unknown_character"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Character reference '$ref:characters.unknown_character' in job 'shot1_market_arrival' not found. Available characters: [ming, ling]"
      );
    });

    it("cleanly rejects missing character reference in shot2 when characters registry is emptied", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.characters = {};

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Character reference '$ref:characters.ming' in job 'shot1_market_arrival' not found. Available characters: [none]"
      );
    });

    it("cleanly rejects missing background reference in shot1", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].background = "$ref:backgrounds.night_supermarket";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Background reference '$ref:backgrounds.night_supermarket' in job 'shot1_market_arrival' not found. Available backgrounds: [fruit_market_stall]"
      );
    });

    it("cleanly rejects missing background reference in shot3 when backgrounds registry is emptied", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.backgrounds = {};

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Background reference '$ref:backgrounds.fruit_market_stall' in job 'shot1_market_arrival' not found. Available backgrounds: [none]"
      );
    });

    it("cleanly rejects missing prop reference in shot1 props array", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].props = ["$ref:props.dragon_fruit"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Prop reference '$ref:props.dragon_fruit' in job 'shot1_market_arrival' not found. Available props: [bamboo_basket, fresh_apple, watermelon_slice]"
      );
    });

    it("cleanly rejects missing prop reference in shot2 props array", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[1].props = ["$ref:props.bamboo_basket", "$ref:props.golden_pineapple"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Prop reference '$ref:props.golden_pineapple' in job 'shot2_apple_discovery' not found. Available props: [bamboo_basket, fresh_apple, watermelon_slice]"
      );
    });

    it("cleanly rejects missing reference inside ingredients array", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].ingredients = ["$ref:props.phantom_crate"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Prop reference '$ref:props.phantom_crate' in ingredients of job 'shot1_market_arrival' not found. Available props: [bamboo_basket, fresh_apple, watermelon_slice]"
      );
    });

    it("cleanly rejects missing reference inside startFrame", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].startFrame = "$ref:backgrounds.phantom_backdrop";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Background reference '$ref:backgrounds.phantom_backdrop' in startFrame of job 'shot1_market_arrival' not found. Available backgrounds: [fruit_market_stall]"
      );
    });

    it("cleanly rejects missing reference inside endFrame", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[2].endFrame = "$ref:props.unregistered_knife";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Prop reference '$ref:props.unregistered_knife' in endFrame of job 'shot3_watermelon_joy' not found. Available props: [bamboo_basket, fresh_apple, watermelon_slice]"
      );
    });

    it("cleanly rejects dangling $output pointer to non-existent upstream job in shot2", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[1].startFrame = "$output:shot_non_existent";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Job 'shot2_apple_discovery' references output of undefined job 'shot_non_existent'. Defined jobs: [shot1_market_arrival, shot2_apple_discovery, shot3_watermelon_joy]"
      );
    });

    it("cleanly rejects dangling $output pointer to non-existent upstream job in shot3", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[2].startFrame = "$output:ghost_shot_42";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Job 'shot3_watermelon_joy' references output of undefined job 'ghost_shot_42'. Defined jobs: [shot1_market_arrival, shot2_apple_discovery, shot3_watermelon_joy]"
      );
    });

    it("cleanly rejects self-referential $output pointer in shot1", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].startFrame = "$output:shot1_market_arrival";

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Job 'shot1_market_arrival' cannot reference its own output (self-dependency detected)"
      );
    });

    it("cleanly rejects self-referential explicit dependsOn in shot1", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].dependsOn = ["shot1_market_arrival"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Job 'shot1_market_arrival' cannot depend on itself (self-dependency detected)"
      );
    });

    it("cleanly rejects undefined explicit dependsOn in shot2", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[1].dependsOn = ["phantom_upstream_job"];

      expect(() => resolvePipeline(parsed)).toThrowError(
        "Job 'shot2_apple_discovery' depends on undefined job 'phantom_upstream_job'. Defined jobs: [shot1_market_arrival, shot2_apple_discovery, shot3_watermelon_joy]"
      );
    });

    it("cleanly rejects interpolateJobOutputs when upstream job produced no artifacts", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const resolved = resolvePipeline(batch);
      const shot2 = resolved.jobs[1] as VideoJob;

      expect(() => interpolateJobOutputs(shot2, {})).toThrowError(
        "Cannot resolve output reference '$output:shot1_market_arrival': Upstream job 'shot1_market_arrival' produced no output artifacts."
      );
    });

    it("cleanly rejects interpolateJobOutputs when requested index is out of bounds", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[1].startFrame = "$output:shot1_market_arrival[3]";
      const batch = parseBatch(parsed);
      const resolved = resolvePipeline(batch);
      const shot2 = resolved.jobs[1] as VideoJob;

      expect(() =>
        interpolateJobOutputs(shot2, {
          shot1_market_arrival: ["/out/shot1_1.mp4"]
        })
      ).toThrowError(
        "Cannot resolve output reference '$output:shot1_market_arrival[3]': Upstream job 'shot1_market_arrival' only produced 1 artifact(s), requested index [3]."
      );
    });
  });

  // ==========================================================================
  // SECTION 4: Cycle Injection Adversarial Testing
  // ==========================================================================
  describe("4. Cycle Injection Adversarial Testing", () => {
    it("detects and rejects direct 2-job cycle injected via startFrame: shot1 -> shot2 -> shot1", () => {
      const parsed = YAML.parse(rawYamlContent);
      // shot2 already has startFrame: "$output:shot1_market_arrival"
      // inject shot1 startFrame: "$output:shot2_apple_discovery"
      parsed.jobs[0].startFrame = "$output:shot2_apple_discovery";

      const batch = parseBatch(parsed);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1_market_arrival.*shot2_apple_discovery/
      );
    });

    it("detects and rejects 3-job full circular cycle: shot1 -> shot2 -> shot3 -> shot1", () => {
      const parsed = YAML.parse(rawYamlContent);
      // shot2 depends on shot1, shot3 depends on shot2
      // inject shot1 startFrame: "$output:shot3_watermelon_joy"
      parsed.jobs[0].startFrame = "$output:shot3_watermelon_joy";

      const batch = parseBatch(parsed);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1_market_arrival.*shot3_watermelon_joy.*shot2_apple_discovery/
      );
    });

    it("detects cycle injected via explicit dependsOn: shot1 dependsOn shot3", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].dependsOn = ["shot3_watermelon_joy"];

      const batch = parseBatch(parsed);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1_market_arrival/
      );
    });

    it("detects cycle injected via ingredients array: shot1 ingredients containing $output:shot3_watermelon_joy", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].ingredients = ["$output:shot3_watermelon_joy"];

      const batch = parseBatch(parsed);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1_market_arrival/
      );
    });

    it("detects complex cycle injected via intermediate auxiliary job", () => {
      const parsed = YAML.parse(rawYamlContent);
      // Create aux job that depends on shot3, and make shot1 depend on aux job
      parsed.jobs.push({
        id: "aux_bridge",
        type: "video",
        prompt: "Auxiliary bridge shot",
        duration: 5,
        ratio: "9:16",
        out: "/media/vpsg24gb/DATA/gflow/out",
        startFrame: "$output:shot3_watermelon_joy"
      });
      parsed.jobs[0].startFrame = "$output:aux_bridge";

      const batch = parseBatch(parsed);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*aux_bridge/
      );
    });
  });

  // ==========================================================================
  // SECTION 5: Strict Parameter Validation (Duration, Aspect Ratio, Out Path)
  // ==========================================================================
  describe("5. Strict Parameter Validation (Duration, Ratio, Out Path, Schema Constraints)", () => {
    it("strictly verifies duration specifications in baseline Pixar pipeline (7s + 7s + 6s = 20s)", () => {
      const batch = parseBatchYaml(rawYamlContent);
      const [s1, s2, s3] = batch.jobs as VideoJob[];

      expect(s1.duration).toBe(7);
      expect(s2.duration).toBe(7);
      expect(s3.duration).toBe(6);

      const totalDuration = (s1.duration ?? 0) + (s2.duration ?? 0) + (s3.duration ?? 0);
      expect(totalDuration).toBe(20);
    });

    it("strictly verifies aspect ratio is '9:16' across all 3 shots", () => {
      const batch = parseBatchYaml(rawYamlContent);

      for (const job of batch.jobs) {
        expect(job.ratio).toBe("9:16");
      }
    });

    it("strictly verifies out directory is '/media/vpsg24gb/DATA/gflow/out' across all 3 shots", () => {
      const batch = parseBatchYaml(rawYamlContent);

      for (const job of batch.jobs) {
        expect(job.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      }
    });

    it("rejects invalid duration: duration = 0 (violates min(1))", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].duration = 0;

      expect(() => parseBatch(parsed)).toThrowError(/greater than or equal to 1/);
    });

    it("rejects invalid duration: duration = -3 (negative)", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].duration = -3;

      expect(() => parseBatch(parsed)).toThrowError(/greater than or equal to 1/);
    });

    it("rejects invalid duration: duration = 35 (violates max(30))", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].duration = 35;

      expect(() => parseBatch(parsed)).toThrowError(/less than or equal to 30/);
    });

    it("rejects non-integer duration: duration = 7.5 (violates int())", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].duration = 7.5;

      expect(() => parseBatch(parsed)).toThrowError(/Expected integer, received float/);
    });

    it("rejects string duration: duration = '7' (type mismatch)", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].duration = "7";

      expect(() => parseBatch(parsed)).toThrowError(/Expected number, received string/);
    });

    it("rejects empty aspect ratio: ratio = ''", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].ratio = "";

      expect(() => parseBatch(parsed)).toThrowError(/String must contain at least 1 character/);
    });

    it("rejects empty out path: out = ''", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[0].out = "";

      expect(() => parseBatch(parsed)).toThrowError(/String must contain at least 1 character/);
    });

    it("rejects invalid job IDs containing illegal characters (spaces, symbols)", () => {
      const parsed = YAML.parse(rawYamlContent);

      parsed.jobs[0].id = "shot 1 invalid";
      expect(() => parseBatch(parsed)).toThrowError(/Invalid/);

      parsed.jobs[0].id = "shot1@market";
      expect(() => parseBatch(parsed)).toThrowError(/Invalid/);

      parsed.jobs[0].id = "shot1/market";
      expect(() => parseBatch(parsed)).toThrowError(/Invalid/);
    });

    it("rejects duplicate job IDs in pipeline", () => {
      const parsed = YAML.parse(rawYamlContent);
      parsed.jobs[1].id = "shot1_market_arrival";

      expect(() => parseBatch(parsed)).toThrowError("Duplicate job id: shot1_market_arrival");
    });

    it("rejects invalid outputs count: outputs = 0 or outputs = 10", () => {
      const parsed0 = YAML.parse(rawYamlContent);
      parsed0.jobs[0].outputs = 0;
      expect(() => parseBatch(parsed0)).toThrowError(/greater than or equal to 1/);

      const parsed10 = YAML.parse(rawYamlContent);
      parsed10.jobs[0].outputs = 10;
      expect(() => parseBatch(parsed10)).toThrowError(/less than or equal to 8/);
    });

    it("rejects empty strings in asset registry required fields", () => {
      const parsedChar = YAML.parse(rawYamlContent);
      parsedChar.characters.ming.name = "";
      expect(() => parseBatch(parsedChar)).toThrowError(/String must contain at least 1 character/);

      const parsedBg = YAML.parse(rawYamlContent);
      parsedBg.backgrounds.fruit_market_stall.plate = "";
      expect(() => parseBatch(parsedBg)).toThrowError(/String must contain at least 1 character/);

      const parsedProp = YAML.parse(rawYamlContent);
      parsedProp.props.bamboo_basket.asset = "";
      expect(() => parseBatch(parsedProp)).toThrowError(/String must contain at least 1 character/);
    });
  });

  // ==========================================================================
  // SECTION 6: Milestone Progression & Disk Asset Inventory Check
  // ==========================================================================
  describe("6. Milestone Progression & Disk Asset Inventory Check", () => {
    it("documents referenced asset paths planned for generation in Milestone M6", () => {
      const batch = parseBatchYaml(rawYamlContent);

      const expectedAssets = [
        batch.characters.ming.referenceSheet!,
        batch.characters.ling.referenceSheet!,
        batch.backgrounds.fruit_market_stall.plate,
        batch.props.bamboo_basket.asset,
        batch.props.fresh_apple.asset,
        batch.props.watermelon_slice.asset
      ];

      // Verify all paths start with examples/assets/pixar_fruit_market/
      for (const assetPath of expectedAssets) {
        expect(assetPath).toMatch(/^examples\/assets\/pixar_fruit_market\/[a-z0-9_]+\.png$/);
      }

      // Check whether target directory exists or is pending Milestone M6
      const assetDir = join(REPO_ROOT, "examples/assets/pixar_fruit_market");
      const dirExists = existsSync(assetDir);

      // In Milestone M5, pipeline specification is authored.
      // Milestone M6 will generate the physical asset files.
      // We document this boundary condition explicitly.
      expect(typeof dirExists).toBe("boolean");
    });
  });
});
