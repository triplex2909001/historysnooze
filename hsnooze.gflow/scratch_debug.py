import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    profile_dir = os.path.expanduser(
        os.getenv("GFLOW_DEFAULT_PROFILE_DIR", "/media/vpsg24gb/DATA/gflow/.gflow/profiles/default")
    )
    out_dir = os.getenv("GFLOW_OUT_DIR", "/media/vpsg24gb/DATA/gflow/out")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            profile_dir,
            executable_path="/opt/google/chrome/chrome",
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://labs.google/fx/tools/flow", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        print("Page URL:", page.url)
        print("Page Title:", await page.title())

        buttons = await page.locator("button, a").all()
        print(f"Total buttons/links: {len(buttons)}")
        for idx, btn in enumerate(buttons):
            try:
                txt = (await btn.text_content() or "").strip()
                if txt:
                    print(f"[{idx}] Text: '{txt}'")
            except:
                pass

        os.makedirs(out_dir, exist_ok=True)
        await page.screenshot(path=os.path.join(out_dir, "debug_flow.png"))
        print("Saved debug_flow.png")

if __name__ == "__main__":
    asyncio.run(main())
