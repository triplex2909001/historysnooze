import type { CharacterAsset, GFlowJob } from "../jobs/schema.js";

export interface FlowArtifact {
  path: string;
  metadataPath: string;
}

export interface FlowJobResult {
  jobId: string;
  artifacts: FlowArtifact[];
  flowUrl: string;
}

export interface FlowAutomationRunInput {
  job: GFlowJob & {
    resolvedCharacters?: CharacterAsset[];
  };
  resolvedCharacters?: CharacterAsset[];
  outDir: string;
}

export interface FlowAutomation {
  runJob(input: FlowAutomationRunInput): Promise<FlowJobResult>;
}
