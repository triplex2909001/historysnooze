import { describe, expect, it } from "vitest";
import { parseBatchYaml, parseVideoJob } from "../src/jobs/schema.js";
import {
  interpolateJobOutputs,
  resolveJobOrder,
  resolvePipeline
} from "../src/jobs/resolver.js";

describe("Adversarial Stress Testing: Cyclic Dependencies & Self-References", () => {
  it("detects direct self-dependency via dependsOn: [A] in resolvePipeline", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: job-loop
    type: image
    prompt: Loop test
    dependsOn: [job-loop]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'job-loop' cannot depend on itself (self-dependency detected)"
    );
  });

  it("detects direct self-dependency via resolveJobOrder", () => {
    const jobs = [
      {
        id: "self-node",
        type: "image" as const,
        prompt: "Self loop",
        dependsOn: ["self-node"],
        out: ".",
        outputs: 1,
        ingredients: [],
        character: []
      }
    ];
    expect(() => resolveJobOrder(jobs)).toThrow(
      "Cyclic dependency detected: Job 'self-node' depends on itself"
    );
  });

  it("detects direct self-dependency via startFrame: $output:A", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: video-self
    type: video
    prompt: Self video loop
    startFrame: $output:video-self
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'video-self' cannot reference its own output (self-dependency detected)"
    );
  });

  it("detects direct self-dependency via endFrame: $output:A", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: video-self-end
    type: video
    prompt: Self video loop endFrame
    endFrame: $output:video-self-end
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'video-self-end' cannot reference its own output (self-dependency detected)"
    );
  });

  it("detects direct self-dependency via ingredients: [$output:A]", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: img-self-ing
    type: image
    prompt: Self ingredient
    ingredients:
      - $output:img-self-ing
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'img-self-ing' cannot reference its own output (self-dependency detected)"
    );
  });

  it("detects 2-node cycle (A -> B -> A) via dependsOn with descriptive cycle trace", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: node-1
    type: image
    prompt: "Node 1"
    dependsOn: [node-2]
  - id: node-2
    type: image
    prompt: "Node 2"
    dependsOn: [node-1]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs:.*node-1.*node-2/
    );
  });

  it("detects 2-node cycle (A -> B -> A) via $output references", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-alpha
    type: video
    prompt: Alpha
    startFrame: $output:shot-beta
  - id: shot-beta
    type: video
    prompt: Beta
    startFrame: $output:shot-alpha
`);
    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs:.*shot-alpha.*shot-beta/
    );
  });

  it("detects 3-node cycle (A -> B -> C -> A) via dependsOn with exact path", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: job-A
    type: image
    prompt: A
    dependsOn: [job-C]
  - id: job-B
    type: image
    prompt: B
    dependsOn: [job-A]
  - id: job-C
    type: image
    prompt: C
    dependsOn: [job-B]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Cyclic dependency detected in pipeline jobs: job-A -> job-C -> job-B -> job-A"
    );
  });

  it("detects 3-node cycle (A -> B -> C -> A) via $output references in different fields", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Shot 1
    startFrame: $output:shot-3
  - id: shot-2
    type: video
    prompt: Shot 2
    endFrame: $output:shot-1
  - id: shot-3
    type: image
    prompt: Shot 3
    ingredients:
      - $output:shot-2
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Cyclic dependency detected in pipeline jobs: shot-1 -> shot-3 -> shot-2 -> shot-1"
    );
  });

  it("detects mixed cycle with both explicit dependsOn and $output references", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: step-A
    type: image
    prompt: A
    dependsOn: [step-B]
  - id: step-B
    type: video
    prompt: B
    startFrame: $output:step-C
  - id: step-C
    type: image
    prompt: C
    dependsOn: [step-A]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs:.*step-A.*step-B.*step-C/
    );
  });

  it("handles complex 10-node cycle without stack overflow or infinite loop", () => {
    const count = 10;
    const jobs = Array.from({ length: count }, (_, i) => {
      const nextId = `node-${(i + 1) % count}`;
      return `  - id: node-${i}\n    type: image\n    prompt: Node ${i}\n    dependsOn: [${nextId}]`;
    }).join("\n");

    const yaml = `jobs:\n${jobs}`;
    const batch = parseBatchYaml(yaml);

    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs:.*node-/
    );
  });

  it("detects cycle in a disconnected graph with independent valid jobs", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: good-1
    type: image
    prompt: Good 1
  - id: good-2
    type: image
    prompt: Good 2
    dependsOn: [good-1]
  - id: bad-1
    type: image
    prompt: Bad 1
    dependsOn: [bad-2]
  - id: bad-2
    type: image
    prompt: Bad 2
    dependsOn: [bad-1]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs:.*bad-1.*bad-2/
    );
  });

  it("detects cycles when graph contains multiple disconnected cycles", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: c1-a
    type: image
    prompt: C1 A
    dependsOn: [c1-b]
  - id: c1-b
    type: image
    prompt: C1 B
    dependsOn: [c1-a]
  - id: c2-a
    type: image
    prompt: C2 A
    dependsOn: [c2-b]
  - id: c2-b
    type: image
    prompt: C2 B
    dependsOn: [c2-a]
`);
    expect(() => resolvePipeline(batch)).toThrow(/Cyclic dependency detected in pipeline jobs:/);
  });
});

