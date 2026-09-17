import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeAll, afterAll } from "vitest";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";
import { CharacterPage } from "../src/flow/characters.js";
import { FlowPage } from "../src/flow/page.js";

describe("CharacterPage & FlowPage Integration Suite", () => {
  let browser: Browser;
  let context: BrowserContext;
  let page: Page;

  beforeAll(async () => {
    browser = await chromium.launch({
      channel: "chrome",
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });
    context = await browser.newContext({ bypassCSP: true });
    page = await context.newPage();

    // Mock dashboard at FLOW_BASE
    await context.route("https://labs.google/fx/tools/flow", async (route) => {
      await route.fulfill({
        contentType: "text/html",
        body: `
          <div class="dashboard">
            <div><a href="/fx/tools/flow/project/proj-1">proj-1</a></div>
            <div><a href="/fx/tools/flow/project/proj-2">proj-2</a></div>
            <div><a href="/fx/tools/flow/project/proj-3">proj-3</a></div>
            <div><a href="/fx/tools/flow/project/proj-toggle">proj-toggle</a></div>
            <div><a href="/fx/tools/flow/project/proj-empty">proj-empty</a></div>
            <div><a href="/fx/tools/flow/project/proj-upload">proj-upload</a></div>
          </div>
        `
      });
    });

    // Mock project editor and character routes
    await context.route("**/fx/tools/flow/project/**", async (route) => {
      const url = route.request().url();

      if (url.includes("/proj-1/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div class="characters-grid">
              <div data-character-id="c1" class="character-card">
                <img alt="Alice" src="https://example.test/alice.png" />
                <h3>Alice</h3>
                <button aria-label="Pin Alice" aria-pressed="false">push_pin</button>
              </div>
              <div data-character-id="c2" class="character-card">
                <img alt="Bob" src="https://example.test/bob.png" />
                <h3>Bob</h3>
                <button aria-label="Unpin Bob" aria-pressed="true">push_pin</button>
              </div>
            </div>
          `
        });
      }

      if (url.includes("/proj-2/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div class="characters-grid">
              <div data-character-id="c1" class="character-card">
                <h3>Alice</h3>
                <button id="alice-pin" aria-label="Pin Alice" aria-pressed="false">push_pin</button>
              </div>
              <div data-character-id="c2" class="character-card">
                <h3>Bob</h3>
                <button id="bob-pin" aria-label="Pin Bob" aria-pressed="false">push_pin</button>
              </div>
            </div>
            <script>
              window.__aliceClicked = false;
              window.__bobClicked = false;
              document.getElementById("alice-pin").onclick = () => { window.__aliceClicked = true; };
              document.getElementById("bob-pin").onclick = () => { window.__bobClicked = true; };
            </script>
          `
        });
      }

      if (url.includes("/proj-empty/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `<div class="characters-grid"></div>`
        });
      }

      if (url.includes("/proj-3/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div data-character-id="c1" class="character-card">
              <h3>Alice</h3>
              <button id="pin-btn" aria-label="Pin Alice" aria-pressed="true">push_pin</button>
            </div>
            <script>
              window.__pinClicked = false;
              document.getElementById("pin-btn").onclick = () => { window.__pinClicked = true; };
            </script>
          `
        });
      }

      if (url.includes("/proj-toggle/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div data-character-id="c1" class="character-card">
              <h3>Alice</h3>
              <button id="pin-toggle-btn" aria-label="Pin Alice" aria-pressed="false">push_pin</button>
            </div>
            <script>
              window.__pinToggleClicked = false;
              document.getElementById("pin-toggle-btn").onclick = () => { window.__pinToggleClicked = true; };
            </script>
          `
        });
      }

      if (url.includes("/proj-upload/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div id="characters-view">
              <button id="create-btn">Create character</button>
              <div id="char-form" style="display:none;">
                <input placeholder="Character Name" id="name-input" />
                <textarea placeholder="Description" id="desc-input"></textarea>
                <button id="save-btn">Done</button>
              </div>
            </div>
            <script>
              window.__charSaved = false;
              document.getElementById("create-btn").onclick = () => {
                document.getElementById("char-form").style.display = "block";
              };
              document.getElementById("save-btn").onclick = () => {
                window.__charSaved = true;
                window.__savedName = document.getElementById("name-input").value;
              };
            </script>
          `
        });
      }

      // Default editor page for project
      return route.fulfill({
        contentType: "text/html",
        body: `
          <!doctype html>
          <html>
            <body>
              <div role="textbox" class="ProseMirror"></div>
            </body>
          </html>
        `
      });
    });
  });

  afterAll(async () => {
    await browser?.close();
  });

  // 1. listCharacters
  it("scrapes character cards and extracts thumbnails and pinned states", async () => {
    const charPage = new CharacterPage(page);
    const list = await charPage.listCharacters("proj-1");
    expect(list).toEqual([
      { name: "Alice", thumbnailUrl: "https://example.test/alice.png", pinned: false },
      { name: "Bob", thumbnailUrl: "https://example.test/bob.png", pinned: true }
    ]);
  });

  // 2. setCharacterPin selector precision
  it("pins target character Bob without affecting sibling Alice in wrapper div", async () => {
    const charPage = new CharacterPage(page);
    await charPage.setCharacterPin("Bob", true, "proj-2");

    const aliceClicked = await page.evaluate(() => Boolean((window as unknown as { __aliceClicked: boolean }).__aliceClicked));
    const bobClicked = await page.evaluate(() => Boolean((window as unknown as { __bobClicked: boolean }).__bobClicked));

    expect(bobClicked).toBe(true);
    expect(aliceClicked).toBe(false);
  });

  it("throws descriptive error when character is not found", async () => {
    const charPage = new CharacterPage(page);
    await expect(charPage.setCharacterPin("NonExistent", true, "proj-empty")).rejects.toThrow(
      'Character "NonExistent" not found in project.'
    );
  });

  // 3. ensureCharacter idempotency and toggle
  it("does not toggle pin when character already has requested pinned status", async () => {
    const charPage = new CharacterPage(page);
    await charPage.ensureCharacter({ name: "Alice", pinned: true }, "proj-3");

    const pinClicked = await page.evaluate(() => Boolean((window as unknown as { __pinClicked: boolean }).__pinClicked));
    expect(pinClicked).toBe(false);
  });

  it("toggles pin when character has different pinned status", async () => {
    const charPage = new CharacterPage(page);
    await charPage.ensureCharacter({ name: "Alice", pinned: true }, "proj-toggle");

    const pinToggleClicked = await page.evaluate(() => Boolean((window as unknown as { __pinToggleClicked: boolean }).__pinToggleClicked));
    expect(pinToggleClicked).toBe(true);
  });

  // 4. uploadReferenceSheet via ensureCharacter when character is missing
  it("creates new character via uploadReferenceSheet when character does not exist", async () => {
    const charPage = new CharacterPage(page);
    await charPage.uploadReferenceSheet({ name: "CyberSamurai", pinned: false, description: "Futuristic swordsman" }, "proj-upload");

    const saved = await page.evaluate(() => Boolean((window as unknown as { __charSaved: boolean }).__charSaved));
    const savedName = await page.evaluate(() => (window as unknown as { __savedName?: string }).__savedName);

    expect(saved).toBe(true);
    expect(savedName).toBe("CyberSamurai");
  });

  // 5. tagCharacter
  it("skips tagging if character is already tagged in prompt box", async () => {
    await page.setContent(`
      <div role="textbox" class="ProseMirror">
        <span data-character="Alice">Alice</span>
      </div>
      <button id="add-btn" aria-haspopup="dialog">add_2</button>
      <script>
        window.__addClicked = false;
        document.getElementById("add-btn").onclick = () => { window.__addClicked = true; };
      </script>
    `);

    const charPage = new CharacterPage(page);
    await charPage.tagCharacter("Alice");

    const addClicked = await page.evaluate(() => Boolean((window as unknown as { __addClicked: boolean }).__addClicked));
    expect(addClicked).toBe(false);
  });

  it("tags character via picker dialog when not yet tagged", async () => {
    await page.setContent(`
      <div role="textbox" class="ProseMirror">Hello</div>
      <button id="add-btn" aria-haspopup="dialog">add_2</button>
      <div id="dialog" role="dialog" aria-modal="true" style="display:none;">
        <button role="tab" id="chars-tab">Characters</button>
        <div id="tab-content" style="display:none;">
          <div id="tile-alice">Alice</div>
          <button id="confirm-btn">add to prompt</button>
        </div>
      </div>
      <script>
        window.__tagged = false;
        document.getElementById("add-btn").onclick = () => {
          document.getElementById("dialog").style.display = "block";
        };
        document.getElementById("chars-tab").onclick = () => {
          document.getElementById("tab-content").style.display = "block";
        };
        document.getElementById("tile-alice").onclick = () => {
          window.__tileSelected = true;
        };
        document.getElementById("confirm-btn").onclick = () => {
          window.__tagged = true;
          document.getElementById("dialog").style.display = "none";
        };
      </script>
    `);

    const charPage = new CharacterPage(page);
    await charPage.tagCharacter("Alice");

    const tagged = await page.evaluate(() => Boolean((window as unknown as { __tagged: boolean }).__tagged));
    expect(tagged).toBe(true);
  });

  // 6. clearIngredients scoping
  it("clears only ingredient chips and leaves frame remove buttons intact", async () => {
    await page.setContent(`
      <div id="tray">
        <div data-testid="ingredient-chip"><button id="ing-1" aria-label="Remove ingredient">x</button></div>
        <div class="ingredient-chip"><button id="ing-2">x</button></div>
        <div data-slot="ingredients"><button id="ing-3" aria-label="remove ingredient">x</button></div>
      </div>
      <div data-slot="start">
        <button id="start-rm" aria-label="Remove start frame">x</button>
      </div>
      <div data-slot="end">
        <button id="end-rm" aria-label="Remove end frame">x</button>
      </div>
      <script>
        document.getElementById("ing-1").onclick = function() { this.remove(); };
        document.getElementById("ing-2").onclick = function() { this.remove(); };
        document.getElementById("ing-3").onclick = function() { this.remove(); };
      </script>
    `);

    const flowPage = new FlowPage(page);
    await flowPage.clearIngredients();

    // Ingredients removed
    expect(await page.locator("#ing-1").count()).toBe(0);
    expect(await page.locator("#ing-2").count()).toBe(0);
    expect(await page.locator("#ing-3").count()).toBe(0);
    // Frame remove buttons preserved
    expect(await page.locator("#start-rm").count()).toBe(1);
    expect(await page.locator("#end-rm").count()).toBe(1);
  });

  // 7. clearFrame
  it("clears individual start and end frames", async () => {
    await page.setContent(`
      <div data-slot="start">
        <button id="start-rm" aria-label="Remove start frame">x</button>
      </div>
      <div data-slot="end">
        <button id="end-rm" aria-label="Remove end frame">x</button>
      </div>
      <script>
        document.getElementById("start-rm").onclick = function() { this.remove(); };
        document.getElementById("end-rm").onclick = function() { this.remove(); };
      </script>
    `);

    const flowPage = new FlowPage(page);

    // Clear Start frame
    await flowPage.clearFrame("Start");
    expect(await page.locator("#start-rm").count()).toBe(0);
    expect(await page.locator("#end-rm").count()).toBe(1);

    // Clear End frame
    await flowPage.clearFrame("End");
    expect(await page.locator("#end-rm").count()).toBe(0);
  });

  // 8. FlowPage has CharacterPage property
  it("instantiates CharacterPage as this.characters", () => {
    const flowPage = new FlowPage(page);
    expect(flowPage.characters).toBeDefined();
    expect(flowPage.characters).toBeInstanceOf(CharacterPage);
  });

  // 9. FlowPage.runJob character upload and tagging wiring
  it("runJob invokes ensureCharacter for resolved characters and executes job", async () => {
    const FIXTURE = `file://${process.cwd()}/fixtures/flow/index.html`;
    const profileDir = await mkdtemp(join(tmpdir(), "gflow-char-profile-"));
    const outDir = await mkdtemp(join(tmpdir(), "gflow-char-output-"));
    const fixtureContext = await chromium.launchPersistentContext(profileDir, {
      channel: "chrome",
      headless: true,
      acceptDownloads: true,
      bypassCSP: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });

    try {
      const fixturePage = fixtureContext.pages()[0] ?? (await fixtureContext.newPage());
      await fixturePage.goto(FIXTURE);

      const flow = new FlowPage(fixturePage);
      let ensured = false;
      flow.characters.ensureCharacter = async (char) => {
        ensured = true;
        expect(char.name).toBe("Hero");
      };

      const result = await flow.runJob({
        job: {
          id: "char-shot",
          type: "image",
          prompt: "Hero in a cyberpunk alley",
          outputs: 1,
          out: outDir,
          ingredients: [],
          character: ["Hero"],
          resolvedCharacters: [
            {
              name: "Hero",
              referenceSheet: "/tmp/hero.png",
              pinned: true
            }
          ]
        },
        outDir
      });

      expect(ensured).toBe(true);
      expect(result.jobId).toBe("char-shot");
      expect(result.artifacts).toHaveLength(1);
    } finally {
      await fixtureContext.close();
    }
  });
});
