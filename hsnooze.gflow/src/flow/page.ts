import { join } from "node:path";
import type { Page } from "playwright";
import {
  CreditLimitError,
  GenerationBlockedError,
  GenerationFailedError,
  LoginRequiredError,
  ManualActionRequiredError,
  RateLimitedError
} from "../errors.js";
import { artifactBasename, writeArtifactMetadata } from "../output/artifacts.js";
import { downloadResult, type DownloadQuality } from "./download.js";
import type { CharacterAsset, GFlowJob } from "../jobs/schema.js";
import type { FlowAutomation, FlowAutomationRunInput, FlowJobResult } from "./types.js";
import { flowLocators } from "./locators.js";
import {
  confirmPicker,
  dismissOpenLayers,
  navigateToProject,
  pickModel,
  pickOption,
  projectIdFromUrl,
  projectSubUrl
} from "./ui.js";
import { CharacterPage } from "./characters.js";

export const FLOW_URL = "https://flow.google.com";

// Flow's aspect-ratio buttons render a Material icon ligature prefix; this maps the visible
// ratio label to that ligature so we can target the right popover button.
const RATIO_ICON: Record<string, string> = {
  "16:9": "crop_16_9",
  "9:16": "crop_9_16",
  "4:3": "crop_landscape",
  "1:1": "crop_square",
  "3:4": "crop_portrait"
};


export class FlowPage implements FlowAutomation {
  public readonly characters: CharacterPage;

  constructor(private readonly page: Page, private readonly flowUrl = FLOW_URL) {
    this.characters = new CharacterPage(page);
  }

  async open(): Promise<void> {
    await this.page.goto(this.flowUrl, { waitUntil: "domcontentloaded" });
    // Flow is a single-page app. Wait for either the signed-in dashboard or, when already
    // inside a project, the prompt box. A login/consent wall shows neither, so the wait
    // times out and assertReady() reports the real problem.
    const locators = flowLocators(this.page);
    await locators.promptBox
      .first()
      .or(locators.dashboardMarker.first())
      .waitFor({ state: "visible", timeout: 20000 })
      .catch(() => undefined);
  }

  async assertReady(): Promise<void> {
    const locators = flowLocators(this.page);

    // A signed-in session shows the Flow dashboard (project list) or, inside a project, the
    // prompt box. Either one means we are authenticated and ready.
    const dashboardReady = await locators.dashboardMarker.first().isVisible().catch(() => false);
    const promptReady = (await locators.promptBox.count()) > 0;
    if (dashboardReady || promptReady) return;

    if (await locators.manualActionMarker.first().isVisible().catch(() => false)) {
      throw new ManualActionRequiredError("Flow requires login, consent, or verification.");
    }
    throw new LoginRequiredError();
  }

