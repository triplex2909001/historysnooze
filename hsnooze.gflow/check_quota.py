import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:49657")
        context = browser.contexts[0]
        flow_page = context.pages[0]
        print(f"URL: {flow_page.url}")
        print(f"Title: {await flow_page.title()}")

        errors = await flow_page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('.error-text, flow-chat-error-card, [class*="error"]'));
            return els.map(e => e.textContent.trim()).filter(Boolean);
        }""")
        print(f"Errors found: {errors}")

        # Check text content of body
        body_text = await flow_page.evaluate("() => document.body.innerText")
        print("Body text contains 'usage limit':", "usage limit" in body_text.lower())
        print("Body text contains 'rate limit':", "rate limit" in body_text.lower())

if __name__ == "__main__":
    asyncio.run(main())
