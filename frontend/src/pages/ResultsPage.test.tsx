import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../services/client";
import { makeBattle, nova, rook } from "../test/fixtures";
import type { Result } from "../types/api";
import { ResultsPage } from "./ResultsPage";

vi.mock("../services/battles", () => ({
  fetchBattle: vi.fn(),
  fetchResult: vi.fn(),
  requestRematch: vi.fn(),
}));

import { fetchBattle, fetchResult, requestRematch } from "../services/battles";

function makeResult(overrides: Partial<Result> = {}): Result {
  return {
    battle_id: "battle-1",
    status: "completed",
    is_draw: false,
    winner: { character_id: nova.id, name: nova.name, accent: nova.accent, votes: 2, vote_share: 1 },
    fighters: [
      { character_id: nova.id, name: nova.name, accent: nova.accent, votes: 2, vote_share: 1 },
      { character_id: rook.id, name: rook.name, accent: rook.accent, votes: 0, vote_share: 0 },
    ],
    vote_count: 2,
    best_verse: null,
    ai_judge: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/battle/battle-1/result"]}>
      <Routes>
        <Route path="/battle/:battleId/result" element={<ResultsPage />} />
        <Route path="/battle/:battleId" element={<p>arena</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchResult).mockReset();
    vi.mocked(fetchBattle).mockReset();
    vi.mocked(requestRematch).mockReset();
  });

  it("shows the winner's name and the vote tally", async () => {
    vi.mocked(fetchResult).mockResolvedValue(makeResult());
    vi.mocked(fetchBattle).mockResolvedValue(makeBattle({ status: "completed" }));
    renderPage();

    await waitFor(() => expect(screen.getByText("Nova Vex wins!")).toBeInTheDocument());
    expect(screen.getByText(/Votes \(2\)/)).toBeInTheDocument();
    expect(screen.getByText(/2 votes · 100%/)).toBeInTheDocument();
    expect(screen.getByText(/0 votes · 0%/)).toBeInTheDocument();
    expect(screen.getByText("Human vote only. No AI judge was used.")).toBeInTheDocument();
  });

  it("shows the losing robot with a zero share", async () => {
    const result = makeResult();
    vi.mocked(fetchResult).mockResolvedValue(result);
    vi.mocked(fetchBattle).mockResolvedValue(makeBattle({ status: "completed" }));
    renderPage();

    await waitFor(() => expect(screen.getByText("Nova Vex wins!")).toBeInTheDocument());
    expect(screen.getByText("Rook Blaze")).toBeInTheDocument();
  });

  it("reports a draw when there is no winner", async () => {
    vi.mocked(fetchResult).mockResolvedValue(makeResult({ is_draw: true, winner: null }));
    vi.mocked(fetchBattle).mockResolvedValue(makeBattle({ status: "completed" }));
    renderPage();

    await waitFor(() => expect(screen.getByText("It's a draw!")).toBeInTheDocument());
    expect(screen.getByText("Nobody won this one.")).toBeInTheDocument();
  });

  it("starts a rematch and navigates to the new battle", async () => {
    vi.mocked(fetchResult).mockResolvedValue(makeResult());
    vi.mocked(fetchBattle).mockResolvedValue(makeBattle({ status: "completed" }));
    vi.mocked(requestRematch).mockResolvedValue(makeBattle({ id: "battle-2" }));
    renderPage();

    await waitFor(() => expect(screen.getByText("Nova Vex wins!")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Rematch" }));
    await waitFor(() => expect(screen.getByText("arena")).toBeInTheDocument());
    expect(vi.mocked(requestRematch)).toHaveBeenCalledWith("battle-1");
  });

  it("shows an error state when the result cannot be loaded", async () => {
    vi.mocked(fetchResult).mockRejectedValue(new ApiError("The server had a problem.", { status: 500 }));
    vi.mocked(fetchBattle).mockRejectedValue(new ApiError("The server had a problem.", { status: 500 }));
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("The server had a problem.")).toBeInTheDocument(),
    );
  });
});
