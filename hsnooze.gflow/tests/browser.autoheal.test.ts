import { describe, expect, it, vi } from "vitest";
import {
  calculateBackoff,
  classifyTransientError,
  isCdpDisconnectError,
  isHardStopError,
  isNetworkTransientError,
  isPageCrashError,
  isTimeoutError,
  isTransientError,
  withAutoheal
} from "../src/browser/autoheal.js";
import { registerGracefulShutdown } from "../src/jobs/checkpoint.js";
import {
  CreditLimitError,
  GenerationBlockedError,
  LoginRequiredError,
  ManualActionRequiredError,
  ProfilePoolExhaustedError,
  RateLimitedError,
  UiContractError
} from "../src/errors.js";

describe("Autoheal & Error Classification (src/browser/autoheal.ts)", () => {
  describe("Error Classification Matrix", () => {
    it("classifies CDP disconnects as transient and identifiable", () => {
      const targetClosed = new Error("Target closed");
      const sessionClosed = new Error("Protocol error (Runtime.callFunctionOn): Session closed. Most likely page has been closed.");
      const wsClosed = new Error("WebSocket error: Connection closed");
      const detachedFrame = new Error("Navigating frame was detached");

      expect(isCdpDisconnectError(targetClosed)).toBe(true);
      expect(isCdpDisconnectError(sessionClosed)).toBe(true);
      expect(isCdpDisconnectError(wsClosed)).toBe(true);
      expect(isCdpDisconnectError(detachedFrame)).toBe(true);

      expect(isTransientError(targetClosed)).toBe(true);
      expect(classifyTransientError(targetClosed)).toBe("cdp_disconnect");
    });

    it("classifies page crashes as transient and identifiable", () => {
      const pageCrashed = new Error("Page crashed!");
      const targetCrashed = new Error("Target crashed");
      const crashpad = new Error("Crashpad caught an exception in renderer");

      expect(isPageCrashError(pageCrashed)).toBe(true);
      expect(isPageCrashError(targetCrashed)).toBe(true);
      expect(isPageCrashError(crashpad)).toBe(true);

      expect(isTransientError(pageCrashed)).toBe(true);
      expect(classifyTransientError(pageCrashed)).toBe("page_crash");
    });

    it("classifies actionability timeouts as transient and identifiable", () => {
      const timeoutErr = new Error("locator.click: Timeout 20000ms exceeded while waiting for element");
      const pwTimeout = new Error("Timed out waiting for selector");
      pwTimeout.name = "TimeoutError";

      expect(isTimeoutError(timeoutErr)).toBe(true);
      expect(isTimeoutError(pwTimeout)).toBe(true);

      expect(isTransientError(timeoutErr)).toBe(true);
      expect(classifyTransientError(timeoutErr)).toBe("timeout");
    });

    it("classifies network stalls and connection resets as transient", () => {
      const connReset = new Error("read ECONNRESET");
      (connReset as NodeJS.ErrnoException).code = "ECONNRESET";
      const netReset = new Error("net::ERR_CONNECTION_RESET");
      const fetchFailed = new Error("TypeError: fetch failed");

      expect(isNetworkTransientError(connReset)).toBe(true);
      expect(isNetworkTransientError(netReset)).toBe(true);
      expect(isNetworkTransientError(fetchFailed)).toBe(true);

      expect(isTransientError(connReset)).toBe(true);
      expect(classifyTransientError(connReset)).toBe("network_stall");
    });

    it("strictly classifies terminal errors as hard stop and non-transient", () => {
      const loginErr = new LoginRequiredError();
      const manualErr = new ManualActionRequiredError("2FA challenge");
      const uiErr = new UiContractError("Prompt box missing");
      const blockedErr = new GenerationBlockedError("Policy violation");
      const rateErr = new RateLimitedError("Too many requests");
      const creditErr = new CreditLimitError("Out of quota");
      const exhaustedErr = new ProfilePoolExhaustedError("All profiles busy");

      const hardStops = [loginErr, manualErr, uiErr, blockedErr, rateErr, creditErr, exhaustedErr];

      for (const err of hardStops) {
        expect(isHardStopError(err)).toBe(true);
        expect(isTransientError(err)).toBe(false);
      }
    });
  });

  describe("Backoff Calculation", () => {
    it("computes exponential backoff with bounded jitter", () => {
      for (let attempt = 1; attempt <= 4; attempt++) {
        const backoff = calculateBackoff(attempt, 1000, 30000, 200);
        const minExpected = 1000 * Math.pow(2, attempt - 1);
        const maxExpected = minExpected + 200;
        expect(backoff).toBeGreaterThanOrEqual(minExpected);
        expect(backoff).toBeLessThanOrEqual(maxExpected);
      }
    });

    it("caps backoff at maxMs", () => {
      const backoff = calculateBackoff(10, 1000, 5000, 100);
      expect(backoff).toBeLessThanOrEqual(5000);
    });
  });

  describe("withAutoheal Execution", () => {
    it("returns result immediately if action succeeds on first try", async () => {
      const onHeal = vi.fn();
      const result = await withAutoheal(async () => "success", onHeal, { maxRetries: 2, baseBackoffMs: 10 });

      expect(result).toBe("success");
      expect(onHeal).not.toHaveBeenCalled();
    });

    it("retries on transient error, invokes onHeal, and recovers", async () => {
      let attempts = 0;
      const onHeal = vi.fn(async () => undefined);

      const result = await withAutoheal(
        async () => {
          attempts++;
          if (attempts === 1) {
            throw new Error("Target closed");
          }
          return "recovered";
        },
        onHeal,
        { maxRetries: 2, baseBackoffMs: 10, jitterMs: 5 }
      );

      expect(result).toBe("recovered");
      expect(attempts).toBe(2);
      expect(onHeal).toHaveBeenCalledTimes(1);
      expect(onHeal).toHaveBeenCalledWith("cdp_disconnect");
    });

    it("immediately fails without retrying on hard-stop error", async () => {
      let attempts = 0;
      const onHeal = vi.fn();

      await expect(
        withAutoheal(
          async () => {
            attempts++;
            throw new CreditLimitError("Quota depleted");
          },
          onHeal,
          { maxRetries: 3, baseBackoffMs: 10 }
        )
      ).rejects.toThrow(CreditLimitError);

      expect(attempts).toBe(1);
      expect(onHeal).not.toHaveBeenCalled();
    });

    it("aborts and rethrows after maxRetries are exhausted", async () => {
      let attempts = 0;
      const onHeal = vi.fn(async () => undefined);

      await expect(
        withAutoheal(
          async () => {
            attempts++;
            throw new Error("Page crashed");
          },
          onHeal,
          { maxRetries: 2, baseBackoffMs: 10, jitterMs: 5 }
        )
      ).rejects.toThrow("Page crashed");

      // Attempt 1 + 2 retries = 3 attempts total (1 initial + 2 retries)
      expect(attempts).toBe(3);
      expect(onHeal).toHaveBeenCalledTimes(2);
    });
  });

  describe("Graceful Shutdown Trapping", () => {
    it("registers and cleanly unregisters signal listeners", () => {
      const initialSigintCount = process.listenerCount("SIGINT");
      const initialSigtermCount = process.listenerCount("SIGTERM");

      const unregister = registerGracefulShutdown(async () => undefined);
      expect(process.listenerCount("SIGINT")).toBe(initialSigintCount + 1);
      expect(process.listenerCount("SIGTERM")).toBe(initialSigtermCount + 1);

      unregister();
      expect(process.listenerCount("SIGINT")).toBe(initialSigintCount);
      expect(process.listenerCount("SIGTERM")).toBe(initialSigtermCount);
    });

    it("invokes onShutdown callback with received signal string", async () => {
      let capturedSignal: string | undefined;
      const unregister = registerGracefulShutdown({
        onShutdown: async (signal) => {
          capturedSignal = signal;
        },
        timeoutMs: 5000
      });

      // Mock process.exit to avoid terminating test runner
      const exitSpy = vi.spyOn(process, "exit").mockImplementation((() => {}) as never);

      try {
        // Trigger SIGINT event
        process.emit("SIGINT");
        // Allow microtask queue to process
        await new Promise((r) => setTimeout(r, 50));

        expect(capturedSignal).toBe("SIGINT");
        expect(exitSpy).toHaveBeenCalledWith(130);
      } finally {
        exitSpy.mockRestore();
        unregister();
      }
    });

    it("exits with code 143 when receiving SIGTERM", async () => {
      let capturedSignal: string | undefined;
      const unregister = registerGracefulShutdown({
        onShutdown: async (signal) => {
          capturedSignal = signal;
        },
        timeoutMs: 5000
      });

      const exitSpy = vi.spyOn(process, "exit").mockImplementation((() => {}) as never);

      try {
        process.emit("SIGTERM");
        await new Promise((r) => setTimeout(r, 50));

        expect(capturedSignal).toBe("SIGTERM");
        expect(exitSpy).toHaveBeenCalledWith(143);
      } finally {
        exitSpy.mockRestore();
        unregister();
      }
    });
  });
});
