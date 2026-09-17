import type { Page } from "playwright";
import type { CharacterAsset } from "../jobs/schema.js";
import { confirmPicker, dismissOpenLayers, navigateToProject, projectSubUrl } from "./ui.js";

export interface CharacterSummary {
  name: string;
  thumbnailUrl?: string;
  pinned?: boolean;
}

export class CharacterPage {
  constructor(private readonly page: Page) {}

  private characterPageUrl(projectId: string): string {
    if (this.page.url().includes("flow.google.com")) {
      return `https://flow.google.com/project/${projectId}/character`;
    }
    return projectSubUrl(projectId, "characters");
  }

  /**
   * Scrapes all characters currently registered in the Flow project.
   */
  async listCharacters(project?: string): Promise<CharacterSummary[]> {
    const onPage = await this.page.evaluate(() => {
      const names = Array.from(document.querySelectorAll(".character-tile-name, .character-item-name, [class*='character-name']"))
        .map((e) => e.textContent?.trim() || "")
        .filter(Boolean);
      return names.map((name) => ({ name, pinned: true }));
    });
    if (onPage.length > 0) return onPage;

    const projectId = await navigateToProject(this.page, project);
    await this.page.goto(this.characterPageUrl(projectId), { waitUntil: "domcontentloaded" });
    await this.page.waitForTimeout(800);

    return this.page.evaluate(() => {
      const results: CharacterSummary[] = [];
      const seen = new Set<string>();

      const cards = [
        ...document.querySelectorAll('a[href*="/character/"], [data-character-id], [role="article"], [data-testid="character-card"], [class*="character-card" i]')
      ];

      for (const card of cards) {
        const img = card.querySelector("img") as HTMLImageElement | null;
        const thumbnailUrl = img?.currentSrc || img?.src || undefined;
        const alt = img?.alt?.trim();

        const nameEl = card.querySelector("figcaption, [class*='name'], h3, h4, span");
        const cardText = (nameEl?.textContent || card.textContent || "")
          .replace(/push_pin|keep|accessibility_new/g, " ")
          .replace(/\s+/g, " ")
          .trim();

        const name = alt && !/generated image|user profile/i.test(alt) ? alt : cardText;
        if (!name || seen.has(name)) continue;
        seen.add(name);

        const pinBtn = card.querySelector("button[aria-label*='pin' i], button:has(.push_pin), button");
        const isPinned = pinBtn
          ? pinBtn.getAttribute("aria-pressed") === "true" ||
            pinBtn.getAttribute("data-pinned") === "true" ||
            pinBtn.classList.contains("pinned") ||
            /unpin/i.test(pinBtn.getAttribute("aria-label") || "")
          : false;

        results.push({ name, thumbnailUrl, pinned: isPinned });
      }

      return results;
    });
  }

  /**
   * Toggles the pinned state of a character card idempotently.
   */
  async setCharacterPin(name: string, targetPinned: boolean, project?: string): Promise<void> {
    const projectId = await navigateToProject(this.page, project);
    await this.page.goto(this.characterPageUrl(projectId), { waitUntil: "domcontentloaded" });
    await this.page.waitForTimeout(600);

    const card = this.page
      .locator('a[href*="/character/"], [data-character-id], [role="article"], [data-testid="character-card"], [data-testid*="character" i], [class*="character-card" i]')
      .filter({ hasText: name })
      .first();

    if ((await card.count()) === 0) {
      throw new Error(`Character "${name}" not found in project.`);
    }

    const pinBtn = card
      .locator("button")
      .filter({ hasText: /push_pin|keep/i })
      .or(card.locator("button[aria-label*='pin' i]"))
      .first();

    if ((await pinBtn.count()) === 0) {
      throw new Error(`Pin button not found on character card for "${name}".`);
    }

    const isCurrentlyPinned = await pinBtn.evaluate((btn) => {
      return (
        btn.getAttribute("aria-pressed") === "true" ||
        btn.getAttribute("data-pinned") === "true" ||
        btn.classList.contains("pinned") ||
        /unpin/i.test(btn.getAttribute("aria-label") || "") ||
        /push_pin_filled/i.test(btn.textContent || "")
      );
    });

    if (isCurrentlyPinned !== targetPinned) {
      await pinBtn.click();
      await this.page.waitForTimeout(400);
    }
  }

