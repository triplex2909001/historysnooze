import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { Command } from "commander";
import { createProgram, resolveVersion } from "../src/cli.js";

function sub(program: Command, name: string): Command {
  const found = program.commands.find((c) => c.name() === name);
  if (!found) throw new Error(`command not found: ${name}`);
  return found;
}

describe("gflow help", () => {
  it("lists streamlined top-level commands in help output", () => {
    const program = createProgram();
    const help = program.helpInformation();
    const commandNames = program.commands.map((c) => c.name());

    // 1. Positive assertions: core operational commands
    const expectedCommands = ["run", "doctor", "profiles", "auth"];
    for (const name of expectedCommands) {
      expect(commandNames).toContain(name);
      expect(help).toContain(name);
    }

    // 2. Negative assertions: legacy bloat & deleted GUI commands must NOT exist
    const legacyCommands = [
      "image",
      "prompts",
      "batch",
      "character",
      "tool",
      "agent",
      "extend",
      "scene",
      "video"
    ];
    for (const name of legacyCommands) {
      expect(commandNames).not.toContain(name);
      // Ensure command name does not appear as a top-level command entry in help text
      const cmdEntryRegex = new RegExp(`^\\s*${name}\\b`, "m");
      expect(help).not.toMatch(cmdEntryRegex);
    }

    // 3. Descriptive assertions for command roles
    expect(help).toMatch(/run[\s\S]*?pipeline/i);
    expect(help).toMatch(/doctor[\s\S]*?ready/i);
    expect(help).toMatch(/profiles[\s\S]*?(profile|status|pool)/i);
    expect(help).toMatch(/auth[\s\S]*?(session|login)/i);
  });

  it("exposes run subcommand help, arguments, and options", () => {
    const program = createProgram();
    const runHelp = sub(program, "run").helpInformation();

    expect(runHelp).toMatch(/run/);
    expect(runHelp).toMatch(/<pipeline.*?>/i);
    expect(runHelp).toContain("--profile");
    expect(runHelp).toContain("--no-checkpoint");
    expect(runHelp).toContain("--headed");
    expect(runHelp).toMatch(/--(output-dir|out)/);
    expect(runHelp).toContain("--browser");
    expect(runHelp).toContain("--continue-on-failure");
  });

  it("exposes doctor subcommand help and options", () => {
    const program = createProgram();
    const doctorHelp = sub(program, "doctor").helpInformation();

    expect(doctorHelp).toMatch(/doctor/);
    expect(doctorHelp).toContain("--profile");
    expect(doctorHelp).toContain("--browser");
    expect(doctorHelp).toContain("--headed");
    expect(doctorHelp).toContain("--no-headed");
  });

  it("exposes profiles subcommand help", () => {
    const program = createProgram();
    const profilesHelp = sub(program, "profiles").helpInformation();

    expect(profilesHelp).toMatch(/profiles/);
    expect(profilesHelp).toMatch(/(status|pool|cooldown|health|profile)/i);
  });

  it("exposes auth login subcommand help and options", () => {
    const program = createProgram();
    const authHelp = sub(program, "auth").helpInformation();
    expect(authHelp).toContain("login");

    const loginHelp = sub(sub(program, "auth"), "login").helpInformation();
    expect(loginHelp).toContain("--profile");
  });

  it("reports the package.json version (no drift)", () => {
    const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as { version: string };
    expect(resolveVersion()).toBe(pkg.version);
  });
});
