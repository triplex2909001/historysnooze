import { chromium } from "playwright";
import { flowLocators } from "./dist/src/flow/locators.js";

async function main() {
  console.log("Connecting to CDP...");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:49657");
  const page = browser.contexts()[0].pages()[0];

  console.log("Navigating to fresh project...");
  await page.goto("https://flow.google.com", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);

  const locators = flowLocators(page);
  const newProj = locators.newProjectButton.first();
  await newProj.waitFor({ state: "visible", timeout: 15000 }).catch(() => undefined);
  if (await newProj.count() > 0) {
    console.log("Clicking New Project...");
    await newProj.click();
    await page.waitForTimeout(3000);
  }

  console.log("Current URL:", page.url());

  const box = locators.promptBox.first();
  await box.waitFor({ state: "attached", timeout: 15000 });
  console.log("Prompt box attached!");

  console.log("Typing test prompt for default model...");
  await box.click();
  await page.keyboard.insertText("Majestic snow-capped Mount Fuji reflected in Lake Kawaguchi at golden dawn, Japanese Edo woodblock style, wide 16:9");
  await box.evaluate((el) => el.dispatchEvent(new Event("input", { bubbles: true, cancelable: true })));

  const submit = locators.submitButton.first();
  await page.waitForTimeout(1000);
  console.log("Submitting test prompt...");
  await submit.click();
  console.log("Submitted! Observing response for up to 35 seconds...");

  const t0 = Date.now();
  while (Date.now() - t0 < 35000) {
    await page.waitForTimeout(2000);
    const elapsed = Math.round((Date.now() - t0) / 1000);
    const errorCards = await page.$$eval(".chat-error-card, .error-text", (nodes) => nodes.map(n => n.textContent?.trim()));
    if (errorCards.length > 0) {
      console.log(`[${elapsed}s] RATE LIMIT / USAGE LIMIT STILL ACTIVE:`, errorCards);
      process.exit(2);
    }
    const imgs = await page.$$eval("img", (nodes) => nodes.map(n => n.src).filter(s => s.includes("flow-content") || s.includes("getMediaUrlRedirect")));
    if (imgs.length > 0) {
      console.log(`[${elapsed}s] GENERATION SUCCEEDED! Image:`, imgs[0].slice(0, 80));
      process.exit(0);
    }
    console.log(`[${elapsed}s] Generating...`);
  }

  console.log("Timed out waiting for result.");
  process.exit(1);
}

main().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
