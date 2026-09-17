import { existsSync, readFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  parseBatchYaml,
  videoJobSchema,
  type VideoJob
} from "../src/jobs/schema.js";
import {
  interpolateJobOutputs,
  parseOutputRef,
  resolvePipeline
} from "../src/jobs/resolver.js";
import { parseOutputReference } from "../src/jobs/frame-extractor.js";
import { createProgram } from "../src/cli.js";
import type { FlowAutomation } from "../src/flow/types.js";

const PIPELINE_YAML_PATH = join(__dirname, "../examples/pixar_fruit_market_pipeline.yaml");

describe("M5.2 Pixar Fruit Market Pipeline: Empirical Ingestion & Boundary Challenge", () => {
  const yamlContent = readFileSync(PIPELINE_YAML_PATH, "utf-8");

  describe("1. Schema Ingestion & CLI Pipeline Resolution", () => {
    it("parses the pipeline YAML cleanly through batchSchema", () => {
      const batch = parseBatchYaml(yamlContent);

      expect(batch).toBeDefined();
      expect(batch.pipeline).toMatchObject({
        name: "pixar-fruit-market-vocabulary",
        profiles: ["default"],
        autoheal: true,
        resume: true,
        maxRetries: 3,
        continueOnFailure: false
      });

      expect(Object.keys(batch.characters).sort()).toEqual(["ling", "ming"]);
      expect(Object.keys(batch.backgrounds)).toEqual(["fruit_market_stall"]);
      expect(Object.keys(batch.props).sort()).toEqual([
        "bamboo_basket",
        "fresh_apple",
        "watermelon_slice"
      ]);
      expect(batch.jobs).toHaveLength(3);
    });

    it("verifies character registry conforms to 3D Pixar specs for Ming and Ling", () => {
      const batch = parseBatchYaml(yamlContent);

      const ming = batch.characters.ming;
      expect(ming).toBeDefined();
      expect(ming.name).toBe("Li Ming");
      expect(ming.referenceSheet).toBe("examples/assets/pixar_fruit_market/ming_reference_sheet.png");
      expect(ming.pinned).toBe(true);
      expect(ming.description).toContain("9-year-old Chinese boy");
      expect(ming.description).toContain("yellow");
      expect(ming.description).toContain("dinosaur");

      const ling = batch.characters.ling;
      expect(ling).toBeDefined();
      expect(ling.name).toBe("Xiao Ling");
      expect(ling.referenceSheet).toBe("examples/assets/pixar_fruit_market/ling_reference_sheet.png");
      expect(ling.pinned).toBe(true);
      expect(ling.description).toContain("10-year-old Chinese girl");
      expect(ling.description).toContain("twin pigtails");
      expect(ling.description).toContain("ribbon");
    });

    it("verifies background plate and isolated props registry", () => {
      const batch = parseBatchYaml(yamlContent);

      const bg = batch.backgrounds.fruit_market_stall;
      expect(bg).toBeDefined();
      expect(bg.name).toBe("Traditional Chinese Fruit Market Stall");
      expect(bg.plate).toBe("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(bg.description).toContain("苹果");
      expect(bg.description).toContain("西瓜");

      const props = batch.props;
      expect(props.bamboo_basket.name).toBe("Woven Bamboo Basket");
      expect(props.bamboo_basket.asset).toBe("examples/assets/pixar_fruit_market/bamboo_basket_isolated.png");

      expect(props.fresh_apple.name).toBe("Fresh Red Apple");
      expect(props.fresh_apple.asset).toBe("examples/assets/pixar_fruit_market/fresh_apple_isolated.png");

      expect(props.watermelon_slice.name).toBe("Fresh Watermelon Slice");
      expect(props.watermelon_slice.asset).toBe("examples/assets/pixar_fruit_market/watermelon_slice_isolated.png");
    });
  });

  describe("2. Output Paths & Directory Validation", () => {
    it("validates that all 3 jobs explicitly declare out as /media/vpsg24gb/DATA/gflow/out", () => {
      const batch = parseBatchYaml(yamlContent);

      for (const job of batch.jobs) {
        expect(job.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      }
    });

    it("preserves explicit out path through pipeline resolution", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      expect(resolved.jobs).toHaveLength(3);
      for (const job of resolved.jobs) {
        expect(job.out).toBe("/media/vpsg24gb/DATA/gflow/out");
      }
    });
  });

  describe("3. Duration Boundaries & 9:16 Aspect Ratio", () => {
    it("verifies exact duration boundaries: 7s, 7s, 6s summing to 20s", () => {
      const batch = parseBatchYaml(yamlContent);
      const [shot1, shot2, shot3] = batch.jobs as VideoJob[];

      expect(shot1.duration).toBe(7);
      expect(shot2.duration).toBe(7);
      expect(shot3.duration).toBe(6);

      const totalDuration = (shot1.duration ?? 0) + (shot2.duration ?? 0) + (shot3.duration ?? 0);
      expect(totalDuration).toBe(20);
    });

    it("verifies vertical 9:16 aspect ratio across all 3 shots", () => {
      const batch = parseBatchYaml(yamlContent);

      for (const job of batch.jobs) {
        expect(job.ratio).toBe("9:16");
        expect(job.type).toBe("video");
        expect(job.model).toBe("veo-3.1-fast");
        expect(job.outputs).toBe(1);
      }
    });

    it("enforces schema boundaries on duration: rejects 0 and >30, accepts 1-30", () => {
      const validJob = {
        id: "test-boundary",
        type: "video",
        prompt: "test",
        duration: 7,
        ratio: "9:16"
      };
      expect(() => videoJobSchema.parse(validJob)).not.toThrow();

      // Below lower bound
      expect(() =>
        videoJobSchema.parse({ ...validJob, duration: 0 })
      ).toThrow();

      // Negative duration
      expect(() =>
        videoJobSchema.parse({ ...validJob, duration: -5 })
      ).toThrow();

      // Above upper bound
      expect(() =>
        videoJobSchema.parse({ ...validJob, duration: 31 })
      ).toThrow();

      // Float duration (must be integer)
      expect(() =>
        videoJobSchema.parse({ ...validJob, duration: 7.5 })
      ).toThrow();
    });
  });

  describe("4. Multi-Layer Reference Resolution & Asset Pinning", () => {
    it("resolves characters to names and attaches character asset sheets with pinned: true", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      for (const job of resolved.jobs) {
        expect(job.character).toEqual(["Li Ming", "Xiao Ling"]);
        expect(job.resolvedCharacters).toHaveLength(2);

        const ming = job.resolvedCharacters!.find((c) => c.name === "Li Ming");
        expect(ming).toBeDefined();
        expect(ming!.pinned).toBe(true);
        expect(ming!.referenceSheet).toBe("examples/assets/pixar_fruit_market/ming_reference_sheet.png");

        const ling = job.resolvedCharacters!.find((c) => c.name === "Xiao Ling");
        expect(ling).toBeDefined();
        expect(ling!.pinned).toBe(true);
        expect(ling!.referenceSheet).toBe("examples/assets/pixar_fruit_market/ling_reference_sheet.png");
      }
    });

    it("injects master environment plate and isolated props into ingredients across shots", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs;

      const platePath = "examples/assets/pixar_fruit_market/fruit_market_stall_plate.png";
      const basketPath = "examples/assets/pixar_fruit_market/bamboo_basket_isolated.png";
      const applePath = "examples/assets/pixar_fruit_market/fresh_apple_isolated.png";
      const watermelonPath = "examples/assets/pixar_fruit_market/watermelon_slice_isolated.png";

      // Shot 1: stall + bamboo basket
      expect(shot1.ingredients).toContain(platePath);
      expect(shot1.ingredients).toContain(basketPath);
      expect(shot1.ingredients).not.toContain(applePath);
      expect(shot1.ingredients).not.toContain(watermelonPath);

      // Shot 2: stall + bamboo basket + fresh apple
      expect(shot2.ingredients).toContain(platePath);
      expect(shot2.ingredients).toContain(basketPath);
      expect(shot2.ingredients).toContain(applePath);
      expect(shot2.ingredients).not.toContain(watermelonPath);

      // Shot 3: stall + watermelon slice
      expect(shot3.ingredients).toContain(platePath);
      expect(shot3.ingredients).toContain(watermelonPath);
      expect(shot3.ingredients).not.toContain(applePath);
      expect(shot3.ingredients).not.toContain(basketPath);
    });
  });

  describe("5. Scene Chaining, DAG Ingestion & Topological Resolution", () => {
    it("chains startFrame sequentially from Shot 1 -> Shot 2 and Shot 2 -> Shot 3", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs as VideoJob[];

      expect(shot1.id).toBe("shot1_market_arrival");
      expect(shot1.startFrame).toBeUndefined();

      expect(shot2.id).toBe("shot2_apple_discovery");
      expect(shot2.startFrame).toBe("$output:shot1_market_arrival");

      expect(shot3.id).toBe("shot3_watermelon_joy");
      expect(shot3.startFrame).toBe("$output:shot2_apple_discovery");
    });

    it("correctly infers DAG dependencies from startFrame $output references", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs;

      expect(shot1.dependsOn).toEqual([]);
      expect(shot2.dependsOn).toEqual(["shot1_market_arrival"]);
      expect(shot3.dependsOn).toEqual(["shot2_apple_discovery"]);
    });

    it("topologically sorts jobs in correct sequential order even if defined out of order", () => {
      const batch = parseBatchYaml(yamlContent);
      // Scramble order: shot 3, shot 1, shot 2
      const scrambledBatch = {
        ...batch,
        jobs: [batch.jobs[2], batch.jobs[0], batch.jobs[1]]
      };

      const resolved = resolvePipeline(scrambledBatch);
      const jobOrder = resolved.jobs.map((j) => j.id);

      expect(jobOrder).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy"
      ]);
    });

    it("parses output references with parseOutputReference and parseOutputRef", () => {
      const batch = parseBatchYaml(yamlContent);
      const shot2 = batch.jobs[1] as VideoJob;
      const shot3 = batch.jobs[2] as VideoJob;

      expect(parseOutputReference(shot2.startFrame!)).toEqual({
        jobId: "shot1_market_arrival",
        index: 0,
        position: undefined
      });
      expect(parseOutputRef(shot2.startFrame!)).toEqual({
        jobId: "shot1_market_arrival",
        index: 0,
        position: undefined
      });

      expect(parseOutputReference(shot3.startFrame!)).toEqual({
        jobId: "shot2_apple_discovery",
        index: 0,
        position: undefined
      });
      expect(parseOutputRef(shot3.startFrame!)).toEqual({
        jobId: "shot2_apple_discovery",
        index: 0,
        position: undefined
      });
    });

    it("interpolates runtime video artifact paths into startFrame", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const artifactsMap = {
        shot1_market_arrival: ["/media/vpsg24gb/DATA/gflow/out/shot1_market_arrival.mp4"],
        shot2_apple_discovery: ["/media/vpsg24gb/DATA/gflow/out/shot2_apple_discovery.mp4"]
      };

      const interpolatedShot2 = interpolateJobOutputs(resolved.jobs[1] as VideoJob, artifactsMap);
      expect(interpolatedShot2.startFrame).toBe("/media/vpsg24gb/DATA/gflow/out/shot1_market_arrival.mp4");

      const interpolatedShot3 = interpolateJobOutputs(resolved.jobs[2] as VideoJob, artifactsMap);
      expect(interpolatedShot3.startFrame).toBe("/media/vpsg24gb/DATA/gflow/out/shot2_apple_discovery.mp4");
    });
  });

  describe("6. Adversarial Fault Injection & Schema Boundaries", () => {
    it("fails resolution when character reference is missing in registry", () => {
      const batch = parseBatchYaml(yamlContent);
      batch.jobs[0].character = ["$ref:characters.unknown_character"];

      expect(() => resolvePipeline(batch)).toThrow(
        /Character reference '\$ref:characters\.unknown_character' in job 'shot1_market_arrival' not found/
      );
    });

    it("fails resolution when background reference is missing in registry", () => {
      const batch = parseBatchYaml(yamlContent);
      batch.jobs[0].background = "$ref:backgrounds.unknown_background";

      expect(() => resolvePipeline(batch)).toThrow(
        /Background reference '\$ref:backgrounds\.unknown_background' in job 'shot1_market_arrival' not found/
      );
    });

    it("fails resolution when prop reference is missing in registry", () => {
      const batch = parseBatchYaml(yamlContent);
      batch.jobs[0].props = ["$ref:props.unknown_prop"];

      expect(() => resolvePipeline(batch)).toThrow(
        /Prop reference '\$ref:props\.unknown_prop' in job 'shot1_market_arrival' not found/
      );
    });

    it("fails resolution when startFrame references an undefined job", () => {
      const batch = parseBatchYaml(yamlContent);
      (batch.jobs[1] as VideoJob).startFrame = "$output:non_existent_shot";

      expect(() => resolvePipeline(batch)).toThrow(
        /references output of undefined job 'non_existent_shot'/
      );
    });

    it("detects and rejects circular dependency introduced into pipeline", () => {
      const batch = parseBatchYaml(yamlContent);
      // Introduce cycle: shot1 depends on shot3
      batch.jobs[0].dependsOn = ["shot3_watermelon_joy"];

      expect(() => resolvePipeline(batch)).toThrow(
        /Cyclic dependency detected in pipeline jobs/
      );
    });

    it("detects and rejects self-dependency", () => {
      const batch = parseBatchYaml(yamlContent);
      (batch.jobs[0] as VideoJob).startFrame = "$output:shot1_market_arrival";

      expect(() => resolvePipeline(batch)).toThrow(
        /cannot reference its own output \(self-dependency detected\)/
      );
    });
  });

  describe("7. CLI Execution Pathway Compatibility", () => {
    let tempDir: string;
    let sampleVideoPath: string;

    it("executes cleanly through createProgram CLI runner with mock automation and real frame extraction", async () => {
      const { promisify } = await import("node:util");
      const { execFile } = await import("node:child_process");
      const { copyFile } = await import("node:fs/promises");
      const execFileAsync = promisify(execFile);

      tempDir = await mkdtemp(join(tmpdir(), "pixar-cli-test-"));
      sampleVideoPath = join(tempDir, "sample.mp4");

      // Generate a small 1s synthetic video for real ffmpeg extraction
      await execFileAsync("ffmpeg", [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=160x120:rate=10",
        sampleVideoPath
      ]);

      const executedJobs: string[] = [];
      const automation: FlowAutomation = {
        runJob: vi.fn(async (input) => {
          executedJobs.push(input.job.id);
          const jobVideo = join(input.outDir, `${input.job.id}.mp4`);
          await copyFile(sampleVideoPath, jobVideo);

          return {
            jobId: input.job.id,
            artifacts: [
              {
                path: jobVideo,
                metadataPath: join(input.outDir, `${input.job.id}.json`)
              }
            ],
            flowUrl: "https://flow.google.com"
          };
        })
      };

      const program = createProgram({ automation });
      program.configureOutput({ writeErr: () => {}, writeOut: () => {} });

      // Execute through CLI run command with custom output-dir pointing to tempDir
      await program.parseAsync([
        "node",
        "gflow",
        "run",
        PIPELINE_YAML_PATH,
        "--no-checkpoint",
        "--output-dir",
        tempDir
      ]);

      expect(executedJobs).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy"
      ]);

      // Verify that frame extractor created frames in <tempDir>/frames/
      expect(existsSync(join(tempDir, "frames/shot1_market_arrival-last-frame.png"))).toBe(true);
      expect(existsSync(join(tempDir, "frames/shot2_apple_discovery-last-frame.png"))).toBe(true);

      await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
    });
  });
});
