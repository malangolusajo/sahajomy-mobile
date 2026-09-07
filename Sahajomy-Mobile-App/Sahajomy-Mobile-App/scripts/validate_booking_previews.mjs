import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const requireFromFrontend = createRequire(resolve(root, "../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const files = [
  "customer-search-container.html",
  "customer-book-cbm.html",
  "customer-booking-confirmation.html",
  "customer-express-air-cargo.html",
  "agent-containers.html",
  "agent-express-air-cargo.html",
];
const viewports = [
  { width: 360, height: 800 },
  { width: 393, height: 852 },
  { width: 430, height: 932 },
];
const browserCandidates = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);
const executablePath = browserCandidates.find(existsSync);

const browser = await chromium.launch({
  headless: true,
  ...(executablePath ? { executablePath } : {}),
});

const failures = [];
for (const viewport of viewports) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  for (const file of files) {
    const url = pathToFileURL(resolve(root, "html-previews", file)).href;
    try {
      await page.goto(url, { waitUntil: "load" });
      await page.evaluate(() => showStep(1));
      const layout = await page.evaluate(() => ({
        bodyWidth: document.body.scrollWidth,
        viewportWidth: window.innerWidth,
        phoneWidth: document.querySelector(".phone")?.scrollWidth,
        phoneClientWidth: document.querySelector(".phone")?.clientWidth,
        stepCount: document.querySelectorAll(".step").length,
        visibleAddress: Boolean(document.querySelector(".address")?.offsetParent),
      }));
      if (layout.bodyWidth > layout.viewportWidth + 1 || layout.phoneWidth > layout.phoneClientWidth + 1) {
        throw new Error(`horizontal overflow: ${JSON.stringify(layout)}`);
      }
      if (layout.stepCount !== 3 || layout.visibleAddress) {
        throw new Error(`invalid initial state: ${JSON.stringify(layout)}`);
      }

      const chooseButtonVisible = await page.locator(".serviceAction button").first().isVisible();
      if (!chooseButtonVisible) {
        throw new Error("first recommended service action is not visible");
      }
      await page.evaluate(() => chooseService("Responsive QA service"));
      await page.waitForTimeout(550);
      if (!(await page.locator('[data-step="1"]').evaluate((node) => node.classList.contains("done")))) {
        throw new Error("service selection did not complete step one");
      }
      if (await page.locator(".address").isVisible()) {
        throw new Error("China address became visible before Review");
      }

      await page.evaluate(() => openReview());
      await page.waitForTimeout(300);
      if (!(await page.getByRole("button", { name: "Confirm booking" }).isVisible())) {
        throw new Error("Review did not expose final confirmation");
      }
      if (!(await page.locator(".address").isVisible())) {
        throw new Error("Review did not expose the prepared China address");
      }

      await page.evaluate(() => confirmBooking());
      const completedSteps = await page.locator(".step.done").count();
      if (completedSteps !== 3) {
        throw new Error(`expected all steps complete, received ${completedSteps}`);
      }
    } catch (error) {
      failures.push(`${file} @ ${viewport.width}x${viewport.height}: ${error.message}`);
    }
  }
  await context.close();
}

await browser.close();
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(`Booking preview QA passed ${files.length * viewports.length} responsive flows.`);
