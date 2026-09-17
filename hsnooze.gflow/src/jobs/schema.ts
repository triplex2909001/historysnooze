import YAML from "yaml";
import { z } from "zod";

/**
 * Character Asset Schema
 * Represents a persistent character reference sheet and multi-angle turnarounds.
 */
export const characterAssetSchema = z.object({
  name: z.string().min(1),
  referenceSheet: z.string().min(1).optional(),
  images: z.array(z.string().min(1)).optional(),
  pinned: z.boolean().default(false),
  description: z.string().optional(),
  voice: z.string().optional()
});
export type CharacterAsset = z.infer<typeof characterAssetSchema>;

/**
 * Background Asset Schema
 * Represents a master environment plate for architectural/spatial consistency.
 */
export const backgroundAssetSchema = z.object({
  name: z.string().min(1),
  plate: z.string().min(1),
  description: z.string().optional()
});
export type BackgroundAsset = z.infer<typeof backgroundAssetSchema>;

/**
 * Prop Asset Schema
 * Represents an isolated reference asset for key objects, items, and vehicles.
 */
export const propAssetSchema = z.object({
  name: z.string().min(1),
  asset: z.string().min(1),
  description: z.string().optional()
});
export type PropAsset = z.infer<typeof propAssetSchema>;

const baseJobSchema = z.object({
  id: z.string().min(1).regex(/^[a-zA-Z0-9._-]+$/),
  project: z.string().min(1).optional(),
  prompt: z.string().min(1),
  model: z.string().min(1).optional(),
  ratio: z.string().min(1).optional(),
  outputs: z.number().int().min(1).max(8).default(1),
  out: z.string().min(1).default("./gflow-output"),
  timeout: z.number().int().min(1).optional(),
  ingredients: z
    .union([z.string().min(1).transform((s) => [s]), z.array(z.string().min(1))])
    .default([]),
  character: z
    .union([z.string().min(1).transform((s) => [s]), z.array(z.string().min(1))])
    .default([]),
  background: z.string().min(1).optional(),
  props: z
    .union([z.string().min(1).transform((s) => [s]), z.array(z.string().min(1))])
    .optional(),
  upscale: z.enum(["2k", "4k"]).optional(),
  dependsOn: z.array(z.string().min(1)).optional(),
  retry: z.number().int().min(0).max(5).optional()
});

export const imageJobSchema = baseJobSchema.extend({
  type: z.literal("image")
});

export const videoJobSchema = baseJobSchema.extend({
  type: z.literal("video"),
  duration: z.number().int().min(1).max(30).optional(),
  startFrame: z.string().min(1).optional(),
  endFrame: z.string().min(1).optional()
});

export const jobSchema = z.discriminatedUnion("type", [imageJobSchema, videoJobSchema]);

export const UPSCALE_TIERS = ["2k", "4k"] as const;

export const pipelineMetaSchema = z.object({
  name: z.string().optional(),
  profiles: z.array(z.string().min(1)).default(["default"]),
  autoheal: z.boolean().default(true),
  resume: z.boolean().default(true),
  maxRetries: z.number().int().default(3),
  continueOnFailure: z.boolean().default(false)
});

export const batchSchema = z.object({
  pipeline: z
    .union([
      z.string().transform((name) => ({
        name,
        profiles: ["default"],
        autoheal: true,
        resume: true,
        maxRetries: 3,
        continueOnFailure: false
      })),
      pipelineMetaSchema
    ])
    .optional(),
  characters: z.record(z.string(), characterAssetSchema).default({}),
  backgrounds: z.record(z.string(), backgroundAssetSchema).default({}),
  props: z.record(z.string(), propAssetSchema).default({}),
  jobs: z.array(jobSchema).min(1)
});

export type PipelineMeta = z.infer<typeof pipelineMetaSchema>;

export type ImageJob = z.infer<typeof imageJobSchema>;
export type VideoJob = z.infer<typeof videoJobSchema>;
export type GFlowJob = z.infer<typeof jobSchema>;
export type BatchFile = z.infer<typeof batchSchema>;

export function parseImageJob(value: unknown): ImageJob {
  return imageJobSchema.parse(value);
}

export function parseVideoJob(value: unknown): VideoJob {
  return videoJobSchema.parse(value);
}

export function parseJob(value: unknown): GFlowJob {
  return jobSchema.parse(value);
}

export function parseBatch(value: unknown): BatchFile {
  const batch = batchSchema.parse(value);
  const seen = new Set<string>();

  for (const job of batch.jobs) {
    if (seen.has(job.id)) {
      throw new Error(`Duplicate job id: ${job.id}`);
    }
    seen.add(job.id);
  }

  return batch;
}

export function parseBatchYaml(text: string): BatchFile {
  return parseBatch(YAML.parse(text));
}