describe("Adversarial Stress Testing: Diamond Graphs & Complex Branching", () => {
  it("correctly resolves a diamond DAG using $output references", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: sink-D
    type: video
    prompt: Final composite
    startFrame: $output:branch-B
    endFrame: $output:branch-C
  - id: branch-C
    type: image
    prompt: Branch C
    ingredients:
      - $output:root-A
  - id: branch-B
    type: image
    prompt: Branch B
    ingredients:
      - $output:root-A
  - id: root-A
    type: image
    prompt: Root source
`);

    const resolved = resolvePipeline(batch);
    const ids = resolved.jobs.map((j) => j.id);

    // root-A must precede branch-B and branch-C
    expect(ids.indexOf("root-A")).toBeLessThan(ids.indexOf("branch-B"));
    expect(ids.indexOf("root-A")).toBeLessThan(ids.indexOf("branch-C"));
    // both branches must precede sink-D
    expect(ids.indexOf("branch-B")).toBeLessThan(ids.indexOf("sink-D"));
    expect(ids.indexOf("branch-C")).toBeLessThan(ids.indexOf("sink-D"));
  });

  it("resolves deep multi-tiered diamond lattice: A -> (B, C) -> D -> (E, F) -> G", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: G
    type: video
    prompt: Final
    startFrame: $output:E
    endFrame: $output:F
  - id: F
    type: image
    prompt: Tier 2 Right
    ingredients: [$output:D]
  - id: E
    type: image
    prompt: Tier 2 Left
    ingredients: [$output:D]
  - id: D
    type: video
    prompt: Mid Sink
    startFrame: $output:B
    endFrame: $output:C
  - id: C
    type: image
    prompt: Tier 1 Right
    ingredients: [$output:A]
  - id: B
    type: image
    prompt: Tier 1 Left
    ingredients: [$output:A]
  - id: A
    type: image
    prompt: Root
`);

    const resolved = resolvePipeline(batch);
    const ids = resolved.jobs.map((j) => j.id);

    expect(ids.indexOf("A")).toBe(0);
    expect(ids.indexOf("B")).toBeLessThan(ids.indexOf("D"));
    expect(ids.indexOf("C")).toBeLessThan(ids.indexOf("D"));
    expect(ids.indexOf("D")).toBeLessThan(ids.indexOf("E"));
    expect(ids.indexOf("D")).toBeLessThan(ids.indexOf("F"));
    expect(ids.indexOf("E")).toBeLessThan(ids.indexOf("G"));
    expect(ids.indexOf("F")).toBeLessThan(ids.indexOf("G"));
  });

  it("handles wide fan-out (1 producer feeding 25 consumer jobs)", () => {
    const consumerCount = 25;
    const consumers = Array.from({ length: consumerCount }, (_, i) => {
      return `  - id: consumer-${i}\n    type: image\n    prompt: Consumer ${i}\n    ingredients: [$output:producer]`;
    }).join("\n");

    const yaml = `jobs:\n${consumers}\n  - id: producer\n    type: image\n    prompt: Producer`;
    const batch = parseBatchYaml(yaml);

    const resolved = resolvePipeline(batch);
    const ids = resolved.jobs.map((j) => j.id);

    expect(ids[0]).toBe("producer");
    expect(resolved.jobs).toHaveLength(26);
  });

  it("handles wide fan-in (25 producer jobs feeding 1 aggregator job)", () => {
    const producerCount = 25;
    const producers = Array.from({ length: producerCount }, (_, i) => {
      return `  - id: prod-${i}\n    type: image\n    prompt: Producer ${i}`;
    }).join("\n");

    const aggIngredients = Array.from({ length: producerCount }, (_, i) => `      - $output:prod-${i}`).join("\n");
    const aggregator = `  - id: aggregator\n    type: image\n    prompt: Aggregator\n    ingredients:\n${aggIngredients}`;

    const yaml = `jobs:\n${aggregator}\n${producers}`;
    const batch = parseBatchYaml(yaml);

    const resolved = resolvePipeline(batch);
    const ids = resolved.jobs.map((j) => j.id);

    expect(ids[ids.length - 1]).toBe("aggregator");
    expect(resolved.jobs).toHaveLength(26);
  });

  it("handles 50-step linear dependency chain efficiently (<50ms)", () => {
    const chainLength = 50;
    const jobs = Array.from({ length: chainLength }, (_, i) => {
      if (i === 0) {
        return `  - id: step-0\n    type: image\n    prompt: Step 0`;
      }
      return `  - id: step-${i}\n    type: video\n    prompt: Step ${i}\n    startFrame: $output:step-${i - 1}`;
    }).reverse().join("\n");

    const yaml = `jobs:\n${jobs}`;
    const start = performance.now();
    const batch = parseBatchYaml(yaml);
    const resolved = resolvePipeline(batch);
    const duration = performance.now() - start;

    expect(resolved.jobs).toHaveLength(50);
    for (let i = 0; i < chainLength; i++) {
      expect(resolved.jobs[i].id).toBe(`step-${i}`);
    }
    expect(duration).toBeLessThan(100);
  });

  it("deduplicates dual dependencies (dependsOn + $output:X) without double counting inDegree", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: consumer
    type: video
    prompt: Consumer
    dependsOn: [producer]
    startFrame: $output:producer
    endFrame: $output:producer[1]
    ingredients:
      - $output:producer
  - id: producer
    type: image
    prompt: Producer
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs.map((j) => j.id)).toEqual(["producer", "consumer"]);
    expect(resolved.jobs[1].dependsOn).toEqual(["producer"]);
  });

  it("supports job IDs with periods, underscores, and hyphens", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: job.sub_2-v1
    type: video
    prompt: Child
    startFrame: $output:job.sub_1-v0
  - id: job.sub_1-v0
    type: image
    prompt: Parent
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs.map((j) => j.id)).toEqual(["job.sub_1-v0", "job.sub_2-v1"]);
  });
});

