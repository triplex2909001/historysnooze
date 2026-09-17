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

        print("Page URL:", page.url)
        vids = await page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll("video, img"));
            return els.map(e => ({
                tag: e.tagName,
                src: e.currentSrc || e.src || "",
                attrSrc: e.getAttribute("src") || "",
                className: e.className
            }));
        }''')
        print("Found media elements:", json.dumps(vids, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
