import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nova, rook } from "../test/fixtures";
import { BattleSetupPage } from "./BattleSetupPage";

vi.mock("../services/battles", () => ({
  fetchCharacters: vi.fn(),
  createBattle: vi.fn(),
}));

vi.mock("../services/system", () => ({
  fetchHealth: vi.fn().mockResolvedValue({
    status: "ok",
    version: "0.1.0",
    database_ready: true,
    llm_provider: "demo",
    llm_model: "openai/gpt-oss-120b",
    llm_key_present: false,
    demo_mode: true,
    tts_provider: "piper",
    tts_voices: 2,
    tts_ready: true,
  }),
  fetchVoices: vi.fn().mockResolvedValue([]),
}));

import { createBattle, fetchCharacters } from "../services/battles";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/battle/new"]}>
      <Routes>
        <Route path="/battle/new" element={<BattleSetupPage />} />
        <Route path="/battle/:battleId" element={<p>arena</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Both pickers list both robots, so names legitimately appear twice. */
async function waitForRobots() {
  const matches = await screen.findAllByText("Nova Vex");
  expect(matches.length).toBeGreaterThan(0);
}

describe("BattleSetupPage", () => {
  beforeEach(() => {
    vi.mocked(fetchCharacters).mockResolvedValue([nova, rook]);
    vi.mocked(createBattle).mockReset();
  });

  it("defaults to the two built-in robots", async () => {
    renderPage();
    await waitForRobots();
    expect(screen.getAllByText("Rook Blaze").length).toBeGreaterThan(0);
    // Each picker preselects a different robot.
    const pressed = screen
      .getAllByRole("button", { pressed: true })
      .map((button) => button.textContent);
    expect(pressed.some((text) => text?.includes("Nova Vex"))).toBe(true);
    expect(pressed.some((text) => text?.includes("Rook Blaze"))).toBe(true);
  });

  it("blocks a too-short topic without calling the API", async () => {
    renderPage();
    await waitForRobots();
    await userEvent.type(screen.getByLabelText(/battle topic/i), "ab");
    await userEvent.click(screen.getByRole("button", { name: /start battle/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/at least 3 characters/i);
    expect(createBattle).not.toHaveBeenCalled();
  });

  it("creates a battle and navigates to the arena", async () => {
    vi.mocked(createBattle).mockResolvedValue({
      id: "battle-9",
      topic: "best antenna",
    } as never);

    renderPage();
    await waitForRobots();
    await userEvent.type(screen.getByLabelText(/battle topic/i), "best antenna");
    await userEvent.click(screen.getByRole("button", { name: /start battle/i }));

    await waitFor(() => expect(createBattle).toHaveBeenCalledTimes(1));
    expect(createBattle).toHaveBeenCalledWith(
      expect.objectContaining({
        fighter_a_id: nova.id,
        fighter_b_id: rook.id,
        topic: "best antenna",
        round_count: 3,
      }),
    );
    expect(await screen.findByText("arena")).toBeInTheDocument();
  });

  it("applies a topic idea chip", async () => {
    renderPage();
    await waitForRobots();
    await userEvent.click(screen.getByRole("button", { name: "is cereal a soup" }));
    expect(screen.getByLabelText(/battle topic/i)).toHaveValue("is cereal a soup");
  });
});