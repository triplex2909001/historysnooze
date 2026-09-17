import { mkdtemp, rm, writeFile, readdir, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeEach, afterEach } from "vitest";
import {
  CHECKPOINT_FILE_NAME,
  LEGACY_CHECKPOINT_FILE_NAME,
  createInitialCheckpoint,
  isJobCompleted,
  loadCheckpoint,
  recordJobFailure,
  recordJobStart,
  recordJobSuccess,
  saveCheckpointAtomic,
  clearCheckpoint,
  getCompletedArtifacts,
  buildArtifactsMap,
  writeAtomicJson,
  resolveCheckpointPath
} from "../src/jobs/checkpoint.js";

describe("Checkpoint Module (src/jobs/checkpoint.ts)", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-checkpoint-test-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  it("creates valid initial checkpoint matching schema", () => {
    const cp = createInitialCheckpoint("cyberpunk-city", "profile-alpha");
    expect(cp.version).toBe("1.0");
    expect(cp.pipeline).toBe("cyberpunk-city");
    expect(cp.activeProfile).toBe("profile-alpha");
    expect(cp.currentJobId).toBeNull();
    expect(cp.completedJobs).toEqual({});
    expect(cp.failedJobs).toEqual({});
    expect(cp.startedAt).toBeDefined();
    expect(cp.updatedAt).toBeDefined();
  });

  it("atomically writes and loads checkpoint.json without leaving temp files", async () => {
    const cp = createInitialCheckpoint("test-pipeline", "prof-1");
    await saveCheckpointAtomic(tempDir, cp);

    // Target checkpoint.json exists
    const loaded = await loadCheckpoint(tempDir);
    expect(loaded).not.toBeNull();
    expect(loaded?.pipeline).toBe("test-pipeline");
    expect(loaded?.activeProfile).toBe("prof-1");

    // Verify no .tmp files linger in directory
    const files = await readdir(tempDir);
    expect(files).toContain(CHECKPOINT_FILE_NAME);
    const tmpFiles = files.filter((f) => f.includes(".tmp"));
    expect(tmpFiles).toHaveLength(0);
  });

  it("writeAtomicJson writes arbitrary JSON data atomically", async () => {
    const filePath = join(tempDir, "custom.json");
    await writeAtomicJson(filePath, { hello: "world" });
    const content = JSON.parse(await readFile(filePath, "utf8"));
    expect(content).toEqual({ hello: "world" });
  });

  it("tracks in-flight job execution via recordJobStart", async () => {
    const cp = createInitialCheckpoint("test-pipeline");
    await recordJobStart(tempDir, cp, "shot-1");

    expect(cp.currentJobId).toBe("shot-1");
    const loaded = await loadCheckpoint(tempDir);
    expect(loaded?.currentJobId).toBe("shot-1");
  });

  it("records job success, updates completedJobs, and clears currentJobId", async () => {
    const assetPath = join(tempDir, "shot-1.png");
    await writeFile(assetPath, "image data");

    const cp = createInitialCheckpoint("test-pipeline", "prof-1");
    await recordJobStart(tempDir, cp, "shot-1");
    await recordJobSuccess(tempDir, cp, "shot-1", [assetPath], {
      profile: "prof-1",
      durationMs: 4500
    });

    expect(cp.currentJobId).toBeNull();
    expect(isJobCompleted(cp, "shot-1")).toBe(true);
    expect(cp.completedJobs["shot-1"]).toBeDefined();
    expect(cp.completedJobs["shot-1"].artifacts).toEqual([assetPath]);
    expect(cp.completedJobs["shot-1"].profile).toBe("prof-1");
    expect(cp.completedJobs["shot-1"].durationMs).toBe(4500);

    const loaded = await loadCheckpoint(tempDir);
    expect(loaded?.completedJobs["shot-1"]).toBeDefined();
    expect(loaded?.currentJobId).toBeNull();
  });

  it("records job failure with attempt counter and clears currentJobId", async () => {
    const cp = createInitialCheckpoint("test-pipeline", "prof-1");
    await recordJobStart(tempDir, cp, "shot-failed");
    await recordJobFailure(tempDir, cp, "shot-failed", "Server timeout", "prof-1");

    expect(cp.currentJobId).toBeNull();
    expect(cp.failedJobs["shot-failed"]).toBeDefined();
    expect(cp.failedJobs["shot-failed"].error).toBe("Server timeout");
    expect(cp.failedJobs["shot-failed"].attempts).toBe(1);

    // Second failure increments attempts
    await recordJobFailure(tempDir, cp, "shot-failed", "Rate limited", "prof-2");
    expect(cp.failedJobs["shot-failed"].attempts).toBe(2);
    expect(cp.failedJobs["shot-failed"].error).toBe("Rate limited");
  });

  it("invalidates completed job record when artifact file is missing from disk", async () => {
    const existingAsset = join(tempDir, "valid.png");
    const deletedAsset = join(tempDir, "deleted.png");
    await writeFile(existingAsset, "valid image");
    await writeFile(deletedAsset, "deleted image");

    const cp = createInitialCheckpoint("test-pipeline");
    await recordJobSuccess(tempDir, cp, "job-kept", [existingAsset]);
    await recordJobSuccess(tempDir, cp, "job-deleted", [deletedAsset]);

    // Delete one artifact from disk
    await rm(deletedAsset);

    // loadCheckpoint should detect missing artifact and invalidate job-deleted
    const loaded = await loadCheckpoint(tempDir, { verifyArtifactsOnDisk: true });
    expect(loaded).not.toBeNull();
    expect(isJobCompleted(loaded, "job-kept")).toBe(true);
    expect(isJobCompleted(loaded, "job-deleted")).toBe(false);
    expect(loaded?.completedJobs["job-deleted"]).toBeUndefined();
  });

  it("migrates legacy gflow-checkpoint.json format transparently", async () => {
    const legacyPath = join(tempDir, LEGACY_CHECKPOINT_FILE_NAME);
    const dummyAsset = join(tempDir, "legacy-out.png");
    await writeFile(dummyAsset, "legacy png");

    const legacyPayload = {
      pipelineId: "legacy-pipeline",
      createdAt: "2026-09-12T10:00:00.000Z",
      updatedAt: "2026-09-12T10:05:00.000Z",
      activeProfile: "legacy-user",
      completed: ["shot-a", "shot-b"],
      failed: [{ id: "shot-c", error: "Failed connection", timestamp: "2026-09-12T10:04:00.000Z" }],
      artifacts: {
        "shot-a": [dummyAsset],
        "shot-b": [dummyAsset]
      }
    };

    await writeFile(legacyPath, JSON.stringify(legacyPayload, null, 2), "utf8");

    const loaded = await loadCheckpoint(tempDir);
    expect(loaded).not.toBeNull();
    expect(loaded?.pipeline).toBe("legacy-pipeline");
    expect(loaded?.activeProfile).toBe("legacy-user");
    expect(loaded?.completedJobs["shot-a"]).toBeDefined();
    expect(loaded?.completedJobs["shot-a"].artifacts).toEqual([dummyAsset]);
    expect(loaded?.completedJobs["shot-b"]).toBeDefined();
    expect(loaded?.failedJobs["shot-c"]).toBeDefined();
    expect(loaded?.failedJobs["shot-c"].error).toBe("Failed connection");

    // Migrated checkpoint is also saved to modern checkpoint.json
    const modernPath = resolveCheckpointPath(tempDir);
    const modernRaw = await readFile(modernPath, "utf8");
    expect(modernRaw).toContain("completedJobs");
  });

  it("provides getCompletedArtifacts and buildArtifactsMap re-hydration helpers", async () => {
    const asset1 = join(tempDir, "a1.png");
    const asset2 = join(tempDir, "a2.png");
    await writeFile(asset1, "a1");
    await writeFile(asset2, "a2");

    const cp = createInitialCheckpoint("test-pipeline");
    await recordJobSuccess(tempDir, cp, "shot-1", [asset1]);
    await recordJobSuccess(tempDir, cp, "shot-2", [asset2]);

    expect(getCompletedArtifacts(cp, "shot-1")).toEqual([asset1]);
    expect(getCompletedArtifacts(cp, "shot-2")).toEqual([asset2]);
    expect(getCompletedArtifacts(cp, "non-existent")).toEqual([]);

    const map = buildArtifactsMap(cp);
    expect(map).toEqual({
      "shot-1": [asset1],
      "shot-2": [asset2]
    });
  });

  it("clears checkpoint files when clearCheckpoint is called", async () => {
    const cp = createInitialCheckpoint("test-pipeline");
    await saveCheckpointAtomic(tempDir, cp);

    const cleared = await clearCheckpoint(tempDir);
    expect(cleared).toBe(true);

    const loaded = await loadCheckpoint(tempDir);
    expect(loaded).toBeNull();
  });
});
