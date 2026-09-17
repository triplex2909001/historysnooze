import { describe, expect, it } from "vitest";
import { isRecoverableConnectionError, withAutoheal } from "../src/browser/autoheal.js";
import { ProfilePool } from "../src/browser/profile-pool.js";
import { getProfileRecord, updateProfileRecord } from "../src/browser/profile-status.js";
import { optimizePrompt } from "../src/engine/prompt-optimizer.js";
import { planSceneExtension } from "../src/engine/scene-extender.js";
import { buildBatchYamlFromScript, parseRawScript } from "../src/engine/scriptwriter.js";
import {
  createInitialCheckpoint,
  isJobCompleted,
  loadCheckpoint,
  recordJobFailure,
  recordJobSuccess,
  saveCheckpoint
} from "../src/jobs/checkpoint.js";
import { interpolateJobParameters, resolveJobOrder } from "../src/jobs/orchestrator.js";
import { parseJob, type GFlowJob } from "../src/jobs/schema.js";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

describe("Subagent 1: Autoheal & Connection Recovery", () => {
  it("correctly identifies recoverable CDP and network errors", () => {
    expect(isRecoverableConnectionError(new Error("Target closed"))).toBe(true);
    expect(isRecoverableConnectionError(new Error("Session closed"))).toBe(true);
    expect(isRecoverableConnectionError(new Error("net::ERR_INTERNET_DISCONNECTED"))).toBe(true);
    expect(isRecoverableConnectionError(new Error("SingletonLock"))).toBe(true);
    expect(isRecoverableConnectionError(new Error("Some random application error"))).toBe(false);
  });

  it("retries and heals on transient failure with withAutoheal", async () => {
    let callCount = 0;
    let healCount = 0;

    const action = async () => {
      callCount++;
      if (callCount < 2) {
        throw new Error("Target closed due to crash");
      }
      return "success_result";
    };

    const onHeal = async () => {
      healCount++;
    };

    const res = await withAutoheal(action, onHeal, { maxRetries: 3, backoffMs: 10 });
    expect(res).toBe("success_result");
    expect(callCount).toBe(2);
    expect(healCount).toBe(1);
  });

  it("persists and restores job checkpoint state across pipeline interruptions", async () => {
    const tempDir = await mkdtemp(join(tmpdir(), "gflow-chk-"));
    try {
      const state = createInitialCheckpoint("test-pipeline", "acc1");
      expect(isJobCompleted(state, "job_01")).toBe(false);

      await recordJobSuccess(tempDir, state, "job_01", ["/path/to/vid1.mp4"]);
      expect(isJobCompleted(state, "job_01")).toBe(true);

      await recordJobFailure(tempDir, state, "job_02", "Quota exceeded", "acc1");
      expect(state.failed).toHaveLength(1);
      expect(state.failed[0].id).toBe("job_02");

      const loaded = await loadCheckpoint(tempDir);
      expect(loaded).not.toBeNull();
      expect(loaded?.completed).toContain("job_01");
      expect(loaded?.artifacts["job_01"]).toEqual(["/path/to/vid1.mp4"]);
    } finally {
      await rm(tempDir, { recursive: true, force: true });
    }
  });
});

describe("Subagent 2: Multi-Account Profile Rotation", () => {
  it("rotates to next ready profile when current profile exhausts credit", async () => {
    const pool = new ProfilePool({ profiles: ["acc_alpha", "acc_beta", "acc_gamma"] });
    expect(pool.getActiveProfile()).toBe("acc_alpha");

    // Setup statuses
    await updateProfileRecord("acc_alpha", { status: "ready" });
    await updateProfileRecord("acc_beta", { status: "ready" });

    // Mark alpha credit exhausted
    await pool.markCreditExhausted();
    const rotated = await pool.rotateToNextReady();

    expect(rotated).toBe("acc_beta");
    expect(pool.getActiveProfile()).toBe("acc_beta");
  });
});

describe("Subagent 3: AI Scriptwriter & Prompt Engine", () => {
  it("parses raw multi-scene script and extracts characters and camera cues", () => {
    const script = `
# Neo Tokyo Cyberpunk
Scene 1: [Kael] steps into the neon rain. Camera tracking shot following him.
Scene 2: [Kael] enters the underground vault. Dramatic dolly in.
    `;

    const parsed = parseRawScript(script, "video");
    expect(parsed.title).toBe("Neo Tokyo Cyberpunk");
    expect(parsed.scenes).toHaveLength(2);
    expect(parsed.characters).toContain("Kael");
    expect(parsed.scenes[0].camera).toBe("tracking");
    expect(parsed.scenes[1].camera).toBe("dolly-in");
  });

  it("enhances prompt with cinematic lighting, camera moves and safety filters", () => {
    const optimized = optimizePrompt("A robot detective holding a gun in the dark alley", {
      type: "video",
      camera: "tracking",
      lighting: "cyberpunk-neon",
      characters: ["Unit-734"],
      sanitize: true
    });

    expect(optimized).toContain("tracking shot");
    expect(optimized).toContain("neon rim lighting");
    expect(optimized).toContain("Unit-734");
    // Gun should be sanitized
    expect(optimized).not.toContain("gun");
  });

  it("plans continuous video extension hops up to 148 seconds", () => {
    const plan = planSceneExtension({
      sceneId: "epic_scene",
      storyPrompt: "A warrior climbing a snow mountain peak",
      targetDurationSeconds: 45,
      characters: ["Aria"]
    });

    expect(plan.sceneId).toBe("epic_scene");
    expect(plan.totalTargetDuration).toBe(45);
    expect(plan.totalHops).toBeGreaterThan(0);
    expect(plan.hops.length).toBe(plan.totalHops);
    expect(plan.cliArguments.extendCommand).toContain("--prompt");
  });
});

describe("Subagent 4: Smart Orchestrator & Job Queue", () => {
  it("topologically sorts jobs respecting dependsOn declarations", () => {
    const jobs: GFlowJob[] = [
      parseJob({ id: "scene_03", type: "video", prompt: "p3", dependsOn: ["scene_02"], out: "./out" }),
      parseJob({ id: "scene_01", type: "image", prompt: "p1", out: "./out" }),
      parseJob({ id: "scene_02", type: "video", prompt: "p2", dependsOn: ["scene_01"], out: "./out" })
    ];

    const sorted = resolveJobOrder(jobs);
    expect(sorted.map((j) => j.id)).toEqual(["scene_01", "scene_02", "scene_03"]);
  });

  it("detects cyclic dependencies and throws error", () => {
    const jobs: GFlowJob[] = [
      parseJob({ id: "job_a", type: "video", prompt: "pa", dependsOn: ["job_b"], out: "./out" }),
      parseJob({ id: "job_b", type: "video", prompt: "pb", dependsOn: ["job_a"], out: "./out" })
    ];

    expect(() => resolveJobOrder(jobs)).toThrow(/cyclic dependency/i);
  });

  it("interpolates dynamic artifact paths from parent jobs", () => {
    const job = parseJob({
      id: "job_b",
      type: "video",
      prompt: "render video from frame",
      startFrame: "${job_a.artifacts[0]}",
      out: "./out"
    });

    const interpolated = interpolateJobParameters(job, {
      job_a: ["/storage/out/frame_01.png"]
    });

    if ("startFrame" in interpolated) {
      expect(interpolated.startFrame).toBe("/storage/out/frame_01.png");
    }
  });
});
