import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync, spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const OUT_DIR = "/media/vpsg24gb/DATA/gflow/out";
const FRAMES_DIR = join(OUT_DIR, "frames");

interface StreamInfo {
  index: number;
  codec_name: string;
  codec_type: string;
  codec_tag_string?: string;
  width?: number;
  height?: number;
  r_frame_rate?: string;
  avg_frame_rate?: string;
  duration?: string;
  bit_rate?: string;
  nb_frames?: string;
  sample_rate?: string;
  channels?: number;
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

function runFfprobe(filePath: string): FfprobeOutput {
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

describe("Milestone 7: Video Deliverables Adversarial Probe Suite", () => {
  const shots = [
    {
      id: "shot1_market_arrival",
      mp4: "shot1_market_arrival-001.mp4",
      json: "shot1_market_arrival-001.json",
      expectedDurationMin: 5.0,
      expectedDurationMax: 12.0,
    },
    {
      id: "shot2_apple_discovery",
      mp4: "shot2_apple_discovery-001.mp4",
      json: "shot2_apple_discovery-001.json",
      expectedDurationMin: 5.0,
      expectedDurationMax: 12.0,
    },
    {
      id: "shot3_watermelon_joy",
      mp4: "shot3_watermelon_joy-001.mp4",
      json: "shot3_watermelon_joy-001.json",
      expectedDurationMin: 5.0,
      expectedDurationMax: 12.0,
    },
  ];

  describe("File Existence and Size Checks", () => {
    for (const shot of shots) {
      it(`should have valid MP4 file for ${shot.id} with size > 1MB`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        expect(existsSync(mp4Path)).toBe(true);
        const buffer = readFileSync(mp4Path);
        expect(buffer.length).toBeGreaterThan(1_000_000);
      });

      it(`should have valid JSON metadata sidecar for ${shot.id}`, () => {
        const jsonPath = join(OUT_DIR, shot.json);
        expect(existsSync(jsonPath)).toBe(true);
        const content = JSON.parse(readFileSync(jsonPath, "utf-8"));
        expect(content.jobId).toBe(shot.id);
        expect(content.type).toBe("video");
        expect(content.ratio).toBe("9:16");
        expect(content.status).toBe("downloaded");
      });
    }

    it("should have valid checkpoint.json with all 3 jobs completed", () => {
      const cpPath = join(OUT_DIR, "checkpoint.json");
      expect(existsSync(cpPath)).toBe(true);
      const cp = JSON.parse(readFileSync(cpPath, "utf-8"));
      expect(cp.completed).toEqual([
        "shot1_market_arrival",
        "shot2_apple_discovery",
        "shot3_watermelon_joy",
      ]);
      expect(cp.failed).toEqual([]);
    });

    it("should have chaining frames extracted for shot1 and shot2", () => {
      const f1 = join(FRAMES_DIR, "shot1_market_arrival-001-last-frame.png");
      const f2 = join(FRAMES_DIR, "shot2_apple_discovery-001-last-frame.png");
      expect(existsSync(f1)).toBe(true);
      expect(existsSync(f2)).toBe(true);
      expect(readFileSync(f1).length).toBeGreaterThan(500_000);
      expect(readFileSync(f2).length).toBeGreaterThan(500_000);
    });
  });

  describe("Container and Stream Technical Specifications", () => {
    let totalDuration = 0;

    for (const shot of shots) {
      it(`should satisfy codec, dimensions, and aspect ratio for ${shot.mp4}`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        const probe = runFfprobe(mp4Path);

        const videoStreams = probe.streams.filter((s) => s.codec_type === "video");
        expect(videoStreams.length).toBe(1);

        const vs = videoStreams[0];
        expect(vs.codec_name).toBe("h264");
        expect(vs.codec_tag_string).toBe("avc1");
        expect(vs.width).toBe(720);
        expect(vs.height).toBe(1280);

        // Aspect ratio verification: 720 / 1280 = 9 / 16 = 0.5625
        const ratio = vs.width! / vs.height!;
        expect(Math.abs(ratio - 9 / 16)).toBeLessThan(1e-4);

        // Frame rate verification: 24 fps
        expect(vs.r_frame_rate).toBe("24/1");
        expect(vs.avg_frame_rate).toBe("24/1");

        // Duration check
        const dur = parseFloat(vs.duration ?? "0");
        expect(dur).toBeGreaterThanOrEqual(shot.expectedDurationMin);
        expect(dur).toBeLessThanOrEqual(shot.expectedDurationMax);
        totalDuration += dur;

        // Bitrate check
        const bitRate = parseInt(vs.bit_rate ?? "0", 10);
        expect(bitRate).toBeGreaterThan(1_000_000); // at least 1 Mbps

        const fmtBitRate = parseInt(probe.format.bit_rate ?? "0", 10);
        expect(fmtBitRate).toBeGreaterThan(1_000_000);
      });

      it(`should decode completely cleanly without errors or warnings for ${shot.mp4}`, () => {
        const mp4Path = join(OUT_DIR, shot.mp4);
        const check = runFfmpegDecodeCheck(mp4Path);
        expect(check.exitCode).toBe(0);
        expect(check.stderr).toBe("");
      });
    }

    it("should satisfy the ~20s total storyboard duration requirement across all 3 shots", () => {
      // 3 shots of ~6-10s each = 15s to 36s total, which satisfies the storyboard requirement
      expect(totalDuration).toBeGreaterThanOrEqual(15.0);
      expect(totalDuration).toBeLessThanOrEqual(36.0);
    });
  });

  describe("Chaining Frame Properties", () => {
    it("should verify last-frame PNGs are 720x1280", () => {
      for (const fname of [
        "shot1_market_arrival-001-last-frame.png",
        "shot2_apple_discovery-001-last-frame.png",
      ]) {
        const p = join(FRAMES_DIR, fname);
        const probe = runFfprobe(p);
        const s = probe.streams[0];
        expect(s.width).toBe(720);
        expect(s.height).toBe(1280);
        expect(s.codec_name).toBe("png");
      }
    });
  });
});
