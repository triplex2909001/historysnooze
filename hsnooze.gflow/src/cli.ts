import { readFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Command, CommanderError, InvalidArgumentError } from "commander";
import {
  BROWSER_CHANNELS,
  DEFAULT_BROWSER_CHANNEL,
  launchLoginChrome,
  openBrowserSession,
  resolveChromeExecutable,
  clearStaleSingletonLock,
  findChromeProcessesForProfile,
  type BrowserChannel
} from "./browser/session.js";
import { ProfilePool } from "./browser/profile-pool.js";
import { formatProfileStatusTable, listDiscoveredProfiles } from "./browser/profile-status.js";
import { exitCodeForError, messageForError, LoginRequiredError, ManualActionRequiredError } from "./errors.js";
import { FlowPage } from "./flow/page.js";
import type { FlowAutomation } from "./flow/types.js";
import { parseBatchYaml } from "./jobs/schema.js";
import { hasFfmpeg } from "./jobs/frame-extractor.js";
import { resolvePipeline } from "./jobs/resolver.js";
import { resolveOutputDir, resolveProfileDir } from "./config/paths.js";
import { SmartPipelineOrchestrator, type PipelineProgressEvent } from "./jobs/orchestrator.js";

export interface CreateProgramOptions {
  automation?: FlowAutomation;
}

export function parseBrowserOption(value: string): BrowserChannel {
  if (!BROWSER_CHANNELS.includes(value as BrowserChannel)) {
    throw new InvalidArgumentError(`must be one of: ${BROWSER_CHANNELS.join(", ")}`);
  }
  return value as BrowserChannel;
}

export function resolveVersion(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  for (const rel of ["../package.json", "../../package.json"]) {
    try {
      return (JSON.parse(readFileSync(join(here, rel), "utf8")) as { version: string }).version;
    } catch {
      // try next candidate
    }
  }
  return "1.5.0";
}

async function realAutomation(
  profile: string,
  headed: boolean,
  browser: BrowserChannel
): Promise<{ automation: FlowAutomation; close(): Promise<void> }> {
  const session = await openBrowserSession({ profile, headed, browser });
  const flow = new FlowPage(session.page);
  await flow.open();
  return {
    automation: flow,
    close: () => session.close()
  };
}

export interface DoctorCheckResult {
  name: string;
  ok: boolean;
  message: string;
  remediation?: string;
}

export async function runDoctorChecks(options: {
  profile: string;
  headed?: boolean;
  browser?: BrowserChannel;
  automation?: FlowAutomation;
}): Promise<DoctorCheckResult[]> {
  const results: DoctorCheckResult[] = [];

  // 1. Chrome Executable
  const chromePath = resolveChromeExecutable();
  const chromeExists = existsSync(chromePath) || chromePath === "google-chrome";
  if (chromeExists) {
    results.push({
      name: "Chrome Executable",
      ok: true,
      message: `Google Chrome executable found at '${chromePath}'`
    });
  } else {
    results.push({
      name: "Chrome Executable",
      ok: false,
      message: `Google Chrome executable not found at '${chromePath}'`,
      remediation: "Install Google Chrome (https://www.google.com/chrome/) or set GFLOW_CHROME_PATH."
    });
  }

  // 2. Profile Directory & Locks
  const profileDir = resolveProfileDir(options.profile);
  try {
    const runningPids = await findChromeProcessesForProfile(profileDir);
    const staleCleared = await clearStaleSingletonLock(profileDir);
    const lockDetail =
      runningPids.length > 0
        ? `active Chrome process detected (PID: ${runningPids.join(", ")})`
        : staleCleared
        ? "cleaned up stale lock files"
        : "clean, no locks";
    results.push({
      name: "Profile Directory",
      ok: true,
      message: `Profile directory at '${profileDir}' (${lockDetail})`
    });
  } catch (err) {
    results.push({
      name: "Profile Directory",
      ok: false,
      message: `Profile directory check failed at '${profileDir}': ${err instanceof Error ? err.message : String(err)}`,
      remediation: `Ensure write permissions or run 'gflow auth login --profile ${options.profile}'.`
    });
  }

  // 3. Flow Connectivity & Authentication
  if (options.automation) {
    try {
      if (options.automation instanceof FlowPage) {
        await options.automation.assertReady();
      }
      results.push({
        name: "Flow Connectivity",
        ok: true,
        message: "Google Flow session is authenticated and ready"
      });
    } catch (err) {
      results.push({
        name: "Flow Connectivity",
        ok: false,
        message: err instanceof Error ? err.message : String(err),
        remediation: `Run 'gflow auth login --profile ${options.profile}' to authenticate.`
      });
    }
  } else {
    try {
      const owned = await realAutomation(options.profile, options.headed ?? false, options.browser ?? "chrome");
      try {
        if (owned.automation instanceof FlowPage) {
          await owned.automation.assertReady();
        }
        results.push({
          name: "Flow Connectivity",
          ok: true,
          message: "Google Flow session is authenticated and ready"
        });
      } finally {
        await owned.close();
      }
    } catch (err) {
      const isLogin = err instanceof LoginRequiredError;
      const isManual = err instanceof ManualActionRequiredError;
      const msg = isLogin
        ? "Google Flow session is not signed in."
        : isManual
        ? "Google Flow requires manual action (login/consent verification)."
        : `Could not connect to Google Flow: ${err instanceof Error ? err.message : String(err)}`;
      results.push({
        name: "Flow Connectivity",
        ok: false,
        message: msg,
        remediation: `Run 'gflow auth login --profile ${options.profile}' to complete sign-in.`
      });
    }
  }

  // 4. Video Frame Extractor (FFmpeg)
  const ffmpegOk = await hasFfmpeg();
  if (ffmpegOk) {
    results.push({
      name: "Video Frame Extractor",
      ok: true,
      message: "ffmpeg executable found on PATH for video scene chaining"
    });
  } else {
    results.push({
      name: "Video Frame Extractor",
      ok: false,
      message: "ffmpeg executable not found on PATH",
      remediation: "Install ffmpeg ('sudo apt install ffmpeg' or 'brew install ffmpeg') for high-speed video scene chaining."
    });
  }

  return results;
}

