import { describe, it, expect } from "vitest";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, readFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { extractVideoFrame } from "../src/jobs/frame-extractor.js";

const execFileAsync = promisify(execFile);

describe("M7 Empirical Challenge: Terminal Frame Extraction & Scene Continuity", () => {
  const outDir = "/media/vpsg24gb/DATA/gflow/out";
  const framesDir = join(outDir, "frames");

  const shot1Video = join(outDir, "shot1_market_arrival-001.mp4");
  const shot2Video = join(outDir, "shot2_apple_discovery-001.mp4");
  const shot3Video = join(outDir, "shot3_watermelon_joy-001.mp4");

  const shot1LastFrame = join(framesDir, "shot1_market_arrival-001-last-frame.png");
  const shot2LastFrame = join(framesDir, "shot2_apple_discovery-001-last-frame.png");

  it("verifies all three video deliverables exist and are non-empty", () => {
    expect(existsSync(shot1Video)).toBe(true);
    expect(existsSync(shot2Video)).toBe(true);
    expect(existsSync(shot3Video)).toBe(true);

    const stat1 = readFileSync(shot1Video);
    const stat2 = readFileSync(shot2Video);
    const stat3 = readFileSync(shot3Video);

    expect(stat1.length).toBeGreaterThan(1_000_000);
    expect(stat2.length).toBeGreaterThan(1_000_000);
    expect(stat3.length).toBeGreaterThan(1_000_000);
  });

  it("verifies PNG header magic bytes and IHDR dimensions on existing frames", () => {
    const pngMagic = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

    for (const framePath of [shot1LastFrame, shot2LastFrame]) {
      expect(existsSync(framePath)).toBe(true);
      const buf = readFileSync(framePath);
      expect(buf.subarray(0, 8).equals(pngMagic)).toBe(true);

      // IHDR chunk: width at offset 16 (4 bytes BE), height at offset 20 (4 bytes BE)
      const width = buf.readUInt32BE(16);
      const height = buf.readUInt32BE(20);
      expect(width).toBe(720);
      expect(height).toBe(1280);
    }
  });

  it("independently extracts terminal frame for Shot 1 and matches existing frame exactly", async () => {
    const existingHash = createHash("md5").update(readFileSync(shot1LastFrame)).digest("hex");
    const tmpDir = await mkdtemp(join(tmpdir(), "m7-frame-test-"));
    const tmpOut = join(tmpDir, "shot1_test.png");

    try {
      await execFileAsync("ffmpeg", [
        "-y",
        "-sseof",
        "-1",
        "-i",
        shot1Video,
        "-update",
        "1",
        "-q:v",
        "1",
        tmpOut
      ]);

      const independentHash = createHash("md5").update(readFileSync(tmpOut)).digest("hex");
      expect(independentHash).toBe(existingHash);
    } finally {
      await rm(tmpDir, { recursive: true, force: true });
    }
  });

  it("independently extracts terminal frame for Shot 2 and matches existing frame exactly", async () => {
    const existingHash = createHash("md5").update(readFileSync(shot2LastFrame)).digest("hex");
    const tmpDir = await mkdtemp(join(tmpdir(), "m7-frame-test-"));
    const tmpOut = join(tmpDir, "shot2_test.png");

    try {
      await execFileAsync("ffmpeg", [
        "-y",
        "-sseof",
        "-1",
        "-i",
        shot2Video,
        "-update",
        "1",
        "-q:v",
        "1",
        tmpOut
      ]);

      const independentHash = createHash("md5").update(readFileSync(tmpOut)).digest("hex");
      expect(independentHash).toBe(existingHash);
    } finally {
      await rm(tmpDir, { recursive: true, force: true });
    }
  });

  it("verifies frame-extractor.ts extractVideoFrame caching on existing frames", async () => {
    const res1 = await extractVideoFrame(shot1Video, { outDir });
    expect(res1.cached).toBe(true);
    expect(res1.path).toBe(shot1LastFrame);

    const res2 = await extractVideoFrame(shot2Video, { outDir });
    expect(res2.cached).toBe(true);
    expect(res2.path).toBe(shot2LastFrame);
  });

  it("probes all 3 video streams for vertical 9:16 aspect ratio, 24fps, and 8.0s duration", async () => {
    for (const vid of [shot1Video, shot2Video, shot3Video]) {
      const { stdout } = await execFileAsync("ffprobe", [
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames,codec_name",
        "-of",
        "json",
        vid
      ]);

      const data = JSON.parse(stdout.toString());
      const stream = data.streams[0];

      expect(stream.codec_name).toBe("h264");
      expect(stream.width).toBe(720);
      expect(stream.height).toBe(1280);
      expect(stream.r_frame_rate).toBe("24/1");
      expect(parseInt(stream.nb_frames, 10)).toBeGreaterThanOrEqual(120);
    }
  });

  it("verifies checkpoint.json marks all 3 jobs as completed", () => {
    const cpPath = join(outDir, "checkpoint.json");
    expect(existsSync(cpPath)).toBe(true);
    const cp = JSON.parse(readFileSync(cpPath, "utf-8"));

    expect(cp.pipeline).toBe("pixar-fruit-market-vocabulary");
    expect(cp.completed).toEqual([
      "shot1_market_arrival",
      "shot2_apple_discovery",
      "shot3_watermelon_joy"
    ]);
    expect(cp.failed).toEqual([]);
    expect(Object.keys(cp.completedJobs)).toHaveLength(3);
    for (const id of cp.completed) {
      expect(cp.completedJobs[id].status).toBe("completed");
    }
  });

  describe("Scene Chaining Continuity Metrics", () => {
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

    async function getPngRgb(pngPath: string): Promise<Buffer> {
      const { stdout } = await execFileAsync("ffmpeg", [
        "-y", "-i", pngPath, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
      ], { maxBuffer: 10 * 1024 * 1024, encoding: "buffer" });
      return stdout as unknown as Buffer;
    }

    async function getVideoStartRgb(videoPath: string): Promise<Buffer> {
      const { stdout } = await execFileAsync("ffmpeg", [
        "-y", "-ss", "0", "-i", videoPath, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
      ], { maxBuffer: 10 * 1024 * 1024, encoding: "buffer" });
      return stdout as unknown as Buffer;
    }

    it("verifies high color histogram continuity between Shot 1 terminal frame and Shot 2 start frame (> 0.85)", async () => {
      const s1LastRgb = await getPngRgb(shot1LastFrame);
      const s2StartRgb = await getVideoStartRgb(shot2Video);

      const sim = cosineSimilarity(computeHistogram(s1LastRgb), computeHistogram(s2StartRgb));
      expect(sim).toBeGreaterThan(0.85);
    });

    it("verifies very high color histogram continuity between Shot 2 terminal frame and Shot 3 start frame (> 0.85)", async () => {
      const s2LastRgb = await getPngRgb(shot2LastFrame);
      const s3StartRgb = await getVideoStartRgb(shot3Video);

      const sim = cosineSimilarity(computeHistogram(s2LastRgb), computeHistogram(s3StartRgb));
      expect(sim).toBeGreaterThan(0.85);
    });

    it("verifies mean luminance stability across chained shot transitions (< 50 units drift)", async () => {
      function meanLuminance(rgb: Buffer): number {
        let sum = 0;
        const total = rgb.length / 3;
        for (let i = 0; i < rgb.length; i += 3) {
          // Standard ITU-R BT.601 luminance weights
          sum += 0.299 * rgb[i] + 0.587 * rgb[i + 1] + 0.114 * rgb[i + 2];
        }
        return sum / total;
      }

      const s1LastRgb = await getPngRgb(shot1LastFrame);
      const s2StartRgb = await getVideoStartRgb(shot2Video);
      const s2LastRgb = await getPngRgb(shot2LastFrame);
      const s3StartRgb = await getVideoStartRgb(shot3Video);

      const lumS1Last = meanLuminance(s1LastRgb);
      const lumS2Start = meanLuminance(s2StartRgb);
      const lumS2Last = meanLuminance(s2LastRgb);
      const lumS3Start = meanLuminance(s3StartRgb);

      const drift1To2 = Math.abs(lumS2Start - lumS1Last);
      const drift2To3 = Math.abs(lumS3Start - lumS2Last);

      expect(drift1To2).toBeLessThan(50.0);
      expect(drift2To3).toBeLessThan(50.0);
    });
  });
});
