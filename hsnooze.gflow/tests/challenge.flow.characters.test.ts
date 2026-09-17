import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, beforeAll, afterAll } from "vitest";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";
import { CharacterPage } from "../src/flow/characters.js";
import { FlowPage } from "../src/flow/page.js";

describe("Empirical Challenge: Character & Frame Automation Stress Harness", () => {
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
            <div><a href="/fx/tools/flow/project/proj-multi-grid">proj-multi-grid</a></div>
            <div><a href="/fx/tools/flow/project/proj-names">proj-names</a></div>
          </div>
        `
      });
    });

    // Mock project editor and character routes
    await context.route("**/fx/tools/flow/project/**", async (route) => {
      const url = route.request().url();

      if (url.includes("/proj-multi-grid/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div class="characters-grid">
              <div data-character-id="c1" class="character-card">
                <img alt="Alice" src="https://example.test/alice.png" />
                <h3>Alice</h3>
                <button id="pin-alice" aria-label="Pin Alice" aria-pressed="false">push_pin</button>
              </div>
              <div data-character-id="c2" class="character-card">
                <img alt="Bob" src="https://example.test/bob.png" />
                <h3>Bob</h3>
                <button id="pin-bob" aria-label="Pin Bob" aria-pressed="false">push_pin</button>
              </div>
              <div data-character-id="c3" class="character-card">
                <img alt="Charlie" src="https://example.test/charlie.png" />
                <h3>Charlie</h3>
                <button id="pin-charlie" aria-label="Unpin Charlie" aria-pressed="true">push_pin</button>
              </div>
              <div data-character-id="c4" class="character-card">
                <img alt="David" src="https://example.test/david.png" />
                <h3>David</h3>
                <button id="pin-david" aria-label="Pin David" aria-pressed="false">push_pin</button>
              </div>
            </div>
            <script>
              window.__clicks = { alice: 0, bob: 0, charlie: 0, david: 0 };
              document.getElementById("pin-alice").onclick = () => { window.__clicks.alice++; };
              document.getElementById("pin-bob").onclick = () => { window.__clicks.bob++; };
              document.getElementById("pin-charlie").onclick = () => { window.__clicks.charlie++; };
              document.getElementById("pin-david").onclick = () => { window.__clicks.david++; };
            </script>
          `
        });
      }

      if (url.includes("/proj-names/characters")) {
        return route.fulfill({
          contentType: "text/html",
          body: `
            <div class="characters-grid">
              <div data-character-id="c1" class="character-card">
                <h3>Bobby</h3>
                <button id="pin-bobby" aria-label="Pin Bobby" aria-pressed="false">push_pin</button>
              </div>
              <div data-character-id="c2" class="character-card">
                <h3>Bob</h3>
                <button id="pin-bob" aria-label="Pin Bob" aria-pressed="false">push_pin</button>
              </div>
            </div>
            <script>
              window.__nameClicks = { bobby: 0, bob: 0 };
              document.getElementById("pin-bobby").onclick = () => { window.__nameClicks.bobby++; };
              document.getElementById("pin-bob").onclick = () => { window.__nameClicks.bob++; };
            </script>
          `
        });
      }

      return route.fulfill({
        contentType: "text/html",
        body: `
          <div role="textbox" class="ProseMirror"></div>
        `
      });
    });
  });

  afterAll(async () => {
    await browser?.close();
  });

  describe("1. Pin Toggling Precision with Multi-Card Grid", () => {
    it("pins target character Bob without clicking Alice, Charlie, or David", async () => {
      const charPage = new CharacterPage(page);
      await charPage.setCharacterPin("Bob", true, "proj-multi-grid");

      const clicks = await page.evaluate(() => (window as unknown as { __clicks: Record<string, number> }).__clicks);
      expect(clicks.bob).toBe(1);
      expect(clicks.alice).toBe(0);
      expect(clicks.charlie).toBe(0);
      expect(clicks.david).toBe(0);
    });

    it("unpins Charlie without affecting other characters", async () => {
      const charPage = new CharacterPage(page);
      await charPage.setCharacterPin("Charlie", false, "proj-multi-grid");

      const clicks = await page.evaluate(() => (window as unknown as { __clicks: Record<string, number> }).__clicks);
      expect(clicks.charlie).toBe(1);
      expect(clicks.alice).toBe(0);
      expect(clicks.bob).toBe(0);
      expect(clicks.david).toBe(0);
    });

    it("does not trigger click when target character already matches targetPinned state", async () => {
      const charPage = new CharacterPage(page);
      // Charlie is already pinned in the mock HTML (aria-pressed="true")
      await charPage.setCharacterPin("Charlie", true, "proj-multi-grid");

      const clicks = await page.evaluate(() => (window as unknown as { __clicks: Record<string, number> }).__clicks);
      expect(clicks.charlie).toBe(0);
      expect(clicks.alice).toBe(0);
      expect(clicks.bob).toBe(0);
      expect(clicks.david).toBe(0);
    });

    it("evaluates prefix substring behavior when Bobby precedes Bob in DOM", async () => {
      const charPage = new CharacterPage(page);
      await charPage.setCharacterPin("Bob", true, "proj-names");

      const nameClicks = await page.evaluate(() => (window as unknown as { __nameClicks: Record<string, number> }).__nameClicks);
      // Log / verify empirical result
      console.log("Empirical prefix match result for Bob vs Bobby:", nameClicks);
      expect(nameClicks).toBeDefined();
    });
  });

  describe("2. clearIngredients Scoping vs Simultaneous Start and End Frame Buttons", () => {
    it("clears multiple ingredient chips while strictly preserving simultaneous Start and End frame buttons", async () => {
      await page.setContent(`
        <div id="editor">
          <!-- Diverse ingredient chips in tray -->
          <div class="ingredients-container">
            <button data-testid="remove-ingredient" id="ing-btn-1">x</button>
            <button aria-label="Remove ingredient" id="ing-btn-2">x</button>
            <div data-testid="ingredient-chip"><button id="ing-btn-3">x</button></div>
            <div class="ingredient-chip"><button id="ing-btn-4">x</button></div>
            <div data-slot="ingredients"><button aria-label="remove ingredient" id="ing-btn-5">x</button></div>
            <div class="ingredients-container"><button aria-label="remove item" id="ing-btn-6">x</button></div>
          </div>

          <!-- Start Frame slot with remove button -->
          <div data-slot="start" class="frame-slot">
            <img src="start.png" />
            <button id="start-frame-rm" aria-label="Remove start frame">close</button>
          </div>

          <!-- End Frame slot with remove button -->
          <div data-slot="end" class="frame-slot">
            <img src="end.png" />
            <button id="end-frame-rm" aria-label="Remove end frame">close</button>
          </div>
        </div>
        <script>
          window.__frameClicked = { start: false, end: false };
          document.getElementById("start-frame-rm").onclick = () => { window.__frameClicked.start = true; };
          document.getElementById("end-frame-rm").onclick = () => { window.__frameClicked.end = true; };

          // Remove ingredient elements on click
          for (let i = 1; i <= 6; i++) {
            const el = document.getElementById("ing-btn-" + i);
            if (el) el.onclick = function() { this.remove(); };
          }
        </script>
      `);

      const flowPage = new FlowPage(page);
      await flowPage.clearIngredients();

      // Check ingredient buttons were all clicked and removed
      for (let i = 1; i <= 6; i++) {
        expect(await page.locator(`#ing-btn-${i}`).count()).toBe(0);
      }

      // Check frame remove buttons were NEVER clicked
      const frameClicks = await page.evaluate(() => (window as unknown as { __frameClicked: { start: boolean; end: boolean } }).__frameClicked);
      expect(frameClicks.start).toBe(false);
      expect(frameClicks.end).toBe(false);

      // Check frame buttons are still present in DOM
      expect(await page.locator("#start-frame-rm").count()).toBe(1);
      expect(await page.locator("#end-frame-rm").count()).toBe(1);
    });

    it("clearFrame specifically removes only the targeted frame slot without collateral damage", async () => {
      await page.setContent(`
        <div data-slot="start">
          <button id="start-rm" aria-label="Remove start frame">close</button>
        </div>
        <div data-slot="end">
          <button id="end-rm" aria-label="Remove end frame">close</button>
        </div>
        <div data-slot="ingredients">
          <button id="ing-rm" aria-label="remove ingredient">x</button>
        </div>
        <script>
          window.__removed = { start: false, end: false, ing: false };
          document.getElementById("start-rm").onclick = function() { window.__removed.start = true; this.remove(); };
          document.getElementById("end-rm").onclick = function() { window.__removed.end = true; this.remove(); };
          document.getElementById("ing-rm").onclick = function() { window.__removed.ing = true; this.remove(); };
        </script>
      `);

      const flowPage = new FlowPage(page);

      // Clear Start Frame
      await flowPage.clearFrame("Start");
      let removed = await page.evaluate(() => (window as unknown as { __removed: Record<string, boolean> }).__removed);
      expect(removed.start).toBe(true);
      expect(removed.end).toBe(false);
      expect(removed.ing).toBe(false);
      expect(await page.locator("#start-rm").count()).toBe(0);
      expect(await page.locator("#end-rm").count()).toBe(1);
      expect(await page.locator("#ing-rm").count()).toBe(1);

      // Clear End Frame
      await flowPage.clearFrame("End");
      removed = await page.evaluate(() => (window as unknown as { __removed: Record<string, boolean> }).__removed);
      expect(removed.end).toBe(true);
      expect(removed.ing).toBe(false);
      expect(await page.locator("#end-rm").count()).toBe(0);
      expect(await page.locator("#ing-rm").count()).toBe(1);
    });
  });

  describe("3. Sequential Job Execution: Frame and Ingredient Reset", () => {
    it("clears leftover Start/End frames and ingredients when Job 2 omits them", async () => {
      // Simulate state left behind by Job 1 (both frames and ingredient present)
      await page.setContent(`
        <div id="app">
          <div role="textbox" class="ProseMirror"></div>
          <button data-testid="submit-btn" aria-label="Submit">Submit</button>

          <!-- Leftover Start and End frames from Job 1 -->
          <div data-slot="start">
            <img src="job1-start.png" />
            <button id="job1-start-rm" aria-label="Remove start frame">x</button>
          </div>
          <div data-slot="end">
            <img src="job1-end.png" />
            <button id="job1-end-rm" aria-label="Remove end frame">x</button>
          </div>

          <!-- Leftover ingredient from Job 1 -->
          <div class="ingredients-container">
            <div class="ingredient-chip">
              <span>plate.png</span>
              <button id="job1-ing-rm" aria-label="Remove ingredient">x</button>
            </div>
          </div>
        </div>

        <script>
          window.__cleared = { start: false, end: false, ing: false };
          document.getElementById("job1-start-rm").onclick = function() {
            window.__cleared.start = true;
            this.parentElement.remove();
          };
          document.getElementById("job1-end-rm").onclick = function() {
            window.__cleared.end = true;
            this.parentElement.remove();
          };
          document.getElementById("job1-ing-rm").onclick = function() {
            window.__cleared.ing = true;
            this.closest('.ingredient-chip').remove();
          };
        </script>
      `);

      const flowPage = new FlowPage(page);

      // Verify sequential reset operations invoked when job omits frames & ingredients
      await flowPage.clearFrame("Start");
      await flowPage.clearFrame("End");
      await flowPage.clearIngredients();

      const cleared = await page.evaluate(() => (window as unknown as { __cleared: Record<string, boolean> }).__cleared);
      expect(cleared.start).toBe(true);
      expect(cleared.end).toBe(true);
      expect(cleared.ing).toBe(true);

      // Verify DOM is now free of leftover frames and ingredients
      expect(await page.locator("#job1-start-rm").count()).toBe(0);
      expect(await page.locator("#job1-end-rm").count()).toBe(0);
      expect(await page.locator("#job1-ing-rm").count()).toBe(0);
    });

    it("verifies runJob full flow resets leftover frames and ingredients for image job", async () => {
      const FIXTURE = `file://${process.cwd()}/fixtures/flow/index.html`;
      const profileDir = await mkdtemp(join(tmpdir(), "gflow-seq-profile-"));
      const outDir = await mkdtemp(join(tmpdir(), "gflow-seq-output-"));

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

        // Inject simulated leftovers from prior job into the fixture page
        await fixturePage.evaluate(() => {
          const container = document.body;
          const leftovers = document.createElement("div");
          leftovers.id = "leftovers";
          leftovers.innerHTML = `
            <div data-slot="start">
              <button id="res-start" aria-label="Remove start frame">x</button>
            </div>
            <div data-slot="end">
              <button id="res-end" aria-label="Remove end frame">x</button>
            </div>
            <div data-testid="ingredient-chip">
              <button id="res-ing" aria-label="Remove ingredient">x</button>
            </div>
          `;
          container.appendChild(leftovers);

          (window as unknown as { __seqCleared: Record<string, boolean> }).__seqCleared = { start: false, end: false, ing: false };
          const sBtn = document.getElementById("res-start");
          if (sBtn) sBtn.onclick = () => {
            (window as unknown as { __seqCleared: Record<string, boolean> }).__seqCleared.start = true;
            sBtn.remove();
          };
          const eBtn = document.getElementById("res-end");
          if (eBtn) eBtn.onclick = () => {
            (window as unknown as { __seqCleared: Record<string, boolean> }).__seqCleared.end = true;
            eBtn.remove();
          };
          const iBtn = document.getElementById("res-ing");
          if (iBtn) iBtn.onclick = () => {
            (window as unknown as { __seqCleared: Record<string, boolean> }).__seqCleared.ing = true;
            iBtn.remove();
          };
        });

        const flow = new FlowPage(fixturePage);

        // Run Job 2: image job with NO frames and NO ingredients
        const res = await flow.runJob({
          job: {
            id: "seq-shot-2",
            type: "image",
            prompt: "Clean room without frames",
            outputs: 1,
            out: outDir,
            ingredients: [],
            character: []
          },
          outDir
        });

        expect(res.jobId).toBe("seq-shot-2");

        const seqCleared = await fixturePage.evaluate(
          () => (window as unknown as { __seqCleared: Record<string, boolean> }).__seqCleared
        );

        // Both frames and ingredients must have been cleared during runJob
        expect(seqCleared.start).toBe(true);
        expect(seqCleared.end).toBe(true);
        expect(seqCleared.ing).toBe(true);
      } finally {
        await fixtureContext.close();
      }
    });

    it("verifies runJob resets frames and ingredients when transitioning between video jobs", async () => {
      const FIXTURE = `file://${process.cwd()}/fixtures/flow/index.html?type=video`;
      const profileDir = await mkdtemp(join(tmpdir(), "gflow-seq-vid-profile-"));
      const outDir = await mkdtemp(join(tmpdir(), "gflow-seq-vid-output-"));

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

        // Inject simulated leftovers from prior video job
        await fixturePage.evaluate(() => {
          const container = document.body;
          const leftovers = document.createElement("div");
          leftovers.id = "leftovers-vid";
          leftovers.innerHTML = `
            <div data-slot="start">
              <button id="vid-res-start" aria-label="Remove start frame">x</button>
            </div>
            <div data-slot="end">
              <button id="vid-res-end" aria-label="Remove end frame">x</button>
            </div>
            <div data-testid="ingredient-chip">
              <button id="vid-res-ing" aria-label="Remove ingredient">x</button>
            </div>
          `;
          container.appendChild(leftovers);

          (window as unknown as { __vidCleared: Record<string, boolean> }).__vidCleared = { start: false, end: false, ing: false };
          const vsBtn = document.getElementById("vid-res-start");
          if (vsBtn) vsBtn.onclick = () => {
            (window as unknown as { __vidCleared: Record<string, boolean> }).__vidCleared.start = true;
            vsBtn.remove();
          };
          const veBtn = document.getElementById("vid-res-end");
          if (veBtn) veBtn.onclick = () => {
            (window as unknown as { __vidCleared: Record<string, boolean> }).__vidCleared.end = true;
            veBtn.remove();
          };
          const viBtn = document.getElementById("vid-res-ing");
          if (viBtn) viBtn.onclick = () => {
            (window as unknown as { __vidCleared: Record<string, boolean> }).__vidCleared.ing = true;
            viBtn.remove();
          };
        });

        const flow = new FlowPage(fixturePage);

        // Run Job 2: video job with NO startFrame, NO endFrame, NO ingredients
        const res = await flow.runJob({
          job: {
            id: "seq-shot-vid-2",
            type: "video",
            prompt: "Video without frames or ingredients",
            outputs: 1,
            out: outDir,
            ingredients: [],
            character: []
          },
          outDir
        });

        expect(res.jobId).toBe("seq-shot-vid-2");

        const vidCleared = await fixturePage.evaluate(
          () => (window as unknown as { __vidCleared: Record<string, boolean> }).__vidCleared
        );

        // In a video job with no startFrame/endFrame/ingredients, all must be cleared
        expect(vidCleared.start).toBe(true);
        expect(vidCleared.end).toBe(true);
        expect(vidCleared.ing).toBe(true);
      } finally {
        await fixtureContext.close();
      }
    });
  });
});
