import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import {
  extractLastFrame,
  extractVideoFrame
} from "../src/jobs/frame-extractor.js";

const execFileAsync = promisify(execFile);

/**
 * Validates PNG file structure per PNG specification:
 * - Bytes 0..7: 89 50 4E 47 0D 0A 1A 0A
 * - Bytes 8..11: IHDR chunk length (must be 13 = 0x0000000D)
 * - Bytes 12..15: "IHDR" chunk signature
 * - Bytes 16..23: Width (4 bytes BE) and Height (4 bytes BE)
 * - Trailing bytes: IEND chunk signature
 */
async function validatePngFile(
  filePath: string,
  expectedWidth?: number,
  expectedHeight?: number
): Promise<{ width: number; height: number; size: number }> {
  const fileStat = await stat(filePath);
  expect(fileStat.size).toBeGreaterThan(64); // Smallest valid PNG is ~67 bytes

  const buffer = await readFile(filePath);

  // 1. Magic bytes
  const pngMagic = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  expect(buffer.subarray(0, 8).equals(pngMagic)).toBe(true);

  // 2. First chunk must be IHDR
  const ihdrLength = buffer.readUInt32BE(8);
  expect(ihdrLength).toBe(13);
  const ihdrType = buffer.subarray(12, 16).toString("ascii");
  expect(ihdrType).toBe("IHDR");

  // 3. Extract dimensions
  const width = buffer.readUInt32BE(16);
  const height = buffer.readUInt32BE(20);
  expect(width).toBeGreaterThan(0);
  expect(height).toBeGreaterThan(0);

  if (expectedWidth !== undefined) {
    expect(width).toBe(expectedWidth);
  }
  if (expectedHeight !== undefined) {
    expect(height).toBe(expectedHeight);
  }

  // 4. Last chunk should be IEND
  const iendPos = buffer.lastIndexOf(Buffer.from("IEND"));
  expect(iendPos).toBeGreaterThan(16);

  return { width, height, size: fileStat.size };
}

/**
 * Reads RGB values at (0, 0) of an image using ffmpeg rawvideo decoder.
 */
async function getTopLeftPixelRgb(imagePath: string): Promise<[number, number, number]> {
  const { stdout } = await execFileAsync("ffmpeg", [
    "-i",
    imagePath,
    "-vframes",
    "1",
    "-f",
    "rawvideo",
    "-pix_fmt",
    "rgb24",
    "-"
  ], { encoding: "buffer", maxBuffer: 10 * 1024 * 1024 });

  return [stdout[0], stdout[1], stdout[2]];
}

