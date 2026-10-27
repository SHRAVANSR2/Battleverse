import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../services/client";
import { makeBattle } from "../../test/fixtures";
import { VotingPanel } from "./VotingPanel";

vi.mock("../../services/battles", () => ({
  castVote: vi.fn(),
}));

import { castVote } from "../../services/battles";

function renderPanel(battle = makeBattle({ status: "awaiting_vote" })) {
  return render(
    <MemoryRouter initialEntries={["/battle/battle-1"]}>
      <Routes>
        <Route path="/battle/:battleId" element={<VotingPanel battle={battle} onDecided={() => {}} />} />
        <Route path="/battle/:battleId/result" element={<p>result page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VotingPanel", () => {
  beforeEach(() => {
    vi.mocked(castVote).mockReset();
  });

  it("offers a vote button for each fighter", () => {
    renderPanel();
    expect(screen.getByRole("button", { name: "Vote for Nova Vex" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Vote for Rook Blaze" })).toBeInTheDocument();
  });

  it("sends the vote and navigates to the result page", async () => {
    vi.mocked(castVote).mockResolvedValue({} as Awaited<ReturnType<typeof castVote>>);
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Vote for Rook Blaze" }));
    await waitFor(() => expect(screen.getByText("result page")).toBeInTheDocument());
    expect(vi.mocked(castVote)).toHaveBeenCalledWith("battle-1", "char-rook", expect.any(String));
  });

  it("disables both buttons while a vote is in flight", async () => {
    const deferred: { promise: Promise<unknown>; resolve: (value: unknown) => void } = {
      promise: Promise.resolve(),
      resolve: () => {},
    };
    deferred.promise = new Promise((resolve) => {
      deferred.resolve = resolve;
    });
    vi.mocked(castVote).mockReturnValue(deferred.promise as Promise<Awaited<ReturnType<typeof castVote>>>);
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Vote for Nova Vex" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Vote for Rook Blaze" })).toBeDisabled(),
    );
    deferred.resolve(undefined);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Vote for Rook Blaze" })).toBeEnabled(),
    );
  });

  it("shows the API message when the vote fails", async () => {
    vi.mocked(castVote).mockRejectedValue(
      new ApiError("The vote could not be saved.", { code: "PROVIDER_ERROR", status: 502 }),
    );
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Vote for Nova Vex" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("could not be saved"));
    // Both buttons stay usable so the user can retry.
    expect(screen.getByRole("button", { name: "Vote for Nova Vex" })).toBeEnabled();
  });

  it("explains the one-vote rule on ALREADY_VOTED", async () => {
    vi.mocked(castVote).mockRejectedValue(
      new ApiError("You already voted.", { code: "ALREADY_VOTED", status: 409 }),
    );
    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Vote for Rook Blaze" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("One vote per browser per battle"),
    );
  });
});
