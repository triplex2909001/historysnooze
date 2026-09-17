import {
  type CooldownDetail,
  type PoolAvailabilitySummary,
  ProfilePoolExhaustedError
} from "../errors.js";
import {
  getProfileRecord,
  updateProfileRecord,
  listDiscoveredProfiles,
  type ProfileRecord
} from "./profile-status.js";

export interface ProfilePoolOptions {
  profiles?: string[];
  autoDiscover?: boolean;
  rateLimitCooldownMs?: number;
}

export class ProfilePool {
  private profiles: string[];
  private activeIndex: number;
  private readonly rateLimitCooldownMs: number;
  private records: Map<string, ProfileRecord> = new Map();

  constructor(options: ProfilePoolOptions = {}) {
    const rawList = options.profiles && options.profiles.length > 0 ? options.profiles : ["default"];
    // Remove duplicates while preserving order
    this.profiles = Array.from(new Set(rawList));
    this.activeIndex = 0;
    this.rateLimitCooldownMs = options.rateLimitCooldownMs ?? 30 * 60 * 1000; // 30 minutes default

    for (const p of this.profiles) {
      this.records.set(p, {
        name: p,
        status: "ready",
        totalGenerated: 0,
        failures: 0
      });
    }
  }

  static async create(options: ProfilePoolOptions = {}): Promise<ProfilePool> {
    let profiles = options.profiles;
    if (!profiles || profiles.length === 0) {
      if (options.autoDiscover !== false) {
        profiles = await listDiscoveredProfiles();
      } else {
        profiles = ["default"];
      }
    }
    const pool = new ProfilePool({ ...options, profiles });
    await pool.syncFromDisk();
    return pool;
  }

  async syncFromDisk(): Promise<void> {
    for (const p of this.profiles) {
      const rec = await getProfileRecord(p);
      this.records.set(p, rec);
    }
  }

  getProfiles(): string[] {
    return [...this.profiles];
  }

  getActiveProfile(): string {
    return this.profiles[this.activeIndex] ?? "default";
  }

  setActiveProfile(name: string): boolean {
    const idx = this.profiles.indexOf(name);
    if (idx !== -1) {
      this.activeIndex = idx;
      return true;
    }
    return false;
  }

  async getActiveRecord(): Promise<ProfileRecord> {
    return this.getProfileRecord(this.getActiveProfile());
  }

  async getProfileRecord(name: string): Promise<ProfileRecord> {
    const rec = await getProfileRecord(name);
    this.records.set(name, rec);
    return rec;
  }

  isCoolingDown(profile?: string): boolean {
    const target = profile ?? this.getActiveProfile();
    const rec = this.records.get(target);
    if (!rec || rec.status !== "rate_limited" || !rec.cooldownUntil) {
      return false;
    }
    const untilMs = new Date(rec.cooldownUntil).getTime();
    if (Date.now() >= untilMs) {
      rec.status = "ready";
      rec.cooldownUntil = undefined;
      return false;
    }
    return true;
  }

  coolDownUntil(profile?: string): number | undefined {
    const target = profile ?? this.getActiveProfile();
    const rec = this.records.get(target);
    if (!rec || rec.status !== "rate_limited" || !rec.cooldownUntil) {
      return undefined;
    }
    const untilMs = new Date(rec.cooldownUntil).getTime();
    if (Date.now() >= untilMs) {
      rec.status = "ready";
      rec.cooldownUntil = undefined;
      return undefined;
    }
    return untilMs;
  }

  isExhausted(profile?: string): boolean {
    const target = profile ?? this.getActiveProfile();
    const rec = this.records.get(target);
    return rec?.status === "credit_exhausted";
  }

  async markSuccess(profile?: string): Promise<void> {
    const target = profile ?? this.getActiveProfile();
    const record = await getProfileRecord(target);
    const updated = await updateProfileRecord(target, {
      status: "ready",
      lastUsed: new Date().toISOString(),
      totalGenerated: record.totalGenerated + 1
    });
    this.records.set(target, updated);
  }

