import asyncio
import json
import os
from playwright.async_api import async_playwright

async def main():
    profile_dir = os.path.expanduser(
        os.getenv("GFLOW_DEFAULT_PROFILE_DIR", "/media/vpsg24gb/DATA/gflow/.gflow/profiles/default")
    )
    with open(os.path.join(profile_dir, "DevToolsActivePort")) as f:
        port = int(f.readline().strip())

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0]
        page = context.pages[0]
        for pg in context.pages:
            if "project" in pg.url or "flow" in pg.url:
                page = pg
                break

        print("=== PAGE INFO ===")
        print("URL:", page.url)
        print("Title:", await page.title())

        print("\n=== VIDEOS ON PAGE ===")
        vids = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll("video"));
            return els.map(e => ({
                src: e.currentSrc || e.src || "",
                attrSrc: e.getAttribute("src") || "",
                duration: e.duration,
                paused: e.paused,
                readyState: e.readyState,
                outerHTML: e.outerHTML.slice(0, 200)
            }));
        }''')
        print(json.dumps(vids, indent=2))

        print("\n=== IMAGES ON PAGE ===")
        imgs = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll("img"));
            return els.map(e => ({
                src: e.currentSrc || e.src || "",
                alt: e.alt,
                className: e.className
            })).filter(i => i.src.includes("media") || i.src.includes("blob") || i.src.includes("googleusercontent"));
        }''')
        print(json.dumps(imgs, indent=2))

        print("\n=== DOWNLOAD BUTTONS ON PAGE ===")
        dl_btns = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll("button, a"));
            return els
                .filter(e => (e.textContent || "").toLowerCase().includes("download") || (e.getAttribute("aria-label") || "").toLowerCase().includes("download"))
                .map(e => ({
                    tag: e.tagName,
                    text: e.textContent?.trim(),
                    aria: e.getAttribute("aria-label"),
                    html: e.outerHTML.slice(0, 200)
                }));
        }''')
        print(json.dumps(dl_btns, indent=2))

        # Take screenshot
        out_dir = os.getenv("GFLOW_OUT_DIR", "/media/vpsg24gb/DATA/gflow/out")
        os.makedirs(out_dir, exist_ok=True)
        screenshot_path = os.path.join(out_dir, "current_state.png")
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved to {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(main())
