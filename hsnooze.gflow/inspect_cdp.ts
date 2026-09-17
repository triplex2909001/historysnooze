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
  console.log("Current URL:", page.url());
  console.log("Current Title:", await page.title());

  const buttons = await page.$$eval("button, a, [role=button], [role=textbox]", els => els.map(e => ({
    tag: e.tagName,
    text: e.textContent?.trim() || "",
    role: e.getAttribute("role") || "",
    aria: e.getAttribute("aria-label") || ""
  })));
  console.log("Elements found:", buttons);

  await browser.close();
}

main().catch(console.error);