  async markCreditExhausted(profile?: string): Promise<void> {
    const target = profile ?? this.getActiveProfile();
    const record = await getProfileRecord(target);
    console.warn(`[gflow:profile] Profile '${target}' has exhausted its Flow credits/quota.`);
    const updated = await updateProfileRecord(target, {
      status: "credit_exhausted",
      exhaustedAt: new Date().toISOString(),
      failures: record.failures + 1
    });
    this.records.set(target, updated);
  }

  async markRateLimited(profileOrMs?: string | number, customCooldownMs?: number): Promise<void> {
    let target = this.getActiveProfile();
    let cooldownMs = this.rateLimitCooldownMs;

    if (typeof profileOrMs === "string") {
      target = profileOrMs;
      if (typeof customCooldownMs === "number") {
        cooldownMs = customCooldownMs;
      }
    } else if (typeof profileOrMs === "number") {
      cooldownMs = profileOrMs;
    }

    const cooldownUntil = new Date(Date.now() + cooldownMs).toISOString();
    const record = await getProfileRecord(target);
    console.warn(`[gflow:profile] Profile '${target}' hit rate limit. Cooldown until ${cooldownUntil}.`);
    const updated = await updateProfileRecord(target, {
      status: "rate_limited",
      cooldownUntil,
      failures: record.failures + 1
    });
    this.records.set(target, updated);
  }

  async getAvailabilitySummary(): Promise<PoolAvailabilitySummary> {
    const ready: string[] = [];
    const coolingDown: CooldownDetail[] = [];
    const exhausted: string[] = [];
    const authRequired: string[] = [];
    let earliest: { profile: string; coolDownUntil: Date; remainingMs: number } | undefined;

    for (const name of this.profiles) {
      const record = await getProfileRecord(name);
      this.records.set(name, record);

      const untilMs = this.coolDownUntil(name);
      if (untilMs !== undefined) {
        const remainingMs = Math.max(0, untilMs - Date.now());
        coolingDown.push({
          profile: name,
          coolDownUntil: untilMs,
          remainingMs
        });
        if (!earliest || untilMs < earliest.coolDownUntil.getTime()) {
          earliest = {
            profile: name,
            coolDownUntil: new Date(untilMs),
            remainingMs
          };
        }
      } else if (this.isExhausted(name)) {
        exhausted.push(name);
      } else if (record.status === "auth_required") {
        authRequired.push(name);
      } else {
        ready.push(name);
      }
    }

    return {
      total: this.profiles.length,
      ready,
      coolingDown,
      exhausted,
      authRequired,
      earliestAvailable: earliest
    };
  }

  /**
   * Attempts to find and rotate to the next available profile that is ready.
   * Cycles through the list once.
   * Returns the new profile name if rotated, or null if all profiles are exhausted/unusable.
   */
  async rotateToNextReady(): Promise<string | null> {
    const total = this.profiles.length;
    if (total <= 1) {
      return null;
    }

    for (let offset = 1; offset < total; offset++) {
      const candidateIndex = (this.activeIndex + offset) % total;
      const candidateName = this.profiles[candidateIndex];
      const record = await getProfileRecord(candidateName);
      this.records.set(candidateName, record);

      if (record.status === "ready" && !this.isCoolingDown(candidateName) && !this.isExhausted(candidateName)) {
        const previousProfile = this.getActiveProfile();
        this.activeIndex = candidateIndex;
        console.info(`[gflow:profile] Rotated active profile: '${previousProfile}' -> '${candidateName}'`);
        return candidateName;
      }
    }

    console.error(`[gflow:profile] All ${total} profiles in pool are exhausted or rate-limited.`);
    return null;
  }

  async acquireHealthyProfile(): Promise<string> {
    const active = this.getActiveProfile();
    if (!this.isCoolingDown(active) && !this.isExhausted(active)) {
      return active;
    }
    const rotated = await this.rotateToNextReady();
    if (rotated) {
      return rotated;
    }
    const summary = await this.getAvailabilitySummary();
    throw new ProfilePoolExhaustedError(summary);
  }

  async getPoolStatus(): Promise<ProfileRecord[]> {
    return Promise.all(this.profiles.map((p) => this.getProfileRecord(p)));
  }
}
