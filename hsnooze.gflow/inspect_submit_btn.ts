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
  const page = context.pages().find(p => p.url().includes("flow.google.com/project")) || context.pages()[0];

  console.log("Current URL:", page.url());

  // Dump all buttons on the project page
  const buttons = await page.$$eval("button", els => els.map(e => ({
    text: e.textContent?.trim() || "",
    aria: e.getAttribute("aria-label") || "",
    className: e.className,
    disabled: (e as HTMLButtonElement).disabled,
    html: e.outerHTML.slice(0, 150)
  })));

  console.log("Found buttons:", JSON.stringify(buttons, null, 2));
  await browser.close();
}

main().catch(console.error);
