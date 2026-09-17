import { EventEmitter } from "node:events";
import { mkdir } from "node:fs/promises";
import { withAutoheal, forceCleanProfileLocks } from "../browser/autoheal.js";
import { ProfilePool } from "../browser/profile-pool.js";
import { openBrowserSession, type BrowserChannel } from "../browser/session.js";
import { resolveOutputDir } from "../config/paths.js";
import {
  CreditLimitError,
  RateLimitedError,
  ProfilePoolExhaustedError,
  messageForError
} from "../errors.js";
import { FlowPage } from "../flow/page.js";
import type { FlowAutomation, FlowJobResult } from "../flow/types.js";
import {
  createInitialCheckpoint,
  isJobCompleted,
  loadCheckpoint,
  recordJobFailure,
  recordJobSuccess,
  recordJobStart,
  saveCheckpointAtomic,
  getCompletedArtifacts,
  registerGracefulShutdown,
  type JobCheckpointState
} from "./checkpoint.js";
import type { GFlowJob } from "./schema.js";

export interface OrchestratorOptions {
  pipeline?: string;
  jobs: GFlowJob[];
  outDir: string;
  profiles?: string[];
  browser?: BrowserChannel;
  headed?: boolean;
  resume?: boolean;
  checkpoint?: boolean;
  autoheal?: boolean;
  continueOnFailure?: boolean;
  maxRetriesPerJob?: number;
  automationFactory?: (profile: string) => Promise<{ automation: FlowAutomation; close(): Promise<void> }>;
}

import {
  extractVideoFrame,
  isVideoFile,
  parseOutputReference
} from "./frame-extractor.js";
import {
  interpolateJobOutputs,
  resolveJobOrder
} from "./resolver.js";

export { resolveJobOrder };

export interface FrameExtractionProgressEvent {
  jobId: string;
  upstreamJobId: string;
  framePath: string;
  cached: boolean;
  position: "last" | "first" | number;
}

export interface PipelineProgressEvent {
  type: "start" | "job:start" | "job:frame" | "job:success" | "job:retry" | "job:fail" | "profile:rotate" | "autoheal" | "complete";
  jobId?: string;
  profile?: string;
  index?: number;
  total?: number;
  error?: string;
  artifacts?: string[];
  message?: string;
}

/**
 * Replaces dynamic artifact placeholders like `${job_id.artifacts[0]}`
 * with the actual paths produced by earlier jobs.
 */
export function interpolateJobParameters(job: GFlowJob, artifactsMap: Record<string, string[]>): GFlowJob {
  return interpolateJobOutputs(job, artifactsMap);
}

/**
 * Asynchronously resolves dynamic references ($output:<job_id> and ${dep.artifacts})
 * and automatically extracts video frames when an image is required for:
 * 1. startFrame (for video chaining)
 * 2. endFrame
 * 3. ingredients (Flow ingredients drawer only accepts images)
 */
