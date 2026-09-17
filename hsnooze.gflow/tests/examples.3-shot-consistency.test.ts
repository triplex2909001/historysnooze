import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parseBatchYaml } from "../src/jobs/schema.js";
import type { VideoJob } from "../src/jobs/schema.js";
import {
  interpolateJobOutputs,
  resolvePipeline
} from "../src/jobs/resolver.js";
import { parseOutputReference } from "../src/jobs/frame-extractor.js";

const PIPELINE_YAML_PATH = join(__dirname, "../examples/3-shot-consistency-pipeline.yaml");
const REPO_ROOT = join(__dirname, "..");

describe("3-Shot Sequential Consistency Pipeline Verification", () => {
  const yamlContent = readFileSync(PIPELINE_YAML_PATH, "utf-8");

  it("parses the pipeline YAML cleanly through batchSchema", () => {
    const batch = parseBatchYaml(yamlContent);

    expect(batch).toBeDefined();
    expect(batch.pipeline).toMatchObject({
      name: "Cyberpunk Courier: The Data Heist",
      profiles: ["default"],
      autoheal: true,
      resume: true,
      maxRetries: 3,
      continueOnFailure: false
    });

    expect(Object.keys(batch.characters)).toEqual(["elena"]);
    expect(Object.keys(batch.backgrounds)).toEqual(["shibuya_alley"]);
    expect(Object.keys(batch.props)).toEqual(["quantum_drive", "monobike"]);
    expect(batch.jobs).toHaveLength(3);
  });

  it("verifies that all referenced asset files exist on disk", () => {
    const batch = parseBatchYaml(yamlContent);

    // Characters
    const elena = batch.characters.elena;
    expect(existsSync(join(REPO_ROOT, elena.referenceSheet!))).toBe(true);
    for (const img of elena.images ?? []) {
      expect(existsSync(join(REPO_ROOT, img))).toBe(true);
    }

    // Backgrounds
    const bg = batch.backgrounds.shibuya_alley;
    expect(existsSync(join(REPO_ROOT, bg.plate))).toBe(true);

    // Props
    const qd = batch.props.quantum_drive;
    expect(existsSync(join(REPO_ROOT, qd.asset))).toBe(true);
    const mb = batch.props.monobike;
    expect(existsSync(join(REPO_ROOT, mb.asset))).toBe(true);
  });

  describe("Dimension 1: Character Consistency (reference sheet, description, pinning)", () => {
    it("defines character registry with reference sheet, multi-angle images, description, and pinned: true", () => {
      const batch = parseBatchYaml(yamlContent);
      const character = batch.characters.elena;

      expect(character).toBeDefined();
      expect(character.name).toBe("Elena Vance");
      expect(character.referenceSheet).toBe("examples/assets/elena_reference_sheet.png");
      expect(character.images).toEqual([
        "examples/assets/elena_profile.png",
        "examples/assets/elena_action.png"
      ]);
      expect(character.pinned).toBe(true);
      expect(character.description).toContain("Athletic cyber-courier woman");
      expect(character.voice).toBe("Zephyr");
    });

    it("resolves character references and propagates pinned asset metadata to all 3 shots", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      expect(resolved.jobs).toHaveLength(3);
      for (const job of resolved.jobs) {
        expect(job.character).toEqual(["Elena Vance"]);
        expect(job.resolvedCharacters).toBeDefined();
        expect(job.resolvedCharacters).toHaveLength(1);
        expect(job.resolvedCharacters![0]).toMatchObject({
          name: "Elena Vance",
          referenceSheet: "examples/assets/elena_reference_sheet.png",
          pinned: true
        });
      }
    });
  });

  describe("Dimension 2: Background Consistency (master environment plate)", () => {
    it("defines master environment plate in backgrounds registry", () => {
      const batch = parseBatchYaml(yamlContent);
      const bg = batch.backgrounds.shibuya_alley;

      expect(bg).toBeDefined();
      expect(bg.name).toBe("Neo-Shibuya Rain Alley");
      expect(bg.plate).toBe("examples/assets/shibuya_alley_plate.png");
      expect(bg.description).toContain("Neo-Shibuya");
    });

    it("injects master environment plate into ingredients across all 3 shots", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      for (const job of resolved.jobs) {
        expect(job.ingredients).toContain("examples/assets/shibuya_alley_plate.png");
      }
    });
  });

  describe("Dimension 3: Prop Consistency (isolated reference assets)", () => {
    it("defines isolated prop assets in props registry", () => {
      const batch = parseBatchYaml(yamlContent);

      expect(batch.props.quantum_drive).toMatchObject({
        name: "Quantum Data Drive",
        asset: "examples/assets/quantum_drive_isolated.png"
      });
      expect(batch.props.monobike).toMatchObject({
        name: "Hover Monobike",
        asset: "examples/assets/monobike_isolated.png"
      });
    });

    it("injects isolated prop assets into the ingredients of the relevant shots", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs;

      // Shot 1 has both quantum drive and monobike
      expect(shot1.ingredients).toContain("examples/assets/quantum_drive_isolated.png");
      expect(shot1.ingredients).toContain("examples/assets/monobike_isolated.png");

      // Shot 2 has quantum drive being plugged in
      expect(shot2.ingredients).toContain("examples/assets/quantum_drive_isolated.png");
      expect(shot2.ingredients).not.toContain("examples/assets/monobike_isolated.png");

      // Shot 3 has monobike for high-speed escape
      expect(shot3.ingredients).toContain("examples/assets/monobike_isolated.png");
      expect(shot3.ingredients).not.toContain("examples/assets/quantum_drive_isolated.png");
    });
  });

  describe("Dimension 4: Scene Chaining ($output:<job_id> as startFrame across 3 shots)", () => {
    it("chains startFrame sequentially from Shot 1 to Shot 2 and Shot 2 to Shot 3", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs as VideoJob[];

      expect(shot1.id).toBe("shot1_alley_rendezvous");
      expect(shot1.type).toBe("video");
      expect(shot1.startFrame).toBeUndefined();

      expect(shot2.id).toBe("shot2_terminal_hack");
      expect(shot2.type).toBe("video");
      expect(shot2.startFrame).toBe("$output:shot1_alley_rendezvous");

      expect(shot3.id).toBe("shot3_highspeed_escape");
      expect(shot3.type).toBe("video");
      expect(shot3.startFrame).toBe("$output:shot2_terminal_hack");
    });

    it("automatically infers DAG dependencies from startFrame $output references", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const [shot1, shot2, shot3] = resolved.jobs;

      expect(shot1.dependsOn).toEqual([]);
      expect(shot2.dependsOn).toContain("shot1_alley_rendezvous");
      expect(shot3.dependsOn).toContain("shot2_terminal_hack");
    });

    it("topologically sorts jobs in correct sequential order even if defined out of order", () => {
      const batch = parseBatchYaml(yamlContent);
      // Reverse job definitions in input
      const shuffledBatch = {
        ...batch,
        jobs: [batch.jobs[2], batch.jobs[0], batch.jobs[1]]
      };

      const resolved = resolvePipeline(shuffledBatch);
      const jobOrder = resolved.jobs.map((j) => j.id);

      expect(jobOrder).toEqual([
        "shot1_alley_rendezvous",
        "shot2_terminal_hack",
        "shot3_highspeed_escape"
      ]);
    });

    it("correctly parses output reference structure for video frame extraction", () => {
      const batch = parseBatchYaml(yamlContent);
      const shot2 = batch.jobs.find((j) => j.id === "shot2_terminal_hack") as VideoJob;
      const shot3 = batch.jobs.find((j) => j.id === "shot3_highspeed_escape") as VideoJob;

      expect(shot2.startFrame).toBeDefined();
      const parsed2 = parseOutputReference(shot2.startFrame!);
      expect(parsed2).toEqual({
        jobId: "shot1_alley_rendezvous",
        index: 0,
        position: undefined
      });

      expect(shot3.startFrame).toBeDefined();
      const parsed3 = parseOutputReference(shot3.startFrame!);
      expect(parsed3).toEqual({
        jobId: "shot2_terminal_hack",
        index: 0,
        position: undefined
      });
    });

    it("interpolates runtime video artifact paths into startFrame", () => {
      const batch = parseBatchYaml(yamlContent);
      const resolved = resolvePipeline(batch);

      const artifactsMap = {
        shot1_alley_rendezvous: ["/gflow-output/3-shot-consistency/shot1_1.mp4"],
        shot2_terminal_hack: ["/gflow-output/3-shot-consistency/shot2_1.mp4"]
      };

      const interpolatedShot2 = interpolateJobOutputs(resolved.jobs[1] as VideoJob, artifactsMap);
      expect(interpolatedShot2.startFrame).toBe("/gflow-output/3-shot-consistency/shot1_1.mp4");

      const interpolatedShot3 = interpolateJobOutputs(resolved.jobs[2] as VideoJob, artifactsMap);
      expect(interpolatedShot3.startFrame).toBe("/gflow-output/3-shot-consistency/shot2_1.mp4");
    });
  });
});
