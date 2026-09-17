import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

export type ProfileHealth = "ready" | "credit_exhausted" | "rate_limited" | "auth_required" | "unknown";

export interface ProfileRecord {
  name: string;
  status: ProfileHealth;
  lastUsed?: string;
  exhaustedAt?: string;
  cooldownUntil?: string;
  totalGenerated: number;
  failures: number;
  notes?: string;
}

export interface ProfileStatesFile {
  updatedAt: string;
  profiles: Record<string, ProfileRecord>;
}

function resolveProfileStatesPath(): string {
  if (process.env.GFLOW_PROFILE_STATES_PATH) {
    return process.env.GFLOW_PROFILE_STATES_PATH;
  }
  return join(process.cwd(), ".gflow", "profile-states.json");
}

export async function loadProfileStates(): Promise<ProfileStatesFile> {
  const filePath = resolveProfileStatesPath();
  try {
    const raw = await readFile(filePath, "utf8");
    return JSON.parse(raw) as ProfileStatesFile;
  } catch {
    return {
      updatedAt: new Date().toISOString(),
      profiles: {}
    };
  }
}

export async function saveProfileStates(data: ProfileStatesFile): Promise<void> {
  const filePath = resolveProfileStatesPath();
  await mkdir(dirname(filePath), { recursive: true });
  data.updatedAt = new Date().toISOString();
  await writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

export async function resetProfileState(name: string): Promise<void> {
  const data = await loadProfileStates();
  delete data.profiles[name];
  await saveProfileStates(data);
}

export async function getProfileRecord(name: string): Promise<ProfileRecord> {
  const data = await loadProfileStates();
  if (data.profiles[name]) {
    const record = data.profiles[name];
    // Auto-recover from rate-limit if cooldown passed
    if (record.status === "rate_limited" && record.cooldownUntil) {
      if (Date.now() >= new Date(record.cooldownUntil).getTime()) {
        record.status = "ready";
        record.cooldownUntil = undefined;
        await saveProfileStates(data);
      }
    }
    return record;
  }
  return {
    name,
    status: "ready",
    totalGenerated: 0,
    failures: 0
  };
}

export async function updateProfileRecord(name: string, updates: Partial<ProfileRecord>): Promise<ProfileRecord> {
  const data = await loadProfileStates();
  const current = data.profiles[name] ?? {
    name,
    status: "ready",
    totalGenerated: 0,
    failures: 0
  };
  const updated: ProfileRecord = {
    ...current,
    ...updates,
    name
  };
  data.profiles[name] = updated;
  await saveProfileStates(data);
  return updated;
}

/**
 * Scan the `.gflow/profiles` directory to find all existing local profiles.
 * Does NOT inject a phantom "default" profile if named profiles exist on disk.
 */
export async function listDiscoveredProfiles(baseDir = process.cwd()): Promise<string[]> {
  const profilesDir = join(baseDir, ".gflow", "profiles");
  try {
    const entries = await readdir(profilesDir, { withFileTypes: true });
    const discovered = entries
      .filter((e) => e.isDirectory() && !e.name.startsWith("."))
      .map((e) => e.name);

    if (discovered.length === 0) {
      return ["default"];
    }
    return discovered;
  } catch {
    return ["default"];
  }
}

/**
 * Formats an array of ProfileRecord objects into a clean, human-readable ASCII table.
 */
export function formatProfileStatusTable(records: ProfileRecord[]): string {
  if (records.length === 0) {
    return "No profiles discovered in .gflow/profiles. Run 'gflow auth login <profile>' to create one.";
  }

  const formatStatus = (status: ProfileHealth): string => {
    switch (status) {
      case "ready":
        return "READY";
      case "rate_limited":
        return "RATE_LIMITED";
      case "credit_exhausted":
        return "EXHAUSTED";
      case "auth_required":
        return "AUTH_REQUIRED";
      default:
        return "UNKNOWN";
    }
  };

  const formatCooldown = (rec: ProfileRecord): string => {
    if (rec.status === "rate_limited" && rec.cooldownUntil) {
      const diffMs = new Date(rec.cooldownUntil).getTime() - Date.now();
      if (diffMs > 0) {
        const mins = Math.ceil(diffMs / 60000);
        return `${mins}m left (${rec.cooldownUntil.replace("T", " ").slice(0, 19)})`;
      }
      return "Cooldown expired (ready)";
    }
    if (rec.status === "credit_exhausted" && rec.exhaustedAt) {
      return `Exhausted at ${rec.exhaustedAt.replace("T", " ").slice(0, 19)}`;
    }
    return "None";
  };

  const headers = ["Profile", "Status", "Cooldown / Quota", "Generated", "Failures", "Last Used"];
  const rows = records.map((r) => [
    r.name,
    formatStatus(r.status),
    formatCooldown(r),
    String(r.totalGenerated ?? 0),
    String(r.failures ?? 0),
    r.lastUsed ? r.lastUsed.replace("T", " ").slice(0, 19) : "Never"
  ]);

  const colWidths = headers.map((header, colIndex) =>
    Math.max(header.length, ...rows.map((row) => row[colIndex].length))
  );

  const pad = (text: string, width: number) => text.padEnd(width);

  const headerLine = headers.map((h, i) => pad(h, colWidths[i])).join("  ");
  const separatorLine = colWidths.map((w) => "─".repeat(w)).join("  ");
  const rowLines = rows.map((row) => row.map((cell, i) => pad(cell, colWidths[i])).join("  "));

  return [headerLine, separatorLine, ...rowLines].join("\n");
}
