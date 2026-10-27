export type Accent = "mint" | "coral" | string;
export type RobotMood = "idle" | "speaking" | "reacting" | "thinking";
export type RobotVariant = "nova" | "rook" | "baron" | "gizmo";

export interface RobotAvatarProps {
  accent: Accent;
  /** Which robot personality to draw — changes the face, not the colour. */
  variant?: RobotVariant;
  size?: number;
  /** Shorthand for mood="speaking". */
  speaking?: boolean;
  /**
   * idle      – gentle bobbing
   * speaking  – mic raised, mouth flapping, head bouncing
   * reacting  – just got roasted: flinch, wide eyes (Nova) / smug smirk (Rook)
   * thinking  – looking up, cooking a comeback
   */
  mood?: RobotMood;
  className?: string;
  /** Decorative by default; the surrounding card carries the name. */
  label?: string;
}

const PALETTE: Record<string, { body: string; dark: string; glow: string }> = {
  mint: { body: "#14b8a6", dark: "#0f766e", glow: "#ccfbf1" },
  coral: { body: "#f43f5e", dark: "#be123c", glow: "#ffe4e6" },
  violet: { body: "#8b5cf6", dark: "#5b21b6", glow: "#ede9fe" },
  amber: { body: "#f59e0b", dark: "#b45309", glow: "#fef3c7" },
};

export function paletteFor(accent: Accent) {
  return PALETTE[accent] ?? PALETTE.mint!;
}

/**
 * Hand-drawn inline SVG robot. Pure 2D shapes, no images and no animation
 * library. Motion is CSS (see `.bv-robot-*` in index.css) and is switched off
 * under prefers-reduced-motion.
 *
 * Small sizes (< 80px) show just the head and shoulders so avatars in speech
 * bubbles stay readable.
 */