export async function resolveJobPipingAndFrames(
  rawJob: GFlowJob,
  checkpoint: JobCheckpointState,
  outDir: string,
  options?: {
    onFrameExtracted?: (event: FrameExtractionProgressEvent) => void;
  }
): Promise<GFlowJob> {
  const cloned = { ...rawJob, ingredients: [...(rawJob.ingredients ?? [])] };

  const resolveRef = (
    val: string
  ): { resolvedPath: string; upstreamJobId?: string; framePos?: "first" | "last" | number } => {
    // 1. $output:<job_id>[<idx>]#<tag>
    const outRef = parseOutputReference(val);
    if (outRef) {
      const artifacts = getCompletedArtifacts(checkpoint, outRef.jobId);
      const artifact = artifacts[outRef.index];
      if (!artifact) {
        throw new Error(
          `Cannot resolve output reference '${val}': Upstream job '${outRef.jobId}' produced no output artifacts.`
        );
      }
      return { resolvedPath: artifact, upstreamJobId: outRef.jobId, framePos: outRef.position };
    }

    // 2. Legacy template syntax: ${depId.artifacts[idx]}
    const legacyMatch = val.match(/^\$\{([a-zA-Z0-9._-]+)\.artifacts(?:\[(\d+)\])?\}$/);
    if (legacyMatch) {
      const depId = legacyMatch[1];
      const idx = legacyMatch[2] ? parseInt(legacyMatch[2], 10) : 0;
      const artifacts = getCompletedArtifacts(checkpoint, depId);
      const artifact = artifacts[idx];
      if (!artifact) {
        throw new Error(
          `Cannot resolve output reference '${val}': Upstream job '${depId}' produced no output artifacts.`
        );
      }
      return { resolvedPath: artifact, upstreamJobId: depId };
    }

    return { resolvedPath: val };
  };

  // 1. Resolve startFrame
  if ("startFrame" in cloned && cloned.startFrame) {
    const { resolvedPath, upstreamJobId, framePos } = resolveRef(cloned.startFrame);
    if (isVideoFile(resolvedPath)) {
      const pos = framePos ?? "last";
      const extractResult = await extractVideoFrame(resolvedPath, {
        position: pos,
        outDir
      });
      cloned.startFrame = extractResult.path;
      if (options?.onFrameExtracted) {
        options.onFrameExtracted({
          jobId: cloned.id,
          upstreamJobId: upstreamJobId ?? "external",
          framePath: extractResult.path,
          cached: extractResult.cached,
          position: pos
        });
      }
    } else {
      cloned.startFrame = resolvedPath;
    }
  }

  // 2. Resolve endFrame
  if ("endFrame" in cloned && cloned.endFrame) {
    const { resolvedPath, upstreamJobId, framePos } = resolveRef(cloned.endFrame);
    if (isVideoFile(resolvedPath)) {
      const pos = framePos ?? "last";
      const extractResult = await extractVideoFrame(resolvedPath, {
        position: pos,
        outDir
      });
      cloned.endFrame = extractResult.path;
      if (options?.onFrameExtracted) {
        options.onFrameExtracted({
          jobId: cloned.id,
          upstreamJobId: upstreamJobId ?? "external",
          framePath: extractResult.path,
          cached: extractResult.cached,
          position: pos
        });
      }
    } else {
      cloned.endFrame = resolvedPath;
    }
  }

  // 3. Resolve ingredients
  if (cloned.ingredients && cloned.ingredients.length > 0) {
    const newIngredients: string[] = [];
    for (const item of cloned.ingredients) {
      const { resolvedPath, upstreamJobId, framePos } = resolveRef(item);
      if (isVideoFile(resolvedPath)) {
        const extractResult = await extractVideoFrame(resolvedPath, {
          position: framePos ?? "last",
          outDir
        });
        newIngredients.push(extractResult.path);
        if (options?.onFrameExtracted) {
          options.onFrameExtracted({
            jobId: cloned.id,
            upstreamJobId: upstreamJobId ?? "external",
            framePath: extractResult.path,
            cached: extractResult.cached,
            position: framePos ?? "last"
          });
        }
      } else {
        newIngredients.push(resolvedPath);
      }
    }
    cloned.ingredients = newIngredients;
  }

  return cloned;
}

export class SmartPipelineOrchestrator extends EventEmitter {
  private options: OrchestratorOptions;
  private profilePool: ProfilePool;
  private currentSession?: { automation: FlowAutomation; close(): Promise<void> };
  private activeProfile: string;

  constructor(options: OrchestratorOptions) {
    super();
    this.options = options;
    this.profilePool = new ProfilePool({ profiles: options.profiles ?? ["default"] });
    this.activeProfile = this.profilePool.getActiveProfile();
  }

  private async getAutomation(profile: string): Promise<{ automation: FlowAutomation; close(): Promise<void> }> {
    if (this.currentSession && this.activeProfile === profile) {
      return this.currentSession;
    }

    if (this.currentSession) {
      await this.currentSession.close().catch(() => undefined);
      this.currentSession = undefined;
    }

    if (this.options.automationFactory) {
      this.currentSession = await this.options.automationFactory(profile);
    } else {
      const session = await openBrowserSession({
        profile,
        headed: this.options.headed ?? false,
        browser: this.options.browser ?? "chrome"
      });
      const flow = new FlowPage(session.page);
      await flow.open();
      this.currentSession = {
        automation: flow,
        close: () => session.close()
      };
    }
    this.activeProfile = profile;
    return this.currentSession;
  }

