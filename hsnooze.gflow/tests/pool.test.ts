import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { ProfilePool } from "../src/browser/profile-pool.js";
import { listDiscoveredProfiles } from "../src/browser/profile-status.js";
import { ProfilePoolExhaustedError } from "../src/errors.js";

describe("ProfilePool & Auto-Discovery", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-pool-test-"));
    process.env.GFLOW_PROFILE_STATES_PATH = join(tempDir, "profile-states.json");
  });

  afterEach(async () => {
    delete process.env.GFLOW_PROFILE_STATES_PATH;
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  describe("listDiscoveredProfiles", () => {
    it("returns ['default'] when .gflow/profiles does not exist", async () => {
      const profiles = await listDiscoveredProfiles(tempDir);
      expect(profiles).toEqual(["default"]);
    });

    it("returns ['default'] when .gflow/profiles exists but is empty", async () => {
      await mkdir(join(tempDir, ".gflow", "profiles"), { recursive: true });
      const profiles = await listDiscoveredProfiles(tempDir);
      expect(profiles).toEqual(["default"]);
    });

    it("discovers named profiles and ignores hidden dot directories", async () => {
      const profilesDir = join(tempDir, ".gflow", "profiles");
      await mkdir(join(profilesDir, "work"), { recursive: true });
      await mkdir(join(profilesDir, "personal"), { recursive: true });
      await mkdir(join(profilesDir, ".hidden-cache"), { recursive: true });

      const profiles = await listDiscoveredProfiles(tempDir);
      expect(profiles).toContain("work");
      expect(profiles).toContain("personal");
      expect(profiles).not.toContain(".hidden-cache");
      // Does NOT inject phantom "default" when named profiles exist
      expect(profiles).not.toContain("default");
    });

    it("includes 'default' if a directory named 'default' actually exists", async () => {
      const profilesDir = join(tempDir, ".gflow", "profiles");
      await mkdir(join(profilesDir, "default"), { recursive: true });
      await mkdir(join(profilesDir, "work"), { recursive: true });

      const profiles = await listDiscoveredProfiles(tempDir);
      expect(profiles).toContain("default");
      expect(profiles).toContain("work");
    });
  });

  describe("ProfilePool Cooldown & Exhaustion Queries", () => {
    it("initializes profiles with ready status", () => {
      const pool = new ProfilePool({ profiles: ["alpha", "beta"] });
      expect(pool.getProfiles()).toEqual(["alpha", "beta"]);
      expect(pool.getActiveProfile()).toBe("alpha");
      expect(pool.isCoolingDown("alpha")).toBe(false);
      expect(pool.isExhausted("alpha")).toBe(false);
      expect(pool.coolDownUntil("alpha")).toBeUndefined();
    });

    it("tracks 30-minute cooldown on rate limiting and auto-recovers after expiration", async () => {
      const pool = new ProfilePool({
        profiles: ["alpha", "beta"],
        rateLimitCooldownMs: 150 // Short cooldown for testing
      });

      await pool.markRateLimited("alpha", 150);

      expect(pool.isCoolingDown("alpha")).toBe(true);
      const until = pool.coolDownUntil("alpha");
      expect(until).toBeDefined();
      expect(typeof until).toBe("number");
      expect(until!).toBeGreaterThan(Date.now() - 10);
      expect(pool.isExhausted("alpha")).toBe(false);

      // Wait for cooldown to expire
      await new Promise((r) => setTimeout(r, 180));

      expect(pool.isCoolingDown("alpha")).toBe(false);
      expect(pool.coolDownUntil("alpha")).toBeUndefined();
    });

    it("marks profile as credit_exhausted without auto-recovery", async () => {
      const pool = new ProfilePool({ profiles: ["alpha", "beta"] });

      await pool.markCreditExhausted("alpha");

      expect(pool.isExhausted("alpha")).toBe(true);
      expect(pool.isCoolingDown("alpha")).toBe(false);

      // Advancing time should NOT reset credit exhaustion
      await new Promise((r) => setTimeout(r, 50));
      expect(pool.isExhausted("alpha")).toBe(true);
    });

    it("rotates to next ready profile, skipping cooling and exhausted profiles", async () => {
      const pool = new ProfilePool({ profiles: ["p1", "p2", "p3"] });
      expect(pool.getActiveProfile()).toBe("p1");

      // Mark p1 in cooldown
      await pool.markRateLimited("p1", 60000);
      const rotated1 = await pool.rotateToNextReady();
      expect(rotated1).toBe("p2");
      expect(pool.getActiveProfile()).toBe("p2");

      // Mark p2 credit exhausted
      await pool.markCreditExhausted("p2");
      const rotated2 = await pool.rotateToNextReady();
      expect(rotated2).toBe("p3");
      expect(pool.getActiveProfile()).toBe("p3");

      // Mark p3 in cooldown -> pool exhausted
      await pool.markRateLimited("p3", 60000);
      const rotated3 = await pool.rotateToNextReady();
      expect(rotated3).toBeNull();
    });

    it("computes availability summary with remaining cooldown and earliest available", async () => {
      const pool = new ProfilePool({ profiles: ["alpha", "beta", "gamma"] });

      await pool.markRateLimited("alpha", 10000);
      await pool.markCreditExhausted("beta");

      const summary = await pool.getAvailabilitySummary();
      expect(summary.total).toBe(3);
      expect(summary.ready).toEqual(["gamma"]);
      expect(summary.exhausted).toEqual(["beta"]);
      expect(summary.coolingDown.length).toBe(1);
      expect(summary.coolingDown[0].profile).toBe("alpha");
      expect(summary.coolingDown[0].remainingMs).toBeGreaterThan(0);
      expect(summary.earliestAvailable?.profile).toBe("alpha");
    });

    it("throws ProfilePoolExhaustedError when acquireHealthyProfile finds no available profile", async () => {
      const pool = new ProfilePool({ profiles: ["p1", "p2"] });

      await pool.markRateLimited("p1", 30000);
      await pool.markCreditExhausted("p2");

      await expect(pool.acquireHealthyProfile()).rejects.toThrow(ProfilePoolExhaustedError);

      try {
        await pool.acquireHealthyProfile();
      } catch (err) {
        expect(err).toBeInstanceOf(ProfilePoolExhaustedError);
        const exhaustedErr = err as ProfilePoolExhaustedError;
        expect(exhaustedErr.summary).toBeDefined();
        expect(exhaustedErr.summary?.coolingDown.map((c) => c.profile)).toContain("p1");
        expect(exhaustedErr.summary?.exhausted).toContain("p2");
        expect(exhaustedErr.reason).toBe("rate_limited");
      }
    });

    it("marks ProfilePoolExhaustedError reason as credit_exhausted when all profiles are exhausted", async () => {
      const pool = new ProfilePool({ profiles: ["p1", "p2"] });

      await pool.markCreditExhausted("p1");
      await pool.markCreditExhausted("p2");

      try {
        await pool.acquireHealthyProfile();
        expect.unreachable("Should have thrown");
      } catch (err) {
        expect(err).toBeInstanceOf(ProfilePoolExhaustedError);
        const exhaustedErr = err as ProfilePoolExhaustedError;
        expect(exhaustedErr.reason).toBe("credit_exhausted");
        expect(exhaustedErr.code).toBe("CREDIT_LIMIT");
      }
    });
  });
});
