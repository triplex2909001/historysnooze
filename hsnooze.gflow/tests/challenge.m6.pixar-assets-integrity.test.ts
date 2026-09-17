import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { inflateSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { parseBatchYaml } from "../src/jobs/schema.js";
import { resolvePipeline } from "../src/jobs/resolver.js";

// ============================================================================
// PNG Specification Constants & CRC32 Implementation
// ============================================================================

export const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// Precomputed CRC-32 table (ISO 3309 / ITU-T V.42 / PNG specification)
const CRC_TABLE = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) {
    c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  CRC_TABLE[n] = c >>> 0;
}

export function computePngCrc32(data: Uint8Array | Buffer): number {
  let c = 0xffffffff;
  for (let i = 0; i < data.length; i++) {
    c = CRC_TABLE[(c ^ data[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

export interface PngIhdr {
  width: number;
  height: number;
  bitDepth: number;
  colorType: number;
  compression: number;
  filter: number;
  interlace: number;
}

export interface PngChunk {
  type: string;
  length: number;
  data: Buffer;
  crc: number;
  expectedCrc: number;
  crcValid: boolean;
  offset: number;
}

export interface PngParseResult {
  signatureValid: boolean;
  fileSize: number;
  chunks: PngChunk[];
  ihdr: PngIhdr | null;
  idatChunks: PngChunk[];
  totalIdatBytes: number;
  decompressedBytes: number | null;
  trailingBytes: number;
  errors: string[];
}

export function parsePng(buffer: Buffer): PngParseResult {
  const result: PngParseResult = {
    signatureValid: false,
    fileSize: buffer.length,
    chunks: [],
    ihdr: null,
    idatChunks: [],
    totalIdatBytes: 0,
    decompressedBytes: null,
    trailingBytes: 0,
    errors: []
  };

  if (buffer.length < 8) {
    result.errors.push(`File too short: ${buffer.length} bytes (minimum 8 bytes for PNG signature)`);
    return result;
  }

  if (!buffer.subarray(0, 8).equals(PNG_SIGNATURE)) {
    result.errors.push("Invalid PNG signature magic bytes");
    return result;
  }
  result.signatureValid = true;

  let offset = 8;
  let seenIhdr = false;
  let seenIend = false;
  let inIdatSequence = false;
  let finishedIdatSequence = false;

  while (offset < buffer.length) {
    if (seenIend) {
      result.trailingBytes = buffer.length - offset;
      result.errors.push(`Extraneous data detected after IEND chunk: ${result.trailingBytes} bytes`);
      break;
    }

    if (offset + 8 > buffer.length) {
      result.errors.push(`Truncated file: incomplete chunk header at byte offset ${offset}`);
      break;
    }

    const length = buffer.readUInt32BE(offset);
    const typeBuf = buffer.subarray(offset + 4, offset + 8);
    const type = typeBuf.toString("latin1");
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;

    if (dataEnd + 4 > buffer.length) {
      result.errors.push(
        `Truncated file: chunk '${type}' claims length ${length}, but file ends at ${buffer.length} (expected at least ${dataEnd + 4})`
      );
      break;
    }

    const chunkData = buffer.subarray(dataStart, dataEnd);
    const storedCrc = buffer.readUInt32BE(dataEnd);
    const crcSubject = buffer.subarray(offset + 4, dataEnd);
    const expectedCrc = computePngCrc32(crcSubject);
    const crcValid = storedCrc === expectedCrc;

    if (!crcValid) {
      result.errors.push(
        `CRC32 mismatch in chunk '${type}' at offset ${offset}: stored 0x${storedCrc.toString(16)}, computed 0x${expectedCrc.toString(16)}`
      );
    }

    const chunk: PngChunk = {
      type,
      length,
      data: chunkData,
      crc: storedCrc,
      expectedCrc,
      crcValid,
      offset
    };
    result.chunks.push(chunk);

    // Validate IHDR
    if (type === "IHDR") {
      if (result.chunks.length !== 1) {
        result.errors.push(`IHDR must be the first chunk, but appeared at chunk index ${result.chunks.length - 1}`);
      }
      if (seenIhdr) {
        result.errors.push("Duplicate IHDR chunk found");
      }
      if (length !== 13) {
        result.errors.push(`Invalid IHDR length: ${length} (expected exactly 13 bytes)`);
      } else {
        const width = chunkData.readUInt32BE(0);
        const height = chunkData.readUInt32BE(4);
        const bitDepth = chunkData[8];
        const colorType = chunkData[9];
        const compression = chunkData[10];
        const filter = chunkData[11];
        const interlace = chunkData[12];

        result.ihdr = { width, height, bitDepth, colorType, compression, filter, interlace };

        if (width === 0 || height === 0) {
          result.errors.push(`Invalid image dimensions: ${width}x${height}`);
        }
        if (![1, 2, 4, 8, 16].includes(bitDepth)) {
          result.errors.push(`Invalid bit depth: ${bitDepth}`);
        }
        if (![0, 2, 3, 4, 6].includes(colorType)) {
          result.errors.push(`Invalid color type: ${colorType}`);
        }
        if (compression !== 0) {
          result.errors.push(`Invalid compression method: ${compression} (must be 0)`);
        }
        if (filter !== 0) {
          result.errors.push(`Invalid filter method: ${filter} (must be 0)`);
        }
        if (![0, 1].includes(interlace)) {
          result.errors.push(`Invalid interlace method: ${interlace} (must be 0 or 1)`);
        }
      }
      seenIhdr = true;
    } else if (!seenIhdr) {
      result.errors.push(`First chunk is '${type}', but PNG specification requires 'IHDR'`);
    }

    // Validate IDAT chunk ordering and sequence continuity
    if (type === "IDAT") {
      if (finishedIdatSequence) {
        result.errors.push("Non-consecutive IDAT chunk detected after previous IDAT sequence concluded");
      }
      inIdatSequence = true;
      result.idatChunks.push(chunk);
      result.totalIdatBytes += length;
      if (length === 0) {
        result.errors.push(`Empty IDAT chunk found at offset ${offset}`);
      }
    } else if (inIdatSequence) {
      // Transitioned out of IDAT sequence
      inIdatSequence = false;
      finishedIdatSequence = true;
    }

    // Validate IEND
    if (type === "IEND") {
      seenIend = true;
      if (length !== 0) {
        result.errors.push(`IEND chunk has non-zero length: ${length}`);
      }
    }

    offset = dataEnd + 4;
  }

  if (!seenIend) {
    result.errors.push("Missing IEND chunk (file truncated or corrupt)");
  }

  if (result.idatChunks.length === 0) {
    result.errors.push("No IDAT chunks found in image");
  } else {
    // Attempt ZLIB inflate decompression of concatenated IDAT stream
    try {
      const concatenatedIdat = Buffer.concat(result.idatChunks.map((c) => c.data));
      const decompressed = inflateSync(concatenatedIdat);
      result.decompressedBytes = decompressed.length;

      // If non-interlaced, check expected uncompressed scanlines size
      if (result.ihdr && result.ihdr.interlace === 0) {
        let bytesPerPixel = 1;
        switch (result.ihdr.colorType) {
          case 0: // Grayscale
            bytesPerPixel = 1;
            break;
          case 2: // Truecolor RGB
            bytesPerPixel = 3;
            break;
          case 3: // Indexed
            bytesPerPixel = 1;
            break;
          case 4: // Grayscale with Alpha
            bytesPerPixel = 2;
            break;
          case 6: // Truecolor with Alpha RGBA
            bytesPerPixel = 4;
            break;
        }
        if (result.ihdr.bitDepth === 16) {
          bytesPerPixel *= 2;
        }
        const scanlineWidth = 1 + result.ihdr.width * bytesPerPixel;
        const expectedDecompressedSize = scanlineWidth * result.ihdr.height;

        if (decompressed.length !== expectedDecompressedSize) {
          result.errors.push(
            `Decompressed scanline size mismatch: got ${decompressed.length} bytes, expected ${expectedDecompressedSize} bytes (${result.ihdr.width}x${result.ihdr.height}, colorType ${result.ihdr.colorType})`
          );
        }
      }
    } catch (err: unknown) {
      result.errors.push(`ZLIB IDAT payload decompression failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return result;
}

// ============================================================================
// Test Suite: M6 Adversarial Asset & Pipeline Resolution Verification
// ============================================================================

const ASSETS_DIR = resolve(__dirname, "../examples/assets/pixar_fruit_market");
const PIPELINE_YAML_PATH = resolve(__dirname, "../examples/pixar_fruit_market_pipeline.yaml");

describe("Milestone M6 Challenger: Pixar Fruit Market Binary Asset Integrity & Pipeline Resolution", () => {
  const assetFiles = readdirSync(ASSETS_DIR).filter((f) => f.endsWith(".png"));

  // ==========================================================================
  // Section 1: Directory Enumeration & Non-Zero Byte Verification
  // ==========================================================================
  describe("1. Asset Inventory & Non-Zero File Size Verification", () => {
    it("finds all expected reference assets in examples/assets/pixar_fruit_market/", () => {
      const expectedAssets = [
        "bamboo_basket.png",
        "bamboo_basket_isolated.png",
        "fresh_apple.png",
        "fresh_apple_isolated.png",
        "fruit_market_stall_plate.png",
        "ling_reference_sheet.png",
        "ming_reference_sheet.png",
        "watermelon_slice.png",
        "watermelon_slice_isolated.png"
      ];

      for (const expected of expectedAssets) {
        expect(assetFiles, `Asset directory must contain ${expected}`).toContain(expected);
      }
      expect(assetFiles.length).toBeGreaterThanOrEqual(9);
    });

    it("verifies no assets are 0-byte or suspiciously small (< 10KB)", () => {
      for (const fileName of assetFiles) {
        const filePath = join(ASSETS_DIR, fileName);
        const stats = statSync(filePath);

        expect(stats.size, `File ${fileName} must not be 0 bytes`).toBeGreaterThan(0);
        expect(
          stats.size,
          `File ${fileName} size (${stats.size} bytes) should be substantial (> 100KB for high-res asset)`
        ).toBeGreaterThan(100 * 1024);
      }
    });
  });

  // ==========================================================================
  // Section 2: Deep PNG Binary Parsing, IHDR, CRC32, IDAT Checks
  // ==========================================================================
  describe("2. Deep PNG Binary Parsing & Specification Conformance", () => {
    for (const fileName of assetFiles) {
      describe(`Asset: ${fileName}`, () => {
        const filePath = join(ASSETS_DIR, fileName);
        const buffer = readFileSync(filePath);
        const parsed = parsePng(buffer);

        it("has valid 8-byte PNG magic signature", () => {
          expect(parsed.signatureValid, `Valid PNG signature for ${fileName}`).toBe(true);
          expect(buffer.subarray(0, 8)).toEqual(PNG_SIGNATURE);
        });

        it("has valid IHDR header chunk as first chunk with valid dimensions and color type", () => {
          expect(parsed.ihdr, `IHDR must be present for ${fileName}`).not.toBeNull();
          const ihdr = parsed.ihdr!;

          expect(ihdr.width).toBeGreaterThan(0);
          expect(ihdr.height).toBeGreaterThan(0);
          expect(ihdr.bitDepth).toBe(8);
          expect(ihdr.colorType).toBe(6); // RGBA
          expect(ihdr.compression).toBe(0);
          expect(ihdr.filter).toBe(0);
          expect(ihdr.interlace).toBe(0);
        });

        it("passes CRC32 validation for every chunk in the file", () => {
          expect(parsed.chunks.length).toBeGreaterThanOrEqual(3);
          for (const chunk of parsed.chunks) {
            expect(
              chunk.crcValid,
              `CRC32 mismatch in ${fileName} chunk ${chunk.type} at offset ${chunk.offset}`
            ).toBe(true);
            expect(chunk.crc).toBe(chunk.expectedCrc);
          }
        });

        it("contains non-empty, consecutive IDAT chunks that decompress cleanly without truncation", () => {
          expect(parsed.idatChunks.length, `Must have IDAT chunks in ${fileName}`).toBeGreaterThan(0);
          expect(parsed.totalIdatBytes, `Total IDAT bytes must be > 0 in ${fileName}`).toBeGreaterThan(0);

          for (const idat of parsed.idatChunks) {
            expect(idat.length, `Each IDAT in ${fileName} must have length > 0`).toBeGreaterThan(0);
          }

          expect(
            parsed.decompressedBytes,
            `Decompressed scanline payload must not be null in ${fileName}`
          ).not.toBeNull();
          expect(parsed.decompressedBytes!).toBeGreaterThan(0);

          // Verify exact scanline byte size: height * (1 + width * 4)
          const expectedScanlineBytes = parsed.ihdr!.height * (1 + parsed.ihdr!.width * 4);
          expect(parsed.decompressedBytes).toBe(expectedScanlineBytes);
        });

        it("terminates with valid IEND chunk with 0 trailing bytes", () => {
          const lastChunk = parsed.chunks[parsed.chunks.length - 1];
          expect(lastChunk.type).toBe("IEND");
          expect(lastChunk.length).toBe(0);
          expect(lastChunk.crcValid).toBe(true);
          expect(parsed.trailingBytes, `No trailing bytes permitted after IEND in ${fileName}`).toBe(0);
        });

        it("has zero parsing errors or corruptions", () => {
          expect(parsed.errors, `Errors encountered while parsing ${fileName}`).toEqual([]);
        });
      });
    }
  });

  // ==========================================================================
  // Section 3: Oracle Sensitivity & Adversarial Detection Verification
  // ==========================================================================
  describe("3. Adversarial Test Harness Oracle Sensitivity", () => {
    const sampleBuffer = readFileSync(join(ASSETS_DIR, "fresh_apple.png"));

    it("detects 0-byte file", () => {
      const res = parsePng(Buffer.alloc(0));
      expect(res.signatureValid).toBe(false);
      expect(res.errors.length).toBeGreaterThan(0);
      expect(res.errors[0]).toContain("File too short");
    });

    it("detects corrupted PNG magic signature", () => {
      const corrupt = Buffer.from(sampleBuffer);
      corrupt[0] = 0x00;
      const res = parsePng(corrupt);
      expect(res.signatureValid).toBe(false);
      expect(res.errors).toContain("Invalid PNG signature magic bytes");
    });

    it("detects corrupted CRC32 in IHDR", () => {
      const corrupt = Buffer.from(sampleBuffer);
      // IHDR CRC is at byte 8 + 4 + 4 + 13 = 29
      corrupt[29] ^= 0xff;
      const res = parsePng(corrupt);
      expect(res.errors.some((e) => e.includes("CRC32 mismatch in chunk 'IHDR'"))).toBe(true);
    });

    it("detects truncated IDAT chunk payload", () => {
      // Truncate file in the middle of IDAT chunks
      const corrupt = sampleBuffer.subarray(0, sampleBuffer.length - 5000);
      const res = parsePng(corrupt);
      expect(
        res.errors.some((e) => e.includes("Truncated file") || e.includes("Missing IEND chunk")),
        "Must flag truncated file"
      ).toBe(true);
    });

    it("detects trailing garbage bytes after IEND", () => {
      const corrupt = Buffer.concat([sampleBuffer, Buffer.from("EXTRA_GARBAGE_PAYLOAD")]);
      const res = parsePng(corrupt);
      expect(res.trailingBytes).toBe(21);
      expect(res.errors.some((e) => e.includes("Extraneous data detected after IEND"))).toBe(true);
    });

    it("detects corrupted ZLIB compressed stream inside IDAT", () => {
      const corrupt = Buffer.from(sampleBuffer);
      // Find first IDAT data start (byte offset 8 + 8 + 13 + 4 + 8 = 41)
      corrupt[42] ^= 0x55;
      corrupt[43] ^= 0xaa;
      const res = parsePng(corrupt);
      expect(
        res.errors.some((e) => e.includes("CRC32 mismatch") || e.includes("ZLIB IDAT payload decompression failed"))
      ).toBe(true);
    });
  });

  // ==========================================================================
  // Section 4: Pipeline Declarative Reference & Asset Resolution
  // ==========================================================================
  describe("4. Pipeline Declarative Reference & Asset Resolution", () => {
    it("loads and resolves examples/pixar_fruit_market_pipeline.yaml cleanly", () => {
      expect(existsSync(PIPELINE_YAML_PATH), "Pipeline YAML file must exist").toBe(true);
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      expect(batch).toBeDefined();

      const resolved = resolvePipeline(batch);
      expect(resolved).toBeDefined();
      expect(resolved.jobs.length).toBe(3);
    });

    it("verifies all character reference sheets resolve to readable existing files", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      expect(resolved.characters.ming).toBeDefined();
      expect(resolved.characters.ming.referenceSheet).toBeDefined();
      const mingSheetPath = resolve(__dirname, "..", resolved.characters.ming.referenceSheet!);
      expect(existsSync(mingSheetPath), `Ming reference sheet must exist at ${mingSheetPath}`).toBe(true);
      expect(statSync(mingSheetPath).size).toBeGreaterThan(0);

      expect(resolved.characters.ling).toBeDefined();
      expect(resolved.characters.ling.referenceSheet).toBeDefined();
      const lingSheetPath = resolve(__dirname, "..", resolved.characters.ling.referenceSheet!);
      expect(existsSync(lingSheetPath), `Ling reference sheet must exist at ${lingSheetPath}`).toBe(true);
      expect(statSync(lingSheetPath).size).toBeGreaterThan(0);
    });

    it("verifies master background plate resolves to readable existing file", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      const bg = resolved.backgrounds.fruit_market_stall;
      expect(bg).toBeDefined();
      expect(bg.plate).toBeDefined();
      const platePath = resolve(__dirname, "..", bg.plate);
      expect(existsSync(platePath), `Background plate must exist at ${platePath}`).toBe(true);
      expect(statSync(platePath).size).toBeGreaterThan(0);
    });

    it("verifies all prop isolated assets resolve to readable existing files", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      const expectedProps = ["bamboo_basket", "fresh_apple", "watermelon_slice"];
      for (const propKey of expectedProps) {
        const prop = resolved.props[propKey];
        expect(prop, `Prop ${propKey} must be defined`).toBeDefined();
        expect(prop.asset, `Prop ${propKey} asset must be defined`).toBeDefined();

        const assetPath = resolve(__dirname, "..", prop.asset);
        expect(existsSync(assetPath), `Prop asset must exist at ${assetPath}`).toBe(true);
        expect(statSync(assetPath).size).toBeGreaterThan(0);
      }
    });

    it("verifies job ingredient and character attachments are non-empty and accessible", () => {
      const rawYaml = readFileSync(PIPELINE_YAML_PATH, "utf-8");
      const batch = parseBatchYaml(rawYaml);
      const resolved = resolvePipeline(batch);

      for (const job of resolved.jobs) {
        // Character attachments
        expect(job.resolvedCharacters, `Job ${job.id} must have resolvedCharacters`).toBeDefined();
        expect(job.resolvedCharacters!.length).toBe(2);
        for (const char of job.resolvedCharacters!) {
          expect(char.referenceSheet).toBeDefined();
          const sheetPath = resolve(__dirname, "..", char.referenceSheet!);
          expect(existsSync(sheetPath)).toBe(true);
        }

        // Ingredient attachments
        expect(job.ingredients, `Job ${job.id} must have ingredients`).toBeDefined();
        expect(job.ingredients!.length).toBeGreaterThanOrEqual(2); // At least background plate + 1 prop
        for (const ing of job.ingredients!) {
          // If it's a file path (starts with examples/ or assets/)
          if (ing.startsWith("examples/") || ing.startsWith("assets/")) {
            const ingPath = resolve(__dirname, "..", ing);
            expect(existsSync(ingPath), `Ingredient file ${ing} must exist on disk`).toBe(true);
            expect(statSync(ingPath).size).toBeGreaterThan(0);
          }
        }
      }
    });
  });
});
