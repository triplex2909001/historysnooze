import { mkdtemp, rm, writeFile, readdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { describe, expect, it, beforeEach, afterEach } from "vitest";
import {
  CHECKPOINT_FILE_NAME,
  createInitialCheckpoint,
  isJobCompleted,
  loadCheckpoint,
  writeAtomicJson,
  recordJobSuccess
} from "../src/jobs/checkpoint.js";
import { SmartPipelineOrchestrator } from "../src/jobs/orchestrator.js";
import { createProgram } from "../src/cli.js";
import type { FlowAutomation, FlowJobResult } from "../src/flow/types.js";
import type { GFlowJob } from "../src/jobs/schema.js";

interface MockJobOverrides {
  type?: "image" | "video";
  prompt?: string;
  outputs?: number;
  ingredients?: string[];
  character?: string[];
  startFrame?: string;
  endFrame?: string;
  duration?: number;
  retry?: number;
}

function createMockJob(
  id: string,
  outDir: string,
  overrides: MockJobOverrides = {}
): GFlowJob {
  const type = overrides.type ?? "image";
  if (type === "video") {
    return {
      id,
      type: "video",
      prompt: overrides.prompt ?? `Mock prompt for ${id}`,
      outputs: overrides.outputs ?? 1,
      out: outDir,
      ingredients: overrides.ingredients ?? [],
      character: overrides.character ?? [],
      startFrame: overrides.startFrame,
      endFrame: overrides.endFrame,
      duration: overrides.duration,
      retry: overrides.retry
    };
  }
  return {
    id,
    type: "image",
    prompt: overrides.prompt ?? `Mock prompt for ${id}`,
    outputs: overrides.outputs ?? 1,
    out: outDir,
    ingredients: overrides.ingredients ?? [],
    character: overrides.character ?? [],
    retry: overrides.retry
  };
}

function createMockResult(jobId: string, outPath: string): FlowJobResult {
  return {
    jobId,
    flowUrl: "https://flow.google.com/test",
    artifacts: [{ path: outPath, metadataPath: `${outPath}.json` }]
  };
}

describe("Milestone 3 Empirical Stress Tests: Checkpoint & Shutdown", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-m3-stress-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  // =========================================================================
  // TASK 1.1: Rapid concurrent writes to checkpoint.json
  // =========================================================================
  describe("1.1 Rapid Concurrent Checkpoint Writes", () => {
    it("survives 100 concurrent atomic writes with zero corruption or dangling tmp files", async () => {
      const targetFile = join(tempDir, "checkpoint.json");
      const writeCount = 100;
      const payloads = Array.from({ length: writeCount }, (_, i) => ({
        iteration: i,
        timestamp: new Date().toISOString(),
        payload: "x".repeat(1024 * (i % 10 + 1)), // varying size up to 10KB
        completedJobs: {
          [`job-${i}`]: {
            status: "completed",
            artifacts: [`/path/to/artifact-${i}.png`],
            completedAt: new Date().toISOString()
          }
        }
      }));

      // Fire 100 concurrent writes
      const results = await Promise.allSettled(
        payloads.map((payload) => writeAtomicJson(targetFile, payload))
      );

      // Verify all writes succeeded
      for (const res of results) {
        expect(res.status).toBe("fulfilled");
      }

      // Verify the final file is strictly valid JSON and matches one of the written payloads
      expect(existsSync(targetFile)).toBe(true);
      const fileContent = await readFile(targetFile, "utf8");
      let parsed: Record<string, unknown> = {};
      expect(() => {
        parsed = JSON.parse(fileContent) as Record<string, unknown>;
      }).not.toThrow();

      expect(parsed).toHaveProperty("iteration");
      expect(typeof parsed.iteration).toBe("number");
      expect(Number(parsed.iteration)).toBeGreaterThanOrEqual(0);
      expect(Number(parsed.iteration)).toBeLessThan(writeCount);
      expect(parsed).toHaveProperty("completedJobs");

      // Verify no temporary files (.tmp) linger in the target directory
      const directoryFiles = await readdir(tempDir);
      const tmpFiles = directoryFiles.filter((f) => f.includes(".tmp"));
      expect(tmpFiles).toHaveLength(0);
      expect(directoryFiles).toContain("checkpoint.json");
    });
  });

  // =========================================================================
  // TASK 1.2: Missing disk artifacts -> job invalidated from cache & scheduled for re-exec
  // =========================================================================
  describe("1.2 Missing Disk Artifacts Invalidation & Re-execution", () => {
    it("invalidates job from checkpoint when artifact deleted, and orchestrator re-executes it", async () => {
      const art1 = join(tempDir, "art1.png");
      const art2 = join(tempDir, "art2.png");
      await writeFile(art1, "fake image 1");
      await writeFile(art2, "fake image 2");

      // Seed checkpoint with both jobs completed
      const cp = createInitialCheckpoint("test-pipe");
      await recordJobSuccess(tempDir, cp, "shot-1", [art1]);
      await recordJobSuccess(tempDir, cp, "shot-2", [art2]);

      // Verify both are originally completed
      const initialLoaded = await loadCheckpoint(tempDir);
      expect(isJobCompleted(initialLoaded, "shot-1")).toBe(true);
      expect(isJobCompleted(initialLoaded, "shot-2")).toBe(true);

      // DELETE art2 from disk
      await rm(art2);

      // Reload checkpoint -> shot-2 must be invalidated
      const reloaded = await loadCheckpoint(tempDir, { verifyArtifactsOnDisk: true });
      expect(isJobCompleted(reloaded, "shot-1")).toBe(true);
      expect(isJobCompleted(reloaded, "shot-2")).toBe(false);
      expect(reloaded?.completedJobs["shot-2"]).toBeUndefined();

      // Now run SmartPipelineOrchestrator with resume: true
      const executedJobs: string[] = [];
      const fakeAutomation: FlowAutomation = {
        runJob: async ({ job, outDir }: { job: GFlowJob; outDir: string }) => {
          executedJobs.push(job.id);
          const outPath = join(outDir, `${job.id}.png`);
          await writeFile(outPath, `regenerated ${job.id}`);
          return createMockResult(job.id, outPath);
        }
      };

      const orchestrator = new SmartPipelineOrchestrator({
        jobs: [
          createMockJob("shot-1", tempDir, { prompt: "first shot" }),
          createMockJob("shot-2", tempDir, { prompt: "second shot" })
        ],
        outDir: tempDir,
        resume: true,
        automationFactory: async () => ({
          automation: fakeAutomation,
          close: async () => {}
        })
      });

      const runResult = await orchestrator.run();
      expect(runResult.status).toBe("completed");

      // shot-1 was cached on disk, so it MUST NOT be re-executed
      // shot-2 was missing from disk, so it MUST be re-executed!
      expect(executedJobs).toEqual(["shot-2"]);

      // After completion, shot-2 artifact is restored and checkpoint has both
      expect(existsSync(join(tempDir, "shot-2.png"))).toBe(true);
      expect(isJobCompleted(runResult.checkpoint, "shot-1")).toBe(true);
      expect(isJobCompleted(runResult.checkpoint, "shot-2")).toBe(true);
    });
  });

  // =========================================================================
  // TASK 1.3: Resume pipeline with partial checkpoint & $output:<job_id> resolution
  // =========================================================================
  describe("1.3 Resumption with Partial Checkpoint and $output:<job_id> resolution", () => {
    it("skips completed jobs and resolves $output:<job_id> downstream from checkpoint artifacts", async () => {
      const shot1Art = join(tempDir, "shot-1.png");
      await writeFile(shot1Art, "upstream artifact data");

      // Seed checkpoint with shot-1 completed
      const cp = createInitialCheckpoint("chain-pipeline");
      await recordJobSuccess(tempDir, cp, "shot-1", [shot1Art]);

      const executedJobs: GFlowJob[] = [];
      const fakeAutomation: FlowAutomation = {
        runJob: async ({ job, outDir }: { job: GFlowJob; outDir: string }) => {
          executedJobs.push(job);
          const outPath = join(outDir, `${job.id}.png`);
          await writeFile(outPath, `output of ${job.id}`);
          return createMockResult(job.id, outPath);
        }
      };

      const jobs: GFlowJob[] = [
        createMockJob("shot-1", tempDir, {
          prompt: "first shot"
        }),
        createMockJob("shot-2", tempDir, {
          prompt: "second shot using shot 1",
          ingredients: ["$output:shot-1"]
        }),
        createMockJob("shot-3", tempDir, {
          type: "video",
          prompt: "third shot video starting from shot 1",
          startFrame: "$output:shot-1"
        })
      ];

      const orchestrator = new SmartPipelineOrchestrator({
        jobs,
        outDir: tempDir,
        resume: true,
        automationFactory: async () => ({
          automation: fakeAutomation,
          close: async () => {}
        })
      });

      const result = await orchestrator.run();
      expect(result.status).toBe("completed");

      // Verify shot-1 was SKIPPED completely
      const executedIds = executedJobs.map((j) => j.id);
      expect(executedIds).toEqual(["shot-2", "shot-3"]);

      // Verify shot-2 ingredients resolved $output:shot-1 to the exact artifact path on disk
      const executedShot2 = executedJobs.find((j) => j.id === "shot-2");
      expect(executedShot2?.ingredients).toEqual([shot1Art]);

      // Verify shot-3 startFrame resolved $output:shot-1 to the exact artifact path
      const executedShot3 = executedJobs.find((j) => j.id === "shot-3");
      if (executedShot3 && executedShot3.type === "video") {
        expect(executedShot3.startFrame).toBe(shot1Art);
      }

      // Verify final checkpoint records all 3 jobs as completed
      expect(isJobCompleted(result.checkpoint, "shot-1")).toBe(true);
      expect(isJobCompleted(result.checkpoint, "shot-2")).toBe(true);
      expect(isJobCompleted(result.checkpoint, "shot-3")).toBe(true);
    });
  });

  // =========================================================================
  // TASK 1.4: Test --no-checkpoint flag: verify no checkpoint is read or written
  // =========================================================================
  describe("1.4 --no-checkpoint Flag Behavior", () => {
    it("verifies --no-checkpoint does not resume from existing checkpoint", async () => {
      // Create pipeline YAML
      const pipelineYaml = join(tempDir, "test-pipeline.yaml");
      await writeFile(
        pipelineYaml,
        `
pipeline: no-cp-test
jobs:
  - id: shot-1
    type: image
    prompt: establishing shot
`
      );

      // Seed existing checkpoint with shot-1 completed
      const artPath = join(tempDir, "shot-1.png");
      await writeFile(artPath, "existing image");
      const cp = createInitialCheckpoint("no-cp-test");
      await recordJobSuccess(tempDir, cp, "shot-1", [artPath]);

      let runCount = 0;
      const fakeAutomation: FlowAutomation = {
        runJob: async ({ job }: { job: GFlowJob }) => {
          runCount++;
          return createMockResult(job.id, artPath);
        }
      };

      const program = createProgram({ automation: fakeAutomation });
      program.configureOutput({ writeErr: () => {}, writeOut: () => {} });

      // Run with --no-checkpoint
      await program.parseAsync([
        "node",
        "gflow",
        "run",
        pipelineYaml,
        "--no-checkpoint",
        "--output-dir",
        tempDir
      ]);

      // When --no-checkpoint is passed, it must NOT skip shot-1
      expect(runCount).toBe(1);
    });

    it("evaluates whether --no-checkpoint prevents writing checkpoint.json to disk", async () => {
      const freshDir = join(tempDir, "no-checkpoint-write-test");
      const pipelineYaml = join(tempDir, "fresh-pipeline.yaml");
      await writeFile(
        pipelineYaml,
        `
pipeline: fresh-test
jobs:
  - id: fresh-shot-1
    type: image
    prompt: test fresh shot
`
      );

      const fakeAutomation: FlowAutomation = {
        runJob: async ({ job, outDir }: { job: GFlowJob; outDir: string }) => {
          const p = join(outDir, `${job.id}.png`);
          await writeFile(p, "data");
          return createMockResult(job.id, p);
        }
      };

      const program = createProgram({ automation: fakeAutomation });
      program.configureOutput({ writeErr: () => {}, writeOut: () => {} });

      await program.parseAsync([
        "node",
        "gflow",
        "run",
        pipelineYaml,
        "--no-checkpoint",
        "--output-dir",
        freshDir
      ]);

      const checkpointFile = join(freshDir, CHECKPOINT_FILE_NAME);
      const checkpointExists = existsSync(checkpointFile);

      // Requirement: "--no-checkpoint flag: verify no checkpoint is read or written."
      // If checkpointExists is true, then checkpoint WAS written despite --no-checkpoint flag!
      console.log(`[EMPIRICAL PROOF] Checkpoint file exists after --no-checkpoint run: ${checkpointExists}`);
      expect(checkpointExists, "checkpoint.json should NOT be written when --no-checkpoint is specified").toBe(false);
    });
  });

  // =========================================================================
  // TASK 2: Stress test shutdown: SIGINT, SIGTERM, re-entrant force exit, checkpoint preservation
  // =========================================================================
  describe("2. Shutdown & Signal Handling", () => {
    it("verifies registerGracefulShutdown exits with 130 on SIGINT in child process", async () => {
      const childScript = join(tempDir, "sigint-worker.mjs");
      await writeFile(
        childScript,
        `
import { registerGracefulShutdown } from "${join(process.cwd(), "src/jobs/checkpoint.ts")}";
registerGracefulShutdown(async (signal) => {
  await new Promise((r) => setTimeout(r, 100));
});
process.stdout.write("READY\\n");
setInterval(() => {}, 1000);
`
      );

      const child = spawn(process.execPath, ["--import", "tsx", childScript], {
        stdio: ["ignore", "pipe", "pipe"]
      });

      await new Promise<void>((resolve, reject) => {
        child.stdout.on("data", (data) => {
          if (data.toString().includes("READY")) {
            resolve();
          }
        });
        child.on("error", reject);
      });

      // Send SIGINT
      child.kill("SIGINT");

      const exitCode = await new Promise<number | null>((resolve) => {
        child.on("exit", (code) => resolve(code));
      });

      expect(exitCode).toBe(130);
    });

    it("verifies registerGracefulShutdown exits with 143 on SIGTERM in child process", async () => {
      const childScript = join(tempDir, "sigterm-worker.mjs");
      await writeFile(
        childScript,
        `
import { registerGracefulShutdown } from "${join(process.cwd(), "src/jobs/checkpoint.ts")}";
registerGracefulShutdown(async (signal) => {
  await new Promise((r) => setTimeout(r, 100));
});
process.stdout.write("READY\\n");
setInterval(() => {}, 1000);
`
      );

      const child = spawn(process.execPath, ["--import", "tsx", childScript], {
        stdio: ["ignore", "pipe", "pipe"]
      });

      await new Promise<void>((resolve, reject) => {
        child.stdout.on("data", (data) => {
          if (data.toString().includes("READY")) {
            resolve();
          }
        });
        child.on("error", reject);
      });

      // Send SIGTERM
      child.kill("SIGTERM");

      const exitCode = await new Promise<number | null>((resolve) => {
        child.on("exit", (code) => resolve(code));
      });

      expect(exitCode).toBe(143);
    });

    it("verifies re-entrant signal triggers immediate force exit without waiting for slow handler", async () => {
      const childScript = join(tempDir, "reentrant-worker.mjs");
      await writeFile(
        childScript,
        `
import { registerGracefulShutdown } from "${join(process.cwd(), "src/jobs/checkpoint.ts")}";
let handlerFinished = false;
registerGracefulShutdown(async (signal) => {
  // Slow shutdown handler (5 seconds)
  await new Promise((r) => setTimeout(r, 5000));
  handlerFinished = true;
});
process.stdout.write("READY\\n");
setInterval(() => {}, 1000);
`
      );

      const child = spawn(process.execPath, ["--import", "tsx", childScript], {
        stdio: ["ignore", "pipe", "pipe"]
      });

      await new Promise<void>((resolve, reject) => {
        child.stdout.on("data", (data) => {
          if (data.toString().includes("READY")) {
            resolve();
          }
        });
        child.on("error", reject);
      });

      const startTime = Date.now();

      // Send first SIGINT
      child.kill("SIGINT");

      // Give 50ms then send second SIGINT (re-entrant!)
      await new Promise((r) => setTimeout(r, 50));
      child.kill("SIGINT");

      const exitCode = await new Promise<number | null>((resolve) => {
        child.on("exit", (code) => resolve(code));
      });
      const elapsed = Date.now() - startTime;

      // Must exit immediately (< 1000ms), NOT wait for the 5000ms slow handler
      expect(elapsed).toBeLessThan(1500);
      expect(exitCode).toBe(130);
    });

    it("verifies active checkpoint state is preserved on interrupt during pipeline execution", async () => {
      const pipelineOut = join(tempDir, "pipeline-out");
      const childScript = join(tempDir, "interrupt-orchestrator.mjs");

      await writeFile(
        childScript,
        `
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { SmartPipelineOrchestrator } from "${join(process.cwd(), "src/jobs/orchestrator.ts")}";

const outDir = "${pipelineOut}";

const fakeAutomation = {
  runJob: async ({ job, outDir }) => {
    const p = join(outDir, job.id + ".png");
    await writeFile(p, "data for " + job.id);
    if (job.id === "job-1") {
      process.stdout.write("JOB1_DONE\\n");
      return { id: job.id, success: true, artifacts: [{ path: p, type: "image" }] };
    }
    if (job.id === "job-2") {
      process.stdout.write("JOB2_STARTED\\n");
      // Simulate slow job waiting for signal
      await new Promise((r) => setTimeout(r, 10000));
      return { id: job.id, success: true, artifacts: [{ path: p, type: "image" }] };
    }
    return { id: job.id, success: true, artifacts: [] };
  }
};

const orchestrator = new SmartPipelineOrchestrator({
  jobs: [
    { id: "job-1", type: "image", prompt: "first", out: outDir },
    { id: "job-2", type: "image", prompt: "second", out: outDir }
  ],
  outDir,
  resume: false,
  automationFactory: async () => ({ automation: fakeAutomation, close: async () => {} })
});

await orchestrator.run();
`
      );

      const child = spawn(process.execPath, ["--import", "tsx", childScript], {
        stdio: ["ignore", "pipe", "pipe"]
      });

      // Wait until job-2 starts
      let errOutput = "";
      child.stderr.on("data", (d) => { errOutput += d.toString(); });
      await new Promise<void>((resolve, reject) => {
        child.stdout.on("data", (data) => {
          const str = data.toString();
          if (str.includes("JOB2_STARTED")) {
            resolve();
          }
        });
        child.on("exit", (code) => {
          reject(new Error(`Child exited early with code ${code}. Stderr: ${errOutput}`));
        });
        child.on("error", reject);
      });

      // Send SIGINT
      child.kill("SIGINT");

      const exitCode = await new Promise<number | null>((resolve) => {
        child.on("exit", (code) => resolve(code));
      });

      expect(exitCode).toBe(130);

      // Verify active checkpoint state on disk
      const checkpointPath = join(pipelineOut, CHECKPOINT_FILE_NAME);
      expect(existsSync(checkpointPath)).toBe(true);

      const raw = await readFile(checkpointPath, "utf8");
      const cp = JSON.parse(raw);

      // job-1 should be completed
      expect(cp.completedJobs["job-1"]).toBeDefined();
      expect(cp.completedJobs["job-1"].status).toBe("completed");

      // currentJobId should record job-2
      expect(cp.currentJobId).toBe("job-2");
    });

    it("verifies watchdog timeout forcibly exits when shutdown handler hangs", async () => {
      const childScript = join(tempDir, "watchdog-worker.mjs");
      await writeFile(
        childScript,
        `
import { registerGracefulShutdown } from "${join(process.cwd(), "src/jobs/checkpoint.ts")}";
registerGracefulShutdown({
  timeoutMs: 400,
  onShutdown: async () => {
    // Hang forever
    await new Promise(() => {});
  }
});
process.stdout.write("READY\\n");
setInterval(() => {}, 1000);
`
      );

      const child = spawn(process.execPath, ["--import", "tsx", childScript], {
        stdio: ["ignore", "pipe", "pipe"]
      });

      await new Promise<void>((resolve, reject) => {
        child.stdout.on("data", (data) => {
          if (data.toString().includes("READY")) resolve();
        });
        child.on("error", reject);
      });

      const startTime = Date.now();
      child.kill("SIGINT");

      const exitCode = await new Promise<number | null>((resolve) => {
        child.on("exit", (code) => resolve(code));
      });
      const elapsed = Date.now() - startTime;

      // Watchdog timeout was 400ms -> should exit around 400-800ms
      expect(elapsed).toBeGreaterThanOrEqual(350);
      expect(elapsed).toBeLessThan(2000);
      expect(exitCode).toBe(130);
    });
  });

  // =========================================================================
  // TASK 3: Corrupted Checkpoint Recovery
  // =========================================================================
  describe("3. Resilience Against Corrupted & Empty Checkpoints", () => {
    it("gracefully recovers from truncated/corrupted checkpoint.json", async () => {
      const checkpointFile = join(tempDir, CHECKPOINT_FILE_NAME);
      // Malformed truncated JSON
      await writeFile(checkpointFile, '{"version":"1.0", "pipeline": "broken", "completedJobs": { "shot-1": {');

      const loaded = await loadCheckpoint(tempDir);
      expect(loaded).toBeNull();

      // Orchestrator starts with fresh checkpoint rather than crashing
      const fakeAutomation: FlowAutomation = {
        runJob: async ({ job, outDir }: { job: GFlowJob; outDir: string }) => {
          const p = join(outDir, `${job.id}.png`);
          await writeFile(p, "data");
          return createMockResult(job.id, p);
        }
      };

      const orchestrator = new SmartPipelineOrchestrator({
        jobs: [createMockJob("shot-1", tempDir, { prompt: "test" })],
        outDir: tempDir,
        resume: true,
        automationFactory: async () => ({ automation: fakeAutomation, close: async () => {} })
      });

      const result = await orchestrator.run();
      expect(result.status).toBe("completed");
      expect(isJobCompleted(result.checkpoint, "shot-1")).toBe(true);
    });

    it("handles zero-byte checkpoint file cleanly without crashing", async () => {
      const checkpointFile = join(tempDir, CHECKPOINT_FILE_NAME);
      await writeFile(checkpointFile, "");

      const loaded = await loadCheckpoint(tempDir);
      expect(loaded).toBeNull();
    });
  });
});