  async run(): Promise<{ status: "completed" | "failed"; results: FlowJobResult[]; checkpoint: JobCheckpointState }> {
    const outDir = resolveOutputDir(this.options.outDir);
    await mkdir(outDir, { recursive: true });

    // Startup disk sync: load profile health states from disk
    await this.profilePool.syncFromDisk();

    const persist = this.options.checkpoint !== false;
    const shouldResume = Boolean(this.options.resume && persist);

    const sortedJobs = resolveJobOrder(this.options.jobs);
    const checkpoint: JobCheckpointState =
      (shouldResume ? await loadCheckpoint(outDir) : null) ?? createInitialCheckpoint(this.options.pipeline, this.activeProfile);

    // If resuming with an active profile that is allowed and healthy, respect it; otherwise acquire a healthy profile
    const isProfileAllowed = Boolean(!this.options.profiles || this.options.profiles.length === 0 || (checkpoint.activeProfile && this.options.profiles.includes(checkpoint.activeProfile)));

    if (
      shouldResume &&
      checkpoint.activeProfile &&
      isProfileAllowed &&
      this.profilePool.setActiveProfile(checkpoint.activeProfile) &&
      !this.profilePool.isCoolingDown(checkpoint.activeProfile) &&
      !this.profilePool.isExhausted(checkpoint.activeProfile)
    ) {
      this.activeProfile = checkpoint.activeProfile;
    } else {
      this.activeProfile = await this.profilePool.acquireHealthyProfile();
      checkpoint.activeProfile = this.activeProfile;
    }

    // Setup graceful shutdown handler to flush state on interrupt
    const unregisterShutdown = registerGracefulShutdown(async () => {
      if (persist) {
        try {
          checkpoint.interruptedAt = new Date().toISOString();
          await saveCheckpointAtomic(outDir, checkpoint);
        } catch (err) {
          console.error("[gflow:orchestrator] Failed to save checkpoint during interrupt:", err);
        }
      }
      if (this.currentSession) {
        await this.currentSession.close().catch(() => undefined);
        this.currentSession = undefined;
      }
      await forceCleanProfileLocks(this.activeProfile).catch(() => undefined);
    });

    const results: FlowJobResult[] = [];
    this.emit("progress", {
      type: "start",
      total: sortedJobs.length,
      message: `Starting pipeline with ${sortedJobs.length} jobs across profile pool.`
    } as PipelineProgressEvent);

    try {
      for (const [index, rawJob] of sortedJobs.entries()) {
        const jobId = rawJob.id;

        // Resume: Skip already successfully generated jobs
        if (shouldResume && isJobCompleted(checkpoint, jobId)) {
          console.info(`[gflow:orchestrator] Skipping already completed job '${jobId}'.`);
          this.emit("progress", {
            type: "job:success",
            jobId,
            index: index + 1,
            total: sortedJobs.length,
            message: `Skipped completed job '${jobId}'.`
          } as PipelineProgressEvent);
          continue;
        }

        const job = await resolveJobPipingAndFrames(rawJob, checkpoint, outDir, {
          onFrameExtracted: (info) => {
            this.emit("progress", {
              type: "job:frame",
              jobId: info.jobId,
              message: `${info.cached ? "Reused cached" : "Extracted"} video frame from '${info.upstreamJobId}' -> '${info.framePath}' for scene chaining.`
            } as PipelineProgressEvent);
          }
        });
        const maxRetries = job.retry ?? this.options.maxRetriesPerJob ?? 2;
        let attempt = 0;
        let jobSuccess = false;
        let lastError: unknown;
        let lastErrorMsg: string | undefined;

        this.emit("progress", {
          type: "job:start",
          jobId,
          profile: this.activeProfile,
          index: index + 1,
          total: sortedJobs.length
        } as PipelineProgressEvent);

        while (attempt <= maxRetries && !jobSuccess) {
          attempt++;
          await recordJobStart(outDir, checkpoint, jobId, { persist });

          try {
            const executeJobOnCurrentProfile = async () => {
              const { automation } = await this.getAutomation(this.activeProfile);
              return await automation.runJob({ job, outDir });
            };

            let result: FlowJobResult;
            if (this.options.autoheal !== false) {
              result = await withAutoheal(
                executeJobOnCurrentProfile,
                async () => {
                  this.emit("progress", {
                    type: "autoheal",
                    jobId,
                    profile: this.activeProfile,
                    message: "Self-healing triggered. Re-establishing Flow session."
                  } as PipelineProgressEvent);
                  if (this.currentSession) {
                    await this.currentSession.close().catch(() => undefined);
                    this.currentSession = undefined;
                  }
                  await this.getAutomation(this.activeProfile);
                },
                { maxRetries: 2, label: `Job '${jobId}'` }
              );
            } else {
              result = await executeJobOnCurrentProfile();
            }

            // Job succeeded!
            jobSuccess = true;
            await this.profilePool.markSuccess(this.activeProfile);
            const artifactPaths = result.artifacts.map((a) => a.path);
            await recordJobSuccess(outDir, checkpoint, jobId, artifactPaths, { profile: this.activeProfile, persist });
            results.push(result);

            this.emit("progress", {
              type: "job:success",
              jobId,
              profile: this.activeProfile,
              index: index + 1,
              total: sortedJobs.length,
              artifacts: artifactPaths
            } as PipelineProgressEvent);

          } catch (error) {
            lastError = error;
            lastErrorMsg = messageForError(error);
            const errMsg = lastErrorMsg;

            // Check if failure is due to credit limit or rate limit
            if (error instanceof CreditLimitError || error instanceof RateLimitedError) {
              if (error instanceof CreditLimitError) {
                await this.profilePool.markCreditExhausted(this.activeProfile);
              } else {
                await this.profilePool.markRateLimited(this.activeProfile);
              }

              const nextProfile = await this.profilePool.rotateToNextReady();

              if (nextProfile) {
                this.emit("progress", {
                  type: "profile:rotate",
                  jobId,
                  profile: nextProfile,
                  message: `Rotated profile to '${nextProfile}' due to ${error.code}. Retrying job '${jobId}'...`
                } as PipelineProgressEvent);
                // Invalidate session to switch to new profile on next try
                if (this.currentSession) {
                  await this.currentSession.close().catch(() => undefined);
                  this.currentSession = undefined;
                }
                this.activeProfile = nextProfile;
                checkpoint.activeProfile = nextProfile;
                attempt = 0; // Decouple profile rotation from job retry count
                continue; // Retry on new profile without burning attempt count
              }

              // All profiles in the pool are exhausted or rate-limited!
              // Immediately escalate with ProfilePoolExhaustedError instead of retrying dead account!
              const summary = await this.profilePool.getAvailabilitySummary();
              throw new ProfilePoolExhaustedError(summary);
            }

            console.warn(`[gflow:orchestrator] Job '${jobId}' failed attempt ${attempt}/${maxRetries + 1}: ${errMsg}`);

            if (attempt <= maxRetries) {
              this.emit("progress", {
                type: "job:retry",
                jobId,
                profile: this.activeProfile,
                index: index + 1,
                error: errMsg
              } as PipelineProgressEvent);
              await new Promise((r) => setTimeout(r, 2000 * attempt));
            } else {
              // Mark job failed
              await recordJobFailure(outDir, checkpoint, jobId, errMsg, this.activeProfile, { persist });
              this.emit("progress", {
                type: "job:fail",
                jobId,
                profile: this.activeProfile,
                index: index + 1,
                error: errMsg
              } as PipelineProgressEvent);

              if (!this.options.continueOnFailure) {
                throw error;
              }
            }
          }
        }

        // Defensive invariant: ensure that if the retry loop finished without success,
        // the failure is guaranteed to be recorded in checkpoint and escalated
        if (!jobSuccess) {
          if (!checkpoint.failedJobs?.[jobId]) {
            await recordJobFailure(
              outDir,
              checkpoint,
              jobId,
              lastErrorMsg ?? `Job '${jobId}' failed after retries`,
              this.activeProfile,
              { persist }
            );
          }
          if (!this.options.continueOnFailure) {
            throw (lastError instanceof Error ? lastError : new Error(lastErrorMsg ?? `Job '${jobId}' failed after retries`));
          }
        }
      }

      this.emit("progress", {
        type: "complete",
        message: "Pipeline batch execution finished."
      } as PipelineProgressEvent);

      checkpoint.completedAt = new Date().toISOString();
      checkpoint.currentJobId = null;
      if (persist) {
        await saveCheckpointAtomic(outDir, checkpoint);
      }

      const failedCount =
        Object.keys(checkpoint.failedJobs ?? {}).length +
        (Array.isArray(checkpoint.failed) ? checkpoint.failed.length : 0);

      return {
        status: failedCount > 0 ? "failed" : "completed",
        results,
        checkpoint
      };
    } finally {
      unregisterShutdown();
      if (this.currentSession) {
        await this.currentSession.close().catch(() => undefined);
        this.currentSession = undefined;
      }
    }
  }
}