  async runJob(input: FlowAutomationRunInput): Promise<FlowJobResult> {
    await this.assertReady();
    const locators = flowLocators(this.page);
    if (input.job.project) {
      await navigateToProject(this.page, input.job.project);
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 20000 }).catch(() => undefined);
    } else {
      await this.ensureProject();
    }
    // Character reference sheet upload & pinning
    const resolvedChars: CharacterAsset[] =
      input.resolvedCharacters ??
      (input.job as { resolvedCharacters?: CharacterAsset[] }).resolvedCharacters ??
      [];

    for (const charAsset of resolvedChars) {
      if (charAsset.referenceSheet || charAsset.images?.length || charAsset.pinned !== undefined) {
        await this.characters.ensureCharacter(charAsset, input.job.project);
      }
    }

    // Return to project editor if ensureCharacter navigated to /characters or /character
    const currentProjectId = projectIdFromUrl(this.page.url());
    if (currentProjectId && (this.page.url().includes("/characters") || this.page.url().includes("/character"))) {
      const returnUrl = this.page.url().includes("flow.google.com")
        ? `https://flow.google.com/project/${currentProjectId}`
        : projectSubUrl(currentProjectId, "");
      await this.page.goto(returnUrl, { waitUntil: "domcontentloaded" });
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 20000 }).catch(() => undefined);
    }

    await this.applySettings(input.job);

    if (input.job.type === "video") {
      if (input.job.startFrame) {
        await this.uploadFrame("Start", input.job.startFrame);
      } else {
        await this.clearFrame("Start").catch(() => undefined);
      }
      if (input.job.endFrame) {
        await this.uploadFrame("End", input.job.endFrame);
      } else {
        await this.clearFrame("End").catch(() => undefined);
      }
    } else {
      await this.clearFrame("Start").catch(() => undefined);
      await this.clearFrame("End").catch(() => undefined);
    }

    if (input.job.ingredients && input.job.ingredients.length > 0) {
      await this.uploadIngredients(input.job.ingredients);
    } else {
      await this.clearIngredients().catch(() => undefined);
    }

    if ((await locators.promptBox.count()) === 0) {
      throw new GenerationFailedError("Could not find the Flow prompt box. Open or create a project first.");
    }

    const before = new Set(await this.resultSrcs(input.job.type));
    await this.fillPrompt(input.job.prompt);

    for (const name of input.job.character ?? []) {
      await this.characters.tagCharacter(name);
    }

    await this.submit();

    const generationTimeoutSeconds = input.job.timeout ?? (input.job.type === "video" ? 1800 : 900);
    const newSrcs = await this.waitForResults(before, input.job.outputs, generationTimeoutSeconds * 1000, input.job.type);

    const context = this.page.context();
    const quality: DownloadQuality = input.job.upscale ?? "original";
    const artifacts = [];
    for (let index = 0; index < Math.min(input.job.outputs, newSrcs.length); index += 1) {
      const basename = artifactBasename(input.job.id, index + 1);
      const { assetPath } = await downloadResult({
        page: this.page,
        context,
        src: newSrcs[index],
        type: input.job.type,
        quality,
        outDir: input.outDir,
        basename
      });
      const metadataPath = join(input.outDir, `${basename}.json`);
      await writeArtifactMetadata(metadataPath, {
        jobId: input.job.id,
        type: input.job.type,
        prompt: input.job.prompt,
        project: input.job.project,
        model: input.job.model,
        ratio: input.job.ratio,
        duration: input.job.type === "video" ? input.job.duration : undefined,
        requestedOutputs: input.job.outputs,
        quality,
        characters: input.job.character?.length ? input.job.character : undefined,
        downloadedAt: new Date().toISOString(),
        source: "google-flow-browser",
        flowUrl: this.page.url(),
        status: "downloaded"
      });
      artifacts.push({ path: assetPath, metadataPath });
    }

    if (artifacts.length === 0) {
      throw new GenerationFailedError("No downloadable results appeared.");
    }

    return {
      jobId: input.job.id,
      artifacts,
      flowUrl: this.page.url()
    };
  }

  // Result media currently on the page (authenticated media URLs, or data: in fixtures).
  // Video results render as <video> elements; image results as full (non-thumbnail) <img>.
  // Video posters/thumbnails carry mediaUrlType=...THUMBNAIL and must be excluded.
  private async resultSrcs(type: "image" | "video"): Promise<string[]> {
    if (type === "video") {
      const videoSrcs = await this.page.$$eval("video", (vids) =>
        vids
          .map((v) => (v as HTMLVideoElement).currentSrc || (v as HTMLVideoElement).src || v.querySelector("source")?.src || "")
          .filter((src) => /flow-content\.google\/video|flow\.google\.com\/asb|media\.getMediaUrlRedirect|storage\.googleapis|video|data:/i.test(src))
      );
      if (videoSrcs.length > 0) return videoSrcs;

      return this.page.$$eval(
        "flow-a2ui-video-option:not(:has(flow-soupy-overlay)):not(:has([class*='soupy'])) img, .video-container:not(:has(flow-soupy-overlay)):not(:has([class*='soupy'])) img, flow-video-card:not(:has(flow-soupy-overlay)) img, [class*='video-option']:not(:has(flow-soupy-overlay)) img",
        (imgs) =>
          imgs
            .map((i) => (i as HTMLImageElement).currentSrc || (i as HTMLImageElement).src)
            .filter((src) => /flow-content\.google|flow\.google\.com\/asb|media\.getMediaUrlRedirect|blob:|data:/i.test(src))
      );
    }
    return this.page.$$eval("img", (imgs) =>
      imgs
        .map((img) => (img as HTMLImageElement).currentSrc || (img as HTMLImageElement).src)
        .filter((src) => (/flow-content\.google\/image|flow\.google\.com\/asb|media\.getMediaUrlRedirect/.test(src) && !/mediaUrlType=/.test(src)) || src.startsWith("data:"))
    );
  }

  // Enter a project so the prompt box exists. Prefer opening a fresh project to avoid
  // context clutter and "Agent failed" errors on long production pipelines.
  private async ensureProject(projectId?: string): Promise<void> {
    const locators = flowLocators(this.page);
    if ((await locators.promptBox.count()) > 0) return;
    const targetProject = projectId ?? process.env.GFLOW_PROJECT_ID;
    if (targetProject) {
      await navigateToProject(this.page, targetProject);
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 20000 }).catch(() => undefined);
      if ((await locators.promptBox.count()) > 0) return;
    }
    const newProject = locators.newProjectButton.first();
    if (await newProject.count()) {
      await newProject.click().catch(() => undefined);
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 20000 }).catch(() => undefined);
      if ((await locators.promptBox.count()) > 0) return;
    }
    const existing = this.page.locator('a[href*="/project/"]').first();
    if (await existing.count()) {
      await existing.click().catch(() => undefined);
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 20000 }).catch(() => undefined);
      if ((await locators.promptBox.count()) > 0) return;
    }
  }

  async createNewProject(): Promise<void> {
    const locators = flowLocators(this.page);
    await this.page.goto("https://flow.google.com/", { waitUntil: "domcontentloaded" });
    await this.page.waitForTimeout(2000);
    const newProject = locators.newProjectButton.first();
    if (await newProject.isVisible({ timeout: 10000 }).catch(() => false)) {
      await newProject.click().catch(() => undefined);
      await locators.promptBox.first().waitFor({ state: "visible", timeout: 25000 }).catch(() => undefined);
    }
  }

  // Best-effort: open the settings popover and set mode/model/ratio/duration/outputs. The
  // controls live in a portal and are driven by React, so each option must be picked with a
  // real (trusted) Playwright click — a DOM .click() in page.evaluate is ignored and leaves
  // the mode on Image. When the popover is absent (e.g. the fixture) we leave current settings.
  private async applySettings(job: GFlowJob): Promise<void> {
    const settings = flowLocators(this.page).settingsButton.first();
    const tuneSettings = this.page.locator("button[aria-label=\"Settings\"], button:has-text(\"tune\")").first();
    const targetSettings = (await settings.count()) ? settings : (await tuneSettings.count()) ? tuneSettings : null;
    if (!targetSettings) return;

    // A layer left open by a previous (failed) command would make this click TOGGLE the
    // popover closed and every pick below silently miss — start from a clean slate.
    await dismissOpenLayers(this.page);
    await targetSettings.click({ force: true }).catch(() => undefined);
    await this.page.waitForTimeout(700);

    // Check if Google Flow Settings panel opened with Save button
    const saveBtn = this.page.locator("button.settings-save-button").first();
    if (await saveBtn.isVisible().catch(() => false)) {
      if (job.ratio) {
        const ratioToggle = this.page.locator(".mat-button-toggle-button").filter({ hasText: new RegExp(job.ratio) }).last();
        if (await ratioToggle.count()) await ratioToggle.click().catch(() => undefined);
      }
      if (job.model) {
        const picker = job.type === "video"
          ? this.page.locator("button.video-model-picker-button").first()
          : this.page.locator("button.image-model-picker-button").first();
        if (await picker.count()) {
          await picker.click().catch(() => undefined);
          await this.page.waitForTimeout(500);
          const modelItem = this.page.locator("[role=menuitem], button").filter({ hasText: new RegExp(job.model.replace(/[-_.]/g, ".*"), "i") }).first();
          if (await modelItem.count()) await modelItem.click().catch(() => undefined);
          await this.page.waitForTimeout(300);
          await dismissOpenLayers(this.page);
        }
      }
      await saveBtn.click({ force: true }).catch(() => undefined);
      await this.page.waitForTimeout(800);
      return;
    }

    // Mode first — switching it changes which ratios/durations/models are offered.
    await pickOption(this.page, job.type === "video" ? /Video$/ : /Image$/);
    await this.page.waitForTimeout(400);

    // Video input mode: Frames (first/last frame images) vs Ingredients (text-to-video).
    if (job.type === "video") {
      const wantsFrames = Boolean(job.startFrame || job.endFrame);
      await pickOption(this.page, wantsFrames ? /Frames$/ : /Ingredients$/);
      await this.page.waitForTimeout(300);
    }

    if (job.ratio && RATIO_ICON[job.ratio]) await pickOption(this.page, new RegExp(`^${RATIO_ICON[job.ratio]}`));
    if (job.type === "video" && job.duration) await pickOption(this.page, new RegExp(`^${job.duration}s$`));
    await pickOption(this.page, job.outputs === 1 ? /^1x$/ : new RegExp(`^x${job.outputs}$`));
    if (job.model) {
      // pickModel's retry dismisses every layer, including this popover — hand it a way back in.
      await pickModel(this.page, job.model, async () => {
        await targetSettings.click({ force: true }).catch(() => undefined);
        await this.page.waitForTimeout(700);
      });
    }

    // The model dropdown and the settings popover are separate layers; a single Escape can
    // leave one of them open over the prompt box, so close them all.
    await dismissOpenLayers(this.page);
  }

  /**
  * Clears any attached ingredients currently in the prompt box tray.
  */
  async clearIngredients(): Promise<void> {
    const removeButtons = this.page.locator(
      '[data-testid="remove-ingredient"], button[aria-label*="Remove ingredient" i], [data-testid="ingredient-chip"] button, .ingredient-chip button, [data-slot="ingredients"] button[aria-label*="remove" i], .ingredients-container button[aria-label*="remove" i]'
    );
    const count = await removeButtons.count();
    for (let i = 0; i < count; i++) {
      await removeButtons.first().click().catch(() => undefined);
      await this.page.waitForTimeout(150);
    }
  }

  /**
   * Clears any start or end frame currently set in the prompt box.
   */
  async clearFrame(slot: "Start" | "End"): Promise<void> {
    const slotKey = slot.toLowerCase();
    const removeBtn = this.page
      .locator(`[data-slot="${slotKey}"] button[aria-label*="remove" i], button[aria-label*="remove ${slotKey}" i]`)
      .or(this.page.locator(`[data-slot="${slotKey}"] button`).filter({ hasText: /close|clear/i }))
      .first();

    if (await removeBtn.isVisible().catch(() => false)) {
      await removeBtn.click().catch(() => undefined);
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Uploads background environment plates and isolated prop assets into the Ingredients drawer.
   */
  async uploadIngredients(ingredientPaths: string[]): Promise<void> {
    if (!ingredientPaths || ingredientPaths.length === 0) return;

    // Clear previous ingredients if reusing an existing project/session
    await this.clearIngredients().catch(() => undefined);

    for (const filePath of ingredientPaths) {
      await dismissOpenLayers(this.page);

      // 1. Click Add Media / Ingredient button
      const addBtn = this.page
        .locator('button[aria-haspopup="dialog"]')
        .filter({ hasText: /add(_2)?/i })
        .or(this.page.locator('button[aria-label*="Add ingredient" i]'))
        .first();

      if ((await addBtn.count()) === 0) {
        throw new Error("Could not find Add Media / Ingredient button in Flow prompt area.");
      }

      await addBtn.click().catch(() => undefined);

      const dialog = this.page.locator("[role=dialog],[aria-modal=true],.cdk-overlay-pane,.flow-menu-panel").first();
      await dialog.waitFor({ state: "visible", timeout: 10000 });

      // 2. Click Upload Media and handle file chooser
      const uploadButton = dialog.locator("button").filter({ hasText: /upload media|upload/i }).first();
      await uploadButton.waitFor({ state: "visible", timeout: 10000 });

      const [chooser] = await Promise.all([
        this.page.waitForEvent("filechooser", { timeout: 15000 }),
        uploadButton.click()
      ]);
      await chooser.setFiles(filePath);
      await this.page.waitForTimeout(1000);

      const agreeBtn = this.page.locator("button").filter({ hasText: /I agree/i }).first();
      if (await agreeBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
        await agreeBtn.click().catch(() => undefined);
        await this.page.waitForTimeout(1500);
      }

      // 3. Confirm addition to prompt: Click "Add to prompt" if available, else select tile & confirmPicker
      const addToPrompt = this.page
        .locator("button.detail-add-to-prompt-btn")
        .or(dialog.locator("button").filter({ hasText: /add to (prompt|scene)|^add$/i }))
        .first();
      if (await addToPrompt.isVisible({ timeout: 10000 }).catch(() => false)) {
        await addToPrompt.click().catch(() => undefined);
      } else {
        const selected = dialog.locator('[role=option][aria-selected="true"]').first();
        await selected.waitFor({ state: "visible", timeout: 15000 }).catch(async () => {
          await dialog.locator("[role=option]").first().click().catch(() => undefined);
        });
        await confirmPicker(this.page, dialog);
      }

      await dismissOpenLayers(this.page);

      // 5. Wait for thumbnail confirmation in DOM
      const attachedThumbnail = this.page
        .locator('[data-testid="ingredient-chip"], [aria-label*="ingredient" i], .ingredient-chip, [role="group"] img, .base-prompt-box img')
        .last();
      await attachedThumbnail.waitFor({ state: "visible", timeout: 10000 }).catch(() => undefined);
    }
  }

  // Frames mode: fill the Start/End frame slot.
  // Supports empty slots and clears previously filled slots to allow scene chaining.
  private async uploadFrame(slot: "Start" | "End", filePath: string): Promise<void> {
    const slotKey = slot.toLowerCase();

    // 1. Check if the slot is already filled from an earlier job; if so, clear it
    await this.clearFrame(slot);

    // 2. Locate the slot trigger (empty slot or container)
    const slotEl = this.page
      .locator(`button, [role="button"], [data-slot="${slotKey}"]`)
      .filter({ hasText: new RegExp(`^${slot}(?:\\s*frame)?$`, "i") })
      .or(this.page.locator(`[data-slot="${slotKey}"]`))
      .first();

    if ((await slotEl.count()) === 0 || !(await slotEl.isVisible().catch(() => false))) {
      await this.uploadIngredients([filePath]);
      return;
    } else {
      await slotEl.click().catch(() => undefined);
    }

    await dismissOpenLayers(this.page);
    const dialog = this.page.locator("[role=dialog],[aria-modal=true],.cdk-overlay-pane,.flow-menu-panel").first();
    await dialog.waitFor({ state: "visible", timeout: 10000 }).catch(() => undefined);

    const uploadButton = dialog.locator("button").filter({ hasText: /upload media|upload/i }).first();
    const [chooser] = await Promise.all([
      this.page.waitForEvent("filechooser", { timeout: 15000 }),
      uploadButton.click()
    ]);
    await chooser.setFiles(filePath);
    await this.page.waitForTimeout(1000);

    const agreeBtn = this.page.locator("button").filter({ hasText: /I agree/i }).first();
    if (await agreeBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await agreeBtn.click().catch(() => undefined);
      await this.page.waitForTimeout(1500);
    }

    const addToPrompt = this.page
      .locator("button.detail-add-to-prompt-btn")
      .or(dialog.locator("button").filter({ hasText: /add to (prompt|scene|frame)|^add$/i }))
      .first();
    if (await addToPrompt.isVisible({ timeout: 10000 }).catch(() => false)) {
      await addToPrompt.click().catch(() => undefined);
    } else {
      // The freshly uploaded image is auto-selected; wait for that, falling back to selecting
      // the first tile if needed, then confirm.
      const selected = dialog.locator('[role=option][aria-selected="true"]').first();
      await selected.waitFor({ state: "visible", timeout: 15000 }).catch(async () => {
        await dialog.locator("[role=option]").first().click().catch(() => undefined);
      });
      await confirmPicker(this.page, dialog);
    }

    await dismissOpenLayers(this.page);

    const frameThumbnail = this.page.locator(`[data-slot="${slotKey}"] img, [aria-label*="${slotKey} frame" i] img, .base-prompt-box img`).first();
    await frameThumbnail.waitFor({ state: "visible", timeout: 10000 }).catch(() => undefined);
  }

  // Reference a saved character in the current generation.
  private async referenceCharacter(name: string): Promise<void> {
    await this.characters.tagCharacter(name);
  }

  private async fillPrompt(prompt: string): Promise<void> {
    const box = flowLocators(this.page).promptBox.first();
    // A leftover popover layer over the prompt box swallows the click; clear layers first,
    // and if a click is still intercepted, clear again and fall back to focusing directly.
    await dismissOpenLayers(this.page);
    // Short timeout: layers were just dismissed, so a still-intercepted click should reach
    // the recovery path quickly instead of burning the full 20s session default.
    await box.click({ timeout: 2000 }).catch(async () => {
      await dismissOpenLayers(this.page);
      await box.click({ timeout: 5000 }).catch(() => box.evaluate((el) => (el as HTMLElement).focus()));
    });
    // Clear any existing text (sequential/batch jobs reuse the same prompt box) with real
    // key events, then type so the contenteditable's framework registers the input.
    await box.press("ControlOrMeta+a").catch(() => undefined);
    await box.press("Backspace").catch(() => undefined);
    try {
      await this.page.keyboard.insertText(prompt);
    } catch {
      await box.pressSequentially(prompt, { delay: 0, timeout: 60000 });
    }
  }

  private async submit(): Promise<void> {
    const box = flowLocators(this.page).promptBox.first();
    await box.press("Enter").catch(() => undefined);

    const submit = flowLocators(this.page).submitButton.first();
    if (await submit.isVisible({ timeout: 2000 }).catch(() => false)) {
      await submit.click({ force: true }).catch(() => undefined);
    }

    // Handle Flow agent permission/approval prompt ("Would you like me to kick off this 1 video generation...")
    const approveBtn = this.page
      .locator('[role=radio][aria-label="Always approve"], [role=radio][aria-label="Approve"], button:has-text("Always approve"), button:has-text("Approve")')
      .first();
    if (await approveBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await approveBtn.click().catch(() => undefined);
    }
  }

  private async waitForResults(before: Set<string>, expected: number, timeoutMs: number, type: "image" | "video"): Promise<string[]> {
    const locators = flowLocators(this.page);
    const deadline = Date.now() + timeoutMs;
    const initialFailures = await locators.failedMarker.count();
    const initialBlocks = await locators.blockedMarker.count();

    let approved = false;
    while (Date.now() < deadline) {
      if (!approved) {
        const approveBtn = this.page
          .locator('[role=radio][aria-label="Always approve"], [role=radio][aria-label="Approve"], button:has-text("Always approve"), button:has-text("Approve")')
          .last();
        if (await approveBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
          await approveBtn.click().catch(() => undefined);
          approved = true;
        }
      }

      if (await locators.rateLimitMarker.first().isVisible().catch(() => false)) {
        throw new RateLimitedError("Flow displayed a rate limit or unusual activity message.");
      }
      if (await locators.creditMarker.first().isVisible().catch(() => false)) {
        throw new CreditLimitError("Flow displayed a credit or quota message.");
      }
      if ((await locators.blockedMarker.count()) > initialBlocks && (await locators.blockedMarker.last().isVisible().catch(() => false))) {
        throw new GenerationBlockedError("Flow displayed a policy block message.");
      }
      if ((await locators.failedMarker.count()) > initialFailures && (await locators.failedMarker.last().isVisible().catch(() => false))) {
        throw new GenerationFailedError("Flow displayed a generation failed message.");
      }
      if (await this.page.locator("flow-error-tile, .error-tile, .chat-error-card").first().isVisible().catch(() => false)) {
        const errorText = await this.page.locator("flow-error-tile, .error-tile, .chat-error-card").first().textContent().catch(() => "");
        throw new GenerationFailedError(`Flow displayed a generation failed message: ${errorText}`);
      }

      const added = (await this.resultSrcs(type)).filter((src) => !before.has(src));
      if (added.length >= expected) return added.slice(0, expected);
      await this.page.waitForTimeout(1500);
    }

    const added = (await this.resultSrcs(type)).filter((src) => !before.has(src));
    if (added.length > 0) return added;
    throw new GenerationFailedError(`Timed out waiting for ${expected} result(s).`);
  }
}
