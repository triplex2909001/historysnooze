import { describe, expect, it } from "vitest";
import {
  parseBatch,
  parseBatchYaml,
  parseImageJob,
  parseJob,
  parseVideoJob,
  UPSCALE_TIERS
} from "../src/jobs/schema.js";

describe("job schemas", () => {
  it("parses an image job with defaults", () => {
    const job = parseImageJob({
      id: "concept-image",
      type: "image",
      prompt: "A studio product still"
    });

    expect(job).toMatchObject({
      id: "concept-image",
      type: "image",
      prompt: "A studio product still",
      outputs: 1,
      out: "./gflow-output",
      ingredients: [],
      character: []
    });
  });

  it("parses a video job with duration and ratio", () => {
    const job = parseVideoJob({
      id: "hero-video",
      type: "video",
      prompt: "A cinematic product reveal",
      duration: 8,
      ratio: "16:9",
      startFrame: "assets/start.png",
      endFrame: "assets/end.png"
    });

    expect(job.duration).toBe(8);
    expect(job.ratio).toBe("16:9");
    expect(job.startFrame).toBe("assets/start.png");
    expect(job.endFrame).toBe("assets/end.png");
  });

  it("parses jobs via generic parseJob discriminator", () => {
    const img = parseJob({
      id: "img-1",
      type: "image",
      prompt: "An image"
    });
    expect(img.type).toBe("image");

    const vid = parseJob({
      id: "vid-1",
      type: "video",
      prompt: "A video",
      duration: 5
    });
    expect(vid.type).toBe("video");
  });

  it("rejects invalid job types or missing prompt", () => {
    expect(() =>
      parseJob({
        id: "invalid-type",
        type: "audio",
        prompt: "sound effect"
      })
    ).toThrow();

    expect(() =>
      parseJob({
        id: "no-prompt",
        type: "image"
      })
    ).toThrow();
  });

  it("rejects invalid job IDs with illegal characters", () => {
    expect(() =>
      parseImageJob({
        id: "bad id with spaces",
        type: "image",
        prompt: "test"
      })
    ).toThrow();

    expect(() =>
      parseImageJob({
        id: "bad$id",
        type: "image",
        prompt: "test"
      })
    ).toThrow();
  });
});

describe("image/video upscale + character + dependencies", () => {
  it("defaults character to [] and leaves upscale undefined", () => {
    const job = parseImageJob({ id: "a", type: "image", prompt: "x" });
    expect(job.character).toEqual([]);
    expect(job.upscale).toBeUndefined();
  });

  it("accepts upscale 2k/4k and character names", () => {
    expect(UPSCALE_TIERS).toEqual(["2k", "4k"]);

    const job2k = parseVideoJob({
      id: "b1",
      type: "video",
      prompt: "x",
      upscale: "2k",
      character: ["Nyra"]
    });
    expect(job2k.upscale).toBe("2k");
    expect(job2k.character).toEqual(["Nyra"]);

    const job4k = parseImageJob({
      id: "b2",
      type: "image",
      prompt: "x",
      upscale: "4k"
    });
    expect(job4k.upscale).toBe("4k");
  });

  it("rejects an invalid upscale value", () => {
    expect(() => parseImageJob({ id: "c", type: "image", prompt: "x", upscale: "8k" as unknown as "2k" })).toThrow();
  });

  it("accepts dependsOn and retry fields", () => {
    const job = parseImageJob({
      id: "c2",
      type: "image",
      prompt: "x",
      dependsOn: ["job-a", "job-b"],
      retry: 2
    });
    expect(job.dependsOn).toEqual(["job-a", "job-b"]);
    expect(job.retry).toBe(2);
  });
});

describe("batch pipeline parsing", () => {
  it("parses string pipeline shorthand", () => {
    const batch = parseBatchYaml(`
pipeline: test-pipeline
jobs:
  - id: step-1
    type: image
    prompt: First image
`);
    expect(batch.pipeline).toEqual({
      name: "test-pipeline",
      profiles: ["default"],
      autoheal: true,
      resume: true,
      maxRetries: 3,
      continueOnFailure: false
    });
    expect(batch.jobs).toHaveLength(1);
    expect(batch.jobs[0].id).toBe("step-1");
  });

  it("parses structured pipeline meta", () => {
    const batch = parseBatch({
      pipeline: {
        name: "custom-pipeline",
        profiles: ["p1", "p2"],
        autoheal: false,
        resume: false,
        maxRetries: 5,
        continueOnFailure: true
      },
      jobs: [
        {
          id: "step-1",
          type: "image",
          prompt: "First image"
        }
      ]
    });

    expect(batch.pipeline).toEqual({
      name: "custom-pipeline",
      profiles: ["p1", "p2"],
      autoheal: false,
      resume: false,
      maxRetries: 5,
      continueOnFailure: true
    });
  });

  it("rejects a batch with duplicate ids", () => {
    expect(() =>
      parseBatchYaml(`
jobs:
  - id: dup
    type: image
    prompt: One
  - id: dup
    type: video
    prompt: Two
`)
    ).toThrow("Duplicate job id: dup");
  });

  it("rejects empty jobs array", () => {
    expect(() =>
      parseBatch({
        jobs: []
      })
    ).toThrow();
  });

  it("parses declarative registries for characters, backgrounds, and props", () => {
    const batch = parseBatchYaml(`
pipeline: multi-layer-test
characters:
  hero:
    name: Elena Vance
    referenceSheet: assets/elena_sheet.png
    pinned: true
    description: Cyberpunk courier with cybernetic arm
backgrounds:
  alleyway:
    name: Neon Alley
    plate: assets/neon_alley_plate.png
    description: Wet asphalt reflecting holographic signs
props:
  motorcycle:
    name: Monobike
    asset: assets/monobike_isolated.png
jobs:
  - id: shot-1
    type: image
    prompt: Elena standing by her motorcycle
    character: $ref:characters.hero
    background: $ref:backgrounds.alleyway
    props: $ref:props.motorcycle
`);
    expect(batch.characters.hero).toMatchObject({
      name: "Elena Vance",
      referenceSheet: "assets/elena_sheet.png",
      pinned: true,
      description: "Cyberpunk courier with cybernetic arm"
    });
    expect(batch.backgrounds.alleyway).toMatchObject({
      name: "Neon Alley",
      plate: "assets/neon_alley_plate.png"
    });
    expect(batch.props.motorcycle).toMatchObject({
      name: "Monobike",
      asset: "assets/monobike_isolated.png"
    });
    expect(batch.jobs[0].character).toEqual(["$ref:characters.hero"]);
    expect(batch.jobs[0].background).toBe("$ref:backgrounds.alleyway");
    expect(batch.jobs[0].props).toEqual(["$ref:props.motorcycle"]);
  });

  it("normalizes single string values to arrays for character, ingredients, and props", () => {
    const job = parseImageJob({
      id: "norm-test",
      type: "image",
      prompt: "test",
      character: "SoloHero",
      ingredients: "single_plate.png",
      props: "single_prop.png"
    });
    expect(job.character).toEqual(["SoloHero"]);
    expect(job.ingredients).toEqual(["single_plate.png"]);
    expect(job.props).toEqual(["single_prop.png"]);
  });
});
