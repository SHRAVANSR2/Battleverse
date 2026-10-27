import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeVerse } from "../../test/fixtures";
import { SpeechBubble } from "./SpeechBubble";

const baseProps = {
  side: "left" as const,
  speaking: false,
  onPlay: vi.fn(),
  pending: false,
  error: null,
};

describe("SpeechBubble", () => {
  it("labels demo verses so they can never look AI-generated", () => {
    render(<SpeechBubble {...baseProps} verse={makeVerse({ is_demo: true })} />);
    expect(screen.getByText("demo")).toBeInTheDocument();
  });

  it("labels real Groq verses with their provider", () => {
    render(
      <SpeechBubble
        {...baseProps}
        verse={makeVerse({ is_demo: false, provider: "groq" })}
      />,
    );
    expect(screen.queryByText("demo")).not.toBeInTheDocument();
    expect(screen.getByText("groq")).toBeInTheDocument();
  });

  it("labels Gemini verses with their provider", () => {
    render(
      <SpeechBubble
        {...baseProps}
        verse={makeVerse({ is_demo: false, provider: "gemini" })}
      />,
    );
    expect(screen.getByText("gemini")).toBeInTheDocument();
  });

  it("shows a text Speaking label (not colour alone) and calls onPlay", async () => {
    const onPlay = vi.fn();
    render(<SpeechBubble {...baseProps} onPlay={onPlay} verse={makeVerse()} speaking />);
    expect(screen.getByText("Speaking")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /restart this line/i }));
    expect(onPlay).toHaveBeenCalledWith("verse-1");
  });

  it("disables play while generating", () => {
    render(<SpeechBubble {...baseProps} verse={makeVerse()} pending />);
    expect(screen.getByRole("button", { name: /speak this line/i })).toBeDisabled();
  });

  it("surfaces an inline audio error", () => {
    render(<SpeechBubble {...baseProps} verse={makeVerse()} error="TTS is missing" />);
    expect(screen.getByRole("alert")).toHaveTextContent("TTS is missing");
  });

  it("renders each verse line", () => {
    render(<SpeechBubble {...baseProps} verse={makeVerse()} />);
    expect(screen.getByText(/First line about antennas/)).toBeInTheDocument();
  });
});