  /**
   * Uploads a character reference sheet and configures the character in Flow.
   */
  async uploadReferenceSheet(character: CharacterAsset, project?: string): Promise<void> {
    const projectId = await navigateToProject(this.page, project);
    await this.page.goto(this.characterPageUrl(projectId), { waitUntil: "domcontentloaded" });
    await this.page.waitForTimeout(600);

    // Click "Create character" / "New character" if visible
    const newCharBtn = this.page
      .locator("button")
      .filter({ hasText: /create character|new character|add character/i })
      .first();
    if (await newCharBtn.isVisible().catch(() => false)) {
      await newCharBtn.click();
      await this.page.waitForTimeout(500);
    }

    // Upload Reference Sheet image and turnaround views
    const uploadFiles = [
      ...(character.referenceSheet ? [character.referenceSheet] : []),
      ...(character.images ?? [])
    ];

    for (const filePath of uploadFiles) {
      const uploadBtn = this.page
        .locator("button")
        .filter({ hasText: /upload|add reference|add image/i })
        .first();

      if (await uploadBtn.isVisible().catch(() => false)) {
        const [chooser] = await Promise.all([
          this.page.waitForEvent("filechooser", { timeout: 15000 }),
          uploadBtn.click()
        ]);
        await chooser.setFiles(filePath);
        await this.page.waitForTimeout(1000);
        const agreeBtn = this.page.locator("button").filter({ hasText: /I agree/i }).first();
        if (await agreeBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
          await agreeBtn.click().catch(() => undefined);
          await this.page.waitForTimeout(1000);
        }
      }
    }

    // Character Name
    const nameInput = this.page
      .locator('input[placeholder*="Character name" i], input[placeholder*="Untitled character" i], input[aria-label*="Character name" i], input.name-input, input.editable-text-input')
      .first();
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.fill("");
      await nameInput.fill(character.name);
      await nameInput.press("Enter").catch(() => undefined);
    } else {
      const editBtn = this.page.locator('button:has(mat-icon:has-text("edit")), button[aria-label*="edit" i]').first();
      if (await editBtn.isVisible().catch(() => false)) {
        await editBtn.click().catch(() => undefined);
        await this.page.waitForTimeout(400);
        const editableInput = this.page.locator('input.editable-text-input, input.name-input').first();
        if (await editableInput.isVisible().catch(() => false)) {
          await editableInput.fill("");
          await editableInput.fill(character.name);
          await editableInput.press("Enter").catch(() => undefined);
        }
      }
    }

    // Character Description
    if (character.description) {
      const descInput = this.page
        .locator('textarea[placeholder*="how your character acts" i], textarea[placeholder*="Description" i]')
        .first();
      if (await descInput.isVisible().catch(() => false)) {
        await descInput.fill(character.description);
      }
    }

    // Voice
    if (character.voice) {
      const voiceBtn = this.page.locator("button").filter({ hasText: /select a voice/i }).first();
      if (await voiceBtn.isVisible().catch(() => false)) {
        await voiceBtn.click();
        const voiceOpt = this.page.locator("[role=option]").filter({ hasText: character.voice }).first();
        await voiceOpt.click().catch(() => undefined);
        const addBtn = this.page.locator("button").filter({ hasText: /add to character/i }).first();
        await addBtn.click().catch(() => undefined);
      }
    }

    // Wait for reference image progress to complete if indicator is visible
    const progress = this.page.locator("text=/%/");
    if (await progress.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await progress.first().waitFor({ state: "hidden", timeout: 45000 }).catch(() => undefined);
    }
    await this.page.waitForTimeout(1500);

    // Save / Done
    const doneBtn = this.page.locator("button").filter({ hasText: /^Done$|^Save$/i }).first();
    if (await doneBtn.isVisible().catch(() => false)) {
      await doneBtn.click();
      await this.page.waitForTimeout(1500);
    }

    // Toggle Pin state if requested
    if (character.pinned) {
      try {
        await this.setCharacterPin(character.name, true, project);
      } catch {
        // When card is not yet rendered in DOM (e.g. real Google Flow before model generation), continue gracefully
      }
    }
  }

  /**
   * Ensures a character asset is registered in Flow and pinned if required.
   */
  async ensureCharacter(character: CharacterAsset, project?: string): Promise<void> {
    const existing = await this.listCharacters(project);
    const match = existing.find((c) => c.name.toLowerCase() === character.name.toLowerCase());

    if (!match) {
      await this.uploadReferenceSheet(character, project);
    } else if (character.pinned !== undefined && match.pinned !== character.pinned) {
      try {
        await this.setCharacterPin(character.name, character.pinned, project);
      } catch {
        // Pin state is best-effort on web Flow
      }
    }
  }

  /**
   * Tags a character into the active generation prompt bar.
   */
  async tagCharacter(name: string): Promise<void> {
    try {
      const isAlreadyTagged = await this.page
        .locator('.ProseMirror, [role="textbox"]')
        .locator(`[data-character="${name}"], [data-character-id], .character-chip, .mention-chip, [data-mention="${name}"], span[contenteditable="false"]:has-text("${name}")`)
        .first()
        .isVisible()
        .catch(() => false);

      if (isAlreadyTagged) return;

      const addBtn = this.page
        .locator('button[aria-haspopup="dialog"], button.add-menu-trigger')
        .filter({ hasText: /add(_2)?/i })
        .or(this.page.locator('button[aria-label*="Add ingredient" i]'))
        .first();
      if ((await addBtn.count()) === 0) return;
      await addBtn.click().catch(() => undefined);

      const dialog = this.page.locator("[role=dialog],[aria-modal=true],.cdk-overlay-pane,.flow-menu-panel").first();
      if (!(await dialog.isVisible({ timeout: 5000 }).catch(() => false))) {
        await dismissOpenLayers(this.page);
        return;
      }

      const charsTab = dialog.locator("button,[role=tab]").filter({ hasText: /Characters/i }).first();
      if (await charsTab.isVisible().catch(() => false)) {
        await charsTab.click().catch(() => undefined);
        await this.page.waitForTimeout(400);
      }

      const tile = dialog
        .locator("button, [role=menuitem], [role=option], div")
        .filter({ hasText: new RegExp(`^${name}|${name}Character`, "i") })
        .first();
      if (await tile.isVisible({ timeout: 4000 }).catch(() => false)) {
        await tile.click().catch(() => undefined);
        await confirmPicker(this.page, dialog);
      }
      await dismissOpenLayers(this.page);
    } catch {
      await dismissOpenLayers(this.page).catch(() => undefined);
    }
  }
}