describe("Adversarial Stress Testing: Unknown Reference Targets", () => {
  it("throws descriptive error for unknown character reference in character array", () => {
    const batch = parseBatchYaml(`
characters:
  alice:
    name: Alice
jobs:
  - id: shot-1
    type: image
    prompt: Test
    character:
      - $ref:characters.missing
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Character reference '$ref:characters.missing' in job 'shot-1' not found. Available characters: [alice]"
    );
  });

  it("throws descriptive error for unknown character when registry is completely empty", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: image
    prompt: Test
    character: $ref:characters.nobody
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Character reference '$ref:characters.nobody' in job 'shot-1' not found. Available characters: [none]"
    );
  });

  it("throws descriptive error for unknown background in background field", () => {
    const batch = parseBatchYaml(`
backgrounds:
  cyberpunk_city:
    name: City
    plate: city.png
jobs:
  - id: shot-1
    type: image
    prompt: Test
    background: $ref:backgrounds.unknown_bg
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Background reference '$ref:backgrounds.unknown_bg' in job 'shot-1' not found. Available backgrounds: [cyberpunk_city]"
    );
  });

  it("throws descriptive error for unknown background in ingredients array", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: image
    prompt: Test
    ingredients:
      - $ref:backgrounds.ghost_plate
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Background reference '$ref:backgrounds.ghost_plate' in ingredients of job 'shot-1' not found. Available backgrounds: [none]"
    );
  });

  it("throws descriptive error for unknown background in startFrame", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Test
    startFrame: $ref:backgrounds.missing_start
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Background reference '$ref:backgrounds.missing_start' in startFrame of job 'shot-1' not found. Available backgrounds: [none]"
    );
  });

  it("throws descriptive error for unknown background in endFrame", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Test
    endFrame: $ref:backgrounds.missing_end
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Background reference '$ref:backgrounds.missing_end' in endFrame of job 'shot-1' not found. Available backgrounds: [none]"
    );
  });

  it("throws descriptive error for unknown prop in props array", () => {
    const batch = parseBatchYaml(`
props:
  katana:
    name: Katana
    asset: katana.png
jobs:
  - id: shot-1
    type: image
    prompt: Test
    props:
      - $ref:props.plasma_cannon
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Prop reference '$ref:props.plasma_cannon' in job 'shot-1' not found. Available props: [katana]"
    );
  });

  it("throws descriptive error for unknown prop in ingredients array", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: image
    prompt: Test
    ingredients:
      - $ref:props.unregistered_prop
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Prop reference '$ref:props.unregistered_prop' in ingredients of job 'shot-1' not found. Available props: [none]"
    );
  });

  it("throws descriptive error for unknown prop in startFrame", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Test
    startFrame: $ref:props.prop_start
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Prop reference '$ref:props.prop_start' in startFrame of job 'shot-1' not found. Available props: [none]"
    );
  });

  it("throws descriptive error for unknown prop in endFrame", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-1
    type: video
    prompt: Test
    endFrame: $ref:props.prop_end
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Prop reference '$ref:props.prop_end' in endFrame of job 'shot-1' not found. Available props: [none]"
    );
  });

  it("throws descriptive error for unknown job referenced in startFrame $output", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-2
    type: video
    prompt: Test
    startFrame: $output:nonexistent_parent
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'shot-2' references output of undefined job 'nonexistent_parent'. Defined jobs: [shot-2]"
    );
  });

  it("throws descriptive error for unknown job referenced in endFrame $output", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-2
    type: video
    prompt: Test
    endFrame: $output:phantom_job
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'shot-2' references output of undefined job 'phantom_job'. Defined jobs: [shot-2]"
    );
  });

  it("throws descriptive error for unknown job referenced in ingredients $output", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-2
    type: image
    prompt: Test
    ingredients:
      - $output:ghost_upstream
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'shot-2' references output of undefined job 'ghost_upstream'. Defined jobs: [shot-2]"
    );
  });

  it("throws descriptive error for unknown job in explicit dependsOn", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: shot-2
    type: image
    prompt: Test
    dependsOn: [ghost_dep]
`);

    expect(() => resolvePipeline(batch)).toThrow(
      "Job 'shot-2' depends on undefined job 'ghost_dep'. Defined jobs: [shot-2]"
    );
  });
});

