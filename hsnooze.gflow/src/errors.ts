export class GFlowError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = new.target.name;
    this.code = code;
  }
}

export class LoginRequiredError extends GFlowError {
  constructor(message = "Google Flow login is required. Run `gflow auth login` and complete login in the browser.") {
    super("LOGIN_REQUIRED", message);
  }
}

export class ManualActionRequiredError extends GFlowError {
  constructor(message: string) {
    super("MANUAL_ACTION_REQUIRED", `Manual action required in the Flow browser: ${message}`);
  }
}

export class UiContractError extends GFlowError {
  constructor(message: string) {
    super("UI_CONTRACT_CHANGED", `Google Flow UI contract changed or could not be detected: ${message}`);
  }
}

export class GenerationBlockedError extends GFlowError {
  constructor(message: string) {
    super("GENERATION_BLOCKED", `Flow blocked this generation: ${message}`);
  }
}

export class RateLimitedError extends GFlowError {
  constructor(message: string) {
    super("RATE_LIMITED", `Flow reported rate limiting or unusual activity: ${message}`);
  }
}

export class CreditLimitError extends GFlowError {
  constructor(message: string) {
    super("CREDIT_LIMIT", `Flow reported a credit or quota problem: ${message}`);
  }
}

export class GenerationFailedError extends GFlowError {
  constructor(message: string) {
    super("GENERATION_FAILED", `Flow generation failed: ${message}`);
  }
}

export class DownloadError extends GFlowError {
  constructor(message: string) {
    super("DOWNLOAD_FAILED", `Generated output could not be downloaded: ${message}`);
  }
}

export interface CooldownDetail {
  profile: string;
  coolDownUntil?: number | string | Date;
  remainingMs?: number;
}

export interface PoolAvailabilitySummary {
  total: number;
  ready: string[];
  coolingDown: CooldownDetail[];
  exhausted: string[];
  authRequired?: string[];
  earliestAvailable?: { profile: string; coolDownUntil: number | string | Date; remainingMs: number };
}

export class ProfilePoolExhaustedError extends GFlowError {
  readonly summary?: PoolAvailabilitySummary;
  readonly reason: "credit_exhausted" | "rate_limited" | "mixed";
  readonly earliestAvailable?: { profile: string; coolDownUntil: number | string | Date; remainingMs: number };
  readonly exhaustedProfiles: string[];
  readonly coolingDownProfiles: CooldownDetail[];

  constructor(summaryOrMessage?: PoolAvailabilitySummary | string, customMessage?: string) {
    if (typeof summaryOrMessage === "object" && summaryOrMessage !== null) {
      const summary = summaryOrMessage;
      const reason: "credit_exhausted" | "rate_limited" | "mixed" =
        summary.exhausted.length === summary.total && summary.total > 0
          ? "credit_exhausted"
          : summary.coolingDown.length > 0
          ? "rate_limited"
          : "mixed";

      const defaultMsg =
        reason === "credit_exhausted"
          ? `All ${summary.total} profiles in pool are credit-exhausted (${summary.exhausted.join(", ")}).`
          : reason === "rate_limited" && summary.earliestAvailable
          ? `All ${summary.total} profiles in pool are currently unavailable. Earliest profile '${summary.earliestAvailable.profile}' ready in ${Math.ceil(summary.earliestAvailable.remainingMs / 60000)}m.`
          : `All ${summary.total} profiles in pool are exhausted or rate-limited.`;

      super(reason === "credit_exhausted" ? "CREDIT_LIMIT" : "RATE_LIMITED", customMessage ?? defaultMsg);
      this.summary = summary;
      this.reason = reason;
      this.earliestAvailable = summary.earliestAvailable;
      this.exhaustedProfiles = [...summary.exhausted];
      this.coolingDownProfiles = [...summary.coolingDown];
    } else {
      const msg = typeof summaryOrMessage === "string" ? summaryOrMessage : "All profiles in pool are unavailable.";
      super("RATE_LIMITED", customMessage ?? msg);
      this.reason = "mixed";
      this.exhaustedProfiles = [];
      this.coolingDownProfiles = [];
    }
  }
}

