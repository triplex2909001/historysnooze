import { describe, expect, it } from "vitest";
import { parseBatchYaml, parseVideoJob } from "../src/jobs/schema.js";
import {
  extractOutputDependencies,
  interpolateJobOutputs,
  isBackgroundRef,
  isCharacterRef,
  isPropRef,
  parseOutputRef,
  resolveJobOrder,
  resolvePipeline
} from "../src/jobs/resolver.js";

describe("resolver reference regex & helpers", () => {
  it("correctly identifies reference patterns", () => {
    expect(isCharacterRef("$ref:characters.hero")).toBe(true);
    expect(isCharacterRef("$ref:characters.hero_1")).toBe(true);
    expect(isCharacterRef("$ref:backgrounds.alley")).toBe(false);
    expect(isCharacterRef("plain-character")).toBe(false);

    expect(isBackgroundRef("$ref:backgrounds.alley")).toBe(true);
    expect(isBackgroundRef("$ref:characters.hero")).toBe(false);

    expect(isPropRef("$ref:props.motorcycle")).toBe(true);
    expect(isPropRef("$ref:backgrounds.plate")).toBe(false);
  });

  it("parses output references with indices and position tags", () => {
    expect(parseOutputRef("$output:shot_1")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: undefined
    });
    expect(parseOutputRef("$output:shot_1[2]")).toEqual({
      jobId: "shot_1",
      index: 2,
      position: undefined
    });
    expect(parseOutputRef("$output:shot_1#last")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: "last"
    });
    expect(parseOutputRef("$output:shot_1[1]#first")).toEqual({
      jobId: "shot_1",
      index: 1,
      position: "first"
    });
    expect(parseOutputRef("$output:shot_1#3.5s")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: 3.5
    });
    expect(parseOutputRef("not-an-output-ref")).toBeNull();
  });
});

describe("dependency inference from outputs", () => {
  it("extracts output dependencies from startFrame, endFrame, and ingredients", () => {
    const job = {
      id: "shot-3",
      type: "video" as const,
      prompt: "Continuing the scene",
      startFrame: "$output:shot-1",
      endFrame: "$output:shot-2[1]",
      ingredients: ["$output:asset-gen", "plain-image.png"]
    };

    const deps = extractOutputDependencies(job);
    expect(deps).toContain("shot-1");
    expect(deps).toContain("shot-2");
    expect(deps).toContain("asset-gen");
    expect(deps).not.toContain("plain-image.png");
  });

  it("extracts legacy ${job.artifacts} dependencies", () => {
    const job = {
      id: "shot-legacy",
      type: "video" as const,
      prompt: "Legacy scene",
      startFrame: "${prev-job.artifacts[0]}"
    };

    const deps = extractOutputDependencies(job);
    expect(deps).toEqual(["prev-job"]);
  });
});

