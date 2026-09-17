import type {
  BackgroundAsset,
  BatchFile,
  CharacterAsset,
  GFlowJob,
  ImageJob,
  PropAsset,
  VideoJob
} from "./schema.js";

export interface ResolvedAssetRegistries {
  characters: Record<string, CharacterAsset>;
  backgrounds: Record<string, BackgroundAsset>;
  props: Record<string, PropAsset>;
}

export type ResolvedJob = (ImageJob | VideoJob) & {
  /** Detailed character asset records attached for pinning/tagging in FlowPage */
  resolvedCharacters?: CharacterAsset[];
  /** Combined explicit and inferred dependencies */
  dependsOn: string[];
};

export interface ResolvedPipeline {
  pipeline?: BatchFile["pipeline"];
  characters: Record<string, CharacterAsset>;
  backgrounds: Record<string, BackgroundAsset>;
  props: Record<string, PropAsset>;
  jobs: ResolvedJob[];
}

// Regular expressions for reference parsing
export const CHARACTER_REF_REGEX = /^\$ref:characters\.([a-zA-Z0-9._-]+)$/;
export const BACKGROUND_REF_REGEX = /^\$ref:backgrounds\.([a-zA-Z0-9._-]+)$/;
export const PROP_REF_REGEX = /^\$ref:props\.([a-zA-Z0-9._-]+)$/;
export const OUTPUT_REF_REGEX = /^\$output:([a-zA-Z0-9._-]+)(?:\[(\d+)\])?(?:#(first|last|(?:\d+(?:\.\d+)?s?)))?$/;
export const LEGACY_OUTPUT_REF_REGEX = /\$\{([a-zA-Z0-9._-]+)\.artifacts(?:\[(\d+)\])?\}/g;

export function isCharacterRef(val: string): boolean {
  return CHARACTER_REF_REGEX.test(val);
}

export function isBackgroundRef(val: string): boolean {
  return BACKGROUND_REF_REGEX.test(val);
}

export function isPropRef(val: string): boolean {
  return PROP_REF_REGEX.test(val);
}

export function parseOutputRef(val: string): { jobId: string; index: number; position?: "first" | "last" | number } | null {
  const match = OUTPUT_REF_REGEX.exec(val);
  if (match) {
    let position: "first" | "last" | number | undefined;
    if (match[3]) {
      if (match[3] === "first" || match[3] === "last") {
        position = match[3];
      } else {
        const num = parseFloat(match[3].replace(/s$/, ""));
        if (!isNaN(num)) position = num;
      }
    }
    return {
      jobId: match[1],
      index: match[2] ? parseInt(match[2], 10) : 0,
      position
    };
  }
  return null;
}

/**
 * Extracts dependency job IDs referenced by $output:<job_id> or legacy syntax in job fields.
 */
export function extractOutputDependencies(job: Partial<GFlowJob> & { id?: string }): string[] {
  const deps = new Set<string>();

  const checkVal = (val?: string) => {
    if (!val) return;
    const outputParsed = parseOutputRef(val);
    if (outputParsed) {
      deps.add(outputParsed.jobId);
      return;
    }

    const singleMatch = val.match(/\$output:([a-zA-Z0-9._-]+)/);
    if (singleMatch) {
      deps.add(singleMatch[1]);
    }

    let legacyMatch: RegExpExecArray | null;
    const regex = new RegExp(LEGACY_OUTPUT_REF_REGEX);
    while ((legacyMatch = regex.exec(val)) !== null) {
      deps.add(legacyMatch[1]);
    }
  };

  if ("startFrame" in job && job.startFrame) checkVal(job.startFrame);
  if ("endFrame" in job && job.endFrame) checkVal(job.endFrame);
  for (const ingredient of job.ingredients ?? []) {
    checkVal(ingredient);
  }

  return Array.from(deps);
}

/**
 * Resolves static $ref:* references and infers DAG dependencies for a single job.
 */
export function resolveJobReferences(
  job: GFlowJob,
  registries: ResolvedAssetRegistries,
  knownJobIds: Set<string>
): ResolvedJob {
  const resolvedCharactersList: string[] = [];
  const resolvedChars: CharacterAsset[] = [];
  const resolvedIngredients: string[] = [...(job.ingredients ?? [])];
  const resolvedDependsOn: string[] = [...(job.dependsOn ?? [])];

  // 1. Resolve characters
  for (const charItem of job.character ?? []) {
    const match = CHARACTER_REF_REGEX.exec(charItem);
    if (match) {
      const key = match[1];
      const asset = registries.characters[key];
      if (!asset) {
        const available = Object.keys(registries.characters).join(", ") || "none";
        throw new Error(
          `Character reference '$ref:characters.${key}' in job '${job.id}' not found. Available characters: [${available}]`
        );
      }
      resolvedCharactersList.push(asset.name);
      resolvedChars.push(asset);
    } else if (registries.characters[charItem]) {
      const asset = registries.characters[charItem];
      resolvedCharactersList.push(asset.name);
      resolvedChars.push(asset);
    } else {
      resolvedCharactersList.push(charItem);
    }
  }

  // 2. Resolve background plate convenience field
  const backgroundField = job.background;
  if (backgroundField) {
    const match = BACKGROUND_REF_REGEX.exec(backgroundField);
    if (match) {
      const key = match[1];
      const asset = registries.backgrounds[key];
      if (!asset) {
        const available = Object.keys(registries.backgrounds).join(", ") || "none";
        throw new Error(
          `Background reference '$ref:backgrounds.${key}' in job '${job.id}' not found. Available backgrounds: [${available}]`
        );
      }
      if (!resolvedIngredients.includes(asset.plate)) {
        resolvedIngredients.push(asset.plate);
      }
    } else if (registries.backgrounds[backgroundField]) {
      const asset = registries.backgrounds[backgroundField];
      if (!resolvedIngredients.includes(asset.plate)) {
        resolvedIngredients.push(asset.plate);
      }
    } else {
      if (!resolvedIngredients.includes(backgroundField)) {
        resolvedIngredients.push(backgroundField);
      }
    }
  }

  // 3. Resolve props convenience field
  const propsField = job.props;
  if (propsField) {
    for (const propItem of propsField) {
      const match = PROP_REF_REGEX.exec(propItem);
      if (match) {
        const key = match[1];
        const asset = registries.props[key];
        if (!asset) {
          const available = Object.keys(registries.props).join(", ") || "none";
          throw new Error(
            `Prop reference '$ref:props.${key}' in job '${job.id}' not found. Available props: [${available}]`
          );
        }
        if (!resolvedIngredients.includes(asset.asset)) {
          resolvedIngredients.push(asset.asset);
        }
      } else if (registries.props[propItem]) {
        const asset = registries.props[propItem];
        if (!resolvedIngredients.includes(asset.asset)) {
          resolvedIngredients.push(asset.asset);
        }
      } else {
        if (!resolvedIngredients.includes(propItem)) {
          resolvedIngredients.push(propItem);
        }
      }
    }
  }

  // 4. Resolve references inside ingredients
  const mappedIngredients = resolvedIngredients.map((item) => {
    const charMatch = CHARACTER_REF_REGEX.exec(item);
    if (charMatch) {
      const key = charMatch[1];
      const asset = registries.characters[key];
      if (!asset) {
        const available = Object.keys(registries.characters).join(", ") || "none";
        throw new Error(
          `Character reference '$ref:characters.${key}' in ingredients of job '${job.id}' not found. Available characters: [${available}]`
        );
      }
      return asset.referenceSheet || asset.images?.[0] || item;
    }

    const bgMatch = BACKGROUND_REF_REGEX.exec(item);
    if (bgMatch) {
      const key = bgMatch[1];
      const asset = registries.backgrounds[key];
      if (!asset) {
        const available = Object.keys(registries.backgrounds).join(", ") || "none";
        throw new Error(
          `Background reference '$ref:backgrounds.${key}' in ingredients of job '${job.id}' not found. Available backgrounds: [${available}]`
        );
      }
      return asset.plate;
    }

    const propMatch = PROP_REF_REGEX.exec(item);
    if (propMatch) {
      const key = propMatch[1];
      const asset = registries.props[key];
      if (!asset) {
        const available = Object.keys(registries.props).join(", ") || "none";
        throw new Error(
          `Prop reference '$ref:props.${key}' in ingredients of job '${job.id}' not found. Available props: [${available}]`
        );
      }
      return asset.asset;
    }

    return item;
  });

  let startFrame = "startFrame" in job ? job.startFrame : undefined;
  let endFrame = "endFrame" in job ? job.endFrame : undefined;

  // 5. Resolve references inside startFrame / endFrame
  if (startFrame) {
    const bgMatch = BACKGROUND_REF_REGEX.exec(startFrame);
    if (bgMatch) {
      const key = bgMatch[1];
      const asset = registries.backgrounds[key];
      if (!asset) {
        const available = Object.keys(registries.backgrounds).join(", ") || "none";
        throw new Error(
          `Background reference '$ref:backgrounds.${key}' in startFrame of job '${job.id}' not found. Available backgrounds: [${available}]`
        );
      }
      startFrame = asset.plate;
    }
    const propMatch = PROP_REF_REGEX.exec(startFrame);
    if (propMatch) {
      const key = propMatch[1];
      const asset = registries.props[key];
      if (!asset) {
        const available = Object.keys(registries.props).join(", ") || "none";
        throw new Error(
          `Prop reference '$ref:props.${key}' in startFrame of job '${job.id}' not found. Available props: [${available}]`
        );
      }
      startFrame = asset.asset;
    }
  }

  if (endFrame) {
    const bgMatch = BACKGROUND_REF_REGEX.exec(endFrame);
    if (bgMatch) {
      const key = bgMatch[1];
      const asset = registries.backgrounds[key];
      if (!asset) {
        const available = Object.keys(registries.backgrounds).join(", ") || "none";
        throw new Error(
          `Background reference '$ref:backgrounds.${key}' in endFrame of job '${job.id}' not found. Available backgrounds: [${available}]`
        );
      }
      endFrame = asset.plate;
    }
    const propMatch = PROP_REF_REGEX.exec(endFrame);
    if (propMatch) {
      const key = propMatch[1];
      const asset = registries.props[key];
      if (!asset) {
        const available = Object.keys(registries.props).join(", ") || "none";
        throw new Error(
          `Prop reference '$ref:props.${key}' in endFrame of job '${job.id}' not found. Available props: [${available}]`
        );
      }
      endFrame = asset.asset;
    }
  }

  // 6. Infer and validate dependencies from $output references
  const inferredDeps = extractOutputDependencies(job);
  for (const depId of inferredDeps) {
    if (depId === job.id) {
      throw new Error(`Job '${job.id}' cannot reference its own output (self-dependency detected)`);
    }
    if (!knownJobIds.has(depId)) {
      throw new Error(
        `Job '${job.id}' references output of undefined job '${depId}'. Defined jobs: [${Array.from(knownJobIds).join(", ")}]`
      );
    }
    if (!resolvedDependsOn.includes(depId)) {
      resolvedDependsOn.push(depId);
    }
  }

  // Validate explicit dependsOn
  for (const depId of job.dependsOn ?? []) {
    if (depId === job.id) {
      throw new Error(`Job '${job.id}' cannot depend on itself (self-dependency detected)`);
    }
    if (!knownJobIds.has(depId)) {
      throw new Error(
        `Job '${job.id}' depends on undefined job '${depId}'. Defined jobs: [${Array.from(knownJobIds).join(", ")}]`
      );
    }
  }

  const baseResult = {
    ...job,
    character: resolvedCharactersList,
    ingredients: mappedIngredients,
    dependsOn: resolvedDependsOn,
    resolvedCharacters: resolvedChars.length > 0 ? resolvedChars : undefined
  };

  if (job.type === "video") {
    return {
      ...baseResult,
      type: "video",
      startFrame,
      endFrame
    } as ResolvedJob;
  }

  return {
    ...baseResult,
    type: "image"
  } as ResolvedJob;
}

/**
 * Traces a cycle path through dependency edges for descriptive error reporting.
 */
function traceCycle(cycleCandidates: string[], dependencies: Map<string, string[]>): string {
  const visited = new Set<string>();
  const stack: string[] = [];
  const stackSet = new Set<string>();

  function dfs(node: string): string[] | null {
    visited.add(node);
    stack.push(node);
    stackSet.add(node);

    const prereqs = dependencies.get(node) ?? [];
    for (const prereq of prereqs) {
      if (stackSet.has(prereq)) {
        const startIndex = stack.indexOf(prereq);
        return [...stack.slice(startIndex), prereq];
      }
      if (!visited.has(prereq)) {
        const cycle = dfs(prereq);
        if (cycle) return cycle;
      }
    }

    stack.pop();
    stackSet.delete(node);
    return null;
  }

  for (const candidate of cycleCandidates) {
    if (!visited.has(candidate)) {
      const cycle = dfs(candidate);
      if (cycle) return cycle.join(" -> ");
    }
  }

  return cycleCandidates.join(", ");
}

/**
 * Topologically sorts jobs based on explicit dependsOn and inferred $output dependencies.
 * Throws descriptive cycle error if circular dependencies exist.
 */
export function resolveJobOrder<T extends GFlowJob>(jobs: T[]): T[] {
  const jobMap = new Map<string, T>();
  const inDegree = new Map<string, number>();
  const dependents = new Map<string, string[]>();   // prereq -> jobs waiting on prereq
  const dependencies = new Map<string, string[]>(); // job -> prereqs

  for (const job of jobs) {
    jobMap.set(job.id, job);
    inDegree.set(job.id, 0);
    dependents.set(job.id, []);
    dependencies.set(job.id, []);
  }

  for (const job of jobs) {
    const outputDeps = extractOutputDependencies(job);
    const deps = Array.from(new Set([...(job.dependsOn ?? []), ...outputDeps]));
    for (const depId of deps) {
      if (!jobMap.has(depId)) {
        throw new Error(`Job '${job.id}' depends on undefined job '${depId}'`);
      }
      if (depId === job.id) {
        throw new Error(`Cyclic dependency detected: Job '${job.id}' depends on itself`);
      }
      dependents.get(depId)!.push(job.id);
      dependencies.get(job.id)!.push(depId);
      inDegree.set(job.id, (inDegree.get(job.id) ?? 0) + 1);
    }
  }

  // Seed queue with inDegree 0 jobs preserving original order
  const queue: string[] = [];
  for (const job of jobs) {
    if (inDegree.get(job.id) === 0) {
      queue.push(job.id);
    }
  }

  const sorted: T[] = [];
  while (queue.length > 0) {
    const currentId = queue.shift()!;
    sorted.push(jobMap.get(currentId)!);

    for (const dependentId of dependents.get(currentId)!) {
      const nextDegree = (inDegree.get(dependentId) ?? 1) - 1;
      inDegree.set(dependentId, nextDegree);
      if (nextDegree === 0) {
        queue.push(dependentId);
      }
    }
  }

  if (sorted.length !== jobs.length) {
    const remaining = jobs
      .filter((j) => (inDegree.get(j.id) ?? 0) > 0)
      .map((j) => j.id);
    const cycleTrace = traceCycle(remaining, dependencies);
    throw new Error(`Cyclic dependency detected in pipeline jobs: ${cycleTrace}`);
  }

  return sorted;
}

/**
 * Resolves all declarative references in a parsed BatchFile and returns
 * a validated, topologically sorted ResolvedPipeline.
 */
export function resolvePipeline(batch: BatchFile): ResolvedPipeline {
  const registries: ResolvedAssetRegistries = {
    characters: batch.characters ?? {},
    backgrounds: batch.backgrounds ?? {},
    props: batch.props ?? {}
  };

  const knownJobIds = new Set(batch.jobs.map((j) => j.id));

  // 1. Resolve references and infer dependencies for each job
  const resolvedJobs: ResolvedJob[] = batch.jobs.map((job) =>
    resolveJobReferences(job, registries, knownJobIds)
  );

  // 2. Sort topologically
  const sortedJobs = resolveJobOrder(resolvedJobs);

  return {
    pipeline: batch.pipeline,
    characters: registries.characters,
    backgrounds: registries.backgrounds,
    props: registries.props,
    jobs: sortedJobs
  };
}

/**
 * Interpolates runtime artifact paths into $output references across job parameters.
 */
export function interpolateJobOutputs<T extends GFlowJob>(
  job: T,
  artifactsMap: Record<string, string[]>
): T {
  const cloned = { ...job, ingredients: [...(job.ingredients ?? [])] };

  const replaceRef = (val?: string): string | undefined => {
    if (!val) return val;

    // 1. Check $output:<job_id>[index]#tag
    const directMatch = OUTPUT_REF_REGEX.exec(val);
    if (directMatch) {
      const depId = directMatch[1];
      const idx = directMatch[2] ? parseInt(directMatch[2], 10) : 0;
      const depArtifacts = artifactsMap[depId];
      if (!depArtifacts || depArtifacts.length === 0) {
        throw new Error(
          `Cannot resolve output reference '${val}': Upstream job '${depId}' produced no output artifacts.`
        );
      }
      if (idx >= depArtifacts.length) {
        throw new Error(
          `Cannot resolve output reference '${val}': Upstream job '${depId}' only produced ${depArtifacts.length} artifact(s), requested index [${idx}].`
        );
      }
      return depArtifacts[idx];
    }

    // 2. Check legacy ${job_id.artifacts[index]}
    return val.replace(
      /\$\{([a-zA-Z0-9._-]+)\.artifacts(?:\[(\d+)\])?\}/g,
      (match, depId, indexStr) => {
        const depArtifacts = artifactsMap[depId];
        if (!depArtifacts || depArtifacts.length === 0) {
          throw new Error(
            `Cannot resolve output reference '${match}': Upstream job '${depId}' produced no output artifacts.`
          );
        }
        const idx = indexStr ? parseInt(indexStr, 10) : 0;
        if (idx >= depArtifacts.length) {
          throw new Error(
            `Cannot resolve output reference '${match}': Upstream job '${depId}' only produced ${depArtifacts.length} artifact(s), requested index [${idx}].`
          );
        }
        return depArtifacts[idx];
      }
    );
  };

  // Interpolate startFrame & endFrame for video jobs
  if ("startFrame" in cloned && cloned.startFrame) {
    cloned.startFrame = replaceRef(cloned.startFrame);
  }
  if ("endFrame" in cloned && cloned.endFrame) {
    cloned.endFrame = replaceRef(cloned.endFrame);
  }

  // Interpolate ingredients
  cloned.ingredients = cloned.ingredients.map((ing) => replaceRef(ing) ?? ing);

  return cloned;
}
