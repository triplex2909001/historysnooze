import { execFile } from "node:child_process";
import { rm } from "node:fs/promises";
import { join } from "node:path";
import { promisify } from "node:util";
import { resolveProfileDir } from "../config/paths.js";
import {
  isTransientError,
  isHardStopError,
  isCdpDisconnectError,
  isPageCrashError,
  isTimeoutError,
  isNetworkTransientError,
  classifyTransientError,
  type TransientErrorReason
} from "../errors.js";
import { findChromeProcessesForProfile } from "./session.js";

export {
  isTransientError,
  isHardStopError,
  isCdpDisconnectError,
  isPageCrashError,
  isTimeoutError,
  isNetworkTransientError,
  classifyTransientError,
  type TransientErrorReason
};

const execFileAsync = promisify(execFile);
const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

const SINGLETON_FILES = [
  "SingletonLock",
  "SingletonCookie",
  "SingletonSocket",
  "DevToolsActivePort"
] as const;

export interface AutohealOptions {
  profile: string;
  maxRetries?: number;
  initialBackoffMs?: number;
  onHealAttempt?: (attempt: number, reason: string) => void;
  onHealSuccess?: (attempt: number) => void;
  onHealFailure?: (error: Error) => void;
}

/**
 * Check if a process is still running.
 */
function isPidRunning(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === "EPERM";
  }
}

/**
 * Aggressively and safely cleans stale or orphaned Chrome lock files
 * for a specific profile. If processes are still attached to the profile
 * but unresponsive, terminates them (SIGTERM then SIGKILL) before removing locks.
 */
export async function forceCleanProfileLocks(profile: string): Promise<{ killedProcesses: number[]; removedLocks: string[] }> {
  const profileDir = resolveProfileDir(profile);
  const killedProcesses: number[] = [];
  const removedLocks: string[] = [];

  // 1. Locate any Chrome processes currently holding this profile dir
  const pids = await findChromeProcessesForProfile(profileDir);
  for (const pid of pids) {
    try {
      process.kill(pid, "SIGTERM");
      killedProcesses.push(pid);
    } catch {
      // Process already terminated
    }
  }

  // Allow up to 2 seconds for graceful shutdown
  if (killedProcesses.length > 0) {
    const deadline = Date.now() + 2000;
    while (Date.now() < deadline) {
      const anyAlive = killedProcesses.some((pid) => isPidRunning(pid));
      if (!anyAlive) break;
      await delay(100);
    }

    // Force-kill any stubborn remaining processes
    for (const pid of killedProcesses) {
      if (isPidRunning(pid)) {
        try {
          process.kill(pid, "SIGKILL");
        } catch {
          // Ignored
        }
      }
    }
  }

  // 2. Remove all singleton lock files, sockets, and active port files
  for (const file of SINGLETON_FILES) {
    const filePath = join(profileDir, file);
    try {
      await rm(filePath, { force: true, recursive: true });
      removedLocks.push(file);
    } catch {
      // Ignore if file does not exist
    }
  }

  return { killedProcesses, removedLocks };
}

/**
 * Test network connectivity to verify connection is not locally down.
 */
export async function checkNetworkConnectivity(targetHost = "1.1.1.1", timeoutMs = 4000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const pingCmd = process.platform === "darwin" ? ["-c", "1", "-W", "3", targetHost] : ["-c", "1", "-W", "3", targetHost];
      await execFileAsync("ping", pingCmd);
      return true;
    } finally {
      clearTimeout(timeout);
    }
  } catch {
    // Ping failed or blocked, try HTTP fetch
    try {
      const res = await fetch("https://www.google.com/generate_204", { signal: AbortSignal.timeout(timeoutMs) });
      return res.status === 204 || res.ok;
    } catch {
      return false;
    }
  }
}

/**
 * Checks if a given error indicates a dropped CDP session, network failure, or browser crash.
 */
export function isRecoverableConnectionError(error: unknown): boolean {
  if (isHardStopError(error)) return false;
  return isTransientError(error);
}

/**
 * Computes decorrelated exponential backoff with bounded jitter.
 */
export function calculateBackoff(
  attempt: number,
  baseMs = 1500,
  maxMs = 30000,
  jitterMs = 500
): number {
  const exp = Math.min(maxMs, baseMs * Math.pow(2, attempt - 1));
  const jitter = Math.floor(Math.random() * jitterMs);
  return Math.min(maxMs, exp + jitter);
}

export interface AutohealPolicyOptions {
  maxRetries?: number;
  backoffMs?: number;
  baseBackoffMs?: number;
  maxBackoffMs?: number;
  jitterMs?: number;
  label?: string;
  onAttempt?: (attempt: number, maxRetries: number, reason: string) => void;
  onSuccess?: (attempt: number) => void;
}

/**
 * Resilient wrapper around operations executed on a Playwright page.
 * If the connection drops or browser crashes mid-operation, triggers self-healing:
 * lock cleaning, relaunching, and operation retry with exponential backoff and jitter.
 */
export async function withAutoheal<T>(
  action: () => Promise<T>,
  onHeal: (reason?: string) => Promise<void>,
  options: AutohealPolicyOptions = {}
): Promise<T> {
  const maxRetries = options.maxRetries ?? 3;
  const baseBackoff = options.baseBackoffMs ?? options.backoffMs ?? 1500;
  let attempt = 0;

  while (true) {
    try {
      const result = await action();
      if (attempt > 0) {
        options.onSuccess?.(attempt);
      }
      return result;
    } catch (error) {
      attempt++;
      if (attempt > maxRetries || !isTransientError(error)) {
        throw error;
      }

      const reason = classifyTransientError(error);
      const errMessage = error instanceof Error ? error.message : String(error);
      const backoffMs = calculateBackoff(
        attempt,
        baseBackoff,
        options.maxBackoffMs ?? 30000,
        options.jitterMs ?? 500
      );

      options.onAttempt?.(attempt, maxRetries, `${reason}: ${errMessage}`);
      console.warn(
        `[gflow:autoheal] Transient glitch (${reason}) in ${options.label ?? "operation"} (attempt ${attempt}/${maxRetries}): ${errMessage}. Retrying in ${backoffMs}ms...`
      );

      // Check internet if network error
      if (reason === "network_stall" || reason === "cdp_disconnect") {
        const isOnline = await checkNetworkConnectivity();
        if (!isOnline) {
          console.warn("[gflow:autoheal] Network appears offline. Waiting 5s for connection recovery...");
          await delay(5000);
        }
      }

      console.info(`[gflow:autoheal] Performing self-healing session recovery in ${backoffMs}ms...`);
      await delay(backoffMs);

      try {
        await onHeal(reason);
        console.info(`[gflow:autoheal] Session self-healing succeeded. Retrying ${options.label ?? "operation"}...`);
      } catch (healError) {
        console.error(`[gflow:autoheal] Session self-healing attempt failed:`, healError);
      }
    }
  }
}
