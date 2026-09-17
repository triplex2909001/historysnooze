import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { ProfilePool } from "../src/browser/profile-pool.js";
import {
  listDiscoveredProfiles,
  getProfileRecord,
  formatProfileStatusTable,
  resetProfileState
} from "../src/browser/profile-status.js";
import {
  ProfilePoolExhaustedError,
  RateLimitedError,
  CreditLimitError,
  exitCodeForError,
  LoginRequiredError,
  ManualActionRequiredError,
  UiContractError,
  GenerationBlockedError,
  GenerationFailedError,
  DownloadError
} from "../src/errors.js";
import { SmartPipelineOrchestrator } from "../src/jobs/orchestrator.js";
import type { FlowAutomation, FlowJobResult } from "../src/flow/types.js";
import type { GFlowJob } from "../src/jobs/schema.js";

function createMockJob(id: string, outDir: string, retry?: number): GFlowJob {
  return {
    id,
    type: "image",
    prompt: "Test prompt",
    outputs: 1,
    out: outDir,
    ingredients: [],
    character: [],
    retry
  };
}

function createMockResult(jobId: string, outPath: string): FlowJobResult {
  return {
    jobId,
    flowUrl: "https://flow.google.com/test",
    artifacts: [{ path: outPath, metadataPath: `${outPath}.json` }]
  };
}