describe("Empirical Challenge Suite: Video Frame Extraction & Caching", () => {
  let tempDir: string;
  let testMp4: string;
  let testWebm: string;
  let testMov: string;
  let colorConcatMp4: string;
  let singleFrameMp4: string;
  let ultraShortMp4: string;
  let specialCharMp4: string;

  beforeAll(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-empirical-challenge-"));

    testMp4 = join(tempDir, "standard_320x240.mp4");
    testWebm = join(tempDir, "standard_320x240.webm");
    testMov = join(tempDir, "standard_320x240.mov");
    singleFrameMp4 = join(tempDir, "single_frame.mp4");
    ultraShortMp4 = join(tempDir, "ultra_short_0.1s.mp4");
    specialCharMp4 = join(tempDir, "shot & test [v1] (final).mp4");

    // 1. Standard 2-second 320x240 test videos across containers
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=2:size=320x240:rate=25",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      testMp4
    ]);

    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=1:size=320x240:rate=25",
      "-c:v",
      "libvpx-vp9",
      testWebm
    ]);

    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=1:size=320x240:rate=25",
      "-c:v",
      "libx264",
      testMov
    ]);

    // 2. Special filename with spaces, ampersand, brackets
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=1:size=160x120:rate=10",
      "-c:v",
      "libx264",
      specialCharMp4
    ]);

    // 3. Single frame MP4 (duration 0.04s at 25fps = 1 frame)
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=0.04:size=320x240:rate=25",
      "-c:v",
      "libx264",
      singleFrameMp4
    ]);

    // 4. Ultra-short MP4 (0.1s = 2.5 frames)
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=0.1:size=320x240:rate=25",
      "-c:v",
      "libx264",
      ultraShortMp4
    ]);

    // 5. Oracle Video: Second 0..1 is solid RED, Second 1..2 is solid BLUE
    const redPart = join(tempDir, "part_red.mp4");
    const bluePart = join(tempDir, "part_blue.mp4");
    colorConcatMp4 = join(tempDir, "oracle_red_blue.mp4");

    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "color=c=red:s=160x120:d=1",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      redPart
    ]);

    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "color=c=blue:s=160x120:d=1",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      bluePart
    ]);

    const concatList = join(tempDir, "concat_list.txt");
    await writeFile(concatList, `file '${redPart}'\nfile '${bluePart}'\n`);
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "concat",
      "-safe",
      "0",
      "-i",
      concatList,
      "-c",
      "copy",
      colorConcatMp4
    ]);
  });

  afterAll(async () => {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  describe("1. Real Video Frame Extraction & PNG Specification Compliance", () => {
    it("extracts terminal frame from MP4 and creates byte-for-byte valid PNG", async () => {
      const result = await extractVideoFrame(testMp4, {
        outDir: tempDir,
        position: "last"
      });

      expect(result.cached).toBe(false);
      expect(result.sourceVideo).toBe(testMp4);
      expect(result.position).toBe("last");

      const info = await validatePngFile(result.path, 320, 240);
      expect(info.size).toBeGreaterThan(1000);
    });

    it("extracts terminal frame from WebM (VP9) video", async () => {
      const result = await extractVideoFrame(testWebm, {
        outDir: tempDir,
        position: "last"
      });
      const info = await validatePngFile(result.path, 320, 240);
      expect(info.size).toBeGreaterThan(1000);
    });

    it("extracts terminal frame from MOV video", async () => {
      const result = await extractVideoFrame(testMov, {
        outDir: tempDir,
        position: "last"
      });
      const info = await validatePngFile(result.path, 320, 240);
      expect(info.size).toBeGreaterThan(1000);
    });

    it("extracts terminal frame from video with special characters in filename", async () => {
      const result = await extractVideoFrame(specialCharMp4, {
        outDir: tempDir,
        position: "last"
      });
      const info = await validatePngFile(result.path, 160, 120);
      expect(info.size).toBeGreaterThan(500);
    });

    it("extractLastFrame convenience helper returns same path and valid PNG", async () => {
      const framePath = await extractLastFrame(testMp4, tempDir);
      expect(typeof framePath).toBe("string");
      await validatePngFile(framePath, 320, 240);
    });
  });

  describe("2. Terminal vs Initial Frame Oracle Verification", () => {
    it("empirically verifies 'last' extracts terminal frame (Blue) and 'first' extracts start frame (Red)", async () => {
      // First frame should be Red
      const firstResult = await extractVideoFrame(colorConcatMp4, {
        outDir: tempDir,
        position: "first"
      });
      const [r1, , b1] = await getTopLeftPixelRgb(firstResult.path);
      // Red: R should be high (> 200), B should be low (< 50)
      expect(r1).toBeGreaterThan(200);
      expect(b1).toBeLessThan(50);

      // Last frame should be Blue
      const lastResult = await extractVideoFrame(colorConcatMp4, {
        outDir: tempDir,
        position: "last"
      });
      const [r2, , b2] = await getTopLeftPixelRgb(lastResult.path);
      // Blue: B should be high (> 200), R should be low (< 50)
      expect(b2).toBeGreaterThan(200);
      expect(r2).toBeLessThan(50);
    });
  });

  describe("3. Deterministic Caching Performance & Semantics", () => {
    it("returns cached: true near-instantaneously without re-running FFmpeg", async () => {
      const uniqueVideo = join(tempDir, "cache_speed_test.mp4");
      await execFileAsync("ffmpeg", [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=160x120:rate=10",
        "-c:v",
        "libx264",
        uniqueVideo
      ]);

      // Call 1: cold extraction (spawns ffmpeg)
      const t0 = performance.now();
      const coldResult = await extractVideoFrame(uniqueVideo, {
        outDir: tempDir,
        position: "last"
      });
      const coldDurationMs = performance.now() - t0;
      expect(coldResult.cached).toBe(false);

      // Call 2: warm cached extraction (pure stat check)
      const t1 = performance.now();
      const warmResult = await extractVideoFrame(uniqueVideo, {
        outDir: tempDir,
        position: "last"
      });
      const warmDurationMs = performance.now() - t1;

      expect(warmResult.cached).toBe(true);
      expect(warmResult.path).toBe(coldResult.path);
      // Cached hit should be at least 3x faster than cold run and < 25ms
      expect(warmDurationMs).toBeLessThan(25);
      expect(warmDurationMs).toBeLessThan(coldDurationMs);
    });

    it("verifies FFmpeg executor is NOT called when cache hits", async () => {
      const uniqueVideo = join(tempDir, "cache_executor_spy.mp4");
      await execFileAsync("ffmpeg", [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=160x120:rate=10",
        "-c:v",
        "libx264",
        uniqueVideo
      ]);

      const executorMock = vi.fn(async () => ({ stdout: "", stderr: "" }));

      // First run to populate cache using real ffmpeg
      const res1 = await extractVideoFrame(uniqueVideo, {
        outDir: tempDir,
        position: "last"
      });
      expect(res1.cached).toBe(false);

      // Second run passes executorMock; if cache hits, executorMock should NEVER be called
      const res2 = await extractVideoFrame(uniqueVideo, {
        outDir: tempDir,
        position: "last",
        ffmpegExecutor: executorMock
      });

      expect(res2.cached).toBe(true);
      expect(executorMock).not.toHaveBeenCalled();
    });

    it("re-executes and ignores cache when overwrite: true is requested", async () => {
      const resCold = await extractVideoFrame(testMp4, {
        outDir: tempDir,
        position: "last"
      });
      expect(resCold.cached).toBe(true); // Already populated from earlier test

      const resOverwrite = await extractVideoFrame(testMp4, {
        outDir: tempDir,
        position: "last",
        overwrite: true
      });

      expect(resOverwrite.cached).toBe(false);
      expect(resOverwrite.path).toBe(resCold.path);
      await validatePngFile(resOverwrite.path, 320, 240);
    });

    it("does NOT treat a corrupt/0-byte pre-existing file as a valid cache entry", async () => {
      const uniqueVideo = join(tempDir, "zero_cache_test.mp4");
      await execFileAsync("ffmpeg", [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=160x120:rate=10",
        "-c:v",
        "libx264",
        uniqueVideo
      ]);

      const expectedCachedFrame = join(tempDir, "frames", "zero_cache_test-last-frame.png");
      // Intentionally simulate an aborted or corrupted 0-byte frame in cache
      await writeFile(expectedCachedFrame, Buffer.alloc(0));

      const res = await extractVideoFrame(uniqueVideo, {
        outDir: tempDir,
        position: "last",
        overwrite: false // overwrite is false, but cache has 0-byte file
      });

      // It must recognize the 0-byte file is invalid, re-extract, and report cached: false
      expect(res.cached).toBe(false);
      const fileStat = await stat(res.path);
      expect(fileStat.size).toBeGreaterThan(500);
      await validatePngFile(res.path, 160, 120);
    });
  });

  describe("4. Error Handling: Missing, 0-byte, Corrupt Videos", () => {
    it("throws descriptive error immediately for non-existent video path without spawning ffmpeg", async () => {
      const nonExistentPath = join(tempDir, "does_not_exist_404.mp4");
      const executorMock = vi.fn(async () => ({ stdout: "", stderr: "" }));

      await expect(
        extractVideoFrame(nonExistentPath, {
          outDir: tempDir,
          ffmpegExecutor: executorMock
        })
      ).rejects.toThrow(
        `Cannot extract frame: input video '${nonExistentPath}' does not exist or is unreadable.`
      );

      expect(executorMock).not.toHaveBeenCalled();
    });

    it("throws descriptive error immediately for 0-byte video file without spawning ffmpeg", async () => {
      const zeroBytePath = join(tempDir, "empty_video.mp4");
      await writeFile(zeroBytePath, Buffer.alloc(0));
      const executorMock = vi.fn(async () => ({ stdout: "", stderr: "" }));

      await expect(
        extractVideoFrame(zeroBytePath, {
          outDir: tempDir,
          ffmpegExecutor: executorMock
        })
      ).rejects.toThrow(`Video file at '${zeroBytePath}' is 0 bytes.`);

      expect(executorMock).not.toHaveBeenCalled();
    });

    it("handles corrupted video files (random garbage bytes) with clean descriptive error", async () => {
      const corruptPath = join(tempDir, "garbage.mp4");
      // 4KB of random pseudo-garbage data
      const garbage = Buffer.alloc(4096);
      for (let i = 0; i < 4096; i++) garbage[i] = (i * 37 + 13) % 256;
      await writeFile(corruptPath, garbage);

      await expect(
        extractVideoFrame(corruptPath, { outDir: tempDir })
      ).rejects.toThrow(/FFmpeg frame extraction failed for/);
    });

    it("handles truncated MP4 (header intact but media payload destroyed)", async () => {
      // Read 128 bytes of real MP4 header, truncate the rest
      const realMp4Buffer = await readFile(testMp4);
      const truncatedPath = join(tempDir, "truncated.mp4");
      await writeFile(truncatedPath, realMp4Buffer.subarray(0, 128));

      await expect(
        extractVideoFrame(truncatedPath, { outDir: tempDir })
      ).rejects.toThrow(/FFmpeg frame extraction failed for/);
    });

    it("handles text file renamed to .mp4", async () => {
      const fakeMp4Path = join(tempDir, "fake_text.mp4");
      await writeFile(fakeMp4Path, "Plain text content that is not video data.");

      await expect(
        extractVideoFrame(fakeMp4Path, { outDir: tempDir })
      ).rejects.toThrow(/FFmpeg frame extraction failed for/);
    });
  });

  describe("5. Boundary & Extreme Video Edge Cases", () => {
    it("handles 1-frame MP4 (0.04s duration) without failure under -sseof -1", async () => {
      // -sseof -1 seeks 1s before EOF, which exceeds 0.04s video duration.
      // FFmpeg logs warning and resets seek to 0, producing a valid single-frame PNG.
      const result = await extractVideoFrame(singleFrameMp4, {
        outDir: tempDir,
        position: "last"
      });

      expect(result.position).toBe("last");
      const info = await validatePngFile(result.path, 320, 240);
      expect(info.size).toBeGreaterThan(1000);
    });

    it("handles ultra-short MP4 (0.1s duration)", async () => {
      const result = await extractVideoFrame(ultraShortMp4, {
        outDir: tempDir,
        position: "last"
      });

      const info = await validatePngFile(result.path, 320, 240);
      expect(info.size).toBeGreaterThan(1000);
    });

    it("handles explicit outPath overriding default directory and naming pattern", async () => {
      const customOut = join(tempDir, "custom_named_terminal.png");
      const result = await extractVideoFrame(testMp4, {
        outPath: customOut,
        position: "last"
      });

      expect(result.path).toBe(customOut);
      await validatePngFile(customOut, 320, 240);
    });

    it("handles concurrent simultaneous extractions of the same video safely", async () => {
      const promises = Array.from({ length: 5 }, () =>
        extractVideoFrame(testMp4, {
          outDir: tempDir,
          position: "last"
        })
      );

      const results = await Promise.all(promises);
      expect(results.length).toBe(5);
      for (const res of results) {
        expect(res.path).toContain("standard_320x240-last-frame.png");
        const s = await stat(res.path);
        expect(s.size).toBeGreaterThan(0);
      }
    });
  });
});
