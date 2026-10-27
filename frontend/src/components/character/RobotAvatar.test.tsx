import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RobotAvatar, paletteFor, variantForName } from "./RobotAvatar";

describe("RobotAvatar", () => {
  it("is decorative when no label is given", () => {
    const { container } = render(<RobotAvatar accent="mint" />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).not.toHaveAttribute("role", "img");
  });

  it("exposes a label when given", () => {
    render(<RobotAvatar accent="coral" label="Rook Blaze" />);
    expect(screen.getByRole("img", { name: "Rook Blaze" })).toBeInTheDocument();
  });

  it("never relies on colour alone: both variants draw distinct faces", () => {
    const nova = render(<RobotAvatar accent="mint" variant="nova" />).container.innerHTML;
    const rook = render(<RobotAvatar accent="coral" variant="rook" />).container.innerHTML;
    expect(nova).not.toEqual(rook);
  });

  it("draws four different robots, even in the same colour", () => {
    const faces = (["nova", "rook", "baron", "gizmo"] as const).map(
      (variant) => render(<RobotAvatar accent="mint" variant={variant} />).container.innerHTML,
    );
    expect(new Set(faces).size).toBe(4);
  });

  it("changes expression with mood", () => {
    const idle = render(<RobotAvatar accent="mint" variant="baron" mood="idle" />).container.innerHTML;
    const speaking = render(<RobotAvatar accent="mint" variant="baron" speaking />).container;
    expect(speaking.querySelector("svg")).toHaveClass("bv-robot-speaking");
    expect(speaking.innerHTML).not.toEqual(idle);
  });

  it("maps accents to palettes with a safe fallback", () => {
    expect(paletteFor("mint").body).toBe("#14b8a6");
    expect(paletteFor("coral").body).toBe("#f43f5e");
    expect(paletteFor("violet").body).toBe("#8b5cf6");
    expect(paletteFor("amber").body).toBe("#f59e0b");
    expect(paletteFor("unknown").body).toBe("#14b8a6");
  });

  it("derives the variant from the name", () => {
    expect(variantForName("Rook Blaze")).toBe("rook");
    expect(variantForName("Nova Vex")).toBe("nova");
    expect(variantForName("Baron Byte")).toBe("baron");
    expect(variantForName("Gizmo Jinx")).toBe("gizmo");
  });
});