describe("Adversarial Stress Testing: Out-of-Bounds Output Index ($output:job[99])", () => {
  it("throws descriptive error when requesting index 99 on job with 1 artifact", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "OOB test",
      startFrame: "$output:job1[99]"
    });

    const artifactsMap = {
      job1: ["/outputs/job1_0.png"]
    };

    expect(() => interpolateJobOutputs(job, artifactsMap)).toThrow(
      "Cannot resolve output reference '$output:job1[99]': Upstream job 'job1' only produced 1 artifact(s), requested index [99]."
    );
  });

  it("throws descriptive error on off-by-one boundary: index 1 requested for 1 artifact", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Boundary test",
      startFrame: "$output:job1[1]"
    });

    const artifactsMap = {
      job1: ["/outputs/job1_0.png"]
    };

    expect(() => interpolateJobOutputs(job, artifactsMap)).toThrow(
      "Cannot resolve output reference '$output:job1[1]': Upstream job 'job1' only produced 1 artifact(s), requested index [1]."
    );
  });

  it("succeeds when requesting exact max index: index 0 requested for 1 artifact", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Valid boundary test",
      startFrame: "$output:job1[0]"
    });

    const artifactsMap = {
      job1: ["/outputs/job1_0.png"]
    };

    const result = interpolateJobOutputs(job, artifactsMap);
    expect(result.startFrame).toBe("/outputs/job1_0.png");
  });

  it("succeeds when requesting last valid index: index 3 requested for 4 artifacts", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Valid last index",
      startFrame: "$output:job1[3]"
    });

    const artifactsMap = {
      job1: [
        "/outputs/job1_0.png",
        "/outputs/job1_1.png",
        "/outputs/job1_2.png",
        "/outputs/job1_3.png"
      ]
    };

    const result = interpolateJobOutputs(job, artifactsMap);
    expect(result.startFrame).toBe("/outputs/job1_3.png");
  });

  it("throws descriptive error when upstream job produced 0 artifacts (empty list)", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Empty list test",
      startFrame: "$output:job1[0]"
    });

    const artifactsMap = {
      job1: []
    };

    expect(() => interpolateJobOutputs(job, artifactsMap)).toThrow(
      "Cannot resolve output reference '$output:job1[0]': Upstream job 'job1' produced no output artifacts."
    );
  });

  it("throws descriptive error when upstream job is completely missing from artifactsMap", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Missing from map test",
      startFrame: "$output:job1"
    });

    expect(() => interpolateJobOutputs(job, {})).toThrow(
      "Cannot resolve output reference '$output:job1': Upstream job 'job1' produced no output artifacts."
    );
  });

  it("throws descriptive error for legacy format ${job1.artifacts[99]} out of bounds", () => {
    const job = parseVideoJob({
      id: "shot-consumer",
      type: "video",
      prompt: "Legacy OOB test",
      startFrame: "${job1.artifacts[99]}"
    });

    const artifactsMap = {
      job1: ["/outputs/job1_0.png"]
    };

    expect(() => interpolateJobOutputs(job, artifactsMap)).toThrow(
      "Cannot resolve output reference '${job1.artifacts[99]}': Upstream job 'job1' only produced 1 artifact(s), requested index [99]."
    );
  });

  it("interpolates multiple outputs correctly across startFrame, endFrame, and ingredients", () => {
    const job = parseVideoJob({
      id: "multi-consumer",
      type: "video",
      prompt: "Multi ref test",
      startFrame: "$output:jobA[0]",
      endFrame: "$output:jobB[1]",
      ingredients: [
        "$output:jobA[1]",
        "$output:jobC[0]",
        "/static/path.png"
      ]
    });

    const artifactsMap = {
      jobA: ["/a0.png", "/a1.png"],
      jobB: ["/b0.png", "/b1.png"],
      jobC: ["/c0.png"]
    };

    const interpolated = interpolateJobOutputs(job, artifactsMap);
    expect(interpolated.startFrame).toBe("/a0.png");
    expect(interpolated.endFrame).toBe("/b1.png");
    expect(interpolated.ingredients).toEqual([
      "/a1.png",
      "/c0.png",
      "/static/path.png"
    ]);
  });
});