export function exitCodeForError(error: unknown): number {
  if (error instanceof LoginRequiredError) return 2;
  if (error instanceof ManualActionRequiredError) return 2;
  if (error instanceof UiContractError) return 3;
  if (error instanceof GenerationBlockedError) return 4;
  if (error instanceof ProfilePoolExhaustedError) return error.reason === "credit_exhausted" ? 6 : 5;
  if (error instanceof RateLimitedError) return 5;
  if (error instanceof CreditLimitError) return 6;
  if (error instanceof GenerationFailedError) return 7;
  if (error instanceof DownloadError) return 8;
  return 1;
}

export function messageForError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

/**
 * Determines if an error is a permanent, non-retryable hard stop.
 * Hard stop errors must immediately bypass retry loops on the same profile.
 */
export function isHardStopError(error: unknown): boolean {
  if (
    error instanceof LoginRequiredError ||
    error instanceof ManualActionRequiredError ||
    error instanceof UiContractError ||
    error instanceof GenerationBlockedError ||
    error instanceof RateLimitedError ||
    error instanceof CreditLimitError ||
    error instanceof ProfilePoolExhaustedError
  ) {
    return true;
  }

  if (error && typeof error === "object" && "code" in error) {
    const code = (error as { code: unknown }).code;
    if (
      code === "LOGIN_REQUIRED" ||
      code === "MANUAL_ACTION_REQUIRED" ||
      code === "UI_CONTRACT_CHANGED" ||
      code === "GENERATION_BLOCKED" ||
      code === "RATE_LIMITED" ||
      code === "CREDIT_LIMIT" ||
      code === "PROFILE_POOL_EXHAUSTED"
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Identifies if an error indicates a dropped CDP session or closed target.
 */
export function isCdpDisconnectError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  return (
    msg.includes("target closed") ||
    msg.includes("session closed") ||
    msg.includes("browser has been closed") ||
    msg.includes("connection closed") ||
    msg.includes("protocol error") ||
    msg.includes("websocket error") ||
    msg.includes("navigating frame was detached") ||
    msg.includes("frame was detached") ||
    msg.includes("execution context was destroyed")
  );
}

/**
 * Identifies if an error indicates a crashed browser tab or renderer process.
 */
export function isPageCrashError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  return (
    msg.includes("page crashed") ||
    msg.includes("target crashed") ||
    msg.includes("crashpad") ||
    msg.includes("render process gone")
  );
}

/**
 * Identifies if an error is a transient Playwright actionability or navigation timeout.
 */
export function isTimeoutError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return (
    error.name === "TimeoutError" ||
    error.message.toLowerCase().includes("timeout") ||
    error.message.toLowerCase().includes("timed out")
  );
}

/**
 * Identifies if an error is caused by a transient network hiccup.
 */
export function isNetworkTransientError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  const code = (error as NodeJS.ErrnoException).code;
  return (
    msg.includes("net::err_internet_disconnected") ||
    msg.includes("net::err_connection_reset") ||
    msg.includes("net::err_connection_refused") ||
    msg.includes("net::err_name_not_resolved") ||
    msg.includes("net::err_network_changed") ||
    msg.includes("net::err_timed_out") ||
    msg.includes("fetch failed") ||
    code === "ECONNRESET" ||
    code === "ECONNREFUSED" ||
    code === "ETIMEDOUT" ||
    code === "ENOTFOUND" ||
    code === "EPIPE" ||
    code === "EAI_AGAIN"
  );
}

/**
 * Comprehensive transient error classifier.
 * Returns true ONLY if the error can potentially be resolved by auto-healing.
 */
export function isTransientError(error: unknown): boolean {
  if (isHardStopError(error)) {
    return false;
  }
  return (
    isCdpDisconnectError(error) ||
    isPageCrashError(error) ||
    isTimeoutError(error) ||
    isNetworkTransientError(error)
  );
}

export type TransientErrorReason =
  | "cdp_disconnect"
  | "page_crash"
  | "timeout"
  | "network_stall"
  | "unknown_transient";

/**
 * Classifies transient error into its specific operational reason.
 */
export function classifyTransientError(error: unknown): TransientErrorReason {
  if (isCdpDisconnectError(error)) return "cdp_disconnect";
  if (isPageCrashError(error)) return "page_crash";
  if (isTimeoutError(error)) return "timeout";
  if (isNetworkTransientError(error)) return "network_stall";
  return "unknown_transient";
}
