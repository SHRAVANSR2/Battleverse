import type { Character } from "../../types/api";
import { paletteFor, RobotAvatar, variantForName } from "../character/RobotAvatar";

export interface FighterCardProps {
  character: Character;
  speaking: boolean;
  active: boolean;
  side: "left" | "right";
}

export function FighterCard({ character, speaking, active, side }: FighterCardProps) {
  const palette = paletteFor(character.accent);
  const role = side === "left" ? "Robot A" : "Robot B";

  return (
    <div
      className={`bv-card flex items-center gap-3 px-4 py-3 ${side === "right" ? "flex-row-reverse text-right" : ""}`}
      style={{ borderColor: speaking ? palette.body : "var(--color-line)" }}
      aria-current={active ? "true" : undefined}
    >
      <RobotAvatar
        accent={character.accent}
        variant={variantForName(character.name)}
        size={56}
        speaking={speaking}
      />
      <div className="min-w-0">
        <div
          className={`flex flex-wrap items-center gap-2 ${side === "right" ? "justify-end" : ""}`}
        >
          <span className="font-bold">{character.name}</span>
          <span className="rounded-full bg-[#f5f1ec] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--color-muted)]">
            {role}
          </span>
        </div>
        <p className="truncate text-xs text-[var(--color-muted)]" title={character.tagline}>
          {character.tagline}
        </p>
        {speaking ? (
          <span
            className="mt-0.5 inline-flex items-center gap-1 text-xs font-bold"
            style={{ color: palette.dark }}
          >
            <span className="bv-wave" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            Speaking
          </span>
        ) : null}
      </div>
    </div>
  );
}