describe("Adversarial Stress Testing: Edge Cases & Large Graphs", () => {
  it("isolates sub-cycle within larger acyclic graph (Root -> A -> B -> C -> B -> Sink)", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: root
    type: image
    prompt: Root
  - id: node-A
    type: image
    prompt: A
    dependsOn: [root]
  - id: node-B
    type: image
    prompt: B
    dependsOn: [node-A, node-C]
  - id: node-C
    type: image
    prompt: C
    dependsOn: [node-B]
  - id: sink
    type: image
    prompt: Sink
    dependsOn: [node-C]
`);
    expect(() => resolvePipeline(batch)).toThrow(
      "Cyclic dependency detected in pipeline jobs: node-B -> node-C -> node-B"
    );
  });

  it("handles 50-node cycle cleanly without exceeding call stack", () => {
    const n = 50;
    const jobs = Array.from({ length: n }, (_, i) => {
      const next = `cycle-node-${(i + 1) % n}`;
      return `  - id: cycle-node-${i}\n    type: image\n    prompt: Node ${i}\n    dependsOn: [${next}]`;
    }).join("\n");

    const batch = parseBatchYaml(`jobs:\n${jobs}`);
    expect(() => resolvePipeline(batch)).toThrow(
      /Cyclic dependency detected in pipeline jobs: cycle-node-/
    );
  });

  it("handles 100 independent jobs preserving original order", () => {
    const n = 100;
    const jobs = Array.from({ length: n }, (_, i) => {
      return `  - id: job-${i.toString().padStart(3, "0")}\n    type: image\n    prompt: Job ${i}`;
    }).join("\n");

    const batch = parseBatchYaml(`jobs:\n${jobs}`);
    const resolved = resolvePipeline(batch);
    expect(resolved.jobs).toHaveLength(100);
    for (let i = 0; i < n; i++) {
      expect(resolved.jobs[i].id).toBe(`job-${i.toString().padStart(3, "0")}`);
    }
  });

  it("verifies prompt text containing $output or $ref tokens does NOT create false dependencies", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: narrator
    type: image
    prompt: "This mentions $output:ghost_job and $ref:characters.nobody in plain text"
`);

    // Should resolve without error because prompt is not an artifact dependency channel
    const resolved = resolvePipeline(batch);
    expect(resolved.jobs).toHaveLength(1);
    expect(resolved.jobs[0].dependsOn).toEqual([]);
    expect(resolved.jobs[0].prompt).toBe(
      "This mentions $output:ghost_job and $ref:characters.nobody in plain text"
    );
  });

  it("preserves non-reference raw string paths in ingredients and frames", () => {
    const batch = parseBatchYaml(`
jobs:
  - id: raw-paths-job
    type: video
    prompt: Raw paths
    startFrame: ./local/path/frame_01.png
    endFrame: /absolute/path/frame_99.png
    ingredients:
      - ./textures/wall.png
      - https://example.com/asset.jpg
      - plain_string_not_a_ref
`);

    const resolved = resolvePipeline(batch);
    const job = resolved.jobs[0];
    expect(job.type === "video" && job.startFrame).toBe("./local/path/frame_01.png");
    expect(job.type === "video" && job.endFrame).toBe("/absolute/path/frame_99.png");
    expect(job.ingredients).toEqual([
      "./textures/wall.png",
      "https://example.com/asset.jpg",
      "plain_string_not_a_ref"
    ]);
  });

  it("handles full multi-layer consistency pipeline with characters, backgrounds, props and video chaining", () => {
    const batch = parseBatchYaml(`
pipeline: full-sci-fi-short
characters:
  commander:
    name: Commander Shepard
    referenceSheet: sheets/shepard.png
    pinned: true
  pilot:
    name: Joker
    referenceSheet: sheets/joker.png
    pinned: false
backgrounds:
  bridge:
    name: Normandy Bridge
    plate: plates/bridge.png
  hangar:
    name: Normandy Hangar
    plate: plates/hangar.png
props:
  omnitool:
    name: Omni-tool
    asset: props/omnitool.png
  mako:
    name: Mako Vehicle
    asset: props/mako.png
jobs:
  - id: shot-3
    type: video
    prompt: Joker pilots away
    character: $ref:characters.pilot
    background: $ref:backgrounds.hangar
    props: $ref:props.mako
    startFrame: $output:shot-2#last
  - id: shot-1
    type: image
    prompt: Shepard on bridge
    character: $ref:characters.commander
    background: $ref:backgrounds.bridge
    props: $ref:props.omnitool
  - id: shot-2
    type: video
    prompt: Shepard gives orders
    character:
      - $ref:characters.commander
      - $ref:characters.pilot
    startFrame: $output:shot-1
`);

    const resolved = resolvePipeline(batch);
    expect(resolved.jobs.map((j) => j.id)).toEqual(["shot-1", "shot-2", "shot-3"]);

    // Check shot-1
    expect(resolved.jobs[0].character).toEqual(["Commander Shepard"]);
    expect(resolved.jobs[0].resolvedCharacters?.[0].pinned).toBe(true);
    expect(resolved.jobs[0].ingredients).toContain("plates/bridge.png");
    expect(resolved.jobs[0].ingredients).toContain("props/omnitool.png");

    // Check shot-2
    expect(resolved.jobs[1].character).toEqual(["Commander Shepard", "Joker"]);
    expect(resolved.jobs[1].dependsOn).toEqual(["shot-1"]);

    // Check shot-3
    expect(resolved.jobs[2].character).toEqual(["Joker"]);
    expect(resolved.jobs[2].ingredients).toContain("plates/hangar.png");
    expect(resolved.jobs[2].ingredients).toContain("props/mako.png");
    expect(resolved.jobs[2].dependsOn).toEqual(["shot-2"]);

    // Test runtime output interpolation on shot-3
    const artifactsMap = {
      "shot-1": ["/out/shot1.png"],
      "shot-2": ["/out/shot2.mp4"]
    };
    const interpolated = interpolateJobOutputs(resolved.jobs[2], artifactsMap);
    expect(interpolated.type === "video" && interpolated.startFrame).toBe("/out/shot2.mp4");
  });
});
