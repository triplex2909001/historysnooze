import { describe, expect, it } from "vitest";
import { parseBatchYaml, parseVideoJob } from "../src/jobs/schema.js";
import type { VideoJob } from "../src/jobs/schema.js";
import {
  interpolateJobOutputs,
  resolveJobOrder,
  resolvePipeline
} from "../src/jobs/resolver.js";

describe("Milestone M4 Challenger Adversarial Suite", () => {
  // --------------------------------------------------------------------------
  // Task 2.1: Missing Character References ($ref:characters.missing)
  // --------------------------------------------------------------------------
  describe("Adversarial: Missing Character References", () => {
    it("throws a clear and descriptive error when referencing non-existent character in empty registry", () => {
      const yaml = `
jobs:
  - id: shot1
    type: image
    prompt: "Cyberpunk heroine standing in rain"
    character: $ref:characters.missing
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Character reference '$ref:characters.missing' in job 'shot1' not found. Available characters: [none]"
      );
    });

    it("throws a clear error listing available characters when referencing non-existent character in populated registry", () => {
      const yaml = `
characters:
  elena:
    name: "Elena Vance"
    referenceSheet: "examples/assets/elena_reference_sheet.png"
  marcus:
    name: "Marcus Cole"
jobs:
  - id: shot1
    type: image
    prompt: "Elena meets a stranger"
    character:
      - $ref:characters.elena
      - $ref:characters.ghost_operative
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Character reference '$ref:characters.ghost_operative' in job 'shot1' not found. Available characters: [elena, marcus]"
      );
    });
  });

  // --------------------------------------------------------------------------
  // Task 2.2: Missing Background References ($ref:backgrounds.missing)
  // --------------------------------------------------------------------------
  describe("Adversarial: Missing Background References", () => {
    it("throws a clear error when background convenience field references non-existent background", () => {
      const yaml = `
backgrounds:
  shibuya:
    name: "Shibuya Rain"
    plate: "assets/shibuya.png"
jobs:
  - id: shot1
    type: image
    prompt: "Street view"
    background: $ref:backgrounds.missing
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Background reference '$ref:backgrounds.missing' in job 'shot1' not found. Available backgrounds: [shibuya]"
      );
    });

    it("throws a clear error when ingredients array references non-existent background", () => {
      const yaml = `
jobs:
  - id: shot1
    type: image
    prompt: "Alleyway scene"
    ingredients:
      - $ref:backgrounds.phantom_alley
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Background reference '$ref:backgrounds.phantom_alley' in ingredients of job 'shot1' not found. Available backgrounds: [none]"
      );
    });

    it("throws a clear error when startFrame references non-existent background plate", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Pan across the skyline"
    startFrame: $ref:backgrounds.missing_skyline
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Background reference '$ref:backgrounds.missing_skyline' in startFrame of job 'shot1' not found. Available backgrounds: [none]"
      );
    });

    it("throws a clear error when endFrame references non-existent background plate", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Zoom into terminal"
    endFrame: $ref:backgrounds.missing_terminal
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Background reference '$ref:backgrounds.missing_terminal' in endFrame of job 'shot1' not found. Available backgrounds: [none]"
      );
    });
  });

  // --------------------------------------------------------------------------
  // Task 2.3: Missing Prop References ($ref:props.missing)
  // --------------------------------------------------------------------------
  describe("Adversarial: Missing Prop References", () => {
    it("throws a clear error when props convenience field references non-existent prop", () => {
      const yaml = `
props:
  quantum_drive:
    name: "Quantum Drive"
    asset: "assets/drive.png"
jobs:
  - id: shot1
    type: image
    prompt: "Elena inspects weapon"
    props:
      - $ref:props.plasma_rifle
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Prop reference '$ref:props.plasma_rifle' in job 'shot1' not found. Available props: [quantum_drive]"
      );
    });

    it("throws a clear error when ingredients array references non-existent prop", () => {
      const yaml = `
jobs:
  - id: shot1
    type: image
    prompt: "Elena with gear"
    ingredients:
      - $ref:props.missing_gadget
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Prop reference '$ref:props.missing_gadget' in ingredients of job 'shot1' not found. Available props: [none]"
      );
    });

    it("throws a clear error when startFrame references non-existent prop asset", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Focus on object"
    startFrame: $ref:props.unregistered_cube
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Prop reference '$ref:props.unregistered_cube' in startFrame of job 'shot1' not found. Available props: [none]"
      );
    });

    it("throws a clear error when endFrame references non-existent prop asset", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Focus on object end"
    endFrame: $ref:props.unregistered_cube
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Prop reference '$ref:props.unregistered_cube' in endFrame of job 'shot1' not found. Available props: [none]"
      );
    });
  });

  // --------------------------------------------------------------------------
  // Task 2.4: Cyclic Dependency Detection (shot1 -> shot2 -> shot1)
  // --------------------------------------------------------------------------
  describe("Adversarial: Cyclic Dependency Detection", () => {
    it("detects 2-shot cycle: shot1 -> shot2 -> shot1 via startFrame $output references", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "First shot"
    startFrame: $output:shot2
  - id: shot2
    type: video
    prompt: "Second shot"
    startFrame: $output:shot1
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1.*shot2/
      );
    });

    it("detects 2-shot cycle: shot1 -> shot2 -> shot1 via explicit dependsOn", () => {
      const yaml = `
jobs:
  - id: shot1
    type: image
    prompt: "Shot 1"
    dependsOn: [shot2]
  - id: shot2
    type: image
    prompt: "Shot 2"
    dependsOn: [shot1]
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        /Cyclic dependency detected in pipeline jobs:.*shot1.*shot2/
      );
    });

    it("detects direct self-cycle: shot1 referencing its own output in startFrame", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Self looping shot"
    startFrame: $output:shot1
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Job 'shot1' cannot reference its own output (self-dependency detected)"
      );
    });

    it("detects direct self-cycle: shot1 explicitly depending on shot1", () => {
      const yaml = `
jobs:
  - id: shot1
    type: image
    prompt: "Self dependent"
    dependsOn: [shot1]
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Job 'shot1' cannot depend on itself (self-dependency detected)"
      );
    });

    it("detects multi-shot loop: shot1 -> shot2 -> shot3 -> shot1 with exact cycle trace", () => {
      const yaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Shot 1"
    startFrame: $output:shot3
  - id: shot2
    type: video
    prompt: "Shot 2"
    startFrame: $output:shot1
  - id: shot3
    type: video
    prompt: "Shot 3"
    startFrame: $output:shot2
`;
      const batch = parseBatchYaml(yaml);
      expect(() => resolvePipeline(batch)).toThrowError(
        "Cyclic dependency detected in pipeline jobs: shot1 -> shot3 -> shot2 -> shot1"
      );
    });
  });

  // --------------------------------------------------------------------------
  // Task 2.5: Shuffled Dependencies & Deterministic Topological Sort
  // --------------------------------------------------------------------------
  describe("Adversarial: Shuffled Dependencies & Deterministic Topological Sort", () => {
    it("deterministically sorts linear chain [shot1, shot2, shot3] regardless of input permutations", () => {
      const originalYaml = `
jobs:
  - id: shot1
    type: video
    prompt: "Shot 1"
  - id: shot2
    type: video
    prompt: "Shot 2"
    startFrame: $output:shot1
  - id: shot3
    type: video
    prompt: "Shot 3"
    startFrame: $output:shot2
`;
      const batch = parseBatchYaml(originalYaml);

      // Permutation 1: [shot3, shot2, shot1]
      const perm1 = { ...batch, jobs: [batch.jobs[2], batch.jobs[1], batch.jobs[0]] };
      expect(resolvePipeline(perm1).jobs.map((j) => j.id)).toEqual(["shot1", "shot2", "shot3"]);

      // Permutation 2: [shot2, shot3, shot1]
      const perm2 = { ...batch, jobs: [batch.jobs[1], batch.jobs[2], batch.jobs[0]] };
      expect(resolvePipeline(perm2).jobs.map((j) => j.id)).toEqual(["shot1", "shot2", "shot3"]);

      // Permutation 3: [shot3, shot1, shot2]
      const perm3 = { ...batch, jobs: [batch.jobs[2], batch.jobs[0], batch.jobs[1]] };
      expect(resolvePipeline(perm3).jobs.map((j) => j.id)).toEqual(["shot1", "shot2", "shot3"]);
    });

    it("deterministically orders diamond DAG: root -> (branchA, branchB) -> merge", () => {
      const yaml = `
jobs:
  - id: merge
    type: video
    prompt: "Merge"
    startFrame: $output:branchA
    endFrame: $output:branchB
  - id: branchB
    type: image
    prompt: "Branch B"
    ingredients: [$output:root]
  - id: branchA
    type: image
    prompt: "Branch A"
    ingredients: [$output:root]
  - id: root
    type: image
    prompt: "Root"
`;
      const batch = parseBatchYaml(yaml);
      const resolved = resolvePipeline(batch);
      const order = resolved.jobs.map((j) => j.id);

      expect(order[0]).toBe("root");
      expect(order.indexOf("branchB")).toBeGreaterThan(order.indexOf("root"));
      expect(order.indexOf("branchA")).toBeGreaterThan(order.indexOf("root"));
      expect(order.indexOf("merge")).toBeGreaterThan(order.indexOf("branchA"));
      expect(order.indexOf("merge")).toBeGreaterThan(order.indexOf("branchB"));
    });

    it("preserves stable input order for independent parallel jobs", () => {
      const jobs = [
        { id: "alpha", type: "image" as const, prompt: "Alpha", out: ".", outputs: 1, ingredients: [], character: [] },
        { id: "beta", type: "image" as const, prompt: "Beta", out: ".", outputs: 1, ingredients: [], character: [] },
        { id: "gamma", type: "image" as const, prompt: "Gamma", out: ".", outputs: 1, ingredients: [], character: [] }
      ];

      const sorted = resolveJobOrder(jobs);
      expect(sorted.map((j) => j.id)).toEqual(["alpha", "beta", "gamma"]);

      const reversed = resolveJobOrder([...jobs].reverse());
      expect(reversed.map((j) => j.id)).toEqual(["gamma", "beta", "alpha"]);
    });
  });

  // --------------------------------------------------------------------------
  // Task 3: Edge Cases in Pipeline Asset Definitions
  // --------------------------------------------------------------------------
  describe("Edge Cases: Pipeline Asset Definitions", () => {
    describe("3.1 Empty Character Images Array", () => {
      it("accepts character with empty images array images: []", () => {
        const yaml = `
characters:
  minimal_char:
    name: "Minimalist"
    images: []
jobs:
  - id: shot1
    type: image
    prompt: "Minimal test"
    character: $ref:characters.minimal_char
`;
        const batch = parseBatchYaml(yaml);
        expect(batch.characters.minimal_char.images).toEqual([]);

        const resolved = resolvePipeline(batch);
        expect(resolved.characters.minimal_char.images).toEqual([]);
        expect(resolved.jobs[0].character).toEqual(["Minimalist"]);
        expect(resolved.jobs[0].resolvedCharacters![0].images).toEqual([]);
      });

      it("accepts character without images field (undefined / omitted)", () => {
        const yaml = `
characters:
  solo_sheet:
    name: "Solo Sheet Hero"
    referenceSheet: "assets/sheet.png"
jobs:
  - id: shot1
    type: image
    prompt: "Solo test"
    character: $ref:characters.solo_sheet
`;
        const batch = parseBatchYaml(yaml);
        expect(batch.characters.solo_sheet.images).toBeUndefined();

        const resolved = resolvePipeline(batch);
        expect(resolved.jobs[0].resolvedCharacters![0].images).toBeUndefined();
      });

      it("rejects character images array containing empty string (fails min(1) validation)", () => {
        const yaml = `
characters:
  broken_char:
    name: "Broken"
    images:
      - ""
jobs:
  - id: shot1
    type: image
    prompt: "Broken test"
`;
        expect(() => parseBatchYaml(yaml)).toThrow();
      });
    });

    describe("3.2 Pinned Character Flag Toggles", () => {
      it("defaults pinned to false when omitted", () => {
        const yaml = `
characters:
  default_char:
    name: "Default Unpinned"
jobs:
  - id: shot1
    type: image
    prompt: "Unpinned"
    character: $ref:characters.default_char
`;
        const batch = parseBatchYaml(yaml);
        expect(batch.characters.default_char.pinned).toBe(false);

        const resolved = resolvePipeline(batch);
        expect(resolved.jobs[0].resolvedCharacters![0].pinned).toBe(false);
      });

      it("propagates pinned: true accurately to resolved job metadata", () => {
        const yaml = `
characters:
  pinned_hero:
    name: "Pinned Hero"
    pinned: true
jobs:
  - id: shot1
    type: image
    prompt: "Hero shot"
    character: $ref:characters.pinned_hero
`;
        const batch = parseBatchYaml(yaml);
        expect(batch.characters.pinned_hero.pinned).toBe(true);

        const resolved = resolvePipeline(batch);
        expect(resolved.jobs[0].resolvedCharacters![0].pinned).toBe(true);
      });

      it("handles mixed pinned: true and pinned: false characters in the same pipeline", () => {
        const yaml = `
characters:
  lead:
    name: "Protagonist"
    pinned: true
  extra:
    name: "Background Extra"
    pinned: false
jobs:
  - id: shot1
    type: image
    prompt: "Lead with extra"
    character:
      - $ref:characters.lead
      - $ref:characters.extra
`;
        const batch = parseBatchYaml(yaml);
        const resolved = resolvePipeline(batch);
        const chars = resolved.jobs[0].resolvedCharacters!;

        expect(chars).toHaveLength(2);
        expect(chars[0].name).toBe("Protagonist");
        expect(chars[0].pinned).toBe(true);
        expect(chars[1].name).toBe("Background Extra");
        expect(chars[1].pinned).toBe(false);
      });
    });

    describe("3.3 Missing startFrame / endFrame References", () => {
      it("throws clear error when startFrame references an undefined job output", () => {
        const yaml = `
jobs:
  - id: shot2
    type: video
    prompt: "Second shot"
    startFrame: $output:nonexistent_parent
`;
        const batch = parseBatchYaml(yaml);
        expect(() => resolvePipeline(batch)).toThrowError(
          "Job 'shot2' references output of undefined job 'nonexistent_parent'. Defined jobs: [shot2]"
        );
      });

      it("throws clear error when endFrame references an undefined job output", () => {
        const yaml = `
jobs:
  - id: shot2
    type: video
    prompt: "Second shot"
    endFrame: $output:nonexistent_future_job
`;
        const batch = parseBatchYaml(yaml);
        expect(() => resolvePipeline(batch)).toThrowError(
          "Job 'shot2' references output of undefined job 'nonexistent_future_job'. Defined jobs: [shot2]"
        );
      });

      it("allows video job with undefined startFrame and undefined endFrame", () => {
        const yaml = `
jobs:
  - id: standalone_video
    type: video
    prompt: "Fresh video from text prompt"
`;
        const batch = parseBatchYaml(yaml);
        const resolved = resolvePipeline(batch);

        const job = resolved.jobs[0] as VideoJob;
        expect(job.startFrame).toBeUndefined();
        expect(job.endFrame).toBeUndefined();
        expect(job.dependsOn).toEqual([]);
      });

      it("allows startFrame and endFrame with static file paths without creating false dependencies", () => {
        const yaml = `
jobs:
  - id: static_frame_video
    type: video
    prompt: "Static frames"
    startFrame: "examples/assets/elena_reference_sheet.png"
    endFrame: "examples/assets/shibuya_alley_plate.png"
`;
        const batch = parseBatchYaml(yaml);
        const resolved = resolvePipeline(batch);

        const job = resolved.jobs[0] as VideoJob;
        expect(job.startFrame).toBe("examples/assets/elena_reference_sheet.png");
        expect(job.endFrame).toBe("examples/assets/shibuya_alley_plate.png");
        expect(job.dependsOn).toEqual([]);
      });

      it("throws runtime error when startFrame $output references job that produced zero artifacts", () => {
        const job = parseVideoJob({
          id: "shot2",
          type: "video",
          prompt: "Consumer",
          startFrame: "$output:shot1"
        });

        const artifactsMap = {
          shot1: []
        };

        expect(() => interpolateJobOutputs(job, artifactsMap)).toThrowError(
          "Cannot resolve output reference '$output:shot1': Upstream job 'shot1' produced no output artifacts."
        );
      });

      it("throws runtime error when startFrame $output references index out of bounds", () => {
        const job = parseVideoJob({
          id: "shot2",
          type: "video",
          prompt: "Consumer",
          startFrame: "$output:shot1[2]"
        });

        const artifactsMap = {
          shot1: ["/out/shot1_0.mp4"]
        };

        expect(() => interpolateJobOutputs(job, artifactsMap)).toThrowError(
          "Cannot resolve output reference '$output:shot1[2]': Upstream job 'shot1' only produced 1 artifact(s), requested index [2]."
        );
      });
    });
  });
});
