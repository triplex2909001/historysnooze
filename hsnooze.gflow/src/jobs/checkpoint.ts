import { open, readFile, rename, unlink, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { randomBytes } from "node:crypto";
import { z } from "zod";

export const CHECKPOINT_FILE_NAME = "checkpoint.json";
export const LEGACY_CHECKPOINT_FILE_NAME = "gflow-checkpoint.json";

export const completedJobRecordSchema = z.object({
  status: z.literal("completed").default("completed"),
  artifacts: z.array(z.string().min(1)),
  completedAt: z.string(),
  profile: z.string().optional(),
  durationMs: z.number().optional()
});
export type CompletedJobRecord = z.infer<typeof completedJobRecordSchema>;

export const failedJobRecordSchema = z.object({
  status: z.literal("failed").default("failed"),
  error: z.string(),
  failedAt: z.string(),
  profile: z.string().optional(),
  attempts: z.number().optional()
});
export type FailedJobRecord = z.infer<typeof failedJobRecordSchema>;

export const pipelineCheckpointSchema = z.object({
  version: z.string().default("1.0"),
  pipeline: z.string().default("default"),
  startedAt: z.string(),
  updatedAt: z.string(),
  completedAt: z.string().optional(),
  interruptedAt: z.string().optional(),
  currentJobId: z.string().nullable().optional(),
  activeProfile: z.string().optional(),
  completedJobs: z.record(z.string(), completedJobRecordSchema).default({}),
  failedJobs: z.record(z.string(), failedJobRecordSchema).default({})
});
export type PipelineCheckpoint = z.infer<typeof pipelineCheckpointSchema>;

export interface JobCheckpointFailedRecord {
  id: string;
  error: string;
  timestamp: string;
  profile?: string;
}

export interface JobCheckpointState extends PipelineCheckpoint {
  pipelineId?: string;
  createdAt?: string;
  completed?: string[];
  failed?: JobCheckpointFailedRecord[];
  artifacts?: Record<string, string[]>;
}

export function resolveCheckpointPath(outDir: string): string {
  return join(outDir, CHECKPOINT_FILE_NAME);
}

export function resolveLegacyCheckpointPath(outDir: string): string {
  return join(outDir, LEGACY_CHECKPOINT_FILE_NAME);
}

/**
 * Performs an atomic JSON write:
 * 1. Writes to a temporary file in the same directory.
 * 2. Flushes page cache to physical disk using sync().
 * 3. Atomically replaces target file using POSIX rename.
 * 4. Cleans up temp file on failure.
 */
export async function writeAtomicJson(filePath: string, data: unknown): Promise<void> {
  const dir = dirname(filePath);
  await mkdir(dir, { recursive: true });

  const randomSuffix = randomBytes(6).toString("hex");
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.${randomSuffix}.tmp`;
  const content = `${JSON.stringify(data, null, 2)}\n`;

  const handle = await open(tempPath, "w");
  try {
    await handle.writeFile(content, "utf8");
    await handle.sync();
  } finally {
    await handle.close();
  }

  try {
    await rename(tempPath, filePath);
  } catch (err) {
    await unlink(tempPath).catch(() => undefined);
    throw err;
  }
}

export async function saveCheckpointAtomic(outDir: string, state: JobCheckpointState): Promise<void> {
  await mkdir(outDir, { recursive: true });
  state.updatedAt = new Date().toISOString();
  await writeAtomicJson(resolveCheckpointPath(outDir), state);
}

export const saveCheckpoint = saveCheckpointAtomic;

/**
 * Loads and validates checkpoint.json.
 * Supports transparent backward-compatible migration from legacy gflow-checkpoint.json.
 * If verifyArtifactsOnDisk is true (default), verifies all recorded output artifacts physically exist on disk.
 */
export async function loadCheckpoint(
  outDir: string,
  options?: { verifyArtifactsOnDisk?: boolean }
): Promise<JobCheckpointState | null> {
  const primaryPath = resolveCheckpointPath(outDir);
  const legacyPath = resolveLegacyCheckpointPath(outDir);

  let raw: string | null = null;
  let loadedFromLegacy = false;

  try {
    raw = await readFile(primaryPath, "utf8");
  } catch {
    try {
      raw = await readFile(legacyPath, "utf8");
      loadedFromLegacy = true;
    } catch {
      return null;
    }
  }

  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw);
    let state: JobCheckpointState;

    // Handle legacy schema: { completed: string[], artifacts: Record<string, string[]> }
    if (Array.isArray(parsed.completed) && parsed.artifacts) {
      const migrated: JobCheckpointState = {
        version: "1.0",
        pipeline: parsed.pipelineId ?? parsed.pipeline ?? "default",
        pipelineId: parsed.pipelineId ?? parsed.pipeline ?? "default",
        startedAt: parsed.createdAt ?? parsed.startedAt ?? new Date().toISOString(),
        createdAt: parsed.createdAt ?? parsed.startedAt ?? new Date().toISOString(),
        updatedAt: parsed.updatedAt ?? new Date().toISOString(),
        completedAt: parsed.completedAt,
        activeProfile: parsed.activeProfile,
        currentJobId: parsed.currentJobId ?? null,
        completedJobs: {},
        failedJobs: {},
        completed: [...parsed.completed],
        failed: Array.isArray(parsed.failed) ? [...parsed.failed] : [],
        artifacts: { ...parsed.artifacts }
      };

      for (const id of parsed.completed) {
        migrated.completedJobs[id] = {
          status: "completed",
          artifacts: parsed.artifacts[id] ?? [],
          completedAt: parsed.updatedAt ?? new Date().toISOString()
        };
      }

      if (Array.isArray(parsed.failed)) {
        for (const f of parsed.failed) {
          migrated.failedJobs[f.id] = {
            status: "failed",
            error: f.error ?? String(f),
            failedAt: f.timestamp ?? new Date().toISOString(),
            profile: f.profile
          };
        }
      }
      state = migrated;
    } else {
      const validated = pipelineCheckpointSchema.parse(parsed);
      state = {
        ...validated,
        pipelineId: validated.pipeline,
        createdAt: validated.startedAt,
        completed: Object.keys(validated.completedJobs),
        artifacts: Object.fromEntries(
          Object.entries(validated.completedJobs).map(([k, v]) => [k, [...v.artifacts]])
        ),
        failed: Object.entries(validated.failedJobs).map(([k, v]) => ({
          id: k,
          error: v.error,
          timestamp: v.failedAt,
          profile: v.profile
        }))
      };
    }

    // Verify artifact files physically exist on disk
    if (options?.verifyArtifactsOnDisk !== false) {
      for (const [jobId, record] of Object.entries(state.completedJobs)) {
        const missing = record.artifacts.find((p) => !existsSync(p));
        if (missing) {
          console.warn(
            `[gflow:checkpoint] Artifact '${missing}' for completed job '${jobId}' is missing on disk. Invalidating cached status.`
          );
          delete state.completedJobs[jobId];
          if (state.completed) {
            state.completed = state.completed.filter((id) => id !== jobId);
          }
          if (state.artifacts) {
            delete state.artifacts[jobId];
          }
        }
      }
    }

    // If loaded from legacy, persist to new canonical filename
    if (loadedFromLegacy) {
      await saveCheckpointAtomic(outDir, state).catch(() => undefined);
    }

    return state;
  } catch (err) {
    console.warn(`[gflow:checkpoint] Error reading checkpoint in '${outDir}':`, err);
    return null;
  }
}

export function createInitialCheckpoint(pipelineId?: string, activeProfile?: string): JobCheckpointState {
  const now = new Date().toISOString();
  const name = pipelineId ?? "default";
  return {
    version: "1.0",
    pipeline: name,
    pipelineId: name,
    startedAt: now,
    createdAt: now,
    updatedAt: now,
    currentJobId: null,
    activeProfile,
    completedJobs: {},
    failedJobs: {},
    completed: [],
    failed: [],
    artifacts: {}
  };
}

export function isJobCompleted(state: JobCheckpointState | null, jobId: string): boolean {
  if (!state) return false;
  if (state.completedJobs && state.completedJobs[jobId]) return true;
  if (Array.isArray(state.completed) && state.completed.includes(jobId)) return true;
  return false;
}

export function getCompletedArtifacts(state: JobCheckpointState | null, jobId: string): string[] {
  if (!state) return [];
  if (state.completedJobs?.[jobId]?.artifacts) {
    return [...state.completedJobs[jobId].artifacts];
  }
  if (state.artifacts?.[jobId]) {
    return [...state.artifacts[jobId]];
  }
  return [];
}

export function buildArtifactsMap(state: JobCheckpointState | null): Record<string, string[]> {
  const map: Record<string, string[]> = {};
  if (!state) return map;
  if (state.completedJobs) {
    for (const [id, rec] of Object.entries(state.completedJobs)) {
      map[id] = [...rec.artifacts];
    }
  } else if (state.artifacts) {
    for (const [id, list] of Object.entries(state.artifacts)) {
      map[id] = [...list];
    }
  }
  return map;
}

export async function recordJobStart(
  outDir: string,
  state: JobCheckpointState,
  jobId: string,
  options?: { persist?: boolean }
): Promise<void> {
  state.currentJobId = jobId;
  if (options?.persist !== false) {
    await saveCheckpointAtomic(outDir, state);
  }
}

export async function recordJobSuccess(
  outDir: string,
  state: JobCheckpointState,
  jobId: string,
  artifacts: string[],
  options?: { profile?: string; durationMs?: number; persist?: boolean }
): Promise<void> {
  const now = new Date().toISOString();
  state.completedJobs[jobId] = {
    status: "completed",
    artifacts: [...artifacts],
    completedAt: now,
    profile: options?.profile,
    durationMs: options?.durationMs
  };
  delete state.failedJobs[jobId];
  state.currentJobId = null;

  // Sync legacy fields
  if (!state.completed) state.completed = [];
  if (!state.completed.includes(jobId)) state.completed.push(jobId);
  if (!state.artifacts) state.artifacts = {};
  state.artifacts[jobId] = [...artifacts];
  if (state.failed) {
    state.failed = state.failed.filter((f) => f.id !== jobId);
  }

  if (options?.persist !== false) {
    await saveCheckpointAtomic(outDir, state);
  }
}

export async function recordJobFailure(
  outDir: string,
  state: JobCheckpointState,
  jobId: string,
  error: string,
  profile?: string,
  options?: { persist?: boolean }
): Promise<void> {
  const now = new Date().toISOString();
  const existingAttempts = state.failedJobs[jobId]?.attempts ?? 0;
  state.failedJobs[jobId] = {
    status: "failed",
    error,
    failedAt: now,
    profile,
    attempts: existingAttempts + 1
  };
  state.currentJobId = null;

  // Sync legacy fields
  if (!state.failed) state.failed = [];
  state.failed = state.failed.filter((f) => f.id !== jobId);
  state.failed.push({
    id: jobId,
    error,
    timestamp: now,
    profile
  });

  if (options?.persist !== false) {
    await saveCheckpointAtomic(outDir, state);
  }
}

export async function clearCheckpoint(outDir: string): Promise<boolean> {
  let cleared = false;
  for (const path of [resolveCheckpointPath(outDir), resolveLegacyCheckpointPath(outDir)]) {
    try {
      await unlink(path);
      cleared = true;
    } catch {
      // Ignore if not present
    }
  }
  return cleared;
}

export interface GracefulShutdownConfig {
  onShutdown?: (signal: "SIGINT" | "SIGTERM") => Promise<void>;
  timeoutMs?: number;
}

/**
 * Registers process handlers for SIGINT and SIGTERM to ensure
 * state is saved on interruption before exiting:
 * - POSIX exit codes: 130 for SIGINT, 143 for SIGTERM.
 * - Re-entrant second signal forces immediate exit.
 * - 10-second watchdog timer prevents hang.
 * - Cursor restored before exit.
 */
export function registerGracefulShutdown(
  handlerOrConfig: ((signal: "SIGINT" | "SIGTERM") => Promise<void>) | GracefulShutdownConfig
): () => void {
  const config: GracefulShutdownConfig =
    typeof handlerOrConfig === "function" ? { onShutdown: handlerOrConfig } : handlerOrConfig;
  const timeoutMs = config.timeoutMs ?? 10000;
  let isShuttingDown = false;

  const handleSignal = async (signal: "SIGINT" | "SIGTERM") => {
    const exitCode = signal === "SIGTERM" ? 143 : 130;

    if (isShuttingDown) {
      process.stderr.write(`\n[gflow:shutdown] Immediate exit forced by second ${signal}.\n`);
      process.stderr.write("\u001B[?25h");
      process.exit(exitCode);
    }

    isShuttingDown = true;
    console.warn(`\n[gflow:checkpoint] Received ${signal}. Preserving current pipeline checkpoint...`);

    const watchdog = setTimeout(() => {
      console.error(`\n[gflow:checkpoint] Teardown exceeded ${timeoutMs}ms watchdog. Exiting.`);
      process.stderr.write("\u001B[?25h");
      process.exit(exitCode);
    }, timeoutMs);
    watchdog.unref();

    try {
      if (config.onShutdown) {
        await config.onShutdown(signal);
        console.info("[gflow:checkpoint] Checkpoint saved successfully. Resume with --resume.");
      }
    } catch (err) {
      console.error("[gflow:checkpoint] Failed to save checkpoint on exit:", err);
    } finally {
      clearTimeout(watchdog);
      process.stderr.write("\u001B[?25h");
      process.exit(exitCode);
    }
  };

  const onSigint = () => handleSignal("SIGINT");
  const onSigterm = () => handleSignal("SIGTERM");

  process.on("SIGINT", onSigint);
  process.on("SIGTERM", onSigterm);

  return () => {
    process.off("SIGINT", onSigint);
    process.off("SIGTERM", onSigterm);
  };
}
