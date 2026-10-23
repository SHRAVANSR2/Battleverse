export type Accent = "mint" | "coral" | string;

export interface RobotAvatarProps {
  accent: Accent;
  /** Which robot personality to draw — changes the face, not the colour. */
  variant?: "nova" | "rook";
  size?: number;
  speaking?: boolean;
  className?: string;
  /** Decorative by default; the surrounding card carries the name. */
  label?: string;
}

const PALETTE: Record<string, { body: string; dark: string; glow: string }> = {
  mint: { body: "#14b8a6", dark: "#0f766e", glow: "#ccfbf1" },
  coral: { body: "#f43f5e", dark: "#be123c", glow: "#ffe4e6" },
};

export function paletteFor(accent: Accent) {
  return PALETTE[accent] ?? PALETTE.mint!;
}

/**
 * Hand-drawn inline SVG robot. Pure 2D shapes — no images, no 3D, no animation
 * library. `speaking` only swaps the face; motion lives in CSS elsewhere and is
 * disabled under prefers-reduced-motion.
 */
export function RobotAvatar({
  accent,
  variant = "nova",
  size = 120,
  speaking = false,
  className = "",
  label,
}: RobotAvatarProps) {
  const { body, dark, glow } = paletteFor(accent);
  const isNova = variant === "nova";
  const uid = `robot-${accent}-${variant}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role={label ? "img" : "presentation"}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      className={className}
    >
      <defs>
        <linearGradient id={`${uid}-body`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={glow} />
          <stop offset="100%" stopColor={body} />
        </linearGradient>
      </defs>

      {/* antenna */}
      <line x1="60" y1="14" x2="60" y2="26" stroke={dark} strokeWidth="3" strokeLinecap="round" />
      <circle cx="60" cy="11" r="5" fill={isNova ? "#fbbf24" : "#94a3b8"} />

      {/* ears */}
      <rect x="16" y="50" width="8" height="20" rx="4" fill={dark} />
      <rect x="96" y="50" width="8" height="20" rx="4" fill={dark} />

      {/* head */}
      <rect
        x="24"
        y="26"
        width="72"
        height="58"
        rx="20"
        fill={`url(#${uid}-body)`}
        stroke={dark}
        strokeWidth="2.5"
      />

      {/* screen */}
      <rect x="34" y="38" width="52" height="32" rx="10" fill="#0f172a" opacity="0.92" />

      {/* eyes */}
      {isNova ? (
        <>
          <circle cx="49" cy="52" r="5" fill="#a7f3d0">
            <animate attributeName="ry" values="5;5;1.2;5" dur="4.2s" repeatCount="indefinite" />
          </circle>
          <circle cx="71" cy="52" r="5" fill="#a7f3d0" />
        </>
      ) : (
        <>
          <rect x="43" y="49" width="11" height="6" rx="3" fill="#fecdd3" />
          <rect x="66" y="49" width="11" height="6" rx="3" fill="#fecdd3" />
        </>
      )}

      {/* mouth */}
      {speaking ? (
        <ellipse cx="60" cy="62" rx="7" ry="4.5" fill={isNova ? "#5eead4" : "#fda4af"} />
      ) : isNova ? (
        <path
          d="M53 61 Q60 67 67 61"
          stroke="#5eead4"
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
        />
      ) : (
        <line x1="54" y1="63" x2="66" y2="63" stroke="#fda4af" strokeWidth="2.5" strokeLinecap="round" />
      )}

      {/* body */}
      <rect x="38" y="88" width="44" height="22" rx="9" fill={dark} />
      <circle cx="60" cy="99" r="5" fill={glow} opacity="0.9" />
    </svg>
  );
}

export function variantForName(name: string): "nova" | "rook" {
  return name.toLowerCase().includes("rook") ? "rook" : "nova";
}