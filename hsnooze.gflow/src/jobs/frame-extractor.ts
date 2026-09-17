import { execFile } from "node:child_process";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { basename, extname, join } from "node:path";
import { promisify } from "node:util";
import type { Page } from "playwright";

const execFileAsync = promisify(execFile);

export const VIDEO_EXTENSIONS = new Set([".mp4", ".webm", ".mov", ".mkv", ".m4v", ".avi"]);

/**
 * Checks whether a given file path points to a recognized video file.
 */
export function isVideoFile(filePath?: string): boolean {
  if (!filePath) return false;
  const ext = extname(filePath).toLowerCase();
  return VIDEO_EXTENSIONS.has(ext);
}

/**
 * Parses an $output:<job_id>[<index>]#<tag> reference string.
 */
export function parseOutputReference(ref: string): {
  jobId: string;
  index: number;
  position?: "first" | "last" | number;
} | null {
  const match = ref.match(/^\$output:([a-zA-Z0-9._-]+)(?:\[(\d+)\])?(?:#(first|last|(\d+(?:\.\d+)?s?)))?$/);
  if (!match) return null;
  const jobId = match[1];
  const index = match[2] ? parseInt(match[2], 10) : 0;
  let position: "first" | "last" | number | undefined;
  if (match[3]) {
    if (match[3] === "first" || match[3] === "last") {
      position = match[3];
    } else {
      const num = parseFloat(match[3].replace(/s$/, ""));
      if (!isNaN(num)) position = num;
    }
  }
  return { jobId, index, position };
}

export interface FrameExtractionOptions {
  /**
   * Target frame position:
   * - "last" (default): extract the last frame of the video
   * - "first": extract the first frame (00:00:00)
   * - number: timestamp in seconds (e.g. 2.5)
   */
  position?: "last" | "first" | number;

  /**
   * Explicit destination path. If omitted, defaults to:
   * `<outDir>/frames/<videoBasename>-<position>-frame.<format>`
   */
  outPath?: string;

  /**
   * Output directory for storing cached frames. Defaults to `./gflow-output`.
   */
  outDir?: string;

  /**
   * Overwrite existing cached frame if it already exists. Defaults to false.
   */
  overwrite?: boolean;

  /**
   * Output image format: "png" (default) or "jpg".
   */
  format?: "png" | "jpg";

  /**
   * Optional Playwright Page for fallback canvas extraction if ffmpeg is missing.
   */
  page?: Page;

  /**
   * Optional custom executor for unit test dependency injection.
   */
  ffmpegExecutor?: (args: string[]) => Promise<{ stdout: string; stderr: string }>;
}

export interface ExtractedFrameResult {
  path: string;
  cached: boolean;
  sourceVideo: string;
  position: "last" | "first" | number;
}

let cachedFfmpegAvailable: boolean | undefined;

/**
 * Detects whether the ffmpeg binary is executable on system PATH.
 */
export async function hasFfmpeg(): Promise<boolean> {
  if (cachedFfmpegAvailable !== undefined) return cachedFfmpegAvailable;
  try {
    await execFileAsync("ffmpeg", ["-version"]);
    cachedFfmpegAvailable = true;
  } catch {
    cachedFfmpegAvailable = false;
  }
  return cachedFfmpegAvailable;
}

export function _resetFfmpegCacheForTesting(state?: boolean): void {
  cachedFfmpegAvailable = state;
}

/**
 * Extracts a frame from a video using system ffmpeg.
 */
export async function extractFrameWithFfmpeg(
  videoPath: string,
  outPath: string,
  position: "last" | "first" | number = "last",
  executor?: (args: string[]) => Promise<{ stdout: string; stderr: string }>
): Promise<void> {
  const runFfmpeg = executor ?? (async (args: string[]) => execFileAsync("ffmpeg", args));

  let args: string[];
  if (position === "last") {
    args = ["-y", "-sseof", "-1", "-i", videoPath, "-update", "1", "-q:v", "1", outPath];
  } else if (position === "first") {
    args = ["-y", "-ss", "0", "-i", videoPath, "-frames:v", "1", "-q:v", "1", outPath];
  } else {
    args = ["-y", "-ss", `${position}`, "-i", videoPath, "-frames:v", "1", "-q:v", "1", outPath];
  }

  try {
    await runFfmpeg(args);
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    throw new Error(`FFmpeg frame extraction failed for '${videoPath}': ${errorMsg}`);
  }
}

/**
 * Extracts a frame from a video using Playwright HTML5 Canvas (fallback).
 */
export async function extractFrameWithCanvas(
  videoPath: string,
  outPath: string,
  position: "last" | "first" | number = "last",
  page?: Page
): Promise<void> {
  if (!page) {
    throw new Error("Playwright page instance is required for canvas frame extraction.");
  }

  const videoBuffer = await readFile(videoPath);
  const base64 = videoBuffer.toString("base64");

  const dataUrl = await page.evaluate(
    async ({ b64, pos }) => {
      return new Promise<string>((resolve, reject) => {
        const video = document.createElement("video");
        video.src = "data:video/mp4;base64," + b64;
        video.muted = true;
        video.onloadedmetadata = () => {
          if (pos === "first") {
            video.currentTime = 0;
          } else if (pos === "last") {
            video.currentTime = Math.max(0, video.duration - 0.05);
          } else {
            video.currentTime = Math.min(Math.max(0, pos), video.duration);
          }
        };
        video.onseeked = () => {
          try {
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            if (!ctx) return reject(new Error("Failed to acquire 2D canvas context"));
            ctx.drawImage(video, 0, 0);
            resolve(canvas.toDataURL("image/png"));
          } catch (e) {
            reject(e);
          }
        };
        video.onerror = () => reject(new Error("HTML5 video element failed to decode video stream"));
      });
    },
    { b64: base64, pos: position }
  );

  const rawBase64 = dataUrl.replace(/^data:image\/\w+;base64,/, "");
  await writeFile(outPath, Buffer.from(rawBase64, "base64"));
}

/**
 * High-level frame extractor with deterministic caching under `<outDir>/frames/`.
 */
export async function extractVideoFrame(
  videoPath: string,
  options: FrameExtractionOptions = {}
): Promise<ExtractedFrameResult> {
  // Input validation
  try {
    const stats = await stat(videoPath);
    if (stats.size === 0) {
      throw new Error(`Video file at '${videoPath}' is 0 bytes.`);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("0 bytes")) throw err;
    throw new Error(`Cannot extract frame: input video '${videoPath}' does not exist or is unreadable.`);
  }

  const position = options.position ?? "last";
  const format = options.format ?? "png";
  const outDir = options.outDir ?? "./gflow-output";
  const framesDir = join(outDir, "frames");
  await mkdir(framesDir, { recursive: true });

  const base = basename(videoPath, extname(videoPath));
  const posTag = typeof position === "number" ? `${position}s` : position;
  const outPath = options.outPath ?? join(framesDir, `${base}-${posTag}-frame.${format}`);

  // Caching: reuse existing non-empty frame unless overwrite is explicitly requested
  if (!options.overwrite) {
    try {
      const existing = await stat(outPath);
      if (existing.size > 0) {
        return { path: outPath, cached: true, sourceVideo: videoPath, position };
      }
    } catch {
      // Not cached, proceed
    }
  }

  const ffmpegOk = await hasFfmpeg();
  if (ffmpegOk || options.ffmpegExecutor) {
    await extractFrameWithFfmpeg(videoPath, outPath, position, options.ffmpegExecutor);
  } else if (options.page) {
    await extractFrameWithCanvas(videoPath, outPath, position, options.page);
  } else {
    throw new Error(
      `Cannot extract video frame from '${videoPath}': Neither 'ffmpeg' was found on PATH, nor was an active Playwright page provided. Install ffmpeg or run 'gflow doctor'.`
    );
  }

  const created = await stat(outPath).catch(() => null);
  if (!created || created.size === 0) {
    throw new Error(`Frame extraction failed to generate non-empty file at '${outPath}'.`);
  }

  return { path: outPath, cached: false, sourceVideo: videoPath, position };
}

/**
 * Convenience wrapper to extract the terminal frame.
 * Accepts either an explicit output directory string or full options object.
 */
export async function extractLastFrame(
  videoPath: string,
  outDirOrOptions?: string | Omit<FrameExtractionOptions, "position">
): Promise<string> {
  const options: FrameExtractionOptions =
    typeof outDirOrOptions === "string"
      ? { outDir: outDirOrOptions, position: "last" }
      : { ...(outDirOrOptions ?? {}), position: "last" };
  const result = await extractVideoFrame(videoPath, options);
  return result.path;
}
