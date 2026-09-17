import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import type { FlowAutomation } from "../src/flow/types.js";
import { createProgram, runCli } from "../src/cli.js";

describe("CLI Surface & Options", () => {
  it("returns zero for top-level help and version", async () => {
    await expect(runCli(["node", "gflow", "--help"])).resolves.toBe(0);
    await expect(runCli(["node", "gflow", "--version"])).resolves.toBe(0);
  });

  it("parses auth login as a subcommand with --profile option", () => {
    const program = createProgram();
    const auth = program.commands.find((command) => command.name() === "auth");
    const login = auth?.commands.find((command) => command.name() === "login");

    expect(auth).toBeDefined();
    expect(login).toBeDefined();
    expect(login?.options.map((option) => option.long)).toContain("--profile");
  });

  it("configures doctor options with headless default and browser selection", () => {
    const program = createProgram();
    const doctor = program.commands.find((command) => command.name() === "doctor");
    expect(doctor).toBeDefined();

    const options = doctor!.options.map((o) => o.long);
    expect(options).toContain("--profile");
    expect(options).toContain("--browser");
    expect(options).toContain("--headed");
    expect(options).toContain("--no-headed");

    const headedOpt = doctor!.options.find((o) => o.long === "--headed");
    expect(headedOpt?.defaultValue).toBe(false);
  });

  it("configures run options: --profile, --no-checkpoint, --headed, --output-dir", () => {
    const program = createProgram();
    const run = program.commands.find((command) => command.name() === "run");
    expect(run).toBeDefined();

    const options = run!.options.map((o) => o.long);
    expect(options).toContain("--profile");
    expect(options).toContain("--no-checkpoint");
    expect(options).toContain("--headed");
    expect(options.some((opt) => opt === "--output-dir" || opt === "--out")).toBe(true);
    expect(options).toContain("--browser");
    expect(options).toContain("--continue-on-failure");
  });

  it("rejects unsupported browser channels with invalidArgument", async () => {
    const program = createProgram();
    program.configureOutput({ writeErr: () => {} });

    await expect(
      program.parseAsync(["node", "gflow", "doctor", "--browser", "firefox"])
    ).rejects.toMatchObject({
      code: "commander.invalidArgument"
    });
  });
});

describe("CLI Execution & Automation Wiring", () => {
  let tempDir: string;
  let pipelinePath: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-cli-test-"));
    pipelinePath = join(tempDir, "pipeline.yaml");
    await writeFile(
      pipelinePath,
      `
pipeline: test-pipeline
jobs:
  - id: shot-1
    type: image
    prompt: "A cinematic establishing shot"
    outputs: 1
`
    );
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  it("runs a pipeline through mock automation via run command", async () => {
    const automation: FlowAutomation = {
      runJob: vi.fn(async (input) => ({
        jobId: input.job.id,
        artifacts: [{ path: join(tempDir, "shot-1.png"), metadataPath: join(tempDir, "shot-1.json") }],
        flowUrl: "https://flow.google.com"
      }))
    };

    const program = createProgram({ automation });
    program.configureOutput({ writeErr: () => {} });

    await program.parseAsync([
      "node",
      "gflow",
      "run",
      pipelinePath,
      "--no-checkpoint",
      "--output-dir",
      tempDir
    ]);

    expect(automation.runJob).toHaveBeenCalledTimes(1);
    expect(automation.runJob).toHaveBeenCalledWith(
      expect.objectContaining({
        job: expect.objectContaining({
          id: "shot-1",
          type: "image",
          prompt: "A cinematic establishing shot"
        }),
        outDir: tempDir
      })
    );
  });

  it("passes profile and headed options to orchestrator", async () => {
    const program = createProgram();
    const run = program.commands.find((c) => c.name() === "run");

    await run!.parseOptions([
      pipelinePath,
      "--profile",
      "work-profile",
      "--headed",
      "--no-checkpoint"
    ]);

    expect(run!.opts().profile).toBe("work-profile");
    expect(run!.opts().headed).toBe(true);
    expect(run!.opts().checkpoint).toBe(false);
  });
});

describe("CLI Error Handling", () => {
  it("rejects run when required pipeline argument is missing", async () => {
    const program = createProgram();
    program.configureOutput({ writeErr: () => {} });

    await expect(program.parseAsync(["node", "gflow", "run"])).rejects.toMatchObject({
      code: "commander.missingArgument"
    });
  });

  it("returns exit code 1 via runCli when pipeline argument is missing", async () => {
    const exitCode = await runCli(["node", "gflow", "run"]);
    expect(exitCode).toBe(1);
  });

  it("rejects run when pipeline file does not exist", async () => {
    const program = createProgram();
    program.configureOutput({ writeErr: () => {} });

    await expect(
      program.parseAsync(["node", "gflow", "run", "non-existent-pipeline.yaml", "--no-checkpoint"])
    ).rejects.toThrow(/ENOENT|no such file/i);
  });

  it("returns exit code 1 via runCli when pipeline file does not exist", async () => {
    const exitCode = await runCli(["node", "gflow", "run", "non-existent-pipeline.yaml"]);
    expect(exitCode).toBe(1);
  });

  it("rejects legacy deleted commands with unknownCommand error", async () => {
    const legacyCommands = [
      ["image", "--prompt", "test"],
      ["batch", "pipeline.yaml"],
      ["prompts", "prompts.txt"],
      ["character", "create", "--name", "Nyra"],
      ["tool", "list"],
      ["agent", "--prompt", "test"],
      ["extend", "--media-id", "123"],
      ["scene", "list"]
    ];

    for (const cmd of legacyCommands) {
      const program = createProgram();
      program.configureOutput({ writeErr: () => {} });

      await expect(
        program.parseAsync(["node", "gflow", ...cmd])
      ).rejects.toMatchObject({
        code: "commander.unknownCommand"
      });
    }
  });
});
