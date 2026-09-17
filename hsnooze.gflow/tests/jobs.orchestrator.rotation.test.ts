import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { SmartPipelineOrchestrator } from "../src/jobs/orchestrator.js";
import { CreditLimitError, RateLimitedError, ProfilePoolExhaustedError } from "../src/errors.js";
import type { FlowAutomation, FlowJobResult } from "../src/flow/types.js";
import type { GFlowJob } from "../src/jobs/schema.js";
import { loadCheckpoint } from "../src/jobs/checkpoint.js";

function createMockJob(id: string, outDir: string): GFlowJob {
  return {
    id,
    type: "image",
    prompt: "Sample prompt",
    outputs: 1,
    out: outDir,
    ingredients: [],
    character: []
  };
}

function createMockResult(jobId: string, outPath: string): FlowJobResult {
  return {
    jobId,
    flowUrl: "https://flow.google.com/test",
    artifacts: [{ path: outPath, metadataPath: `${outPath}.json` }]
  };
}

describe("Orchestrator Profile Rotation & Resumption", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-orch-test-"));
    process.env.GFLOW_PROFILE_STATES_PATH = join(tempDir, "profile-states.json");
  });

  afterEach(async () => {
    delete process.env.GFLOW_PROFILE_STATES_PATH;
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  it("rotates to next ready profile when encountering RateLimitedError", async () => {
    const executedProfiles: string[] = [];
    const job = createMockJob("shot-1", tempDir);

    const mockAutomationFactory = vi.fn(async (profile: string) => {
      executedProfiles.push(profile);
      const mockAutomation: FlowAutomation = {
        runJob: vi.fn(async () => {
          if (profile === "prof-1") {
            throw new RateLimitedError("Unusual activity on prof-1");
          }
          return createMockResult("shot-1", join(tempDir, "shot-1.png"));
        })
      };
      return {
        automation: mockAutomation,
        close: vi.fn(async () => undefined)
      };
    });

    const orchestrator = new SmartPipelineOrchestrator({
      jobs: [job],
      outDir: tempDir,
      profiles: ["prof-1", "prof-2"],
      automationFactory: mockAutomationFactory,
      autoheal: false
    });

    const result = await orchestrator.run();
    expect(result.status).toBe("completed");
    expect(executedProfiles).toContain("prof-1");
    expect(executedProfiles).toContain("prof-2");
    expect(result.checkpoint.activeProfile).toBe("prof-2");
  });

  it("rotates to next ready profile when encountering CreditLimitError", async () => {
    const executedProfiles: string[] = [];
    const job = createMockJob("shot-1", tempDir);

    const mockAutomationFactory = vi.fn(async (profile: string) => {
      executedProfiles.push(profile);
      const mockAutomation: FlowAutomation = {
        runJob: vi.fn(async () => {
          if (profile === "p-alpha") {
            throw new CreditLimitError("No compute credits left");
          }
          return createMockResult("shot-1", join(tempDir, "shot-1.png"));
        })
      };
      return {
        automation: mockAutomation,
        close: vi.fn(async () => undefined)
      };
    });

    const orchestrator = new SmartPipelineOrchestrator({
      jobs: [job],
      outDir: tempDir,
      profiles: ["p-alpha", "p-beta"],
      automationFactory: mockAutomationFactory,
      autoheal: false
    });

    const result = await orchestrator.run();
    expect(result.status).toBe("completed");
    expect(executedProfiles).toEqual(["p-alpha", "p-beta"]);
    expect(result.checkpoint.activeProfile).toBe("p-beta");
  });

  it("immediately throws ProfilePoolExhaustedError when all profiles are rate-limited or exhausted", async () => {
    const job = createMockJob("shot-1", tempDir);

    const mockAutomationFactory = vi.fn(async (profile: string) => {
      const mockAutomation: FlowAutomation = {
        runJob: vi.fn(async () => {
          throw new RateLimitedError(`Rate limited on ${profile}`);
        })
      };
      return {
        automation: mockAutomation,
        close: vi.fn(async () => undefined)
      };
    });

    const orchestrator = new SmartPipelineOrchestrator({
      jobs: [job],
      outDir: tempDir,
      profiles: ["acc-1", "acc-2"],
      automationFactory: mockAutomationFactory,
      autoheal: false,
      maxRetriesPerJob: 3
    });

    await expect(orchestrator.run()).rejects.toThrow(ProfilePoolExhaustedError);
  });

  it("restores activeProfile on checkpoint resumption", async () => {
    const job1 = createMockJob("job-1", tempDir);
    const job2 = createMockJob("job-2", tempDir);

    const factory1 = vi.fn(async (profile: string) => {
      return {
        automation: {
          runJob: vi.fn(async () => {
            if (profile === "acc-1") {
              throw new RateLimitedError("Rate limit");
            }
            return createMockResult("job-1", join(tempDir, "job-1.png"));
          })
        },
        close: vi.fn(async () => undefined)
      };
    });

    // Run 1: job 1 fails on acc-1, rotates to acc-2, succeeds
    const orch1 = new SmartPipelineOrchestrator({
      jobs: [job1],
      outDir: tempDir,
      profiles: ["acc-1", "acc-2"],
      automationFactory: factory1,
      autoheal: false
    });
    await orch1.run();

    const cp = await loadCheckpoint(tempDir);
    expect(cp?.activeProfile).toBe("acc-2");

    // Run 2 with resume: should pick up acc-2 directly
    const factory2 = vi.fn(async (profile: string) => {
      expect(profile).toBe("acc-2");
      return {
        automation: {
          runJob: vi.fn(async () => createMockResult("job-2", join(tempDir, "job-2.png")))
        },
        close: vi.fn(async () => undefined)
      };
    });

    const orch2 = new SmartPipelineOrchestrator({
      jobs: [job1, job2],
      outDir: tempDir,
      profiles: ["acc-1", "acc-2"],
      automationFactory: factory2,
      resume: true,
      autoheal: false
    });

    const result2 = await orch2.run();
    expect(result2.status).toBe("completed");
    expect(factory2).toHaveBeenCalledWith("acc-2");
  });
});