describe("Empirical Challenge: Profile Pooling, Rotation, Rate Limiting & Exhaustion", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-chal-pool-"));
    process.env.GFLOW_PROFILE_STATES_PATH = join(tempDir, "profile-states.json");
  });

  afterEach(async () => {
    delete process.env.GFLOW_PROFILE_STATES_PATH;
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  // -------------------------------------------------------------------------
  // 1. Multiple Rate-Limited Profiles Cycling to Next Ready Profile
  // -------------------------------------------------------------------------
  describe("Dimension 1: Multiple Rate-Limited Profiles Cycling", () => {
    it("cycles through multiple rate-limited profiles until finding a ready one in ProfilePool", async () => {
      const pool = new ProfilePool({ profiles: ["p1", "p2", "p3", "p4", "p5"] });
      expect(pool.getActiveProfile()).toBe("p1");

      // Rate-limit p1, p2, p3
      await pool.markRateLimited("p1", 60000);
      await pool.markRateLimited("p2", 60000);
      await pool.markRateLimited("p3", 60000);

      // p1 is active and cooling down, acquireHealthyProfile should rotate past p2, p3 to p4
      const healthy = await pool.acquireHealthyProfile();
      expect(healthy).toBe("p4");
      expect(pool.getActiveProfile()).toBe("p4");

      // Now rate limit p4 as well -> should rotate to p5
      await pool.markRateLimited("p4", 60000);
      const nextHealthy = await pool.acquireHealthyProfile();
      expect(nextHealthy).toBe("p5");
      expect(pool.getActiveProfile()).toBe("p5");
    });

    it("Orchestrator: rotates through 3 rate-limited profiles on a single job without premature termination", async () => {
      // 4 profiles: p1, p2, p3 will be rate limited, p4 will succeed.
      // Default maxRetriesPerJob is 2. If attempt count is burned on rotation, p4 will NEVER be reached!
      const attemptedProfiles: string[] = [];
      const job = createMockJob("job-cycle", tempDir, 2);

      const mockAutomationFactory = vi.fn(async (profile: string) => {
        attemptedProfiles.push(profile);
        const mockAutomation: FlowAutomation = {
          runJob: vi.fn(async () => {
            if (profile === "p1" || profile === "p2" || profile === "p3") {
              throw new RateLimitedError(`Rate limit on ${profile}`);
            }
            return createMockResult("job-cycle", join(tempDir, "job-cycle.png"));
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
        profiles: ["p1", "p2", "p3", "p4"],
        automationFactory: mockAutomationFactory,
        autoheal: false,
        maxRetriesPerJob: 2
      });

      const result = await orchestrator.run();
      expect(result.status).toBe("completed");
      expect(attemptedProfiles).toEqual(["p1", "p2", "p3", "p4"]);
      expect(result.checkpoint.activeProfile).toBe("p4");
    });

    it("Orchestrator: with 4 profiles all rate-limited and maxRetries=2, fails to throw ProfilePoolExhaustedError if loop terminates early", async () => {
      const job = createMockJob("job-all-fail", tempDir, 2);

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
        profiles: ["p1", "p2", "p3", "p4"],
        automationFactory: mockAutomationFactory,
        autoheal: false,
        maxRetriesPerJob: 2
      });

      // It SHOULD throw ProfilePoolExhaustedError, but because attempt burns on rotation:
      // Does it throw ProfilePoolExhaustedError or exit silently?
      await expect(orchestrator.run()).rejects.toThrow(ProfilePoolExhaustedError);
    });
  });

  // -------------------------------------------------------------------------
  // 2. All Profiles in Cooldown -> ProfilePoolExhaustedError with Exact Cooldown
  // -------------------------------------------------------------------------
  describe("Dimension 2: All Profiles in Cooldown Escalation", () => {
    it("throws ProfilePoolExhaustedError with exact cooldown remaining and earliest available profile", async () => {
      const pool = new ProfilePool({ profiles: ["acc-a", "acc-b", "acc-c"] });

      // Set distinct cooldown durations:
      // acc-a: 10,000ms
      // acc-b: 50,000ms
      // acc-c: 25,000ms
      await pool.markRateLimited("acc-a", 10000);
      await pool.markRateLimited("acc-b", 50000);
      await pool.markRateLimited("acc-c", 25000);

      try {
        await pool.acquireHealthyProfile();
        expect.unreachable("Should have thrown ProfilePoolExhaustedError");
      } catch (err) {
        expect(err).toBeInstanceOf(ProfilePoolExhaustedError);
        const pErr = err as ProfilePoolExhaustedError;

        expect(pErr.code).toBe("RATE_LIMITED");
        expect(pErr.reason).toBe("rate_limited");
        expect(pErr.summary).toBeDefined();
        expect(pErr.summary?.total).toBe(3);
        expect(pErr.summary?.ready).toEqual([]);
        expect(pErr.summary?.exhausted).toEqual([]);
        expect(pErr.coolingDownProfiles.length).toBe(3);

        // Verify earliestAvailable
        expect(pErr.earliestAvailable).toBeDefined();
        expect(pErr.earliestAvailable?.profile).toBe("acc-a");
        expect(pErr.earliestAvailable?.remainingMs).toBeGreaterThan(0);
        expect(pErr.earliestAvailable?.remainingMs).toBeLessThanOrEqual(10000);

        // Verify exact cooldown remaining is captured for all profiles
        const cdMap = new Map(pErr.coolingDownProfiles.map((c) => [c.profile, c]));
        const cdA = cdMap.get("acc-a");
        const cdB = cdMap.get("acc-b");
        const cdC = cdMap.get("acc-c");

        expect(cdA?.remainingMs).toBeGreaterThan(9000);
        expect(cdB?.remainingMs).toBeGreaterThan(48000);
        expect(cdC?.remainingMs).toBeGreaterThan(23000);

        // Verify exitCodeForError maps it to 5
        expect(exitCodeForError(pErr)).toBe(5);
      }
    });

    it("Orchestrator: throws ProfilePoolExhaustedError immediately when all profiles are in cooldown", async () => {
      const job = createMockJob("job-exhaust", tempDir);

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
        profiles: ["p-1", "p-2"],
        automationFactory: mockAutomationFactory,
        autoheal: false
      });

      await expect(orchestrator.run()).rejects.toThrow(ProfilePoolExhaustedError);

      try {
        await orchestrator.run();
      } catch (err) {
        expect(err).toBeInstanceOf(ProfilePoolExhaustedError);
        const pErr = err as ProfilePoolExhaustedError;
        expect(pErr.reason).toBe("rate_limited");
        expect(pErr.coolingDownProfiles.length).toBe(2);
        expect(exitCodeForError(pErr)).toBe(5);
      }
    });
  });

  // -------------------------------------------------------------------------
  // 3. Credit Exhaustion on One Profile -> Permanent Exclusion
  // -------------------------------------------------------------------------
  describe("Dimension 3: Credit Exhaustion & Permanent Exclusion", () => {
    it("permanently excludes credit_exhausted profile across multiple pool rotation cycles", async () => {
      const pool = new ProfilePool({ profiles: ["c1", "c2", "c3"] });

      // Mark c1 as credit exhausted
      await pool.markCreditExhausted("c1");
      expect(pool.isExhausted("c1")).toBe(true);

      // Acquire healthy: should skip c1 and give c2
      const first = await pool.acquireHealthyProfile();
      expect(first).toBe("c2");

      // Mark c2 rate-limited with very short cooldown
      await pool.markRateLimited("c2", 50);
      const second = await pool.acquireHealthyProfile();
      expect(second).toBe("c3");

      // Mark c3 rate-limited with very short cooldown
      await pool.markRateLimited("c3", 50);

      // Wait 70ms for c2 and c3 cooldowns to expire
      await new Promise((r) => setTimeout(r, 70));

      // c2 and c3 should have auto-recovered, but c1 must STILL be credit_exhausted
      expect(pool.isCoolingDown("c2")).toBe(false);
      expect(pool.isCoolingDown("c3")).toBe(false);
      expect(pool.isExhausted("c1")).toBe(true);

      // Acquire should pick active healthy c3, NEVER exhausted c1
      const third = await pool.acquireHealthyProfile();
      expect(third).toBe("c3");

      // Rotating from c3 must skip exhausted c1 and land on c2
      const fourth = await pool.rotateToNextReady();
      expect(fourth).toBe("c2");

      // Another rotation should skip exhausted c1 and land on c3
      const fifth = await pool.rotateToNextReady();
      expect(fifth).toBe("c3");

      const summary = await pool.getAvailabilitySummary();
      expect(summary.exhausted).toEqual(["c1"]);
    });

    it("Orchestrator: permanent exclusion of credit-exhausted profile across subsequent jobs in batch", async () => {
      const job1 = createMockJob("shot-1", tempDir);
      const job2 = createMockJob("shot-2", tempDir);
      const job3 = createMockJob("shot-3", tempDir);

      const jobRunsOnProfiles: string[] = [];

      const mockAutomationFactory = vi.fn(async (profile: string) => {
        const mockAutomation: FlowAutomation = {
          runJob: vi.fn(async (opts) => {
            jobRunsOnProfiles.push(profile);
            if (profile === "bad-credit") {
              throw new CreditLimitError("No compute units remaining");
            }
            return createMockResult(opts.job.id, join(tempDir, `${opts.job.id}.png`));
          })
        };
        return {
          automation: mockAutomation,
          close: vi.fn(async () => undefined)
        };
      });

      const orchestrator = new SmartPipelineOrchestrator({
        jobs: [job1, job2, job3],
        outDir: tempDir,
        profiles: ["bad-credit", "good-account"],
        automationFactory: mockAutomationFactory,
        autoheal: false
      });

      const result = await orchestrator.run();
      expect(result.status).toBe("completed");

      // bad-credit should only be attempted ONCE at the start of job1, then NEVER again for job2 or job3
      const badCreditAttempts = jobRunsOnProfiles.filter((p) => p === "bad-credit");
      expect(badCreditAttempts.length).toBe(1);

      const goodAccountAttempts = jobRunsOnProfiles.filter((p) => p === "good-account");
      expect(goodAccountAttempts.length).toBe(3); // job1 retry, job2, job3
    });

    it("Orchestrator: should respect profile-states.json on disk at startup rather than assuming all profiles are ready", async () => {
      // Save profile states to disk: "exhausted-acc" is credit_exhausted
      const { saveProfileStates } = await import("../src/browser/profile-status.js");
      await saveProfileStates({
        updatedAt: new Date().toISOString(),
        profiles: {
          "exhausted-acc": {
            name: "exhausted-acc",
            status: "credit_exhausted",
            exhaustedAt: new Date().toISOString(),
            totalGenerated: 5,
            failures: 3
          },
          "ready-acc": {
            name: "ready-acc",
            status: "ready",
            totalGenerated: 2,
            failures: 0
          }
        }
      });

      const job = createMockJob("job-disk-state", tempDir);
      const executedProfiles: string[] = [];

      const mockAutomationFactory = vi.fn(async (profile: string) => {
        executedProfiles.push(profile);
        const mockAutomation: FlowAutomation = {
          runJob: vi.fn(async (opts) => createMockResult(opts.job.id, join(tempDir, `${opts.job.id}.png`)))
        };
        return {
          automation: mockAutomation,
          close: vi.fn(async () => undefined)
        };
      });

      const orchestrator = new SmartPipelineOrchestrator({
        jobs: [job],
        outDir: tempDir,
        profiles: ["exhausted-acc", "ready-acc"],
        automationFactory: mockAutomationFactory,
        autoheal: false
      });

      await orchestrator.run();

      // If orchestrator respected disk state, it would NOT execute on exhausted-acc!
      // It should immediately pick ready-acc!
      expect(executedProfiles).toEqual(["ready-acc"]);
    });
  });

  // -------------------------------------------------------------------------
  // 4. Auto-Recovery when Date.now() >= cooldownUntil
  // -------------------------------------------------------------------------
  describe("Dimension 4: Cooldown Auto-Recovery", () => {
    it("auto-recovers rate-limited profile when cooldown timestamp passes", async () => {
      const pool = new ProfilePool({ profiles: ["rec-1"] });

      // Mark rate-limited with 200ms cooldown
      await pool.markRateLimited("rec-1", 200);

      expect(pool.isCoolingDown("rec-1")).toBe(true);
      expect(pool.coolDownUntil("rec-1")).toBeGreaterThan(Date.now() - 10);

      // Verify acquire fails right now
      await expect(pool.acquireHealthyProfile()).rejects.toThrow(ProfilePoolExhaustedError);

      // Sleep until cooldown expires
      await new Promise((r) => setTimeout(r, 250));

      expect(pool.isCoolingDown("rec-1")).toBe(false);
      expect(pool.coolDownUntil("rec-1")).toBeUndefined();

      // acquireHealthyProfile should succeed now without error
      const recovered = await pool.acquireHealthyProfile();
      expect(recovered).toBe("rec-1");

      // Verify state was persisted as ready
      const rec = await getProfileRecord("rec-1");
      expect(rec.status).toBe("ready");
      expect(rec.cooldownUntil).toBeUndefined();
    });

    it("resets profile state cleanly via resetProfileState", async () => {
      const pool = new ProfilePool({ profiles: ["p-reset"] });
      await pool.markRateLimited("p-reset", 100000);

      expect(pool.isCoolingDown("p-reset")).toBe(true);

      await resetProfileState("p-reset");
      await pool.syncFromDisk();

      expect(pool.isCoolingDown("p-reset")).toBe(false);
      const rec = await getProfileRecord("p-reset");
      expect(rec.status).toBe("ready");
    });
  });

  // -------------------------------------------------------------------------
  // 5. Pool Sizes: Empty Directory, Single Profile, 10+ Profiles
  // -------------------------------------------------------------------------
  describe("Dimension 5: Scale & Boundary Testing", () => {
    it("handles empty profiles directory gracefully and falls back to default", async () => {
      const emptyProfilesDir = join(tempDir, "empty-test");
      await mkdir(join(emptyProfilesDir, ".gflow", "profiles"), { recursive: true });

      const discovered = await listDiscoveredProfiles(emptyProfilesDir);
      expect(discovered).toEqual(["default"]);

      const pool = new ProfilePool({ profiles: discovered });
      expect(pool.getProfiles()).toEqual(["default"]);
      expect(pool.getActiveProfile()).toBe("default");
    });

    it("handles directory with only hidden files or dot directories without creating phantom profiles", async () => {
      const dotDir = join(tempDir, "dot-test");
      const profilesPath = join(dotDir, ".gflow", "profiles");
      await mkdir(join(profilesPath, ".DS_Store"), { recursive: true });
      await mkdir(join(profilesPath, ".tmp_chrome"), { recursive: true });

      const discovered = await listDiscoveredProfiles(dotDir);
      expect(discovered).toEqual(["default"]);
    });

    it("handles single profile pool behavior on rate limit and credit exhaustion", async () => {
      const pool = new ProfilePool({ profiles: ["solo"] });
      expect(pool.getProfiles()).toEqual(["solo"]);
      expect(pool.getActiveProfile()).toBe("solo");

      // Cannot rotate single profile pool
      const rot = await pool.rotateToNextReady();
      expect(rot).toBeNull();

      // Rate limiting solo profile exhausts pool immediately
      await pool.markRateLimited("solo", 10000);
      await expect(pool.acquireHealthyProfile()).rejects.toThrow(ProfilePoolExhaustedError);

      // Reset and credit exhaust
      await resetProfileState("solo");
      await pool.syncFromDisk();
      await pool.markCreditExhausted("solo");
      try {
        await pool.acquireHealthyProfile();
        expect.unreachable("Should throw");
      } catch (err) {
        expect(err).toBeInstanceOf(ProfilePoolExhaustedError);
        const pErr = err as ProfilePoolExhaustedError;
        expect(pErr.reason).toBe("credit_exhausted");
        expect(exitCodeForError(pErr)).toBe(6);
      }
    });

    it("handles 10+ profiles scaling, selective rate limiting, and round-robin cycling", async () => {
      const profileNames = Array.from({ length: 12 }, (_, i) => `worker-${String(i).padStart(2, "0")}`);
      const pool = new ProfilePool({ profiles: profileNames });

      expect(pool.getProfiles().length).toBe(12);
      expect(pool.getActiveProfile()).toBe("worker-00");

      // Rate limit odd-indexed profiles: worker-01, worker-03, worker-05, worker-07, worker-09, worker-11
      for (let i = 1; i < 12; i += 2) {
        await pool.markRateLimited(profileNames[i], 60000);
      }

      // Credit exhaust worker-02 and worker-04
      await pool.markCreditExhausted("worker-02");
      await pool.markCreditExhausted("worker-04");

      // Rate limit the currently active worker-00
      await pool.markRateLimited("worker-00", 60000);

      // Next ready must skip worker-01 (cooldown), worker-02 (exhausted),
      // worker-03 (cooldown), worker-04 (exhausted), worker-05 (cooldown)
      // and land on worker-06!
      const nextHealthy = await pool.acquireHealthyProfile();
      expect(nextHealthy).toBe("worker-06");
      expect(pool.getActiveProfile()).toBe("worker-06");

      // Rotating again should skip worker-07 (cooldown) -> worker-08
      const r1 = await pool.rotateToNextReady();
      expect(r1).toBe("worker-08");

      // Rotating again should skip worker-09 (cooldown) -> worker-10
      const r2 = await pool.rotateToNextReady();
      expect(r2).toBe("worker-10");

      // Rotating again should wrap around, skip worker-11, worker-00..worker-05 -> worker-06
      const r3 = await pool.rotateToNextReady();
      expect(r3).toBe("worker-06");

      const summary = await pool.getAvailabilitySummary();
      expect(summary.total).toBe(12);
      expect(summary.ready).toEqual(["worker-06", "worker-08", "worker-10"]);
      expect(summary.exhausted).toEqual(["worker-02", "worker-04"]);
      expect(summary.coolingDown.length).toBe(7); // 00, 01, 03, 05, 07, 09, 11
    });

    it("deduplicates redundant profile names in constructor", () => {
      const pool = new ProfilePool({ profiles: ["alpha", "beta", "alpha", "gamma", "beta"] });
      expect(pool.getProfiles()).toEqual(["alpha", "beta", "gamma"]);
    });
  });

  // -------------------------------------------------------------------------
  // 6. Exit Codes and Error Diagnostics Verification
  // -------------------------------------------------------------------------
  describe("Dimension 6: Exit Codes and Error Diagnostics", () => {
    it("verifies exit codes for all specific GFlow error types", () => {
      expect(exitCodeForError(new LoginRequiredError())).toBe(2);
      expect(exitCodeForError(new ManualActionRequiredError("consent"))).toBe(2);
      expect(exitCodeForError(new UiContractError("selector changed"))).toBe(3);
      expect(exitCodeForError(new GenerationBlockedError("safety filter"))).toBe(4);
      expect(exitCodeForError(new RateLimitedError("too fast"))).toBe(5);
      expect(exitCodeForError(new CreditLimitError("zero balance"))).toBe(6);
      expect(exitCodeForError(new GenerationFailedError("backend timeout"))).toBe(7);
      expect(exitCodeForError(new DownloadError("failed fetch"))).toBe(8);
      expect(exitCodeForError(new Error("generic error"))).toBe(1);
    });

    it("verifies exit code 6 for credit_exhausted ProfilePoolExhaustedError and 5 for rate_limited/mixed", () => {
      const creditExhaustedError = new ProfilePoolExhaustedError({
        total: 2,
        ready: [],
        coolingDown: [],
        exhausted: ["p1", "p2"]
      });
      expect(creditExhaustedError.reason).toBe("credit_exhausted");
      expect(exitCodeForError(creditExhaustedError)).toBe(6);

      const rateLimitedError = new ProfilePoolExhaustedError({
        total: 2,
        ready: [],
        coolingDown: [{ profile: "p1", coolDownUntil: Date.now() + 10000, remainingMs: 10000 }],
        exhausted: ["p2"],
        earliestAvailable: { profile: "p1", coolDownUntil: Date.now() + 10000, remainingMs: 10000 }
      });
      expect(rateLimitedError.reason).toBe("rate_limited");
      expect(exitCodeForError(rateLimitedError)).toBe(5);

      const mixedError = new ProfilePoolExhaustedError("All profiles failed");
      expect(mixedError.reason).toBe("mixed");
      expect(exitCodeForError(mixedError)).toBe(5);
    });

    it("verifies formatProfileStatusTable generates correct ASCII diagnostic output", () => {
      const records = [
        {
          name: "prof-ready",
          status: "ready" as const,
          totalGenerated: 15,
          failures: 0,
          lastUsed: "2026-09-13T01:00:00.000Z"
        },
        {
          name: "prof-cooling",
          status: "rate_limited" as const,
          cooldownUntil: new Date(Date.now() + 120000).toISOString(),
          totalGenerated: 5,
          failures: 2
        },
        {
          name: "prof-exhausted",
          status: "credit_exhausted" as const,
          exhaustedAt: "2026-09-13T00:30:00.000Z",
          totalGenerated: 3,
          failures: 1
        }
      ];

      const table = formatProfileStatusTable(records);
      expect(table).toContain("Profile");
      expect(table).toContain("Status");
      expect(table).toContain("Cooldown / Quota");
      expect(table).toContain("prof-ready");
      expect(table).toContain("READY");
      expect(table).toContain("prof-cooling");
      expect(table).toContain("RATE_LIMITED");
      expect(table).toContain("left");
      expect(table).toContain("prof-exhausted");
      expect(table).toContain("EXHAUSTED");
      expect(table).toContain("Exhausted at");
    });
  });
});
