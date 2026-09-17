import { execFile } from "node:child_process";
import { mkdtemp, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import {
  extractFrameWithFfmpeg,
  extractLastFrame,
  extractVideoFrame,
  hasFfmpeg,
  isVideoFile,
  parseOutputReference,
  _resetFfmpegCacheForTesting
} from "../src/jobs/frame-extractor.js";

const execFileAsync = promisify(execFile);

describe("isVideoFile", () => {
  it("recognizes standard video file extensions", () => {
    expect(isVideoFile("video.mp4")).toBe(true);
    expect(isVideoFile("/path/to/movie.webm")).toBe(true);
    expect(isVideoFile("CLIP.MOV")).toBe(true);
    expect(isVideoFile("sequence.mkv")).toBe(true);
    expect(isVideoFile("shot.m4v")).toBe(true);
    expect(isVideoFile("capture.avi")).toBe(true);
  });

  it("rejects non-video extensions and invalid paths", () => {
    expect(isVideoFile("image.png")).toBe(false);
    expect(isVideoFile("photo.jpg")).toBe(false);
    expect(isVideoFile("photo.jpeg")).toBe(false);
    expect(isVideoFile("graphic.webp")).toBe(false);
    expect(isVideoFile("checkpoint.json")).toBe(false);
    expect(isVideoFile("")).toBe(false);
    expect(isVideoFile(undefined)).toBe(false);
  });
});

describe("parseOutputReference", () => {
  it("parses output reference strings correctly", () => {
    expect(parseOutputReference("$output:shot_1")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: undefined
    });

    expect(parseOutputReference("$output:shot_1[2]")).toEqual({
      jobId: "shot_1",
      index: 2,
      position: undefined
    });

    expect(parseOutputReference("$output:shot_1#last")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: "last"
    });

    expect(parseOutputReference("$output:shot_1[1]#first")).toEqual({
      jobId: "shot_1",
      index: 1,
      position: "first"
    });

    expect(parseOutputReference("$output:shot_1#2.5s")).toEqual({
      jobId: "shot_1",
      index: 0,
      position: 2.5
    });

    expect(parseOutputReference("$ref:characters.hero")).toBeNull();
    expect(parseOutputReference("not_an_output_ref")).toBeNull();
  });
});

describe("hasFfmpeg", () => {
  it("detects system ffmpeg", async () => {
    _resetFfmpegCacheForTesting();
    const available = await hasFfmpeg();
    expect(typeof available).toBe("boolean");
    expect(available).toBe(true);
  });
});

describe("extractFrameWithFfmpeg", () => {
  it("invokes executor with correct arguments for last, first, and timestamp", async () => {
    const mockExecutor = vi.fn(async (args: string[]) => {
      void args;
      return { stdout: "", stderr: "" };
    });

    await extractFrameWithFfmpeg("input.mp4", "last.png", "last", mockExecutor);
    expect(mockExecutor).toHaveBeenCalledWith([
      "-y",
      "-sseof",
      "-1",
      "-i",
      "input.mp4",
      "-update",
      "1",
      "-q:v",
      "1",
      "last.png"
    ]);

    await extractFrameWithFfmpeg("input.mp4", "first.png", "first", mockExecutor);
    expect(mockExecutor).toHaveBeenCalledWith([
      "-y",
      "-ss",
      "0",
      "-i",
      "input.mp4",
      "-frames:v",
      "1",
      "-q:v",
      "1",
      "first.png"
    ]);

    await extractFrameWithFfmpeg("input.mp4", "ts.png", 3.2, mockExecutor);
    expect(mockExecutor).toHaveBeenCalledWith([
      "-y",
      "-ss",
      "3.2",
      "-i",
      "input.mp4",
      "-frames:v",
      "1",
      "-q:v",
      "1",
      "ts.png"
    ]);
  });

  it("throws formatted error when ffmpeg execution fails", async () => {
    const failingExecutor = vi.fn(async (args: string[]) => {
      void args;
      throw new Error("FFmpeg error: Invalid data found when processing input");
    });

    await expect(
      extractFrameWithFfmpeg("corrupt.mp4", "out.png", "last", failingExecutor)
    ).rejects.toThrow("FFmpeg frame extraction failed for 'corrupt.mp4': FFmpeg error: Invalid data");
  });
});

describe("extractVideoFrame and caching", () => {
  let tempDir: string;
  let sampleVideoPath: string;

  beforeAll(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "gflow-frame-test-"));
    sampleVideoPath = join(tempDir, "synth_sample.mp4");

    // Generate a quick 1-second synthetic video using native ffmpeg
    await execFileAsync("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "testsrc=duration=1:size=160x120:rate=10",
      sampleVideoPath
    ]);
  });

  afterAll(async () => {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  });

  it("extracts the last frame to <outDir>/frames/ and caches result", async () => {
    const result1 = await extractVideoFrame(sampleVideoPath, {
      outDir: tempDir,
      position: "last"
    });

    expect(result1.cached).toBe(false);
    expect(result1.path).toContain("frames/synth_sample-last-frame.png");

    const fileStat = await stat(result1.path);
    expect(fileStat.size).toBeGreaterThan(0);

    // Second call without overwrite should return cached: true
    const result2 = await extractVideoFrame(sampleVideoPath, {
      outDir: tempDir,
      position: "last"
    });

    expect(result2.cached).toBe(true);
    expect(result2.path).toBe(result1.path);

    // Third call with overwrite should re-extract
    const result3 = await extractVideoFrame(sampleVideoPath, {
      outDir: tempDir,
      position: "last",
      overwrite: true
    });

    expect(result3.cached).toBe(false);
    expect(result3.path).toBe(result1.path);
  });

  it("extractLastFrame convenience helper returns the string path", async () => {
    const framePath = await extractLastFrame(sampleVideoPath, tempDir);
    expect(typeof framePath).toBe("string");
    expect(framePath).toContain("synth_sample-last-frame.png");
    const s = await stat(framePath);
    expect(s.size).toBeGreaterThan(0);
  });

  it("throws descriptive error when input video does not exist", async () => {
    await expect(
      extractVideoFrame(join(tempDir, "missing.mp4"), { outDir: tempDir })
    ).rejects.toThrow("Cannot extract frame: input video");
  });

  it("throws descriptive error when input video is 0 bytes", async () => {
    const zeroByteVideo = join(tempDir, "zero.mp4");
    await writeFile(zeroByteVideo, Buffer.alloc(0));

    await expect(
      extractVideoFrame(zeroByteVideo, { outDir: tempDir })
    ).rejects.toThrow("Video file at");
  });
});
