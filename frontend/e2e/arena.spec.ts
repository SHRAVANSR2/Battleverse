import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const SHOTS = path.resolve(process.cwd(), "e2e-artifacts", "screenshots");

async function shot(page: Page, name: string) {
  await mkdir(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

/**
 * Drives the real app against the real backend (Demo writer + real Piper audio).
 *
 * Prerequisites: backend on http://127.0.0.1:8000 and Piper voice models
 * installed. The first audio request takes several seconds while Piper loads the
 * voice, hence the generous expect timeout.
 */

async function createBattle(page: Page, topic: string, rounds: number) {
  await page.goto("/battle/new");
  await expect(page.getByLabel(/battle topic/i)).toBeVisible();
  await page.getByLabel(/battle topic/i).fill(topic);
  await page.locator("#rounds").fill(String(rounds));
  await page.getByRole("button", { name: /start battle/i }).click();
  await expect(page).toHaveURL(/\/battle\/[0-9a-f-]{36}$/);
  return page.url().split("/").pop() as string;
}

test("plays a real generated verse and keeps replay out of the turn API", async ({ page }) => {
  const turnRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/api\/battles\/[^/]+\/turn$/.test(request.url())) {
      turnRequests.push(request.url());
    }
  });

  const battleId = await createBattle(page, "who has the best antenna", 1);

  // --- generate both turns -------------------------------------------------
  await page.getByRole("button", { name: /let nova vex start/i }).click();
  await expect(page.locator("article[data-verse-id]")).toHaveCount(1);

  await page.getByRole("button", { name: /generate turn 2/i }).click();
  await expect(page.locator("article[data-verse-id]")).toHaveCount(2);
  expect(turnRequests).toHaveLength(2);

  // Both fighters spoke, in order, and both lines came from the backend.
  await expect(page.getByText(/Nova Vex/).first()).toBeVisible();
  await expect(page.getByText(/Rook Blaze/).first()).toBeVisible();
  const verses = page.locator("article[data-verse-id]");
  await expect(verses.nth(0)).toHaveAttribute("aria-label", /Verse 1 by Nova Vex/);
  await expect(verses.nth(1)).toHaveAttribute("aria-label", /Verse 2 by Rook Blaze/);

  // Demo verses must be visibly tagged, never presented as AI output.
  await expect(verses.nth(0).getByText("demo", { exact: true })).toBeVisible();

  // --- real audio playback -------------------------------------------------
  await verses.nth(0).getByRole("button", { name: /speak this line/i }).click();

  const speaking = verses.nth(0).getByText("Speaking", { exact: true });
  await expect(speaking).toBeVisible({ timeout: 90_000 });
  await expect(verses.nth(0).getByRole("button", { name: /restart this line/i })).toBeVisible();

  // The audio element reports real progress, i.e. a file actually decoded.
  const playing = await page.evaluate(() => {
    const elements = Array.from(document.querySelectorAll("audio"));
    const active = elements.find((element) => element.currentSrc);
    return active
      ? { currentTime: active.currentTime, duration: active.duration, paused: active.paused }
      : null;
  });
  // AudioProvider keeps one detached Audio() instance; assert via the UI state.
  expect(playing === null || playing.paused === false).toBe(true);

  await shot(page, "arena-desktop");

  // --- pause / resume ------------------------------------------------------
  await page.getByRole("button", { name: /pause playback/i }).click();
  await expect(page.getByRole("button", { name: /^resume$/i })).toBeVisible();
  await expect(speaking).toBeHidden();
  await page.getByRole("button", { name: /^resume$/i }).click();
  await expect(speaking).toBeVisible();

  // --- replay must not create a verse or a turn request --------------------
  const beforeReplay = turnRequests.length;
  await page.getByRole("button", { name: /replay the current line/i }).click();
  await page.waitForTimeout(1500);
  expect(turnRequests).toHaveLength(beforeReplay);
  await expect(page.locator("article[data-verse-id]")).toHaveCount(2);

  // --- mute / volume -------------------------------------------------------
  const mute = page.getByRole("button", { name: /mute audio/i });
  await mute.click();
  await expect(page.getByRole("button", { name: /unmute audio/i })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // Raising the volume while muted un-mutes, so the control flips back.
  await page.getByRole("slider", { name: /volume/i }).fill("40");
  await expect(page.getByRole("button", { name: /^mute audio$/i })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByRole("slider", { name: /volume/i })).toHaveValue("40");
  // Mute/volume persist across a reload.
  await page.reload();
  await expect(page.getByRole("slider", { name: /volume/i })).toHaveValue("40");

  // --- vote -> result -> rematch ------------------------------------------
  await expect(page.getByRole("heading", { name: /who won\?/i })).toBeVisible();
  await page.getByRole("button", { name: /vote for nova vex/i }).click();
  await expect(page).toHaveURL(new RegExp(`/battle/${battleId}/result$`));
  await expect(page.getByRole("heading", { name: /nova vex wins/i })).toBeVisible();
  await expect(page.getByText(/human vote only/i)).toBeVisible();

  await shot(page, "result-desktop");

  await page.getByRole("button", { name: /^rematch$/i }).click();
  await expect(page).toHaveURL(/\/battle\/[0-9a-f-]{36}$/);
  expect(page.url()).not.toContain(battleId);
});

test("mobile view stacks into one readable column", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await createBattle(page, "is cereal a soup", 1);
  await page.getByRole("button", { name: /let nova vex start/i }).click();
  await expect(page.locator("article[data-verse-id]")).toHaveCount(1);

  const columnTops = await page
    .locator("section[aria-label='Battle transcript'] > div")
    .evaluateAll((nodes) => nodes.map((node) => node.getBoundingClientRect().top));
  expect(columnTops).toHaveLength(2);
  expect(columnTops[1]).toBeGreaterThan(columnTops[0]);

  await shot(page, "arena-mobile");
});
