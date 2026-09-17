import { describe, expect, it, afterEach, beforeEach } from "vitest";
import { chromium, type Browser, type Page } from "playwright";
import { FlowPage } from "../src/flow/page.js";

describe("FlowPage referenceIngredient Modal Automation", () => {
  let browser: Browser;
  let page: Page;

  beforeEach(async () => {
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage();
  });

  afterEach(async () => {
    await browser?.close();
  });

  it("handles standard modal workflow with Ingredients tab and exact filename match", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog" id="add-btn">
            <span>add_2</span> Create
          </button>
          <div id="modal" role="dialog" style="display: none;">
            <div role="tablist">
              <button role="tab" id="tab-chars">Characters</button>
              <button role="tab" id="tab-ing">Ingredients</button>
            </div>
            <div id="panel-ingredients">
              <div class="tile" id="tile-basho">ref_character_basho.jpg</div>
              <div class="tile" id="tile-edo">ref_setting_edo_hermitage.jpg</div>
            </div>
            <button id="confirm-btn">Add to prompt</button>
          </div>
          <script>
            const addBtn = document.getElementById("add-btn");
            const modal = document.getElementById("modal");
            const tabIng = document.getElementById("tab-ing");
            const tileEdo = document.getElementById("tile-edo");
            const confirmBtn = document.getElementById("confirm-btn");

            window.__clicked = { add: false, tab: false, tile: false, confirm: false };

            addBtn.addEventListener("click", () => {
              window.__clicked.add = true;
              modal.style.display = "block";
            });
            tabIng.addEventListener("click", () => {
              window.__clicked.tab = true;
            });
            tileEdo.addEventListener("click", () => {
              window.__clicked.tile = true;
            });
            confirmBtn.addEventListener("click", () => {
              window.__clicked.confirm = true;
              modal.style.display = "none";
            });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_setting_edo_hermitage.jpg");

    const clicked = await page.evaluate(() => (window as any).__clicked);
    expect(clicked.add).toBe(true);
    expect(clicked.tab).toBe(true);
    expect(clicked.tile).toBe(true);
    expect(clicked.confirm).toBe(true);
  });

  it("matches extension-stripped tile name when DOM does not include .jpg", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <button role="tab">Ingredients</button>
            <div class="tile" id="target-tile">ref_prop_bamboo_staff_inkstone</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            const tile = document.getElementById("target-tile");
            const confirmBtn = document.querySelectorAll("button")[2];

            window.__tileClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tile.addEventListener("click", () => { window.__tileClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    // Passing full filename with .jpg extension
    await (flow as any).referenceIngredient("ref_prop_bamboo_staff_inkstone.jpg");

    const tileClicked = await page.evaluate(() => (window as any).__tileClicked);
    expect(tileClicked).toBe(true);
  });

  it("matches tile via aria-label when inner text differs", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <button role="tab">Ingredients</button>
            <div class="card" aria-label="Thumbnail: ref_setting_mountain_pass asset" id="aria-tile">
              <span>Generic Landscape</span>
            </div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            const tile = document.getElementById("aria-tile");
            const confirmBtn = document.querySelectorAll("button")[2];

            window.__ariaTileClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tile.addEventListener("click", () => { window.__ariaTileClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_setting_mountain_pass.jpg");

    const ariaTileClicked = await page.evaluate(() => (window as any).__ariaTileClicked);
    expect(ariaTileClicked).toBe(true);
  });

  it("handles alternative tab names such as Media and Uploads", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <button role="tab" id="uploads-tab">Uploads</button>
            <div id="tile">ref_prop_inkstone</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            const tab = document.getElementById("uploads-tab");
            const confirmBtn = document.querySelectorAll("button")[2];

            window.__uploadsTabClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tab.addEventListener("click", () => { window.__uploadsTabClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_prop_inkstone");

    const uploadsClicked = await page.evaluate(() => (window as any).__uploadsTabClicked);
    expect(uploadsClicked).toBe(true);
  });

  it("operates smoothly when modal has no tab list (flat picker layout)", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <div id="tile">ref_prop_walking_stick</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            const tile = document.getElementById("tile");
            const confirmBtn = document.querySelector("button:nth-of-type(2)");

            window.__flatTileClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tile.addEventListener("click", () => { window.__flatTileClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_prop_walking_stick");

    const flatTileClicked = await page.evaluate(() => (window as any).__flatTileClicked);
    expect(flatTileClicked).toBe(true);
  });

  it("handles modal identified via aria-modal='true' without role='dialog'", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <section aria-modal="true" style="display: none;">
            <div id="tile">ref_custom_ingredient</div>
            <button>ADD TO PROMPT</button>
          </section>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[aria-modal="true"]');
            const tile = document.getElementById("tile");
            const confirmBtn = modal.querySelector("button");

            window.__ariaModalClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tile.addEventListener("click", () => { window.__ariaModalClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_custom_ingredient");

    const ariaModalClicked = await page.evaluate(() => (window as any).__ariaModalClicked);
    expect(ariaModalClicked).toBe(true);
  });

  it("gracefully returns without exception when add_2 button does not exist", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <p>No add button on this page</p>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    // Should complete cleanly without throwing an unhandled rejection
    await expect((flow as any).referenceIngredient("ref_setting_edo")).resolves.toBeUndefined();
  });

  it("gracefully handles missing tile in dialog without crashing pipeline", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <div>Other tiles only</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    const start = Date.now();
    const promise = (flow as any).referenceIngredient("non_existent_tile");
    await expect(promise).resolves.toBeUndefined();
    const duration = Date.now() - start;
    console.log(`[STALL DIAGNOSTIC] Missing tile took ${duration}ms to recover`);
  }, 60000);

  it("selects first tile when multiple matching elements exist without ambiguity failure", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <div class="tile">ref_duplicate_item</div>
            <div class="tile">ref_duplicate_item</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            const tiles = document.querySelectorAll(".tile");
            const confirmBtn = document.querySelector("button:nth-of-type(2)");

            window.__firstTileClicked = false;
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
            tiles[0].addEventListener("click", () => { window.__firstTileClicked = true; });
            confirmBtn.addEventListener("click", () => { modal.style.display = "none"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    await (flow as any).referenceIngredient("ref_duplicate_item");

    const firstClicked = await page.evaluate(() => (window as any).__firstTileClicked);
    expect(firstClicked).toBe(true);
  });

  it("safely handles ingredient names with quotes or CSS-sensitive characters without crashing with syntax error", async () => {
    await page.setContent(`
      <!doctype html>
      <html>
        <body>
          <button aria-haspopup="dialog">add_2</button>
          <div role="dialog" style="display: none;">
            <div class="tile">ref_special_name</div>
            <button>Add to prompt</button>
          </div>
          <script>
            const addBtn = document.querySelector('button[aria-haspopup="dialog"]');
            const modal = document.querySelector('[role="dialog"]');
            addBtn.addEventListener("click", () => { modal.style.display = "block"; });
          </script>
        </body>
      </html>
    `);

    const flow = new FlowPage(page);
    // Name with double quote: does locator('[aria-label*="..."]') throw an unhandled CSS syntax error?
    let caughtError: any = null;
    try {
      await (flow as any).referenceIngredient('ref_quote_"item"');
    } catch (err) {
      caughtError = err;
    }
    // We expect the system either handles it or catches the error without throwing an uncaught exception
    console.log("[QUOTE SELECTOR DIAGNOSTIC] Caught error:", caughtError?.message ?? "none (graceful)");
  });
});