export function RobotAvatar({
  accent,
  variant = "nova",
  size = 120,
  speaking = false,
  mood = "idle",
  className = "",
  label,
}: RobotAvatarProps) {
  const { body, dark, glow } = paletteFor(accent);
  const isNova = variant === "nova";
  const state: RobotMood = speaking ? "speaking" : mood;
  const bust = size < 80;
  const uid = `robot-${accent}-${variant}`;
  const eye = { nova: "#a7f3d0", rook: "#fecdd3", baron: "#ddd6fe", gizmo: "#fde68a" }[variant];
  const mouthColor = { nova: "#5eead4", rook: "#fda4af", baron: "#c4b5fd", gizmo: "#fcd34d" }[variant];

  const viewBox = bust ? "14 0 112 104" : "0 0 140 170";
  const height = bust ? size * (104 / 112) : size * (170 / 140);

  return (
    <svg
      width={size}
      height={height}
      viewBox={viewBox}
      role={label ? "img" : "presentation"}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      className={`bv-robot bv-robot-${state} ${className}`}
      style={{ overflow: "visible" }}
    >
      <defs>
        <linearGradient id={`${uid}-body`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={glow} />
          <stop offset="100%" stopColor={body} />
        </linearGradient>
        <linearGradient id={`${uid}-torso`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={body} />
          <stop offset="100%" stopColor={dark} />
        </linearGradient>
      </defs>

      <g className="bv-robot-body">
        {/* ---------- legs, torso, arms (cropped away in bust mode) ---------- */}
        <g>
          <rect x="48" y="146" width="15" height="20" rx="6" fill={dark} />
          <rect x="77" y="146" width="15" height="20" rx="6" fill={dark} />
          <rect x="43" y="159" width="24" height="9" rx="4.5" fill="#1f2430" />
          <rect x="73" y="159" width="24" height="9" rx="4.5" fill="#1f2430" />

          <rect
            x="38"
            y="98"
            width="64"
            height="52"
            rx="16"
            fill={`url(#${uid}-torso)`}
            stroke={dark}
            strokeWidth="2.5"
          />
          <rect x="52" y="110" width="36" height="22" rx="7" fill="#0f172a" opacity="0.88" />
          <circle cx="62" cy="121" r="3.4" fill={eye} className="bv-robot-chest" />
          <rect x="70" y="118" width="12" height="3" rx="1.5" fill={eye} opacity="0.7" />
          <rect x="70" y="123.5" width="8" height="3" rx="1.5" fill={eye} opacity="0.45" />
          <ChestDecor variant={variant} eye={eye} />

          {/* resting arm */}
          <g>
            <rect x="22" y="102" width="15" height="38" rx="7.5" fill={dark} />
            <circle cx="29.5" cy="143" r="8" fill={glow} stroke={dark} strokeWidth="2" />
          </g>

          {/* mic arm: swings up while speaking */}
          <g className="bv-robot-arm-mic" style={{ transformOrigin: "110px 106px" }}>
            <rect x="103" y="102" width="15" height="38" rx="7.5" fill={dark} />
            <circle cx="110.5" cy="143" r="8" fill={glow} stroke={dark} strokeWidth="2" />
            <rect x="107.5" y="128" width="6" height="22" rx="3" fill="#334155" />
            <circle cx="110.5" cy="125" r="6.5" fill="#cbd5e1" stroke="#475569" strokeWidth="1.5" />
            <path d="M106 123 h9 M106 126.5 h9" stroke="#64748b" strokeWidth="1" />
          </g>
        </g>

        {/* ---------- head ---------- */}
        <g className="bv-robot-head">
          <Topper variant={variant} dark={dark} />

          <rect x="18" y="52" width="10" height="26" rx="5" fill={dark} />
          <rect x="112" y="52" width="10" height="26" rx="5" fill={dark} />
          {isNova ? (
            <>
              <circle cx="23" cy="48" r="6" fill="#fbbf24" />
              <circle cx="117" cy="48" r="6" fill="#fbbf24" />
            </>
          ) : null}

          <rect
            x="28"
            y="28"
            width="84"
            height="70"
            rx="24"
            fill={`url(#${uid}-body)`}
            stroke={dark}
            strokeWidth="3"
          />
          {variant === "rook" ? (
            <path
              d="M34 40 Q40 34 48 36"
              stroke={dark}
              strokeWidth="2"
              fill="none"
              opacity="0.45"
              strokeLinecap="round"
            />
          ) : null}

          <rect x="38" y="42" width="64" height="42" rx="13" fill="#0f172a" opacity="0.94" />
          <rect x="43" y="46" width="30" height="5" rx="2.5" fill="#fff" opacity="0.09" />

          <Face variant={variant} state={state} eye={eye} mouth={mouthColor} />
          {variant === "baron" ? <Hat /> : null}
          {variant === "gizmo" ? <Goggles /> : null}

          {state === "reacting" ? (
            <path
              d="M108 38 Q112 46 108 50 Q104 46 108 38z"
              fill="#7dd3fc"
              stroke="#0284c7"
              strokeWidth="1"
              className="bv-robot-sweat"
            />
          ) : null}
        </g>
      </g>
    </svg>
  );
}

function NovaEyes({ state, color }: { state: RobotMood; color: string }) {
  if (state === "speaking") {
    return (
      <>
        <path d="M48 62 Q54 54 60 62" stroke={color} strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M80 62 Q86 54 92 62" stroke={color} strokeWidth="4" fill="none" strokeLinecap="round" />
      </>
    );
  }
  const y = state === "thinking" ? 58 : 61;
  const r = state === "reacting" ? 8 : 6.5;
  return (
    <>
      <circle cx="54" cy={y} r={r} fill={color} className="bv-robot-eye" />
      <circle cx="86" cy={y} r={r} fill={color} className="bv-robot-eye" />
      <circle cx="56" cy={y - 2} r="2.2" fill="#fff" opacity="0.9" />
      <circle cx="88" cy={y - 2} r="2.2" fill="#fff" opacity="0.9" />
    </>
  );
}

function RookEyes({ state, color }: { state: RobotMood; color: string }) {
  const lidTop = state === "speaking" ? 55 : 57;
  const pupilY = state === "reacting" || state === "thinking" ? 59 : 63;
  return (
    <>
      <rect x="45" y={lidTop} width="16" height="11" rx="4" fill={color} />
      <rect x="79" y={lidTop} width="16" height="11" rx="4" fill={color} />
      <rect x="44" y={lidTop - 1} width="18" height="6" rx="3" fill="#0f172a" />
      <rect x="78" y={lidTop - 1} width="18" height="6" rx="3" fill="#0f172a" />
      <circle cx="53" cy={pupilY} r="2.6" fill="#1f2430" />
      <circle cx="87" cy={pupilY} r="2.6" fill="#1f2430" />
    </>
  );
}

function Mouth({ isNova, state, color }: { isNova: boolean; state: RobotMood; color: string }) {
  if (state === "speaking") {
    return (
      <ellipse cx="70" cy="76" rx={isNova ? 9 : 7} ry="5" fill={color}>
        <animate attributeName="ry" values="2.5;6.5;3;7;2.5" dur="0.55s" repeatCount="indefinite" />
      </ellipse>
    );
  }
  if (state === "reacting") {
    return isNova ? (
      <ellipse cx="70" cy="77" rx="5" ry="6" fill="none" stroke={color} strokeWidth="2.6" />
    ) : (
      <path d="M58 77 Q70 76 80 70" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
    );
  }
  return isNova ? (
    <path d="M58 72 Q70 84 82 72" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
  ) : (
    <path d="M60 76 L80 76" stroke={color} strokeWidth="3" strokeLinecap="round" />
  );
}

export function variantForName(name: string): RobotVariant {
  const n = name.toLowerCase();
  if (n.includes("rook")) return "rook";
  if (n.includes("baron")) return "baron";
  if (n.includes("gizmo")) return "gizmo";
  return "nova";
}

/* ------------------------------------------------------------------ */
/* Per-robot parts                                                     */
/* ------------------------------------------------------------------ */

function novaBrow(side: "l" | "r", state: RobotMood) {
  const up = state === "speaking" || state === "reacting";
  if (side === "l") return up ? "M47 43 Q54 37 61 42" : "M47 46 Q54 42 61 46";
  return up ? "M79 42 Q86 37 93 43" : "M79 46 Q86 42 93 46";
}

function Topper({ variant, dark }: { variant: RobotVariant; dark: string }) {
  if (variant === "nova") {
    return (
      <>
        <line x1="70" y1="14" x2="70" y2="29" stroke={dark} strokeWidth="3.5" strokeLinecap="round" />
        <circle cx="70" cy="11" r="6.5" fill="#fbbf24" className="bv-robot-antenna" />
        <circle cx="70" cy="11" r="2.4" fill="#fffbeb" />
      </>
    );
  }
  if (variant === "rook") {
    return (
      <>
        <path
          d="M70 29 L70 20 L80 12"
          stroke={dark}
          strokeWidth="3.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <rect
          x="77"
          y="7"
          width="11"
          height="9"
          rx="2.5"
          fill="#94a3b8"
          transform="rotate(-25 82 11)"
          className="bv-robot-antenna"
        />
      </>
    );
  }
  if (variant === "gizmo") {
    return (
      <>
        <path d="M62 30 q-8 -7 0 -11 q8 -4 -3 -11" stroke={dark} strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M80 30 q8 -7 0 -11 q-8 -4 3 -11" stroke={dark} strokeWidth="3" fill="none" strokeLinecap="round" />
        <circle cx="58" cy="7" r="5" fill="#f43f5e" className="bv-robot-antenna" />
        <circle cx="84" cy="7" r="5" fill="#38bdf8" className="bv-robot-antenna" />
      </>
    );
  }
  return null; // baron wears a hat (drawn over the head)
}

function Hat() {
  return (
    <>
      <rect x="49" y="1" width="42" height="26" rx="5" fill="#1e1b4b" stroke="#0f0a2e" strokeWidth="2" />
      <rect x="49" y="16" width="42" height="7" fill="#a78bfa" />
      <rect x="37" y="24" width="66" height="8" rx="4" fill="#1e1b4b" stroke="#0f0a2e" strokeWidth="2" />
    </>
  );
}

function Goggles() {
  return (
    <>
      <path d="M32 36 Q70 26 108 36" stroke="#92400e" strokeWidth="4" fill="none" strokeLinecap="round" />
      <circle cx="54" cy="35" r="8.5" fill="#bae6fd" opacity="0.9" stroke="#92400e" strokeWidth="3" />
      <circle cx="86" cy="35" r="8.5" fill="#bae6fd" opacity="0.9" stroke="#92400e" strokeWidth="3" />
      <circle cx="51" cy="32" r="2.4" fill="#fff" opacity="0.9" />
      <circle cx="83" cy="32" r="2.4" fill="#fff" opacity="0.9" />
    </>
  );
}

function ChestDecor({ variant, eye }: { variant: RobotVariant; eye: string }) {
  if (variant === "nova") {
    return (
      <path
        d="M46 106 l1.6 3.4 3.4 1.6 -3.4 1.6 -1.6 3.4 -1.6 -3.4 -3.4 -1.6 3.4 -1.6z"
        fill="#fde68a"
      />
    );
  }
  if (variant === "rook") {
    return (
      <path
        d="M92 134 l8 -5 M95 140 l6 -3"
        stroke="#7f1d1d"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.5"
      />
    );
  }
  if (variant === "baron") {
    return (
      <g>
        <path d="M70 104 L56 98 L56 110 Z M70 104 L84 98 L84 110 Z" fill="#a78bfa" stroke="#4c1d95" strokeWidth="1.5" />
        <circle cx="70" cy="104" r="3.6" fill="#7c3aed" stroke="#4c1d95" strokeWidth="1.5" />
        <circle cx="93" cy="132" r="3" fill="#fbbf24" />
      </g>
    );
  }
  return (
    <g stroke={eye} strokeWidth="2" strokeLinecap="round" opacity="0.9">
      <circle cx="93" cy="118" r="5" fill="none" />
      <path d="M93 109 v-3 M93 127 v3 M84 118 h-3 M102 118 h3" />
    </g>
  );
}

function Face({
  variant,
  state,
  eye,
  mouth,
}: {
  variant: RobotVariant;
  state: RobotMood;
  eye: string;
  mouth: string;
}) {
  if (variant === "nova") {
    return (
      <>
        <NovaEyes state={state} color={eye} />
        <path d={novaBrow("l", state)} stroke={eye} strokeWidth="2.6" fill="none" strokeLinecap="round" />
        <path d={novaBrow("r", state)} stroke={eye} strokeWidth="2.6" fill="none" strokeLinecap="round" />
        <ellipse cx="46" cy="72" rx="5.5" ry="3" fill="#fb7185" opacity="0.55" />
        <ellipse cx="94" cy="72" rx="5.5" ry="3" fill="#fb7185" opacity="0.55" />
        <Mouth isNova state={state} color={mouth} />
      </>
    );
  }
  if (variant === "rook") {
    return (
      <>
        <RookEyes state={state} color={eye} />
        <path d={state === "speaking" ? "M45 50 L61 46" : "M45 48 L61 48"} stroke={eye} strokeWidth="3" strokeLinecap="round" />
        <path
          d={state === "speaking" ? "M79 43 L95 47" : state === "reacting" ? "M79 44 L95 46" : "M79 48 L95 48"}
          stroke={eye}
          strokeWidth="3"
          strokeLinecap="round"
        />
        <Mouth isNova={false} state={state} color={mouth} />
      </>
    );
  }
  if (variant === "baron") return <BaronFace state={state} eye={eye} mouth={mouth} />;
  return <GizmoFace state={state} eye={eye} mouth={mouth} />;
}

function BaronFace({ state, eye, mouth }: { state: RobotMood; eye: string; mouth: string }) {
  const wide = state === "reacting";
  return (
    <>
      <circle cx="54" cy="60" r={wide ? 6.5 : 5.5} fill={eye} />
      <circle cx="86" cy="60" r={wide ? 6.5 : 5.5} fill={eye} />
      {/* monocle + chain */}
      <circle cx="86" cy="60" r="11" fill="none" stroke="#fbbf24" strokeWidth="2.6" />
      <path d="M96 66 Q101 78 97 88" stroke="#fbbf24" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      {/* brows: one permanently unimpressed */}
      <path d="M46 49 Q54 45 62 49" stroke={eye} strokeWidth="2.8" fill="none" strokeLinecap="round" />
      <path
        d={state === "speaking" ? "M77 41 Q87 33 96 42" : "M77 45 Q87 39 96 46"}
        stroke={eye}
        strokeWidth="2.8"
        fill="none"
        strokeLinecap="round"
      />
      {/* handlebar moustache */}
      <path
        d="M52 71 Q61 66 70 71 Q79 66 88 71 Q84 77 70 74 Q56 77 52 71Z"
        fill={eye}
        stroke={mouth}
        strokeWidth="1"
      />
      <path d="M52 71 q-6 -1 -6 -8 M88 71 q6 -1 6 -8" stroke={eye} strokeWidth="2.4" fill="none" strokeLinecap="round" />
      {/* mouth below */}
      {state === "speaking" ? (
        <ellipse cx="70" cy="80" rx="6" ry="3" fill={mouth}>
          <animate attributeName="ry" values="1.5;4.5;2;5;1.5" dur="0.55s" repeatCount="indefinite" />
        </ellipse>
      ) : state === "reacting" ? (
        <ellipse cx="70" cy="80" rx="3.5" ry="3.8" fill="none" stroke={mouth} strokeWidth="2.2" />
      ) : (
        <path d="M63 80 L77 80" stroke={mouth} strokeWidth="2.6" strokeLinecap="round" />
      )}
    </>
  );
}

function GizmoFace({ state, eye, mouth }: { state: RobotMood; eye: string; mouth: string }) {
  const wide = state === "reacting";
  const pupilY = state === "thinking" ? 56 : 61;
  return (
    <>
      {/* mismatched eyes */}
      <circle cx="54" cy="60" r={wide ? 10 : 8.5} fill={eye} />
      <circle cx="54" cy={pupilY} r="3.6" fill="#1f2430">
        {state === "speaking" ? (
          <animate attributeName="cx" values="52;57;52;56;52" dur="0.6s" repeatCount="indefinite" />
        ) : null}
      </circle>
      <circle cx="87" cy="62" r={wide ? 6 : 4.5} fill={eye} />
      <circle cx="87" cy="62" r="1.8" fill="#1f2430" />
      {/* one brow cocked */}
      <path d="M45 47 L62 43" stroke={eye} strokeWidth="3" strokeLinecap="round" />
      <path
        d={state === "speaking" ? "M78 50 L95 45" : "M78 52 L95 50"}
        stroke={eye}
        strokeWidth="3"
        strokeLinecap="round"
      />
      {/* gap-toothed grin */}
      {state === "speaking" ? (
        <path d="M50 72 Q70 92 90 72 Z" fill={mouth}>
          <animate
            attributeName="d"
            values="M50 72 Q70 80 90 72 Z;M50 72 Q70 94 90 72 Z;M50 72 Q70 82 90 72 Z;M50 72 Q70 92 90 72 Z;M50 72 Q70 80 90 72 Z"
            dur="0.5s"
            repeatCount="indefinite"
          />
        </path>
      ) : state === "reacting" ? (
        <path d="M54 77 q4 -6 8 0 t8 0 t8 0" stroke={mouth} strokeWidth="3" fill="none" strokeLinecap="round" />
      ) : (
        <path
          d="M52 72 L58 79 L64 72 L70 79 L76 72 L82 79 L88 72"
          stroke={mouth}
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </>
  );
}