export function createProgram(options: CreateProgramOptions = {}): Command {
  const program = new Command();
  program
    .name("gflow")
    .description("Headless Consistency Engine for Google Flow.")
    .version(resolveVersion());
  program.exitOverride();

  // 1. gflow run <pipeline.yaml>
  program
    .command("run")
    .description("Execute a multi-layer consistency pipeline YAML on Google Flow.")
    .argument("<pipeline.yaml>", "path to pipeline YAML file")
    .option("--profile <name>", "browser profile name to run pipeline with")
    .option("--profiles <names...>", "list of Google profiles for failover")
    .option("--no-checkpoint", "disable checkpoint persistence and resumption")
    .option("--headed", "run with browser GUI visible", false)
    .option("--no-headed", "run browser headless")
    .option("--output-dir <dir>", "directory to save output artifacts and checkpoint")
    .option("--browser <name>", "browser channel: chrome or chromium", parseBrowserOption, DEFAULT_BROWSER_CHANNEL)
    .option("--continue-on-failure", "continue after individual job failures", false)
    .option("--autoheal", "automatically recover from browser stalls", true)
    .action(
      async (
        file: string,
        command: {
          profile?: string;
          profiles?: string[];
          checkpoint?: boolean;
          headed?: boolean;
          outputDir?: string;
          browser: BrowserChannel;
          continueOnFailure?: boolean;
          autoheal?: boolean;
        }
      ) => {
        const content = await readFile(file, "utf8");
        const batch = parseBatchYaml(content);
        const resolvedPipeline = resolvePipeline(batch);
        const yamlOutDir = resolvedPipeline.jobs.find((j) => j.out)?.out;
        const outDir = resolveOutputDir(command.outputDir || yamlOutDir || "./gflow-output");

        let profiles: string[] = [];
        if (command.profiles && command.profiles.length > 0) {
          profiles = command.profiles;
        } else if (command.profile) {
          profiles = [command.profile];
        } else if (resolvedPipeline.pipeline?.profiles && resolvedPipeline.pipeline.profiles.length > 0) {
          profiles = resolvedPipeline.pipeline.profiles;
        } else {
          profiles = await listDiscoveredProfiles();
        }
        if (!profiles || profiles.length === 0) {
          profiles = ["default"];
        }

        const orchestrator = new SmartPipelineOrchestrator({
          pipeline: resolvedPipeline.pipeline?.name,
          jobs: resolvedPipeline.jobs.map((job) => ({ ...job, out: outDir })),
          outDir,
          profiles,
          browser: command.browser ?? "chrome",
          headed: Boolean(command.headed),
          resume: command.checkpoint !== false,
          checkpoint: command.checkpoint !== false,
          autoheal: command.autoheal !== false,
          continueOnFailure: command.continueOnFailure ?? resolvedPipeline.pipeline?.continueOnFailure ?? false,
          automationFactory: options.automation
            ? async () => ({ automation: options.automation!, close: async () => undefined })
            : undefined
        });

        orchestrator.on("progress", (ev: PipelineProgressEvent) => {
          if (ev.type === "start") {
            console.log(`\n🚀 [gflow:run] ${ev.message ?? `Starting pipeline with ${ev.total} jobs across profile pool.`}`);
          } else if (ev.type === "job:start") {
            console.log(`[gflow:job] [${ev.index}/${ev.total}] Starting job '${ev.jobId}' (profile: ${ev.profile ?? "active"})...`);
          } else if (ev.type === "job:frame") {
            console.log(`🎬 [gflow:chain] ${ev.message}`);
          } else if (ev.type === "job:success") {
            console.log(`[gflow:job] [${ev.index}/${ev.total}] Finished '${ev.jobId}' ${ev.artifacts?.length ? `-> ${ev.artifacts.join(", ")}` : ""}`);
          } else if (ev.type === "job:retry") {
            console.warn(`⚠️ [gflow:job] [${ev.index}/${ev.total}] Retrying '${ev.jobId}': ${ev.error}`);
          } else if (ev.type === "profile:rotate") {
            console.warn(`🔄 [gflow:profile] ${ev.message}`);
          } else if (ev.type === "autoheal") {
            console.warn(`🩹 [gflow:autoheal] ${ev.message}`);
          } else if (ev.type === "job:fail") {
            console.error(`❌ [gflow:fail] Job '${ev.jobId}' failed: ${ev.error}`);
          } else if (ev.type === "complete") {
            console.log(`\n✨ [gflow:run] Pipeline finished.`);
          }
        });

        const result = await orchestrator.run();
        if (result.status === "failed") {
          process.exitCode = 1;
        }
      }
    );

  // 2. gflow doctor
  program
    .command("doctor")
    .description("Check that the Flow browser session is signed in and ready.")
    .option("--profile <name>", "browser profile name", "default")
    .option("--browser <name>", "browser channel: chrome or chromium", parseBrowserOption, DEFAULT_BROWSER_CHANNEL)
    .option("--headed", "show browser during connectivity check", false)
    .option("--no-headed", "run browser headless")
    .action(async (command: { profile: string; headed?: boolean; browser: BrowserChannel }) => {
      console.log(`🔍 Checking gflow environment for profile '${command.profile}'...\n`);
      const results = await runDoctorChecks({
        profile: command.profile,
        headed: command.headed,
        browser: command.browser,
        automation: options.automation
      });

      let hasFailure = false;
      for (const res of results) {
        if (res.ok) {
          console.log(`✅ [${res.name}] ${res.message}`);
        } else {
          hasFailure = true;
          console.error(`❌ [${res.name}] ${res.message}`);
          if (res.remediation) {
            console.error(`   👉 Remediation: ${res.remediation}`);
          }
        }
      }

      if (hasFailure) {
        console.error(`\n⚠️ Doctor checks failed. Please address the issues above.`);
        process.exitCode = 1;
      } else {
        console.log(`\n✨ All checks passed! Google Flow environment is ready.`);
      }
    });

  // 3. gflow profiles
  program
    .command("profiles")
    .description("List discovered Google Flow profiles, status, and health metrics.")
    .option("--json", "output profile states as JSON", false)
    .action(async (command: { json?: boolean }) => {
      const pool = await ProfilePool.create({ autoDiscover: true });
      const records = await pool.getPoolStatus();
      if (command.json) {
        console.log(JSON.stringify(records, null, 2));
      } else {
        console.log(formatProfileStatusTable(records));
      }
    });

  // 4. gflow auth login [profile]
  const auth = program.command("auth").description("Manage local Flow browser profiles and login session.");
  auth
    .command("login")
    .description("Open Google Chrome to authenticate with a Google Flow profile.")
    .argument("[profile]", "browser profile name", "default")
    .option("--profile <name>", "browser profile name")
    .action(async (profileArg: string, command: { profile?: string }) => {
      const targetProfile = command.profile ?? profileArg ?? "default";
      const profileDir = await launchLoginChrome(targetProfile);
      console.log(`Opened Google Chrome for login with profile '${targetProfile}': ${profileDir}`);
      console.log(`Sign in to your Google Flow account in that window, then run 'gflow doctor --profile ${targetProfile}'.`);
    });

  program.configureOutput({
    writeErr: (text) => process.stderr.write(text)
  });

  return program;
}

export async function runCli(argv: string[]): Promise<number> {
  const program = createProgram();
  try {
    await program.parseAsync(argv);
    return typeof process.exitCode === "number" ? process.exitCode : 0;
  } catch (error) {
    if (
      error instanceof CommanderError &&
      (error.code === "commander.helpDisplayed" ||
        error.code === "commander.version" ||
        error.code === "commander.invalidArgument" ||
        error.code === "commander.missingArgument")
    ) {
      return error.exitCode;
    }
    console.error(messageForError(error));
    return exitCodeForError(error);
  }
}