describe("resolvePipeline declarative references", () => {
  it("resolves characters, backgrounds, and props into job definitions", () => {
    const batch = parseBatchYaml(`
pipeline: test-scene
characters:
  hero:
    name: Elena Vance
    referenceSheet: assets/elena.png
    pinned: true
backgrounds:
  alley:
    name: Neon Alley
    plate: assets/alley_plate.png
props:
  bike:
    name: Monobike
    asset: assets/bike.png
jobs:
  - id: shot-1
    type: image
    prompt: Elena in the alley
    character: $ref:characters.hero
    background: $ref:backgrounds.alley
    props: $ref:props.bike
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs).toHaveLength(1);
    const job = resolved.jobs[0];

    expect(job.character).toEqual(["Elena Vance"]);
    expect(job.resolvedCharacters).toBeDefined();
    expect(job.resolvedCharacters?.[0]).toMatchObject({
      name: "Elena Vance",
      referenceSheet: "assets/elena.png",
      pinned: true
    });
    expect(job.ingredients).toContain("assets/alley_plate.png");
    expect(job.ingredients).toContain("assets/bike.png");
  });

  it("resolves references inside ingredients array directly", () => {
    const batch = parseBatchYaml(`
pipeline: test-ingredients
backgrounds:
  rooftop:
    name: Rooftop
    plate: assets/rooftop.png
props:
  drone:
    name: Drone
    asset: assets/drone.png
jobs:
  - id: shot-1
    type: image
    prompt: Drone over rooftop
    ingredients:
      - $ref:backgrounds.rooftop
      - $ref:props.drone
      - assets/static_extra.png
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs[0].ingredients).toEqual([
      "assets/rooftop.png",
      "assets/drone.png",
      "assets/static_extra.png"
    ]);
  });

  it("throws descriptive error when referencing unknown character", () => {
    const batch = parseBatchYaml(`
characters:
  hero:
    name: Elena
jobs:
  - id: shot-1
    type: image
    prompt: Unknown character test
    character: $ref:characters.villain
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Character reference '$ref:characters.villain' in job 'shot-1' not found. Available characters: [hero]"
    );
  });

  it("throws descriptive error when referencing unknown background", () => {
    const batch = parseBatchYaml(`
backgrounds:
  lab:
    name: Cyber Lab
    plate: assets/lab.png
jobs:
  - id: shot-1
    type: image
    prompt: Unknown background test
    background: $ref:backgrounds.mars
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Background reference '$ref:backgrounds.mars' in job 'shot-1' not found. Available backgrounds: [lab]"
    );
  });

  it("throws descriptive error when referencing unknown prop", () => {
    const batch = parseBatchYaml(`
props:
  blaster:
    name: Blaster
    asset: assets/blaster.png
jobs:
  - id: shot-1
    type: image
    prompt: Unknown prop test
    props: $ref:props.sword
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Prop reference '$ref:props.sword' in job 'shot-1' not found. Available props: [blaster]"
    );
  });
});

describe("DAG Topological Sorter & Dependency Inference", () => {
  it("infers DAG edges from $output references and sorts in topological order", () => {
    const batch = parseBatchYaml(`
pipeline: scene-chaining
jobs:
  - id: shot-3
    type: video
    prompt: Final shot
    startFrame: $output:shot-2
  - id: shot-1
    type: image
    prompt: Establishing shot
  - id: shot-2
    type: video
    prompt: Middle shot
    startFrame: $output:shot-1
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs.map((j) => j.id)).toEqual(["shot-1", "shot-2", "shot-3"]);
    expect(resolved.jobs[1].dependsOn).toContain("shot-1");
    expect(resolved.jobs[2].dependsOn).toContain("shot-2");
  });

  it("preserves order for independent jobs", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: job-a
    type: image
    prompt: Job A
  - id: job-b
    type: image
    prompt: Job B
  - id: job-c
    type: image
    prompt: Job C
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs.map((j) => j.id)).toEqual(["job-a", "job-b", "job-c"]);
  });

  it("directly sorts raw jobs using resolveJobOrder", () => {
    const rawJobs = [
      { id: "step-2", type: "image" as const, prompt: "2", dependsOn: ["step-1"], out: ".", outputs: 1, ingredients: [], character: [] },
      { id: "step-1", type: "image" as const, prompt: "1", out: ".", outputs: 1, ingredients: [], character: [] }
    ];
    const ordered = resolveJobOrder(rawJobs);
    expect(ordered.map((j) => j.id)).toEqual(["step-1", "step-2"]);
  });

  it("resolves diamond dependencies correctly", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: d
    type: image
    prompt: D
    dependsOn: [b, c]
  - id: b
    type: image
    prompt: B
    dependsOn: [a]
  - id: c
    type: image
    prompt: C
    dependsOn: [a]
  - id: a
    type: image
    prompt: A
`);

    const resolved = resolvePipeline(batch);
    const order = resolved.jobs.map((j) => j.id);

    expect(order.indexOf("a")).toBeLessThan(order.indexOf("b"));
    expect(order.indexOf("a")).toBeLessThan(order.indexOf("c"));
    expect(order.indexOf("b")).toBeLessThan(order.indexOf("d"));
    expect(order.indexOf("c")).toBeLessThan(order.indexOf("d"));
  });

  it("throws descriptive error on self-dependency", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: self-loop
    type: video
    prompt: Self referencing
    startFrame: $output:self-loop
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'self-loop' cannot reference its own output (self-dependency detected)"
    );
  });

  it("throws descriptive error when referencing output of non-existent job", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Test
    startFrame: $output:non_existent_shot
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'shot-1' references output of undefined job 'non_existent_shot'"
    );
  });

  it("detects 2-node circular dependencies with path tracing", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: job-1
    type: image
    prompt: J1
    dependsOn: [job-2]
  - id: job-2
    type: image
    prompt: J2
    dependsOn: [job-1]
`);

    expect(() => resolvePipeline(batch)).toThrow(/Cyclic dependency detected in pipeline jobs:.*job-1.*job-2/);
  });

  it("detects 3-node circular dependencies with path tracing", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: node-a
    type: image
    prompt: A
    dependsOn: [node-c]
  - id: node-b
    type: image
    prompt: B
    dependsOn: [node-a]
  - id: node-c
    type: image
    prompt: C
    dependsOn: [node-b]
`);

    expect(() => resolvePipeline(batch)).toThrow(/Cyclic dependency detected in pipeline jobs:.*node-a/);
  });
});

describe("interpolateJobOutputs", () => {
  it("interpolates $output references using artifacts map", () => {
    const job = parseVideoJob({
      id: "shot-2",
      type: "video",
      prompt: "Second shot",
      startFrame: "$output:shot-1",
      endFrame: "$output:shot-1[1]",
      ingredients: ["$output:asset-gen[0]", "static.png"]
    });

    const artifactsMap = {
      "shot-1": ["/out/shot-1_1.png", "/out/shot-1_2.png"],
      "asset-gen": ["/out/asset.png"]
    };

    const interpolated = interpolateJobOutputs(job, artifactsMap);
    expect(interpolated.startFrame).toBe("/out/shot-1_1.png");
    expect(interpolated.endFrame).toBe("/out/shot-1_2.png");
    expect(interpolated.ingredients).toEqual(["/out/asset.png", "static.png"]);
  });

  it("throws error when referenced job has no recorded artifacts", () => {
    const job = parseVideoJob({
      id: "shot-2",
      type: "video",
      prompt: "Second shot",
      startFrame: "$output:shot-1"
    });

    expect(() => interpolateJobOutputs(job, {})).toThrow(
      "Cannot resolve output reference '$output:shot-1': Upstream job 'shot-1' produced no output artifacts."
    );
  });

  it("throws error when requested index is out of bounds", () => {
    const job = parseVideoJob({
      id: "shot-2",
      type: "video",
      prompt: "Second shot",
      startFrame: "$output:shot-1[5]"
    });

    const artifactsMap = {
      "shot-1": ["/out/shot-1_1.png"]
    };

    expect(() => interpolateJobOutputs(job, artifactsMap)).toThrow(
      "Cannot resolve output reference '$output:shot-1[5]': Upstream job 'shot-1' only produced 1 artifact(s), requested index [5]."
    );
  });
});
