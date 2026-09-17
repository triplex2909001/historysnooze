import type { Page } from "playwright";

export function flowLocators(page: Page) {
  return {
    // The Flow prompt is a contenteditable ProseMirror div ("What do you want to create?").
    promptBox: page.locator('.ProseMirror[contenteditable="true"], [role="textbox"][contenteditable="true"]'),
    // Signed-in Flow dashboard/landing (projects view). Proves an authenticated session
    // for `doctor`; the prompt box only exists once a project is open.
    dashboardMarker: page.getByRole("button", { name: /new project/i }),
    newProjectButton: page.getByRole("button", { name: /new project/i }),
    // Submit button: carrying the arrow_forward icon or aria-label="Start generation".
    submitButton: page.locator('button[aria-label="Start generation"], button[type="submit"], button').filter({ hasText: /arrow_forward/ }),
    // The model/settings pill (e.g. "🍌 Nano Banana 2 / crop_16_9 / x2") opens the popover
    // with Image/Video mode, aspect ratio, output count and model.
    settingsButton: page.locator("button").filter({ hasText: /crop_(16_9|9_16|square|portrait|landscape)/ }),
    rateLimitMarker: page.getByText(/unusual activity|trying again too|rate limit/i),
    creditMarker: page.getByText(/run out of credits|insufficient credits|no credits left|reached your usage limit|usage limit|quota/i),
    blockedMarker: page.getByText(/can.?t help with|violates|content policy/i),
    failedMarker: page.getByText(/generation failed|couldn.?t generate|something went wrong|the agent failed/i),
    manualActionMarker: page.getByText(/verify your identity|sign in to continue|consent required/i)
  };
}
