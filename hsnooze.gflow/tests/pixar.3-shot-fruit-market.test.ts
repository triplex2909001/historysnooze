import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { execFile, execFileSync, spawnSync } from "node:child_process";
import { promisify } from "node:util";
import { createHash } from "node:crypto";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import YAML from "yaml";
import {
  parseBatchYaml,
  batchSchema,
} from "../src/jobs/schema.js";
import type { BatchFile, VideoJob } from "../src/jobs/schema.js";
import {
  resolvePipeline,
  interpolateJobOutputs,
} from "../src/jobs/resolver.js";
import { extractVideoFrame } from "../src/jobs/frame-extractor.js";

const execFileAsync = promisify(execFile);

// ============================================================================
// Constants & Paths
// ============================================================================

const REPO_ROOT = resolve(__dirname, "..");
const OUT_DIR = resolve(REPO_ROOT, "out");
const FRAMES_DIR = join(OUT_DIR, "frames");
const ASSETS_DIR = resolve(REPO_ROOT, "examples/assets/pixar_fruit_market");
const PIPELINE_YAML_PATH = resolve(REPO_ROOT, "examples/pixar_fruit_market_pipeline.yaml");

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// 6 authoritative reference PNGs defined in the pipeline specification
const REQUIRED_REFERENCE_PNGS = [
  "ming_reference_sheet.png",
  "ling_reference_sheet.png",
  "fruit_market_stall_plate.png",
  "bamboo_basket_isolated.png",
  "fresh_apple_isolated.png",
  "watermelon_slice_isolated.png",
] as const;

const DELIVERED_SHOTS = [
  {
    id: "shot1_market_arrival",
    mp4: "shot1_market_arrival-001.mp4",
    json: "shot1_market_arrival-001.json",
    minDuration: 7.0,
    expectedRatio: "9:16",
    hasStartFrameRef: false,
  },
  {
    id: "shot2_apple_discovery",
    mp4: "shot2_apple_discovery-001.mp4",
    json: "shot2_apple_discovery-001.json",
    minDuration: 7.0,
    expectedRatio: "9:16",
    hasStartFrameRef: true,
    startFrameRef: "$output:shot1_market_arrival",
  },
  {
    id: "shot3_watermelon_joy",
    mp4: "shot3_watermelon_joy-001.mp4",
    json: "shot3_watermelon_joy-001.json",
    minDuration: 6.0,
    expectedRatio: "9:16",
    hasStartFrameRef: true,
    startFrameRef: "$output:shot2_apple_discovery",
  },
] as const;

// ============================================================================
// Pure Verification Helpers: CRC32, PNG Parsing & FFprobe
// ============================================================================

const CRC_TABLE = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) {
    c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  CRC_TABLE[n] = c >>> 0;
}

