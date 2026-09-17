import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    profile_dir = os.path.expanduser(
        os.getenv("GFLOW_DEFAULT_PROFILE_DIR", "/media/vpsg24gb/DATA/gflow/.gflow/profiles/default")
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            executable_path="/opt/google/chrome/chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        print("Navigating to https://labs.google/fx/tools/flow ...")
        await page.goto("https://labs.google/fx/tools/flow", wait_until="networkidle")
        await asyncio.sleep(3)
        print("Final URL:", page.url)
        print("Final Title:", await page.title())
        body_text = await page.inner_text("body")
        print("Body text snippet:\n", body_text[:1000])

if __name__ == "__main__":
    asyncio.run(main())
