import { NavLink } from "react-router-dom";
import { useHealth } from "../../hooks/useHealth";
import { Chip } from "../ui/Chip";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/battle/new", label: "New battle" },
  { to: "/history", label: "History" },
  { to: "/leaderboard", label: "Leaderboard" },
];

export function NavBar() {
  const { health } = useHealth();

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--color-line)] bg-[color-mix(in_srgb,var(--color-bg)_88%,white)] backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <NavLink
          to="/"
          className="flex items-center gap-2 rounded-full text-[var(--color-ink)] no-underline"
        >
          <LogoMark />
          <span className="text-lg font-extrabold tracking-tight">BattleVerse</span>
        </NavLink>

        <nav aria-label="Main" className="order-3 w-full sm:order-2 sm:w-auto">
          <ul className="flex flex-wrap items-center gap-1">
            {links.map((link) => (
              <li key={link.to}>
                <NavLink
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) =>
                    `bv-transition block rounded-full px-3 py-2 text-sm font-semibold no-underline ${
                      isActive
                        ? "bg-white text-[var(--color-primary-ink)] shadow-[var(--shadow-soft)]"
                        : "text-[var(--color-muted)] hover:bg-white/70 hover:text-[var(--color-ink)]"
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="order-2 ml-auto flex items-center gap-2 sm:order-3">
          {health?.demo_mode ? (
            <Chip tone="demo" title="No Groq API key configured — verses are scripted, not AI-generated.">
              Demo Mode
            </Chip>
          ) : null}
          {health?.tts_provider === "fake" ? (
            <Chip tone="warn" title="TTS_PROVIDER=fake — audio is a synthetic test tone.">
              Test tone
            </Chip>
          ) : null}
          <BackendDot health={health} />
        </div>
      </div>
    </header>
  );
}

function BackendDot({ health }: { health: ReturnType<typeof useHealth>["health"] }) {
  const ok = Boolean(health?.database_ready);
  const label = ok ? "Backend connected" : health ? "Backend degraded" : "Backend offline";
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-muted)]"
      title={label}
    >
      <span
        aria-hidden="true"
        className="size-2 rounded-full"
        style={{ backgroundColor: ok ? "var(--color-ok)" : "var(--color-danger)" }}
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}

export function LogoMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect x="2" y="6" width="13" height="13" rx="4" fill="var(--color-robot-a)" />
      <rect x="17" y="13" width="13" height="13" rx="4" fill="var(--color-robot-b)" />
      <circle cx="8.5" cy="12.5" r="1.6" fill="#fff" />
      <circle cx="23.5" cy="19.5" r="1.6" fill="#fff" />
    </svg>
  );
}