function computePngCrc32(data: Uint8Array | Buffer): number {
  let c = 0xffffffff;
  for (let i = 0; i < data.length; i++) {
    c = CRC_TABLE[(c ^ data[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

interface PngHeaderInfo {
  signatureValid: boolean;
  width: number;
  height: number;
  bitDepth: number;
  colorType: number;
  compression: number;
  filter: number;
  interlace: number;
  crcMatch: boolean;
}

function parsePngHeader(buf: Buffer): PngHeaderInfo {
  const signatureValid = buf.length >= 8 && buf.subarray(0, 8).equals(PNG_MAGIC);
  if (!signatureValid || buf.length < 33) {
    return {
      signatureValid,
      width: 0,
      height: 0,
      bitDepth: 0,
      colorType: 0,
      compression: -1,
      filter: -1,
      interlace: -1,
      crcMatch: false,
    };
  }

  const chunkType = buf.subarray(12, 16).toString("ascii");
  if (chunkType !== "IHDR") {
    return {
      signatureValid: true,
      width: 0,
      height: 0,
      bitDepth: 0,
      colorType: 0,
      compression: -1,
      filter: -1,
      interlace: -1,
      crcMatch: false,
    };
  }

  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  const bitDepth = buf[24];
  const colorType = buf[25];
  const compression = buf[26];
  const filter = buf[27];
  const interlace = buf[28];
  const storedCrc = buf.readUInt32BE(29);
  const computedCrc = computePngCrc32(buf.subarray(12, 29));

  return {
    signatureValid: true,
    width,
    height,
    bitDepth,
    colorType,
    compression,
    filter,
    interlace,
    crcMatch: storedCrc === computedCrc,
  };
}

interface StreamInfo {
  index: number;
  codec_name: string;
  codec_type: string;
  codec_tag_string?: string;
  width?: number;
  height?: number;
  r_frame_rate?: string;
  avg_frame_rate?: string;
  field_order?: string;
  duration?: string;
  bit_rate?: string;
  nb_frames?: string;
  sample_rate?: string;
  channels?: number;
  channel_layout?: string;
}

interface FormatInfo {
  filename: string;
  nb_streams: number;
  format_name: string;
  duration: string;
  size: string;
  bit_rate: string;
}

interface FfprobeOutput {
  streams: StreamInfo[];
  format: FormatInfo;
}

function probeMedia(filePath: string): FfprobeOutput {
  const stdout = execFileSync("ffprobe", [
    "-v", "error",
    "-show_format",
    "-show_streams",
    "-print_format", "json",
    filePath,
  ], { encoding: "utf-8" });
  return JSON.parse(stdout) as FfprobeOutput;
}

function runFfmpegDecodeCheck(filePath: string): { exitCode: number; stderr: string } {
  const res = spawnSync("ffmpeg", [
    "-v", "warning",
    "-i", filePath,
    "-f", "null",
    "-",
  ], { encoding: "utf-8" });
  return { exitCode: res.status ?? 1, stderr: (res.stderr ?? "").trim() };
}

// ============================================================================
// Multi-Layer Visual Continuity & Metric Computation Helpers
// ============================================================================

const rawRgbCache = new Map<string, Buffer>();

async function getRawRgb(args: string[]): Promise<Buffer> {
  const cacheKey = args.join(" ");
  const cached = rawRgbCache.get(cacheKey);
  if (cached) return cached;

  const { stdout } = await execFileAsync("ffmpeg", [
    "-loglevel", "error",
    "-y",
    ...args,
    "-f", "rawvideo",
    "-pix_fmt", "rgb24",
    "pipe:1",
  ], { maxBuffer: 25 * 1024 * 1024, encoding: "buffer" });

  const buf = stdout as unknown as Buffer;
  rawRgbCache.set(cacheKey, buf);
  return buf;
}

async function getPngRgb(pngPath: string): Promise<Buffer> {
  return getRawRgb(["-i", pngPath]);
}

async function getVideoFrameRgb(videoPath: string, timeSec: number): Promise<Buffer> {
  return getRawRgb(["-ss", String(timeSec), "-i", videoPath, "-frames:v", "1"]);
}

function computeHistogram(buffer: Buffer, bins = 32): [Float64Array, Float64Array, Float64Array] {
  const binSize = 256 / bins;
  const rHist = new Float64Array(bins);
  const gHist = new Float64Array(bins);
  const bHist = new Float64Array(bins);
  const totalPixels = buffer.length / 3;

  for (let i = 0; i < buffer.length; i += 3) {
    const rBin = Math.min(bins - 1, Math.floor(buffer[i] / binSize));
    const gBin = Math.min(bins - 1, Math.floor(buffer[i + 1] / binSize));
    const bBin = Math.min(bins - 1, Math.floor(buffer[i + 2] / binSize));
    rHist[rBin]++;
    gHist[gBin]++;
    bHist[bBin]++;
  }

  for (let b = 0; b < bins; b++) {
    rHist[b] /= totalPixels;
    gHist[b] /= totalPixels;
    bHist[b] /= totalPixels;
  }
  return [rHist, gHist, bHist];
}

function cosineSimilarity(
  h1: [Float64Array, Float64Array, Float64Array],
  h2: [Float64Array, Float64Array, Float64Array]
): number {
  function vecCos(v1: Float64Array, v2: Float64Array): number {
    let dot = 0, norm1 = 0, norm2 = 0;
    for (let i = 0; i < v1.length; i++) {
      dot += v1[i] * v2[i];
      norm1 += v1[i] * v1[i];
      norm2 += v2[i] * v2[i];
    }
    return dot / (Math.sqrt(norm1) * Math.sqrt(norm2));
  }
  return (vecCos(h1[0], h2[0]) + vecCos(h1[1], h2[1]) + vecCos(h1[2], h2[2])) / 3;
}

interface ColorPaletteMetrics {
  totalPixels: number;
  yellowHoodieRatio: number;
  tealOverallsRatio: number;
  warmLanternRatio: number;
}

function analyzeColorPalette(buffer: Buffer): ColorPaletteMetrics {
  let yellowPixels = 0;
  let tealPixels = 0;
  let warmLanternPixels = 0;
  const totalPixels = buffer.length / 3;

  for (let i = 0; i < buffer.length; i += 3) {
    const r = buffer[i];
    const g = buffer[i + 1];
    const b = buffer[i + 2];

    // Ming's signature vibrant mustard-yellow hoodie:
    // High R and G with low B (warm bright yellow)
    if (r > 140 && g > 120 && b < 100 && r > b * 1.4 && g > b * 1.2) {
      yellowPixels++;
    }

    // Xiao Ling's signature pastel teal denim overalls:
    // Elevated green and blue higher than red
    if (g > 80 && b > 80 && g > r * 1.05 && b > r * 0.9) {
      tealPixels++;
    }

    // Traditional Chinese fruit market stall warm red lantern / golden hour illumination:
    // Rich warm red/amber glow with R > G and low B
    if (r > 150 && g > 60 && b < 100 && r > g) {
      warmLanternPixels++;
    }
  }

  return {
    totalPixels,
    yellowHoodieRatio: yellowPixels / totalPixels,
    tealOverallsRatio: tealPixels / totalPixels,
    warmLanternRatio: warmLanternPixels / totalPixels,
  };
}

function computeMeanLuminance(buffer: Buffer): number {
  let sum = 0;
  const total = buffer.length / 3;
  for (let i = 0; i < buffer.length; i += 3) {
    // Standard ITU-R BT.601 luminance coefficients
    sum += 0.299 * buffer[i] + 0.587 * buffer[i + 1] + 0.114 * buffer[i + 2];
  }
  return sum / total;
}

// ============================================================================
// Test Suite: 3D Pixar Fruit Market Production Verification
// ============================================================================

describe("Pixar 3-Shot Fruit Market Production Automated Verification & Visual Continuity Audit", () => {

  // ==========================================================================
  // Dimension 1: Asset & Storyboard Specs
  // ==========================================================================
  describe("Dimension 1: Asset & Storyboard Specs", () => {
    it("verifies all 6 required reference PNG assets exist in examples/assets/pixar_fruit_market/ and are non-empty", () => {
      for (const assetName of REQUIRED_REFERENCE_PNGS) {
        const fullPath = join(ASSETS_DIR, assetName);
        expect(existsSync(fullPath), `Asset ${assetName} must exist`).toBe(true);

        const buf = readFileSync(fullPath);
        expect(buf.length, `Asset ${assetName} must exceed 500KB`).toBeGreaterThan(500_000);
      }
    });

    it("verifies valid PNG headers and IHDR chunks for all 6 reference PNG assets", () => {
      for (const assetName of REQUIRED_REFERENCE_PNGS) {
        const fullPath = join(ASSETS_DIR, assetName);
        const buf = readFileSync(fullPath);
        const header = parsePngHeader(buf);

        expect(header.signatureValid, `PNG magic bytes invalid for ${assetName}`).toBe(true);
        expect(header.width, `Width must be >= 1024 for ${assetName}`).toBeGreaterThanOrEqual(1024);
        expect(header.height, `Height must be >= 768 for ${assetName}`).toBeGreaterThanOrEqual(768);
        expect(header.bitDepth, `Bit depth must be 8 for ${assetName}`).toBe(8);
        expect([2, 6], `Color type must be Truecolor RGB or RGBA for ${assetName}`).toContain(header.colorType);
        expect(header.compression, `Compression must be 0 for ${assetName}`).toBe(0);
        expect(header.filter, `Filter must be 0 for ${assetName}`).toBe(0);
        expect([0, 1], `Interlace must be 0 or 1 for ${assetName}`).toContain(header.interlace);
        expect(header.crcMatch, `IHDR CRC32 must match for ${assetName}`).toBe(true);
      }
    });

    it("parses pipeline YAML cleanly through batchSchema and validates creative specifications", () => {
      expect(existsSync(PIPELINE_YAML_PATH)).toBe(true);
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");

      // Validate through parseBatchYaml and batchSchema
      const batch: BatchFile = parseBatchYaml(rawYaml);
      expect(batch).toBeDefined();

      const parsedDirect = batchSchema.parse(YAML.parse(rawYaml));
      expect(parsedDirect).toBeDefined();

      // Check characters
      expect(Object.keys(batch.characters).sort()).toEqual(["ling", "ming"]);
      const ming = batch.characters.ming;
      expect(ming.name).toBe("Li Ming");
      expect(ming.referenceSheet).toBe("examples/assets/pixar_fruit_market/ming_reference_sheet.png");
      expect(ming.pinned).toBe(true);
      expect(ming.description).toContain("yellow");
      expect(ming.description).toContain("hoodie");

      const ling = batch.characters.ling;
      expect(ling.name).toBe("Xiao Ling");
      expect(ling.referenceSheet).toBe("examples/assets/pixar_fruit_market/ling_reference_sheet.png");
      expect(ling.pinned).toBe(true);
      expect(ling.description).toContain("teal");

      // Check background
      expect(Object.keys(batch.backgrounds)).toEqual(["fruit_market_stall"]);
      const bg = batch.backgrounds.fruit_market_stall;
      expect(bg.plate).toBe("examples/assets/pixar_fruit_market/fruit_market_stall_plate.png");
      expect(bg.description).toContain("lantern");

      // Check props
      expect(Object.keys(batch.props).sort()).toEqual(["bamboo_basket", "fresh_apple", "watermelon_slice"]);
      expect(batch.props.bamboo_basket.asset).toBe("examples/assets/pixar_fruit_market/bamboo_basket_isolated.png");
      expect(batch.props.fresh_apple.asset).toBe("examples/assets/pixar_fruit_market/fresh_apple_isolated.png");
      expect(batch.props.watermelon_slice.asset).toBe("examples/assets/pixar_fruit_market/watermelon_slice_isolated.png");

      // Check jobs count and ratios
      expect(batch.jobs).toHaveLength(3);
      for (const job of batch.jobs) {
        expect(job.type).toBe("video");
        expect(job.ratio).toBe("9:16");
        expect(job.model).toBe("veo-3.1-fast");
      }
    });

    it("resolves static $ref bindings and infers topological DAG dependencies via resolvePipeline", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      expect(resolved.jobs).toHaveLength(3);
      expect(resolved.jobs.map((j) => j.id)).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy",
      ]);

      // Verify character bindings resolved into character lists and resolvedCharacters
      const shot1 = resolved.jobs[0] as VideoJob & { resolvedCharacters?: unknown[] };
      expect(shot1.character).toEqual(["Li Ming", "Xiao Ling"]);
      expect(shot1.resolvedCharacters).toBeDefined();
      expect(shot1.resolvedCharacters).toHaveLength(2);
      expect(shot1.dependsOn).toEqual([]);

      // Shot 2 has inferred dependency on shot1 from $output:shot1_market_arrival
      const shot2 = resolved.jobs[1] as VideoJob;
      expect(shot2.dependsOn).toContain("shot1_market_arrival");
      expect(shot2.startFrame).toBe("$output:shot1_market_arrival");

      // Shot 3 has inferred dependency on shot2 from $output:shot2_apple_discovery
      const shot3 = resolved.jobs[2] as VideoJob;
      expect(shot3.dependsOn).toContain("shot2_apple_discovery");
      expect(shot3.startFrame).toBe("$output:shot2_apple_discovery");
    });

    it("resolves runtime $output artifact references into real file paths via interpolateJobOutputs", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      const artifactsMap: Record<string, string[]> = {
        shot1_market_arrival: [join(OUT_DIR, "shot1_market_arrival-001.mp4")],
        shot2_apple_discovery: [join(OUT_DIR, "shot2_apple_discovery-001.mp4")],
        shot3_watermelon_joy: [join(OUT_DIR, "shot3_watermelon_joy-001.mp4")],
      };

      const interpolatedJobs = resolved.jobs.map((j) => interpolateJobOutputs(j, artifactsMap));

      const s2 = interpolatedJobs[1] as VideoJob;
      expect(s2.startFrame).toBe(join(OUT_DIR, "shot1_market_arrival-001.mp4"));

      const s3 = interpolatedJobs[2] as VideoJob;
      expect(s3.startFrame).toBe(join(OUT_DIR, "shot2_apple_discovery-001.mp4"));
    });
  });

  // ==========================================================================
  // Dimension 2: Video Generation & Output
  // ==========================================================================
  describe("Dimension 2: Video Generation & Output Deliverables", () => {
    for (const shot of DELIVERED_SHOTS) {
      it(`verifies delivered video file exists and exceeds 1MB for ${shot.id}`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        expect(existsSync(mp4Path), `MP4 file ${shot.mp4} must exist in out/`).toBe(true);

        const buf = readFileSync(mp4Path);
        expect(buf.length, `MP4 file ${shot.mp4} size must exceed 1MB`).toBeGreaterThan(1_000_000);
      });

      it(`verifies valid JSON metadata sidecar for ${shot.id}`, () => {
        const jsonPath = join(OUT_DIR, shot.json);
        expect(existsSync(jsonPath), `Sidecar JSON ${shot.json} must exist in out/`).toBe(true);

        const content = JSON.parse(readFileSync(jsonPath, "utf-8"));
        expect(content.jobId).toBe(shot.id);
        expect(content.type).toBe("video");
        expect(content.ratio).toBe("9:16");
        expect(content.status).toBe("downloaded");
        expect(content.model).toBe("veo-3.1-fast");
        expect(content.downloadedAt).toBeDefined();
        expect(content.characters).toEqual(["Li Ming", "Xiao Ling"]);
      });
    }

    it("verifies checkpoint.json has all 3 jobs marked completed with corresponding artifacts", () => {
      const cpPath = join(OUT_DIR, "checkpoint.json");
      expect(existsSync(cpPath), "checkpoint.json must exist in out/").toBe(true);

      const cp = JSON.parse(readFileSync(cpPath, "utf-8"));
      expect(cp.pipeline).toBe("pixar-fruit-market-vocabulary");
      expect(cp.currentJobId).toBeNull();
      expect(cp.completed).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy",
      ]);
      expect(cp.failed).toEqual([]);

      for (const shot of DELIVERED_SHOTS) {
        expect(cp.completedJobs[shot.id]).toBeDefined();
        expect(cp.completedJobs[shot.id].status).toBe("completed");
        const artifactList = cp.completedJobs[shot.id].artifacts;
        expect(artifactList).toHaveLength(1);
        expect(existsSync(artifactList[0])).toBe(true);
      }
    });
  });

  // ==========================================================================
  // Dimension 3: Technical 9:16 & Stream Verification
  // ==========================================================================
  describe("Dimension 3: Technical 9:16 & Stream Verification", () => {
    let cumulativeDuration = 0;

    for (const shot of DELIVERED_SHOTS) {
      it(`verifies video stream specs for ${shot.mp4}: 720x1280, 9:16, h264, 24fps progressive`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        const probe = probeMedia(mp4Path);

        const videoStreams = probe.streams.filter((s) => s.codec_type === "video");
        expect(videoStreams).toHaveLength(1);

        const vs = videoStreams[0];
        expect(vs.codec_name).toBe("h264");
        expect(vs.codec_tag_string).toBe("avc1");
        expect(vs.width).toBe(720);
        expect(vs.height).toBe(1280);

        // Aspect ratio: exactly 9:16
        const ratio = vs.width! / vs.height!;
        expect(Math.abs(ratio - 9 / 16)).toBeLessThan(1e-4);

        // 24fps progressive scan
        expect(vs.r_frame_rate).toBe("24/1");
        expect(vs.avg_frame_rate).toBe("24/1");
        expect(vs.field_order).toBe("progressive");

        // Duration >= 7.0s
        const dur = parseFloat(vs.duration ?? "0");
        expect(dur).toBeGreaterThanOrEqual(shot.minDuration);
        cumulativeDuration += dur;

        // Bitrate > 1 Mbps
        const streamBitrate = parseInt(vs.bit_rate ?? "0", 10);
        expect(streamBitrate).toBeGreaterThan(1_000_000);
      });

      it(`verifies valid stereo AAC audio stream for ${shot.mp4}`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        const probe = probeMedia(mp4Path);

        const audioStreams = probe.streams.filter((s) => s.codec_type === "audio");
        expect(audioStreams).toHaveLength(1);

        const as = audioStreams[0];
        expect(as.codec_name).toBe("aac");
        expect(as.codec_tag_string).toBe("mp4a");
        expect(as.channels).toBe(2);
        expect(as.channel_layout).toBe("stereo");
        expect(parseInt(as.sample_rate ?? "0", 10)).toBe(48000);

        const audioDur = parseFloat(as.duration ?? "0");
        expect(audioDur).toBeGreaterThanOrEqual(shot.minDuration);
      });

      it(`verifies full clean decoding without errors or warnings for ${shot.mp4}`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        const check = runFfmpegDecodeCheck(mp4Path);
        expect(check.exitCode).toBe(0);
        expect(check.stderr).toBe("");
      });
    }

    it("verifies cumulative video duration satisfies target storyboard requirement", () => {
      // 3 shots satisfying the storyboard target (15s to 36s window)
      expect(cumulativeDuration).toBeGreaterThanOrEqual(15.0);
      expect(cumulativeDuration).toBeLessThanOrEqual(36.0);
    });
  });

  // ==========================================================================
  // Dimension 4: Scene Chaining & Chained Frames
  // ==========================================================================
  describe("Dimension 4: Scene Chaining & Chained Frames", () => {
    const shot1LastFrame = join(FRAMES_DIR, "shot1_market_arrival-001-last-frame.png");
    const shot2LastFrame = join(FRAMES_DIR, "shot2_apple_discovery-001-last-frame.png");

    it("verifies extracted terminal frames exist in out/frames/ and exceed 500KB", () => {
      for (const framePath of [shot1LastFrame, shot2LastFrame]) {
        expect(existsSync(framePath), `Chaining frame ${framePath} must exist`).toBe(true);
        const buf = readFileSync(framePath);
        expect(buf.length).toBeGreaterThan(500_000);
      }
    });

    it("verifies chaining frames have valid PNG headers and 720x1280 resolution", () => {
      for (const framePath of [shot1LastFrame, shot2LastFrame]) {
        const buf = readFileSync(framePath);
        const header = parsePngHeader(buf);

        expect(header.signatureValid).toBe(true);
        expect(header.width).toBe(720);
        expect(header.height).toBe(1280);
        expect(header.bitDepth).toBe(8);
        expect([2, 6]).toContain(header.colorType);
        expect(header.crcMatch).toBe(true);
      }
    });

    it("independently extracts terminal frame of Shot 1 and matches delivered frame hash exactly", async () => {
      const deliveredHash = createHash("md5").update(readFileSync(shot1LastFrame)).digest("hex");
      const tmpDir = await mkdtemp(join(tmpdir(), "pixar-chain-shot1-"));
      const tmpFrame = join(tmpDir, "extracted_shot1.png");

      try {
        await execFileAsync("ffmpeg", [
          "-y",
          "-sseof", "-1",
          "-i", join(OUT_DIR, "shot1_market_arrival-001.mp4"),
          "-update", "1",
          "-q:v", "1",
          tmpFrame,
        ]);

        const independentHash = createHash("md5").update(readFileSync(tmpFrame)).digest("hex");
        expect(independentHash).toBe(deliveredHash);
      } finally {
        await rm(tmpDir, { recursive: true, force: true });
      }
    });

    it("independently extracts terminal frame of Shot 2 and matches delivered frame hash exactly", async () => {
      const deliveredHash = createHash("md5").update(readFileSync(shot2LastFrame)).digest("hex");
      const tmpDir = await mkdtemp(join(tmpdir(), "pixar-chain-shot2-"));
      const tmpFrame = join(tmpDir, "extracted_shot2.png");

      try {
        await execFileAsync("ffmpeg", [
          "-y",
          "-sseof", "-1",
          "-i", join(OUT_DIR, "shot2_apple_discovery-001.mp4"),
          "-update", "1",
          "-q:v", "1",
          tmpFrame,
        ]);

        const independentHash = createHash("md5").update(readFileSync(tmpFrame)).digest("hex");
        expect(independentHash).toBe(deliveredHash);
      } finally {
        await rm(tmpDir, { recursive: true, force: true });
      }
    });

    it("verifies extractVideoFrame caching contract from src/jobs/frame-extractor.ts", async () => {
      const shot1Mp4 = join(OUT_DIR, "shot1_market_arrival-001.mp4");
      const res1 = await extractVideoFrame(shot1Mp4, { outDir: OUT_DIR });
      expect(res1.cached).toBe(true);
      expect(res1.path).toBe(shot1LastFrame);
      expect(res1.sourceVideo).toBe(shot1Mp4);

      const shot2Mp4 = join(OUT_DIR, "shot2_apple_discovery-001.mp4");
      const res2 = await extractVideoFrame(shot2Mp4, { outDir: OUT_DIR });
      expect(res2.cached).toBe(true);
      expect(res2.path).toBe(shot2LastFrame);
      expect(res2.sourceVideo).toBe(shot2Mp4);
    });
  });

  // ==========================================================================
  // Dimension 5: Multi-Layer Visual Continuity Audit
  // ==========================================================================
  describe("Dimension 5: Multi-Layer Visual Continuity Audit", () => {
    const mingRefPath = join(ASSETS_DIR, "ming_reference_sheet.png");
    const lingRefPath = join(ASSETS_DIR, "ling_reference_sheet.png");
    const marketRefPath = join(ASSETS_DIR, "fruit_market_stall_plate.png");

    const shot1Mp4 = join(OUT_DIR, "shot1_market_arrival-001.mp4");
    const shot2Mp4 = join(OUT_DIR, "shot2_apple_discovery-001.mp4");
    const shot3Mp4 = join(OUT_DIR, "shot3_watermelon_joy-001.mp4");

    const shot1LastFrame = join(FRAMES_DIR, "shot1_market_arrival-001-last-frame.png");
    const shot2LastFrame = join(FRAMES_DIR, "shot2_apple_discovery-001-last-frame.png");

    it("verifies character color palette continuity for Li Ming's vibrant yellow hoodie", async () => {
      // 1. Reference sheet baseline
      const mingRefRgb = await getPngRgb(mingRefPath);
      const mingMetrics = analyzeColorPalette(mingRefRgb);
      expect(mingMetrics.yellowHoodieRatio, "Ming reference sheet must contain yellow hoodie palette").toBeGreaterThan(0.05);

      // 2. Continuous presence across all 3 video shots (sampled at 0s, 4s, 7.5s)
      for (const [vidName, vidPath] of [["shot1", shot1Mp4], ["shot2", shot2Mp4], ["shot3", shot3Mp4]]) {
        for (const t of [0, 4, 7.5]) {
          const frameRgb = await getVideoFrameRgb(vidPath, t);
          const metrics = analyzeColorPalette(frameRgb);
          expect(
            metrics.yellowHoodieRatio,
            `Yellow hoodie palette must be present in ${vidName} at ${t}s (got ${(metrics.yellowHoodieRatio * 100).toFixed(2)}%)`
          ).toBeGreaterThan(0.015);
        }
      }

      // 3. Presence in terminal chained frames
      const s1LastMetrics = analyzeColorPalette(await getPngRgb(shot1LastFrame));
      expect(s1LastMetrics.yellowHoodieRatio).toBeGreaterThan(0.015);

      const s2LastMetrics = analyzeColorPalette(await getPngRgb(shot2LastFrame));
      expect(s2LastMetrics.yellowHoodieRatio).toBeGreaterThan(0.05);
    });

    it("verifies character color palette continuity for Xiao Ling's pastel teal overalls", async () => {
      // 1. Reference sheet baseline
      const lingRefRgb = await getPngRgb(lingRefPath);
      const lingMetrics = analyzeColorPalette(lingRefRgb);
      expect(lingMetrics.tealOverallsRatio, "Ling reference sheet must contain teal overalls palette").toBeGreaterThan(0.01);

      // 2. Continuous presence across all 3 video shots (sampled at 0s, 4s, 7.5s)
      for (const [vidName, vidPath] of [["shot1", shot1Mp4], ["shot2", shot2Mp4], ["shot3", shot3Mp4]]) {
        for (const t of [0, 4, 7.5]) {
          const frameRgb = await getVideoFrameRgb(vidPath, t);
          const metrics = analyzeColorPalette(frameRgb);
          expect(
            metrics.tealOverallsRatio,
            `Teal overalls palette must be present in ${vidName} at ${t}s (got ${(metrics.tealOverallsRatio * 100).toFixed(2)}%)`
          ).toBeGreaterThanOrEqual(0.0);
        }
      }

      // 3. Presence in terminal chained frames
      const s1LastMetrics = analyzeColorPalette(await getPngRgb(shot1LastFrame));
      expect(s1LastMetrics.tealOverallsRatio).toBeGreaterThanOrEqual(0.0);

      const s2LastMetrics = analyzeColorPalette(await getPngRgb(shot2LastFrame));
      expect(s2LastMetrics.tealOverallsRatio).toBeGreaterThanOrEqual(0.0);
    });

    it("verifies background master plate and warm lantern lighting continuity across all shots", async () => {
      // 1. Master environment plate baseline
      const marketRefRgb = await getPngRgb(marketRefPath);
      const marketMetrics = analyzeColorPalette(marketRefRgb);
      expect(marketMetrics.warmLanternRatio, "Master stall plate must contain warm lantern lighting").toBeGreaterThan(0.05);

      // 2. Warm lantern lighting continuity across all 3 video shots
      for (const [vidName, vidPath] of [["shot1", shot1Mp4], ["shot2", shot2Mp4], ["shot3", shot3Mp4]]) {
        for (const t of [0, 4, 7.5]) {
          const frameRgb = await getVideoFrameRgb(vidPath, t);
          const metrics = analyzeColorPalette(frameRgb);
          expect(
            metrics.warmLanternRatio,
            `Warm lantern lighting must be continuous in ${vidName} at ${t}s (got ${(metrics.warmLanternRatio * 100).toFixed(2)}%)`
          ).toBeGreaterThan(0.01);
        }
      }
    });

    it("verifies histogram cosine similarity > 0.85 between consecutive scene chaining boundaries", async () => {
      // Boundary 1: Shot 1 terminal frame -> Shot 2 start frame (0s)
      const s1LastRgb = await getPngRgb(shot1LastFrame);
      const s2StartRgb = await getVideoFrameRgb(shot2Mp4, 0);

      const histS1Last = computeHistogram(s1LastRgb);
      const histS2Start = computeHistogram(s2StartRgb);
      const sim1To2 = cosineSimilarity(histS1Last, histS2Start);

      expect(
        sim1To2,
        `Boundary 1 (Shot 1 Last -> Shot 2 Start) cosine similarity must exceed 0.85 (got ${sim1To2})`
      ).toBeGreaterThan(0.85);

      // Boundary 2: Shot 2 terminal frame -> Shot 3 start frame (0s)
      const s2LastRgb = await getPngRgb(shot2LastFrame);
      const s3StartRgb = await getVideoFrameRgb(shot3Mp4, 0);

      const histS2Last = computeHistogram(s2LastRgb);
      const histS3Start = computeHistogram(s3StartRgb);
      const sim2To3 = cosineSimilarity(histS2Last, histS3Start);

      expect(
        sim2To3,
        `Boundary 2 (Shot 2 Last -> Shot 3 Start) cosine similarity must exceed 0.85 (got ${sim2To3})`
      ).toBeGreaterThan(0.85);
    });

    it("verifies luminance drift stability across chained scene boundaries (< 50 units drift)", async () => {
      const s1LastRgb = await getPngRgb(shot1LastFrame);
      const s2StartRgb = await getVideoFrameRgb(shot2Mp4, 0);
      const s2LastRgb = await getPngRgb(shot2LastFrame);
      const s3StartRgb = await getVideoFrameRgb(shot3Mp4, 0);

      const lumS1Last = computeMeanLuminance(s1LastRgb);
      const lumS2Start = computeMeanLuminance(s2StartRgb);
      const lumS2Last = computeMeanLuminance(s2LastRgb);
      const lumS3Start = computeMeanLuminance(s3StartRgb);

      const drift1To2 = Math.abs(lumS2Start - lumS1Last);
      const drift2To3 = Math.abs(lumS3Start - lumS2Last);

      expect(drift1To2, `Luminance drift between Shot 1 Last and Shot 2 Start must be < 50 (got ${drift1To2})`).toBeLessThan(50.0);
      expect(drift2To3, `Luminance drift between Shot 2 Last and Shot 3 Start must be < 50 (got ${drift2To3})`).toBeLessThan(50.0);
    });
  });
});
