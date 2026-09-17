import { readFileSync } from "fs";
import { join } from "path";
import { chromium } from "playwright";

async function main() {
  const profileDir = process.env.GFLOW_DEFAULT_PROFILE_DIR || "/media/vpsg24gb/DATA/gflow/.gflow/profiles/default";
  const portStr = readFileSync(join(profileDir, "DevToolsActivePort"), "utf8").split("\n")[0].trim();
  const port = parseInt(portStr, 10);
  console.log("Connecting to CDP port:", port);
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const context = browser.contexts()[0];
  const page = context.pages().find(p => p.url().includes("google.com")) || context.pages()[0];

  console.log("Current URL before click:", page.url());

  // Click New Project if on dashboard
  const newProjectBtn = page.getByRole("button", { name: /new project/i }).first();
  if (await newProjectBtn.isVisible()) {
    console.log("Clicking New Project button...");
    await newProjectBtn.click();
    await page.waitForTimeout(5000);
  }

  console.log("Current URL after click:", page.url());
  console.log("Current Title:", await page.title());

  // Dump textboxes, textareas, inputs, editable elements
  const editables = await page.$$eval("[contenteditable], textarea, input, [role=textbox], p, div", els => {
    return els
      .filter(el => {
        const ph = el.getAttribute("placeholder") || "";
        const role = el.getAttribute("role") || "";
        const ce = el.getAttribute("contenteditable") || "";
        const txt = el.textContent || "";
        return ph || role === "textbox" || ce === "true" || txt.includes("create") || txt.includes("prompt") || txt.includes("What");
      })
      .map(el => ({
        tag: el.tagName,
        role: el.getAttribute("role"),
        contenteditable: el.getAttribute("contenteditable"),
        placeholder: el.getAttribute("placeholder"),
        ariaLabel: el.getAttribute("aria-label"),
        text: el.textContent?.trim().slice(0, 100),
        className: el.className
      }));
  });

  console.log("Found editable candidates:", JSON.stringify(editables, null, 2));
  await browser.close();
}

main().catch(console.error);
